from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from sqlalchemy.exc import OperationalError
from datetime import datetime, timedelta
import uuid
import time
from typing import List, Optional, Dict, Any

from .model import Session as ChatSession, Message, ReviewData, ReviewGenerationTask

# Session CRUD operations

def create_session(db: Session, session_id: Optional[str] = None) -> ChatSession:
    """Create a new chat session"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"create_session called: session_id={session_id}")
    if session_id is None:
        session_id = str(uuid.uuid4())
        logger.info(f"Generated new session_id: {session_id}")

    db_session = ChatSession(id=session_id, created_at=datetime.utcnow())
    logger.info(f"Created ChatSession object")

    # Retry logic for SQLite locking issues
    max_retries = 5
    for attempt in range(max_retries):
        try:
            db.add(db_session)
            db.commit()
            db.refresh(db_session)
            return db_session
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.1  # Exponential backoff
                time.sleep(wait_time)
                # Rollback and retry
                db.rollback()
                continue
            else:
                raise
        except Exception:
            db.rollback()
            raise

def get_session(db: Session, session_id: str) -> Optional[ChatSession]:
    """Get a session by ID"""
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()

def get_all_sessions(db: Session, limit: int = 100) -> List[ChatSession]:
    """Get all sessions, ordered by creation time"""
    return db.query(ChatSession).order_by(desc(ChatSession.created_at)).limit(limit).all()

def delete_session(db: Session, session_id: str) -> bool:
    """Delete a session and all its messages"""
    session = get_session(db, session_id)
    if session:
        # Retry logic for SQLite locking issues
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Delete associated messages first (cascade would handle this if configured)
                db.query(Message).filter(Message.session_id == session_id).delete()
                db.delete(session)
                db.commit()
                return True
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 0.1  # Exponential backoff
                    time.sleep(wait_time)
                    # Rollback and retry
                    db.rollback()
                    continue
                else:
                    raise
            except Exception:
                db.rollback()
                raise
    return False

# Message CRUD operations

def create_message(
    db: Session,
    session_id: str,
    role: str,
    content: str
) -> Message:
    """Create a new message in a session"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"create_message called: session_id={session_id}, role={role}, content_length={len(content)}")
    # Ensure session exists
    session = get_session(db, session_id)
    if not session:
        logger.info(f"Session {session_id} does not exist, creating new session")
        session = create_session(db, session_id)

    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        timestamp=datetime.utcnow()
    )

    # Retry logic for SQLite locking issues
    max_retries = 5
    for attempt in range(max_retries):
        try:
            db.add(message)
            db.commit()
            db.refresh(message)
            return message
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.1  # Exponential backoff
                time.sleep(wait_time)
                # Rollback and retry
                db.rollback()
                continue
            else:
                raise
        except Exception:
            db.rollback()
            raise

def get_messages_by_session(
    db: Session,
    session_id: str,
    limit: int = 100
) -> List[Message]:
    """Get all messages for a session, ordered by timestamp"""
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.timestamp)
        .limit(limit)
        .all()
    )

def get_message_count(db: Session, session_id: str) -> int:
    """Get the number of messages in a session"""
    return db.query(Message).filter(Message.session_id == session_id).count()

def get_last_message(db: Session, session_id: str) -> Optional[Message]:
    """Get the most recent message in a session"""
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(desc(Message.timestamp))
        .first()
    )

def get_latest_conversation_rounds(db: Session, session_id: str, rounds: int = 1) -> List[Message]:
    """Get the latest N rounds of conversation (each round: user + assistant messages)
    Returns messages in chronological order (oldest first) for proper conversation flow.
    """
    # Each round consists of 2 messages (user + assistant)
    limit = rounds * 2
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(desc(Message.timestamp))
        .limit(limit)
        .all()
    )
    # Reverse to get chronological order (oldest first)
    messages.reverse()
    return messages

def delete_message(db: Session, message_id: int) -> bool:
    """Delete a message by ID"""
    message = db.query(Message).filter(Message.id == message_id).first()
    if message:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                db.delete(message)
                db.commit()
                return True
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 0.1  # Exponential backoff
                    time.sleep(wait_time)
                    # Rollback and retry
                    db.rollback()
                    continue
                else:
                    raise
            except Exception:
                db.rollback()
                raise
    return False

def clear_session_messages(db: Session, session_id: str) -> int:
    """Delete all messages in a session, return count deleted"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            count = db.query(Message).filter(Message.session_id == session_id).delete()
            db.commit()
            return count
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.1  # Exponential backoff
                time.sleep(wait_time)
                # Rollback and retry
                db.rollback()
                continue
            else:
                raise
        except Exception:
            db.rollback()
            raise

def update_message_content(db: Session, message_id: int, new_content: str) -> Optional[Message]:
    """Update the content of an existing message"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if message:
                message.content = new_content
                db.commit()
                db.refresh(message)
                return message
            return None
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.1  # Exponential backoff
                time.sleep(wait_time)
                db.rollback()
                continue
            else:
                raise
        except Exception:
            db.rollback()
            raise


def get_recent_messages_all_sessions(db: Session, days: int = 3, limit: int = 100) -> List[Message]:
    """Get recent messages from all sessions within the last N days"""
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(Message)
        .filter(Message.timestamp >= cutoff_time)
        .order_by(desc(Message.timestamp))
        .limit(limit)
        .all()
    )


def get_recent_messages_by_session(db: Session, session_id: str, days: int = 3, limit: int = 100) -> List[Message]:
    """Get recent messages from a specific session within the last N days"""
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(Message)
        .filter(Message.session_id == session_id, Message.timestamp >= cutoff_time)
        .order_by(Message.timestamp)
        .limit(limit)
        .all()
    )


def get_recent_sessions(db: Session, days: int = 3, limit: int = 50) -> List[ChatSession]:
    """Get sessions that have had activity (messages) within the last N days"""
    cutoff_time = datetime.utcnow() - timedelta(days=days)

    # Find sessions with recent messages
    recent_message_query = (
        db.query(Message.session_id)
        .filter(Message.timestamp >= cutoff_time)
        .distinct()
        .subquery()
    )

    return (
        db.query(ChatSession)
        .join(recent_message_query, ChatSession.id == recent_message_query.c.session_id)
        .order_by(desc(ChatSession.created_at))
        .limit(limit)
        .all()
    )


def get_session_ids_with_recent_activity(db: Session, days: int = 3) -> List[str]:
    """Get list of session IDs that have had activity within the last N days"""
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    result = (
        db.query(Message.session_id)
        .filter(Message.timestamp >= cutoff_time)
        .distinct()
        .all()
    )
    return [row[0] for row in result]


# ReviewData CRUD operations

def create_or_update_review_data(
    db: Session,
    session_id: str,
    review_groups: List[Dict[str, Any]],
    aggregated_summary: str,
    next_review_date: datetime,
    generation_config: Dict[str, Any],
    expires_at: Optional[datetime] = None,
    generation_status: str = "completed"
) -> ReviewData:
    """Create or update structured review data for a session"""
    import logging
    logger = logging.getLogger(__name__)

    # Check if review data already exists
    existing = db.query(ReviewData).filter(ReviewData.session_id == session_id).first()
    now = datetime.utcnow()

    if expires_at is None:
        expires_at = now + timedelta(hours=24)  # Default 24-hour expiration

    # Calculate statistics for logging
    total_groups = len(review_groups)
    total_cards = 0
    total_questions = 0
    for group in review_groups:
        total_cards += len(group.get("knowledge_cards", []))
        total_questions += len(group.get("quiz_questions", []))

    if existing:
        # Update existing record with new structure
        existing.review_groups = review_groups
        existing.aggregated_summary = aggregated_summary
        existing.next_review_date = next_review_date
        existing.generation_config = generation_config
        existing.generation_status = generation_status
        existing.generated_at = now
        existing.expires_at = expires_at
        existing.error_message = None
        logger.info(f"Updated review data for session {session_id}")
    else:
        # Create new record with new structure
        existing = ReviewData(
            session_id=session_id,
            review_groups=review_groups,
            aggregated_summary=aggregated_summary,
            next_review_date=next_review_date,
            generation_config=generation_config,
            generation_status=generation_status,
            generated_at=now,
            expires_at=expires_at,
            last_attempt_at=now,
            learned_cards=[],
            completed_quizzes=[],
            review_count=0
        )
        db.add(existing)
        logger.info(f"Created structured review data for session {session_id}")

    logger.info(f"Review data statistics: {total_groups} groups, {total_cards} cards, {total_questions} questions")

    # Retry logic for SQLite locking issues
    max_retries = 5
    for attempt in range(max_retries):
        try:
            db.commit()
            db.refresh(existing)
            return existing
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.1
                time.sleep(wait_time)
                db.rollback()
                continue
            else:
                raise
        except Exception:
            db.rollback()
            raise

def get_review_data(db: Session, session_id: str) -> Optional[ReviewData]:
    """Get review data for a session"""
    return db.query(ReviewData).filter(ReviewData.session_id == session_id).first()

def get_valid_review_data(db: Session, session_id: str) -> Optional[ReviewData]:
    """Get valid (non-expired and completed) review data for a session"""
    now = datetime.utcnow()
    review_data = db.query(ReviewData).filter(
        ReviewData.session_id == session_id,
        ReviewData.generation_status == "completed",
        ReviewData.expires_at > now
    ).first()
    return review_data

def update_review_generation_status(
    db: Session,
    session_id: str,
    status: str,
    error_message: Optional[str] = None
) -> Optional[ReviewData]:
    """Update generation status for review data"""
    review_data = get_review_data(db, session_id)
    if review_data:
        review_data.generation_status = status
        review_data.last_attempt_at = datetime.utcnow()
        if error_message:
            review_data.error_message = error_message
        if status == "completed":
            review_data.generated_at = datetime.utcnow()
        elif status == "failed" and error_message:
            review_data.error_message = error_message[:500]  # Limit error message length

        max_retries = 5
        for attempt in range(max_retries):
            try:
                db.commit()
                db.refresh(review_data)
                return review_data
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 0.1
                    time.sleep(wait_time)
                    db.rollback()
                    continue
                else:
                    raise
            except Exception:
                db.rollback()
                raise
    return None

def update_review_data_json(
    db: Session,
    session_id: str,
    field_name: str,
    field_value: Any
) -> Optional[ReviewData]:
    """Update a JSON field in review data"""
    import logging
    logger = logging.getLogger(__name__)

    review_data = get_review_data(db, session_id)
    if not review_data:
        logger.warning(f"No review data found for session {session_id}")
        return None

    # Update the specific field
    if hasattr(review_data, field_name):
        setattr(review_data, field_name, field_value)
        review_data.last_attempt_at = datetime.utcnow()  # Update timestamp

        max_retries = 5
        for attempt in range(max_retries):
            try:
                db.commit()
                db.refresh(review_data)
                logger.info(f"Updated {field_name} for session {session_id}")
                return review_data
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 0.1
                    time.sleep(wait_time)
                    db.rollback()
                    continue
                else:
                    raise
            except Exception:
                db.rollback()
                raise
    else:
        logger.error(f"Field {field_name} does not exist in ReviewData")

    return None


def mark_review_question_completed(
    db: Session,
    session_id: str,
    question_id: int
) -> Optional[ReviewData]:
    """Mark a review question as completed (legacy function)"""
    review_data = get_review_data(db, session_id)
    if review_data:
        completed = review_data.completed_quizzes or []
        if question_id not in completed:
            completed.append(question_id)
            review_data.completed_quizzes = completed
            review_data.last_reviewed_at = datetime.utcnow()
            review_data.review_count = (review_data.review_count or 0) + 1

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    db.commit()
                    db.refresh(review_data)
                    return review_data
                except OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 0.1
                        time.sleep(wait_time)
                        db.rollback()
                        continue
                    else:
                        raise
                except Exception:
                    db.rollback()
                    raise
    return None

def mark_review_recommendation_completed(
    db: Session,
    session_id: str,
    recommendation_id: int
) -> Optional[ReviewData]:
    """Mark a review recommendation as completed"""
    review_data = get_review_data(db, session_id)
    if review_data:
        completed = review_data.recommendations_completed or []
        if recommendation_id not in completed:
            completed.append(recommendation_id)
            review_data.recommendations_completed = completed
            review_data.last_reviewed_at = datetime.utcnow()
            review_data.review_count = (review_data.review_count or 0) + 1

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    db.commit()
                    db.refresh(review_data)
                    return review_data
                except OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 0.1
                        time.sleep(wait_time)
                        db.rollback()
                        continue
                    else:
                        raise
                except Exception:
                    db.rollback()
                    raise
    return None

def get_expired_review_data(db: Session, limit: int = 50) -> List[ReviewData]:
    """Get expired review data that needs regeneration"""
    now = datetime.utcnow()
    return (
        db.query(ReviewData)
        .filter(
            ReviewData.expires_at <= now,
            ReviewData.generation_status == "completed"
        )
        .order_by(ReviewData.expires_at)
        .limit(limit)
        .all()
    )

def get_failed_review_data(db: Session, limit: int = 20) -> List[ReviewData]:
    """Get review data that failed generation"""
    return (
        db.query(ReviewData)
        .filter(ReviewData.generation_status == "failed")
        .order_by(ReviewData.last_attempt_at)
        .limit(limit)
        .all()
    )

def get_review_data_in_progress(db: Session, timeout_minutes: int = 30) -> List[ReviewData]:
    """Get review data that's been in 'generating' status for too long"""
    cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    return (
        db.query(ReviewData)
        .filter(
            ReviewData.generation_status == "generating",
            ReviewData.last_attempt_at <= cutoff_time
        )
        .order_by(ReviewData.last_attempt_at)
        .limit(20)
        .all()
    )

def delete_review_data(db: Session, session_id: str) -> bool:
    """Delete review data for a session"""
    review_data = get_review_data(db, session_id)
    if review_data:
        max_retries = 5
        for attempt in range(max_retries):
            try:
                db.delete(review_data)
                db.commit()
                return True
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 0.1
                    time.sleep(wait_time)
                    db.rollback()
                    continue
                else:
                    raise
            except Exception:
                db.rollback()
                raise
    return False

def get_sessions_needing_review_generation(
    db: Session,
    session_ids: List[str],
    exclude_statuses: List[str] = None
) -> List[str]:
    """Filter session IDs that need review generation"""
    if exclude_statuses is None:
        exclude_statuses = ["generating", "completed"]

    now = datetime.utcnow()
    # Get sessions with no review data or with expired/failed status
    existing_reviews = (
        db.query(ReviewData)
        .filter(ReviewData.session_id.in_(session_ids))
        .all()
    )

    existing_map = {rd.session_id: rd for rd in existing_reviews}
    needs_generation = []

    for session_id in session_ids:
        if session_id not in existing_map:
            needs_generation.append(session_id)
        else:
            review_data = existing_map[session_id]
            if (review_data.generation_status in ["failed", "pending"] or
                (review_data.generation_status == "completed" and review_data.expires_at <= now)):
                needs_generation.append(session_id)

    return needs_generation

# ReviewGenerationTask CRUD operations

def create_review_generation_task(
    db: Session,
    session_id: str,
    task_type: str = "initial",
    priority: int = 0,
    review_data_id: Optional[int] = None
) -> ReviewGenerationTask:
    """Create a new review generation task"""
    task = ReviewGenerationTask(
        session_id=session_id,
        task_type=task_type,
        status="pending",
        priority=priority,
        created_at=datetime.utcnow(),
        review_data_id=review_data_id
    )

    max_retries = 5
    for attempt in range(max_retries):
        try:
            db.add(task)
            db.commit()
            db.refresh(task)
            return task
        except OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.1
                time.sleep(wait_time)
                db.rollback()
                continue
            else:
                raise
        except Exception:
            db.rollback()
            raise

def get_pending_tasks(db: Session, limit: int = 20) -> List[ReviewGenerationTask]:
    """Get pending review generation tasks"""
    return (
        db.query(ReviewGenerationTask)
        .filter(ReviewGenerationTask.status == "pending")
        .order_by(desc(ReviewGenerationTask.priority), ReviewGenerationTask.created_at)
        .limit(limit)
        .all()
    )

def update_task_status(
    db: Session,
    task_id: int,
    status: str,
    error_message: Optional[str] = None
) -> Optional[ReviewGenerationTask]:
    """Update task status"""
    task = db.query(ReviewGenerationTask).filter(ReviewGenerationTask.id == task_id).first()
    if task:
        task.status = status
        now = datetime.utcnow()
        if status == "running":
            task.started_at = now
        elif status in ["completed", "failed"]:
            task.completed_at = now
            if error_message:
                task.error_message = error_message

        max_retries = 5
        for attempt in range(max_retries):
            try:
                db.commit()
                db.refresh(task)
                return task
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 0.1
                    time.sleep(wait_time)
                    db.rollback()
                    continue
                else:
                    raise
            except Exception:
                db.rollback()
                raise
    return None

def get_tasks_by_session(db: Session, session_id: str, limit: int = 10) -> List[ReviewGenerationTask]:
    """Get tasks for a specific session"""
    return (
        db.query(ReviewGenerationTask)
        .filter(ReviewGenerationTask.session_id == session_id)
        .order_by(desc(ReviewGenerationTask.created_at))
        .limit(limit)
        .all()
    )


# Multi-session review data functions

def get_recent_valid_reviews(db: Session, limit: int = 10, days: int = 7) -> List[ReviewData]:
    """Get recent valid review data across all sessions (not expired, completed)

    Args:
        db: Database session
        limit: Maximum number of reviews to return
        days: Look back this many days for review generation time

    Returns:
        List of valid ReviewData objects sorted by recency
    """
    now = datetime.utcnow()
    cutoff_time = now - timedelta(days=days)

    return (
        db.query(ReviewData)
        .filter(
            ReviewData.generation_status == "completed",
            ReviewData.expires_at > now,
            ReviewData.generated_at >= cutoff_time
        )
        .order_by(desc(ReviewData.generated_at))
        .limit(limit)
        .all()
    )


def get_aggregated_review_data(db: Session, session_ids: Optional[List[str]] = None, limit: int = 10, days: int = 30) -> Dict[str, Any]:
    """Get aggregated review data from multiple sessions using new structured format

    Implements knowledge-depth-first + recency-assisted aggregation strategy:
    1. Knowledge depth first: High-frequency topics get more detailed coverage
    2. Recency assisted: Recent reviews have higher weight (two-stage decay: 0-7 days, 7-30 days)

    Args:
        db: Database session
        session_ids: Optional list of session IDs to include. If None, uses recent valid reviews.
        limit: Maximum number of reviews to aggregate
        days: Look back this many days for review generation time (default 30)

    Returns:
        Dictionary with aggregated review data in new structured format
    """
    # Get review data for specified sessions or recent valid reviews
    if session_ids:
        review_data_list = (
            db.query(ReviewData)
            .filter(
                ReviewData.session_id.in_(session_ids),
                ReviewData.generation_status == "completed",
                ReviewData.expires_at > datetime.utcnow()
            )
            .order_by(desc(ReviewData.generated_at))
            .limit(limit)
            .all()
        )
    else:
        review_data_list = get_recent_valid_reviews(db, limit=limit, days=days)

    if not review_data_list:
        return {
            "aggregated_summary": "近期会话中没有复习数据。",
            "review_groups": [],
            "next_review_date": datetime.utcnow().isoformat(),
            "session_count": 0,
            "total_groups": 0,
            "total_knowledge_cards": 0,
            "total_quiz_questions": 0,
            "sessions": []
        }

    session_info = []
    # Structure to track groups by title (knowledge depth first)
    # key: group title, value: dict with group info, cards, questions, and metadata
    groups_by_title: Dict[str, Dict[str, Any]] = {}

    # Track recency weights for each review (newer = higher weight) with two-stage decay
    now = datetime.utcnow()

    def calculate_two_stage_weight(days_old: int) -> float:
        """Calculate recency weight using two-stage decay: 0-7 days and 7-30 days

        Stage 1 (0-7 days): weight decays from 1.0 to 0.4 linearly
        Stage 2 (7-30 days): weight decays from 0.4 to 0.1 linearly
        Beyond 30 days: weight stays at 0.1 (minimum)
        """
        if days_old <= 7:
            # Stage 1: 1.0 -> 0.4 over 7 days
            return max(0.4, 1.0 - (days_old / 7) * 0.6)
        elif days_old <= 30:
            # Stage 2: 0.4 -> 0.1 over 23 days (7-30)
            stage2_days = days_old - 7
            return max(0.1, 0.4 - (stage2_days / 23) * 0.3)
        else:
            # Beyond 30 days: minimum weight
            return 0.1

    for review_data in review_data_list:
        # Calculate recency weight using two-stage decay
        days_old = (now - review_data.generated_at).days if review_data.generated_at else 30
        recency_weight = calculate_two_stage_weight(days_old)

        # Record session info
        session_info.append({
            "session_id": review_data.session_id,
            "generated_at": review_data.generated_at.isoformat() if review_data.generated_at else None,
            "recency_weight": recency_weight,
            "message_count": review_data.generation_config.get("message_count", 0) if review_data.generation_config else 0
        })

        # Skip if no review groups
        if not review_data.review_groups:
            continue

        # Process each review group
        for group in review_data.review_groups:
            if not isinstance(group, dict):
                continue

            # Use title as primary key for grouping (new structured format)
            title = group.get("title", "")
            if not title:
                # Fallback to id if title is missing
                title = group.get("id", "未命名分组")

            group_id = group.get("id", title.lower().replace(" ", "_"))
            description = group.get("description", f"关于{title}的复习内容")

            # Initialize group if not exists
            if title not in groups_by_title:
                groups_by_title[title] = {
                    "id": group_id,
                    "title": title,
                    "description": description,
                    "frequency": 0,  # How many times this group appears
                    "total_recency_weight": 0.0,  # Sum of recency weights
                    "knowledge_cards": [],  # List of unique cards with source info
                    "quiz_questions": [],  # List of unique questions with source info
                    "source_sessions": set()  # Sessions that contributed to this group
                }

            current_group = groups_by_title[title]
            current_group["frequency"] += 1
            current_group["total_recency_weight"] += recency_weight
            current_group["source_sessions"].add(review_data.session_id)

            # Merge knowledge cards (deduplicate by content)
            knowledge_cards = group.get("knowledge_cards", [])
            if knowledge_cards:
                for card in knowledge_cards:
                    if not isinstance(card, dict):
                        continue

                    card_id = card.get("id", "")
                    card_content = card.get("content", "")
                    if not card_content or len(card_content.strip()) < 5:
                        continue

                    # Deduplicate by content (first 100 chars)
                    content_key = card_content[:100].strip()
                    existing = False
                    for existing_card in current_group["knowledge_cards"]:
                        if existing_card.get("content_key", "").startswith(content_key[:80]):
                            existing = True
                            # Update recency weight for existing card
                            existing_card["total_weight"] += recency_weight
                            break

                    if not existing:
                        # Generate unique ID if missing
                        if not card_id:
                            card_id = f"{group_id}_card_{len(current_group['knowledge_cards'])}"

                        current_group["knowledge_cards"].append({
                            "id": card_id,
                            "content": card_content.strip(),
                            "content_key": content_key,
                            "source_weight": recency_weight,
                            "total_weight": recency_weight,
                            "is_learned": False,
                            "source_sessions": [review_data.session_id]
                        })

            # Merge quiz questions (deduplicate by question text)
            quiz_questions = group.get("quiz_questions", [])
            if quiz_questions:
                for question in quiz_questions:
                    if not isinstance(question, dict):
                        continue

                    question_id = question.get("id", "")
                    question_text = question.get("question", "")
                    if not question_text or len(question_text.strip()) < 5:
                        continue

                    # Deduplicate by question text (first 100 chars)
                    question_key = question_text[:100].strip()
                    existing = False
                    for existing_q in current_group["quiz_questions"]:
                        if existing_q.get("question_key", "").startswith(question_key[:80]):
                            existing = True
                            # Update recency weight for existing question
                            existing_q["total_weight"] += recency_weight
                            break

                    if not existing:
                        # Generate unique ID if missing
                        if not question_id:
                            question_id = f"{group_id}_quiz_{len(current_group['quiz_questions'])}"

                        # Validate options
                        options = question.get("options", [])
                        if not isinstance(options, list) or len(options) < 4:
                            options = ["选项A", "选项B", "选项C", "选项D"]

                        correct_answer = question.get("correct_answer", 0)
                        if not isinstance(correct_answer, int) or correct_answer < 0 or correct_answer >= len(options):
                            correct_answer = 0

                        explanation = question.get("explanation", "")
                        if not explanation:
                            explanation = f"正确答案是选项{['A','B','C','D'][correct_answer]}"

                        difficulty = question.get("difficulty", "medium")
                        if difficulty not in ["easy", "medium", "hard"]:
                            difficulty = "medium"

                        current_group["quiz_questions"].append({
                            "id": question_id,
                            "question": question_text.strip(),
                            "question_key": question_key,
                            "options": options,
                            "correct_answer": correct_answer,
                            "explanation": explanation.strip(),
                            "difficulty": difficulty,
                            "source_weight": recency_weight,
                            "total_weight": recency_weight,
                            "is_completed": False,
                            "source_sessions": [review_data.session_id]
                        })

    # Calculate final weights for each group (knowledge depth priority)
    # Weight = frequency * avg_recency_weight * (1 + log(frequency))
    # This gives higher weight to frequent topics (knowledge depth first)
    for title, group in groups_by_title.items():
        avg_recency = group["total_recency_weight"] / max(1, group["frequency"])
        # Logarithmic scaling to favor frequent topics but not too aggressively
        frequency_bonus = 1.0 + (0.5 * (group["frequency"] - 1))  # Linear bonus, simpler than log
        group["final_weight"] = group["frequency"] * avg_recency * frequency_bonus

    # Sort groups by final weight (descending)
    sorted_groups = sorted(
        groups_by_title.items(),
        key=lambda x: x[1]["final_weight"],
        reverse=True
    )

    # Select top groups (max 8) and allocate content based on weight
    selected_groups = []
    total_weight_sum = sum(group["final_weight"] for _, group in sorted_groups[:8])

    for title, group in sorted_groups[:8]:  # Max 8 groups
        if total_weight_sum > 0:
            # Allocate content proportionally to weight
            weight_ratio = group["final_weight"] / total_weight_sum

            # Calculate max cards and questions for this group
            # Base: 4 cards + scaled additional (max 10 total)
            max_cards = min(10, 4 + int(6 * weight_ratio))
            # Base: 3 questions + scaled additional (max 6 total)
            max_questions = min(6, 3 + int(3 * weight_ratio))
        else:
            max_cards = 6
            max_questions = 4

        # Sort cards by total weight (most relevant/recency first)
        sorted_cards = sorted(
            group["knowledge_cards"],
            key=lambda x: x["total_weight"],
            reverse=True
        )

        # Sort questions by total weight
        sorted_questions = sorted(
            group["quiz_questions"],
            key=lambda x: x["total_weight"],
            reverse=True
        )

        # Take top cards and questions
        selected_cards = sorted_cards[:max_cards]
        selected_questions = sorted_questions[:max_questions]

        # Remove internal metadata for final output
        final_cards = []
        for card in selected_cards:
            final_cards.append({
                "id": card["id"],
                "content": card["content"],
                "is_learned": card["is_learned"]
            })

        final_questions = []
        for question in selected_questions:
            final_questions.append({
                "id": question["id"],
                "question": question["question"],
                "options": question["options"],
                "correct_answer": question["correct_answer"],
                "explanation": question["explanation"],
                "difficulty": question["difficulty"],
                "is_completed": question["is_completed"]
            })

        selected_groups.append({
            "id": group["id"],
            "title": group["title"],
            "description": group["description"],
            "knowledge_cards": final_cards,
            "quiz_questions": final_questions,
            "frequency": group["frequency"],  # Include for debugging/UI
            "session_count": len(group["source_sessions"])
        })

    # Calculate next review date (earliest from all reviews, or default)
    next_review_dates = []
    for review_data in review_data_list:
        if review_data.next_review_date:
            next_review_dates.append(review_data.next_review_date)

    if next_review_dates:
        next_review_date = min(next_review_dates)
    else:
        next_review_date = datetime.utcnow() + timedelta(days=1)

    # Generate aggregated summary
    if selected_groups:
        group_names = [group["title"] for group in selected_groups[:3]]
        aggregated_summary = f"整合复习数据来自 {len(session_info)} 个近期会话。"
        aggregated_summary += f"包含 {len(selected_groups)} 个知识领域：{', '.join(group_names)}"
        if len(selected_groups) > 3:
            aggregated_summary += " 等。"

        total_knowledge_cards = sum(len(group["knowledge_cards"]) for group in selected_groups)
        total_quiz_questions = sum(len(group["quiz_questions"]) for group in selected_groups)
        aggregated_summary += f" 总计 {total_knowledge_cards} 个知识卡片和 {total_quiz_questions} 个测验题目。"

        # Add knowledge depth insight
        if selected_groups:
            top_group = selected_groups[0]
            if top_group["frequency"] >= 3:
                aggregated_summary += f" 重点领域「{top_group['title']}」在 {top_group['session_count']} 个会话中被讨论。"
    else:
        aggregated_summary = "近期会话中没有复习数据。"
        total_knowledge_cards = 0
        total_quiz_questions = 0

    return {
        "aggregated_summary": aggregated_summary,
        "review_groups": selected_groups,
        "next_review_date": next_review_date.isoformat(),
        "session_count": len(session_info),
        "total_groups": len(selected_groups),
        "total_knowledge_cards": total_knowledge_cards,
        "total_quiz_questions": total_quiz_questions,
        "sessions": session_info
    }


def create_or_update_integrated_review_data(
    db: Session,
    time_range_days: int,
    review_groups: List[Dict[str, Any]],
    aggregated_summary: str,
    next_review_date: datetime,
    generation_config: Dict[str, Any],
    expires_at: Optional[datetime] = None,
    generation_status: str = "completed"
) -> ReviewData:
    """Create or update integrated review data for a specific time range"""
    import logging
    logger = logging.getLogger(__name__)

    # Check if integrated review data already exists for this time range
    existing = db.query(ReviewData).filter(
        ReviewData.generation_type == "integrated",
        ReviewData.time_range_days == time_range_days
    ).first()

    now = datetime.utcnow()

    if expires_at is None:
        expires_at = now + timedelta(hours=24)  # Default 24-hour expiration

    # Calculate statistics for logging
    total_groups = len(review_groups)
    total_cards = 0
    total_questions = 0
    for group in review_groups:
        total_cards += len(group.get("knowledge_cards", []))
        total_questions += len(group.get("quiz_questions", []))

    if existing:
        # Update existing record
        existing.review_groups = review_groups
        existing.aggregated_summary = aggregated_summary
        existing.next_review_date = next_review_date
        existing.generation_config = generation_config
        existing.expires_at = expires_at
        existing.generation_status = generation_status
        existing.generated_at = now
        existing.last_attempt_at = None
        existing.error_message = None

        db.commit()
        db.refresh(existing)

        logger.info(f"Updated integrated review data for {time_range_days} days: "
                   f"{total_groups} groups, {total_cards} cards, {total_questions} questions")
        return existing
    else:
        # Create new record
        review_data = ReviewData(
            session_id=None,  # No session ID for integrated reviews
            generation_type="integrated",
            time_range_days=time_range_days,
            review_groups=review_groups,
            aggregated_summary=aggregated_summary,
            next_review_date=next_review_date,
            generation_config=generation_config,
            expires_at=expires_at,
            generation_status=generation_status,
            generated_at=now,
            learned_cards=[],
            completed_quizzes=[],
            review_count=0
        )

        db.add(review_data)
        db.commit()
        db.refresh(review_data)

        logger.info(f"Created integrated review data for {time_range_days} days: "
                   f"{total_groups} groups, {total_cards} cards, {total_questions} questions")
        return review_data


def get_valid_integrated_review_data(db: Session, time_range_days: int) -> Optional[ReviewData]:
    """Get valid (non-expired and completed) integrated review data for a time range"""
    now = datetime.utcnow()
    review_data = db.query(ReviewData).filter(
        ReviewData.generation_type == "integrated",
        ReviewData.time_range_days == time_range_days,
        ReviewData.generation_status == "completed",
        ReviewData.expires_at > now
    ).first()
    return review_data