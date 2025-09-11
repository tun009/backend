import logging
from datetime import datetime
from sqlalchemy import update
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models import JourneySession
from app.db.session import AsyncSessionLocal
from app.api.routes.journey_sessions_routes import vietnam_tz

logger = logging.getLogger(__name__)

async def end_expired_journeys():
    logger.info("Running scheduler to end expired journeys...")
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(vietnam_tz)
            stmt = (
                update(JourneySession)
                .where(JourneySession.status == 'active', JourneySession.end_time < now)
                .values(status='completed')
            )
            result = await db.execute(stmt)
            await db.commit()
            if result.rowcount > 0:
                logger.info(f"Successfully ended {result.rowcount} expired journeys.")
        except Exception as e:
            logger.error(f"Error ending expired journeys: {e}")
            await db.rollback()

scheduler = AsyncIOScheduler(timezone=str(vietnam_tz))
scheduler.add_job(
    end_expired_journeys,
    'interval',
    minutes=5,
    id='end_expired_journeys_job',
    replace_existing=True
)