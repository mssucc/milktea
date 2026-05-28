#!/usr/bin/env python3
"""Test review endpoint with detailed logging"""

import sys
import os
import json
import logging
from typing import Dict, Any

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_review_endpoint.log')
    ]
)
logger = logging.getLogger(__name__)

def test_review_endpoint_with_params():
    """Test the review endpoint generation process with detailed logging"""

    print(f"\n{'='*60}")
    print("Testing Review Endpoint Process")
    print(f"{'='*60}")

    # Test configuration - read from environment variables
    from dotenv import load_dotenv
    load_dotenv()
    test_api_key = os.getenv("OPENAI_API_KEY", "")
    if not test_api_key:
        print("Error: OPENAI_API_KEY not set in .env or environment")
        return
    test_base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    test_model = os.getenv("OPENAI_MODEL", "deepseek-chat")
    test_session_id = "8f6362d6-c2e5-45e3-99a0-25855b9c8598"

    print(f"Test Configuration:")
    print(f"  API Key: {test_api_key[:10]}...{test_api_key[-4:]}")
    print(f"  Base URL: {test_base_url}")
    print(f"  Model: {test_model}")
    print(f"  Session ID: {test_session_id}")

    try:
        # Import after path setup
        from backend.utils.summarizer import conversation_summarizer
        from backend.utils.review_generator import review_generator

        # Test 1: Test summarizer._create_llm directly
        print(f"\n{'='*60}")
        print("Test 1: Testing summarizer._create_llm directly")
        print(f"{'='*60}")

        try:
            llm1 = conversation_summarizer._create_llm(
                api_key=test_api_key,
                base_url=test_base_url,
                model=test_model
            )
            print(f"[OK] Successfully created summarizer LLM")

            # Test a simple call
            from langchain_core.messages import HumanMessage
            response = llm1.invoke([HumanMessage(content="Hello, test!")])
            print(f"[OK] LLM response: {response.content[:50]}...")
        except Exception as e:
            print(f"[ERROR] Summarizer LLM creation failed: {e}")
            import traceback
            traceback.print_exc()

        # Test 2: Test review_generator._create_llm directly
        print(f"\n{'='*60}")
        print("Test 2: Testing review_generator._create_llm directly")
        print(f"{'='*60}")

        try:
            llm2 = review_generator._create_llm(
                api_key=test_api_key,
                base_url=test_base_url,
                model=test_model
            )
            print(f"[OK] Successfully created review generator LLM")

            from langchain_core.messages import HumanMessage
            response = llm2.invoke([HumanMessage(content="Hello, test!")])
            print(f"[OK] LLM response: {response.content[:50]}...")
        except Exception as e:
            print(f"[ERROR] Review generator LLM creation failed: {e}")
            import traceback
            traceback.print_exc()

        # Test 3: Test with empty API key (should fail)
        print(f"\n{'='*60}")
        print("Test 3: Testing with empty API key")
        print(f"{'='*60}")

        try:
            llm3 = conversation_summarizer._create_llm(
                api_key="",
                base_url=test_base_url,
                model=test_model
            )
            print(f"[ERROR] Should have failed with empty API key, but didn't")
        except ValueError as e:
            print(f"[OK] Correctly failed with empty API key: {e}")
        except Exception as e:
            print(f"[ERROR] Unexpected error with empty API key: {e}")
            import traceback
            traceback.print_exc()

        # Test 4: Test with None API key (using environment)
        print(f"\n{'='*60}")
        print("Test 4: Testing with None API key (using environment)")
        print(f"{'='*60}")

        try:
            llm4 = conversation_summarizer._create_llm(
                api_key=None,
                base_url=test_base_url,
                model=test_model
            )
            print(f"[ERROR] Should have failed with None API key, but didn't")
        except ValueError as e:
            print(f"[OK] Correctly failed with None API key: {e}")
        except Exception as e:
            print(f"[ERROR] Unexpected error with None API key: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n{'='*60}")
        print("Test Summary")
        print(f"{'='*60}")
        print("If Test 1 and 2 succeed, the LLM configuration is working.")
        print("If they fail, there's an issue with the API configuration.")

    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        print("Make sure you're running from the correct directory")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

def test_empty_string_vs_none():
    """Test the difference between empty string and None in parameter handling"""

    print(f"\n{'='*60}")
    print("Testing Empty String vs None Handling")
    print(f"{'='*60}")

    # This simulates what happens in _create_llm
    from backend.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

    print(f"Environment configuration:")
    print(f"  OPENAI_API_KEY: '{OPENAI_API_KEY}' (length: {len(OPENAI_API_KEY)})")
    print(f"  OPENAI_BASE_URL: '{OPENAI_BASE_URL}'")
    print(f"  OPENAI_MODEL: '{OPENAI_MODEL}'")

    # Test different scenarios
    test_cases = [
        {"api_key": OPENAI_API_KEY if len(OPENAI_API_KEY) > 0 else "sk-test-placeholder", "desc": "Valid API key (from env)"},
        {"api_key": "", "desc": "Empty string"},
        {"api_key": None, "desc": "None"},
    ]

    for test in test_cases:
        api_key = test["api_key"]
        print(f"\nTest: {test['desc']}")
        print(f"  Input api_key: {api_key}")

        # Simulate the logic from _create_llm
        actual_api_key = api_key if api_key is not None else OPENAI_API_KEY
        print(f"  actual_api_key after logic: '{actual_api_key}' (length: {len(actual_api_key)})")
        print(f"  bool(actual_api_key): {bool(actual_api_key)}")
        print(f"  actual_api_key.strip() == '': {actual_api_key.strip() == ''}")

def main():
    """Main test function"""

    print("="*60)
    print("Review Endpoint Diagnostic Test")
    print("="*60)

    # First, check environment configuration
    test_empty_string_vs_none()

    # Then test the actual endpoint process
    test_review_endpoint_with_params()

    print(f"\n{'='*60}")
    print("Diagnostic Complete")
    print(f"{'='*60}")
    print("Check the log file: test_review_endpoint.log")

if __name__ == "__main__":
    main()