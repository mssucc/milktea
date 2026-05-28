#!/usr/bin/env python3
"""Quick test to verify LLM responses with actual content display"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def quick_test():
    """Quick test of one LLM call with full response display"""

    print("\n" + "="*80)
    print("QUICK LLM RESPONSE TEST")
    print("="*80)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage

    # Configuration — read from environment variables
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("OPENAI_MODEL", "deepseek-chat")

    if not api_key:
        print("Error: OPENAI_API_KEY not set in .env or environment")
        return

    print(f"\nConfiguration:")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    print(f"  API Key: {api_key[:10]}...")

    # Create LLM
    print(f"\nCreating LLM...")
    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0.3,
        max_tokens=100,  # Short response for testing
        timeout=30.0,
    )

    # Test prompt (similar to summarizer but simplified)
    system_prompt = """You are an assistant. Respond with a short greeting."""
    user_prompt = """Hello, please respond with a short test message."""

    print(f"\nSystem Prompt: {system_prompt}")
    print(f"User Prompt: {user_prompt}")

    # Call LLM
    print(f"\nCalling LLM...")
    start_time = time.time()

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        elapsed = time.time() - start_time

        print(f"\n[SUCCESS] Response received in {elapsed:.2f}s")
        print(f"\nFull Response:")
        print("-"*40)
        print(response.content)
        print("-"*40)

        # Check response characteristics
        print(f"\nResponse Analysis:")
        print(f"  Length: {len(response.content)} characters")
        print(f"  First 200 chars: {response.content[:200]}")

        return True

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[FAILED] Error after {elapsed:.2f}s: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_json_response():
    """Test JSON response format (like what summarizer expects)"""

    print("\n" + "="*80)
    print("TESTING JSON RESPONSE FORMAT")
    print("="*80)

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage

    from dotenv import load_dotenv
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set in .env or environment")
        return
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("OPENAI_MODEL", "deepseek-chat")

    llm = ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0.3,
        max_tokens=300,
        timeout=30.0,
    )

    # Simpler version of summarizer prompt
    system_prompt = """Respond with a JSON object containing:
- "summary": a brief summary
- "key_points": a list of 2 key points
Keep it very short."""

    user_prompt = """Topic: machine learning basics. Provide JSON response."""

    print(f"\nSystem Prompt (simplified):")
    print(system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt)
    print(f"\nUser Prompt: {user_prompt}")

    print(f"\nCalling LLM for JSON response...")
    start_time = time.time()

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        elapsed = time.time() - start_time

        print(f"\n[SUCCESS] JSON response in {elapsed:.2f}s")
        print(f"\nResponse:")
        print("-"*40)
        print(response.content)
        print("-"*40)

        # Try to parse as JSON
        import json
        try:
            # Handle potential markdown code blocks
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            print(f"\n[PARSED] Valid JSON!")
            print(f"  Keys: {list(data.keys())}")
            if "summary" in data:
                print(f"  Summary length: {len(data['summary'])} chars")
            if "key_points" in data:
                print(f"  Key points: {len(data['key_points'])}")
            return True
        except json.JSONDecodeError as e:
            print(f"\n[WARNING] Response is not valid JSON: {e}")
            print(f"  Response may be in markdown or other format")
            return False

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n[FAILED] Error after {elapsed:.2f}s: {e}")
        return False

def main():
    """Main test function"""
    print("Quick LLM Response Test")
    print("="*80)

    # Test 1: Basic response
    print("\nTEST 1: Basic LLM call")
    success1 = quick_test()

    # Test 2: JSON response
    print("\nTEST 2: JSON format response")
    success2 = test_json_response()

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    if success1 and success2:
        print("\n[PASS] Both tests successful. LLM is responding correctly.")
        print("\nRecommendations:")
        print("1. Restart backend server to apply prompt logging changes")
        print("2. Test actual review endpoint with frontend")
        print("3. Check backend logs for detailed prompt/response info")
    else:
        print("\n[FAIL] Some tests failed.")
        print("\nCheck:")
        print("1. API key validity")
        print("2. Network connectivity to DeepSeek")
        print("3. Response format expectations")

    sys.exit(0 if (success1 and success2) else 1)

if __name__ == "__main__":
    main()