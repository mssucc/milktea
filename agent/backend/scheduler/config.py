"""APScheduler configuration and initialization"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED, EVENT_JOB_EXECUTED
from datetime import datetime
from typing import Dict, Any

from backend.database.session import engine

logger = logging.getLogger(__name__)

# Default job store URL (SQLite)
DEFAULT_JOBSTORE_URL = "sqlite:///./scheduler.db"

# Configure scheduler
jobstores = {
    'default': SQLAlchemyJobStore(url=DEFAULT_JOBSTORE_URL, engine=engine)
}

executors = {
    'default': ThreadPoolExecutor(20)  # Max 20 concurrent jobs
}

job_defaults = {
    'coalesce': True,  # Combine multiple pending executions
    'max_instances': 1,  # Only one instance of a job can run at a time
    'misfire_grace_time': 300  # 5 minutes grace period for missed jobs
}

# Create scheduler instance
scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone='UTC'
)


def job_error_listener(event):
    """Handle job execution errors"""
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    else:
        logger.error(f"Job {event.job_id} failed with unknown error")


def job_missed_listener(event):
    """Handle missed jobs"""
    logger.warning(f"Job {event.job_id} missed at {event.scheduled_run_time}")


def job_executed_listener(event):
    """Handle successful job execution"""
    logger.debug(f"Job {event.job_id} executed successfully")


def init_scheduler():
    """Initialize the scheduler and add event listeners"""
    # Add event listeners
    scheduler.add_listener(job_error_listener, EVENT_JOB_ERROR)
    scheduler.add_listener(job_missed_listener, EVENT_JOB_MISSED)
    scheduler.add_listener(job_executed_listener, EVENT_JOB_EXECUTED)

    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler initialized and started")

    # Log scheduled jobs
    jobs = scheduler.get_jobs()
    logger.info(f"Scheduler has {len(jobs)} scheduled jobs")
    for job in jobs:
        logger.info(f"  - Job {job.id}: {job.name}, next run: {job.next_run_time}")


def shutdown_scheduler():
    """Shutdown the scheduler gracefully"""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown completed")