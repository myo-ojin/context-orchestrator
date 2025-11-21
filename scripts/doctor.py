#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
System Health Check Tool (Doctor)

Checks system health and provides remediation steps.

Requirements: Requirement 13 (Troubleshooting)
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_config
from src.utils.logger import setup_logger

logger = setup_logger('doctor', 'INFO')


class HealthCheck:
    """System health checker"""

    def __init__(self):
        """Initialize health checker"""
        try:
            self.config = load_config()
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            self.config = None

        self.checks = []
        self.passed = 0
        self.failed = 0

    def check_ollama_running(self) -> Tuple[bool, str, List[str]]:
        """
        Check if Ollama is running

        Returns:
            Tuple of (success, message, remediation_steps)
        """
        try:
            import requests

            if self.config:
                url = self.config.ollama.url
            else:
                url = "http://localhost:11434"

            response = requests.get(f"{url}/api/tags", timeout=5)

            if response.status_code == 200:
                return True, f"Ollama is running at {url}", []
            else:
                return False, f"Ollama returned status {response.status_code}", [
                    "Check Ollama logs for errors",
                    f"Try restarting: ollama serve"
                ]

        except requests.exceptions.ConnectionError:
            return False, "Ollama is not running", [
                "Start Ollama: ollama serve",
                "Or install Ollama: https://ollama.ai/"
            ]

        except Exception as e:
            return False, f"Failed to connect to Ollama: {e}", [
                "Check Ollama is installed",
                "Check Ollama is running: ollama serve"
            ]

    def check_ollama_models(self) -> Tuple[bool, str, List[str]]:
        """
        Check if required models are installed

        Returns:
            Tuple of (success, message, remediation_steps)
        """
        try:
            import requests

            if self.config:
                url = self.config.ollama.url
                embedding_model = self.config.ollama.embedding_model
                inference_model = self.config.ollama.inference_model
            else:
                url = "http://localhost:11434"
                embedding_model = "nomic-embed-text"
                inference_model = "qwen2.5:7b"

            response = requests.get(f"{url}/api/tags", timeout=5)

            if response.status_code != 200:
                return False, "Failed to list Ollama models", [
                    "Check Ollama is running: ollama serve"
                ]

            data = response.json()
            installed_models = [model['name'] for model in data.get('models', [])]

            # Extract base model names (without tags like :latest)
            installed_model_bases = [model.split(':')[0] for model in installed_models]

            missing_models = []

            # Check models by base name (ignore tags)
            embedding_base = embedding_model.split(':')[0]
            inference_base = inference_model.split(':')[0]

            if embedding_base not in installed_model_bases:
                missing_models.append(embedding_model)

            if inference_base not in installed_model_bases:
                missing_models.append(inference_model)

            if missing_models:
                remediation = [
                    f"Install missing model: ollama pull {model}"
                    for model in missing_models
                ]

                return False, f"Missing models: {', '.join(missing_models)}", remediation
            else:
                return True, f"Required models installed: {embedding_model}, {inference_model}", []

        except Exception as e:
            return False, f"Failed to check models: {e}", [
                "Check Ollama is running: ollama serve"
            ]

    def check_data_directory(self) -> Tuple[bool, str, List[str]]:
        """
        Check if data directory exists and is writable

        Returns:
            Tuple of (success, message, remediation_steps)
        """
        try:
            if self.config:
                data_dir = Path(self.config.data_dir)
            else:
                data_dir = Path.home() / '.context-orchestrator'

            # Check if directory exists
            if not data_dir.exists():
                return False, f"Data directory does not exist: {data_dir}", [
                    f"Create directory: mkdir {data_dir}"
                ]

            # Check if writable
            test_file = data_dir / '.write_test'
            try:
                test_file.write_text('test', encoding='utf-8')
                test_file.unlink()
            except Exception:
                return False, f"Data directory is not writable: {data_dir}", [
                    f"Check permissions: ls -la {data_dir.parent}"
                ]

            return True, f"Data directory OK: {data_dir}", []

        except Exception as e:
            return False, f"Failed to check data directory: {e}", []

    def check_chroma_db(self) -> Tuple[bool, str, List[str]]:
        """
        Check if Chroma DB is accessible

        Returns:
            Tuple of (success, message, remediation_steps)
        """
        try:
            if self.config:
                data_dir = Path(self.config.data_dir)
            else:
                data_dir = Path.home() / '.context-orchestrator'

            chroma_path = data_dir / 'chroma_db'

            if not chroma_path.exists():
                return True, f"Chroma DB will be created on first run: {chroma_path}", []

            # Try to load Chroma DB
            try:
                import chromadb

                client = chromadb.PersistentClient(path=str(chroma_path))
                collections = client.list_collections()

                return True, f"Chroma DB OK: {len(collections)} collections", []

            except Exception as e:
                return False, f"Chroma DB error: {e}", [
                    f"Try removing corrupted DB: rm -rf {chroma_path}",
                    "WARNING: This will delete all memories"
                ]

        except Exception as e:
            return False, f"Failed to check Chroma DB: {e}", []

    def check_config_file(self) -> Tuple[bool, str, List[str]]:
        """
        Check if config file exists

        Returns:
            Tuple of (success, message, remediation_steps)
        """
        config_paths = [
            Path.home() / '.context-orchestrator' / 'config.yaml',
            Path('config.yaml')
        ]

        for config_path in config_paths:
            if config_path.exists():
                return True, f"Config file found: {config_path}", []

        return False, "Config file not found (using defaults)", [
            "Create config file: cp config.yaml.template ~/.context-orchestrator/config.yaml",
            "Edit config: nano ~/.context-orchestrator/config.yaml"
        ]

    def check_codex_logs(self) -> Tuple[bool, str, List[str]]:
        """
        Check if Codex logs directory exists and contains sessions

        Returns:
            Tuple of (success, message, remediation_steps)
        """
        try:
            codex_home = Path(os.environ.get('USERPROFILE', '~')).expanduser() / '.codex'
            sessions_dir = codex_home / 'sessions'

            if not sessions_dir.exists():
                # Codex not installed is OK (user may only use Claude)
                return True, "Codex CLI not installed (optional)", []

            # Count session files
            session_files = list(sessions_dir.glob('**/rollout-*.jsonl'))
            count = len(session_files)

            if count == 0:
                return True, "Codex directory exists (no sessions yet)", []
            else:
                return True, f"Codex sessions found: {count} session logs", []

        except Exception as e:
            return False, f"Failed to check Codex logs: {e}", []

    def run_all_checks(self) -> bool:
        """
        Run all health checks

        Returns:
            True if all checks passed
        """
        checks = [
            ("Ollama Running", self.check_ollama_running),
            ("Ollama Models", self.check_ollama_models),
            ("Data Directory", self.check_data_directory),
            ("Chroma DB", self.check_chroma_db),
            ("Config File", self.check_config_file),
            ("Codex Logs", self.check_codex_logs)
        ]

        print("=" * 60)
        print("Context Orchestrator Health Check")
        print("=" * 60)
        print()

        for name, check_func in checks:
            print(f"Checking {name}...", end=" ")

            try:
                success, message, remediation = check_func()

                if success:
                    print("[PASS]")
                    print(f"  {message}")
                    self.passed += 1
                else:
                    print("[FAIL]")
                    print(f"  {message}")

                    if remediation:
                        print("  Remediation:")
                        for step in remediation:
                            print(f"    - {step}")

                    self.failed += 1

                print()

            except Exception as e:
                print("[ERROR]")
                print(f"  {e}")
                self.failed += 1
                print()

        # Summary
        print("=" * 60)
        print(f"Summary: {self.passed} passed, {self.failed} failed")
        print("=" * 60)

        return self.failed == 0


def main():
    """Main entry point"""
    checker = HealthCheck()
    success = checker.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
