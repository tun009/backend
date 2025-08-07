#!/usr/bin/env python3
"""
Test script for GPS Processor
"""

import asyncio
import logging
from app.services.gps_processor import GPSProcessor
from app.db.session import test_database_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_processor():
    """Test GPS Processor functionality"""
    logger.info("🧪 Testing GPS Processor...")
    
    processor = GPSProcessor()
    
    try:
        # Test database connection
        logger.info("1. Testing database connection...")
        db_ok = await test_database_connection()
        if not db_ok:
            logger.error("❌ Database connection failed")
            return
        
        # Test MQTT initialization
        logger.info("2. Testing MQTT initialization...")
        await processor.initialize()
        logger.info(f"✅ MQTT connected: {processor.is_connected()}")
        
        # Test query active sessions
        logger.info("3. Testing query active sessions...")
        sessions = await processor._get_active_journey_sessions()
        logger.info(f"📋 Found {len(sessions)} active sessions")
        
        for session in sessions:
            logger.info(f"   - Session {session['id']}: {session['device_imei']} ({session['plate_number']})")
        
        # Test single GPS collection (if sessions exist)
        if sessions:
            logger.info("4. Testing GPS collection...")
            session = sessions[0]
            await processor._collect_gps_data(session)
        else:
            logger.info("4. No active sessions to test GPS collection")
        
        # Cleanup
        await processor.stop()
        logger.info("✅ Test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        await processor.stop()

if __name__ == "__main__":
    asyncio.run(test_processor())
