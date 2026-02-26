"""Tests for auto_learn.py — parse_transcript and detect_patterns."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auto_learn import parse_transcript, detect_patterns


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _write_transcript(tmp_path: Path, messages: list[dict]) -> Path:
    """Write a list of message dicts as a .jsonl transcript."""
    fp = tmp_path / "session.jsonl"
    with open(fp, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    return fp


def _tool_use_block(tool_id: str, name: str, inp: dict) -> dict:
    return {"type": "tool_use", "id": tool_id, "name": name, "input": inp}


def _tool_result_block(tool_id: str, output: str, is_error: bool = False) -> dict:
    return {"type": "tool_result", "tool_use_id": tool_id, "content": output, "is_error": is_error}


def _make_session(tool_calls: list[tuple[str, str, dict, str, bool]]) -> list[dict]:
    """Build a session from a list of (tool_id, tool_name, input, output, is_error)."""
    messages = []
    for tid, name, inp, output, is_error in tool_calls:
        messages.append({
            "type": "assistant",
            "message": {"content": [_tool_use_block(tid, name, inp)]},
        })
        messages.append({
            "type": "user",
            "message": {"content": [_tool_result_block(tid, output, is_error)]},
        })
    return messages


# ---------------------------------------------------------------------------
# TestParseTranscript
# ---------------------------------------------------------------------------

class TestParseTranscript:

    def test_parse_empty_file(self, tmp_path: Path):
        fp = tmp_path / "empty.jsonl"
        fp.write_text("", encoding="utf-8")
        result = parse_transcript(fp)
        assert result["session_length"] == 0
        assert result["tool_calls"] == []

    def test_parse_bash_error(self, tmp_path: Path):
        messages = _make_session([
            ("t1", "Bash", {"command": "npm run build"}, "Error: Module not found", True),
            ("t2", "Edit", {"file_path": "/app/src/main.ts"}, "ok", False),
        ])
        fp = _write_transcript(tmp_path, messages)
        result = parse_transcript(fp)
        assert len(result["tool_calls"]) == 2
        assert len(result["bash_errors"]) == 1
        assert result["bash_errors"][0]["command"] == "npm run build"
        assert "/app/src/main.ts" in result["edited_files"]

    def test_parse_multiple_edits_same_file(self, tmp_path: Path):
        messages = _make_session([
            ("t1", "Edit", {"file_path": "/app/foo.ts"}, "ok", False),
            ("t2", "Edit", {"file_path": "/app/foo.ts"}, "ok", False),
            ("t3", "Edit", {"file_path": "/app/foo.ts"}, "ok", False),
        ])
        fp = _write_transcript(tmp_path, messages)
        result = parse_transcript(fp)
        assert result["edited_files"]["/app/foo.ts"] == 3


# ---------------------------------------------------------------------------
# TestDetectPatterns
# ---------------------------------------------------------------------------

class TestDetectPatterns:

    def test_detect_error_fix_cycle(self):
        parsed = {
            "tool_calls": [
                {"tool": "Bash", "input_summary": "npm run build", "is_error": True, "output_preview": "Error: not found"},
                {"tool": "Edit", "input_summary": "/app/main.ts (edit)", "is_error": False, "output_preview": "ok"},
                {"tool": "Bash", "input_summary": "npm run build", "is_error": False, "output_preview": "ok"},
            ],
            "bash_errors": [{"command": "npm run build", "output_preview": "Error: not found"}],
            "edited_files": {"/app/main.ts": 1},
            "assistant_texts": ["Let me fix this"],
            "session_length": 6,
        }
        patterns = detect_patterns(parsed)
        assert len(patterns) >= 1
        assert patterns[0]["signal"] == "error_fix_cycle"

    def test_no_patterns_short_session(self):
        parsed = {
            "tool_calls": [],
            "bash_errors": [],
            "edited_files": {},
            "assistant_texts": [],
            "session_length": 2,
        }
        patterns = detect_patterns(parsed)
        assert patterns == []

    def test_detect_trial_and_error(self):
        parsed = {
            "tool_calls": [
                {"tool": "Edit", "input_summary": "/app/config.ts (edit)", "is_error": False, "output_preview": "ok"},
            ] * 5,
            "bash_errors": [],
            "edited_files": {"/app/config.ts": 5},
            "assistant_texts": ["Trying another approach"],
            "session_length": 10,
        }
        patterns = detect_patterns(parsed)
        assert len(patterns) >= 1
        assert patterns[0]["signal"] == "trial_and_error"

    def test_detect_infra_activity(self):
        parsed = {
            "tool_calls": [
                {"tool": "Bash", "input_summary": "terraform plan", "is_error": False, "output_preview": "ok"},
                {"tool": "Bash", "input_summary": "terraform apply", "is_error": False, "output_preview": "ok"},
                {"tool": "Bash", "input_summary": "aws ecs describe-services", "is_error": False, "output_preview": "ok"},
            ],
            "bash_errors": [],
            "edited_files": {},
            "assistant_texts": ["Deploying infra"],
            "session_length": 6,
        }
        patterns = detect_patterns(parsed)
        assert len(patterns) >= 1
        assert patterns[0]["signal"] == "infra_activity"
