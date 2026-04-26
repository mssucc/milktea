from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import json
import asyncio
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from backend.database.session import get_db
from backend.database import crud
from backend.llm.chat_handler import chat_handler
from backend.graph_db.knowledge_extractor import knowledge_extractor
from backend.graph_db.neo4j_client import test_connection, get_driver, NEO4J_URI
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

# Track active background knowledge extraction tasks
_active_knowledge_tasks = set()
# Session locks to prevent concurrent knowledge extraction for the same session
_session_locks = {}
logger.info("Knowledge extraction using asyncio tasks (coroutine-based)")

# Neo4j status endpoint
@router.get("/neo4j-status")
async def get_neo4j_status():
    """Check Neo4j database connection status"""
    try:
        is_connected = test_connection()
        if is_connected:
            return {"connected": True, "uri": NEO4J_URI, "message": "Neo4j connection successful"}
        else:
            return {"connected": False, "uri": NEO4J_URI, "message": "Neo4j not connected"}
    except Exception as e:
        return {"connected": False, "uri": NEO4J_URI, "message": f"Neo4j connection failed: {str(e)}"}

# Request/Response Models

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    system_prompt: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True


class SessionInfo(BaseModel):
    session_id: str
    title: Optional[str] = None
    created_at: datetime
    message_count: int

    class Config:
        from_attributes = True

# Routes


async def generate_stream_response(
    request: ChatRequest,
    db: Session
):
    """
    Generator function that yields streamed response chunks and collects full response
    """
    session_id = request.session_id
    full_response = ""
    assistant_message_id = None
    should_update_message = False  # Flag to track if we should update the message

    try:
        # Session ID is provided by frontend (generated for new sessions)
        # crud.create_message will create the session if it doesn't exist
        logger.info(f"Using session for streaming: {session_id}")

        # Save user message to database
        user_message = crud.create_message(
            db,
            session_id=session_id,
            role="user",
            content=request.message
        )
        logger.debug(f"Saved user message for streaming with ID: {user_message.id}")

        # Create AI message placeholder BEFORE streaming starts
        # This ensures the message exists in database even if user switches sessions mid-stream
        # Use empty string as placeholder to avoid confusion with actual response
        assistant_message = crud.create_message(
            db,
            session_id=session_id,
            role="assistant",
            content=""
        )
        logger.debug(f"Created AI message placeholder with ID: {assistant_message.id}")
        assistant_message_id = assistant_message.id
        should_update_message = True  # We should update the message when streaming completes

        # Stream response from chat handler
        async for chunk in chat_handler.stream_response(
            message=request.message,
            session_id=session_id,
            system_prompt=request.system_prompt,
            api_key=request.api_key,
            base_url=request.base_url,
            model=request.model
        ):
            full_response += chunk
            # Yield each chunk as a line (simple format)
            # Use try-except to handle client disconnection gracefully
            try:
                yield chunk
            except Exception as e:
                # Client likely disconnected, log and break out of loop
                logger.info(f"Client disconnected during streaming: {e}")
                break

        logger.debug(f"Streaming completed, full response length: {len(full_response)}")

    except Exception as e:
        import traceback
        logger.error(f"Error in stream response generation: {e}")
        logger.error(traceback.format_exc())
        # Append error to response if we have partial content, or set error message
        error_msg = f"\n\nError: {str(e)}"
        if full_response:
            full_response += error_msg
        else:
            full_response = error_msg
        # Yield error message to client
        yield error_msg
    finally:
        # Always try to update the AI message with whatever response we got
        if should_update_message and assistant_message_id:
            try:
                # Always update, even if response is empty or placeholder
                # This ensures database always has the final response (not just placeholder)
                updated_message = crud.update_message_content(
                    db,
                    assistant_message_id,
                    full_response
                )
                if updated_message:
                    logger.debug(f"Updated AI message content for ID: {assistant_message_id}")
                    logger.info(f"Updated message {assistant_message_id} with response length: {len(full_response)}, content preview: {full_response[:50] if full_response else 'empty'}")
                else:
                    logger.error(f"Failed to update AI message with ID: {assistant_message_id}")
            except Exception as e:
                logger.error(f"Failed to update AI message: {e}")
                # Don't fail the stream, just log the error

        # Signal that streaming is complete by yielding an end marker
        # Use try-except to handle case where client has already disconnected
        try:
            yield "[STREAM_END]"
        except Exception as e:
            # Client likely disconnected, log but don't raise
            logger.debug(f"Could not send STREAM_END marker (client may have disconnected): {e}")

        # Capture variables for background thread
        stream_api_key = request.api_key
        stream_base_url = request.base_url
        stream_model = request.model

        # Extract knowledge in background to not block the stream
        # Using asyncio.create_task for coroutine-based background processing
        async def post_process_conversation(api_key, base_url, model):
            try:
                # Check if session_id is None (should not happen, but be safe)
                if session_id is None:
                    logger.warning("Session ID is None, cannot perform knowledge extraction")
                    return

                # Get or create session lock to prevent concurrent extraction for the same session
                if session_id not in _session_locks:
                    _session_locks[session_id] = asyncio.Lock()

                logger.info(f"Waiting for session lock for session: {session_id}")
                async with _session_locks[session_id]:
                    logger.info(f"Acquired session lock for session: {session_id}")
                    logger.info(f"Stream background knowledge extraction started for session: {session_id}")
                    logger.info(f"Stream background coroutine API config - api_key: {bool(api_key)}, base_url: {base_url}, model: {model}")

                    # Create new database session for knowledge extraction
                    from backend.database.session import SessionLocal
                    db_knowledge = SessionLocal()
                    try:
                        # Get latest conversation round (user + AI messages) for knowledge extraction with retry logic
                        latest_round_messages = []
                        max_retries = 5
                        retry_delay = 0.1  # seconds

                        for attempt in range(max_retries):
                            latest_round_messages = crud.get_latest_conversation_rounds(db_knowledge, session_id, rounds=1)
                            logger.info(f"Stream background coroutine retrieved {len(latest_round_messages)} messages for session {session_id} (attempt {attempt + 1}/{max_retries})")

                            if len(latest_round_messages) >= 2:  # At least user + AI messages (one complete round)
                                break

                            if attempt < max_retries - 1:
                                logger.info(f"Not enough messages for a complete round ({len(latest_round_messages)}), waiting {retry_delay}s before retry")
                                await asyncio.sleep(retry_delay)

                        if not latest_round_messages or len(latest_round_messages) < 2:
                            logger.warning(f"Insufficient messages found in database for session {session_id}: {len(latest_round_messages)} messages")
                            return

                        # Explicitly convert to str to satisfy type checker (SQLAlchemy columns -> str)
                        message_list = [
                            {"role": str(msg.role), "content": str(msg.content)}
                            for msg in latest_round_messages
                        ]
                        logger.info(f"Stream calling knowledge extractor with latest round ({len(message_list)} messages)")

                        # Run knowledge extraction in thread pool to avoid blocking event loop
                        result = await asyncio.to_thread(
                            knowledge_extractor.update_graph_from_conversation,
                            message_list,
                            session_id,
                            api_key=api_key,
                            base_url=base_url,
                            model=model
                        )
                        logger.info(f"Stream knowledge extraction completed for session {session_id}: {result}")
                    except Exception as ke:
                        logger.warning(f"Stream knowledge extraction failed: {ke}")
                        import traceback
                        logger.warning(traceback.format_exc())
                    finally:
                        db_knowledge.close()
            except Exception as e:
                logger.error(f"Stream post-processing failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
            finally:
                # Remove task from tracking set when done
                task = asyncio.current_task()
                _active_knowledge_tasks.discard(task)

        # Run post-processing in background using asyncio task
        task = asyncio.create_task(
            post_process_conversation(stream_api_key, stream_base_url, stream_model)
        )
        _active_knowledge_tasks.add(task)

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Stream chat response with real-time token delivery
    """
    logger.info(f"Stream chat request for session: {request.session_id}, message length: {len(request.message)}")
    logger.info(f"Stream request details - api_key provided: {bool(request.api_key)}, base_url: {request.base_url}, model: {request.model}")

    # Return streaming response
    return StreamingResponse(
        generate_stream_response(request, db),
        media_type="text/plain; charset=utf-8"
    )

@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all chat sessions"""
    try:
        sessions = crud.get_all_sessions(db, limit=limit)
        result = []
        for session in sessions:
            message_count = crud.get_message_count(db, session.id)
            result.append(SessionInfo(
                session_id=session.id,
                title=session.title,
                created_at=session.created_at,
                message_count=message_count
            ))
        return result
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/sessions/{session_id}/messages", response_model=List[Message])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all messages for a specific session"""
    try:
        messages = crud.get_messages_by_session(db, session_id, limit=limit)
        return [
            Message(
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp
            )
            for msg in messages
        ]
    except Exception as e:
        logger.error(f"Error getting messages for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Delete a session and all its messages"""
    try:
        success = crud.delete_session(db, session_id)
        if success:
            # Also clear chat handler memory for this session
            chat_handler.clear_memory(session_id)
            return {"message": f"Session {session_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")