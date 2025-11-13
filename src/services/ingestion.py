#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ingestion Service

Handles conversation ingestion pipeline:
1. Receive conversation (User + Assistant + metadata)
2. Classify schema via SchemaClassifier
3. Generate summary via ModelRouter
4. Chunk content via Chunker
5. Index chunks via Indexer
6. Store Memory object

Requirements: Requirements 1, 2, 3 (MVP - Recording, Classification, Chunking)
"""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict
import logging
import os
import re
import time
import uuid

try:
    from langdetect import detect as _langdetect_detect
    from langdetect import DetectorFactory, LangDetectException

    DetectorFactory.seed = 0
except Exception:  # pragma: no cover - optional dependency fallback
    _langdetect_detect = None

    class LangDetectException(Exception):
        """Fallback exception when langdetect is unavailable."""

from src.models import (
    Memory,
    SchemaType,
    MemoryType,
    ModelRouter,
)
from src.processing.classifier import SchemaClassifier
from src.processing.chunker import Chunker
from src.processing.indexer import Indexer
from src.storage.vector_db import ChromaVectorDB

logger = logging.getLogger(__name__)


@dataclass
class LanguageRoutingMetrics:
    """Aggregate stats for language-based routing decisions."""

    total_requests: int = 0
    local_requests: int = 0
    cloud_requests: int = 0
    cloud_failures: int = 0
    cloud_latency_ms_total: float = 0.0
    cloud_latency_ms_max: float = 0.0
    last_cloud_latency_ms: float = 0.0

    def record(self, target: str, duration_ms: float, success: bool) -> None:
        self.total_requests += 1
        if target == 'cloud':
            self.cloud_requests += 1
            self.cloud_latency_ms_total += duration_ms
            self.last_cloud_latency_ms = duration_ms
            if duration_ms > self.cloud_latency_ms_max:
                self.cloud_latency_ms_max = duration_ms
            if not success:
                self.cloud_failures += 1
        else:
            self.local_requests += 1

    def snapshot(self) -> Dict[str, Any]:
        avg_cloud_latency = (
            self.cloud_latency_ms_total / self.cloud_requests
            if self.cloud_requests
            else 0.0
        )
        base = asdict(self)
        base["avg_cloud_latency_ms"] = avg_cloud_latency
        return base


class IngestionService:
    """
    Service for ingesting and processing conversations

    Orchestrates the full ingestion pipeline from raw conversation
    to indexed, searchable memory.

    Attributes:
        vector_db: ChromaVectorDB instance for memory storage
        classifier: SchemaClassifier instance
        chunker: Chunker instance
        indexer: Indexer instance
        model_router: ModelRouter for LLM tasks
    """

    def __init__(
        self,
        vector_db: ChromaVectorDB,
        classifier: SchemaClassifier,
        chunker: Chunker,
        indexer: Indexer,
        model_router: ModelRouter,
        supported_languages: Optional[List[str]] = None,
        language_fallback_strategy: str = "cloud"
    ):
        """
        Initialize Ingestion Service

        Args:
            vector_db: ChromaVectorDB instance
            classifier: SchemaClassifier instance
            chunker: Chunker instance
            indexer: Indexer instance
            model_router: ModelRouter instance
        """
        self.vector_db = vector_db
        self.classifier = classifier
        self.chunker = chunker
        self.indexer = indexer
        self.model_router = model_router
        self.supported_languages: Set[str] = {
            (lang or "").lower()
            for lang in (supported_languages or ["en", "ja", "es"])
            if lang
        }
        self.language_fallback_strategy = (
            language_fallback_strategy.lower()
            if language_fallback_strategy
            else "cloud"
        )
        self._routing_metrics = LanguageRoutingMetrics()

        logger.info("Initialized IngestionService")

    def ingest_conversation(self, conversation: Dict[str, Any]) -> str:
        """
        Ingest a conversation and process it into memories

        Args:
            conversation: Conversation dict with:
                - user: str (user message)
                - assistant: str (assistant response)
                - timestamp: str (ISO 8601 format, optional)
                - source: str ('cli', 'obsidian', 'kiro', optional)
                - refs: list[str] (source URLs, file paths, optional)
                - metadata: dict (additional metadata, optional)
                - project_id: str (project ID for association, optional) - Phase 15

        Returns:
            memory_id: str (unique identifier for the memory)

        Example:
            >>> service = IngestionService(...)
            >>> memory_id = service.ingest_conversation({
            ...     'user': 'How to fix TypeError?',
            ...     'assistant': 'Check null values...',
            ...     'source': 'cli',
            ...     'project_id': 'proj-abc123'  # Phase 15: optional
            ... })
            >>> print(memory_id)
            'mem-abc123...'
        """
        try:
            logger.info(f"Ingesting conversation from {conversation.get('source', 'unknown')}")

            # Step 1: Classify schema
            schema_type = self._classify_schema(conversation)
            logger.debug(f"Classified as {schema_type.value}")

            # Step 2: Generate summary (short task, use local LLM)
            summary = self._generate_summary(conversation)
            logger.debug(f"Generated summary: {summary[:100]}...")

            # Step 3: Create Memory object
            memory = self._create_memory(conversation, schema_type, summary)
            logger.debug(f"Created memory: {memory.id}")

            # Step 4: Chunk content
            chunks = self._chunk_content(conversation, memory.id, memory.metadata)
            logger.debug(f"Created {len(chunks)} chunks")

            # Step 5: Index chunks
            self._index_chunks(chunks)
            logger.debug(f"Indexed {len(chunks)} chunks")

            # Step 6: Store memory metadata in vector DB
            # (The chunks already contain memory_id reference)
            self._store_memory_metadata(memory)

            logger.info(f"Successfully ingested conversation: {memory.id}")
            return memory.id

        except Exception as e:
            logger.error(f"Failed to ingest conversation: {e}", exc_info=True)
            raise

    def ingest_batch(self, conversations: List[Dict[str, Any]]) -> List[str]:
        """
        Ingest multiple conversations (batch operation)

        Args:
            conversations: List of conversation dicts

        Returns:
            List of memory IDs

        Example:
            >>> service = IngestionService(...)
            >>> memory_ids = service.ingest_batch([conv1, conv2, conv3])
            >>> print(f"Ingested {len(memory_ids)} conversations")
        """
        logger.info(f"Ingesting {len(conversations)} conversations...")

        memory_ids = []
        for i, conversation in enumerate(conversations):
            try:
                memory_id = self.ingest_conversation(conversation)
                memory_ids.append(memory_id)

                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(conversations)} conversations")

            except Exception as e:
                logger.error(f"Failed to ingest conversation {i}: {e}")
                # Continue with other conversations

        logger.info(f"Successfully ingested {len(memory_ids)}/{len(conversations)} conversations")
        return memory_ids

    def _classify_schema(self, conversation: Dict[str, Any]) -> SchemaType:
        """
        Classify conversation into schema type

        Args:
            conversation: Conversation dict

        Returns:
            SchemaType enum value
        """
        user_message = conversation.get('user', '')
        assistant_message = conversation.get('assistant', '')
        metadata = conversation.get('metadata', {})

        try:
            return self.classifier.classify_conversation(
                user_message,
                assistant_message,
                metadata
            )
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Fallback to Process
            return SchemaType.PROCESS

    def _generate_summary(self, conversation: Dict[str, Any]) -> str:
        """
        Generate summary of conversation

        Uses local LLM for short summaries (< 100 tokens).

        Args:
            conversation: Conversation dict

        Returns:
            Summary string (max 100 tokens)
        """
        user_message = conversation.get('user', '')
        assistant_message = conversation.get('assistant', '')
        metadata = conversation.get('metadata', {}) or {}

        hints = self._extract_summary_hints(conversation, metadata)
        language_code = self._detect_language(user_message, assistant_message)
        override_language = (
            conversation.get('language_override')
            or metadata.get('language_override')
            or os.getenv('CONTEXT_ORCHESTRATOR_LANG_OVERRIDE')
        )
        if override_language:
            override_language = override_language.lower()
            if override_language != language_code:
                logger.info(
                    "Language override applied (detected=%s -> override=%s)",
                    language_code,
                    override_language,
                )
            language_code = override_language

        routing_target = self._determine_summary_routing(language_code)

        content = f"User: {user_message}\n\nAssistant: {assistant_message}"
        attempts = 2
        for attempt in range(1, attempts + 1):
            prompt = self._build_structured_prompt(
                content=content,
                hints=hints,
                language_code=language_code,
                enforce_notice=(attempt > 1)
            )
            start_time = time.perf_counter()
            try:
                summary = self.model_router.route(
                    task_type='short_summary',
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.0,
                    force_routing=routing_target
                )
            except Exception as exc:
                logger.error(f"Summary generation failed (attempt {attempt}): {exc}")
                summary = ""
            duration_ms = (time.perf_counter() - start_time) * 1000

            cleaned = summary.strip() if isinstance(summary, str) else ""
            is_valid = bool(cleaned and self._is_structured_summary(cleaned))
            self._routing_metrics.record(routing_target, duration_ms, is_valid)

            if routing_target == 'cloud':
                logger.info(
                    "Language routing fallback (lang=%s) attempt %d finished in %.1f ms (success=%s)",
                    language_code,
                    attempt,
                    duration_ms,
                    is_valid,
                )

            if is_valid:
                return cleaned

            logger.warning(
                "Structured summary validation failed (attempt %d). Retrying...",
                attempt
            )

        logger.error("Structured summary generation failed after retries; using fallback.")
        return self._build_fallback_summary(
            hints=hints,
            language_code=language_code,
            user_message=user_message,
            assistant_message=assistant_message
        )

    @classmethod
    def _detect_language(cls, *texts: str) -> str:
        corpus = " ".join(filter(None, texts)).strip()
        if not corpus:
            return "en"

        detected = None
        if _langdetect_detect:
            try:
                detected = _langdetect_detect(corpus)
            except LangDetectException:
                detected = None

        if detected:
            detected = detected.lower()
            if detected == 'zh-cn' or detected == 'zh-tw':
                detected = 'zh'
            return detected

        if cls._JAPANESE_PATTERN.search(corpus):
            return "ja"
        if cls._SPANISH_PATTERN.search(corpus):
            return "es"
        return "en"

    @classmethod
    def _build_structured_prompt(
        cls,
        content: str,
        hints: Dict[str, str],
        language_code: str,
        enforce_notice: bool = False
    ) -> str:
        language = cls._LANGUAGE_MAP.get(language_code, "English")
        metadata_hint = (
            f"- Topic: {hints['topic']}\n"
            f"- DocType: {hints['doc_type']}\n"
            f"- Project: {hints['project']}"
        )
        notice = "Output EXACTLY the headers and bullet list." if enforce_notice else "Follow the format strictly."
        return (
            f"You are a summarization assistant. Respond in {language}.\n"
            f"Known metadata:\n{metadata_hint}\n\n"
            f"Summarize the conversation in the same language.\n"
            f"{notice}\n\n"
            "Required format:\n"
            "Topic: <value>\n"
            "DocType: <value>\n"
            "Project: <value>\n"
            "KeyActions:\n"
            "- <assistant guidance 1>\n"
            "- <assistant guidance 2>\n"
            "(bullet list can be 1-3 items.)\n\n"
            "Do not add extra commentary before or after the headers.\n\n"
            f"Conversation:\n---\n{content[:1500]}\n---\n\nSummary:"
        )

    @classmethod
    def _is_structured_summary(cls, summary: str) -> bool:
        if not summary:
            return False
        lines = [line.rstrip() for line in summary.splitlines()]
        stripped = [line.strip() for line in lines if line.strip()]
        if len(stripped) < 5:
            return False

        expected = cls._STRUCTURED_HEADERS
        for header, line in zip(expected, stripped[:4]):
            if not line.startswith(header):
                return False

        # Ensure KeyActions line is exactly header (no inline text)
        key_actions_idx = None
        for idx, line in enumerate(lines):
            if line.strip().startswith("KeyActions:"):
                key_actions_idx = idx
                break
        if key_actions_idx is None:
            return False

        bullets = [
            lines[i].lstrip()
            for i in range(key_actions_idx + 1, len(lines))
            if lines[i].strip()
        ]
        if not bullets:
            return False
        if not all(bullet.startswith("- ") for bullet in bullets):
            return False
        return True

    @classmethod
    def is_structured_summary(cls, summary: str) -> bool:
        """Public helper for validating structured summary format."""
        return cls._is_structured_summary(summary)

    def get_language_routing_metrics(self) -> Dict[str, Any]:
        """Expose aggregated language routing metrics for monitoring."""
        return self._routing_metrics.snapshot()

    @staticmethod
    def _extract_summary_hints(
        conversation: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        def _pick(*keys):
            for key in keys:
                value = metadata.get(key) or conversation.get(key)
                if value:
                    return str(value)
            return "UNKNOWN"

        return {
            "topic": _pick('topic'),
            "doc_type": _pick('doc_type', 'type'),
            "project": _pick('project', 'project_name', 'project_id')
        }

    @classmethod
    def _build_fallback_summary(
        cls,
        hints: Dict[str, str],
        language_code: str,
        user_message: str,
        assistant_message: str
    ) -> str:
        user_excerpt = (user_message or "").strip()[:80] or "N/A"
        assistant_excerpt = (assistant_message or "").strip()[:80] or "N/A"
        language = cls._LANGUAGE_MAP.get(language_code, "English")
        return "\n".join([
            f"Topic: {hints['topic']}",
            f"DocType: {hints['doc_type']}",
            f"Project: {hints['project']}",
            "KeyActions:",
            f"- [{language}] User: {user_excerpt}",
            f"- [{language}] Assistant: {assistant_excerpt}"
        ])

    def _determine_summary_routing(self, language_code: Optional[str]) -> str:
        """
        Decide whether to use local or cloud LLM based on detected language.
        """
        if not language_code:
            return 'local'

        normalized = language_code.lower()
        if normalized in self.supported_languages:
            return 'local'

        return 'cloud' if self.language_fallback_strategy == 'cloud' else 'local'

    def _create_memory(
        self,
        conversation: Dict[str, Any],
        schema_type: SchemaType,
        summary: str
    ) -> Memory:
        """
        Create Memory object from conversation

        Args:
            conversation: Conversation dict
            schema_type: Classified schema type
            summary: Generated summary

        Returns:
            Memory object
        """
        # Generate unique ID
        memory_id = f"mem-{uuid.uuid4().hex[:12]}"

        # Extract fields
        user_message = conversation.get('user', '')
        assistant_message = conversation.get('assistant', '')
        refs = conversation.get('refs', [])
        source = conversation.get('source', 'unknown')

        # Parse timestamp
        timestamp_str = conversation.get('timestamp')
        if timestamp_str:
            try:
                created_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except Exception as e:
                logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
                created_at = datetime.now()
        else:
            created_at = datetime.now()

        # Build content (Markdown format)
        content = f"**User:**\n{user_message}\n\n**Assistant:**\n{assistant_message}"

        # Build metadata
        metadata = conversation.get('metadata', {}).copy()
        metadata['source'] = source
        metadata['created_at'] = created_at.isoformat()

        # Extract tags from metadata or conversation
        tags = conversation.get('tags', [])
        if 'tags' in metadata:
            tags.extend(metadata['tags'])

        # Extract project_id (Phase 15)
        project_id = conversation.get('project_id')

        # Create Memory object
        memory = Memory(
            id=memory_id,
            schema_type=schema_type,
            content=content,
            summary=summary,
            refs=refs,
            created_at=created_at,
            updated_at=created_at,
            strength=1.0,  # Initial strength
            importance=0.5,  # Default importance (will be adjusted by usage)
            tags=tags,
            metadata=metadata,
            memory_type=MemoryType.WORKING,  # Start in working memory
            cluster_id=None,
            is_representative=False,
            project_id=project_id  # Phase 15: Project association
        )

        logger.debug(f"Created Memory: {memory.id} ({schema_type.value})")
        return memory

    def _chunk_content(
        self,
        conversation: Dict[str, Any],
        memory_id: str,
        metadata: Dict[str, Any]
    ) -> List:
        """
        Chunk conversation content

        Args:
            conversation: Conversation dict
            memory_id: Parent memory ID
            metadata: Metadata to attach

        Returns:
            List of Chunk objects
        """
        user_message = conversation.get('user', '')
        assistant_message = conversation.get('assistant', '')

        try:
            # Use conversation chunking (treats turn as semantic unit)
            chunks = self.chunker.chunk_conversation(
                user_message,
                assistant_message,
                memory_id,
                metadata
            )
            return chunks

        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            # Fallback: create single chunk
            from src.models import Chunk
            fallback_chunk = Chunk(
                id=f"{memory_id}-chunk-0",
                memory_id=memory_id,
                content=f"**User:**\n{user_message}\n\n**Assistant:**\n{assistant_message}",
                tokens=len(user_message.split()) + len(assistant_message.split()),
                metadata=metadata
            )
            return [fallback_chunk]

    def _index_chunks(self, chunks: List) -> None:
        """
        Index chunks in both vector DB and BM25 index

        Args:
            chunks: List of Chunk objects
        """
        try:
            self.indexer.index(chunks)
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            raise

    def _build_enriched_summary(self, memory: Memory) -> str:
        """
        Build enriched summary from memory (Phase 2: Memory Representation Refresh)

        Combines:
        1. Original summary
        2. Top keywords from content
        3. Representative heading (first heading from content)

        Args:
            memory: Memory object

        Returns:
            Enriched summary string
        """
        from src.utils.keyword_extractor import extract_keywords

        parts = [memory.summary]

        # Extract top keywords from content
        if memory.content:
            keywords = extract_keywords(memory.content, top_n=5, min_length=3)
            if keywords:
                parts.append(f"Keywords: {', '.join(keywords)}")

        # Extract representative heading from content (first markdown heading)
        if memory.content:
            heading_match = re.search(r'^#{1,3}\s+(.+)$', memory.content, re.MULTILINE)
            if heading_match:
                heading = heading_match.group(1).strip()
                parts.append(f"Topic: {heading}")

        enriched = " | ".join(parts)
        logger.debug(f"Enriched summary for {memory.id}: {enriched[:100]}...")
        return enriched

    def _store_memory_metadata(self, memory: Memory) -> None:
        """
        Store memory metadata in vector DB

        This creates a separate entry for the memory itself (not just chunks).
        Useful for memory-level operations like consolidation.

        Args:
            memory: Memory object
        """
        try:
            # Phase 2: Build enriched summary (original + keywords + heading)
            enriched_summary = self._build_enriched_summary(memory)

            # Generate embedding for enriched summary (richer context than raw summary)
            embedding = self.model_router.generate_embedding(enriched_summary)

            # Store in vector DB with special prefix
            metadata = memory.metadata.copy()
            metadata['memory_id'] = memory.id
            metadata['schema_type'] = memory.schema_type.value
            metadata['memory_type'] = memory.memory_type.value
            metadata['strength'] = memory.strength
            metadata['importance'] = memory.importance
            metadata['created_at'] = memory.created_at.isoformat()
            metadata['is_memory_entry'] = True  # Flag to distinguish from chunks
            metadata['project_id'] = memory.project_id  # Phase 15: Project association
            metadata['enriched_summary'] = enriched_summary  # Phase 2: Store enriched version

            # Chroma metadata must be simple scalars; drop None and complex types
            def _is_simple(v):
                return isinstance(v, (str, int, float, bool))

            metadata = {k: v for k, v in metadata.items() if v is not None and _is_simple(v)}

            self.vector_db.add(
                id=f"{memory.id}-metadata",
                embedding=embedding,
                metadata=metadata,
                document=enriched_summary  # Phase 2: Store enriched summary as document
            )

            logger.debug(f"Stored memory metadata with enriched summary: {memory.id}")

        except Exception as e:
            logger.error(f"Failed to store memory metadata: {e}")
            # Non-fatal: chunks are already indexed

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """
        Retrieve a memory by ID

        Args:
            memory_id: Memory ID

        Returns:
            Memory object or None if not found

        Example:
            >>> service = IngestionService(...)
            >>> memory = service.get_memory("mem-abc123")
            >>> print(memory.schema_type)
        """
        try:
            # Retrieve memory metadata entry
            result = self.vector_db.get(f"{memory_id}-metadata")

            if result is None:
                logger.warning(f"Memory not found: {memory_id}")
                return None

            # Reconstruct Memory object
            metadata = result['metadata']
            memory = Memory(
                id=memory_id,
                schema_type=SchemaType(metadata['schema_type']),
                content="",  # Content is in chunks, not stored here
                summary=result['content'],  # Summary is stored as document
                refs=metadata.get('refs', []),
                created_at=datetime.fromisoformat(metadata['created_at']),
                updated_at=datetime.fromisoformat(metadata.get('updated_at', metadata['created_at'])),
                strength=metadata.get('strength', 1.0),
                importance=metadata.get('importance', 0.5),
                tags=metadata.get('tags', []),
                metadata=metadata,
                memory_type=MemoryType(metadata.get('memory_type', 'working')),
                cluster_id=metadata.get('cluster_id'),
                is_representative=metadata.get('is_representative', False),
                project_id=metadata.get('project_id')  # Phase 15: Project association
            )

            return memory

        except Exception as e:
            logger.error(f"Failed to retrieve memory {memory_id}: {e}")
            return None

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory and all its chunks

        Args:
            memory_id: Memory ID

        Returns:
            True if successful, False otherwise

        Example:
            >>> service = IngestionService(...)
            >>> success = service.delete_memory("mem-abc123")
        """
        try:
            logger.info(f"Deleting memory: {memory_id}")

            # Delete memory metadata
            self.vector_db.delete(f"{memory_id}-metadata")

            # Delete all chunks
            self.indexer.delete_by_memory_id(memory_id)

            logger.info(f"Successfully deleted memory: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    def get_ingestion_stats(self) -> Dict[str, Any]:
        """
        Get statistics about ingested content

        Returns:
            Dict with ingestion statistics

        Example:
            >>> service = IngestionService(...)
            >>> stats = service.get_ingestion_stats()
            >>> print(stats)
            {'total_memories': 150, 'total_chunks': 450, ...}
        """
        try:
            index_stats = self.indexer.get_index_stats()

            # Approximate memory count (divide chunk count by average chunks per memory)
            # This is a rough estimate - in production, maintain a separate counter
            estimated_memories = index_stats.get('vector_db_count', 0) // 3

            stats = {
                'total_memories': estimated_memories,
                'total_chunks': index_stats.get('vector_db_count', 0),
                'vector_db_count': index_stats.get('vector_db_count', 0),
                'bm25_count': index_stats.get('bm25_count', 0)
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get ingestion stats: {e}")
            return {}
    _STRUCTURED_HEADERS = ("Topic:", "DocType:", "Project:", "KeyActions:")
    _LANGUAGE_MAP = {
        "ja": "Japanese",
        "es": "Spanish",
        "en": "English",
    }
    _JAPANESE_PATTERN = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
    _SPANISH_PATTERN = re.compile(r"[¿¡ñÑáéíóúÁÉÍÓÚ]")
