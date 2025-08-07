#!/usr/bin/env python3
"""
Simple test for Processing Service
"""

import asyncio
import sys
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import JourneySession

async def test_simple():
    """Simple test"""
    print("🧪 Simple Processing Service Test")
    print(f"Database URL: {settings.DATABASE_URL[:50]}...")
    print(f"MQTT Broker: {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
    print(f"Scan Interval: {settings.SCAN_INTERVAL}s")
    
    try:
        # Test database connection
        print("\n1. Testing database connection...")
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            print("✅ Database connection OK")
        
        # Test query journey sessions
        print("\n2. Testing journey sessions query...")
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            stmt = select(JourneySession).limit(5)
            result = await session.execute(stmt)
            sessions = result.scalars().all()
            print(f"📋 Found {len(sessions)} journey sessions in database")
            
            for session_obj in sessions:
                print(f"   - Session {session_obj.id}: status={session_obj.status}")
        
        print("\n✅ Simple test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple())
