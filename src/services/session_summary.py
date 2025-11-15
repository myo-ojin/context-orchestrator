#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Session Summary Worker

Asynchronously summarizes closed session logs using local LLM.
Implements retry logic with exponential backoff (max 3 attempts).

Requirements: Requirement 26 (Phase 2 - Session Logging & Summaries)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging
import json
import time
import math

from src.models import ModelRouter
from src.storage.vector_db import ChromaVectorDB

logger = logging.getLogger(__name__)


class SessionSummaryWorker:
    """
    Worker for session log summarization

    Processes closed session logs asynchronously:
    1. Queue log for summarization
    2. Generate summary via local LLM
    3. Store summary with metadata
    4. Retry failed jobs (max 3 attempts)

    Attributes:
        model_router: ModelRouter for LLM access
        vector_db: VectorDB for storing summaries
        summary_model: Model name for summarization
        job_queue: Queue of pending summarization jobs
        failed_jobs: List of failed jobs with retry info
    """

    def __init__(
        self,
        model_router: ModelRouter,
        vector_db: ChromaVectorDB,
        summary_model: str = "qwen2.5:7b"
    ):
        """
        Initialize Session Summary Worker

        Args:
            model_router: ModelRouter instance
            vector_db: VectorDB instance for storing summaries
            summary_model: Model name for summarization
        """
        self.model_router = model_router
        self.vector_db = vector_db
        self.summary_model = summary_model
        self.job_queue: List[Dict[str, Any]] = []
        self.failed_jobs: List[Dict[str, Any]] = []

        logger.info(f"Initialized SessionSummaryWorker (model={summary_model})")

    def queue_log(
        self,
        session_id: str,
        log_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Queue a session log for summarization

        Args:
            session_id: Session ID
            log_path: Path to log file
            metadata: Optional metadata (start_time, end_time, etc.)

        Returns:
            True if queued successfully

        Example:
            >>> worker.queue_log("session-123", Path("logs/session-123.log"))
        """
        if not log_path.exists():
            logger.error(f"Log file not found: {log_path}")
            return False

        job = {
            'session_id': session_id,
            'log_path': str(log_path),
            'metadata': metadata or {},
            'queued_at': datetime.now().isoformat(),
            'retry_count': 0
        }

        self.job_queue.append(job)
        logger.info(f"Queued session log for summarization: {session_id}")
        return True

    def run_once(self) -> Dict[str, int]:
        """
        Process one batch of queued jobs

        Returns:
            Statistics dict with counts

        Example:
            >>> stats = worker.run_once()
            >>> print(f"Processed: {stats['processed']}, Failed: {stats['failed']}")
        """
        stats = {
            'processed': 0,
            'failed': 0,
            'retried': 0
        }

        # Process queued jobs
        while self.job_queue:
            job = self.job_queue.pop(0)

            try:
                success = self._process_job(job)

                if success:
                    stats['processed'] += 1
                else:
                    # Add to failed jobs for retry
                    self._handle_failed_job(job)
                    stats['failed'] += 1

            except Exception as e:
                logger.error(f"Job processing error for {job['session_id']}: {e}")
                self._handle_failed_job(job)
                stats['failed'] += 1

        # Retry failed jobs
        stats['retried'] = self._retry_failed_jobs()

        return stats

    def _process_job(self, job: Dict[str, Any]) -> bool:
        """
        Process a single summarization job

        Args:
            job: Job data

        Returns:
            True if successful
        """
        session_id = job['session_id']
        log_path = Path(job['log_path'])

        logger.info(f"Processing session summary: {session_id}")

        try:
            # Read log file
            log_content = self._read_log_file(log_path)

            if not log_content:
                logger.warning(f"Empty log file: {log_path}")
                return False

            # Generate summary
            summary = self._summarize_log(log_content)

            # Store summary
            self._store_summary(session_id, summary, job['metadata'])

            logger.info(f"Successfully summarized session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to process job for {session_id}: {e}")
            raise

    def _read_log_file(self, log_path: Path) -> Optional[str]:
        """
        Read log file content

        Args:
            log_path: Path to log file

        Returns:
            Log content or None if failed
        """
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read log file {log_path}: {e}")
            return None

    def _summarize_log(self, log_content: str) -> str:
        """
        Generate summary of log content using local LLM

        Args:
            log_content: Log file content

        Returns:
            Generated summary

        Raises:
            Exception: If summarization fails
        """
        # Truncate if too long (keep first and last parts)
        max_chars = 4000
        if len(log_content) > max_chars:
            half = max_chars // 2
            log_content = (
                log_content[:half] +
                "\n\n[... truncated ...]\n\n" +
                log_content[-half:]
            )

        prompt = f"""Summarize this terminal session log in 2-3 sentences.
Focus on:
- What commands were executed
- What tasks were accomplished
- Any errors or important outcomes

Session log:
{log_content}

Summary:"""

        try:
            # Use local LLM for summarization
            summary = self.model_router.route(
                task_type='short_summary',
                prompt=prompt,
                max_tokens=150
            )

            return summary.strip()

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise

    def _store_summary(
        self,
        session_id: str,
        summary: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Store session summary in vector DB

        Args:
            session_id: Session ID
            summary: Generated summary
            metadata: Job metadata

        Raises:
            Exception: If storage fails
        """
        try:
            # Generate embedding for summary
            embedding = self.model_router.generate_embedding(summary)

            # Build metadata
            summary_metadata = {
                'session_id': session_id,
                'summary_type': 'session',
                'model': self.summary_model,
                'created_at': datetime.now().isoformat(),
                'is_session_summary': True
            }

            # Merge with job metadata
            summary_metadata.update(metadata)

            # Store in vector DB
            self.vector_db.add(
                id=f"{session_id}-summary",
                embedding=embedding,
                metadata=summary_metadata,
                document=summary
            )

            logger.debug(f"Stored summary for session: {session_id}")

        except Exception as e:
            logger.error(f"Failed to store summary for {session_id}: {e}")
            raise

    def _handle_failed_job(self, job: Dict[str, Any]) -> None:
        """
        Handle failed job - add to retry queue

        Args:
            job: Failed job data
        """
        job['retry_count'] = job.get('retry_count', 0) + 1
        job['last_failure'] = datetime.now().isoformat()

        # Max 3 retries
        if job['retry_count'] <= 3:
            self.failed_jobs.append(job)
            logger.warning(f"Job failed, queued for retry ({job['retry_count']}/3): "
                         f"{job['session_id']}")
        else:
            logger.error(f"Job failed after 3 retries, giving up: {job['session_id']}")

    def _retry_failed_jobs(self) -> int:
        """
        Retry failed jobs with exponential backoff

        Returns:
            Number of jobs retried
        """
        if not self.failed_jobs:
            return 0

        retried_count = 0
        still_failed = []

        for job in self.failed_jobs:
            retry_count = job['retry_count']

            # Exponential backoff: 2^retry_count seconds
            backoff_seconds = math.pow(2, retry_count)

            # Check if enough time has passed
            last_failure = datetime.fromisoformat(job['last_failure'])
            elapsed = (datetime.now() - last_failure).total_seconds()

            if elapsed < backoff_seconds:
                # Not ready to retry yet
                still_failed.append(job)
                continue

            # Retry job
            logger.info(f"Retrying job (attempt {retry_count + 1}): {job['session_id']}")

            try:
                success = self._process_job(job)

                if success:
                    retried_count += 1
                else:
                    # Still failed, increment retry count
                    job['retry_count'] += 1
                    job['last_failure'] = datetime.now().isoformat()

                    if job['retry_count'] <= 3:
                        still_failed.append(job)
                    else:
                        logger.error(f"Job exhausted retries: {job['session_id']}")

            except Exception as e:
                logger.error(f"Retry failed for {job['session_id']}: {e}")

                job['retry_count'] += 1
                job['last_failure'] = datetime.now().isoformat()

                if job['retry_count'] <= 3:
                    still_failed.append(job)

        # Update failed jobs list
        self.failed_jobs = still_failed

        if retried_count > 0:
            logger.info(f"Successfully retried {retried_count} jobs")

        return retried_count

    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get queue statistics

        Returns:
            Statistics dict

        Example:
            >>> stats = worker.get_queue_stats()
            >>> print(f"Pending: {stats['pending']}, Failed: {stats['failed']}")
        """
        return {
            'pending': len(self.job_queue),
            'failed': len(self.failed_jobs),
            'total_failed_retries': sum(
                job.get('retry_count', 0) for job in self.failed_jobs
            )
        }

    def clear_queue(self) -> int:
        """
        Clear all pending jobs

        Returns:
            Number of jobs cleared
        """
        count = len(self.job_queue) + len(self.failed_jobs)
        self.job_queue.clear()
        self.failed_jobs.clear()
        logger.info(f"Cleared {count} jobs from queue")
        return count

    def get_session_summary(self, session_id: str) -> Optional[str]:
        """
        Get summary for a session

        Args:
            session_id: Session ID

        Returns:
            Summary text or None if not found
        """
        try:
            result = self.vector_db.get(f"{session_id}-summary")

            if result:
                return result.get('content')

            return None

        except Exception as e:
            logger.error(f"Failed to get summary for {session_id}: {e}")
            return None
