from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import json
import asyncio

from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

from backend.database.session import get_db
from backend.database import crud
from backend.database.model import ReviewData
from backend.scheduler import schedule_review_generation, schedule_integrated_review_generation, schedule_batch_review_generation, is_batch_active, get_batch_progress
from backend.utils.structured_review_generator import structured_review_generator
from backend.utils.node_based_review_generator import node_based_review_generator
from backend.graph_db.graph_generator import graph_generator

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models for Structured Review

class ReviewRequest(BaseModel):
    """Request model for review generation with API configuration"""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    # Legacy parameters kept for API compatibility
    recent_days: int = Field(default=3, ge=1, le=30, description="Legacy parameter")
    top_n_recent: int = Field(default=3, ge=1, le=10, description="Legacy parameter")
    max_questions: int = Field(default=10, ge=1, le=20, description="Legacy parameter")


class KnowledgeCard(BaseModel):
    """Knowledge card for learning key points"""
    id: str
    content: str
    is_learned: bool = False


class QuizQuestion(BaseModel):
    """Multiple-choice quiz question"""
    id: str
    question: str
    options: List[str]
    correct_answer: int = Field(ge=0, le=3, description="Index of correct answer (0-3)")
    explanation: str
    difficulty: str = "medium"  # easy, medium, hard
    is_completed: bool = False
    user_answer: Optional[int] = Field(None, ge=0, le=3, description="User's answer index (if completed)")
    is_correct: Optional[bool] = Field(None, description="Whether user's answer is correct")


class ReviewGroup(BaseModel):
    """Group of related knowledge cards and quiz questions"""
    id: str
    title: str
    description: str
    knowledge_cards: List[KnowledgeCard]
    quiz_questions: List[QuizQuestion]
    category: Optional[str] = None


class StructuredReviewResponse(BaseModel):
    """Response model for structured review data"""
    session_id: str
    aggregated_summary: str
    review_groups: List[ReviewGroup]
    total_groups: int
    total_knowledge_cards: int
    total_quiz_questions: int
    next_review_date: str
    generated_at: str
    message_count: int


class QuizAnswerRequest(BaseModel):
    """Request model for submitting quiz answers"""
    question_id: str
    user_answer: int = Field(ge=0, le=3, description="User's answer index (0-3)")


class MarkCardLearnedRequest(BaseModel):
    """Request model for marking knowledge card as learned"""
    card_id: str
    is_learned: bool = True


# Helper functions

def convert_structured_review_data_to_response(review_data) -> StructuredReviewResponse:
    """Convert ReviewData database object to StructuredReviewResponse"""
    # Get structured data from JSON fields
    review_groups = review_data.review_groups or []
    aggregated_summary = review_data.aggregated_summary or ""

    # Convert groups to Pydantic models
    groups = []
    for group_data in review_groups:
        # Convert knowledge cards
        knowledge_cards = []
        for card_data in group_data.get("knowledge_cards", []):
            knowledge_cards.append(
                KnowledgeCard(
                    id=card_data.get("id", ""),
                    content=card_data.get("content", ""),
                    is_learned=card_data.get("is_learned", False)
                )
            )

        # Convert quiz questions
        quiz_questions = []
        for question_data in group_data.get("quiz_questions", []):
            quiz_questions.append(
                QuizQuestion(
                    id=question_data.get("id", ""),
                    question=question_data.get("question", ""),
                    options=question_data.get("options", ["选项A", "选项B", "选项C", "选项D"]),
                    correct_answer=question_data.get("correct_answer", 0),
                    explanation=question_data.get("explanation", ""),
                    difficulty=question_data.get("difficulty", "medium"),
                    is_completed=question_data.get("is_completed", False),
                    user_answer=question_data.get("user_answer"),
                    is_correct=question_data.get("is_correct")
                )
            )

        groups.append(
            ReviewGroup(
                id=group_data.get("id", ""),
                title=group_data.get("title", ""),
                description=group_data.get("description", ""),
                knowledge_cards=knowledge_cards,
                quiz_questions=quiz_questions,
                category=group_data.get("category")
            )
        )

    # Calculate statistics
    total_groups = len(groups)
    total_knowledge_cards = sum(len(g.knowledge_cards) for g in groups)
    total_quiz_questions = sum(len(g.quiz_questions) for g in groups)

    # Handle dates
    next_review_date = review_data.next_review_date.isoformat() if review_data.next_review_date else datetime.now(timezone.utc).isoformat()
    generated_at = review_data.generated_at.isoformat() if review_data.generated_at else datetime.now(timezone.utc).isoformat()

    # Get message count from generation config or use default
    message_count = 0
    if review_data.generation_config and isinstance(review_data.generation_config, dict):
        message_count = review_data.generation_config.get("message_count", 0)

    return StructuredReviewResponse(
        session_id=review_data.session_id,
        aggregated_summary=aggregated_summary,
        review_groups=groups,
        total_groups=total_groups,
        total_knowledge_cards=total_knowledge_cards,
        total_quiz_questions=total_quiz_questions,
        next_review_date=next_review_date,
        generated_at=generated_at,
        message_count=message_count
    )


# Main review endpoint

@router.post("/review/{session_id}", response_model=StructuredReviewResponse)
async def get_session_review(
    session_id: str,
    request: Optional[ReviewRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Get structured review data for a specific session.

    Returns cached data if available, otherwise triggers background generation.
    """
    if request is None:
        request = ReviewRequest()

    logger.info(f"Structured review request for session {session_id}")

    try:
        # 1. Check for valid cached review data
        cached_review = crud.get_valid_review_data(db, session_id)
        if cached_review:
            logger.info(f"Cache hit for session {session_id}, returning cached review")
            return convert_structured_review_data_to_response(cached_review)

        # 2. Check if review is currently being generated
        review_data = crud.get_review_data(db, session_id)
        if review_data and review_data.generation_status == "generating":
            # Treat as stale if last_attempt_at is missing or older than 10 minutes
            stale_cutoff = datetime.utcnow() - timedelta(minutes=10)
            if (review_data.last_attempt_at is None
                    or review_data.last_attempt_at < stale_cutoff):
                logger.info(f"Stale generating status for session {session_id}, triggering fresh generation")
            else:
                logger.info(f"Review generation in progress for session {session_id}")
                return JSONResponse(
                    status_code=202,
                    content={
                        "message": "Review generation in progress",
                        "session_id": session_id,
                        "status": "generating",
                        "estimated_time": 120,
                        "poll_url": f"/api/review/{session_id}/status",
                        "generated_at": review_data.generated_at.isoformat() if review_data.generated_at else None
                    }
                )

        # 3. Check if session exists (has messages)
        messages = crud.get_messages_by_session(db, session_id, limit=1)
        if not messages:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or has no messages"
            )

        # 4. Trigger background generation
        logger.info(f"Triggering background structured review generation for session {session_id}")

        # Prepare configuration for background task
        config = {
            "api_key": request.api_key,
            "base_url": request.base_url,
            "model": request.model,
            "priority": 10  # Higher priority for user-initiated requests
        }

        # Schedule background generation
        task_id = schedule_review_generation(session_id, config)

        # 5. Return 202 Accepted with task information
        return JSONResponse(
            status_code=202,
            content={
                "message": "Review generation started",
                "session_id": session_id,
                "task_id": task_id,
                "status": "pending",
                "estimated_time": 120,  # Estimated time in seconds (2 minutes)
                "poll_url": f"/api/review/{session_id}/status",
                "config": {
                    "api_key_provided": request.api_key is not None,
                    "base_url": request.base_url,
                    "model": request.model
                }
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Specific error for API key validation or configuration issues
        logger.error(f"Configuration error for session {session_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"API configuration error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing review request for session {session_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process review request: {str(e)}"
        )


# Status and management endpoints

@router.get("/review/{session_id}/status")
async def get_review_status(session_id: str, db: Session = Depends(get_db)):
    """Get review generation status for a session"""
    try:
        logger.info(f"Getting review status for session: {session_id}")

        # Check for cached review data
        cached_review = crud.get_valid_review_data(db, session_id)
        if cached_review:
            return {
                "session_id": session_id,
                "status": "completed",
                "generated_at": cached_review.generated_at.isoformat() if cached_review.generated_at else None,
                "expires_at": cached_review.expires_at.isoformat() if cached_review.expires_at else None,
                "has_cache": True,
                "total_groups": len(cached_review.review_groups or []),
                "total_knowledge_cards": sum(len(g.get("knowledge_cards", [])) for g in (cached_review.review_groups or [])),
                "total_quiz_questions": sum(len(g.get("quiz_questions", [])) for g in (cached_review.review_groups or []))
            }

        # Check current generation status
        review_data = crud.get_review_data(db, session_id)
        if review_data:
            return {
                "session_id": session_id,
                "status": review_data.generation_status,
                "generated_at": review_data.generated_at.isoformat() if review_data.generated_at else None,
                "last_attempt_at": review_data.last_attempt_at.isoformat() if review_data.last_attempt_at else None,
                "error_message": review_data.error_message,
                "has_cache": False
            }

        # No review data at all
        return {
            "session_id": session_id,
            "status": "not_started",
            "has_cache": False,
            "message": "No review data found for this session"
        }

    except Exception as e:
        logger.error(f"Error getting review status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/review/{session_id}/regenerate")
async def regenerate_review(
    session_id: str,
    request: Optional[ReviewRequest] = None,
    db: Session = Depends(get_db)
):
    """Manually trigger review regeneration for a session"""
    if request is None:
        request = ReviewRequest()

    logger.info(f"Manual review regeneration requested for session {session_id}")

    try:
        # Delete existing review data if it exists
        crud.delete_review_data(db, session_id)

        # Prepare configuration for background task
        config = {
            "api_key": request.api_key,
            "base_url": request.base_url,
            "model": request.model,
            "priority": 15  # High priority for manual requests
        }

        # Schedule background generation
        task_id = schedule_review_generation(session_id, config)

        return JSONResponse(
            status_code=202,
            content={
                "message": "Review regeneration started",
                "session_id": session_id,
                "task_id": task_id,
                "status": "pending",
                "estimated_time": 120,
                "poll_url": f"/api/review/{session_id}/status"
            }
        )

    except Exception as e:
        logger.error(f"Error triggering review regeneration: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger review regeneration: {str(e)}"
        )


# Quiz and learning interaction endpoints

@router.post("/review/{session_id}/submit-quiz-answer")
async def submit_quiz_answer(
    session_id: str,
    answer_request: QuizAnswerRequest,
    db: Session = Depends(get_db)
):
    """Submit answer for a quiz question and update user progress"""
    try:
        logger.info(f"Submitting quiz answer for session {session_id}, question {answer_request.question_id}")

        # Get current review data
        review_data = crud.get_valid_review_data(db, session_id)
        if not review_data:
            raise HTTPException(status_code=404, detail="No review data found for this session")

        # Find the question in review groups
        review_groups = review_data.review_groups or []
        question_found = False
        is_correct = False

        for group in review_groups:
            quiz_questions = group.get("quiz_questions", [])
            for i, question in enumerate(quiz_questions):
                if question.get("id") == answer_request.question_id:
                    question_found = True
                    # Check if answer is correct
                    correct_answer = question.get("correct_answer", 0)
                    is_correct = (answer_request.user_answer == correct_answer)

                    # Update question status
                    question["is_completed"] = True
                    question["user_answer"] = answer_request.user_answer
                    question["is_correct"] = is_correct

                    # Update the quiz_questions list
                    quiz_questions[i] = question
                    group["quiz_questions"] = quiz_questions
                    break

            if question_found:
                break

        if not question_found:
            raise HTTPException(status_code=404, detail="Question not found")

        # Update review data in database
        crud.update_review_data_json(db, session_id, "review_groups", review_groups)

        return {
            "success": True,
            "is_correct": is_correct,
            "question_id": answer_request.question_id,
            "user_answer": answer_request.user_answer
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting quiz answer: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/review/{session_id}/mark-card-learned")
async def mark_card_learned(
    session_id: str,
    card_request: MarkCardLearnedRequest,
    db: Session = Depends(get_db)
):
    """Mark a knowledge card as learned or unlearned"""
    try:
        logger.info(f"Marking card {card_request.card_id} as learned={card_request.is_learned} for session {session_id}")

        # Get current review data
        review_data = crud.get_valid_review_data(db, session_id)
        if not review_data:
            raise HTTPException(status_code=404, detail="No review data found for this session")

        # Find the card in review groups
        review_groups = review_data.review_groups or []
        card_found = False

        for group in review_groups:
            knowledge_cards = group.get("knowledge_cards", [])
            for i, card in enumerate(knowledge_cards):
                if card.get("id") == card_request.card_id:
                    card_found = True
                    # Update card status
                    card["is_learned"] = card_request.is_learned

                    # Update the knowledge_cards list
                    knowledge_cards[i] = card
                    group["knowledge_cards"] = knowledge_cards
                    break

            if card_found:
                break

        if not card_found:
            raise HTTPException(status_code=404, detail="Knowledge card not found")

        # Update review data in database
        crud.update_review_data_json(db, session_id, "review_groups", review_groups)

        # Also update learned_cards array for quick statistics
        learned_cards = review_data.learned_cards or []
        if card_request.is_learned and card_request.card_id not in learned_cards:
            learned_cards.append(card_request.card_id)
        elif not card_request.is_learned and card_request.card_id in learned_cards:
            learned_cards.remove(card_request.card_id)

        crud.update_review_data_json(db, session_id, "learned_cards", learned_cards)

        return {
            "success": True,
            "card_id": card_request.card_id,
            "is_learned": card_request.is_learned
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking card as learned: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Session-level and group-level deletion

@router.delete("/review/{session_id}")
async def delete_session_review(session_id: str, db: Session = Depends(get_db)):
    """Delete all review data for a session (including note-based reviews).

    Falls back to removing the session from integrated cache if the per-session
    record no longer exists (e.g. expired and cleaned up).
    """
    try:
        deleted = crud.delete_review_data(db, session_id)
        # Also remove this session from all integrated caches
        cache_cleaned = crud.remove_session_from_integrated_caches(db, session_id)
        if not deleted and not cache_cleaned:
            raise HTTPException(status_code=404, detail=f"No review data found for session '{session_id}'")
        logger.info(f"Deleted review data for session {session_id} (per-session: {deleted}, cache: {cache_cleaned})")
        return {"message": f"Review data deleted for session '{session_id}'", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting review for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/review/{session_id}/groups/{group_id}")
async def delete_review_group_endpoint(session_id: str, group_id: str, db: Session = Depends(get_db)):
    """Delete a specific review group from a session's review data.

    Falls back to removing the group from integrated cache if the per-session
    record no longer exists.
    """
    try:
        deleted = crud.delete_review_group(db, session_id, group_id)
        # Also try to remove this group from integrated caches
        cache_cleaned = crud.remove_group_from_integrated_caches(db, session_id, group_id)
        if not deleted and not cache_cleaned:
            raise HTTPException(status_code=404, detail=f"Group '{group_id}' not found in session '{session_id}'")
        logger.info(f"Deleted group {group_id} from session {session_id} (per-session: {deleted}, cache: {cache_cleaned})")
        return {"message": f"Group '{group_id}' deleted from session '{session_id}'", "session_id": session_id, "group_id": group_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting group {group_id} from session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Integrated review endpoints (cross-session aggregation)

class IntegratedReviewRequest(BaseModel):
    """Request model for integrated review generation"""
    session_ids: Optional[List[str]] = None  # Optional specific sessions to include
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of sessions to aggregate")
    days: int = Field(default=7, ge=1, le=30, description="Time range for review generation (days)")
    force_refresh: bool = Field(default=False, description="Force regeneration of reviews")
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class IntegratedReviewProgressRequest(BaseModel):
    """Request model for saving integrated review progress"""
    days: int = Field(ge=1, le=30, description="Time range in days")
    learned_cards: List[str] = Field(default=[], description="List of learned knowledge card IDs")
    completed_quizzes: List[str] = Field(default=[], description="List of completed quiz question IDs")


class SessionInfo(BaseModel):
    """Information about a session included in integrated review"""
    session_id: str
    generated_at: Optional[str] = None
    recency_weight: Optional[float] = None
    message_count: Optional[int] = None


class IntegratedReviewGroup(ReviewGroup):
    """Review group with additional metadata for integrated review"""
    frequency: int = Field(description="How many sessions mentioned this topic")
    session_count: int = Field(description="Number of sessions contributing to this group")


class SessionGroup(BaseModel):
    """Groups from a single session for nested accordion display"""
    session_id: str
    title: str
    generated_at: Optional[str] = None
    groups: List[ReviewGroup]
    group_count: int


class IntegratedReviewResponse(BaseModel):
    """Response model for integrated review data"""
    aggregated_summary: str
    review_groups: List[IntegratedReviewGroup]
    session_groups: List[SessionGroup] = []
    next_review_date: str
    session_count: int
    total_groups: int
    total_knowledge_cards: int
    total_quiz_questions: int
    sessions: List[SessionInfo]
    generation_in_progress: bool = False
    batch_progress: Optional[dict] = None


def _enrich_session_titles_with_kg(session_groups: list) -> None:
    """Replace session_groups wrapper titles with top knowledge graph entity names.

    Falls back to existing titles if Neo4j is unavailable or returns no entities.
    """
    if not session_groups:
        return
    try:
        session_ids = [sg["session_id"] for sg in session_groups if sg.get("session_id")]
        if not session_ids:
            return

        entities = graph_generator.get_entities_for_sessions(session_ids)
        if not entities:
            return

        # Find the highest importance entity per session
        best_per_session: Dict[str, tuple] = {}
        for e in entities:
            e_name = e.get("name", "")
            e_session_ids = e.get("session_ids", [])
            e_scores = e.get("importance_scores", [])
            if not e_name:
                continue
            for sid in session_ids:
                if sid in e_session_ids:
                    idx = e_session_ids.index(sid)
                    score = e_scores[idx] if idx < len(e_scores) else e.get("importance_score", 1)
                    current = best_per_session.get(sid)
                    if not current or score > current[1]:
                        best_per_session[sid] = (e_name, score)

        for sg in session_groups:
            best = best_per_session.get(sg["session_id"])
            if best:
                sg["title"] = best[0]
    except Exception:
        # Neo4j unavailable — keep existing titles as fallback
        pass


def _format_cached_integrated(cached) -> dict:
    """Format a cached integrated ReviewData record into a response dict."""
    review_groups = cached.review_groups or []
    session_groups = []
    sessions = []
    if cached.generation_config and isinstance(cached.generation_config, dict):
        entity_count = cached.generation_config.get("entity_count", 0)
        session_groups = cached.generation_config.get("session_groups", [])
        for i in range(min(3, max(1, entity_count // 5))):
            sessions.append({
                "session_id": f"cached_session_{i+1}",
                "generated_at": cached.generated_at.isoformat() if cached.generated_at else None,
                "recency_weight": 0.3,
                "message_count": 8
            })
    return {
        "aggregated_summary": cached.aggregated_summary or "",
        "review_groups": review_groups,
        "session_groups": session_groups,
        "next_review_date": cached.next_review_date.isoformat() if cached.next_review_date else datetime.now(timezone.utc).isoformat(),
        "session_count": len(sessions),
        "total_groups": len(review_groups),
        "total_knowledge_cards": sum(len(g.get("knowledge_cards", [])) for g in review_groups),
        "total_quiz_questions": sum(len(g.get("quiz_questions", [])) for g in review_groups),
        "sessions": sessions,
        "generation_in_progress": False,
        "batch_progress": None
    }


def empty_integrated_review(days: int = 7) -> dict:
    """Return empty integrated review data structure"""
    return {
        "aggregated_summary": f"基于最近{days}天对话的复习数据",
        "review_groups": [],
        "session_groups": [],
        "next_review_date": datetime.now(timezone.utc).isoformat(),
        "session_count": 0,
        "total_groups": 0,
        "total_knowledge_cards": 0,
        "total_quiz_questions": 0,
        "sessions": [],
        "generation_in_progress": False,
        "batch_progress": None
    }


@router.post("/review/integrated/overview", response_model=IntegratedReviewResponse)
async def get_integrated_review_overview(
    request: Optional[IntegratedReviewRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Get integrated review overview across multiple sessions.

    New strategy based on time range:
    1. 0-7 days: Use detailed session analysis (knowledge cards + quiz questions)
    2. 7-30 days: Use node-based analysis (entity statistics + LLM-generated content)

    Implements knowledge-depth-first + recency-assisted aggregation.
    """
    if request is None:
        request = IntegratedReviewRequest()

    logger.info(f"Integrated review overview requested: days={request.days}, limit={request.limit}, force_refresh={request.force_refresh}")

    try:
        now = datetime.utcnow()
        stale_incomplete_cutoff = now - timedelta(days=30)  # incomplete + 30 days → stale
        stale_completed_cutoff = now - timedelta(days=7)    # completed + 7 days → stale

        # ── 1. Check cached integrated review ──────────────────────────
        cached_integrated = db.query(ReviewData).filter(
            ReviewData.generation_type == "integrated",
            ReviewData.time_range_days == request.days
        ).first()

        # ── 2. Staleness: clear review groups if too old ───────────────
        if cached_integrated and cached_integrated.review_groups and cached_integrated.generated_at:
            status = cached_integrated.generation_status
            if status in ("generating", "failed", "pending"):
                if cached_integrated.generated_at < stale_incomplete_cutoff:
                    logger.info(f"Clearing stale incomplete integrated review ({request.days}d, status={status})")
                    cached_integrated.review_groups = []
                    db.commit()
            elif status == "completed":
                if cached_integrated.generated_at < stale_completed_cutoff:
                    logger.info(f"Clearing stale completed integrated review ({request.days}d)")
                    cached_integrated.review_groups = []
                    db.commit()

        # ── 3. Determine what to display ───────────────────────────────
        display_data = None
        batch_key = f"integrated_{request.days}d"
        generation_in_progress = is_batch_active(batch_key)

        # Use cached integrated data if it has review groups and is not being force-refreshed
        has_valid_cache = (
            not request.force_refresh
            and cached_integrated
            and cached_integrated.review_groups
            and len(cached_integrated.review_groups) > 0
        )
        if has_valid_cache:
            logger.info(f"Returning cached integrated review ({request.days}d)")
            display_data = _format_cached_integrated(cached_integrated)

        # Fall back to aggregating per-session review data
        if display_data is None and not request.force_refresh and request.days <= 7:
            aggregated = crud.get_aggregated_review_data(
                db=db,
                session_ids=request.session_ids,
                limit=request.limit,
                days=request.days
            )
            if aggregated.get("total_groups", 0) > 0:
                logger.info(f"Aggregated per-session data available: {aggregated['total_groups']} groups")
                # Persist as integrated cache for progress tracking
                # Skip persistence when batch is active — the aggregated view is incomplete
                if not generation_in_progress:
                    try:
                        crud.create_or_update_integrated_review_data(
                            db=db,
                            time_range_days=request.days,
                            review_groups=aggregated.get("review_groups", []),
                            aggregated_summary=aggregated.get("aggregated_summary", ""),
                            next_review_date=(
                                datetime.fromisoformat(aggregated["next_review_date"].replace('Z', '+00:00'))
                                if aggregated.get("next_review_date") else now + timedelta(hours=24)
                            ),
                            generation_config={
                                "source": "aggregation",
                                "session_count": aggregated.get("session_count", 0),
                                "aggregated_at": now.isoformat(),
                                "session_groups": aggregated.get("session_groups", [])
                            },
                            expires_at=now + timedelta(hours=24),
                            generation_status="completed"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to persist aggregated review: {e}")
                display_data = aggregated
                _enrich_session_titles_with_kg(display_data.get("session_groups"))

        # Nothing to display — return empty, but include progress info
        if display_data is None:
            logger.info(f"No review data available for {request.days}d, returning empty")
            display_data = empty_integrated_review(request.days)

        # ── 4. Trigger background generation if needed (fire-and-forget)
        # Skip if a batch is already running for this time range
        if not generation_in_progress:
            recent_sessions = crud.get_session_ids_with_recent_activity(db, days=3)
            if recent_sessions:
                # Check if there's new content that needs generation
                sessions_to_generate = []
                for sid in recent_sessions[:request.limit]:
                    existing_review = db.query(ReviewData).filter(
                        ReviewData.session_id == sid,
                        ReviewData.generation_status == "completed",
                        ReviewData.expires_at > now
                    ).first()
                    if not existing_review:
                        # No valid review → needs generation
                        sessions_to_generate.append(sid)
                    else:
                        # Has valid review → check for new messages
                        last_msg = crud.get_last_message(db, sid)
                        if (last_msg and existing_review.generated_at
                                and last_msg.timestamp > existing_review.generated_at
                                and (now - existing_review.generated_at).days >= 7):
                            sessions_to_generate.append(sid)

                # Also trigger if force_refresh requested
                if request.force_refresh:
                    sessions_to_generate = recent_sessions[:request.limit]

                if sessions_to_generate:
                    try:
                        schedule_batch_review_generation(
                            session_ids=sessions_to_generate,
                            config={
                                "api_key": request.api_key,
                                "base_url": request.base_url,
                                "model": request.model,
                            },
                            batch_key=batch_key
                        )
                        generation_in_progress = True
                        logger.info(f"Triggered batch review generation for {len(sessions_to_generate)} sessions")
                    except Exception as e:
                        logger.error(f"Failed to schedule batch review: {e}")

                    # Invalidate integrated cache so next aggregation picks up fresh data
                    if cached_integrated:
                        try:
                            cached_integrated.review_groups = []
                            db.commit()
                            logger.info(f"Invalidated integrated cache for {request.days}d (background regeneration)")
                        except Exception as e:
                            logger.warning(f"Failed to invalidate cache: {e}")
                            db.rollback()
        else:
            batch_progress = get_batch_progress(batch_key)
            logger.info(f"Batch '{batch_key}' already active ({batch_progress.get('completed', 0)}/{batch_progress.get('total', 0)}), skipping trigger")

        # Also handle 7-30 day range: trigger node-based generation
        if request.days > 7:
            try:
                config = {
                    "api_key": request.api_key,
                    "base_url": request.base_url,
                    "model": request.model,
                    "priority": 10
                }
                schedule_integrated_review_generation(days=request.days, config=config)
                logger.info(f"Triggered background node-based review for {request.days}d")
            except Exception as e:
                logger.error(f"Failed to trigger 7-30d generation: {e}")

        # ── 5. Always return data ──────────────────────────────────────
        display_data["generation_in_progress"] = generation_in_progress
        if generation_in_progress:
            display_data["batch_progress"] = get_batch_progress(batch_key)
        return display_data

    except Exception as e:
        logger.error(f"Error generating integrated review: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate integrated review: {str(e)}"
        )


@router.get("/review/integrated/status")
async def get_integrated_review_status(
    days: int = Query(default=7, ge=1, le=30, description="Time range in days"),
    db: Session = Depends(get_db)
):
    """Check the status of integrated review generation for a specific time range"""
    try:
        logger.info(f"Checking integrated review status for {days} days")

        # Check for valid cached data
        cached_review = crud.get_valid_integrated_review_data(db, days)
        if cached_review:
            return {
                "days": days,
                "status": "completed",
                "generated_at": cached_review.generated_at.isoformat() if cached_review.generated_at else None,
                "expires_at": cached_review.expires_at.isoformat() if cached_review.expires_at else None,
                "total_groups": len(cached_review.review_groups or []),
                "total_knowledge_cards": sum(len(g.get("knowledge_cards", [])) for g in (cached_review.review_groups or [])),
                "total_quiz_questions": sum(len(g.get("quiz_questions", [])) for g in (cached_review.review_groups or [])),
                "has_cache": True
            }

        # Check if generation is in progress
        review_data = db.query(ReviewData).filter(
            ReviewData.generation_type == "integrated",
            ReviewData.time_range_days == days
        ).first()

        if review_data:
            return {
                "days": days,
                "status": review_data.generation_status if review_data.generation_status else "not_started",
                "has_cache": False,
                "last_attempt_at": review_data.last_attempt_at.isoformat() if review_data.last_attempt_at else None,
                "error_message": review_data.error_message
            }

        return {
            "days": days,
            "status": "not_started",
            "has_cache": False,
            "message": "No integrated review data found for this time range"
        }

    except Exception as e:
        logger.error(f"Error checking integrated review status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/review/integrated/progress")
async def get_integrated_review_progress(
    days: int = Query(default=7, ge=1, le=30, description="Time range in days"),
    db: Session = Depends(get_db)
):
    """Get saved progress for an integrated review"""
    try:
        review_data = db.query(ReviewData).filter(
            ReviewData.generation_type == "integrated",
            ReviewData.time_range_days == days
        ).first()

        if not review_data:
            return {
                "learned_cards": [],
                "completed_quizzes": [],
                "review_count": 0
            }

        return {
            "learned_cards": review_data.learned_cards or [],
            "completed_quizzes": review_data.completed_quizzes or [],
            "review_count": review_data.review_count or 0,
            "last_reviewed_at": review_data.last_reviewed_at.isoformat() if review_data.last_reviewed_at else None
        }

    except Exception as e:
        logger.error(f"Error getting integrated review progress: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/review/integrated/progress")
async def save_integrated_review_progress(
    request: IntegratedReviewProgressRequest,
    db: Session = Depends(get_db)
):
    """Save progress for integrated review (learned cards and completed quizzes)"""
    try:
        logger.info(f"Saving integrated review progress for {request.days} days: "
                   f"{len(request.learned_cards)} learned cards, "
                   f"{len(request.completed_quizzes)} completed quizzes")

        review_data = db.query(ReviewData).filter(
            ReviewData.generation_type == "integrated",
            ReviewData.time_range_days == request.days
        ).first()

        if not review_data:
            raise HTTPException(status_code=404, detail="No integrated review data found for this time range")

        # Update progress fields
        review_data.learned_cards = request.learned_cards
        review_data.completed_quizzes = request.completed_quizzes
        review_data.last_reviewed_at = datetime.utcnow()
        if review_data.review_count is None:
            review_data.review_count = 0
        review_data.review_count += 1

        db.commit()

        return {
            "success": True,
            "learned_cards": len(request.learned_cards),
            "completed_quizzes": len(request.completed_quizzes),
            "review_count": review_data.review_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving integrated review progress: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/review/integrated/sessions")
async def get_sessions_with_reviews(
    days: int = Query(default=7, ge=1, le=30, description="Look back days"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum sessions to return"),
    db: Session = Depends(get_db)
):
    """Get list of sessions that have valid review data"""
    try:
        logger.info(f"Getting sessions with reviews: days={days}, limit={limit}")

        # Get recent valid reviews
        review_data_list = crud.get_recent_valid_reviews(db, limit=limit, days=days)

        sessions = []
        for review_data in review_data_list:
            # Handle datetime fields with explicit None checks
            generated_at_value = review_data.generated_at
            expires_at_value = review_data.expires_at

            generated_at_iso = generated_at_value.isoformat() if generated_at_value is not None else None
            expires_at_iso = expires_at_value.isoformat() if expires_at_value is not None else None

            # Handle JSON fields safely
            generation_config = review_data.generation_config
            message_count = 0
            if generation_config is not None and isinstance(generation_config, dict):
                message_count = generation_config.get("message_count", 0)

            review_groups = review_data.review_groups
            if review_groups is None:
                review_groups = []

            session_info = {
                "session_id": review_data.session_id,
                "generated_at": generated_at_iso,
                "expires_at": expires_at_iso,
                "message_count": message_count,
                "total_groups": len(review_groups),
                "total_knowledge_cards": sum(len(g.get("knowledge_cards", [])) for g in review_groups),
                "total_quiz_questions": sum(len(g.get("quiz_questions", [])) for g in review_groups)
            }
            sessions.append(session_info)

        return {
            "sessions": sessions,
            "total_sessions": len(sessions),
            "days": days,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting sessions with reviews: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")