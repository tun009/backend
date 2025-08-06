import asyncio
import json
import logging
import time
import uuid
from typing import Optional, List, Dict

import aiomqtt
from app.core.config import settings
from app.schemas.device_schemas import DeviceRealtimeResponse

logger = logging.getLogger(__name__)


class DeviceTimeoutError(Exception):
    pass

class MQTTConnectionError(Exception):
    pass

class InvalidResponseError(Exception):
    pass

class MQTTPersistentService:
    """Single persistent MQTT connection service"""

    _instance: Optional["MQTTPersistentService"] = None
    _client: Optional[aiomqtt.Client] = None
    _connected: bool = False
    _pending_requests: Dict[str, asyncio.Future] = {}
    _response_listener_task: Optional[asyncio.Task] = None

    def __new__(cls) -> "MQTTPersistentService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.broker_host = settings.MQTT_BROKER_HOST
            self.broker_port = settings.MQTT_BROKER_PORT
            self.username = settings.MQTT_USERNAME
            self.password = settings.MQTT_PASSWORD
            self.user_no = settings.MQTT_USER_NO
            self.timeout = settings.MQTT_TIMEOUT
            self._initialized = True

    @classmethod
    async def initialize(cls) -> None:
        """Initialize persistent MQTT connection"""
        instance = cls()
        if instance._connected:
            logger.info("MQTT already connected")
            return

        try:
            logger.info(f"Initializing MQTT connection to {instance.broker_host}:{instance.broker_port}")

            client_id = f"obu_api_{instance.user_no}_{int(time.time())}"
            instance._client = aiomqtt.Client(
                hostname=instance.broker_host,
                port=instance.broker_port,
                username=instance.username,
                password=instance.password,
                keepalive=60,
                identifier=client_id  # aiomqtt uses 'identifier' parameter
            )

            # Connect to broker
            await instance._client.__aenter__()
            instance._connected = True

            # Subscribe to all possible response topics for this user
            response_topic_pattern = f"user/{instance.user_no}/+/manage/get-configs-result"
            await instance._client.subscribe(response_topic_pattern)
            logger.info(f"Subscribed to response pattern: {response_topic_pattern}")

            # Start background response listener
            instance._response_listener_task = asyncio.create_task(instance._listen_responses())

            logger.info("✅ MQTT persistent connection established successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize MQTT connection: {e}")
            instance._connected = False
            raise MQTTConnectionError(f"Failed to initialize MQTT: {str(e)}")

    @classmethod
    async def close(cls) -> None:
        """Close persistent MQTT connection"""
        instance = cls()
        if not instance._connected:
            return

        try:
            # Cancel response listener
            if instance._response_listener_task:
                instance._response_listener_task.cancel()
                try:
                    await instance._response_listener_task
                except asyncio.CancelledError:
                    pass

            # Cancel all pending requests
            for session_id, future in instance._pending_requests.items():
                if not future.done():
                    future.set_exception(MQTTConnectionError("MQTT connection closing"))
            instance._pending_requests.clear()

            # Close MQTT connection
            if instance._client:
                await instance._client.__aexit__(None, None, None)
                instance._client = None

            instance._connected = False
            logger.info("MQTT persistent connection closed")

        except Exception as e:
            logger.error(f"Error closing MQTT connection: {e}")

    async def _listen_responses(self) -> None:
        """Background task to listen for MQTT responses"""
        if not self._client:
            return

        try:
            async for message in self._client.messages:
                try:
                    # Extract session ID from topic
                    # Topic format: user/{user_no}/{session_id}/manage/get-configs-result
                    topic_parts = str(message.topic).split('/')
                    if len(topic_parts) >= 3:
                        session_id = topic_parts[2]

                        # Check if we have a pending request for this session
                        if session_id in self._pending_requests:
                            future = self._pending_requests.pop(session_id)

                            if not future.done():
                                try:
                                    # Parse response - handle different payload types
                                    payload = message.payload
                                    if isinstance(payload, bytes):
                                        payload_str = payload.decode('utf-8')
                                    elif isinstance(payload, str):
                                        payload_str = payload
                                    else:
                                        payload_str = str(payload)

                                    response_data = json.loads(payload_str)

                                    # Fix typo in field name if exists
                                    if 'timestap' in response_data and 'timestamp' not in response_data:
                                        response_data['timestamp'] = response_data['timestap']

                                    # Create response object
                                    device_response = DeviceRealtimeResponse(**response_data)
                                    future.set_result(device_response)

                                    logger.info(f"Response received for session: {session_id}")

                                except Exception as e:
                                    logger.error(f"Error parsing response for session {session_id}: {e}")
                                    future.set_exception(InvalidResponseError(f"Invalid response format: {str(e)}"))
                        else:
                            logger.warning(f"Received response for unknown session: {session_id}")

                except Exception as e:
                    logger.error(f"Error processing MQTT message: {e}")

        except asyncio.CancelledError:
            logger.info("MQTT response listener cancelled")
        except Exception as e:
            logger.error(f"MQTT response listener error: {e}")
            # Try to reconnect
            await self._handle_connection_error()

    async def _handle_connection_error(self) -> None:
        """Handle connection errors and attempt reconnection"""
        logger.warning("MQTT connection lost, attempting to reconnect...")
        self._connected = False

        # Cancel all pending requests
        for session_id, future in self._pending_requests.items():
            if not future.done():
                future.set_exception(MQTTConnectionError("MQTT connection lost"))
        self._pending_requests.clear()

        # Attempt reconnection
        try:
            await asyncio.sleep(5)  # Wait before reconnecting
            await self.initialize()
        except Exception as e:
            logger.error(f"Failed to reconnect MQTT: {e}")

    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        return str(uuid.uuid4()).replace('-', '')[:16]

    async def get_device_realtime_info(self, device_imei: str) -> Optional[DeviceRealtimeResponse]:
        """
        Get device realtime info using persistent connection

        Args:
            device_imei: IMEI of the device

        Returns:
            DeviceRealtimeResponse or None if error

        Raises:
            DeviceTimeoutError: Device not responding
            MQTTConnectionError: MQTT connection error
            InvalidResponseError: Invalid response format
        """
        if not self._connected or not self._client:
            raise MQTTConnectionError("MQTT not connected. Call initialize() first.")

        session_id = self.generate_session_id()
        request_topic = f"device/{device_imei}/manage/get-configs"

        request_payload = {
            "sessionId": session_id,
            "typeCode": "user",
            "typeNo": self.user_no,
            "version": "1.0.0",
            "timestamp": int(time.time()),
            "data": {
                "structs": "DEVICE_INFO,SYSTEM_INFO,USER_INFO,BATTERY_INFO,GPS_INFO"
            }
        }

        try:
            # Create future for this request
            future: asyncio.Future[DeviceRealtimeResponse] = asyncio.Future()
            self._pending_requests[session_id] = future

            # Publish request
            await self._client.publish(request_topic, json.dumps(request_payload))
            logger.info(f"Published request to: {request_topic} with session: {session_id}")

            # Wait for response with timeout
            try:
                result = await asyncio.wait_for(future, timeout=self.timeout)
                return result
            except asyncio.TimeoutError:
                # Clean up pending request
                self._pending_requests.pop(session_id, None)
                logger.warning(f"Timeout waiting for device {device_imei} response")
                raise DeviceTimeoutError(f"Device {device_imei} không phản hồi trong {self.timeout} giây")

        except Exception as e:
            # Clean up pending request
            self._pending_requests.pop(session_id, None)
            if isinstance(e, (DeviceTimeoutError, MQTTConnectionError, InvalidResponseError)):
                raise
            logger.error(f"Unexpected error: {e}")
            raise MQTTConnectionError(f"Lỗi không xác định: {str(e)}")

    async def get_multiple_devices_realtime_info(self, device_imeis: List[str], max_concurrent: int = 5) -> Dict[str, Optional[DeviceRealtimeResponse]]:
        """
        Get realtime info for multiple devices concurrently using persistent connection

        Args:
            device_imeis: List of device IMEIs
            max_concurrent: Maximum concurrent requests

        Returns:
            Dict mapping IMEI -> DeviceRealtimeResponse (or None if error)
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_single_device(imei: str) -> tuple[str, Optional[DeviceRealtimeResponse]]:
            async with semaphore:
                try:
                    result = await self.get_device_realtime_info(imei)
                    return imei, result
                except Exception as e:
                    logger.warning(f"Failed to get realtime info for device {imei}: {e}")
                    return imei, None

        # Create tasks for all devices
        tasks = [fetch_single_device(imei) for imei in device_imeis]

        # Run concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            realtime_data = {}
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed: {result}")
                    continue

                if isinstance(result, tuple) and len(result) == 2:
                    imei, data = result
                    realtime_data[imei] = data

            return realtime_data

        except Exception as e:
            logger.error(f"Error in batch realtime fetch: {e}")
            return {imei: None for imei in device_imeis}


# Global service instance
mqtt_persistent_service = MQTTPersistentService()

async def get_mqtt_persistent_service() -> MQTTPersistentService:
    return mqtt_persistent_service
