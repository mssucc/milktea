"""Clear all data from Neo4j database."""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent / "agent"
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from backend.graph_db.neo4j_client import init_neo4j, get_driver

def clear_database():
    if not init_neo4j():
        print("Neo4j connection failed. Check your connection settings.")
        return
    driver = get_driver()

    with driver.session() as session:
        print("=" * 60)
        print("Clearing Neo4j Database")
        print("=" * 60)

        # Count before deletion
        result = session.run("MATCH (e:Entity) RETURN count(e) as count")
        entity_count = result.single()["count"]
        print(f"Entities to delete: {entity_count}")

        result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
        rel_count = result.single()["count"]
        print(f"Relationships to delete: {rel_count}")

        # Delete all relationships first
        session.run("MATCH ()-[r:RELATED_TO]->() DELETE r")
        print("Deleted all relationships")

        # Delete all entities
        session.run("MATCH (e:Entity) DELETE e")
        print("Deleted all entities")

        # Verify deletion
        result = session.run("MATCH (e:Entity) RETURN count(e) as count")
        remaining_entities = result.single()["count"]

        result = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count")
        remaining_rels = result.single()["count"]

        print()
        print("=" * 60)
        print("Database Cleared Successfully!")
        print(f"Remaining entities: {remaining_entities}")
        print(f"Remaining relationships: {remaining_rels}")
        print("=" * 60)

    driver.close()

if __name__ == "__main__":
    confirm = input("This will delete ALL data in Neo4j. Type 'yes' to confirm: ")
    if confirm.lower() == 'yes':
        clear_database()
    else:
        print("Cancelled.")
