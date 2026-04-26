from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import asyncio
import time

from backend.graph_db.graph_generator import graph_generator
from backend.graph_db.knowledge_extractor import knowledge_extractor
from backend.graph_db.neo4j_client import test_connection, get_driver, NEO4J_URI
from backend.database.session import get_db
from backend.database import crud
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()

# Response Models

class Neo4jDiagnosticsResponse(BaseModel):
    connected: bool
    total_entities: int
    total_relationships: int
    sessions_with_data: List[str]
    recent_entities: List[Dict[str, Any]]
    message: str

class GraphNode(BaseModel):
    id: int
    label: str
    group: str
    title: str
    value: Optional[float] = None
    mention_count: Optional[int] = None
    importance: Optional[float] = None

class GraphEdge(BaseModel):
    from_node: int = Field(alias="from")
    to: int
    label: str
    title: str

    class Config:
        populate_by_name = True

class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    session_id: str

class Neo4jStatusResponse(BaseModel):
    connected: bool
    uri: str
    message: str

class ReanalysisRequest(BaseModel):
    limit: Optional[int] = 50
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None

class ReanalysisResponse(BaseModel):
    session_id: str
    message: str
    total_messages: int
    entities_extracted: int
    relationships_extracted: int
    elapsed_time: float

# Routes - Order matters: specific routes first, parameterized routes last

@router.get("/graph/system/neo4j-status", response_model=Neo4jStatusResponse)
async def get_neo4j_status():
    """Check Neo4j database connection status"""
    try:
        is_connected = test_connection()
        driver = get_driver()

        if is_connected:
            return Neo4jStatusResponse(
                connected=True,
                uri=NEO4J_URI,
                message="Neo4j connection successful"
            )
        else:
            return Neo4jStatusResponse(
                connected=False,
                uri=NEO4J_URI,
                message="Neo4j not connected. Please check your configuration."
            )
    except Exception as e:
        logger.error(f"Error checking Neo4j status: {e}")
        return Neo4jStatusResponse(
            connected=False,
            uri=NEO4J_URI,
            message=f"Neo4j connection failed: {str(e)}"
        )

@router.get("/graph/stats")
async def get_graph_stats():
    """Get statistics about the knowledge graph"""
    try:
        stats = graph_generator.get_graph_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting graph stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/graph/global", response_model=GraphResponse)
async def get_global_graph(limit: int = 100):
    """
    Get global knowledge graph across all sessions
    """
    try:
        logger.info(f"Getting global graph with limit: {limit}")
        graph_data = graph_generator.generate_global_graph(limit)
        return GraphResponse(**graph_data)
    except Exception as e:
        logger.error(f"Error generating global graph: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate global graph: {str(e)}"
        )

@router.get("/graph/diagnostics/{session_id}", response_model=Neo4jDiagnosticsResponse)
async def diagnose_session_graph(session_id: str):
    """
    Diagnose Neo4j data for a specific session - check what's actually stored
    If session_id is 'global', return data for all sessions
    MUST be defined BEFORE /graph/{session_id} to avoid routing conflicts
    """
    try:
        driver = get_driver()
        if not driver:
            return Neo4jDiagnosticsResponse(
                connected=False,
                total_entities=0,
                total_relationships=0,
                sessions_with_data=[],
                recent_entities=[],
                message="Neo4j driver not available"
            )

        with driver.session() as session:
            # Check connection
            result = session.run("RETURN 1 as test")
            connected = result.single()["test"] == 1

            # Check if querying all sessions (global) or specific session
            is_global = session_id in ['global', 'all', '']

            if is_global:
                # Count all entities
                entity_count = session.run("""
                    MATCH (e:Entity)
                    RETURN count(e) as count
                """).single()["count"]

                # Count all relationships
                rel_count = session.run("""
                    MATCH ()-[r:RELATED_TO]->()
                    RETURN count(r) as count
                """).single()["count"]

                # Get recent entities from all sessions
                recent = session.run("""
                    MATCH (e:Entity)
                    RETURN e.name as name, e.type as type, e.description as description
                    LIMIT 10
                """)
            else:
                # Count entities for this session
                entity_count = session.run("""
                    MATCH (e:Entity)
                    WHERE $session_id IN e.session_ids
                    RETURN count(e) as count
                """, session_id=session_id).single()["count"]

                # Count relationships for this session
                rel_count = session.run("""
                    MATCH ()-[r:RELATED_TO]->()
                    WHERE $session_id IN r.session_ids
                    RETURN count(r) as count
                """, session_id=session_id).single()["count"]

                # Get recent entities for this session
                recent = session.run("""
                    MATCH (e:Entity)
                    WHERE $session_id IN e.session_ids
                    RETURN e.name as name, e.type as type, e.description as description
                    LIMIT 10
                """, session_id=session_id)

            recent_entities = [{
                "name": record["name"],
                "type": record["type"],
                "description": record["description"]
            } for record in recent]

            # Get all sessions with data
            sessions_result = session.run("""
                MATCH (e:Entity)
                WHERE size(e.session_ids) > 0
                UNWIND e.session_ids AS session_id
                WITH DISTINCT session_id
                RETURN session_id
                LIMIT 20
            """)
            sessions_with_data = [record["session_id"] for record in sessions_result]

            if is_global:
                message = f"Total: {entity_count} entities and {rel_count} relationships across {len(sessions_with_data)} sessions"
            else:
                message = f"Found {entity_count} entities and {rel_count} relationships for session {session_id[:8]}..."

            return Neo4jDiagnosticsResponse(
                connected=connected,
                total_entities=entity_count,
                total_relationships=rel_count,
                sessions_with_data=sessions_with_data,
                recent_entities=recent_entities,
                message=message
            )

    except Exception as e:
        logger.error(f"Error diagnosing session {session_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Neo4jDiagnosticsResponse(
            connected=False,
            total_entities=0,
            total_relationships=0,
            sessions_with_data=[],
            recent_entities=[],
            message=f"Error: {str(e)}"
        )

@router.post("/graph/{session_id}/reanalyze", response_model=ReanalysisResponse)
async def reanalyze_session_graph(
    session_id: str,
    request: ReanalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Manually reanalyze the entire conversation history for a session
    This performs full analysis of the conversation (not just incremental)
    Useful when the conversation context has changed significantly
    Uses the same API configuration as chat responses (from frontend config)
    """
    start_time = time.time()
    logger.info(f"Manual reanalysis requested for session {session_id} with limit {request.limit}")
    logger.info(f"API config - api_key: {bool(request.api_key)}, base_url: {request.base_url}, model: {request.model}")

    try:
        # Get full conversation history (or up to limit)
        all_messages = crud.get_messages_by_session(db, session_id, limit=request.limit)
        logger.info(f"Retrieved {len(all_messages)} messages for reanalysis")

        if len(all_messages) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient messages for reanalysis: {len(all_messages)} messages"
            )

        message_list = [
            {"role": msg.role, "content": msg.content}
            for msg in all_messages
        ]

        # First, remove existing contributions from this session to avoid duplicates
        logger.info(f"Removing existing knowledge graph contributions for session {session_id}")
        removal_result = await asyncio.to_thread(
            knowledge_extractor.remove_session_contributions,
            session_id
        )
        logger.info(f"Removal result: {removal_result}")

        # Run knowledge extraction in thread pool (can be long-running)
        # Use frontend-provided API configuration (same as chat responses)
        result = await asyncio.to_thread(
            knowledge_extractor.update_graph_from_conversation,
            message_list,
            session_id,
            api_key=request.api_key,
            base_url=request.base_url,
            model=request.model
        )

        elapsed_time = time.time() - start_time
        logger.info(f"Manual reanalysis completed for session {session_id}: {result}, took {elapsed_time:.2f}s")

        return ReanalysisResponse(
            session_id=session_id,
            message=f"Successfully reanalyzed {len(all_messages)} messages",
            total_messages=len(all_messages),
            entities_extracted=result.get("entities_added", 0),
            relationships_extracted=result.get("relationships_added", 0),
            elapsed_time=elapsed_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during manual reanalysis for session {session_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reanalyze session: {str(e)}"
        )


@router.get("/graph/{session_id}", response_model=GraphResponse)
async def get_session_graph(session_id: str):
    """
    Get knowledge graph for a specific session
    """
    try:
        logger.info(f"Getting graph for session: {session_id}")
        graph_data = graph_generator.generate_session_graph(session_id)
        return GraphResponse(**graph_data)
    except Exception as e:
        logger.error(f"Error generating graph for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate graph: {str(e)}"
        )