"""Test graph API response for value fields"""
import requests
import json
import sys

def test_graph_api():
    base_url = "http://localhost:8000/api"

    try:
        # First get a session ID from chat sessions or use existing
        # For simplicity, check global graph
        print("Testing global graph endpoint...")
        response = requests.get(f"{base_url}/graph/global?limit=5")

        if response.status_code == 200:
            data = response.json()
            print(f"Response status: {response.status_code}")
            print(f"Number of nodes: {len(data.get('nodes', []))}")
            print(f"Number of edges: {len(data.get('edges', []))}")

            # Check first node properties
            nodes = data.get('nodes', [])
            if nodes:
                first_node = nodes[0]
                print("\nFirst node properties:")
                for key, value in first_node.items():
                    print(f"  {key}: {value}")

                # Check for required fields
                required_fields = ['value', 'mention_count', 'importance']
                missing = [field for field in required_fields if field not in first_node]
                if missing:
                    print(f"\nWARNING: Missing fields: {missing}")
                else:
                    print(f"\nOK: All required fields present")
                    print(f"  value: {first_node.get('value')}")
                    print(f"  mention_count: {first_node.get('mention_count')}")
                    print(f"  importance: {first_node.get('importance')}")
            else:
                print("No nodes in response")
        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("Failed to connect to API server. Make sure backend is running.")
        print("Start backend with: uv run python -m backend.main")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_graph_api()