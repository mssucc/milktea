"""
Deep-dive analysis of JSONL data completeness.
Check: Are tool_results truncated in the JSONL itself, or just in my previous script?
Focus on a small sample of complete exchange cycles.
"""
import json
from collections import defaultdict

TRANSCRIPT_PATH = r"C:\Users\19050\.claude\projects\d--Desktop-milktea\933697cc-e2dd-4fbe-96f3-e7c5770c9153.jsonl"
OUTPUT_PATH = r"d:\Desktop\milktea\transcript_completeness.txt"

lines_out = []

def log(s=""):
    lines_out.append(s)

# Statistics
tool_result_lengths = []
truncation_markers = 0
read_results = []  # (line_num, file_path, content_length, content_preview)
samples = []  # full exchange cycles

# Parse and collect stats
log("=" * 80)
log("JSONL DATA COMPLETENESS ANALYSIS")
log("=" * 80)
log(f"Source: {TRANSCRIPT_PATH}")
log("")

with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg_type = obj.get("type", "")
        if msg_type != "user":
            continue

        msg = obj.get("message", {})
        content = msg.get("content", [])
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_result":
                continue

            result_content = block.get("content", "")
            if isinstance(result_content, str):
                length = len(result_content)
                tool_result_lengths.append(length)
                if "truncated" in result_content.lower() or "Results are truncated" in result_content:
                    truncation_markers += 1
            elif isinstance(result_content, list):
                tool_result_lengths.append(len(result_content))

        if i % 10000 == 0:
            print(f"  Processed {i:,} lines...")

print(f"  Done. Total: {i:,} lines", flush=True)

# Analysis
log("=== TOOL RESULT COMPLETENESS ===")
log(f"Total tool_result blocks: {len(tool_result_lengths)}")
log(f"Tool results with truncation markers: {truncation_markers}")
log("")

if tool_result_lengths:
    total_chars = sum(tool_result_lengths)
    avg_len = total_chars / len(tool_result_lengths)
    sorted_lengths = sorted(tool_result_lengths)
    log(f"Content length statistics:")
    log(f"  Total characters: {total_chars:,}")
    log(f"  Average: {avg_len:,.0f} chars")
    log(f"  Min: {sorted_lengths[0]:,}")
    log(f"  P25: {sorted_lengths[len(sorted_lengths)//4]:,}")
    log(f"  Median: {sorted_lengths[len(sorted_lengths)//2]:,}")
    log(f"  P75: {sorted_lengths[len(sorted_lengths)*3//4]:,}")
    log(f"  P95: {sorted_lengths[int(len(sorted_lengths)*0.95)]:,}")
    log(f"  Max: {sorted_lengths[-1]:,}")

    # Distribution buckets
    buckets = defaultdict(int)
    for length in tool_result_lengths:
        if length < 100:
            buckets["<100 chars"] += 1
        elif length < 500:
            buckets["100-500"] += 1
        elif length < 2000:
            buckets["500-2K"] += 1
        elif length < 10000:
            buckets["2K-10K"] += 1
        elif length < 50000:
            buckets["10K-50K"] += 1
        else:
            buckets[">50K"] += 1
    log("")
    log("Length distribution:")
    for bucket in ["<100 chars", "100-500", "500-2K", "2K-10K", "10K-50K", ">50K"]:
        count = buckets[bucket]
        pct = count / len(tool_result_lengths) * 100
        log(f"  {bucket}: {count:,} ({pct:.1f}%)")

# Now extract 3 complete exchange cycles (not truncated in output)
log("")
log("=" * 80)
log("SAMPLE: COMPLETE EXCHANGE CYCLES (FULL CONTENT)")
log("=" * 80)

cycles = []
current_cycle = []
in_assistant_turn = False
cycle_count = 0

with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        msg_type = obj.get("type", "")
        if msg_type == "user":
            msg = obj.get("message", {})
            content = msg.get("content", [])
            has_real_text = False
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text and not text.startswith("<ide_"):
                        has_real_text = True
                        break
            if has_real_text and not in_assistant_turn:
                if current_cycle and cycle_count < 3:
                    cycles.append(current_cycle)
                    cycle_count += 1
                current_cycle = []
                in_assistant_turn = True
            current_cycle.append((i, obj))
        elif msg_type == "assistant":
            in_assistant_turn = True
            current_cycle.append((i, obj))
        else:
            if in_assistant_turn and msg_type not in ("file-history-snapshot", "queue-operation"):
                current_cycle.append((i, obj))

    if current_cycle and cycle_count < 3:
        cycles.append(current_cycle)

log(f"Extracted {len(cycles)} sample cycles")
log("")

for ci, cycle in enumerate(cycles, 1):
    log(f"{'='*80}")
    log(f"CYCLE {ci} ({len(cycle)} messages)")
    log(f"{'='*80}")
    for line_num, obj in cycle[:30]:  # limit per cycle
        msg_type = obj.get("type", "?")
        ts = obj.get("timestamp", "")[:19]
        log(f"\n--- Line {line_num} | {msg_type} | {ts} ---")

        if msg_type == "user":
            msg = obj.get("message", {})
            for block in msg.get("content", []):
                if not isinstance(block, dict):
                    log(f"  [raw_string] {str(block)[:500]}")
                    continue
                bt = block.get("type", "")
                if bt == "text":
                    text = block.get("text", "")
                    if text and not text.startswith("<ide_"):
                        log(f"  [user_input] {text}")
                elif bt == "tool_result":
                    rc = block.get("content", "")
                    if isinstance(rc, str):
                        log(f"  [tool_result] LENGTH={len(rc)} chars")
                        log(f"  [tool_result] FULL CONTENT:")
                        log(rc)
                    elif isinstance(rc, list):
                        log(f"  [tool_result] list with {len(rc)} items")
                        for item in rc[:5]:
                            log(f"    - {str(item)[:200]}")
        elif msg_type == "assistant":
            msg = obj.get("message", {})
            model = msg.get("model", "?")
            for block in msg.get("content", []):
                if not isinstance(block, dict):
                    continue
                bt = block.get("type", "")
                if bt == "thinking":
                    log(f"  [thinking] ({model}) LENGTH={len(block.get('thinking',''))} chars")
                    log(f"  [thinking] FULL:")
                    log(block.get("thinking", ""))
                elif bt == "text":
                    log(f"  [assistant_text] ({model}) FULL:")
                    log(block.get("text", ""))
                elif bt == "tool_use":
                    log(f"  [tool_use] {block.get('name','?')}: {json.dumps(block.get('input',{}), ensure_ascii=False)}")

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines_out))

print(f"\nOutput written to: {OUTPUT_PATH}")
