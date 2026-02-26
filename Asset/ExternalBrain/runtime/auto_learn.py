#!/usr/bin/env python3
"""Auto-learn: extract learnable patterns from Claude Code session transcripts.

Reads the most recent session transcript (.jsonl), detects problem-solving
patterns using heuristics (no LLM required), and creates Inbox candidates
via playbook_api.py learn.

Designed to run as a Stop hook in Claude Code.

Usage:
    python3 auto_learn.py                    # auto-detect latest transcript
    python3 auto_learn.py --transcript FILE  # explicit transcript path
    python3 auto_learn.py --dry-run          # show what would be created
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TRANSCRIPT_DIRS = [
    Path.home() / ".claude" / "projects",
]

# Heuristic thresholds
MIN_BASH_ERRORS = 1          # at least 1 failed command
MIN_EDITS_SAME_FILE = 2      # repeated edits to same file = trial-and-error
MIN_TOTAL_TOOL_CALLS = 5     # skip trivially short sessions

# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------


def find_latest_transcript() -> Optional[Path]:
    """Find the most recent .jsonl transcript across all project dirs."""
    candidates: list[tuple[float, Path]] = []
    for base in TRANSCRIPT_DIRS:
        if not base.is_dir():
            continue
        for project_dir in base.iterdir():
            if not project_dir.is_dir():
                continue
            for jsonl in project_dir.glob("*.jsonl"):
                candidates.append((jsonl.stat().st_mtime, jsonl))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def parse_transcript(path: Path) -> dict:
    """Parse a session transcript and extract signals for learning.

    Returns a dict with:
        tool_calls: list of {tool, input_summary, is_error, output_preview}
        bash_errors: list of {command, output_preview}
        edited_files: dict of {filepath: edit_count}
        assistant_texts: list of str (assistant text blocks)
        session_length: int (number of messages)
    """
    tool_calls: list[dict] = []
    bash_errors: list[dict] = []
    edited_files: dict[str, int] = {}
    assistant_texts: list[str] = []
    pending_tools: dict[str, dict] = {}  # tool_use_id -> tool info
    session_length = 0

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "")
            session_length += 1

            if msg_type == "assistant":
                content = msg.get("message", {}).get("content", [])
                for block in content:
                    if not isinstance(block, dict):
                        continue

                    if block.get("type") == "text":
                        text = block.get("text", "")
                        if text.strip():
                            assistant_texts.append(text.strip())

                    elif block.get("type") == "tool_use":
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {})
                        tool_id = block.get("id", "")

                        info = {
                            "tool": tool_name,
                            "input_summary": _summarize_tool_input(tool_name, tool_input),
                        }
                        pending_tools[tool_id] = info

                        if tool_name == "Edit":
                            fp = tool_input.get("file_path", "")
                            if fp:
                                edited_files[fp] = edited_files.get(fp, 0) + 1

            elif msg_type == "user":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, str):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_result":
                        tool_id = block.get("tool_use_id", "")
                        is_error = block.get("is_error", False)
                        output = block.get("content", "")
                        if isinstance(output, list):
                            output = " ".join(
                                b.get("text", "") for b in output
                                if isinstance(b, dict)
                            )
                        output_preview = str(output)[:500]

                        tool_info = pending_tools.pop(tool_id, {"tool": "?", "input_summary": ""})
                        tool_calls.append({
                            **tool_info,
                            "is_error": is_error,
                            "output_preview": output_preview,
                        })

                        if is_error and tool_info.get("tool") == "Bash":
                            bash_errors.append({
                                "command": tool_info.get("input_summary", ""),
                                "output_preview": output_preview,
                            })

    return {
        "tool_calls": tool_calls,
        "bash_errors": bash_errors,
        "edited_files": edited_files,
        "assistant_texts": assistant_texts,
        "session_length": session_length,
    }


def _summarize_tool_input(tool: str, inp: dict) -> str:
    if tool == "Bash":
        return inp.get("command", "")[:200]
    if tool == "Edit":
        return f"{inp.get('file_path', '')} (edit)"
    if tool == "Write":
        return f"{inp.get('file_path', '')} (write)"
    if tool == "Read":
        return inp.get("file_path", "")
    if tool == "Grep":
        return f"grep '{inp.get('pattern', '')}'"
    if tool == "Glob":
        return f"glob '{inp.get('pattern', '')}'"
    return str(list(inp.keys()))[:100]


# ---------------------------------------------------------------------------
# Pattern detection heuristics
# ---------------------------------------------------------------------------


def detect_patterns(parsed: dict) -> list[dict]:
    """Detect learnable patterns from parsed transcript data.

    Returns a list of dicts with:
        title: str
        body: str
        domain: str (may be empty)
        tags: list[str]
        signal: str (which heuristic triggered)
    """
    patterns: list[dict] = []

    if parsed["session_length"] < 3:
        return patterns  # trivially short session

    # --- Heuristic 1: Error → Fix cycle ---
    # Bash commands that failed, followed by edits, then success
    if parsed["bash_errors"]:
        error_commands = parsed["bash_errors"]
        fix_edits = [
            fp for fp, count in parsed["edited_files"].items()
            if count >= 1
        ]
        if fix_edits:
            error_summary = "\n".join(
                f"- `{e['command'][:120]}`\n  → {e['output_preview'][:200]}"
                for e in error_commands[:3]
            )
            fix_summary = "\n".join(f"- `{fp}`" for fp in fix_edits[:5])

            patterns.append({
                "title": _extract_error_title(error_commands[0]),
                "body": (
                    f"# Error → Fix Pattern\n\n"
                    f"## Errors Encountered\n{error_summary}\n\n"
                    f"## Files Modified\n{fix_summary}\n\n"
                    f"## Resolution\nセッション内でエラーが修正された。\n"
                    f"詳細はセッション transcript を参照。\n"
                ),
                "domain": "",
                "tags": ["error-fix", "auto-detected"],
                "signal": "error_fix_cycle",
            })

    # --- Heuristic 2: Trial-and-error on same file ---
    # Multiple edits to the same file suggest iterative problem-solving
    trial_files = {
        fp: count for fp, count in parsed["edited_files"].items()
        if count >= MIN_EDITS_SAME_FILE
    }
    if trial_files and not patterns:  # avoid duplicate if already caught by H1
        files_summary = "\n".join(
            f"- `{fp}` ({count} edits)" for fp, count in trial_files.items()
        )
        patterns.append({
            "title": f"Iterative fix in {list(trial_files.keys())[0].split('/')[-1]}",
            "body": (
                f"# Iterative Fix Pattern\n\n"
                f"## Files with multiple edits\n{files_summary}\n\n"
                f"## Context\n複数回の編集が同一ファイルに行われた。\n"
                f"試行錯誤の末に解決策が見つかった可能性あり。\n"
            ),
            "domain": "",
            "tags": ["iterative-fix", "auto-detected"],
            "signal": "trial_and_error",
        })

    # --- Heuristic 3: Infrastructure / deploy patterns ---
    # Terraform, Docker, AWS commands suggest infra knowledge
    infra_commands = [
        tc for tc in parsed["tool_calls"]
        if tc["tool"] == "Bash" and any(
            kw in tc["input_summary"].lower()
            for kw in ["terraform", "terragrunt", "docker", "aws ", "ecs", "ecr", "kubectl"]
        )
    ]
    if len(infra_commands) >= 3 and not patterns:
        cmds_summary = "\n".join(
            f"- `{c['input_summary'][:120]}`" for c in infra_commands[:5]
        )
        patterns.append({
            "title": "Infrastructure session activity",
            "body": (
                f"# Infrastructure Activity\n\n"
                f"## Commands\n{cmds_summary}\n\n"
                f"## Context\nインフラ関連の操作が集中的に行われた。\n"
            ),
            "domain": "infra",
            "tags": ["infra", "auto-detected"],
            "signal": "infra_activity",
        })

    return patterns


def _extract_error_title(error: dict) -> str:
    """Extract a concise title from an error."""
    cmd = error.get("command", "")
    output = error.get("output_preview", "")

    # Try to find an error message in the output
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Common error patterns
        if any(kw in line.lower() for kw in ["error", "failed", "not found", "permission denied"]):
            # Clean up and truncate
            clean = re.sub(r"\x1b\[[0-9;]*m", "", line)  # strip ANSI
            return clean[:100]

    # Fallback: use the command
    cmd_short = cmd.split("|")[0].strip()[:80]
    return f"Error in: {cmd_short}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto-learn: extract patterns from session transcripts"
    )
    parser.add_argument("--transcript", type=Path, default=None,
                        help="Path to session transcript .jsonl")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show detected patterns without creating Inbox entries")
    parser.add_argument("--vault", type=Path, default=None,
                        help="Path to ExternalBrain vault")
    args = parser.parse_args()

    # Find transcript
    transcript_path = args.transcript or find_latest_transcript()
    if not transcript_path or not transcript_path.is_file():
        # Silent exit — no transcript is not an error (e.g., fresh install)
        return 0

    # Parse
    parsed = parse_transcript(transcript_path)

    # Skip trivially short sessions
    total_tools = len(parsed["tool_calls"])
    if total_tools < MIN_TOTAL_TOOL_CALLS:
        return 0

    # Detect patterns
    patterns = detect_patterns(parsed)
    if not patterns:
        return 0

    if args.dry_run:
        print(f"Session: {transcript_path.name}")
        print(f"Tool calls: {total_tools}, Bash errors: {len(parsed['bash_errors'])}")
        print(f"Detected {len(patterns)} pattern(s):\n")
        for p in patterns:
            print(f"  [{p['signal']}] {p['title']}")
            print(f"    domain: {p['domain'] or '(none)'}")
            print(f"    tags: {p['tags']}")
            print()
        return 0

    # Create Inbox candidates via playbook_api
    runtime_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(runtime_dir))
    from playbook_api import PlaybookAPI, DEFAULT_VAULT

    vault = args.vault or DEFAULT_VAULT
    api = PlaybookAPI(vault=vault)

    created = 0
    for p in patterns:
        try:
            result = api.learn(
                title=p["title"],
                body=p["body"],
                domain=p["domain"],
                tags=p["tags"],
                source="auto",
            )
            created += 1
            print(f"Auto-learned: {result['inbox_file']}")
        except Exception as e:
            print(f"Warning: failed to create learning: {e}", file=sys.stderr)

    if created:
        print(f"Auto-learn: {created} pattern(s) saved to Inbox.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
