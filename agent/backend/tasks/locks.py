"""Distributed lock implementation for task coordination"""

import logging
import time
import threading
from contextlib import contextmanager
from typing import Dict, Optional
from sqlalchemy.orm import Session

from backend.database import crud
from backend.database.session import SessionLocal

logger = logging.getLogger(__name__)


class DistributedLock:
    """Simple distributed lock using database"""

    def __init__(self, resource_id: str, timeout: int = 300):
        self.resource_id = resource_id
        self.timeout = timeout  # seconds
        self._local_lock = threading.Lock()
        self._acquired = False

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire the lock.

        Args:
            blocking: If True, block until lock is acquired
            timeout: Maximum time to wait for lock (seconds)

        Returns:
            True if lock acquired, False otherwise
        """
        start_time = time.time()
        while True:
            with self._local_lock:
                if self._try_acquire():
                    self._acquired = True
                    logger.debug(f"Acquired lock for resource {self.resource_id}")
                    return True

            if not blocking:
                return False

            if timeout is not None and (time.time() - start_time) >= timeout:
                return False

            # Wait before retry
            time.sleep(0.1)

    def _try_acquire(self) -> bool:
        """Try to acquire the lock (database operation)"""
        db = SessionLocal()
        try:
            # Implementation depends on your database schema
            # For simplicity, we'll use a separate locking table or reuse ReviewData
            # This is a placeholder implementation
            return True  # TODO: Implement actual distributed lock
        finally:
            db.close()

    def release(self):
        """Release the lock"""
        with self._local_lock:
            if self._acquired:
                self._release_db()
                self._acquired = False
                logger.debug(f"Released lock for resource {self.resource_id}")

    def _release_db(self):
        """Release the lock in database"""
        db = SessionLocal()
        try:
            # TODO: Implement actual lock release
            pass
        finally:
            db.close()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


@contextmanager
def session_lock(session_id: str, timeout: int = 300):
    """
    Context manager for session-level locking.

    This prevents concurrent review generation for the same session.
    """
    lock = DistributedLock(f"session_{session_id}", timeout)
    try:
        if lock.acquire(blocking=True, timeout=timeout):
            yield
        else:
            raise TimeoutError(f"Could not acquire lock for session {session_id} within {timeout} seconds")
    finally:
        lock.release()


@contextmanager
def global_lock(lock_name: str, timeout: int = 60):
    """
    Context manager for global-level locking.

    This prevents concurrent execution of global operations (like scheduled scans).
    """
    lock = DistributedLock(f"global_{lock_name}", timeout)
    try:
        if lock.acquire(blocking=True, timeout=timeout):
            yield
        else:
            raise TimeoutError(f"Could not acquire global lock {lock_name} within {timeout} seconds")
    finally:
        lock.release()