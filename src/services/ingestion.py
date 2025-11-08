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

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import uuid

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
        model_router: ModelRouter
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

        # Build summarization prompt
        content = f"User: {user_message}\n\nAssistant: {assistant_message}"
        prompt = f"""Summarize the following conversation in 1-2 sentences (max 100 tokens).
Focus on the key points and outcome.

Conversation:
---
{content[:1000]}
---

Summary:"""

        try:
            # Use local LLM for short summary (Req-10)
            summary = self.model_router.route(
                task_type='short_summary',
                prompt=prompt,
                max_tokens=100
            )
            return summary.strip()

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            # Fallback: use first 100 chars of user message
            return user_message[:100] + "..."

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

    def _store_memory_metadata(self, memory: Memory) -> None:
        """
        Store memory metadata in vector DB

        This creates a separate entry for the memory itself (not just chunks).
        Useful for memory-level operations like consolidation.

        Args:
            memory: Memory object
        """
        try:
            # Generate embedding for summary (lighter than full content)
            embedding = self.model_router.generate_embedding(memory.summary)

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

            self.vector_db.add(
                id=f"{memory.id}-metadata",
                embedding=embedding,
                metadata=metadata,
                document=memory.summary
            )

            logger.debug(f"Stored memory metadata: {memory.id}")

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
