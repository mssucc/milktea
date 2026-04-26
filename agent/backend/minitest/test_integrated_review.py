#!/usr/bin/env python3
"""Test script for the integrated review endpoints"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from backend.database.session import SessionLocal, init_db
from backend.database import crud
from backend.database.model import ReviewData


def test_aggregated_review_functions():
    """Test the aggregated review CRUD functions"""
    print("Testing aggregated review functions...")

    db = SessionLocal()
    try:
        # Create test review data for multiple sessions
        session_ids = []
        for i in range(3):
            session_id = f"test_integrated_{i}_{int(time.time())}"
            session_ids.append(session_id)

            # Create dummy review data
            review_data = crud.create_or_update_review_data(
                db=db,
                session_id=session_id,
                summary=f"Test summary for session {i} about AI and machine learning",
                key_points=[f"Key point {j} for session {i}" for j in range(3)],
                questions=[
                    {
                        "id": 1,
                        "question": f"What is AI? (Session {i})",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correct_answer": 0,
                        "explanation": "AI is artificial intelligence",
                        "difficulty": "easy",
                        "entity_name": "AI"
                    }
                ],
                recommendations=[
                    {
                        "id": 1,
                        "type": "quiz",
                        "title": f"Test Quiz (Session {i})",
                        "description": "Test your knowledge",
                        "estimated_time": "5 minutes",
                        "due_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                        "priority": "high",
                        "completed": False,
                        "entity_name": None
                    }
                ],
                recent_entities=[
                    {
                        "name": f"AI_{i}",
                        "type": "concept",
                        "description": "Artificial Intelligence",
                        "mention_count": 3,
                        "importance_score": 0.9,
                        "is_recent": True
                    }
                ],
                key_entities=[
                    {
                        "name": f"Machine Learning_{i}",
                        "type": "concept",
                        "description": "ML algorithms",
                        "mention_count": 2,
                        "importance_score": 0.8,
                        "is_recent": False
                    }
                ],
                next_review_date=datetime.utcnow() + timedelta(days=1),
                generation_config={
                    "recent_days": 3,
                    "top_n_recent": 3,
                    "max_questions": 10
                }
            )
            print(f"  Created review data for session {session_id}")

        # Test get_recent_valid_reviews
        recent_reviews = crud.get_recent_valid_reviews(db, limit=5, days=7)
        print(f"  Retrieved {len(recent_reviews)} recent valid reviews")

        for review in recent_reviews:
            print(f"    - {review.session_id}: {len(review.key_points or [])} key points")

        # Test get_aggregated_review_data
        aggregated = crud.get_aggregated_review_data(db, session_ids=None, limit=10)
        print(f"\nAggregated data:")
        print(f"  Session count: {aggregated['session_count']}")
        print(f"  Key points: {len(aggregated['aggregated_key_points'])}")
        print(f"  Questions: {len(aggregated['aggregated_questions'])}")
        print(f"  Recommendations: {len(aggregated['aggregated_recommendations'])}")
        print(f"  Entities: {len(aggregated['aggregated_entities'])}")

        if aggregated['aggregated_key_points']:
            print(f"  Sample key points: {aggregated['aggregated_key_points'][:3]}")

        if aggregated['aggregated_questions']:
            print(f"  Sample question: {aggregated['aggregated_questions'][0].get('question', 'No question')}")

        print("[PASS] Aggregated review function tests passed")
        return True

    except Exception as e:
        print(f"[FAIL] Aggregated review function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_integrated_endpoint_simulation():
    """Simulate what the integrated endpoint would return"""
    print("\nSimulating integrated endpoint response...")

    db = SessionLocal()
    try:
        # Get aggregated data
        aggregated = crud.get_aggregated_review_data(db, session_ids=None, limit=10)

        # Simulate response structure
        response = {
            "aggregated_summary": aggregated["aggregated_summary"],
            "aggregated_key_points": aggregated["aggregated_key_points"],
            "aggregated_questions": len(aggregated["aggregated_questions"]),
            "aggregated_recommendations": len(aggregated["aggregated_recommendations"]),
            "session_count": aggregated["session_count"],
            "next_review_date": aggregated["next_review_date"]
        }

        print(f"  Summary: {response['aggregated_summary'][:100]}...")
        print(f"  Key points: {len(response['aggregated_key_points'])}")
        print(f"  Questions: {response['aggregated_questions']}")
        print(f"  Recommendations: {response['aggregated_recommendations']}")
        print(f"  Sessions: {response['session_count']}")
        print(f"  Next review: {response['next_review_date']}")

        print("[PASS] Integrated endpoint simulation passed")
        return True

    except Exception as e:
        print(f"[FAIL] Integrated endpoint simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def cleanup_test_data():
    """Clean up test data"""
    print("\nCleaning up test data...")

    db = SessionLocal()
    try:
        # Delete test sessions
        test_reviews = db.query(ReviewData).filter(
            ReviewData.session_id.like("test_integrated_%")
        ).all()

        for review in test_reviews:
            db.delete(review)

        db.commit()
        print(f"  Cleaned up {len(test_reviews)} test reviews")

    except Exception as e:
        db.rollback()
        print(f"  Error cleaning up test data: {e}")
    finally:
        db.close()


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Integrated Review Endpoints")
    print("=" * 60)

    # Initialize database
    print("\nInitializing database...")
    init_db()

    test_results = []

    # Run tests
    test_results.append(("Aggregated Functions", test_aggregated_review_functions()))
    test_results.append(("Endpoint Simulation", test_integrated_endpoint_simulation()))

    # Cleanup
    cleanup_test_data()

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in test_results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {test_name:30} {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] All tests passed!")
        return 0
    else:
        print("[ERROR] Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())