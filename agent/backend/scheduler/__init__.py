"""Scheduler module for background review generation tasks"""

from .config import scheduler, init_scheduler, shutdown_scheduler
from .job_store import SQLAlchemyJobStore
from .task_executor import (
    execute_review_generation_task,
    execute_scheduled_scan,
    schedule_review_generation,
    schedule_periodic_scans,
    schedule_startup_catchup_scan,
    schedule_retry_task,
    execute_integrated_review_generation_task,
    schedule_integrated_review_generation,
    execute_batch_review_generation_task,
    schedule_batch_review_generation,
    is_batch_active,
    get_batch_progress
)

__all__ = [
    'scheduler',
    'init_scheduler',
    'shutdown_scheduler',
    'SQLAlchemyJobStore',
    'execute_review_generation_task',
    'execute_scheduled_scan',
    'schedule_review_generation',
    'schedule_periodic_scans',
    'schedule_startup_catchup_scan',
    'schedule_retry_task',
    'execute_integrated_review_generation_task',
    'schedule_integrated_review_generation',
    'execute_batch_review_generation_task',
    'schedule_batch_review_generation',
    'is_batch_active',
    'get_batch_progress'
]