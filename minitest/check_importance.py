"""Check importance_score distribution in Neo4j"""
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def check_importance():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        print("=" * 60)
        print("Neo4j Importance Score Distribution")
        print("=" * 60)

        # First, check if importance_score property exists
        result = session.run("""
            MATCH (e:Entity)
            RETURN count(e) as total,
                   count(e.importance_score) as has_importance,
                   min(e.importance_score) as min_importance,
                   max(e.importance_score) as max_importance,
                   avg(e.importance_score) as avg_importance
        """)
        stats = result.single()
        print(f"Total entities: {stats['total']}")
        print(f"Entities with importance_score: {stats['has_importance']}")
        if stats['has_importance'] > 0:
            print(f"Min importance_score: {stats['min_importance']}")
            print(f"Max importance_score: {stats['max_importance']}")
            print(f"Average importance_score: {stats['avg_importance']:.2f}")
        else:
            print("No entities have importance_score property!")

        # Check properties on a few entities
        print("\nSample entities with properties:")
        result = session.run("""
            MATCH (e:Entity)
            RETURN e.name as name, properties(e) as props
            LIMIT 5
        """)
        for record in result:
            name = record['name']
            props = dict(record['props'])
            importance = props.get('importance_score', 'NOT SET')
            mention_count = props.get('mention_count', 'NOT SET')
            print(f"  {name}: mention_count={mention_count}, importance_score={importance}")

        # Distribution of importance_score values
        print("\nImportance score distribution:")
        result = session.run("""
            MATCH (e:Entity)
            WHERE e.importance_score IS NOT NULL
            WITH e.importance_score as score, count(*) as freq
            RETURN score, freq
            ORDER BY score DESC
        """)
        count = 0
        for record in result:
            print(f"  Score {record['score']}: {record['freq']} entities")
            count += 1
        if count == 0:
            print("  (no importance_score values found)")

        # Check if value (mention_count * importance) would vary
        print("\nCalculated value (mention_count * importance_score) for top entities:")
        result = session.run("""
            MATCH (e:Entity)
            WHERE e.importance_score IS NOT NULL AND e.mention_count IS NOT NULL
            RETURN e.name as name, e.mention_count as count, e.importance_score as importance,
                   e.mention_count * e.importance_score as value
            ORDER BY value DESC
            LIMIT 10
        """)
        for record in result:
            name = record['name']
            count_val = record['count']
            importance = record['importance']
            value = record['value']
            print(f"  {name}: {count_val} * {importance} = {value}")

    driver.close()

if __name__ == "__main__":
    check_importance()