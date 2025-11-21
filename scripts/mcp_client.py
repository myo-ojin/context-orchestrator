#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP Client for Context Orchestrator

Simple JSON-RPC client for communicating with Context Orchestrator MCP server.
Supports stdio-based communication via subprocess.

Phase 3 Implementation for Issue #2025-11-15-01
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MCPClient:
    """
    MCP Client for Context Orchestrator.

    Communicates with Context Orchestrator MCP server via stdio JSON-RPC.
    """

    def __init__(self, context_orchestrator_path: Optional[str] = None):
        """
        Initialize MCP client.

        Args:
            context_orchestrator_path: Path to Context Orchestrator entry point
                                       Default: src/main.py in current directory
        """
        if context_orchestrator_path:
            self.orchestrator_path = Path(context_orchestrator_path)
        else:
            # Default to current project's src/main.py
            self.orchestrator_path = Path(__file__).parent.parent / 'src' / 'main.py'

        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0

    def _get_next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    def start(self):
        """
        Start Context Orchestrator MCP server process.

        Raises:
            RuntimeError: If server fails to start
        """
        if self.process is not None:
            logger.warning("MCP server already started")
            return

        # Start Context Orchestrator as subprocess
        try:
            # Use python from current environment
            python_executable = sys.executable

            self.process = subprocess.Popen(
                [python_executable, '-m', 'src.main'],
                cwd=self.orchestrator_path.parent.parent,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                encoding='utf-8'
            )

            logger.info(f"Started Context Orchestrator MCP server (PID: {self.process.pid})")

        except Exception as e:
            raise RuntimeError(f"Failed to start Context Orchestrator: {e}")

    def stop(self):
        """Stop Context Orchestrator MCP server process."""
        if self.process is None:
            return

        try:
            self.process.stdin.close()
            self.process.stdout.close()
            self.process.stderr.close()
            self.process.terminate()
            self.process.wait(timeout=5)
            logger.info("Stopped Context Orchestrator MCP server")
        except Exception as e:
            logger.warning(f"Error stopping MCP server: {e}")
            if self.process:
                self.process.kill()

        self.process = None

    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send JSON-RPC request to Context Orchestrator.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Response payload

        Raises:
            RuntimeError: If server is not started or communication fails
        """
        if self.process is None:
            raise RuntimeError("MCP server not started. Call start() first.")

        # Build JSON-RPC request
        request = {
            'jsonrpc': '2.0',
            'id': self._get_next_id(),
            'method': method,
            'params': params
        }

        request_json = json.dumps(request)

        try:
            # Send request
            self.process.stdin.write(request_json + '\n')
            self.process.stdin.flush()

            logger.debug(f"Sent request: {method} (id={request['id']})")

            # Read response
            response_line = self.process.stdout.readline()

            if not response_line:
                raise RuntimeError("No response from MCP server (stdout closed)")

            response = json.loads(response_line)

            # Check for errors
            if 'error' in response:
                error = response['error']
                raise RuntimeError(f"RPC error: {error.get('message', 'Unknown error')}")

            return response.get('result', {})

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"RPC communication error: {e}")
            raise

    def start_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new session in Context Orchestrator.

        Args:
            metadata: Optional session metadata (e.g., cwd, client, git_branch)

        Returns:
            Session ID
        """
        params = {}
        if metadata:
            params['metadata'] = metadata

        result = self._send_request('start_session', params)
        session_id = result.get('session_id')

        if not session_id:
            raise RuntimeError("No session_id returned from start_session")

        logger.info(f"Started session: {session_id}")
        return session_id

    def add_command(
        self,
        session_id: str,
        command: str,
        output: str,
        exit_code: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a command to a session.

        Args:
            session_id: Session ID
            command: Command executed
            output: Command output
            exit_code: Exit code (0 = success)
            metadata: Optional metadata (e.g., source, timestamp)

        Returns:
            True if successful
        """
        params = {
            'session_id': session_id,
            'command': command,
            'output': output,
            'exit_code': exit_code
        }

        if metadata:
            params['metadata'] = metadata

        result = self._send_request('add_command', params)
        success = result.get('success', False)

        logger.debug(f"Added command to session {session_id}: success={success}")
        return success

    def end_session(self, session_id: str) -> str:
        """
        End a session and trigger memory consolidation.

        Args:
            session_id: Session ID

        Returns:
            Memory ID
        """
        params = {'session_id': session_id}
        result = self._send_request('end_session', params)
        memory_id = result.get('memory_id')

        if not memory_id:
            raise RuntimeError("No memory_id returned from end_session")

        logger.info(f"Ended session {session_id}: memory_id={memory_id}")
        return memory_id

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def main():
    """Test MCP client."""
    import argparse

    parser = argparse.ArgumentParser(description='Test MCP client')
    parser.add_argument('--orchestrator-path', help='Path to Context Orchestrator main.py')
    args = parser.parse_args()

    from src.utils.logger import setup_logger
    setup_logger('mcp_client', 'DEBUG')

    # Test MCP client
    with MCPClient(args.orchestrator_path) as client:
        # Start session
        session_id = client.start_session(metadata={
            'client': 'test_client',
            'cwd': str(Path.cwd())
        })

        print(f"Session started: {session_id}")

        # Add commands
        client.add_command(
            session_id,
            command="echo 'Hello World'",
            output="Hello World",
            exit_code=0,
            metadata={'source': 'test'}
        )

        print("Command added")

        # End session
        memory_id = client.end_session(session_id)

        print(f"Session ended: memory_id={memory_id}")


if __name__ == '__main__':
    main()
