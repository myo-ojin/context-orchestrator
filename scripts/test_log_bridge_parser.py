#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for log_bridge.py file parsing functions

Tests parse_rollout_event() and parse_claude_project_event()
"""

import sys
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Import from log_bridge
sys.path.insert(0, 'scripts')


def test_parse_rollout_event():
    """Test parsing Codex rollout events"""
    print("=" * 60)
    print("Testing parse_rollout_event()")
    print("=" * 60)
    print()

    # Sample data from actual Codex rollout file
    sample_events = [
        # User message
        {
            "type": "event_msg",
            "timestamp": "2025-11-27T12:00:00Z",
            "payload": {
                "type": "user_message",
                "message": "Hello, can you help me?"
            }
        },
        # Agent message
        {
            "type": "event_msg",
            "timestamp": "2025-11-27T12:00:05Z",
            "payload": {
                "type": "agent_message",
                "message": "Of course! I'd be happy to help."
            }
        },
        # Other event (should be skipped)
        {
            "type": "event_msg",
            "timestamp": "2025-11-27T12:00:10Z",
            "payload": {
                "type": "agent_reasoning",
                "message": "Thinking about the response..."
            }
        },
        # Empty message (should be skipped)
        {
            "type": "event_msg",
            "timestamp": "2025-11-27T12:00:15Z",
            "payload": {
                "type": "user_message",
                "message": ""
            }
        }
    ]

    file_path = "rollout-2025-11-27T12-00-00-abc123.jsonl"

    from log_bridge import parse_rollout_event

    results = []
    for i, event in enumerate(sample_events):
        line = json.dumps(event)
        result = parse_rollout_event(line, file_path)
        print(f"Event {i+1}: {event['payload'].get('type', 'unknown')}")
        if result:
            session_id, role, text, ts = result
            print(f"  ✓ Parsed: session_id={session_id}, role={role}, text='{text[:30]}...', ts={ts}")
            results.append(result)
        else:
            print(f"  - Skipped (not a message or empty)")
        print()

    print(f"Results: {len(results)}/4 events parsed (expected: 2)")
    print()

    if len(results) == 2:
        print("✓ TEST PASSED")
        return True
    else:
        print("✗ TEST FAILED")
        return False


def test_parse_claude_project_event():
    """Test parsing Claude project events"""
    print("=" * 60)
    print("Testing parse_claude_project_event()")
    print("=" * 60)
    print()

    # Sample data from Claude project log
    sample_events = [
        # User message
        {
            "type": "user",
            "timestamp": "2025-11-27T12:00:00Z",
            "message": {
                "content": "What is the weather today?"
            }
        },
        # Assistant message
        {
            "type": "response",
            "timestamp": "2025-11-27T12:00:05Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I don't have access to real-time weather data."}
                ]
            }
        },
        # File snapshot (should be skipped)
        {
            "type": "file-history-snapshot",
            "timestamp": "2025-11-27T12:00:10Z",
            "files": []
        }
    ]

    file_path = "xyz789.jsonl"

    from log_bridge import parse_claude_project_event

    results = []
    for i, event in enumerate(sample_events):
        line = json.dumps(event)
        result = parse_claude_project_event(line, file_path)
        print(f"Event {i+1}: {event.get('type', 'unknown')}")
        if result:
            session_id, role, text, ts = result
            print(f"  ✓ Parsed: session_id={session_id}, role={role}, text='{text[:30]}...', ts={ts}")
            results.append(result)
        else:
            print(f"  - Skipped (not a message)")
        print()

    print(f"Results: {len(results)}/3 events parsed (expected: 2)")
    print()

    if len(results) == 2:
        print("✓ TEST PASSED")
        return True
    else:
        print("✗ TEST FAILED")
        return False


if __name__ == "__main__":
    test1_passed = test_parse_rollout_event()
    print()
    test2_passed = test_parse_claude_project_event()
    print()

    if test1_passed and test2_passed:
        print("=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
    else:
        print("=" * 60)
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
