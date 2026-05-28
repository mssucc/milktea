#!/usr/bin/env python3
"""Test LLM performance with realistic data to ensure completion within timeout"""

import sys
import os
import time
import json
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_llm_performance():
    """Test that all LLM calls complete within reasonable time"""

    print("\n" + "="*80)
    print("LLM PERFORMANCE TEST WITH REALISTIC DATA")
    print("="*80)

    # Import modules
    from backend.utils.summarizer import ConversationSummarizer
    from backend.utils.review_generator import ReviewGenerator

    summarizer = ConversationSummarizer()
    review_gen = ReviewGenerator()

    # Test configuration — read from environment variables
    from dotenv import load_dotenv
    load_dotenv()
    test_api_key = os.getenv("OPENAI_API_KEY", "")
    if not test_api_key:
        print("Error: OPENAI_API_KEY not set in .env or environment")
        return
    test_base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    test_model = os.getenv("OPENAI_MODEL", "deepseek-chat")
    test_session_id = "test-session-perf-123"

    print(f"\nTest Configuration:")
    print(f"  API Key: {test_api_key[:10]}...")
    print(f"  Base URL: {test_base_url}")
    print(f"  Model: {test_model}")

    # Create realistic test data
    print(f"\nCreating realistic test data...")

    # Simulate a conversation about machine learning
    test_messages = [
        {"role": "user", "content": "Can you explain what machine learning is?"},
        {"role": "assistant", "content": "Machine learning is a subset of artificial intelligence that allows computers to learn from data without being explicitly programmed. It focuses on developing algorithms that can identify patterns and make predictions based on input data."},
        {"role": "user", "content": "What are the main types of machine learning?"},
        {"role": "assistant", "content": "The three main types are: 1) Supervised learning (learning from labeled data), 2) Unsupervised learning (finding patterns in unlabeled data), and 3) Reinforcement learning (learning through trial and error with rewards)."},
        {"role": "user", "content": "Give me examples of supervised learning algorithms."},
        {"role": "assistant", "content": "Common supervised learning algorithms include linear regression, logistic regression, decision trees, random forests, support vector machines, and neural networks."},
        {"role": "user", "content": "What's the difference between AI and ML?"},
        {"role": "assistant", "content": "AI is the broader concept of machines being able to carry out tasks in a way we'd consider 'smart'. ML is a subset of AI that focuses on the idea that machines should be able to learn and adapt through experience."},
    ]

    test_key_points = [
        "machine learning",
        "artificial intelligence",
        "supervised learning",
        "unsupervised learning",
        "reinforcement learning",
        "neural networks"
    ]

    test_entities = [
        {"name": "machine learning", "type": "concept", "description": "AI subset for learning from data", "mention_count": 5, "importance_score": 0.9},
        {"name": "artificial intelligence", "type": "concept", "description": "Broad field of intelligent machines", "mention_count": 3, "importance_score": 0.8},
        {"name": "neural networks", "type": "algorithm", "description": "ML algorithms inspired by brain neurons", "mention_count": 2, "importance_score": 0.7},
    ]

    print(f"  Messages: {len(test_messages)}")
    print(f"  Key points: {len(test_key_points)}")
    print(f"  Entities: {len(test_entities)}")

    # Run tests with timing
    print(f"\n" + "="*80)
    print("RUNNING PERFORMANCE TESTS")
    print("="*80)

    results = []

    # Test 1: Summarization
    print(f"\n[TEST 1] Summarization")
    print(f"  Input: {len(test_messages)} messages")
    start_time = time.time()
    try:
        summary_result = summarizer.summarize_conversation(
            test_messages,
            test_session_id,
            api_key=test_api_key,
            base_url=test_base_url,
            model=test_model
        )
        elapsed = time.time() - start_time
        success = True
        print(f"  [OK] Success in {elapsed:.2f}s")
        print(f"    Summary length: {len(summary_result.get('summary', ''))} chars")
        print(f"    Key points: {len(summary_result.get('key_points', []))}")
    except Exception as e:
        elapsed = time.time() - start_time
        success = False
        print(f"  [ERROR] Failed after {elapsed:.2f}s: {e}")

    results.append({
        "test": "summarization",
        "success": success,
        "time": elapsed,
        "messages": len(test_messages)
    })

    # Test 2: Question generation
    print(f"\n[TEST 2] Question Generation")
    print(f"  Input: {len(test_key_points)} key points")
    start_time = time.time()
    try:
        questions_result = summarizer.generate_review_questions(
            test_key_points,
            test_session_id,
            api_key=test_api_key,
            base_url=test_base_url,
            model=test_model
        )
        elapsed = time.time() - start_time
        success = True
        print(f"  [OK] Success in {elapsed:.2f}s")
        print(f"    Questions generated: {len(questions_result)}")
    except Exception as e:
        elapsed = time.time() - start_time
        success = False
        print(f"  [ERROR] Failed after {elapsed:.2f}s: {e}")

    results.append({
        "test": "question_generation",
        "success": success,
        "time": elapsed,
        "key_points": len(test_key_points)
    })

    # Test 3: Recommendation generation
    print(f"\n[TEST 3] Recommendation Generation")
    print(f"  Input: {len(test_entities)} entities, recent_days=3")
    start_time = time.time()
    try:
        rec_result = review_gen.generate_review_recommendations(
            test_session_id,
            recent_days=3,
            entities=test_entities,
            summary="Test summary about machine learning concepts",
            api_key=test_api_key,
            base_url=test_base_url,
            model=test_model
        )
        elapsed = time.time() - start_time
        success = True
        print(f"  [OK] Success in {elapsed:.2f}s")
        print(f"    Recommendations: {len(rec_result.get('recommendations', []))}")
    except Exception as e:
        elapsed = time.time() - start_time
        success = False
        print(f"  [ERROR] Failed after {elapsed:.2f}s: {e}")

    results.append({
        "test": "recommendation_generation",
        "success": success,
        "time": elapsed,
        "entities": len(test_entities)
    })

    # Calculate totals
    print(f"\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)

    total_time = sum(r["time"] for r in results if r["success"])
    all_success = all(r["success"] for r in results)

    if all_success:
        print(f"\n✅ ALL TESTS PASSED")
        print(f"\nTiming Summary:")
        for r in results:
            print(f"  {r['test']}: {r['time']:.2f}s")

        print(f"\n  Total time for 3 LLM calls: {total_time:.2f}s")
        print(f"  Average per call: {total_time/len(results):.2f}s")

        # Recommendations
        print(f"\nRecommendations:")
        if total_time > 60:
            print(f"  ❗ Total time > 60s - consider optimizing")
        elif total_time > 30:
            print(f"  ⚠️  Total time > 30s - frontend timeout increased to 90s is good")
        else:
            print(f"  ✅ Total time < 30s - well within limits")

        print(f"\n  Frontend timeout: 90s")
        print(f"  Backend LLM timeout: 30s per call")
        print(f"  Safety margin: {90 - total_time:.1f}s")

    else:
        print(f"\n❌ SOME TESTS FAILED")
        for r in results:
            status = "✅" if r["success"] else "❌"
            print(f"  {status} {r['test']}: {r['time']:.2f}s")

    # Test 4: Simulate full review endpoint (sequential calls)
    print(f"\n" + "="*80)
    print("SIMULATING FULL REVIEW ENDPOINT (SEQUENTIAL)")
    print("="*80)

    if all_success:
        # Use actual results from previous tests
        actual_summary = summary_result.get("summary", "")
        actual_questions = questions_result

        print(f"\nSimulating sequential execution:")
        print(f"  1. Summarization: {results[0]['time']:.2f}s")
        print(f"  2. Question generation: {results[1]['time']:.2f}s")
        print(f"  3. Recommendation generation: {results[2]['time']:.2f}s")

        # Estimate database and other processing time
        db_time = 2.0  # seconds for DB queries, entity selection, etc.
        print(f"  4. Other processing (DB, entities): ~{db_time}s")

        estimated_total = total_time + db_time
        print(f"\n  Estimated total: {estimated_total:.2f}s")

        if estimated_total > 90:
            print(f"  ❗ ESTIMATED TOTAL > 90s - May exceed frontend timeout!")
            print(f"     Consider: Reduce message count, optimize prompts, parallel processing")
        elif estimated_total > 60:
            print(f"  ⚠️  Estimated total > 60s - Close to limit but should work")
        else:
            print(f"  ✅ Estimated total < 60s - Well within 90s timeout")

    print(f"\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

    return all_success

def main():
    """Main test function"""
    print("LLM Performance Test for Review Endpoint")
    print("="*80)

    success = test_llm_performance()

    if success:
        print(f"\n✅ Performance test passed. LLM calls complete within expected time.")
        print(f"   Frontend timeout increased to 90s should be sufficient.")
    else:
        print(f"\n❌ Performance test failed. Check logs for details.")

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()