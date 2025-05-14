import asyncio
from datetime import datetime, timezone, timedelta
from repository.event_pool import EventPoolRepository
from common.logger import get_logger


async def rotation_event_pool_job():
    logger = get_logger(f"[GLOBALS] [rotation_event_pool_job]")

    while True:
        logger.info("Started rotation event pool")

        try:
            delete_result = await EventPoolRepository.delete_many({
                "status": {"$in": ["success", "skip"]},
                "created_at": {"$lte": datetime.now(timezone.utc) - timedelta(hours=36)}
            })

            if deleted_count := delete_result.raw_result['n']:
                logger.info(f"Deleted {deleted_count} events from event pool")

        except Exception as err:
            logger.error(f"Message: {err}")

        logger.info("Finished rotation event pool")

        await asyncio.sleep(3600)
