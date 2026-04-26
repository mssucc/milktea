#!/usr/bin/env python3
"""Test the aggregated CRUD functions only"""

import sys
import os
import json
from datetime import datetime, timedelta, timezone

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.session import SessionLocal, init_db
from backend.database import crud


def test_aggregated_functions_with_existing_data():
    """Test aggregated functions with existing review data"""
    print("Testing aggregated review functions with existing data...")

    db = SessionLocal()
    try:
        # Get existing reviews first
        existing_reviews = crud.get_recent_valid_reviews(db, limit=10, days=30)
        print(f"Found {len(existing_reviews)} existing reviews")

        # Test get_aggregated_review_data with no session_ids (uses recent valid reviews)
        aggregated = crud.get_aggregated_review_data(db, session_ids=None, limit=10)

        print(f"\nAggregated data results:")
        print(f"  Session count: {aggregated['session_count']}")
        print(f"  Key points: {len(aggregated['aggregated_key_points'])}")
        print(f"  Questions: {len(aggregated['aggregated_questions'])}")
        print(f"  Recommendations: {len(aggregated['aggregated_recommendations'])}")
        print(f"  Entities: {len(aggregated['aggregated_entities'])}")

        if aggregated['session_count'] > 0:
            print(f"\nSample data from sessions:")
            for i, session_info in enumerate(aggregated['sessions'][:3]):
                print(f"  Session {i+1}: {session_info['session_id']}")
                print(f"    Key points: {session_info['key_points_count']}")
                print(f"    Questions: {session_info['questions_count']}")
                print(f"    Recommendations: {session_info['recommendations_count']}")

        print(f"\nAggregated summary: {aggregated['aggregated_summary'][:200]}...")

        print("[PASS] Aggregated functions test completed")
        return True

    except Exception as e:
        print(f"[FAIL] Aggregated functions test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_empty_aggregated_data():
    """Test aggregated functions when no review data exists"""
    print("\nTesting aggregated functions with empty data...")

    db = SessionLocal()
    try:
        # Test with specific non-existent session IDs
        non_existent_sessions = ["non_existent_1", "non_existent_2"]
        aggregated = crud.get_aggregated_review_data(
            db=db,
            session_ids=non_existent_sessions,
            limit=10
        )

        print(f"Empty data results:")
        print(f"  Session count: {aggregated['session_count']} (expected 0)")
        print(f"  Key points: {len(aggregated['aggregated_key_points'])} (expected 0)")
        print(f"  Questions: {len(aggregated['aggregated_questions'])} (expected 0)")
        print(f"  Recommendations: {len(aggregated['aggregated_recommendations'])} (expected 0)")

        if aggregated['session_count'] == 0:
            print("[PASS] Empty data handled correctly")
            return True
        else:
            print("[FAIL] Empty data test failed - unexpected data found")
            return False

    except Exception as e:
        print(f"[FAIL] Empty data test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_data_structure():
    """Test that the aggregated data structure is correct"""
    print("\nTesting aggregated data structure...")

    db = SessionLocal()
    try:
        aggregated = crud.get_aggregated_review_data(db, session_ids=None, limit=5)

        # Check required fields
        required_fields = [
            'aggregated_summary', 'aggregated_key_points', 'aggregated_questions',
            'aggregated_recommendations', 'aggregated_entities', 'next_review_date',
            'session_count', 'total_questions', 'total_recommendations', 'sessions'
        ]

        missing_fields = []
        for field in required_fields:
            if field not in aggregated:
                missing_fields.append(field)

        if missing_fields:
            print(f"[FAIL] Missing required fields: {missing_fields}")
            return False

        # Check data types
        if not isinstance(aggregated['aggregated_summary'], str):
            print(f"[FAIL] aggregated_summary should be str, got {type(aggregated['aggregated_summary'])}")
            return False

        if not isinstance(aggregated['aggregated_key_points'], list):
            print(f"[FAIL] aggregated_key_points should be list, got {type(aggregated['aggregated_key_points'])}")
            return False

        if not isinstance(aggregated['session_count'], int):
            print(f"[FAIL] session_count should be int, got {type(aggregated['session_count'])}")
            return False

        print("[PASS] Data structure is correct")
        return True

    except Exception as e:
        print(f"[FAIL] Data structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Aggregated CRUD Functions")
    print("=" * 60)

    # Initialize database
    print("\nInitializing database...")
    init_db()

    test_results = []

    # Run tests
    test_results.append(("Aggregated Functions", test_aggregated_functions_with_existing_data()))
    test_results.append(("Empty Data Handling", test_empty_aggregated_data()))
    test_results.append(("Data Structure", test_data_structure()))

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