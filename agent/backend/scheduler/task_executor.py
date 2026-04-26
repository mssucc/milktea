"""Task executor wrapper for scheduler integration"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any

from backend.tasks.review_generation import (
    generate_review_background,
    scan_and_generate_reviews,
    execute_review_generation
)

# Import node-based review generator for integrated review tasks
from backend.utils.node_based_review_generator import node_based_review_generator

logger = logging.getLogger(__name__)


def execute_review_generation_task(session_id: str, config: Dict[str, Any] = None):
    """
    Wrapper function for APScheduler to execute review generation tasks.

    Note: This function is synchronous to work with APScheduler's ThreadPoolExecutor.
    It runs the async task in a separate asyncio event loop.
    """
    import asyncio

    logger.info(f"Executing review generation task for session {session_id}")
    logger.debug(f"Task config: { {k: v if k != 'api_key' else ('present' if v else 'absent') for k, v in (config or {}).items()} }")

    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the async task
        logger.debug(f"Starting async task execution for session {session_id}")
        result = loop.run_until_complete(generate_review_background(session_id, config))
        logger.debug(f"Async task completed for session {session_id}")

        logger.info(f"Review generation task completed for session {session_id}")
        return result
    except Exception as e:
        logger.error(f"Review generation task failed for session {session_id}: {e}")
        raise
    finally:
        # Clean up the event loop
        if 'loop' in locals():
            loop.close()


def execute_scheduled_scan():
    """
    Execute the scheduled scan for review generation.

    This is the function that gets called by APScheduler every 12 hours.
    """
    import asyncio

    logger.info("Executing scheduled review generation scan")

    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the async task
        result = loop.run_until_complete(scan_and_generate_reviews())

        logger.info(f"Scheduled scan completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Scheduled scan failed: {e}")
        raise
    finally:
        # Clean up the event loop
        if 'loop' in locals():
            loop.close()


def schedule_review_generation(session_id: str, config: Dict[str, Any] = None):
    """
    Schedule an immediate review generation task.

    This is used for on-demand generation when user requests review for an uncached session.
    """
    from .config import scheduler

    if config is None:
        config = {}

    job_id = f"review_gen_{session_id}_{int(datetime.utcnow().timestamp())}"

    # Schedule the job to run immediately
    job = scheduler.add_job(
        execute_review_generation_task,
        'date',
        run_date=datetime.utcnow(),
        args=[session_id, config],
        id=job_id,
        misfire_grace_time=300,  # 5 minutes grace period
        coalesce=True
    )

    logger.info(f"Scheduled review generation job {job_id} for session {session_id}")
    return job_id


def schedule_periodic_scans():
    """
    Schedule periodic review generation scans.

    This should be called during application startup to set up the scheduled scans.
    """
    from .config import scheduler

    # Remove any existing scan jobs (cleanup)
    jobs = scheduler.get_jobs()
    for job in jobs:
        if job.name == "scheduled_review_scan":
            scheduler.remove_job(job.id)

    # Schedule scans every 12 hours (at 08:00 and 20:00 UTC)
    # Using cron syntax: minute hour day month day_of_week
    job = scheduler.add_job(
        execute_scheduled_scan,
        'cron',
        hour='8,20',  # 8 AM and 8 PM UTC
        minute='0',
        id='scheduled_review_scan',
        name='Scheduled Review Generation Scan',
        misfire_grace_time=3600,  # 1 hour grace period for missed scans
        coalesce=True,
        replace_existing=True
    )

    logger.info(f"Scheduled periodic review scans: next run at {job.next_run_time}")
    return job


def schedule_retry_task(session_id: str, delay_minutes: int = 5):
    """
    Schedule a retry task for failed review generation.

    Implements exponential backoff strategy: 1min, 5min, 30min, 24h
    """
    from .config import scheduler

    job_id = f"review_retry_{session_id}_{int(datetime.utcnow().timestamp())}"
    run_date = datetime.utcnow() + asyncio.timeout(delay_minutes * 60)

    job = scheduler.add_job(
        execute_review_generation_task,
        'date',
        run_date=run_date,
        args=[session_id, {}],
        id=job_id,
        misfire_grace_time=300,
        coalesce=True
    )

    logger.info(f"Scheduled retry job {job_id} for session {session_id} in {delay_minutes} minutes")
    return job_id


# Integrated review task functions

def execute_integrated_review_generation_task(days: int, config: Dict[str, Any] = None):
    """
    Execute node-based integrated review generation and store in cache.

    Args:
        days: Time range in days (7-30)
        config: Optional configuration with api_key, base_url, model
    """
    import asyncio

    if config is None:
        config = {}

    logger.info(f"Executing integrated review generation task for {days} days")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            _generate_integrated_review_async(days, config)
        )

        logger.info(f"Integrated review generation task completed for {days} days")
        return result
    except Exception as e:
        logger.error(f"Integrated review generation task failed for {days} days: {e}")
        raise
    finally:
        if 'loop' in locals():
            loop.close()


async def _generate_integrated_review_async(days: int, config: Dict[str, Any]):
    """
    Async function to generate integrated review and store in cache.
    """
    from backend.database.session import SessionLocal
    from backend.database import crud
    from datetime import datetime, timedelta

    logger.info(f"Generating node-based integrated review for {days} days")

    db = SessionLocal()
    try:
        api_key = config.get("api_key")
        base_url = config.get("base_url")
        model = config.get("model")

        # Generate node-based review data
        node_data = await asyncio.to_thread(
            node_based_review_generator.generate_node_based_review,
            days=days,
            limit=20,
            api_key=api_key,
            base_url=base_url,
            model=model
        )

        # Store in cache
        expires_at = datetime.utcnow() + timedelta(hours=24)
        generation_config = {
            "generation_type": "node_based",
            "days": days,
            "entity_count": node_data.get("entity_count", 0),
            "generated_at": node_data.get("generated_at"),
            "api_key_provided": api_key is not None,
            "base_url": base_url,
            "model": model
        }

        crud.create_or_update_integrated_review_data(
            db=db,
            time_range_days=days,
            review_groups=node_data["review_groups"],
            aggregated_summary=node_data["aggregated_summary"],
            next_review_date=datetime.fromisoformat(
                node_data["next_review_date"].replace('Z', '+00:00')
            ),
            generation_config=generation_config,
            expires_at=expires_at,
            generation_status="completed"
        )

        logger.info(f"Successfully stored integrated review for {days} days in cache")
        return node_data

    except Exception as e:
        logger.error(f"Error in integrated review generation: {e}")
        raise
    finally:
        db.close()


def schedule_integrated_review_generation(days: int, config: Dict[str, Any] = None):
    """
    Schedule an immediate integrated review generation task.

    Returns:
        Job ID string
    """
    from .config import scheduler

    if config is None:
        config = {}

    job_id = f"integrated_review_gen_{days}d_{int(datetime.utcnow().timestamp())}"

    job = scheduler.add_job(
        execute_integrated_review_generation_task,
        'date',
        run_date=datetime.utcnow(),
        args=[days, config],
        id=job_id,
        misfire_grace_time=600,  # 10 minutes grace period
        coalesce=True
    )

    logger.info(f"Scheduled integrated review generation job {job_id} for {days} days")
    return job_id