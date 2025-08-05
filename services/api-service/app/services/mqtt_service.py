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
    """Device không phản hồi trong thời gian timeout"""
    pass


class MQTTConnectionError(Exception):
    """Lỗi kết nối MQTT broker"""
    pass


class InvalidResponseError(Exception):
    """Response từ device không hợp lệ"""
    pass


class MQTTRealtimeService:
    """Service để giao tiếp MQTT với thiết bị OBU"""
    
    def __init__(self):
        self.broker_host = settings.MQTT_BROKER_HOST
        self.broker_port = settings.MQTT_BROKER_PORT
        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD
        self.user_no = settings.MQTT_USER_NO
        self.timeout = settings.MQTT_TIMEOUT
    
    def generate_session_id(self) -> str:
        """Tạo session ID duy nhất"""
        return str(uuid.uuid4()).replace('-', '')[:16]
    
    async def get_device_realtime_info(self, device_imei: str) -> Optional[DeviceRealtimeResponse]:
        """
        Lấy thông tin real-time của thiết bị qua MQTT
        
        Args:
            device_imei: IMEI của thiết bị
            
        Returns:
            DeviceRealtimeResponse hoặc None nếu có lỗi
            
        Raises:
            DeviceTimeoutError: Thiết bị không phản hồi
            MQTTConnectionError: Lỗi kết nối MQTT
            InvalidResponseError: Response không hợp lệ
        """
        session_id = self.generate_session_id()
        request_topic = f"device/{device_imei}/manage/get-configs"
        response_topic = f"user/{self.user_no}/{session_id}/manage/get-configs-result"
        
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
            logger.info(f"Connecting to MQTT broker: {self.broker_host}:{self.broker_port}")
            
            async with aiomqtt.Client(
                hostname=self.broker_host,
                port=self.broker_port,
                username=self.username,
                password=self.password
            ) as client:
                
                # Subscribe to response topic
                await client.subscribe(response_topic)
                logger.info(f"Subscribed to: {response_topic}")
                
                # Publish request
                await client.publish(request_topic, json.dumps(request_payload))
                logger.info(f"Published request to: {request_topic} with session: {session_id}")
                
                # Wait for response with timeout
                async def wait_for_response():
                    async for message in client.messages:
                        if message.topic.matches(response_topic):
                            try:
                                response_data = json.loads(message.payload.decode())
                                logger.info(f"Received response for session: {session_id}")

                                # Debug: Log response structure
                                logger.info(f"Response data keys: {list(response_data.keys())}")

                                # Fix typo in field name if exists
                                if 'timestap' in response_data and 'timestamp' not in response_data:
                                    response_data['timestamp'] = response_data['timestap']

                                return DeviceRealtimeResponse(**response_data)
                            except Exception as e:
                                logger.error(f"Error parsing response: {e}")
                                logger.error(f"Response data keys: {list(response_data.keys()) if 'response_data' in locals() else 'No data'}")
                                raise InvalidResponseError(f"Invalid response format: {str(e)}")
                
                try:
                    return await asyncio.wait_for(wait_for_response(), timeout=self.timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for device {device_imei} response")
                    raise DeviceTimeoutError(f"Device {device_imei} không phản hồi trong {self.timeout} giây")
                    
        except aiomqtt.MqttError as e:
            logger.error(f"MQTT connection error: {e}")
            raise MQTTConnectionError(f"Không thể kết nối MQTT broker: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise MQTTConnectionError(f"Lỗi không xác định: {str(e)}")

    async def get_multiple_devices_realtime_info(self, device_imeis: List[str], max_concurrent: int = 5) -> Dict[str, Optional[DeviceRealtimeResponse]]:
        """
        Lấy thông tin real-time của nhiều thiết bị đồng thời

        Args:
            device_imeis: List IMEI của các thiết bị
            max_concurrent: Số lượng request đồng thời tối đa

        Returns:
            Dict mapping IMEI -> DeviceRealtimeResponse (hoặc None nếu lỗi)
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

        # Tạo tasks cho tất cả devices
        tasks = [fetch_single_device(imei) for imei in device_imeis]

        # Chạy đồng thời với timeout
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Xử lý kết quả
            realtime_data = {}
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Task failed: {result}")
                    continue

                imei, data = result
                realtime_data[imei] = data

            return realtime_data

        except Exception as e:
            logger.error(f"Error in batch realtime fetch: {e}")
            return {imei: None for imei in device_imeis}


# Global service instance
mqtt_realtime_service = MQTTRealtimeService()


async def get_mqtt_realtime_service() -> MQTTRealtimeService:
    """Dependency để lấy MQTT service instance"""
    return mqtt_realtime_service
