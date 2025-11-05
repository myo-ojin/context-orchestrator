#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Chroma Vector Database Adapter

Provides vector search and metadata management using Chroma DB.
Chroma is SQLite-based, requires no setup, and stores data locally.

Requirements: Requirement 12 (MVP - Storage Layer)
"""

from typing import List, Dict, Optional, Any
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:  # pragma: no cover - fallback for environments without chromadb
    chromadb = None
    Settings = None
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ChromaVectorDB:
    """
    Wrapper for Chroma vector database

    Chroma is a SQLite-based vector database that requires no server setup.
    All data is stored in a local directory specified by persist_directory.

    Attributes:
        client: Chroma persistent client
        collection: Chroma collection for memories
    """

    def __init__(self, persist_directory: str, collection_name: str = "memories"):
        """
        Initialize Chroma vector database

        Args:
            persist_directory: Path to directory for persistent storage
                              (e.g., ~/.context-orchestrator/chroma_db)
            collection_name: Name of the collection to use (default: "memories")
        """
        if chromadb is None or Settings is None:
            raise ImportError(
                "chromadb is required to use ChromaVectorDB. Install it with `pip install chromadb`."
            )

        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize Chroma client with persistent storage
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,  # Disable telemetry for privacy
            )
        )

        # Create or get collection for memories
        # Using cosine distance for similarity search
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Cosine similarity
        )

        logger.info(f"Initialized Chroma DB at {self.persist_directory}")
        logger.info(f"Collection '{collection_name}' has {self.collection.count()} documents")

    def add(
        self,
        id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        document: str
    ) -> None:
        """
        Add a memory to the database

        Args:
            id: Unique identifier (UUID)
            embedding: Embedding vector (e.g., from nomic-embed-text)
            metadata: Metadata dict (tags, timestamp, schema_type, etc.)
            document: Original text content

        Raises:
            ValueError: If embedding dimension is invalid
        """
        try:
            self.collection.add(
                ids=[id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[document]
            )
            logger.debug(f"Added memory {id} to Chroma DB")
        except Exception as e:
            logger.error(f"Failed to add memory {id}: {e}")
            raise

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 50,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories using vector similarity

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return (default: 50)
            filter_metadata: Optional metadata filter (e.g., {"schema_type": "Incident"})

        Returns:
            List of memory dicts with keys:
                - id: Memory ID
                - content: Document text
                - metadata: Metadata dict
                - distance: Cosine distance (lower = more similar)
                - similarity: Cosine similarity (higher = more similar, 0-1)

        Example:
            >>> results = db.search(query_embedding, top_k=10)
            >>> for result in results:
            ...     print(f"{result['id']}: {result['similarity']:.3f}")
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.collection.count()),
                where=filter_metadata  # Optional metadata filter
            )

            # Convert results to standardized format
            memories = []
            if results and results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    memory = {
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i],
                        'similarity': 1 - results['distances'][0][i]  # Convert distance to similarity
                    }
                    memories.append(memory)

            logger.debug(f"Vector search found {len(memories)} results")
            return memories

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific memory by ID

        Args:
            id: Memory ID

        Returns:
            Memory dict with keys:
                - id: Memory ID
                - content: Document text
                - metadata: Metadata dict
            None if not found
        """
        try:
            result = self.collection.get(
                ids=[id],
                include=['metadatas', 'documents', 'embeddings']
            )

            if not result['ids']:
                logger.debug(f"Memory {id} not found")
                return None

            embedding = None
            embeddings = result.get('embeddings')
            if embeddings and embeddings[0]:
                embedding = embeddings[0]

            return {
                'id': result['ids'][0],
                'content': result['documents'][0],
                'metadata': result['metadatas'][0],
                'embedding': embedding
            }

        except Exception as e:
            logger.error(f"Failed to get memory {id}: {e}")
            return None

    def list_by_metadata(
        self,
        filter_metadata: Dict[str, Any],
        include_documents: bool = False,
        include_embeddings: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List entries that match metadata filters.

        Args:
            filter_metadata: Metadata filter dict (passed to Chroma `where`).
            include_documents: Whether to include documents in the response.
            include_embeddings: Whether to include embeddings in the response.

        Returns:
            List of dicts with keys: id, metadata, and optionally content/embedding.
        """
        include = ['ids', 'metadatas']
        if include_documents:
            include.append('documents')
        if include_embeddings:
            include.append('embeddings')

        try:
            results = self.collection.get(
                where=filter_metadata,
                include=include
            )

            items: List[Dict[str, Any]] = []
            ids = results.get('ids') or []
            metadatas = results.get('metadatas') or []
            documents = results.get('documents') or []
            embeddings = results.get('embeddings') or []

            for idx, item_id in enumerate(ids):
                metadata = metadatas[idx] if idx < len(metadatas) else {}
                entry: Dict[str, Any] = {
                    'id': item_id,
                    'metadata': metadata
                }

                if include_documents and idx < len(documents):
                    entry['content'] = documents[idx]

                if include_embeddings and idx < len(embeddings) and embeddings[idx]:
                    entry['embedding'] = embeddings[idx]

                items.append(entry)

            return items

        except Exception as e:
            logger.error(f"Failed to list by metadata {filter_metadata}: {e}")
            return []

    def delete(self, id: str) -> None:
        """
        Delete a memory

        Args:
            id: Memory ID
        """
        try:
            self.collection.delete(ids=[id])
            logger.debug(f"Deleted memory {id}")
        except Exception as e:
            logger.error(f"Failed to delete memory {id}: {e}")
            raise

    def update_metadata(self, id: str, metadata: Dict[str, Any]) -> None:
        """
        Update metadata for a memory

        Args:
            id: Memory ID
            metadata: New metadata dict (replaces existing)
        """
        try:
            self.collection.update(
                ids=[id],
                metadatas=[metadata]
            )
            logger.debug(f"Updated metadata for memory {id}")
        except Exception as e:
            logger.error(f"Failed to update metadata for {id}: {e}")
            raise

    def count(self) -> int:
        """
        Get total number of memories

        Returns:
            Number of memories in database
        """
        return self.collection.count()

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List recent memories (sorted by timestamp in metadata)

        Args:
            limit: Maximum number of results

        Returns:
            List of memory dicts

        Note:
            This fetches all memories and sorts in Python since Chroma
            doesn't have built-in timestamp sorting.
        """
        try:
            # Get all memories (or up to limit * 2 for efficiency)
            results = self.collection.get(
                limit=min(limit * 2, self.collection.count()) if self.collection.count() > 0 else limit
            )

            if not results['ids']:
                return []

            # Convert to list of dicts
            memories = []
            for i in range(len(results['ids'])):
                memory = {
                    'id': results['ids'][i],
                    'content': results['documents'][i],
                    'metadata': results['metadatas'][i]
                }
                memories.append(memory)

            # Sort by timestamp (descending)
            memories.sort(
                key=lambda m: m['metadata'].get('timestamp', ''),
                reverse=True
            )

            return memories[:limit]

        except Exception as e:
            logger.error(f"Failed to list recent memories: {e}")
            return []
