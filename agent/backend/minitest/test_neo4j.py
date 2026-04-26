"""Test Neo4j cloud connection and basic operations"""
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

print("=" * 60)
print("Neo4j Cloud Connection Test")
print("=" * 60)
print(f"URI: {NEO4J_URI}")
print(f"User: {NEO4J_USER}")
print(f"Password: {'*' * len(NEO4J_PASSWORD) if NEO4J_PASSWORD else 'Not set'}")
print()

def test_connection():
    driver = None
    try:
        print("1. Creating driver...")
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        print("2. Verifying connectivity...")
        driver.verify_connectivity()
        print("   [OK] Connectivity verified!")

        print("3. Testing basic query...")
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            print(f"   [OK] Query result: {record['test']}")

        print("4. Checking existing data...")
        with driver.session() as session:
            # Count all entities
            result = session.run("MATCH (e:Entity) RETURN count(e) as count")
            entity_count = result.single()["count"]
            print(f"   - Total entities: {entity_count}")

            # Count all relationships
            result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            print(f"   - Total relationships: {rel_count}")

            # Get all session IDs
            result = session.run("""
                MATCH (e:Entity)
                WHERE e.session_id IS NOT NULL
                RETURN DISTINCT e.session_id as session_id
                LIMIT 10
            """)
            sessions = [record["session_id"] for record in result]
            print(f"   - Sessions with data: {sessions if sessions else 'None'}")

        print("5. Testing write operation...")
        with driver.session() as session:
            # Create a test entity
            result = session.run("""
                MERGE (e:Entity {name: 'TestEntity', session_id: 'test-session'})
                ON CREATE SET e.type = 'test', e.created_at = datetime()
                RETURN e.name as name
            """)
            record = result.single()
            print(f"   [OK] Created/updated entity: {record['name']}")

            # Read it back
            result = session.run("""
                MATCH (e:Entity {name: 'TestEntity'})
                RETURN e.name as name, e.type as type, e.session_id as session_id
            """)
            record = result.single()
            print(f"   [OK] Read back: {record}")

            # Delete test entity
            result = session.run("""
                MATCH (e:Entity {name: 'TestEntity'})
                DELETE e
            """)
            print(f"   [OK] Deleted test entity")

        print()
        print("=" * 60)
        print("[SUCCESS] All tests passed! Neo4j cloud connection is working.")
        print("=" * 60)
        return True

    except Exception as e:
        print()
        print("=" * 60)
        print(f"[FAILED] Connection failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.close()
            print("\nDriver closed.")

if __name__ == "__main__":
    test_connection()
