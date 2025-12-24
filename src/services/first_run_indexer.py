#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
First-Run Log Indexer

Handles optional indexing of existing session logs on first run.
Provides size estimates, progress tracking, and resumable indexing.

Requirements: PLAN_FIRST_RUN_INDEX.md
"""

import sys
import os
import json
import time
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Set
from datetime import datetime

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default ignore patterns (not configurable)
DEFAULT_IGNORE_PATTERNS = {'.*', '_*', '*.tmp'}


def check_first_run_flag(data_dir: str) -> bool:
    """
    Check if first-run indexing has already been completed.

    Args:
        data_dir: Data directory path

    Returns:
        True if first-run indexing has been completed, False otherwise
    """
    flag_file = Path(data_dir) / 'first_run_index_done'
    return flag_file.exists()


def mark_first_run_complete(data_dir: str) -> None:
    """
    Mark first-run indexing as complete by creating the flag file.

    Args:
        data_dir: Data directory path
    """
    flag_file = Path(data_dir) / 'first_run_index_done'
    flag_file.write_text(datetime.now().isoformat(), encoding='utf-8')
    logger.info(f"Marked first-run indexing as complete: {flag_file}")


def should_run_first_run_indexing(data_dir: str, enabled: bool = True) -> bool:
    """
    Determine if first-run indexing should run.

    Checks:
    1. If feature is enabled in config
    2. If flag file exists (skip if exists)
    3. Environment variable CO_FIRST_RUN_AUTO for non-interactive mode

    Args:
        data_dir: Data directory path
        enabled: Whether first-run indexing is enabled in config

    Returns:
        True if first-run indexing should run, False otherwise
    """
    # Check if feature is enabled
    if not enabled:
        logger.debug("First-run indexing is disabled in config")
        return False

    # Check if already completed
    if check_first_run_flag(data_dir):
        logger.debug("First-run indexing already completed, skipping")
        return False

    # Check if stdin is interactive
    if not sys.stdin.isatty():
        # Non-interactive mode: check environment variable
        auto_run = os.environ.get('CO_FIRST_RUN_AUTO', '0')
        if auto_run == '1':
            logger.info("Non-interactive mode with CO_FIRST_RUN_AUTO=1, running first-run indexing")
            return True
        else:
            logger.info("Non-interactive mode without CO_FIRST_RUN_AUTO=1, skipping first-run indexing")
            return False

    # Interactive mode: will prompt user (handled in later task)
    return True


def _should_include_file(file_path: Path, max_size_bytes: int, allowed_extensions: Set[str]) -> bool:
    """
    Check if a file should be included in indexing.

    Args:
        file_path: Path to the file
        max_size_bytes: Maximum file size in bytes
        allowed_extensions: Set of allowed file extensions

    Returns:
        True if file should be included, False otherwise
    """
    # Check extension
    if file_path.suffix.lower() not in allowed_extensions:
        return False

    # Check if file matches ignore patterns
    name = file_path.name
    if name.startswith('.') or name.startswith('_') or name.endswith('.tmp'):
        return False

    # Check file size
    try:
        size = file_path.stat().st_size
        if size > max_size_bytes:
            logger.debug(f"Skipping {file_path} (size {size} > {max_size_bytes})")
            return False
        if size == 0:
            logger.debug(f"Skipping {file_path} (empty file)")
            return False
    except OSError as e:
        logger.warning(f"Cannot stat {file_path}: {e}")
        return False

    return True


def scan_log_directory(
    session_log_dir: str,
    max_file_size_mb: int,
    allowed_extensions: List[str]
) -> Tuple[List[Path], int]:
    """
    Scan log directory for candidate files.

    Args:
        session_log_dir: Session log directory path
        max_file_size_mb: Maximum file size in MB
        allowed_extensions: List of allowed file extensions

    Returns:
        Tuple of (candidate_files, total_bytes)
    """
    log_dir = Path(session_log_dir)
    if not log_dir.exists():
        logger.warning(f"Log directory does not exist: {log_dir}")
        return [], 0

    max_size_bytes = max_file_size_mb * 1024 * 1024
    allowed_ext_set = set(ext.lower() if ext.startswith('.') else f'.{ext.lower()}' for ext in allowed_extensions)
    candidates = []
    total_bytes = 0

    # Walk directory recursively
    for file_path in log_dir.rglob('*'):
        if not file_path.is_file():
            continue

        if _should_include_file(file_path, max_size_bytes, allowed_ext_set):
            candidates.append(file_path)
            total_bytes += file_path.stat().st_size

    return candidates, total_bytes


def _format_size(bytes_size: int) -> str:
    """Format byte size as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def _estimate_time(total_bytes: int) -> str:
    """
    Estimate indexing time based on total bytes.

    Rough estimate: ~10 MB/sec processing speed.
    """
    if total_bytes == 0:
        return "< 1 second"

    # Estimate processing speed: 10 MB/sec
    total_mb = total_bytes / (1024 * 1024)
    seconds = total_mb / 10

    if seconds < 1:
        return "< 1 second"
    elif seconds < 60:
        return f"~{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"~{minutes} minute{'s' if minutes > 1 else ''}"
    else:
        hours = int(seconds / 3600)
        return f"~{hours} hour{'s' if hours > 1 else ''}"


def prompt_user_for_indexing(file_count: int, total_bytes: int) -> bool:
    """
    Prompt user to approve first-run indexing.

    Args:
        file_count: Number of candidate files
        total_bytes: Total size in bytes

    Returns:
        True if user approves, False otherwise
    """
    if file_count == 0:
        logger.info("No session logs found to index")
        return False

    size_str = _format_size(total_bytes)
    time_str = _estimate_time(total_bytes)

    print("\n" + "=" * 60)
    print("FIRST-RUN LOG INDEXING")
    print("=" * 60)
    print(f"Found {file_count} session log file{'s' if file_count != 1 else ''}")
    print(f"Total size: {size_str}")
    print(f"Estimated time: {time_str}")
    print()
    print("This is a one-time operation to index existing session logs.")
    print("You can skip this and the system will only index new sessions.")
    print("=" * 60)

    # Prompt user
    while True:
        try:
            response = input("Index existing logs now? [y/N]: ").strip().lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no', '']:
                logger.info("User declined first-run indexing")
                return False
            else:
                print("Please enter 'y' or 'n'")
        except (EOFError, KeyboardInterrupt):
            print()
            logger.info("User cancelled first-run indexing prompt")
            return False


class IndexingCheckpoint:
    """Manages checkpoint state for resumable first-run indexing."""

    def __init__(self, data_dir: str):
        """
        Initialize checkpoint manager.

        Args:
            data_dir: Data directory path
        """
        self.checkpoint_file = Path(data_dir) / 'first_run_index_checkpoint.json'
        self.processed: Dict[str, Dict[str, any]] = {}
        self.load()

    def load(self) -> None:
        """Load checkpoint from disk if it exists."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed = data.get('processed', {})
                logger.info(f"Loaded checkpoint: {len(self.processed)} files already processed")
            except Exception as e:
                logger.warning(f"Failed to load checkpoint: {e}")
                self.processed = {}
        else:
            logger.debug("No checkpoint file found, starting fresh")

    def save(self) -> None:
        """Save checkpoint to disk."""
        try:
            data = {
                'processed': self.processed,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved checkpoint: {len(self.processed)} files processed")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def is_processed(self, file_path: Path) -> bool:
        """
        Check if a file has already been processed.

        Uses mtime + size for quick comparison (as per plan).

        Args:
            file_path: Path to check

        Returns:
            True if file was already processed and unchanged
        """
        path_str = str(file_path)
        if path_str not in self.processed:
            return False

        # Check if file metadata changed
        try:
            stat = file_path.stat()
            stored = self.processed[path_str]
            if stored['mtime'] == stat.st_mtime and stored['size'] == stat.st_size:
                return True
            else:
                # File changed, reprocess
                logger.debug(f"File changed since last checkpoint: {file_path}")
                return False
        except OSError:
            # File no longer exists
            return False

    def mark_processed(self, file_path: Path) -> None:
        """
        Mark a file as successfully processed.

        Args:
            file_path: Path to mark
        """
        try:
            stat = file_path.stat()
            self.processed[str(file_path)] = {
                'mtime': stat.st_mtime,
                'size': stat.st_size,
                'processed_at': datetime.now().isoformat()
            }
        except OSError as e:
            logger.warning(f"Cannot mark {file_path} as processed: {e}")

    def clear(self) -> None:
        """Clear checkpoint file."""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                logger.info("Cleared checkpoint file")
            self.processed = {}
        except Exception as e:
            logger.error(f"Failed to clear checkpoint: {e}")


def filter_unprocessed_files(
    candidates: List[Path],
    checkpoint: IndexingCheckpoint
) -> List[Path]:
    """
    Filter out files that have already been processed.

    Args:
        candidates: List of candidate files
        checkpoint: Checkpoint manager

    Returns:
        List of unprocessed files
    """
    unprocessed = []
    for file_path in candidates:
        if not checkpoint.is_processed(file_path):
            unprocessed.append(file_path)
        else:
            logger.debug(f"Skipping already processed file: {file_path}")

    return unprocessed


def _parse_log_file(file_path: Path) -> Optional[Dict[str, any]]:
    """
    Parse a session log file into a conversation dict.

    Args:
        file_path: Path to log file

    Returns:
        Conversation dict or None if parsing fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        if not content.strip():
            logger.debug(f"Skipping empty log file: {file_path}")
            return None

        # Extract session ID from filename (e.g., "session-abc123.log" -> "session-abc123")
        session_id = file_path.stem

        # Get file modification time as timestamp
        mtime = file_path.stat().st_mtime
        timestamp = datetime.fromtimestamp(mtime).isoformat()

        # Create conversation dict
        conversation = {
            'user': f"Session Log: {session_id}",
            'assistant': content,
            'timestamp': timestamp,
            'source': 'session_log',
            'metadata': {
                'session_id': session_id,
                'log_file': str(file_path),
                'file_size': file_path.stat().st_size
            }
        }

        return conversation

    except Exception as e:
        logger.error(f"Failed to parse log file {file_path}: {e}")
        return None


def _index_files_batch(
    files: List[Path],
    ingestion_service,
    checkpoint: IndexingCheckpoint,
    batch_size: int = 10,
    progress_interval: float = 5.0
) -> Tuple[int, int]:
    """
    Index log files in batches with progress tracking.

    Args:
        files: List of log files to index
        ingestion_service: IngestionService instance
        checkpoint: Checkpoint manager
        batch_size: Number of files to process per batch
        progress_interval: Progress log interval in seconds

    Returns:
        Tuple of (success_count, failure_count)
    """
    total = len(files)
    success_count = 0
    failure_count = 0
    last_progress_time = time.time()
    processed_bytes = 0

    logger.info(f"Starting indexing of {total} files...")
    print(f"\nIndexing {total} session log files...")

    for i, file_path in enumerate(files, 1):
        try:
            # Parse log file
            conversation = _parse_log_file(file_path)
            if conversation is None:
                failure_count += 1
                continue

            # Ingest conversation
            memory_id = ingestion_service.ingest_conversation(conversation)
            logger.debug(f"Indexed {file_path.name} -> {memory_id}")

            # Mark as processed
            checkpoint.mark_processed(file_path)
            success_count += 1
            processed_bytes += file_path.stat().st_size

            # Save checkpoint periodically (every 10 files)
            if success_count % 10 == 0:
                checkpoint.save()

            # Show progress every ~5 seconds
            current_time = time.time()
            if current_time - last_progress_time >= progress_interval:
                percent = (i / total) * 100
                print(f"Progress: {i}/{total} files ({percent:.1f}%) - {_format_size(processed_bytes)} processed")
                logger.info(f"Indexing progress: {i}/{total} files ({success_count} successful, {failure_count} failed)")
                last_progress_time = current_time

        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}", exc_info=True)
            failure_count += 1
            # Continue processing other files

    # Final checkpoint save
    checkpoint.save()

    # Final progress report
    percent = 100.0
    print(f"Progress: {total}/{total} files ({percent:.1f}%) - {_format_size(processed_bytes)} processed")
    logger.info(f"Indexing complete: {success_count} successful, {failure_count} failed")

    return success_count, failure_count


def run_first_run_indexing(
    data_dir: str,
    session_log_dir: str,
    ingestion_service,
    auto_approve: bool = False,
    max_file_size_mb: int = 100,
    allowed_extensions: List[str] = None
) -> bool:
    """
    Run first-run indexing of existing session logs.

    Args:
        data_dir: Data directory path
        session_log_dir: Session log directory path
        ingestion_service: IngestionService instance
        auto_approve: If True, skip user prompt and run automatically
        max_file_size_mb: Maximum file size in MB
        allowed_extensions: List of allowed file extensions

    Returns:
        True if indexing completed successfully, False otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = ['.jsonl', '.log', '.txt']

    # Task 2: Dry run and prompt
    logger.info("Scanning session log directory for first-run indexing...")
    candidates, total_bytes = scan_log_directory(session_log_dir, max_file_size_mb, allowed_extensions)

    if len(candidates) == 0:
        logger.info("No session logs found to index")
        mark_first_run_complete(data_dir)
        return True

    # Task 3: Load checkpoint and filter out already processed files
    checkpoint = IndexingCheckpoint(data_dir)
    unprocessed = filter_unprocessed_files(candidates, checkpoint)

    if len(unprocessed) == 0:
        logger.info("All session logs already processed")
        mark_first_run_complete(data_dir)
        checkpoint.clear()
        return True

    # Recalculate total bytes for unprocessed files
    unprocessed_bytes = sum(f.stat().st_size for f in unprocessed)

    # Show dry run info and prompt user (unless auto-approve)
    if auto_approve:
        logger.info(f"Auto-approving first-run indexing: {len(unprocessed)} files, {_format_size(unprocessed_bytes)}")
        user_approved = True
    else:
        user_approved = prompt_user_for_indexing(len(unprocessed), unprocessed_bytes)

    if not user_approved:
        logger.info("First-run indexing declined by user")
        mark_first_run_complete(data_dir)
        checkpoint.clear()
        return False

    # Task 4: Index files with batch processing and progress tracking
    logger.info("Starting first-run indexing...")
    try:
        success_count, failure_count = _index_files_batch(
            files=unprocessed,
            ingestion_service=ingestion_service,
            checkpoint=checkpoint
        )

        # Check if indexing was successful
        if failure_count > 0:
            logger.warning(f"First-run indexing completed with {failure_count} failures")
            print(f"\nIndexing completed: {success_count} successful, {failure_count} failed")

        if success_count == len(unprocessed):
            # All files processed successfully
            logger.info("First-run indexing completed successfully")
            print("\nFirst-run indexing completed successfully!")
            mark_first_run_complete(data_dir)
            checkpoint.clear()
            return True
        elif success_count > 0:
            # Partial success - keep checkpoint for resume
            logger.info(f"Partial first-run indexing: {success_count}/{len(unprocessed)} files processed")
            print(f"\nPartial indexing: {success_count}/{len(unprocessed)} files processed")
            print("Checkpoint saved. Run again to resume.")
            # Don't mark as complete, keep checkpoint
            return False
        else:
            # Total failure
            logger.error("First-run indexing failed completely")
            print("\nIndexing failed. No files were processed.")
            checkpoint.clear()
            return False

    except Exception as e:
        logger.error(f"First-run indexing failed: {e}", exc_info=True)
        print(f"\nIndexing failed: {e}")
        # Keep checkpoint for resume
        return False
