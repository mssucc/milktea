"""Review generation background task implementation"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.database import crud
from backend.database.session import SessionLocal
from backend.utils.structured_review_generator import structured_review_generator
# Legacy imports kept for helper functions
from backend.graph_db.graph_generator import graph_generator
from backend.graph_db.neo4j_client import get_top_entities_by_mention_count, get_sessions_for_entity
from backend.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

# Helper functions for session selection

def get_recent_message_statistics(db: Session, days: int = 2) -> List[Dict[str, Any]]:
    """Get message statistics for recent days"""
    cutoff_time = datetime.utcnow() - timedelta(days=days)

    # Get messages per day for the last N days
    # This is a simplified implementation - in production you might want more detailed stats
    message_counts = []
    for i in range(days):
        day_start = cutoff_time + timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        count = db.query(crud.Message).filter(
            crud.Message.timestamp >= day_start,
            crud.Message.timestamp < day_end
        ).count()

        message_counts.append({
            "date": day_start.date(),
            "count": count
        })

    return message_counts


def get_sessions_with_new_messages(db: Session, limit: int = 20) -> List[str]:
    """Get sessions with new messages (no review data or outdated review)"""
    # Get sessions with messages in the last 3 days
    recent_session_ids = crud.get_session_ids_with_recent_activity(db, days=3)

    if not recent_session_ids:
        return []

    # Filter sessions that need review generation
    sessions_needing_generation = crud.get_sessions_needing_review_generation(
        db, recent_session_ids
    )

    return sessions_needing_generation[:limit]


def filter_active_tasks(db: Session, session_ids: List[str]) -> List[str]:
    """Filter out sessions with active generation tasks"""
    # Get sessions with tasks in 'running' or 'pending' status
    active_tasks = (
        db.query(crud.ReviewGenerationTask)
        .filter(
            crud.ReviewGenerationTask.session_id.in_(session_ids),
            crud.ReviewGenerationTask.status.in_(["pending", "running"])
        )
        .all()
    )

    active_session_ids = {task.session_id for task in active_tasks}
    return [sid for sid in session_ids if sid not in active_session_ids]


def needs_review_generation(db: Session, session_id: str) -> bool:
    """Check if a session needs review generation"""
    review_data = crud.get_review_data(db, session_id)
    if not review_data:
        return True

    now = datetime.utcnow()
    if review_data.generation_status == "failed":
        # Check if we should retry (after some backoff period)
        if review_data.last_attempt_at:
            time_since_last_attempt = now - review_data.last_attempt_at
            # Retry after 1 hour for failed tasks
            return time_since_last_attempt > timedelta(hours=1)
        return True

    if review_data.generation_status == "completed":
        # Check if cache expired (24h)
        if review_data.expires_at and review_data.expires_at <= now:
            return True

        # Check if review is old enough (> 7 days) AND has new messages
        # Fresh reviews (< 7 days) are kept even with new messages to preserve progress
        if review_data.generated_at and (now - review_data.generated_at).days >= 7:
            last_message = crud.get_last_message(db, session_id)
            if last_message and last_message.timestamp > review_data.generated_at:
                return True

    return False


def select_sessions_for_review_generation(
    db: Session,
    limit: int = 20,
    time_range: str = "7d"
) -> List[str]:
    """
    Select sessions for review generation based on high-frequency entities and dynamic adjustment strategy.

    Algorithm design principles:
    1. Focus on high-frequency nodes: prioritize sessions mentioning frequently mentioned entities
    2. Dynamic adjustment: adjust processing scope based on conversation frequency
       - High frequency (>10 messages/day): only process Top 10 high-frequency entity sessions
       - Medium frequency (3-10 messages/day): process Top 15 high-frequency entity sessions
       - Low frequency (<3 messages/day): process all sessions with new messages
    3. Smart filtering: exclude sessions being processed, cached and not expired, or recently failed
    4. Time-range aware:
       - "7d": detailed analysis with session-level insights (knowledge cards + quiz questions)
       - "30d": simplified analysis based on node statistics only (knowledge cards only)

    Args:
        db: Database session
        limit: Maximum number of sessions to select
        time_range: Time range for analysis - "7d" (7 days) or "30d" (30 days)

    Returns:
        List of session IDs selected for review generation
    """

    # 1. Get recent message statistics to calculate conversation frequency
    # For 7d range: use last 2 days stats
    # For 30d range: use last 7 days stats (longer window for stable frequency estimation)
    stats_days = 2 if time_range == "7d" else 7
    message_stats = get_recent_message_statistics(db, days=stats_days)
    total_messages = sum(stats["count"] for stats in message_stats)
    avg_messages_per_day = total_messages / stats_days if message_stats else 0

    logger.info(f"{time_range} range - Recent conversation frequency: {avg_messages_per_day:.1f} messages/day")

    # 2. Determine strategy based on conversation frequency
    if avg_messages_per_day >= 10:
        # High conversation frequency: only focus on Top 10 high-frequency entities
        top_n_entities = 10
        session_limit = min(limit, 15)  # Limit session count
        logger.info(f"High frequency mode: focusing on Top {top_n_entities} entities, max {session_limit} sessions")
    elif avg_messages_per_day >= 3:
        # Medium conversation frequency: focus on Top 15 high-frequency entities
        top_n_entities = 15
        session_limit = min(limit, 20)
        logger.info(f"Medium frequency mode: focusing on Top {top_n_entities} entities, max {session_limit} sessions")
    else:
        # Low conversation frequency: process all sessions with new messages
        top_n_entities = None
        session_limit = limit
        logger.info(f"Low frequency mode: processing all sessions with new messages")

    # 3. Get sessions based on the selected strategy
    if top_n_entities is not None:
        # Get high-frequency entities from Neo4j
        # For 7d range: look at last 2 days for short-term trends
        # For 30d range: look at last 30 days for long-term patterns
        entity_days = 2 if time_range == "7d" else 30
        try:
            top_entities = get_top_entities_by_mention_count(
                days=entity_days,
                limit=top_n_entities
            )
            logger.info(f"Found {len(top_entities)} high-frequency entities from last {entity_days} days")

            # Get sessions associated with these entities
            sessions_from_entities = []
            for entity in top_entities[:top_n_entities]:
                entity_name = entity.get("name", "")
                if entity_name:
                    entity_sessions = get_sessions_for_entity(entity_name)
                    for session_id in entity_sessions:
                        if needs_review_generation(db, session_id):
                            sessions_from_entities.append(session_id)

            # Deduplicate and sort by number of associated entities
            session_counts = {}
            for session_id in sessions_from_entities:
                session_counts[session_id] = session_counts.get(session_id, 0) + 1

            # Sort by number of associated entities (descending)
            sorted_sessions = sorted(
                session_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )

            selected_sessions = [session_id for session_id, _ in sorted_sessions[:session_limit]]
            logger.info(f"Selected {len(selected_sessions)} sessions from high-frequency entities")

        except Exception as e:
            logger.error(f"Error getting high-frequency entities from Neo4j: {e}")
            # Fallback: get sessions with new messages
            selected_sessions = get_sessions_with_new_messages(db, session_limit)
            logger.info(f"Fallback: selected {len(selected_sessions)} sessions with new messages")
    else:
        # Low frequency: process all sessions with new messages
        selected_sessions = get_sessions_with_new_messages(db, session_limit)
        logger.info(f"Selected {len(selected_sessions)} sessions with new messages")

    # 4. Filter out sessions with active tasks
    filtered_sessions = filter_active_tasks(db, selected_sessions)
    logger.info(f"After filtering active tasks: {len(filtered_sessions)} sessions")

    return filtered_sessions[:limit]


# Main task execution functions

async def generate_review_background(session_id: str, config: Dict[str, Any] = None):
    """
    Background task to generate review for a session.
    This function is called by APScheduler.
    """
    if config is None:
        config = {}

    logger.info(f"Starting background review generation for session {session_id}")

    db = SessionLocal()
    try:
        # 1. Create or update task record
        review_data = crud.get_review_data(db, session_id)
        task = crud.create_review_generation_task(
            db=db,
            session_id=session_id,
            task_type="background",
            priority=config.get("priority", 0),
            review_data_id=review_data.id if review_data else None
        )

        # 2. Update review data status
        crud.update_review_generation_status(
            db=db,
            session_id=session_id,
            status="generating"
        )

        # 3. Execute the generation with timeout (300 seconds = 5 minutes)
        try:
            result = await asyncio.wait_for(
                execute_review_generation(db, session_id, config, task.id),
                timeout=300.0  # 5 minutes timeout for entire review generation
            )
            logger.info(f"Background review generation completed for session {session_id}")
            return result
        except asyncio.TimeoutError:
            logger.error(f"Review generation timeout for session {session_id} after 300 seconds")
            raise TimeoutError(f"Review generation timeout for session {session_id}")

    except Exception as e:
        logger.error(f"Error in background review generation for session {session_id}: {e}")

        # Update status to failed
        try:
            crud.update_review_generation_status(
                db=db,
                session_id=session_id,
                status="failed",
                error_message=str(e)
            )

            # Update task status
            if 'task' in locals():
                crud.update_task_status(
                    db=db,
                    task_id=task.id,
                    status="failed",
                    error_message=str(e)
                )
        except Exception as update_error:
            logger.error(f"Error updating status after failure: {update_error}")

        raise
    finally:
        db.close()


async def execute_review_generation(
    db: Session,
    session_id: str,
    config: Dict[str, Any],
    task_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute structured review generation for a session using the new structured generator.
    """
    start_time = datetime.utcnow()

    # Update task status to running
    if task_id:
        crud.update_task_status(db, task_id, "running")

    try:
        # Extract configuration
        api_key = config.get("api_key")
        base_url = config.get("base_url")
        model = config.get("model")

        logger.info(f"Generating structured review for session {session_id}")

        # 1. Get conversation messages
        all_messages = crud.get_messages_by_session(db, session_id, limit=50)
        if not all_messages:
            raise ValueError(f"No messages found for session {session_id}")

        message_list = [
            {"role": msg.role, "content": msg.content}
            for msg in all_messages
        ]

        logger.info(f"Found {len(message_list)} messages for session {session_id}")

        # 2. Generate structured review using the new generator
        logger.debug(f"Generating structured review for {len(message_list)} messages")
        try:
            structured_data = await asyncio.to_thread(
                structured_review_generator.generate_structured_review,
                message_list,
                session_id,
                api_key=api_key,
                base_url=base_url,
                model=model
            )
            logger.info(f"Successfully generated structured review")
        except Exception as e:
            logger.error(f"Failed to generate structured review: {e}")
            raise

        # 2.5. Audit generated content against source conversation (dual-phase verification)
        try:
            logger.info(f"Starting audit phase for session {session_id}")
            structured_data = await asyncio.to_thread(
                structured_review_generator.audit_review,
                structured_data,
                message_list,
                api_key=api_key,
                base_url=base_url,
                model=model
            )
            logger.info(f"Audit phase completed for session {session_id}")
        except Exception as e:
            logger.error(f"Audit phase failed for session {session_id}: {e}, using unverified data")
            # Continue with unverified data rather than failing entirely

        # 3. Prepare data for storage
        review_groups = structured_data.get("review_groups", [])
        aggregated_summary = structured_data.get("aggregated_summary", "")

        # Set next review date (24 hours from now)
        next_review_date = datetime.utcnow() + timedelta(days=1)
        expires_at = datetime.utcnow() + timedelta(hours=24)  # 24-hour cache

        # 4. Create generation config
        generation_config = {
            "api_key_provided": api_key is not None,
            "base_url": base_url,
            "model": model,
            "message_count": len(message_list),
            "generated_at": datetime.utcnow().isoformat(),
            "audit_summary": structured_data.get("audit_summary", "")
        }

        # 5. Store results in database
        review_data = crud.create_or_update_review_data(
            db=db,
            session_id=session_id,
            review_groups=review_groups,
            aggregated_summary=aggregated_summary,
            next_review_date=next_review_date,
            generation_config=generation_config,
            expires_at=expires_at,
            generation_status="completed"
        )

        # 6. Update task status
        if task_id:
            crud.update_task_status(db, task_id, "completed")

        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Structured review generation completed in {elapsed_time:.2f}s")

        # Return the structured data
        return structured_data

    except Exception as e:
        logger.error(f"Error executing structured review generation for session {session_id}: {e}")

        # Update task status to failed
        if task_id:
            crud.update_task_status(db, task_id, "failed", error_message=str(e))

        raise


async def scan_and_generate_reviews():
    """
    Scheduled task to scan for sessions needing review generation and process them.
    Runs every 12 hours (twice a day).
    """
    logger.info("Starting scheduled review generation scan")

    db = SessionLocal()
    try:
        # Select sessions for review generation
        session_ids = select_sessions_for_review_generation(
            db=db,
            limit=20  # Process up to 20 sessions per scan
        )

        logger.info(f"Selected {len(session_ids)} sessions for review generation")

        # Process sessions sequentially in a single batch job to avoid
        # resource contention (N concurrent LLM calls + DB writes).
        if session_ids:
            from backend.scheduler.task_executor import schedule_batch_review_generation
            job_id = schedule_batch_review_generation(session_ids, config={})
            logger.info(f"Scheduled batch review generation job {job_id} for {len(session_ids)} sessions")

        return {
            "sessions_selected": len(session_ids),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in scheduled review generation scan: {e}")
        raise
    finally:
        db.close()