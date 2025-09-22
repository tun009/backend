import asyncio
import json
import logging
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import aiomqtt
from sqlalchemy import select, and_

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import JourneySession, DeviceLog, Device, Vehicle

logger = logging.getLogger(__name__)

# Múi giờ Việt Nam (UTC+7)
vietnam_tz = timezone(timedelta(hours=7))

class GPSProcessor:
    """
    GPS Processor Service - Đơn giản và hiệu quả
    Quét journey sessions active và lấy GPS data qua MQTT
    """
    
    def __init__(self):
        # MQTT settings
        self.broker_host = settings.MQTT_BROKER_HOST
        self.broker_port = settings.MQTT_BROKER_PORT
        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD
        self.user_no = settings.MQTT_USER_NO
        self.timeout = settings.MQTT_TIMEOUT
        
        # Processing settings
        self.scan_interval = settings.SCAN_INTERVAL
        self.max_concurrent = settings.MAX_CONCURRENT_DEVICES
        
        # MQTT client (singleton pattern)
        # Retry settings
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY

        # MQTT client (singleton pattern)
        self._client: Optional[aiomqtt.Client] = None
        self._connected = False
        self._reconnecting = False # Flag to prevent multiple reconnect loops
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._connection_handler_task: Optional[asyncio.Task] = None
        
        # Processing state
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Starts the connection manager task."""
        if self._connection_handler_task:
            logger.warning("Connection handler already running.")
            return
        self._connection_handler_task = asyncio.create_task(self._manage_connection())

    async def _manage_connection(self):
        """Manages the MQTT connection and handles reconnection."""
        while self._running:
            try:
                logger.info("Attempting to establish MQTT connection...")
                await self._connect_mqtt()
                logger.info("MQTT connection is live. Starting message listener.")
                await self._listen_responses() # This runs until disconnection

            except aiomqtt.MqttError as e:
                logger.error(f"MQTT connection error: {e}. Starting reconnection logic.")
            except asyncio.CancelledError:
                logger.info("Connection manager cancelled.")
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred in connection manager: {e}")

            # --- Reconnection Logic ---
            if not self._running:
                break

            self._connected = False
            logger.info("Starting reconnection process...")

            for attempt in range(1, self.max_retries + 1):
                if not self._running:
                    break

                delay = self.retry_delay * (2 ** (attempt - 1)) # Exponential backoff
                logger.info(f"Reconnection attempt {attempt}/{self.max_retries} in {delay} seconds...")
                await asyncio.sleep(delay)

                try:
                    await self._connect_mqtt()
                    logger.info("Reconnection successful!")
                    break # Exit retry loop on success
                except Exception as e:
                    logger.error(f"Reconnection attempt {attempt} failed: {e}")
                    if attempt == self.max_retries:
                        logger.critical("All reconnection attempts failed. Service will remain disconnected.")
                        # Here you could add logic to stop the service or notify someone
                        return # Stop the manager

    async def _connect_mqtt(self):
        """Handles the actual MQTT connection and subscription logic."""
        # Clean up previous client if it exists
        if self._client and self._connected:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                pass # Ignore errors during cleanup
        self._connected = False

        client_id = f"obu_processor_{self.user_no}_{int(time.time())}"
        self._client = aiomqtt.Client(
            hostname=self.broker_host,
            port=self.broker_port,
            username=self.username,
            password=self.password,
            keepalive=60,
            identifier=client_id
        )

        await self._client.__aenter__()
        self._connected = True

        response_topic = f"user/{self.user_no}/+/manage/get-configs-result"
        await self._client.subscribe(response_topic)
        logger.info(f"🔌 MQTT Connected and subscribed to {response_topic}")
    
    async def start_processing(self):
        """Start GPS processing loop"""
        if self._running:
            logger.warning("GPS processing already running")
            return

        self._running = True
        await self.initialize() # Start connection manager
        self._scan_task = asyncio.create_task(self._processing_loop())
        logger.info(f"🚀 GPS processing started (scan every {self.scan_interval}s)")

    async def stop(self):
        """Stop GPS processing and clean up resources."""
        self._running = False

        # Stop all tasks
        tasks = []
        if self._scan_task:
            self._scan_task.cancel()
            tasks.append(self._scan_task)
        if self._connection_handler_task:
            self._connection_handler_task.cancel()
            tasks.append(self._connection_handler_task)

        # Wait for tasks to finish cancellation
        await asyncio.gather(*tasks, return_exceptions=True)

        # Cleanly close MQTT connection
        if self._client and self._connected:
            try:
                await self._client.__aexit__(None, None, None)
                self._connected = False
                logger.info("🔌 MQTT connection cleanly closed")
            except Exception as e:
                logger.error(f"Error during MQTT client exit: {e}")

        logger.info("🛑 GPS processing stopped")
    
    async def _processing_loop(self):
        """Main processing loop. Waits for connection before starting."""
        while not self._connected and self._running:
            logger.info("Processing loop is waiting for MQTT connection...")
            await asyncio.sleep(3)

        while self._running:
            try:
                if not self._connected:
                    logger.warning("MQTT disconnected. Pausing scan.")
                    await asyncio.sleep(self.scan_interval)
                    continue

                logger.info("🔍 Scanning for active journey sessions...")
                active_sessions = await self._get_active_journey_sessions()

                if not active_sessions:
                    logger.info("📭 No active journey sessions found")
                else:
                    logger.info(f"📋 Found {len(active_sessions)} active sessions")
                    await self._process_sessions(active_sessions)

                await asyncio.sleep(self.scan_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Unhandled error in processing loop: {e}")
                await asyncio.sleep(self.scan_interval) # Prevent rapid failure loops
    
    async def _get_active_journey_sessions(self) -> List[Dict]:
        """Query active journey sessions với device info"""
        async with AsyncSessionLocal() as session:
            try:
                now = datetime.now(vietnam_tz)
                
                # Query active sessions với device và vehicle info
                stmt = (
                    select(
                        JourneySession.id,
                        JourneySession.vehicle_id,
                        JourneySession.start_time,
                        JourneySession.end_time,
                        Device.imei.label('device_imei'),
                        Vehicle.plate_number
                    )
                    .join(Vehicle, JourneySession.vehicle_id == Vehicle.id)
                    .join(Device, Vehicle.id == Device.vehicle_id)
                    .where(
                        and_(
                            JourneySession.status == 'active',
                            JourneySession.start_time <= now,
                            JourneySession.end_time >= now
                        )
                    )
                )
                
                result = await session.execute(stmt)
                sessions = []
                for row in result:
                    sessions.append({
                        'id': row.id,
                        'vehicle_id': row.vehicle_id,
                        'device_imei': row.device_imei,
                        'plate_number': row.plate_number,
                        'start_time': row.start_time,
                        'end_time': row.end_time
                    })
                
                return sessions
                
            except Exception as e:
                logger.error(f"❌ Error querying active sessions: {e}")
                return []
    
    async def _process_sessions(self, sessions: List[Dict]):
        """Process multiple sessions concurrently"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_single_session(session: Dict):
            async with semaphore:
                try:
                    await self._collect_gps_data(session)
                except Exception as e:
                    logger.error(f"❌ Failed to process session {session['id']}: {e}")
        
        # Create tasks for all sessions
        tasks = [process_single_session(session) for session in sessions]
        
        # Run concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _collect_gps_data(self, session: Dict):
        """Collect GPS data cho một session"""
        device_imei = session['device_imei']
        session_id = session['id']
        plate_number = session['plate_number']

        logger.info(f"📍 Collecting GPS for session {session_id} - Device {device_imei} ({plate_number})")

        try:
            # 1. Request GPS data via MQTT
            gps_response = await self._request_gps_data(device_imei)

            if gps_response:
                # 2. Save to device_logs
                await self._save_device_log(session_id, device_imei, gps_response)
                logger.info(f"✅ GPS data saved for session {session_id} - {device_imei}")
            else:
                logger.warning(f"⚠️ No GPS response for session {session_id} - {device_imei}")

        except Exception as e:
            logger.error(f"❌ Error collecting GPS for session {session_id}: {e}")

    async def _request_gps_data(self, device_imei: str) -> Optional[Dict]:
        """Request GPS data via MQTT - using same format as API service"""
        if not self._connected or not self._client:
            logger.warning("MQTT not connected")
            return None

        try:
            # Generate unique session ID
            session_id = str(uuid.uuid4()).replace('-', '')[:16]

            # Prepare MQTT request - using same format as API service
            request_topic = f"device/{device_imei}/manage/get-configs"
            request_payload = {
                "sessionId": session_id,
                "typeCode": "user",
                "typeNo": self.user_no,
                "version": "1.0.0",
                "timestamp": int(time.time()),
                "data": {
                    "structs": "SYSTEM_INFO,BATTERY_INFO,GPS_INFO"
                }
            }

            # Create future for response
            future: asyncio.Future = asyncio.Future()
            self._pending_requests[session_id] = future

            # Send MQTT request
            await self._client.publish(request_topic, json.dumps(request_payload))
            logger.debug(f"📤 MQTT request sent to {device_imei} (session: {session_id})")

            # Wait for response
            try:
                result = await asyncio.wait_for(future, timeout=self.timeout)
                logger.debug(f"📥 MQTT response received from {device_imei}")
                return result
            except asyncio.TimeoutError:
                self._pending_requests.pop(session_id, None)
                logger.warning(f"⏰ Timeout waiting for {device_imei} response")
                return None

        except Exception as e:
            logger.error(f"❌ Error requesting GPS from {device_imei}: {e}")
            return None



    async def _listen_responses(self):
        """Listen for MQTT responses and forwards them to the correct future."""
        if not self._client:
            return

        async for message in self._client.messages:
            try:
                topic_parts = str(message.topic).split('/')
                if len(topic_parts) >= 3:
                    session_id = topic_parts[2]
                    if session_id in self._pending_requests:
                        future = self._pending_requests.pop(session_id)
                        if not future.done():
                            try:
                                payload = message.payload
                                if isinstance(payload, bytes):
                                    payload_str = payload.decode('utf-8')
                                else:
                                    payload_str = str(payload)

                                response_data = json.loads(payload_str)

                                if 'timestap' in response_data and 'timestamp' not in response_data:
                                    response_data['timestamp'] = response_data['timestap']

                                future.set_result(response_data)
                            except Exception as e:
                                logger.error(f"Failed to parse response for session {session_id}: {e}")
                                if not future.done():
                                    future.set_exception(e)
            except Exception as e:
                logger.error(f"Critical error in MQTT message listener: {e}")

    async def _save_device_log(self, journey_session_id: int, device_imei: str, mqtt_response: Dict):
        """Save GPS data to device_logs table"""
        async with AsyncSessionLocal() as session:
            try:
                device_data = mqtt_response.get('data', {})

                device_log = DeviceLog(
                    journey_session_id=journey_session_id,
                    device_imei=device_imei,
                    mqtt_response=device_data,
                    collected_at=datetime.now(vietnam_tz)
                )

                session.add(device_log)
                await session.commit()

                logger.debug(f"💾 Device log saved: session={journey_session_id}, imei={device_imei}")

                # Log GPS info if available
                if 'GPS_INFO' in device_data:
                    gps_info = device_data['GPS_INFO']
                    lat = gps_info.get('latitude_str', 'N/A')
                    lng = gps_info.get('longitude_str', 'N/A')
                    speed = gps_info.get('speed', 0)
                    logger.info(f"📍 GPS: {lat}, {lng}, Speed: {speed} km/h")

            except Exception as e:
                logger.error(f"❌ Error saving device log: {e}")
                await session.rollback()

    def is_running(self) -> bool:
        """Check if processing is running"""
        return self._running

    def is_connected(self) -> bool:
        """Check if MQTT is connected"""
        return self._connected
