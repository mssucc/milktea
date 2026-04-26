"""Task utility functions"""

import logging
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.database import crud
from backend.database.session import SessionLocal

logger = logging.getLogger(__name__)


@contextmanager
def session_lock(session_id: str, lock_timeout: int = 300):
    """
    Acquire a lock for a session to prevent concurrent review generation.

    This implements a simple database-based lock using the ReviewData table.
    In production, you might want to use a more sophisticated distributed lock.
    """
    db = SessionLocal()
    try:
        # Get or create review data record
        review_data = crud.get_review_data(db, session_id)
        now = time.time()

        if review_data and review_data.generation_status == "generating":
            # Check if lock has expired
            if review_data.last_attempt_at:
                lock_age = now - review_data.last_attempt_at.timestamp()
                if lock_age < lock_timeout:
                    # Lock is still valid
                    logger.warning(f"Session {session_id} is already being processed (lock age: {lock_age:.1f}s)")
                    raise RuntimeError(f"Session {session_id} is already being processed")

        # Acquire lock by updating status
        crud.update_review_generation_status(
            db=db,
            session_id=session_id,
            status="generating"
        )

        db.commit()
        logger.debug(f"Acquired lock for session {session_id}")

        try:
            yield
        finally:
            # Release lock (if not already released)
            try:
                release_db = SessionLocal()
                current_data = crud.get_review_data(release_db, session_id)
                if current_data and current_data.generation_status == "generating":
                    # Only release if still in generating status
                    crud.update_review_generation_status(
                        release_db,
                        session_id,
                        "completed"  # Or "pending" if not completed?
                    )
                release_db.commit()
                release_db.close()
                logger.debug(f"Released lock for session {session_id}")
            except Exception as e:
                logger.error(f"Error releasing lock for session {session_id}: {e}")

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


def calculate_task_priority(session_id: str) -> int:
    """
    Calculate priority for a review generation task.

    Higher priority numbers = higher priority.
    Factors:
    - User waiting for review (immediate request)
    - Recent activity
    - Previous generation failures
    """
    db = SessionLocal()
    try:
        priority = 0

        # Check if user is waiting (has recent review request)
        # This could be tracked in a separate table, for now use simple heuristic
        review_data = crud.get_review_data(db, session_id)
        if review_data:
            if review_data.generation_status == "failed":
                priority += 10  # Higher priority for retry
            if review_data.review_count and review_data.review_count > 0:
                priority += 5  # Higher priority for sessions with review history

        # Check message count (more messages = higher priority)
        message_count = crud.get_message_count(db, session_id)
        if message_count > 20:
            priority += 15
        elif message_count > 10:
            priority += 10
        elif message_count > 5:
            priority += 5

        # Check recent activity
        recent_messages = crud.get_recent_messages_by_session(db, session_id, days=1, limit=1)
        if recent_messages:
            priority += 20  # High priority for sessions with recent activity

        logger.debug(f"Calculated priority {priority} for session {session_id}")
        return max(0, min(priority, 100))  # Clamp to 0-100 range

    finally:
        db.close()


def should_retry_generation(
    session_id: str,
    error_message: str,
    max_retries: int = 3
) -> bool:
    """
    Determine if a failed generation should be retried.
    """
    db = SessionLocal()
    try:
        review_data = crud.get_review_data(db, session_id)
        if not review_data:
            return True  # First attempt

        # Count previous failures
        task_failures = (
            db.query(crud.ReviewGenerationTask)
            .filter(
                crud.ReviewGenerationTask.session_id == session_id,
                crud.ReviewGenerationTask.status == "failed"
            )
            .count()
        )

        if task_failures >= max_retries:
            logger.info(f"Max retries ({max_retries}) reached for session {session_id}")
            return False

        # Don't retry certain errors
        non_retryable_errors = [
            "Invalid API key",
            "Model not found",
            "Authentication failed"
        ]

        for error in non_retryable_errors:
            if error in error_message:
                logger.info(f"Non-retryable error for session {session_id}: {error}")
                return False

        return True

    finally:
        db.close()


def get_retry_delay(failure_count: int) -> int:
    """
    Calculate retry delay using exponential backoff.

    Strategy: 1min, 5min, 30min, 24h
    """
    delays = [60, 300, 1800, 86400]  # seconds
    if failure_count < len(delays):
        return delays[failure_count]
    return delays[-1]  # Use max delay for subsequent failures