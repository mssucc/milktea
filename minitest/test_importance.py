"""Test importance weight mechanism"""
import json
import os
import sys
from pathlib import Path

# Add project root directory to path to import backend modules
project_root = Path(__file__).parent.parent / "agent"
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from backend.graph_db.knowledge_extractor import KNOWLEDGE_EXTRACTION_PROMPT

def test_prompt_format():
    """Test that prompt includes importance instructions"""
    print("=" * 60)
    print("Testing Importance Prompt Format")
    print("=" * 60)

    # Check prompt contains importance instructions
    assert "importance" in KNOWLEDGE_EXTRACTION_PROMPT.lower(), "Prompt should mention importance"
    assert '"importance": 1-5' in KNOWLEDGE_EXTRACTION_PROMPT, "Prompt should include importance field in JSON format"

    # Check JSON format includes importance
    lines = KNOWLEDGE_EXTRACTION_PROMPT.split('\n')
    json_start = -1
    for i, line in enumerate(lines):
        if '"entities": [' in line:
            json_start = i
            break

    if json_start != -1:
        # Look for importance field in the JSON example
        for i in range(json_start, min(json_start + 20, len(lines))):
            if '"importance": 1-5' in lines[i]:
                print("[OK] Importance field found in JSON format")
                break
        else:
            print("[WARNING] Importance field NOT found in JSON format")
    else:
        print("⚠ Could not find JSON format in prompt")

    print("\nPrompt snippet containing importance instructions:")
    for line in KNOWLEDGE_EXTRACTION_PROMPT.split('\n'):
        if 'importance' in line.lower():
            print(f"  {line}")

    print("\nJSON format snippet:")
    for line in KNOWLEDGE_EXTRACTION_PROMPT.split('\n'):
        if '"importance"' in line or '"entities": [' in line or '"relationships": [' in line:
            print(f"  {line}")

def test_json_parsing():
    """Test parsing of importance field from JSON"""
    print("\n" + "=" * 60)
    print("Testing JSON Parsing with Importance")
    print("=" * 60)

    # Sample JSON with importance
    sample_json = '''{
        "entities": [
            {"name": "Machine Learning", "type": "concept", "description": "AI subset", "importance": 5},
            {"name": "Python", "type": "tool", "description": "Programming language", "importance": 3},
            {"name": "Data Science", "type": "concept", "description": "Field of study", "importance": 4}
        ],
        "relationships": [
            {"source": "Machine Learning", "target": "Data Science", "type": "includes", "description": "ML is part of Data Science"}
        ]
    }'''

    try:
        data = json.loads(sample_json)
        entities = data.get("entities", [])

        print(f"Parsed {len(entities)} entities:")
        for entity in entities:
            name = entity.get("name", "unknown")
            importance = entity.get("importance", 1)
            print(f"  {name}: importance={importance} (type={type(importance)})")

            # Test importance clamping (1-5)
            if 1 <= importance <= 5:
                print(f"    [OK] Importance within valid range (1-5)")
            else:
                print(f"    [WARNING] Importance outside valid range: {importance}")

        print("\n[OK] JSON parsing with importance successful")

    except Exception as e:
        print(f"[ERROR] JSON parsing failed: {e}")

if __name__ == "__main__":
    test_prompt_format()
    test_json_parsing()
    print("\n" + "=" * 60)
    print("Importance Mechanism Test Complete")
    print("=" * 60)