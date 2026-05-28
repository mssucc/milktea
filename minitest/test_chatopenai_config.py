#!/usr/bin/env python3
"""Test ChatOpenAI configuration for DeepSeek API"""

import sys
import os
import asyncio
import logging

# Add parent directory to path to import backend modules if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    print(f"Error importing langchain: {e}")
    print("Make sure langchain-openai is installed: pip install langchain-openai")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_chatopenai_direct(
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    timeout: int = 30
):
    """Test ChatOpenAI directly with given configuration"""

    print(f"\n{'='*60}")
    print("Testing ChatOpenAI Configuration")
    print(f"{'='*60}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
    print(f"Timeout: {timeout}s")

    try:
        # Test without /v1 suffix
        print(f"\nTesting with base_url: {base_url}")
        llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.7,
            max_tokens=50,
            timeout=timeout,
            max_retries=1,
        )

        print("Sending test message...")
        response = llm.invoke([HumanMessage(content="Hello, please respond with a short greeting.")])

        print(f"\n✅ Success with base_url: {base_url}")
        print(f"Response: {response.content}")

        return {
            "success": True,
            "base_url": base_url,
            "response": response.content,
            "error": None
        }

    except Exception as e:
        print(f"\n❌ Error with base_url {base_url}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "base_url": base_url,
            "response": None,
            "error": str(e),
            "error_type": type(e).__name__
        }

def test_chatopenai_with_v1(
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    timeout: int = 30
):
    """Test ChatOpenAI with /v1 suffix added to base_url"""

    # Ensure base_url ends with /v1
    if not base_url.endswith('/v1'):
        base_url_with_v1 = f"{base_url}/v1" if not base_url.endswith('/') else f"{base_url}v1"
    else:
        base_url_with_v1 = base_url

    print(f"\n{'='*60}")
    print("Testing ChatOpenAI with /v1 suffix")
    print(f"{'='*60}")
    print(f"Original base_url: {base_url}")
    print(f"Modified base_url: {base_url_with_v1}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
    print(f"Timeout: {timeout}s")

    try:
        llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url_with_v1,
            model=model,
            temperature=0.7,
            max_tokens=50,
            timeout=timeout,
            max_retries=1,
        )

        print("Sending test message...")
        response = llm.invoke([HumanMessage(content="Hello, please respond with a short greeting.")])

        print(f"\n✅ Success with base_url: {base_url_with_v1}")
        print(f"Response: {response.content}")

        return {
            "success": True,
            "original_base_url": base_url,
            "actual_base_url": base_url_with_v1,
            "response": response.content,
            "error": None
        }

    except Exception as e:
        print(f"\n❌ Error with base_url {base_url_with_v1}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "original_base_url": base_url,
            "actual_base_url": base_url_with_v1,
            "response": None,
            "error": str(e),
            "error_type": type(e).__name__
        }

def main():
    """Main test function"""

    # Get API key from command line or environment
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            print("Please provide API key as argument or set OPENAI_API_KEY environment variable")
            print("Usage: python test_chatopenai_config.py <api_key>")
            sys.exit(1)

    # Configuration
    base_url = "https://api.deepseek.com"
    model = "deepseek-chat"
    timeout = 30

    print("="*60)
    print("ChatOpenAI Configuration Test for DeepSeek API")
    print("="*60)

    # Test 1: Direct base_url (without /v1)
    result1 = test_chatopenai_direct(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout
    )

    # Test 2: With /v1 suffix
    result2 = test_chatopenai_with_v1(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout
    )

    # Summary
    print(f"\n{'='*60}")
    print("Test Summary:")
    print(f"{'='*60}")
    print(f"Test 1 - Direct URL ({base_url}): {'✅ SUCCESS' if result1['success'] else '❌ FAILED'}")
    if not result1['success']:
        print(f"  Error: {result1['error']}")
        print(f"  Type: {result1['error_type']}")

    print(f"Test 2 - URL with /v1 ({base_url}/v1): {'✅ SUCCESS' if result2['success'] else '❌ FAILED'}")
    if not result2['success']:
        print(f"  Error: {result2['error']}")
        print(f"  Type: {result2['error_type']}")

    # Recommendations
    print(f"\n{'='*60}")
    print("Recommendations:")
    print(f"{'='*60}")
    if result1['success']:
        print("✅ Use direct URL (without /v1) in summarizer.py and review_generator.py")
    elif result2['success']:
        print("✅ Use URL with /v1 suffix in summarizer.py and review_generator.py")
        print("  Need to modify _create_llm function to add /v1 if not present")
    else:
        print("❌ Both configurations failed")
        print("  Check API key validity and network connectivity")
        print("  Consider increasing timeout value")

if __name__ == "__main__":
    main()