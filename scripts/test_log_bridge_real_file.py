#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test log_bridge.py with real rollout file
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'scripts')
from log_bridge import parse_rollout_event

def test_real_rollout_file():
    """Test parsing a real rollout file"""
    print("=" * 60)
    print("Testing with real rollout file")
    print("=" * 60)
    print()

    file_path = r'C:\Users\ryomy\.codex\sessions\2025\11\08\rollout-2025-11-08T19-51-59-019a6318-2a47-7692-889d-f99b4fc182e3.jsonl'

    print(f"File: {file_path}")
    print()

    messages = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            result = parse_rollout_event(line.strip(), file_path)
            if result:
                session_id, role, text, ts = result
                messages.append(result)
                print(f"Line {i+1}: {role:10s} | {text[:60]}...")

    print()
    print(f"Total messages parsed: {len(messages)}")

    if len(messages) > 0:
        print()
        print("Sample messages:")
        for i, (session_id, role, text, ts) in enumerate(messages[:3]):
            print(f"{i+1}. [{role}] {text[:100]}...")

        print()
        print(f"Session ID: {session_id}")
        print(f"✓ Successfully parsed {len(messages)} messages from real file")
        return True
    else:
        print("✗ No messages parsed")
        return False


if __name__ == "__main__":
    test_real_rollout_file()
