"""Check mention_count distribution in Neo4j"""
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def check_mention_counts():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        print("=" * 60)
        print("Neo4j mention_count Distribution")
        print("=" * 60)

        # Get mention_count statistics
        result = session.run("""
            MATCH (e:Entity)
            RETURN
                count(e) as total,
                min(e.mention_count) as min_count,
                max(e.mention_count) as max_count,
                avg(e.mention_count) as avg_count,
                percentileCont(e.mention_count, 0.5) as median
        """)
        stats = result.single()
        print(f"Total entities: {stats['total']}")
        print(f"Min mention_count: {stats['min_count']}")
        print(f"Max mention_count: {stats['max_count']}")
        print(f"Average mention_count: {stats['avg_count']:.2f}")
        print(f"Median mention_count: {stats['median']}")

        # Distribution histogram
        print("\nMention count distribution:")
        result = session.run("""
            MATCH (e:Entity)
            WITH e.mention_count as count, count(*) as freq
            RETURN count, freq
            ORDER BY count DESC
        """)
        for record in result:
            print(f"  Count {record['count']}: {record['freq']} entities")

        # Top entities by mention_count
        print("\nTop 10 entities by mention_count:")
        result = session.run("""
            MATCH (e:Entity)
            RETURN e.name as name, e.mention_count as count, e.session_ids as sessions
            ORDER BY e.mention_count DESC
            LIMIT 10
        """)
        for record in result:
            print(f"  {record['name']}: {record['count']} mentions, {len(record['sessions'])} sessions")

        # Check for entities with mention_count = 1 but multiple sessions
        print("\nEntities with mention_count=1 but multiple sessions:")
        result = session.run("""
            MATCH (e:Entity)
            WHERE e.mention_count = 1 AND size(e.session_ids) > 1
            RETURN e.name as name, e.session_ids as sessions
            LIMIT 10
        """)
        count = 0
        for record in result:
            print(f"  {record['name']}: {len(record['sessions'])} sessions")
            count += 1
        if count == 0:
            print("  (none)")

        # Check for entities with mention_count > 1 but single session
        print("\nEntities with mention_count>1 but single session:")
        result = session.run("""
            MATCH (e:Entity)
            WHERE e.mention_count > 1 AND size(e.session_ids) = 1
            RETURN e.name as name, e.mention_count as count, e.session_ids as sessions
            LIMIT 10
        """)
        count = 0
        for record in result:
            print(f"  {record['name']}: {record['count']} mentions, 1 session")
            count += 1
        if count == 0:
            print("  (none)")

    driver.close()

if __name__ == "__main__":
    check_mention_counts()