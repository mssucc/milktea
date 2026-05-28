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


def schedule_startup_catchup_scan():
    """
    Schedule an immediate one-time catch-up scan on backend startup.

    This compensates for missed periodic scans while the backend was offline.
    Sessions with reviews > 7 days old that have new messages will be regenerated.
    """
    from .config import scheduler

    job_id = f"startup_catchup_{int(datetime.utcnow().timestamp())}"

    job = scheduler.add_job(
        execute_scheduled_scan,
        'date',
        run_date=datetime.utcnow(),
        id=job_id,
        misfire_grace_time=600,
        coalesce=True,
        replace_existing=True
    )

    logger.info(f"Scheduled startup catch-up scan (job {job_id})")
    return job_id


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


# Batch review generation — processes sessions sequentially to avoid resource contention
# Module-level tracking to prevent duplicate batches and support incremental display
_active_batches: Dict[str, dict] = {}  # key -> {session_ids, completed_sessions, started_at, config}


def is_batch_active(batch_key: str) -> bool:
    """Check if a batch is currently running for the given key."""
    if batch_key not in _active_batches:
        return False
    # Clean up stale entries (crashed jobs, orphaned tracking)
    started = _active_batches[batch_key].get("started_at")
    if started and (datetime.utcnow() - started).total_seconds() > 1800:  # 30 min timeout
        logger.warning(f"Removing stale batch entry for '{batch_key}' (started {started})")
        del _active_batches[batch_key]
        return False
    return True


def get_batch_progress(batch_key: str) -> dict:
    """Get progress of an active batch. Returns empty dict if no batch active."""
    batch = _active_batches.get(batch_key)
    if not batch:
        return {}
    return {
        "total": len(batch["session_ids"]),
        "completed": len(batch["completed_sessions"]),
        "session_ids": batch["session_ids"],
        "completed_sessions": batch["completed_sessions"],
        "started_at": batch["started_at"].isoformat()
    }


def execute_batch_review_generation_task(session_ids: list, config: Dict[str, Any] = None, batch_key: str = None):
    """
    Process multiple sessions sequentially in a single APScheduler job.

    Avoids the resource contention (DB locks + LLM API calls) that occurs
    when N individual jobs run concurrently via schedule_review_generation().

    Updates _active_batches tracking as each session completes, enabling
    incremental display of results before the full batch finishes.
    """
    import asyncio

    if config is None:
        config = {}

    logger.info(f"Starting batch review generation for {len(session_ids)} sessions (key={batch_key})")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        completed = 0
        failed = 0
        for i, session_id in enumerate(session_ids):
            logger.info(f"Batch [{i+1}/{len(session_ids)}] processing session {session_id}")
            try:
                loop.run_until_complete(generate_review_background(session_id, config))
                completed += 1
                # Mark as completed in tracker so review endpoint can see it immediately
                if batch_key and batch_key in _active_batches:
                    _active_batches[batch_key]["completed_sessions"].append(session_id)
            except Exception as e:
                logger.error(f"Batch [{i+1}/{len(session_ids)}] failed for {session_id}: {e}")
                failed += 1

        logger.info(f"Batch review generation completed: {completed} ok, {failed} failed")
        return {"completed": completed, "failed": failed}
    finally:
        if 'loop' in locals():
            loop.close()
        # Clean up tracking
        if batch_key and batch_key in _active_batches:
            del _active_batches[batch_key]


def schedule_batch_review_generation(session_ids: list, config: Dict[str, Any] = None,
                                     batch_key: str = None):
    """
    Schedule a single batched job that processes sessions sequentially.

    If batch_key is provided and a batch with the same key is already active,
    returns None instead of creating a duplicate.
    """
    from .config import scheduler

    if config is None:
        config = {}

    # Deduplicate: if a batch with this key is already running, don't create another
    if batch_key and is_batch_active(batch_key):
        logger.info(f"Batch '{batch_key}' already active, skipping duplicate")
        return None

    # Filter out sessions that are already in an active batch
    active_session_ids = set()
    for key, batch in _active_batches.items():
        active_session_ids.update(batch["session_ids"])
    filtered_ids = [sid for sid in session_ids if sid not in active_session_ids]
    if not filtered_ids:
        logger.info("All candidate sessions are already being processed, skipping")
        return None

    # Register tracking entry
    if batch_key:
        _active_batches[batch_key] = {
            "session_ids": filtered_ids,
            "completed_sessions": [],
            "started_at": datetime.utcnow(),
            "config": config
        }

    job_id = f"review_batch_{len(filtered_ids)}_{int(datetime.utcnow().timestamp())}"

    job = scheduler.add_job(
        execute_batch_review_generation_task,
        'date',
        run_date=datetime.utcnow(),
        args=[filtered_ids, config, batch_key],
        id=job_id,
        misfire_grace_time=600,
        coalesce=True
    )

    logger.info(f"Scheduled batch review generation job {job_id} for {len(filtered_ids)} sessions (key={batch_key})")
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