#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CLI-based Cloud LLM Client

Provides text generation using cloud LLMs via CLI (claude/codex).
Sets CONTEXT_ORCHESTRATOR_INTERNAL=1 to prevent recursive recording.

Requirements: Requirement 10 (MVP - Model Routing)
"""

import os
import subprocess
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CLICallError(Exception):
    """Raised when CLI call fails"""
    pass


class CLILLMClient:
    """
    Client for cloud LLM via CLI (claude/codex)

    This client invokes the user's existing CLI tools (claude or codex)
    in a subprocess with CONTEXT_ORCHESTRATOR_INTERNAL=1 to prevent
    the Context Orchestrator from recording its own internal calls.

    Attributes:
        cli_command: CLI command to use (claude or codex)
    """

    def __init__(self, cli_command: str = "claude"):
        """
        Initialize CLI LLM client

        Args:
            cli_command: CLI command to use (default: claude)
        """
        self.cli_command = cli_command

        # Verify CLI is available
        self._check_cli_available()

        logger.info(f"Initialized CLILLMClient with command: {self.cli_command}")

    def _check_cli_available(self) -> None:
        """
        Check if CLI command is available

        Raises:
            CLICallError: If CLI command is not found
        """
        # Check if command exists in PATH
        try:
            # Use 'where' on Windows, 'which' on Unix
            check_cmd = "where" if os.name == "nt" else "which"
            result = subprocess.run(
                [check_cmd, self.cli_command],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                logger.warning(f"CLI command '{self.cli_command}' not found in PATH")
                # Don't raise here - let it fail on actual usage
                # This allows setup to proceed even if CLI isn't installed yet
            else:
                logger.debug(f"CLI command '{self.cli_command}' found: {result.stdout.strip()}")

        except Exception as e:
            logger.warning(f"Could not verify CLI availability: {e}")

    def generate(
        self,
        prompt: str,
        timeout: int = 60,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text via CLI

        Args:
            prompt: Input prompt
            timeout: Timeout in seconds (default: 60)
            max_tokens: Maximum tokens (not implemented - depends on CLI)

        Returns:
            Generated text

        Raises:
            CLICallError: If CLI call fails

        Example:
            >>> client = CLILLMClient(cli_command="claude")
            >>> result = client.generate("Summarize this conversation: ...")
            >>> print(result)
            "The conversation discusses implementation of ..."
        """
        try:
            return self._call_cli_background(prompt, timeout)

        except Exception as e:
            logger.error(f"CLI generation failed: {e}")
            raise CLICallError(f"Failed to generate via {self.cli_command}: {e}") from e

    def _call_cli_background(self, prompt: str, timeout: int) -> str:
        """
        Call CLI in background with CONTEXT_ORCHESTRATOR_INTERNAL=1

        This prevents the PowerShell wrapper from recording the
        orchestrator's internal calls, which would cause infinite loops.

        Args:
            prompt: Input prompt
            timeout: Timeout in seconds

        Returns:
            CLI output (generated text)

        Raises:
            subprocess.TimeoutExpired: If timeout is exceeded
            subprocess.CalledProcessError: If CLI returns non-zero exit code
        """
        # Prepare environment with internal flag
        env = os.environ.copy()
        env['CONTEXT_ORCHESTRATOR_INTERNAL'] = '1'  # Prevent recording

        # Write prompt to temporary file for long prompts
        # (avoids command-line length limits)
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            suffix='.txt',
            delete=False
        ) as tmp_file:
            tmp_file.write(prompt)
            tmp_path = tmp_file.name

        try:
            # Build command
            # Use prompt from file to avoid shell escaping issues
            if os.name == "nt":  # Windows
                # PowerShell command to read file and pass to CLI
                cmd = [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Get-Content -Path '{tmp_path}' -Raw | {self.cli_command}"
                ]
            else:  # Unix
                cmd = [
                    "bash",
                    "-c",
                    f"cat '{tmp_path}' | {self.cli_command}"
                ]

            logger.debug(f"Calling CLI: {self.cli_command} (timeout={timeout}s)")
            logger.debug(f"Prompt length: {len(prompt)} chars")

            # Execute CLI command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                encoding='utf-8'
            )

            # Check for errors
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                logger.error(f"CLI exited with code {result.returncode}: {error_msg}")
                raise subprocess.CalledProcessError(
                    result.returncode,
                    cmd,
                    output=result.stdout,
                    stderr=result.stderr
                )

            output = result.stdout.strip()
            logger.debug(f"CLI output length: {len(output)} chars")
            logger.debug(f"CLI output preview: {output[:200]}...")

            return output

        except subprocess.TimeoutExpired as e:
            logger.error(f"CLI call timed out after {timeout}s")
            raise CLICallError(f"CLI call timed out after {timeout}s") from e

        except subprocess.CalledProcessError as e:
            logger.error(f"CLI call failed: {e.stderr}")
            raise CLICallError(f"CLI call failed: {e.stderr}") from e

        finally:
            # Clean up temporary file
            try:
                Path(tmp_path).unlink()
                logger.debug(f"Cleaned up temporary file: {tmp_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {tmp_path}: {e}")

    def generate_with_fallback(
        self,
        prompt: str,
        fallback_text: str = "Error: Could not generate response",
        timeout: int = 60
    ) -> str:
        """
        Generate text with fallback on error

        This is useful for non-critical tasks where a fallback is acceptable.

        Args:
            prompt: Input prompt
            fallback_text: Text to return on error
            timeout: Timeout in seconds

        Returns:
            Generated text, or fallback_text on error

        Example:
            >>> client = CLILLMClient()
            >>> result = client.generate_with_fallback(
            ...     "Summarize: ...",
            ...     fallback_text="[Summary unavailable]"
            ... )
        """
        try:
            return self.generate(prompt, timeout=timeout)
        except Exception as e:
            logger.warning(f"CLI generation failed, using fallback: {e}")
            return fallback_text
