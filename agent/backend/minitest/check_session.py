"""Check data for a specific session"""
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def check_session(session_id):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        print(f"Checking session: {session_id}")
        print("=" * 60)

        # Count entities for this session
        result = session.run("""
            MATCH (e:Entity)
            WHERE e.session_id = $session_id
            RETURN count(e) as count
        """, session_id=session_id)
        entity_count = result.single()["count"]
        print(f"Entities for this session: {entity_count}")

        # Count relationships for this session
        result = session.run("""
            MATCH ()-[r:RELATED_TO]->()
            WHERE r.session_id = $session_id
            RETURN count(r) as count
        """, session_id=session_id)
        rel_count = result.single()["count"]
        print(f"Relationships for this session: {rel_count}")

        # Get sample entities
        result = session.run("""
            MATCH (e:Entity)
            WHERE e.session_id = $session_id
            RETURN e.name as name, e.type as type, e.description as description
            LIMIT 10
        """, session_id=session_id)

        print("\nSample entities:")
        for record in result:
            print(f"  - {record['name']} ({record['type']}): {record['description'][:50] if record['description'] else 'No description'}...")

        # Get all unique session IDs
        result = session.run("""
            MATCH (e:Entity)
            WHERE e.session_id IS NOT NULL
            RETURN DISTINCT e.session_id as session_id
        """)

        print("\nAll sessions with data:")
        for record in result:
            sid = record["session_id"]
            # Count for each session
            cnt_result = session.run("""
                MATCH (e:Entity)
                WHERE e.session_id = $session_id
                RETURN count(e) as count
            """, session_id=sid)
            cnt = cnt_result.single()["count"]
            print(f"  - {sid}: {cnt} entities")

    driver.close()

if __name__ == "__main__":
    # Check the session that has data
    check_session("954f0884-b1c6-4d0f-a45e-75a18022fb90")
