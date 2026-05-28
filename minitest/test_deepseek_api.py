#!/usr/bin/env python3
"""Test DeepSeek API connectivity using OpenAI-compatible client"""

import sys
import os
import json
import asyncio
import logging
from typing import Dict, Any

# Add parent directory to path to import backend modules if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Error: 'openai' package not found. Install with: pip install openai")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_deepseek_api(
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    timeout: int = 30
) -> Dict[str, Any]:
    """Test DeepSeek API connectivity with given credentials"""

    print(f"\n{'='*60}")
    print("Testing DeepSeek API Connectivity")
    print(f"{'='*60}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
    print(f"Timeout: {timeout}s")

    try:
        # Initialize client
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

        print("\nSending test message...")

        # Send a simple test message
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello, please respond with a short greeting."}
            ],
            max_tokens=50,
            stream=False,
        )

        # Extract response
        if response and response.choices:
            message = response.choices[0].message.content
            usage = response.usage

            print(f"\n✅ Success! API is working.")
            print(f"Response: {message}")
            print(f"Model used: {response.model}")
            print(f"Tokens used: {usage.total_tokens if usage else 'N/A'}")

            return {
                "success": True,
                "message": message,
                "model": response.model,
                "usage": {
                    "total_tokens": usage.total_tokens if usage else 0,
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                },
                "raw_response": response
            }
        else:
            print("\n❌ Error: No response received")
            return {"success": False, "error": "No response received"}

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "type": type(e).__name__}

def main():
    """Main function to test API connectivity"""

    # Get configuration from environment or user input
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com")
    model = os.environ.get("OPENAI_MODEL", "deepseek-chat")

    # Check if API key is provided
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it with: export OPENAI_API_KEY='your-api-key'")
        print("Or provide it as an argument.")

        # Try to read from .env file
        env_file = os.path.join(os.path.dirname(__file__), "../../.env")
        if os.path.exists(env_file):
            print(f"\nChecking .env file: {env_file}")
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith("OPENAI_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"\'')
                            print(f"Found API key in .env file: {api_key[:10]}...")
                            break
            except Exception as e:
                print(f"Error reading .env file: {e}")

    # If still no API key, prompt user
    if not api_key:
        try:
            api_key = input("\nEnter your DeepSeek API key (or press Enter to skip): ").strip()
            if not api_key:
                print("No API key provided. Exiting.")
                return
        except KeyboardInterrupt:
            print("\nCancelled by user.")
            return

    # Test with custom parameters if provided
    if len(sys.argv) > 1:
        # Parse command line arguments
        import argparse
        parser = argparse.ArgumentParser(description="Test DeepSeek API connectivity")
        parser.add_argument("--api-key", help="API key for DeepSeek")
        parser.add_argument("--base-url", default=base_url, help="Base URL for API")
        parser.add_argument("--model", default=model, help="Model to use")
        parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")

        args = parser.parse_args()

        if args.api_key:
            api_key = args.api_key

        result = test_deepseek_api(
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            timeout=args.timeout
        )
    else:
        # Use environment/default values
        result = test_deepseek_api(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=30
        )

    # Print summary
    print(f"\n{'='*60}")
    print("Test Summary:")
    print(f"{'='*60}")
    print(f"Success: {result.get('success', False)}")
    if not result.get('success'):
        print(f"Error: {result.get('error', 'Unknown error')}")
        print(f"Error type: {result.get('type', 'Unknown')}")

    # Exit with appropriate code
    sys.exit(0 if result.get('success') else 1)

if __name__ == "__main__":
    main()