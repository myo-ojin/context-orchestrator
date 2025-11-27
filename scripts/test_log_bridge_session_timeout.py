#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for SessionTimeoutTracker in log_bridge.py

This script tests the session timeout functionality without
requiring chromadb or full Context Orchestrator initialization.
"""

import sys
import time
import threading
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class MockSessionManager:
    """Mock SessionManager for testing"""

    def __init__(self):
        self.sessions = {}
        self.ended_sessions = []

    def start_session(self, session_id: str):
        """Start a mock session"""
        self.sessions[session_id] = {
            'id': session_id,
            'started_at': datetime.now(),
            'commands': []
        }
        print(f"✓ Started session: {session_id[:8]}...")

    def end_session(self, session_id: str, create_obsidian_note: bool = False):
        """End a mock session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.ended_sessions.append(session_id)
            print(f"✓ Ended session: {session_id[:8]}... (create_note={create_obsidian_note})")
            return f"memory_{session_id[:8]}"
        return None


class SessionTimeoutTracker:
    """
    Track session activity and detect idle sessions
    (Copied from log_bridge.py for testing)
    """

    def __init__(self, session_manager, timeout_seconds: int = 600):
        """Initialize session timeout tracker"""
        self.last_activity = {}
        self.timeout_seconds = timeout_seconds
        self.session_manager = session_manager
        self._lock = threading.Lock()
        print(f"✓ Session timeout tracker initialized (timeout: {timeout_seconds}s)")

    def update_activity(self, session_id: str):
        """Update last activity timestamp for a session"""
        with self._lock:
            self.last_activity[session_id] = time.time()
            print(f"  Activity update: {session_id[:8]}...")

    def check_and_end_idle_sessions(self):
        """Check for idle sessions and end them"""
        with self._lock:
            now = time.time()
            idle_sessions = []

            for session_id, last_ts in list(self.last_activity.items()):
                idle_time = now - last_ts
                if idle_time > self.timeout_seconds:
                    idle_sessions.append((session_id, idle_time))

            # Remove from tracking
            for session_id, _ in idle_sessions:
                del self.last_activity[session_id]

        # End sessions
        for session_id, idle_time in idle_sessions:
            try:
                print(f"⏰ Ending idle session {session_id[:8]}... (idle for {idle_time:.1f}s)")
                memory_id = self.session_manager.end_session(session_id, create_obsidian_note=False)
                if memory_id:
                    print(f"✓ Session {session_id[:8]}... → Memory {memory_id[:8]}... (indexed)")
                else:
                    print(f"⚠ Session {session_id[:8]}... ended but no memory created")
            except Exception as e:
                print(f"✗ Error ending session {session_id[:8]}...: {e}")


def test_session_timeout():
    """Test the session timeout functionality"""
    print("=" * 60)
    print("Testing SessionTimeoutTracker")
    print("=" * 60)
    print()

    # Create mock session manager
    session_manager = MockSessionManager()

    # Create timeout tracker with 5 second timeout
    tracker = SessionTimeoutTracker(session_manager, timeout_seconds=5)
    print()

    # Scenario 1: Create active sessions
    print("Scenario 1: Create 3 sessions")
    session_manager.start_session("session-001")
    session_manager.start_session("session-002")
    session_manager.start_session("session-003")

    # Update activity for all sessions
    tracker.update_activity("session-001")
    tracker.update_activity("session-002")
    tracker.update_activity("session-003")
    print()

    # Scenario 2: Keep session-001 active, let others idle
    print("Scenario 2: Keep session-001 active, let others idle")
    time.sleep(3)  # Wait 3 seconds
    tracker.update_activity("session-001")  # Keep session-001 active
    print()

    # Scenario 3: Wait for timeout (5 seconds total)
    print("Scenario 3: Wait for timeout (2 more seconds)...")
    time.sleep(2)  # Total: 5 seconds for session-002 and session-003
    print()

    # Scenario 4: Check for idle sessions
    print("Scenario 4: Check for idle sessions")
    tracker.check_and_end_idle_sessions()
    print()

    # Verify results
    print("Results:")
    print(f"  Active sessions: {list(session_manager.sessions.keys())}")
    print(f"  Ended sessions: {session_manager.ended_sessions}")
    print()

    # Expected: session-002 and session-003 should be ended
    expected_ended = 2
    actual_ended = len(session_manager.ended_sessions)

    if actual_ended == expected_ended:
        print(f"✓ TEST PASSED: {actual_ended}/{expected_ended} idle sessions ended")
    else:
        print(f"✗ TEST FAILED: {actual_ended}/{expected_ended} idle sessions ended")

    # Scenario 5: Let session-001 idle and check again
    print()
    print("Scenario 5: Let session-001 idle (5 seconds)...")
    time.sleep(5)
    tracker.check_and_end_idle_sessions()
    print()

    print("Final Results:")
    print(f"  Active sessions: {list(session_manager.sessions.keys())}")
    print(f"  Ended sessions: {session_manager.ended_sessions}")

    if len(session_manager.ended_sessions) == 3:
        print("✓ ALL TESTS PASSED")
    else:
        print(f"✗ SOME TESTS FAILED: {len(session_manager.ended_sessions)}/3 sessions ended")


if __name__ == "__main__":
    test_session_timeout()
