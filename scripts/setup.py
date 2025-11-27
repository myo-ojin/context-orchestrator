#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup Wizard

Interactive setup wizard for Context Orchestrator.

Requirements: Requirement 13 (Deployment and Operations)
"""

import sys
import os
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config, save_config
from src.utils.logger import setup_logger

logger = setup_logger('setup', 'INFO')


class SetupWizard:
    """Interactive setup wizard"""

    def __init__(self):
        """Initialize setup wizard"""
        self.config = Config()

    def print_header(self):
        """Print header"""
        print()
        print("=" * 60)
        print("Context Orchestrator Setup Wizard")
        print("=" * 60)
        print()

    def check_ollama(self) -> bool:
        """
        Check if Ollama is installed and running

        Returns:
            True if Ollama is ready
        """
        print("Step 1: Checking Ollama...")
        print()

        # Check if ollama command exists
        try:
            result = subprocess.run(
                ['ollama', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                print(f"✓ Ollama is installed: {result.stdout.strip()}")
            else:
                print("✗ Ollama is not installed")
                print()
                print("Please install Ollama: https://ollama.ai/")
                return False

        except FileNotFoundError:
            print("✗ Ollama is not installed")
            print()
            print("Please install Ollama: https://ollama.ai/")
            return False

        except Exception as e:
            print(f"✗ Failed to check Ollama: {e}")
            return False

        # Check if Ollama is running
        try:
            import requests

            response = requests.get(f"{self.config.ollama.url}/api/tags", timeout=5)

            if response.status_code == 200:
                print(f"✓ Ollama is running at {self.config.ollama.url}")
                return True
            else:
                print(f"✗ Ollama is not responding (status {response.status_code})")
                print()
                print("Please start Ollama: ollama serve")
                return False

        except Exception:
            print("✗ Ollama is not running")
            print()
            print("Please start Ollama: ollama serve")
            return False

    def install_models(self) -> bool:
        """
        Install required models

        Returns:
            True if models are installed
        """
        print()
        print("Step 2: Installing required models...")
        print()

        models = [
            self.config.ollama.embedding_model,
            self.config.ollama.inference_model
        ]

        # Check installed models
        try:
            import requests

            response = requests.get(f"{self.config.ollama.url}/api/tags", timeout=5)
            data = response.json()
            installed_models = [model['name'] for model in data.get('models', [])]

        except Exception as e:
            print(f"✗ Failed to list models: {e}")
            return False

        # Install missing models
        for model in models:
            if model in installed_models:
                print(f"✓ Model already installed: {model}")
            else:
                print(f"Installing model: {model}")
                print(f"  (This may take several minutes...)")

                try:
                    result = subprocess.run(
                        ['ollama', 'pull', model],
                        capture_output=False,
                        timeout=600  # 10 minutes
                    )

                    if result.returncode == 0:
                        print(f"✓ Model installed: {model}")
                    else:
                        print(f"✗ Failed to install model: {model}")
                        return False

                except subprocess.TimeoutExpired:
                    print(f"✗ Timeout installing model: {model}")
                    return False

                except Exception as e:
                    print(f"✗ Failed to install model: {e}")
                    return False

        return True

    def configure_paths(self):
        """Configure paths"""
        print()
        print("Step 3: Configuring paths...")
        print()

        # Data directory
        default_data_dir = str(Path.home() / '.context-orchestrator')
        data_dir = input(f"Data directory [{default_data_dir}]: ").strip()

        if data_dir:
            self.config.data_dir = data_dir
        else:
            self.config.data_dir = default_data_dir

        # Create data directory
        data_path = Path(self.config.data_dir)
        data_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created data directory: {data_path}")

        # Obsidian vault (optional)
        print()
        use_obsidian = input("Do you use Obsidian? [y/N]: ").strip().lower()

        if use_obsidian in ['y', 'yes']:
            vault_path = input("Obsidian vault path: ").strip()

            if vault_path and Path(vault_path).exists():
                self.config.obsidian_vault_path = vault_path
                print(f"✓ Obsidian vault: {vault_path}")
            else:
                print("✗ Vault path not found, skipping")
                self.config.obsidian_vault_path = None
        else:
            self.config.obsidian_vault_path = None

    def configure_cli_command(self):
        """Configure CLI command"""
        print()
        print("Step 4: Configure CLI command")
        print()
        print("PowerShell wrappers now record both claude and codex automatically.")
        print("Cloud-side CLI calls will default to claude (edit config.yaml later if needed).")
        self.config.cli.command = 'claude'
        print(f"✁ECLI command defaulted to: {self.config.cli.command}")

    def save_configuration(self):
        """Save configuration"""
        print()
        print("Step 5: Saving configuration...")
        print()

        config_path = Path(self.config.data_dir) / 'config.yaml'

        try:
            save_config(self.config, str(config_path))
            print(f"✓ Configuration saved: {config_path}")
            return True

        except Exception as e:
            print(f"✗ Failed to save config: {e}")
            return False


    def install_cli_wrapper(self) -> bool:
        """Install PowerShell CLI recording wrapper"""
        print()
        print("Step 6: Installing CLI recording wrapper...")
        print()

        script_path = Path(__file__).parent / 'setup_cli_recording.ps1'
        if not script_path.exists():
            print(f"✁EWrapper script not found: {script_path}")
            return False

        if os.name != 'nt':
            print("⚠ PowerShell wrapper installation skipped (non-Windows host).")
            print("   Run the script manually on Windows to capture CLI sessions.")
            return True

        try:
            result = subprocess.run(
                [
                    'powershell',
                    '-NoLogo',
                    '-ExecutionPolicy',
                    'Bypass',
                    '-File',
                    str(script_path),
                    '-Install',
                    '-Force'
                ],
                check=False
            )
            if result.returncode == 0:
                print("✓ CLI recording wrapper installed.")
                return True

            print(f"✗ CLI recording wrapper exited with code {result.returncode}. Re-run the script above if needed.")
            return False

        except FileNotFoundError:
            print("✁EPowerShell executable not found. Install PowerShell 7+ or run the wrapper manually later.")
            return False
        except Exception as exc:
            print(f"✁EFailed to run wrapper installer: {exc}")
            return False

    def print_next_steps(self):
        """Print next steps"""
        print()
        print("=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print()
        print("1. Test the system:")
        print("   python scripts/doctor.py")
        print()
        print("2. Start Context Orchestrator:")
        print("   python -m src.main")
        print()
        print("3. Re-run the CLI wrapper installer anytime you reset your PowerShell profile:")
        print("   powershell -ExecutionPolicy Bypass -File scripts/setup_cli_recording.ps1 -Install -Force")
        print()
        print("Note: The CLI wrapper now auto-starts the log bridge for session monitoring.")
        print("      Restart PowerShell to activate all features.")
        print()

    def run(self) -> bool:
        """
        Run setup wizard

        Returns:
            True if setup succeeded
        """
        self.print_header()

        # Check Ollama
        if not self.check_ollama():
            return False

        # Install models
        if not self.install_models():
            return False

        # Configure paths
        self.configure_paths()

        # Configure CLI command
        self.configure_cli_command()

        # Save configuration
        if not self.save_configuration():
            return False

        wrapper_ok = self.install_cli_wrapper()
        if not wrapper_ok:
            print("⚠ CLI recording wrapper installation encountered an issue. Re-run the script above to retry.")

        # Print next steps
        self.print_next_steps()

        return True


def main():
    """Main entry point"""
    wizard = SetupWizard()
    success = wizard.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
