"""Check Neo4j data structure"""
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def check_structure():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        print("=" * 60)
        print("Neo4j Data Structure Check")
        print("=" * 60)

        # Get all Entity nodes and their properties
        result = session.run("""
            MATCH (e:Entity)
            RETURN e, keys(e) as props
            LIMIT 5
        """)

        print("\nSample Entity nodes:")
        for record in result:
            entity = record["e"]
            props = record["props"]
            print(f"  Node ID: {entity.id}")
            print(f"  Properties: {props}")
            for key in props:
                print(f"    {key}: {entity.get(key)}")
            print()

        # Check if session_id property exists on any node
        result = session.run("""
            MATCH (e:Entity)
            WHERE e.session_id IS NOT NULL
            RETURN count(e) as count
        """)
        count_with_session = result.single()["count"]
        print(f"Entities WITH session_id: {count_with_session}")

        # Count all entities
        result = session.run("MATCH (e:Entity) RETURN count(e) as count")
        total = result.single()["count"]
        print(f"Total entities: {total}")

        # Check relationship properties
        result = session.run("""
            MATCH ()-[r:RELATED_TO]->()
            RETURN r, keys(r) as props
            LIMIT 3
        """)

        print("\nSample Relationships:")
        for record in result:
            rel = record["r"]
            props = record["props"]
            print(f"  Rel ID: {rel.id}, Type: {rel.type}")
            print(f"  Properties: {props}")
            for key in props:
                print(f"    {key}: {rel.get(key)}")
            print()

        # Get relationship count
        result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
        rel_count = result.single()["count"]
        print(f"Total relationships: {rel_count}")

    driver.close()

if __name__ == "__main__":
    check_structure()
