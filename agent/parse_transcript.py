"""
Parse Claude Code JSONL transcript into a readable summary.
Usage: uv run python parse_transcript.py
"""
import json
import sys
from collections import defaultdict
from datetime import datetime

TRANSCRIPT_PATH = r"C:\Users\19050\.claude\projects\d--Desktop-milktea\933697cc-e2dd-4fbe-96f3-e7c5770c9153.jsonl"
OUTPUT_PATH = "d:/Desktop/milktea/transcript_analysis.txt"
DETAIL_LIMIT = 1500  # Only show detailed log for first N lines

stats = {
    "total_lines": 0,
    "message_types": defaultdict(int),
    "user_messages": 0,
    "assistant_messages": 0,
    "assistant_thinking": 0,
    "assistant_text": 0,
    "tool_calls": defaultdict(int),
    "tool_results": 0,
    "file_reads": [],
    "files_searched": [],
    "files_grepped": [],
    "total_tokens": {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0},
    "sessions": set(),
    "models": defaultdict(int),
    "content_block_types": defaultdict(int),
    "user_text_messages": [],
}

MIN_TS = None
MAX_TS = None
output_lines = []

def log(msg):
    output_lines.append(msg)

def log_detail(msg):
    if stats["total_lines"] <= DETAIL_LIMIT:
        output_lines.append(msg)

def analyze_line(line_num, obj):
    global MIN_TS, MAX_TS

    stats["total_lines"] += 1
    msg_type = obj.get("type", "unknown")
    stats["message_types"][msg_type] += 1

    ts = obj.get("timestamp", "")
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if MIN_TS is None or dt < MIN_TS:
                MIN_TS = dt
            if MAX_TS is None or dt > MAX_TS:
                MAX_TS = dt
        except ValueError:
            pass

    sid = obj.get("sessionId", "")
    if sid:
        stats["sessions"].add(sid)

    if msg_type == "user":
        stats["user_messages"] += 1
        msg = obj.get("message", {})
        content = msg.get("content", [])
        for block in content:
            if isinstance(block, str):
                stats["content_block_types"]["user.raw_string"] += 1
                continue
            block_type = block.get("type", "")
            stats["content_block_types"][f"user.{block_type}"] += 1

            if block_type == "tool_result":
                stats["tool_results"] += 1
                result_content = block.get("content", "")
                if isinstance(result_content, str) and result_content:
                    preview = result_content[:200].replace("\n", "\\n")
                    log_detail(f"  [tool_result] {preview}")
                elif isinstance(result_content, list):
                    log_detail(f"  [tool_result] list with {len(result_content)} items")
            elif block_type == "text":
                text = block.get("text", "")
                if text and not text.startswith("<ide_"):
                    stats["user_text_messages"].append(text[:300])
                    log_detail(f"  [user_input] {text[:300]}")

    elif msg_type == "assistant":
        stats["assistant_messages"] += 1
        msg = obj.get("message", {})
        model = msg.get("model", "unknown")
        stats["models"][model] += 1
        content = msg.get("content", [])
        usage = msg.get("usage", {})

        if usage:
            stats["total_tokens"]["input"] += usage.get("input_tokens", 0)
            stats["total_tokens"]["output"] += usage.get("output_tokens", 0)
            stats["total_tokens"]["cache_read"] += usage.get("cache_read_input_tokens", 0)
            stats["total_tokens"]["cache_creation"] += usage.get("cache_creation_input_tokens", 0)

        for block in content:
            if isinstance(block, str):
                stats["content_block_types"]["assistant.raw_string"] += 1
                continue
            block_type = block.get("type", "")
            stats["content_block_types"][f"assistant.{block_type}"] += 1

            if block_type == "thinking":
                stats["assistant_thinking"] += 1
                thinking_text = block.get("thinking", "")[:200].replace("\n", "\\n")
                log_detail(f"  [thinking] ({model}) {thinking_text}")
            elif block_type == "text":
                stats["assistant_text"] += 1
                log_detail(f"  [assistant_text] ({model}) {block.get('text', '')[:200]}")
            elif block_type == "tool_use":
                tool_name = block.get("name", "unknown")
                stats["tool_calls"][tool_name] += 1
                tool_input = block.get("input", {})

                fp = tool_input.get("file_path", "") or tool_input.get("path", "")
                pattern = tool_input.get("pattern", "")
                grep_pattern = tool_input.get("pattern", "")

                if tool_name == "Read" and fp:
                    stats["file_reads"].append(fp)
                    log_detail(f"  [tool_use] Read: {fp}")
                elif tool_name == "Glob" and pattern:
                    stats["files_searched"].append(pattern)
                    log_detail(f"  [tool_use] Glob: {pattern}")
                elif tool_name == "Grep":
                    stats["files_grepped"].append(f"pattern={grep_pattern} in {tool_input.get('path','')}")
                    log_detail(f"  [tool_use] Grep: {grep_pattern} in {tool_input.get('path','')}")
                else:
                    log_detail(f"  [tool_use] {tool_name}: {json.dumps(tool_input, ensure_ascii=False)[:200]}")

    elif msg_type == "file-history-snapshot":
        pass  # skip detail for these

    elif msg_type == "ai-title":
        title = obj.get("aiTitle", "")
        log_detail(f"  [ai_title] {title}")

    elif msg_type == "queue-operation":
        pass  # skip detail

    else:
        log_detail(f"  [unknown_type] {json.dumps(obj, ensure_ascii=False)[:300]}")


# === Main ===
log("=" * 80)
log("CLAUDE CODE TRANSCRIPT ANALYSIS")
log("=" * 80)
log(f"Source: {TRANSCRIPT_PATH}")
log(f"Lines with detailed logging: first {DETAIL_LIMIT}")
log("")

print("Reading JSONL...", file=sys.stderr)

with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            log_detail(f"\n--- Line {i} | type={obj.get('type','?')} | {obj.get('timestamp','')[:19]} ---")
            analyze_line(i, obj)
        except json.JSONDecodeError as e:
            log_detail(f"\n--- Line {i} | JSON PARSE ERROR: {e} ---")

        if i % 10000 == 0:
            print(f"  Processed {i:,} lines...", file=sys.stderr)

print(f"  Done. Total: {stats['total_lines']:,} lines", file=sys.stderr)

# === Summary ===
log("")
log("=" * 80)
log("SUMMARY STATISTICS")
log("=" * 80)
log(f"Total JSONL lines: {stats['total_lines']:,}")
if MIN_TS and MAX_TS:
    log(f"Time span: {MIN_TS.isoformat()} to {MAX_TS.isoformat()}")
    log(f"Duration: {MAX_TS - MIN_TS}")
log(f"Unique session IDs: {len(stats['sessions'])}")
for sid in sorted(stats['sessions']):
    log(f"  {sid}")
log("")
log("=== Message type distribution ===")
for mtype, count in sorted(stats['message_types'].items(), key=lambda x: -x[1]):
    log(f"  {mtype}: {count:,}")
log("")
log("=== Models used ===")
for model, count in sorted(stats['models'].items(), key=lambda x: -x[1]):
    log(f"  {model}: {count:,} calls")
log("")
log("=== Content block types ===")
for bt, count in sorted(stats['content_block_types'].items(), key=lambda x: -x[1]):
    log(f"  {bt}: {count:,}")
log("")
log(f"User text messages: {len(stats['user_text_messages'])}")
log(f"User messages (incl. tool results): {stats['user_messages']:,}")
log(f"Assistant messages: {stats['assistant_messages']:,}")
log(f"  with 'thinking' blocks: {stats['assistant_thinking']:,}")
log(f"  with 'text' blocks: {stats['assistant_text']:,}")
log(f"Tool results: {stats['tool_results']:,}")
log("")
log("=== Tool call distribution ===")
for tname, count in sorted(stats['tool_calls'].items(), key=lambda x: -x[1]):
    log(f"  {tname}: {count:,}")
log("")
log("=== Token usage ===")
log(f"  Input tokens: {stats['total_tokens']['input']:,}")
log(f"  Output tokens: {stats['total_tokens']['output']:,}")
log(f"  Cache read tokens: {stats['total_tokens']['cache_read']:,}")
log(f"  Cache creation tokens: {stats['total_tokens']['cache_creation']:,}")
log("")
log(f"=== Unique files read ({len(set(stats['file_reads']))} total) ===")
for fp in sorted(set(stats['file_reads']))[:150]:
    log(f"  {fp}")
remaining = len(set(stats['file_reads'])) - 150
if remaining > 0:
    log(f"  ... and {remaining} more files")
log("")
log(f"=== Glob patterns ({len(set(stats['files_searched']))} total) ===")
for pat in sorted(set(stats['files_searched'])):
    log(f"  {pat}")
log("")
log(f"=== Grep searches ({len(stats['files_grepped'])} total, showing first 50) ===")
for g in stats['files_grepped'][:50]:
    log(f"  {g}")
log("")
log("=== User input messages (all) ===")
for i, msg in enumerate(stats['user_text_messages'], 1):
    log(f"  [{i}] {msg}")

# Write output
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print(f"Output written to: {OUTPUT_PATH}", file=sys.stderr)
print(f"Output lines: {len(output_lines):,}", file=sys.stderr)
