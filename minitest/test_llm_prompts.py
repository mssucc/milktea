#!/usr/bin/env python3
"""Test LLM prompts with detailed logging for DeepSeek API calls"""

import sys
import os
import json
import logging
import time
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_llm_prompts.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def capture_llm_prompts():
    """Capture and analyze LLM prompts used in summarizer and review_generator"""

    print("\n" + "="*80)
    print("CAPTURING LLM PROMPTS FROM SUMMARIZER AND REVIEW GENERATOR")
    print("="*80)

    # Import modules
    from backend.utils.summarizer import ConversationSummarizer
    from backend.utils.review_generator import ReviewGenerator

    summarizer = ConversationSummarizer()
    review_gen = ReviewGenerator()

    # Create test messages for summarization
    test_messages = [
        {"role": "user", "content": "What is machine learning?"},
        {"role": "assistant", "content": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed."},
        {"role": "user", "content": "Can you give me examples of machine learning algorithms?"},
        {"role": "assistant", "content": "Sure! Some common machine learning algorithms include linear regression, decision trees, random forests, support vector machines, and neural networks."},
    ]

    test_key_points = ["machine learning", "artificial intelligence", "algorithms", "neural networks"]

    # Test configuration — read from environment variables
    from dotenv import load_dotenv
    load_dotenv()
    test_api_key = os.getenv("OPENAI_API_KEY", "")
    if not test_api_key:
        print("Error: OPENAI_API_KEY not set in .env or environment")
        return
    test_base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    test_model = os.getenv("OPENAI_MODEL", "deepseek-chat")
    test_session_id = "test-session-123"

    print(f"\nTest Configuration:")
    print(f"  API Key: {test_api_key[:10]}...")
    print(f"  Base URL: {test_base_url}")
    print(f"  Model: {test_model}")
    print(f"  Session ID: {test_session_id}")

    # Test 1: Summarizer - Check prompts and timing
    print("\n" + "="*80)
    print("TEST 1: SUMMARIZER LLM CALL")
    print("="*80)

    try:
        print("\n[INFO] Creating LLM for summarization...")
        start_time = time.time()

        # We need to inspect the prompts in the summarizer
        # For now, let's just test the actual call and log the request

        # Monkey-patch to capture the actual prompts sent to LLM
        original_invoke = None
        captured_prompts = []

        def capture_invoke(messages):
            nonlocal captured_prompts
            print("\n[DEBUG] Captured LLM invocation with messages:")
            for i, msg in enumerate(messages):
                print(f"  Message {i+1}: {msg.type}")
                print(f"    Content (first 200 chars): {msg.content[:200]}...")
                captured_prompts.append({
                    "type": msg.type,
                    "content": msg.content
                })

            # Call original invoke
            if original_invoke:
                return original_invoke(messages)

        # Create LLM and patch its invoke method
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            api_key=test_api_key,
            base_url=test_base_url,
            model=test_model,
            temperature=0.3,
            max_tokens=512,
            timeout=30.0,
        )

        original_invoke = llm.invoke
        llm.invoke = capture_invoke

        # Now call the summarizer (it will use our patched LLM)
        print("\n[INFO] Testing summarizer.summarize_conversation...")

        # Since we can't easily monkey-patch the internal LLM, let's directly test the prompts
        # Instead, let's examine the actual prompts from the source code

        print("\n[INFO] Examining summarizer prompts from source code...")

        # Read the summarizer.py file to extract prompts
        summarizer_path = os.path.join(os.path.dirname(__file__), "../utils/summarizer.py")
        with open(summarizer_path, 'r', encoding='utf-8') as f:
            summarizer_code = f.read()

        # Find system and user prompts
        import re
        system_prompt_match = re.search(r'system_prompt = """([\s\S]*?)"""', summarizer_code)
        user_prompt_match = re.search(r'user_prompt = f"""([\s\S]*?)"""', summarizer_code)

        if system_prompt_match:
            system_prompt = system_prompt_match.group(1)
            print(f"\n[PROMPT] Summarizer System Prompt:")
            print("-"*40)
            print(system_prompt)
            print("-"*40)

            # Analyze prompt
            prompt_words = len(system_prompt.split())
            print(f"\n  Prompt Statistics:")
            print(f"    Length: {len(system_prompt)} characters")
            print(f"    Words: {prompt_words}")
            print(f"    Lines: {system_prompt.count(chr(10)) + 1}")

        if user_prompt_match:
            user_prompt_template = user_prompt_match.group(1)
            print(f"\n[PROMPT] Summarizer User Prompt Template:")
            print("-"*40)
            print(user_prompt_template)
            print("-"*40)

            # Estimate actual user prompt size
            conversation_text = ""
            for msg in test_messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                conversation_text += f"{role}: {content}\n\n"

            estimated_user_prompt = f"""Please analyze this conversation and provide a summary with key knowledge points:

{conversation_text}

Please output valid JSON only."""

            print(f"\n[INFO] Estimated User Prompt Size:")
            print(f"  Conversation text: {len(conversation_text)} chars")
            print(f"  Total user prompt: {len(estimated_user_prompt)} chars")

        # Now test actual summarization
        print("\n" + "="*80)
        print("TEST 2: ACTUAL SUMMARIZATION CALL")
        print("="*80)

        start_time = time.time()
        summary_result = summarizer.summarize_conversation(
            test_messages,
            test_session_id,
            api_key=test_api_key,
            base_url=test_base_url,
            model=test_model
        )
        end_time = time.time()

        elapsed = end_time - start_time
        print(f"\n[RESULT] Summarization completed in {elapsed:.2f} seconds")
        print(f"[RESULT] Summary: {summary_result.get('summary', '')[:100]}...")
        print(f"[RESULT] Key points: {len(summary_result.get('key_points', []))}")

        # Test 3: Review question generation
        print("\n" + "="*80)
        print("TEST 3: REVIEW QUESTION GENERATION")
        print("="*80)

        # Read review_generator prompts
        review_gen_path = os.path.join(os.path.dirname(__file__), "../utils/review_generator.py")
        with open(review_gen_path, 'r', encoding='utf-8') as f:
            review_gen_code = f.read()

        system_prompt_match = re.search(r'system_prompt = """([\s\S]*?)"""', review_gen_code)

        if system_prompt_match:
            system_prompt = system_prompt_match.group(1)
            print(f"\n[PROMPT] Review Generator System Prompt:")
            print("-"*40)
            print(system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt)
            print("-"*40)

            prompt_words = len(system_prompt.split())
            print(f"\n  Prompt Statistics:")
            print(f"    Length: {len(system_prompt)} characters")
            print(f"    Words: {prompt_words}")
            print(f"    Lines: {system_prompt.count(chr(10)) + 1}")

        # Test question generation
        start_time = time.time()
        questions_result = summarizer.generate_review_questions(
            test_key_points,
            test_session_id,
            api_key=test_api_key,
            base_url=test_base_url,
            model=test_model
        )
        end_time = time.time()

        elapsed = end_time - start_time
        print(f"\n[RESULT] Question generation completed in {elapsed:.2f} seconds")
        print(f"[RESULT] Generated {len(questions_result)} questions")

        # Test 4: Review recommendations
        print("\n" + "="*80)
        print("TEST 4: REVIEW RECOMMENDATIONS")
        print("="*80)

        test_entities = [
            {"name": "machine learning", "type": "concept", "description": "AI subset for learning from data"},
            {"name": "neural networks", "type": "algorithm", "description": "ML algorithms inspired by brain"},
        ]

        start_time = time.time()
        rec_result = review_gen.generate_review_recommendations(
            test_session_id,
            recent_days=3,
            entities=test_entities,
            summary=summary_result.get("summary", ""),
            api_key=test_api_key,
            base_url=test_base_url,
            model=test_model
        )
        end_time = time.time()

        elapsed = end_time - start_time
        print(f"\n[RESULT] Recommendation generation completed in {elapsed:.2f} seconds")
        print(f"[RESULT] Generated {len(rec_result.get('recommendations', []))} recommendations")

        # Total time estimate
        print("\n" + "="*80)
        print("TIME ESTIMATE FOR FULL REVIEW GENERATION")
        print("="*80)

        # Estimate based on our tests
        estimate_summary = 3.0  # seconds
        estimate_questions = 3.0  # seconds
        estimate_recommendations = 3.0  # seconds
        estimate_other = 2.0  # seconds (DB queries, etc.)

        total_estimate = estimate_summary + estimate_questions + estimate_recommendations + estimate_other
        print(f"\n[ESTIMATE] Summary generation: {estimate_summary:.1f}s")
        print(f"[ESTIMATE] Question generation: {estimate_questions:.1f}s")
        print(f"[ESTIMATE] Recommendation generation: {estimate_recommendations:.1f}s")
        print(f"[ESTIMATE] Other processing (DB, etc.): {estimate_other:.1f}s")
        print(f"[ESTIMATE] TOTAL ESTIMATED TIME: {total_estimate:.1f}s")
        print(f"\n[NOTE] Frontend timeout is now 90s, should be sufficient.")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print("\nCheck detailed logs in: test_llm_prompts.log")

def main():
    """Main test function"""
    print("LLM Prompts and Performance Test")
    print("="*80)

    capture_llm_prompts()

if __name__ == "__main__":
    main()