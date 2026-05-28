"""Generate graph data for frontend visualization from Neo4j"""

import logging
from typing import Dict, Any, List
from backend.graph_db.neo4j_client import get_driver

logger = logging.getLogger(__name__)


class GraphGenerator:
    """Generate graph data from Neo4j for frontend visualization"""

    def __init__(self):
        self.initialized = True
        logger.info("GraphGenerator initialized")

    def _map_entity_type(self, entity_type: str) -> str:
        """Map entity type to group for visualization"""
        type_map = {
            "concept": "concept",
            "technique": "technique",
            "application": "application",
            "person": "person",
            "organization": "organization",
            "tool": "tool",
            "location": "location",
            "event": "event",
        }
        return type_map.get(entity_type.lower(), "default")

    def _get_group_color(self, group: str) -> str:
        """Get color for entity group"""
        color_map = {
            "concept": "#A99BC8",      # Soft lavender
            "technique": "#8BB8D9",    # Soft sky blue
            "application": "#8FC9A8",  # Soft sage
            "person": "#E8B88A",       # Soft peach
            "organization": "#D9A0A0", # Soft rose
            "tool": "#C8A8D8",         # Soft lilac
            "location": "#8FC9C0",     # Soft teal
            "event": "#D9C888",        # Soft gold
            "default": "#B8B8B8",      # Soft gray
        }
        return color_map.get(group, "#B8B8B8")

    def generate_session_graph(self, session_id: str, min_importance: float = 2.0) -> Dict[str, Any]:
        """Generate graph data for a specific session from Neo4j.

        Args:
            session_id: The session to generate graph for.
            min_importance: Minimum importance_score to include an entity (default 2.0).
                            Set to 0 to show all entities.
        """
        logger.debug(f"Generating graph for session: {session_id}")

        driver = get_driver()
        if not driver:
            logger.warning("Neo4j driver not available, returning empty graph")
            return {
                "nodes": [],
                "edges": [],
                "session_id": session_id,
            }

        try:
            with driver.session() as session:
                # Get entities for this session (entities mentioned in this session)
                entities_result = session.run("""
                    MATCH (e:Entity)
                    WHERE $session_id IN e.session_ids
                    RETURN e.name as name, e.type as type, e.description as description,
                           e.mention_count as mention_count, e.importance_score as importance_score,
                           e.session_ids as session_ids, e.importance_scores as importance_scores
                """, session_id=session_id)

                entities = []
                entity_map = {}  # name -> id mapping
                next_id = 1

                for record in entities_result:
                    name = record["name"]
                    entity_type = record["type"]
                    description = record["description"]
                    mention_count = record["mention_count"] or 1
                    importance_score = record["importance_score"] or 1.0
                    session_ids = record["session_ids"] or []
                    importance_scores = record["importance_scores"] or []

                    # Get session-specific importance score for filtering
                    session_importance = importance_score  # fallback to aggregate
                    if session_id in session_ids and importance_scores:
                        sidx = session_ids.index(session_id)
                        if sidx < len(importance_scores):
                            session_importance = importance_scores[sidx]

                    # Filter out low-importance entities for a cleaner graph
                    if min_importance > 0 and session_importance < min_importance:
                        continue

                    entity_map[name] = next_id
                    next_id += 1

                    entities.append({
                        "id": next_id - 1,
                        "label": name,
                        "group": self._map_entity_type(entity_type),
                        "title": description or name,
                        "color": self._get_group_color(entity_type),
                        "value": mention_count * importance_score,  # for node size in vis-network
                        "mention_count": mention_count,  # custom property for frontend
                        "importance": importance_score,  # aggregate importance score (1-5)
                    })

                # Get relationships for these entities (relationships created in this session)
                relationships_result = session.run("""
                    MATCH (source:Entity)-[r:RELATED_TO]->(target:Entity)
                    WHERE $session_id IN r.session_ids
                    RETURN source.name as source_name, target.name as target_name,
                           r.type as rel_type, r.description as description
                """, session_id=session_id)

                edges = []
                for record in relationships_result:
                    source_name = record["source_name"]
                    target_name = record["target_name"]
                    rel_type = record["rel_type"]
                    description = record["description"]

                    source_id = entity_map.get(source_name)
                    target_id = entity_map.get(target_name)

                    if source_id and target_id:
                        edges.append({
                            "from": source_id,
                            "to": target_id,
                            "label": rel_type.lower() if rel_type else "related_to",
                            "title": description or f"{source_name} -> {target_name}",
                        })

                logger.info(f"Generated graph with {len(entities)} nodes and {len(edges)} edges for session {session_id}")

                return {
                    "nodes": entities,
                    "edges": edges,
                    "session_id": session_id,
                }

        except Exception as e:
            logger.error(f"Error generating session graph: {e}")
            return {
                "nodes": [],
                "edges": [],
                "session_id": session_id,
            }

    def get_entities_for_sessions(self, session_ids: List[str]) -> List[Dict[str, Any]]:
        """Get all entities associated with given session IDs"""
        logger.debug(f"Getting entities for {len(session_ids)} sessions")

        driver = get_driver()
        if not driver:
            logger.warning("Neo4j driver not available, returning empty list")
            return []

        try:
            with driver.session() as session:
                # Get entities for these sessions
                result = session.run("""
                    MATCH (e:Entity)
                    WHERE ANY(sid IN e.session_ids WHERE sid IN $session_ids)
                    RETURN DISTINCT e.name as name, e.type as type, e.description as description,
                           e.mention_count as mention_count, e.importance_score as importance_score,
                           e.session_ids as session_ids, e.importance_scores as importance_scores
                    ORDER BY e.mention_count DESC, e.importance_score DESC
                """, session_ids=session_ids)

                entities = []
                for record in result:
                    name = record["name"]
                    entity_type = record["type"]
                    description = record["description"]
                    mention_count = record["mention_count"] or 1
                    importance_score = record["importance_score"] or 1.0
                    session_ids_list = record["session_ids"] or []
                    importance_scores = record["importance_scores"] or []

                    # Calculate average importance from importance_scores if available
                    avg_importance = importance_score
                    if importance_scores and len(importance_scores) > 0:
                        avg_importance = sum(importance_scores) / len(importance_scores)

                    entities.append({
                        "name": name,
                        "type": entity_type,
                        "description": description,
                        "mention_count": mention_count,
                        "importance_score": avg_importance,
                        "session_ids": session_ids_list,
                        "importance_scores": importance_scores,
                        "recent_session_count": len([sid for sid in session_ids_list if sid in session_ids])
                    })

                logger.info(f"Found {len(entities)} entities for {len(session_ids)} sessions")
                return entities

        except Exception as e:
            logger.error(f"Error getting entities for sessions: {e}")
            return []

    def generate_global_graph(self, limit: int = 100, min_importance: float = 2.0) -> Dict[str, Any]:
        """Generate graph data for all sessions from Neo4j.

        Args:
            limit: Maximum number of entities to return.
            min_importance: Minimum importance_score to include an entity (default 2.0).
        """
        logger.debug(f"Generating global graph with limit: {limit}")

        driver = get_driver()
        if not driver:
            logger.warning("Neo4j driver not available, returning empty graph")
            return {
                "nodes": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "session_id": "global",
            }

        try:
            with driver.session() as session:
                # Get all entities (limited, filtered by importance)
                entities_result = session.run("""
                    MATCH (e:Entity)
                    WHERE e.importance_score >= $min_importance
                    RETURN e.name as name, e.type as type, e.description as description, e.mention_count as mention_count, e.importance_score as importance
                    ORDER BY e.mention_count DESC, e.importance_score DESC
                    LIMIT $limit
                """, limit=limit, min_importance=min_importance)

                entities = []
                entity_map = {}
                next_id = 1

                for record in entities_result:
                    name = record["name"]
                    entity_type = record["type"]
                    description = record["description"]
                    mention_count = record["mention_count"] or 1
                    importance = record["importance"] or 1.0

                    entity_map[name] = next_id
                    next_id += 1

                    entities.append({
                        "id": next_id - 1,
                        "label": name,
                        "group": self._map_entity_type(entity_type),
                        "title": description or name,
                        "color": self._get_group_color(entity_type),
                        "value": mention_count * importance,  # for node size in vis-network
                        "mention_count": mention_count,  # custom property for frontend
                        "importance": importance,  # importance score (1-5)
                    })

                # Get relationships between these entities
                entity_names = list(entity_map.keys())

                relationships_result = session.run("""
                    MATCH (source:Entity)-[r:RELATED_TO]->(target:Entity)
                    WHERE source.name IN $entity_names AND target.name IN $entity_names
                    RETURN source.name as source_name, target.name as target_name,
                           r.type as rel_type, r.description as description
                """, entity_names=entity_names)

                edges = []
                for record in relationships_result:
                    source_name = record["source_name"]
                    target_name = record["target_name"]
                    rel_type = record["rel_type"]
                    description = record["description"]

                    source_id = entity_map.get(source_name)
                    target_id = entity_map.get(target_name)

                    if source_id and target_id:
                        edges.append({
                            "from": source_id,
                            "to": target_id,
                            "label": rel_type.lower() if rel_type else "related_to",
                            "title": description or f"{source_name} -> {target_name}",
                        })

                logger.info(f"Generated global graph with {len(entities)} nodes and {len(edges)} edges")

                return {
                    "nodes": entities,
                    "edges": edges,
                    "total_nodes": len(entities),
                    "total_edges": len(edges),
                    "session_id": "global",
                }

        except Exception as e:
            logger.error(f"Error generating global graph: {e}")
            return {
                "nodes": [],
                "edges": [],
                "total_nodes": 0,
                "total_edges": 0,
                "session_id": "global",
            }

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph"""
        driver = get_driver()
        if not driver:
            return {
                "total_nodes": 0,
                "total_edges": 0,
                "total_sessions": 0,
                "last_updated": None,
            }

        try:
            with driver.session() as session:
                # Count entities
                entities_count = session.run("""
                    MATCH (e:Entity) RETURN count(e) as count
                """).single()["count"]

                # Count relationships
                relationships_count = session.run("""
                    MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count
                """).single()["count"]

                # Count unique sessions (using session_ids list)
                sessions_count = session.run("""
                    MATCH (e:Entity)
                    WHERE size(e.session_ids) > 0
                    UNWIND e.session_ids AS session_id
                    RETURN count(DISTINCT session_id) as count
                """).single()["count"]

                # Get last updated
                last_updated_result = session.run("""
                    MATCH (e:Entity)
                    RETURN max(e.updated_at) as last_updated
                """).single()

                last_updated = last_updated_result["last_updated"]
                if last_updated:
                    last_updated = last_updated.isoformat()

                return {
                    "total_nodes": entities_count,
                    "total_edges": relationships_count,
                    "total_sessions": sessions_count,
                    "last_updated": last_updated,
                }

        except Exception as e:
            logger.error(f"Error getting graph stats: {e}")
            return {
                "total_nodes": 0,
                "total_edges": 0,
                "total_sessions": 0,
                "last_updated": None,
            }


# Global instance
graph_generator = GraphGenerator()
