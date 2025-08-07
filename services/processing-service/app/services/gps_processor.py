import asyncio
import json
import logging
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import aiomqtt
from sqlalchemy import select, and_

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import JourneySession, DeviceLog, Device, Vehicle

logger = logging.getLogger(__name__)

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
        self._client: Optional[aiomqtt.Client] = None
        self._connected = False
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._response_listener_task: Optional[asyncio.Task] = None
        
        # Processing state
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize MQTT connection (một lần duy nhất)"""
        if self._connected:
            logger.info("MQTT already connected")
            return
            
        try:
            logger.info(f"🔌 Connecting to MQTT broker: {self.broker_host}:{self.broker_port}")
            
            # Create MQTT client
            client_id = f"obu_processor_{self.user_no}_{int(time.time())}"
            self._client = aiomqtt.Client(
                hostname=self.broker_host,
                port=self.broker_port,
                username=self.username,
                password=self.password,
                keepalive=60,
                identifier=client_id
            )
            
            # Connect
            await self._client.__aenter__()
            self._connected = True
            
            # Subscribe to response topics
            response_topic = f"user/{self.user_no}/+/manage/get-configs-result"
            await self._client.subscribe(response_topic)
            logger.info(f"📡 Subscribed to: {response_topic}")
            
            # Start response listener
            self._response_listener_task = asyncio.create_task(self._listen_responses())
            
            logger.info("✅ MQTT connection established successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect MQTT: {e}")
            self._connected = False
            raise
    
    async def start_processing(self):
        """Start GPS processing loop"""
        if self._running:
            logger.warning("GPS processing already running")
            return
            
        self._running = True
        self._scan_task = asyncio.create_task(self._processing_loop())
        logger.info(f"🚀 GPS processing started (scan every {self.scan_interval}s)")
    
    async def stop(self):
        """Stop GPS processing"""
        self._running = False
        
        # Stop scan task
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        
        # Stop response listener
        if self._response_listener_task:
            self._response_listener_task.cancel()
            try:
                await self._response_listener_task
            except asyncio.CancelledError:
                pass
        
        # Close MQTT connection
        if self._client and self._connected:
            try:
                await self._client.__aexit__(None, None, None)
                self._connected = False
                logger.info("🔌 MQTT connection closed")
            except Exception as e:
                logger.error(f"Error closing MQTT: {e}")
        
        logger.info("🛑 GPS processing stopped")
    
    async def _processing_loop(self):
        """Main processing loop - quét mỗi 15-20s"""
        while self._running:
            try:
                logger.info("🔍 Scanning for active journey sessions...")
                
                # 1. Query active journey sessions
                active_sessions = await self._get_active_journey_sessions()
                
                if not active_sessions:
                    logger.info("📭 No active journey sessions found")
                else:
                    logger.info(f"📋 Found {len(active_sessions)} active sessions")
                    
                    # 2. Process each session
                    await self._process_sessions(active_sessions)
                
                # 3. Wait for next scan
                await asyncio.sleep(self.scan_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in processing loop: {e}")
                await asyncio.sleep(self.scan_interval)
    
    async def _get_active_journey_sessions(self) -> List[Dict]:
        """Query active journey sessions với device info"""
        async with AsyncSessionLocal() as session:
            try:
                now = datetime.now(timezone.utc)
                
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
        """Listen for MQTT responses (background task)"""
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

                        # Check if we have pending request
                        if session_id in self._pending_requests:
                            future = self._pending_requests.pop(session_id)

                            if not future.done():
                                try:
                                    # Parse MQTT response
                                    payload = message.payload
                                    if isinstance(payload, bytes):
                                        payload_str = payload.decode('utf-8')
                                    elif isinstance(payload, str):
                                        payload_str = payload
                                    else:
                                        payload_str = str(payload)

                                    response_data = json.loads(payload_str)

                                    # Fix typo in field name if exists (same as API service)
                                    if 'timestap' in response_data and 'timestamp' not in response_data:
                                        response_data['timestamp'] = response_data['timestap']

                                    future.set_result(response_data)
                                    logger.info(f"Response received for session: {session_id}")

                                except Exception as e:
                                    logger.error(f"Error parsing response for session {session_id}: {e}")
                                    future.set_exception(Exception(f"Invalid response format: {str(e)}"))
                        else:
                            logger.warning(f"Received response for unknown session: {session_id}")

                except Exception as e:
                    logger.error(f"❌ Error processing MQTT response: {e}")

        except asyncio.CancelledError:
            logger.info("MQTT response listener cancelled")
        except Exception as e:
            logger.error(f"❌ Error in MQTT response listener: {e}")

    async def _save_device_log(self, journey_session_id: int, device_imei: str, mqtt_response: Dict):
        """Save GPS data to device_logs table"""
        async with AsyncSessionLocal() as session:
            try:
                # Extract only the data part from MQTT response
                device_data = mqtt_response.get('data', {})

                # Create device log entry with only the data part
                device_log = DeviceLog(
                    journey_session_id=journey_session_id,
                    device_imei=device_imei,
                    mqtt_response=device_data,  # Chỉ lưu phần data, bỏ metadata
                    collected_at=datetime.now(timezone.utc)
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
