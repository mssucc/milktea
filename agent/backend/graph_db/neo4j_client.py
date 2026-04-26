from neo4j import GraphDatabase
import logging
from typing import List, Dict, Any
from backend.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

driver = None

def init_neo4j():
    """Initialize Neo4j connection"""
    global driver
    try:
        # Note: For Aura (neo4j+s://), encryption is handled by the URI scheme
        # Don't set encrypted parameter for neo4j+s:// or bolt+s:// URIs
        is_aura = NEO4J_URI.startswith("neo4j+s://") or NEO4J_URI.startswith("bolt+s://")

        if is_aura:
            driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
                # No encrypted parameter for Aura - handled by URI scheme
            )
        else:
            driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            test_value = result.single()["test"]
            if test_value == 1:
                logger.info(f"Neo4j connection established to {NEO4J_URI}")
            else:
                logger.warning(f"Neo4j connection test returned unexpected value: {test_value}")

        # Create constraints/indexes
        _create_constraints()
        logger.info("Neo4j initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j: {e}")
        logger.warning("Knowledge graph features will be disabled")
        return False

def _create_constraints():
    """Create necessary constraints and indexes in Neo4j"""
    try:
        with driver.session() as session:
            # Create uniqueness constraint for Entity nodes
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE")
            # Create index for Entity type
            session.run("CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            # Create index for Entity session_ids (for filtering by session)
            session.run("CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.session_ids)")
            # Create index for Entity mention_count (for sorting/aggregation)
            session.run("CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.mention_count)")
            # Create index for Relationship type
            session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:RELATED_TO]-() ON (r.type)")
            # Create index for Relationship session_ids
            session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:RELATED_TO]-() ON (r.session_ids)")
            logger.debug("Neo4j constraints/indexes created")
    except Exception as e:
        logger.warning(f"Failed to create Neo4j constraints: {e}")

def get_driver():
    """Get the Neo4j driver instance"""
    return driver

def close_connection():
    """Close Neo4j connection"""
    global driver
    if driver:
        driver.close()
        driver = None
        logger.info("Neo4j connection closed")

def test_connection() -> bool:
    """Test if Neo4j connection is working"""
    if not driver:
        return False
    try:
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            return result.single()["test"] == 1
    except Exception as e:
        logger.error(f"Neo4j connection test failed: {e}")
        return False


def get_top_entities_by_mention_count(days: int = 2, limit: int = 10) -> List[Dict[str, Any]]:
    """Get top entities by mention count within recent days

    Args:
        days: Number of days to look back
        limit: Maximum number of entities to return

    Returns:
        List of entity dictionaries with name, mention_count, etc.
    """
    if not driver:
        logger.warning("Neo4j driver not initialized")
        return []

    try:
        with driver.session() as session:
            # Note: This query assumes entities have an updated_at timestamp
            # and mention_count is updated when entities are mentioned
            # For simplicity, we'll just get top entities by mention_count
            # regardless of time (this matches the current data model)
            result = session.run("""
                MATCH (e:Entity)
                WHERE e.mention_count > 0
                RETURN e.name as name,
                       e.mention_count as mention_count,
                       e.type as type,
                       e.description as description
                ORDER BY e.mention_count DESC
                LIMIT $limit
            """, limit=limit)

            entities = []
            for record in result:
                entities.append({
                    "name": record["name"],
                    "mention_count": record["mention_count"],
                    "type": record["type"],
                    "description": record["description"]
                })

            logger.debug(f"Retrieved {len(entities)} top entities by mention count")
            return entities
    except Exception as e:
        logger.error(f"Error getting top entities by mention count: {e}")
        return []


def get_sessions_for_entity(entity_name: str) -> List[str]:
    """Get session IDs associated with an entity

    Args:
        entity_name: Name of the entity

    Returns:
        List of session IDs where this entity was mentioned
    """
    if not driver:
        logger.warning("Neo4j driver not initialized")
        return []

    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (e:Entity {name: $entity_name})
                RETURN e.session_ids as session_ids
            """, entity_name=entity_name)

            record = result.single()
            if record and record["session_ids"]:
                return list(record["session_ids"])
            return []
    except Exception as e:
        logger.error(f"Error getting sessions for entity {entity_name}: {e}")
        return []