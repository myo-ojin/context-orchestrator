#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Indexer

Indexes chunks in both vector database (Chroma) and BM25 index.
Coordinates embedding generation and dual indexing.

Requirements: Requirement 3 (MVP - Chunking and Indexing)
"""

from typing import List, Dict, Any
import logging

from src.models import Chunk, ModelRouter
from src.storage.vector_db import ChromaVectorDB
from src.storage.bm25_index import BM25Index

logger = logging.getLogger(__name__)


class Indexer:
    """
    Indexer for vector DB and BM25 index

    Handles dual indexing:
    1. Generate embeddings using local LLM
    2. Index in Chroma vector DB (semantic search)
    3. Index in BM25 (keyword search)

    Attributes:
        vector_db: ChromaVectorDB instance
        bm25_index: BM25Index instance
        model_router: ModelRouter for embedding generation
    """

    def __init__(
        self,
        vector_db: ChromaVectorDB,
        bm25_index: BM25Index,
        model_router: ModelRouter
    ):
        """
        Initialize Indexer

        Args:
            vector_db: ChromaVectorDB instance
            bm25_index: BM25Index instance
            model_router: ModelRouter instance
        """
        self.vector_db = vector_db
        self.bm25_index = bm25_index
        self.model_router = model_router

        logger.info("Initialized Indexer")

    def index(self, chunks: List[Chunk]) -> None:
        """
        Index chunks in both vector DB and BM25 index

        Args:
            chunks: List of Chunk objects

        Example:
            >>> indexer = Indexer(vector_db, bm25_index, router)
            >>> indexer.index(chunks)
        """
        if not chunks:
            logger.warning("No chunks to index")
            return

        logger.info(f"Indexing {len(chunks)} chunks...")

        # Index in both databases
        self._index_vector_db(chunks)
        self._index_bm25(chunks)

        logger.info(f"Successfully indexed {len(chunks)} chunks")

    def index_single(self, chunk: Chunk) -> None:
        """
        Index a single chunk

        Args:
            chunk: Chunk object

        Example:
            >>> indexer = Indexer(vector_db, bm25_index, router)
            >>> indexer.index_single(chunk)
        """
        self.index([chunk])

    def _index_vector_db(self, chunks: List[Chunk]) -> None:
        """
        Index chunks in Chroma vector DB

        Generates embeddings and stores in vector database.
        Adds salience weight metadata (Phase 3 optimization).

        Args:
            chunks: List of Chunk objects
        """
        logger.debug(f"Indexing {len(chunks)} chunks in vector DB...")

        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding using local model (always local for privacy)
                embedding = self.model_router.generate_embedding(chunk.content)

                # Store embedding in chunk
                chunk.embedding = embedding

                metadata = dict(chunk.metadata or {})
                metadata.setdefault('memory_id', chunk.memory_id)
                metadata.setdefault('chunk_index', metadata.get('chunk_index', i))

                # Phase 3: Add salience weight (token length normalization)
                salience_weight = self._calculate_salience_weight(chunk)
                metadata['salience_weight'] = salience_weight

                # Add to vector DB
                self.vector_db.add(
                    id=chunk.id,
                    embedding=embedding,
                    metadata=metadata,
                    document=chunk.content
                )

                if (i + 1) % 10 == 0:
                    logger.debug(f"Indexed {i + 1}/{len(chunks)} chunks in vector DB")

            except Exception as e:
                logger.error(f"Failed to index chunk {chunk.id} in vector DB: {e}")
                # Continue with other chunks

        logger.debug(f"Completed vector DB indexing for {len(chunks)} chunks")

    def _index_bm25(self, chunks: List[Chunk]) -> None:
        """
        Index chunks in BM25 index

        Args:
            chunks: List of Chunk objects
        """
        logger.debug(f"Indexing {len(chunks)} chunks in BM25 index...")

        # Batch indexing for BM25
        documents = {}
        for chunk in chunks:
            documents[chunk.id] = chunk.content

        try:
            self.bm25_index.add_documents(documents)
            logger.debug(f"Completed BM25 indexing for {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Failed to index chunks in BM25: {e}")

    def delete(self, chunk_ids: List[str]) -> None:
        """
        Delete chunks from both indexes

        Args:
            chunk_ids: List of chunk IDs to delete

        Example:
            >>> indexer = Indexer(vector_db, bm25_index, router)
            >>> indexer.delete(["chunk-1", "chunk-2"])
        """
        if not chunk_ids:
            logger.warning("No chunk IDs to delete")
            return

        logger.info(f"Deleting {len(chunk_ids)} chunks from indexes...")

        # Delete from vector DB
        for chunk_id in chunk_ids:
            try:
                self.vector_db.delete(chunk_id)
            except Exception as e:
                logger.error(f"Failed to delete {chunk_id} from vector DB: {e}")

        # Delete from BM25
        for chunk_id in chunk_ids:
            try:
                self.bm25_index.delete(chunk_id)
            except Exception as e:
                logger.error(f"Failed to delete {chunk_id} from BM25: {e}")

        logger.info(f"Successfully deleted {len(chunk_ids)} chunks")

    def delete_by_memory_id(self, memory_id: str) -> None:
        """
        Delete all chunks belonging to a memory

        Args:
            memory_id: Parent memory ID

        Example:
            >>> indexer = Indexer(vector_db, bm25_index, router)
            >>> indexer.delete_by_memory_id("mem-123")
        """
        logger.info(f"Deleting all chunks for memory {memory_id}...")

        try:
            entries = self.vector_db.list_by_metadata({'memory_id': memory_id})

            chunk_ids: List[str] = []
            for entry in entries:
                entry_id = entry.get('id')
                metadata = entry.get('metadata', {})

                # Skip memory metadata entries
                if metadata.get('is_memory_entry') or str(entry_id).endswith('-metadata'):
                    continue

                if entry_id:
                    chunk_ids.append(entry_id)

            if not chunk_ids:
                logger.debug(f"No chunks found for memory {memory_id}")
                return

            self.delete(chunk_ids)

        except Exception as e:
            logger.error(f"Failed to delete chunks for memory {memory_id}: {e}")

    def update_metadata(self, chunk_id: str, metadata: Dict[str, Any]) -> None:
        """
        Update metadata for a chunk

        Args:
            chunk_id: Chunk ID
            metadata: New metadata dict

        Example:
            >>> indexer = Indexer(vector_db, bm25_index, router)
            >>> indexer.update_metadata("chunk-1", {"importance": 0.9})
        """
        try:
            self.vector_db.update_metadata(chunk_id, metadata)
            logger.debug(f"Updated metadata for chunk {chunk_id}")
        except Exception as e:
            logger.error(f"Failed to update metadata for {chunk_id}: {e}")

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about indexed content

        Returns:
            Dict with index statistics

        Example:
            >>> indexer = Indexer(vector_db, bm25_index, router)
            >>> stats = indexer.get_index_stats()
            >>> print(stats)
            {'vector_db_count': 150, 'bm25_count': 150}
        """
        stats = {
            'vector_db_count': self.vector_db.count(),
            'bm25_count': self.bm25_index.count()
        }

        logger.debug(f"Index statistics: {stats}")
        return stats

    def reindex(self, chunks: List[Chunk]) -> None:
        """
        Reindex chunks (delete old, add new)

        Useful for updating existing chunks with new embeddings.

        Args:
            chunks: List of Chunk objects

        Example:
            >>> indexer = Indexer(vector_db, bm25_index, router)
            >>> indexer.reindex(chunks)
        """
        # Delete existing chunks
        chunk_ids = [chunk.id for chunk in chunks]
        self.delete(chunk_ids)

        # Index new versions
        self.index(chunks)

        logger.info(f"Reindexed {len(chunks)} chunks")

    def _calculate_salience_weight(self, chunk: Chunk) -> float:
        """
        Calculate salience weight for a chunk (Phase 3 optimization)

        Salience weight favors concise but informative chunks using token length normalization.

        Formula:
        - Optimal range: 256-384 tokens (Phase 3 chunk size)
        - Penalty for tiny chunks (<256 tokens): linear decay
        - Penalty for oversized chunks (>384 tokens): logarithmic decay
        - Weight range: 0.5-1.0

        Args:
            chunk: Chunk object

        Returns:
            Salience weight (0.5-1.0)

        Example:
            >>> chunk = Chunk(id="c1", content="...", tokens=320, ...)
            >>> weight = indexer._calculate_salience_weight(chunk)
            >>> 0.9 <= weight <= 1.0
            True
        """
        tokens = chunk.tokens if chunk.tokens else len(chunk.content.split())

        # Optimal range (Phase 3): 256-384 tokens
        min_tokens = 256
        max_tokens = 384
        optimal_mid = (min_tokens + max_tokens) / 2  # 320 tokens

        if min_tokens <= tokens <= max_tokens:
            # Perfect range: weight 0.95-1.0
            # Slightly favor chunks closer to optimal_mid
            distance_from_optimal = abs(tokens - optimal_mid) / (max_tokens - min_tokens)
            weight = 1.0 - (distance_from_optimal * 0.05)
            return max(0.95, min(1.0, weight))

        elif tokens < min_tokens:
            # Tiny chunks: linear penalty
            # 128 tokens → 0.75, 64 tokens → 0.5
            ratio = tokens / min_tokens
            weight = 0.5 + (ratio * 0.45)
            return max(0.5, min(0.95, weight))

        else:  # tokens > max_tokens
            # Oversized chunks: logarithmic penalty
            # 512 tokens → 0.85, 768 tokens → 0.70, 1024 tokens → 0.60
            import math
            excess_ratio = (tokens - max_tokens) / max_tokens
            penalty = math.log1p(excess_ratio) * 0.15
            weight = 0.95 - penalty
            return max(0.5, min(0.95, weight))
