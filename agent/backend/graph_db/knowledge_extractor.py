"""Entity and relationship extraction from conversations using LLM"""

import logging
import json
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from backend.graph_db.neo4j_client import get_driver
from backend.database.session import SessionLocal
from backend.database.model import Session as ChatSession

logger = logging.getLogger(__name__)

KNOWLEDGE_EXTRACTION_PROMPT = """You are a knowledge extraction expert. Analyze the following conversation and extract a session title, entities, and relationships.

Instructions:
1. Generate a concise session_title (5-15 characters) that summarizes the core topic of this conversation.
2. Identify key entities (concepts, people, organizations, techniques, applications, etc.)
3. Identify relationships between these entities
4. Assess importance of each entity using the 1-5 scale below, following the DISTRIBUTION GUIDE.
5. Return the result in valid JSON format

Importance scale (1-5):
- 5 (core topic): The most central concepts of the conversation. Should be about 10%-15% of all entities.
- 4 (important): Important supporting concepts. Should be about 15%-25% of all entities.
- 3 (related): Related concepts that provide context. Should be about 30%-40% of all entities.
- 2 (mentioned): Briefly mentioned concepts.
- 1 (peripheral): Edge mentions/tangential references.

IMPORTANT: Follow the distribution percentages above. Not all entities should be importance 4 or 5.

Entity types to identify:
- concept: Abstract concepts, theories, ideas (e.g., "machine learning", "neural network")
- technique: Methods, algorithms, approaches (e.g., "backpropagation", "CNN")
- application: Real-world applications (e.g., "image recognition", "NLP")
- person: People mentioned (e.g., "Alan Turing")
- organization: Companies, institutions (e.g., "OpenAI", "Google")
- tool: Software, frameworks, libraries (e.g., "PyTorch", "TensorFlow")

Relationship types:
- includes: One concept includes/contains another (e.g., "AI includes Machine Learning")
- uses: One technique uses another (e.g., "Deep Learning uses Backpropagation")
- applies_to: Application applies to a domain (e.g., "CNN applies_to Image Recognition")
- related_to: General relationship
- implements: Tool implements a technique (e.g., "PyTorch implements Neural Networks")
- developed_by: Entity developed by person/organization

Return format (strict JSON):
{
    "session_title": "Short title (5-15 chars)",
    "entities": [
        {"name": "Entity Name", "type": "concept|technique|application|person|organization|tool", "description": "Brief description", "importance": 1-5}
    ],
    "relationships": [
        {"source": "Source Entity", "target": "Target Entity", "type": "relationship_type", "description": "Brief description"}
    ]
}

If no entities or relationships are found, return empty arrays.

Conversation to analyze:
"""

class KnowledgeExtractor:
    """Extract entities and relationships from text using LLM"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.initialized = True
        self.llm = None
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._init_llm()
        logger.info("KnowledgeExtractor initialized")

    def _init_llm(self):
        """Initialize the LLM for knowledge extraction"""
        try:
            # Update instance variables with defaults if not set
            self.api_key = self.api_key or OPENAI_API_KEY
            self.base_url = self.base_url or OPENAI_BASE_URL
            self.model = self.model or OPENAI_MODEL

            self.llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.3,  # Lower temperature for more consistent extraction
                max_tokens=1024,
            )
            logger.debug(f"Knowledge extraction LLM initialized: {self.model} at {self.base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize knowledge extraction LLM: {e}")
            self.llm = None

    def update_config(self, api_key: str = None, base_url: str = None, model: str = None):
        """Update LLM configuration and reinitialize"""
        if api_key is not None:
            self.api_key = api_key
        if base_url is not None:
            self.base_url = base_url
        if model is not None:
            self.model = model
        self._init_llm()

    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """Format conversation messages for analysis"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{role.upper()}: {content}")
        return "\n\n".join(formatted)

    def extract_from_conversation(self, messages: List[Dict[str, str]], session_id: str = None,
                                  api_key: str = None, base_url: str = None, model: str = None) -> Dict[str, Any]:
        """Extract entities and relationships from conversation using LLM"""
        # Convert empty strings to None for API configuration
        clean_api_key = api_key.strip() if api_key and api_key.strip() else None
        clean_base_url = base_url.strip() if base_url and base_url.strip() else None
        clean_model = model.strip() if model and model.strip() else None

        # Use provided API config or fall back to instance config
        use_api_key = clean_api_key if clean_api_key is not None else self.api_key
        use_base_url = clean_base_url if clean_base_url is not None else self.base_url
        use_model = clean_model if clean_model is not None else self.model

        # Create LLM instance for this extraction (avoids config conflicts between sessions)
        try:
            llm = ChatOpenAI(
                api_key=use_api_key,
                base_url=use_base_url,
                model=use_model,
                temperature=0.3,
                max_tokens=1024,
            )
            logger.debug(f"Created LLM instance for extraction: {use_model} at {use_base_url}")
        except Exception as e:
            logger.error(f"Failed to create LLM for extraction: {e}")
            logger.error(f"API config - api_key: {bool(use_api_key)}, base_url: {use_base_url}, model: {use_model}")
            import traceback
            logger.error(traceback.format_exc())
            return {"entities": [], "relationships": [], "session_id": session_id}

        try:
            conversation_text = self._format_conversation(messages)
            logger.info(f"Starting knowledge extraction for session {session_id} with {len(messages)} messages")
            logger.debug(f"Conversation text: {conversation_text[:500]}...")

            # Prepare prompt
            messages_for_llm = [
                SystemMessage(content="You are a knowledge extraction expert. Extract entities and relationships from conversations."),
                HumanMessage(content=KNOWLEDGE_EXTRACTION_PROMPT + conversation_text)
            ]

            # Call LLM
            logger.info(f"Calling LLM for extraction - model: {use_model}, base_url: {use_base_url}")
            response = llm.invoke(messages_for_llm)

            # Parse JSON response
            content = response.content.strip()
            logger.info(f"LLM response received, length: {len(content)}")
            logger.debug(f"Raw LLM response: {content}")

            # Handle markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            # Parse JSON
            try:
                result = json.loads(content)
                logger.info(f"Successfully parsed JSON response")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                logger.warning(f"Response content: {content[:500]}...")
                return {"entities": [], "relationships": [], "session_id": session_id}

            # Parse session_title
            session_title = result.get("session_title", "").strip()
            if session_title:
                logger.info(f"Generated session title: {session_title}")

            # Validate structure
            entities = result.get("entities", [])
            relationships = result.get("relationships", [])

            logger.info(f"Extracted {len(entities)} entities and {len(relationships)} relationships")
            if entities:
                logger.info(f"First few entities: {entities[:3]}")

            return {
                "session_title": session_title,
                "entities": entities,
                "relationships": relationships,
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"Error extracting knowledge: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"entities": [], "relationships": [], "session_id": session_id}

    def _store_in_neo4j(self, extraction_result: Dict[str, Any], session_id: str) -> bool:
        """Store extracted knowledge in Neo4j"""
        driver = get_driver()
        if not driver:
            logger.warning("Neo4j driver not available, skipping storage")
            return False

        entities = extraction_result.get("entities", [])
        relationships = extraction_result.get("relationships", [])

        logger.info(f"Attempting to store {len(entities)} entities and {len(relationships)} relationships for session {session_id}")

        if not entities and not relationships:
            logger.warning("No entities or relationships to store")
            return True

        try:
            with driver.session() as session:
                # Store entities
                stored_entities = 0
                for entity in entities:
                    name = entity.get("name", "").strip()
                    entity_type = entity.get("type", "concept").lower()
                    description = entity.get("description", "")
                    importance = max(1, min(5, entity.get("importance", 1)))  # Clamp to 1-5

                    if not name:
                        logger.warning(f"Skipping entity with empty name: {entity}")
                        continue

                    # Check if entity already exists and get current session_ids and importance_scores
                    existing_query = session.run("""
                        MATCH (e:Entity {name: $name})
                        RETURN e.session_ids as session_ids, e.importance_scores as importance_scores,
                               e.mention_count as mention_count, e.importance_score as importance_score
                    """, name=name)
                    existing_record = existing_query.single()

                    if existing_record:
                        # Entity exists, update with new session contribution
                        current_session_ids = existing_record["session_ids"] or []
                        current_importance_scores = existing_record["importance_scores"] or []
                        current_mention_count = existing_record["mention_count"] or 0
                        current_importance_score = existing_record["importance_score"] or 0.0

                        if session_id in current_session_ids:
                            # Session already contributed, update the importance score for this session
                            idx = current_session_ids.index(session_id)
                            current_importance_scores[idx] = importance
                            # Recalculate overall importance_score as average of all session importance scores
                            new_importance_score = sum(current_importance_scores) / len(current_importance_scores)
                            # Update entity with modified importance_scores
                            update_result = session.run("""
                                MATCH (e:Entity {name: $name})
                                SET e.updated_at = datetime(),
                                    e.importance_scores = $importance_scores,
                                    e.importance_score = $importance_score
                                RETURN e.name as name
                            """, name=name, importance_scores=current_importance_scores,
                                   importance_score=new_importance_score)
                        else:
                            # New session contribution
                            new_session_ids = current_session_ids + [session_id]
                            new_importance_scores = current_importance_scores + [importance]
                            new_mention_count = current_mention_count + 1
                            # Calculate new importance_score as weighted average
                            # (current_importance_score * current_mention_count + importance) / new_mention_count
                            new_importance_score = (current_importance_score * current_mention_count + importance) / new_mention_count

                            update_result = session.run("""
                                MATCH (e:Entity {name: $name})
                                SET e.updated_at = datetime(),
                                    e.session_ids = $session_ids,
                                    e.importance_scores = $importance_scores,
                                    e.mention_count = $mention_count,
                                    e.importance_score = $importance_score
                                RETURN e.name as name
                            """, name=name, session_ids=new_session_ids, importance_scores=new_importance_scores,
                                   mention_count=new_mention_count, importance_score=new_importance_score)
                        record = update_result.single()
                    else:
                        # Create new entity
                        create_result = session.run("""
                            CREATE (e:Entity {
                                name: $name,
                                type: $type,
                                description: $description,
                                created_at: datetime(),
                                session_ids: [$session_id],
                                importance_scores: [$importance],
                                mention_count: 1,
                                importance_score: $importance
                            })
                            RETURN e.name as name
                        """, name=name, type=entity_type, description=description,
                               session_id=session_id, importance=importance)
                        record = create_result.single()

                    if record:
                        stored_entities += 1
                        logger.debug(f"Stored entity: {record['name']}")

                # Store relationships
                stored_rels = 0
                for rel in relationships:
                    source = rel.get("source", "").strip()
                    target = rel.get("target", "").strip()
                    rel_type = rel.get("type", "related_to").upper()
                    description = rel.get("description", "")

                    if not source or not target:
                        logger.warning(f"Skipping relationship with empty source/target: {rel}")
                        continue

                    # Create relationship
                    result = session.run("""
                        MATCH (source:Entity {name: $source_name})
                        MATCH (target:Entity {name: $target_name})
                        MERGE (source)-[r:RELATED_TO {type: $rel_type}]->(target)
                        ON CREATE SET
                            r.description = $description,
                            r.created_at = datetime(),
                            r.session_ids = [$session_id]
                        ON MATCH SET
                            r.updated_at = datetime(),
                            r.session_ids = CASE
                                WHEN NOT $session_id IN r.session_ids
                                THEN r.session_ids + $session_id
                                ELSE r.session_ids
                            END
                        RETURN source.name as source, target.name as target
                    """, source_name=source, target_name=target, rel_type=rel_type,
                        description=description, session_id=session_id)
                    record = result.single()
                    if record:
                        stored_rels += 1
                        logger.debug(f"Stored relationship: {record['source']} -> {record['target']}")

            logger.info(f"Successfully stored {stored_entities} entities and {stored_rels} relationships in Neo4j for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing knowledge in Neo4j: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def remove_session_contributions(self, session_id: str) -> Dict[str, Any]:
        """
        Remove all contributions from a session from the knowledge graph.
        Removes session_id from entity session_ids and importance_scores arrays,
        adjusts mention_count and importance_score, and deletes orphaned nodes/relationships.
        """
        driver = get_driver()
        if not driver:
            logger.warning("Neo4j driver not available, skipping removal")
            return {"entities_removed": 0, "relationships_removed": 0, "session_id": session_id}

        try:
            with driver.session() as session:
                # Update entities: remove session_id from session_ids and corresponding importance_scores
                # First, get all entities with this session_id
                result = session.run("""
                    MATCH (e:Entity)
                    WHERE $session_id IN e.session_ids
                    RETURN e.name as name, e.session_ids as session_ids, e.importance_scores as importance_scores
                """, session_id=session_id)
                entities_to_update = []
                for record in result:
                    name = record["name"]
                    session_ids = record["session_ids"] or []
                    importance_scores = record["importance_scores"] or []

                    if session_id not in session_ids:
                        continue

                    # Find index of session_id
                    idx = session_ids.index(session_id)
                    new_session_ids = [sid for sid in session_ids if sid != session_id]
                    new_importance_scores = []
                    if importance_scores and len(importance_scores) == len(session_ids):
                        # Remove corresponding importance score
                        new_importance_scores = [importance_scores[i] for i in range(len(importance_scores)) if i != idx]
                    else:
                        # importance_scores missing or misaligned, create empty array
                        # Importance score will be recalculated based on remaining sessions
                        new_importance_scores = []

                    entities_to_update.append({
                        "name": name,
                        "new_session_ids": new_session_ids,
                        "new_importance_scores": new_importance_scores
                    })

                # Update each entity
                entities_updated = 0
                for entity in entities_to_update:
                    # Calculate new mention_count and importance_score
                    new_session_ids = entity["new_session_ids"]
                    new_importance_scores = entity["new_importance_scores"]
                    new_mention_count = len(new_session_ids)
                    new_importance_score = 0.0
                    if new_importance_scores and len(new_importance_scores) > 0:
                        new_importance_score = sum(new_importance_scores) / len(new_importance_scores)

                    update_result = session.run("""
                        MATCH (e:Entity {name: $name})
                        SET e.session_ids = $session_ids,
                            e.importance_scores = $importance_scores,
                            e.mention_count = $mention_count,
                            e.importance_score = $importance_score,
                            e.updated_at = datetime()
                        RETURN e.name as name
                    """, name=entity["name"],
                       session_ids=new_session_ids,
                       importance_scores=new_importance_scores,
                       mention_count=new_mention_count,
                       importance_score=new_importance_score)
                    if update_result.single():
                        entities_updated += 1

                # Delete entities with empty session_ids and no relationships
                result = session.run("""
                    MATCH (e:Entity)
                    WHERE size(e.session_ids) = 0
                    AND NOT (e)--()
                    DELETE e
                    RETURN count(e) as entities_deleted
                """)
                entities_deleted_record = result.single()
                entities_deleted = entities_deleted_record["entities_deleted"] if entities_deleted_record else 0

                # Remove session_id from relationship session_ids
                result = session.run("""
                    MATCH ()-[r:RELATED_TO]->()
                    WHERE $session_id IN r.session_ids
                    SET r.session_ids = [sid IN r.session_ids WHERE sid <> $session_id]
                    RETURN count(r) as relationships_updated
                """, session_id=session_id)
                relationships_updated_record = result.single()
                relationships_updated = relationships_updated_record["relationships_updated"] if relationships_updated_record else 0

                # Remove relationships with empty session_ids
                result = session.run("""
                    MATCH ()-[r:RELATED_TO]->()
                    WHERE size(r.session_ids) = 0
                    DELETE r
                    RETURN count(r) as relationships_deleted
                """)
                relationships_deleted_record = result.single()
                relationships_deleted = relationships_deleted_record["relationships_deleted"] if relationships_deleted_record else 0

                logger.info(f"Removed session {session_id} contributions: "
                           f"{entities_updated} entities updated, {entities_deleted} entities deleted, "
                           f"{relationships_updated} relationships updated, {relationships_deleted} relationships deleted")

                return {
                    "session_id": session_id,
                    "entities_updated": entities_updated,
                    "entities_deleted": entities_deleted,
                    "relationships_updated": relationships_updated,
                    "relationships_deleted": relationships_deleted,
                    "total_entities_affected": entities_updated + entities_deleted,
                    "total_relationships_affected": relationships_updated + relationships_deleted
                }

        except Exception as e:
            logger.error(f"Error removing session contributions from Neo4j: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"entities_removed": 0, "relationships_removed": 0, "session_id": session_id, "error": str(e)}

    def update_graph_from_conversation(
        self,
        messages: List[Dict[str, str]],
        session_id: str,
        api_key: str = None,
        base_url: str = None,
        model: str = None
    ) -> Dict[str, Any]:
        """Extract knowledge from conversation and update graph"""
        logger.info(f"=== Knowledge Extraction Started ===")
        logger.info(f"Session: {session_id}, Messages: {len(messages)}")
        logger.info(f"API config - api_key: {bool(api_key)}, base_url: {base_url}, model: {model}")

        # Extract knowledge with provided API config (don't update global config)
        extraction_result = self.extract_from_conversation(
            messages,
            session_id,
            api_key=api_key,
            base_url=base_url,
            model=model
        )

        # Check if extraction returned any results
        entities = extraction_result.get("entities", [])
        relationships = extraction_result.get("relationships", [])
        logger.info(f"Extraction result - entities: {len(entities)}, relationships: {len(relationships)}")

        # Update session title if generated
        session_title = extraction_result.get("session_title", "")
        if session_title:
            db_session = None
            try:
                db_session = SessionLocal()
                session_record = db_session.query(ChatSession).filter(ChatSession.id == session_id).first()
                if session_record:
                    session_record.title = session_title
                    db_session.commit()
                    logger.info(f"Updated session {session_id} title: {session_title}")
            except Exception as e:
                logger.warning(f"Failed to update session title: {e}")
                if db_session:
                    db_session.rollback()
            finally:
                if db_session:
                    db_session.close()

        if not entities and not relationships:
            logger.warning("No entities or relationships extracted from conversation")

        # Store in Neo4j
        stored = self._store_in_neo4j(extraction_result, session_id)

        result = {
            "session_id": session_id,
            "message_count": len(messages),
            "entities_added": len(extraction_result.get("entities", [])),
            "relationships_added": len(extraction_result.get("relationships", [])),
            "stored_in_neo4j": stored
        }
        logger.info(f"=== Knowledge Extraction Completed: {result} ===")
        return result

# Global instance
knowledge_extractor = KnowledgeExtractor()
