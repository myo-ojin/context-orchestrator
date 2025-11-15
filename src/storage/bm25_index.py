#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BM25 Index Adapter

Provides keyword-based full-text search using BM25 algorithm.
Index is persisted to disk using pickle.

Requirements: Requirement 12 (MVP - Storage Layer)
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import pickle
import logging
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class BM25Index:
    """
    BM25 index for keyword-based search

    BM25 (Best Matching 25) is a ranking function used for keyword search.
    It's more sophisticated than TF-IDF and works well for short queries.

    The index is stored in memory and persisted to disk using pickle.

    Attributes:
        persist_path: Path to pickle file for persistence
        documents: Dict mapping doc_id to original text
        tokenized_docs: List of tokenized documents (for BM25)
        doc_ids: List of document IDs (parallel to tokenized_docs)
        index: BM25Okapi index object
    """

    def __init__(self, persist_path: str):
        """
        Initialize BM25 index

        Args:
            persist_path: Path to pickle file (e.g., ~/.context-orchestrator/bm25_index/index.pkl)
        """
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory storage
        self.documents: Dict[str, str] = {}  # doc_id -> text
        self.tokenized_docs: List[List[str]] = []  # Tokenized documents
        self.doc_ids: List[str] = []  # Document IDs (parallel to tokenized_docs)
        self.index: Optional[BM25Okapi] = None

        # Load existing index if available
        self._load()

        logger.info(f"Initialized BM25 index at {self.persist_path}")
        logger.info(f"Index contains {len(self.documents)} documents")

    def add_document(self, doc_id: str, text: str) -> None:
        """
        Add a document to the index

        Args:
            doc_id: Unique document ID (memory ID)
            text: Document text to index

        Note:
            This triggers a full index rebuild. For batch additions,
            use add_documents() instead.
        """
        if doc_id in self.documents:
            logger.warning(f"Document {doc_id} already exists, replacing")

        self.documents[doc_id] = text
        self._rebuild_index()
        self._save()

        logger.debug(f"Added document {doc_id} to BM25 index")

    def add_documents(self, documents: Dict[str, str]) -> None:
        """
        Add multiple documents to the index (batch operation)

        Args:
            documents: Dict mapping doc_id to text

        Example:
            >>> index.add_documents({
            ...     "mem-001": "Python is a programming language",
            ...     "mem-002": "JavaScript is also a language"
            ... })
        """
        self.documents.update(documents)
        self._rebuild_index()
        self._save()

        logger.info(f"Added {len(documents)} documents to BM25 index")

    def search(
        self,
        query: str,
        top_k: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for documents matching query

        Args:
            query: Search query string
            top_k: Number of results to return (default: 50)

        Returns:
            List of dicts with keys:
                - id: Document ID
                - score: BM25 score (higher = better match)
                - content: Document text

        Example:
            >>> results = index.search("Python programming", top_k=10)
            >>> for result in results:
            ...     print(f"{result['id']}: {result['score']:.3f}")
        """
        if not self.index or not self.documents:
            logger.debug("BM25 index is empty")
            return []

        try:
            # Tokenize query (simple lowercase split)
            tokenized_query = self._tokenize(query)

            # Get BM25 scores for all documents
            scores = self.index.get_scores(tokenized_query)

            # Get top-k results
            # Sort by score (descending) and take top_k
            scored_docs = [
                (i, scores[i]) for i in range(len(scores)) if scores[i] != 0
            ]

            if not scored_docs:
                logger.debug("BM25 search found 0 results (all scores zero)")
                return []

            scored_docs.sort(key=lambda item: item[1], reverse=True)
            top_scored = scored_docs[:top_k]

            # Build results
            results = []
            for i, score in top_scored:
                doc_id = self.doc_ids[i]
                results.append({
                    'id': doc_id,
                    'score': float(score),
                    'content': self.documents[doc_id]
                })

            logger.debug(f"BM25 search found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    def delete(self, doc_id: str) -> None:
        """
        Delete a document from the index

        Args:
            doc_id: Document ID
        """
        if doc_id not in self.documents:
            logger.warning(f"Document {doc_id} not found in index")
            return

        del self.documents[doc_id]
        self._rebuild_index()
        self._save()

        logger.debug(f"Deleted document {doc_id} from BM25 index")

    def get(self, doc_id: str) -> Optional[str]:
        """
        Get document text by ID

        Args:
            doc_id: Document ID

        Returns:
            Document text, or None if not found
        """
        return self.documents.get(doc_id)

    def count(self) -> int:
        """
        Get total number of documents

        Returns:
            Number of documents in index
        """
        return len(self.documents)

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text (simple lowercase split)

        Args:
            text: Input text

        Returns:
            List of tokens

        Note:
            For better performance, consider using a proper tokenizer
            (e.g., nltk, spaCy) in future versions. For MVP, simple
            lowercase split is sufficient.
        """
        return text.lower().split()

    def _rebuild_index(self) -> None:
        """
        Rebuild BM25 index from documents

        This is called after adding or removing documents.
        """
        if not self.documents:
            self.tokenized_docs = []
            self.doc_ids = []
            self.index = None
            return

        # Tokenize all documents
        self.doc_ids = list(self.documents.keys())
        self.tokenized_docs = [
            self._tokenize(self.documents[doc_id])
            for doc_id in self.doc_ids
        ]

        # Build BM25 index
        self.index = BM25Okapi(self.tokenized_docs)

        logger.debug(f"Rebuilt BM25 index with {len(self.documents)} documents")

    def _save(self) -> None:
        """
        Save index to disk (pickle format)

        Saves:
            - documents dict
            - tokenized_docs list
            - doc_ids list
            - index object (BM25Okapi)
        """
        try:
            data = {
                'documents': self.documents,
                'tokenized_docs': self.tokenized_docs,
                'doc_ids': self.doc_ids,
                'index': self.index
            }

            with open(self.persist_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.debug(f"Saved BM25 index to {self.persist_path}")

        except Exception as e:
            logger.error(f"Failed to save BM25 index: {e}")
            # Don't raise - continue operation even if save fails

    def _load(self) -> None:
        """
        Load index from disk

        If file doesn't exist or is corrupted, starts with empty index.
        """
        if not self.persist_path.exists():
            logger.debug("No existing BM25 index found, starting fresh")
            return

        try:
            with open(self.persist_path, 'rb') as f:
                data = pickle.load(f)

            self.documents = data.get('documents', {})
            self.tokenized_docs = data.get('tokenized_docs', [])
            self.doc_ids = data.get('doc_ids', [])
            self.index = data.get('index')

            logger.info(f"Loaded BM25 index with {len(self.documents)} documents")

        except Exception as e:
            logger.error(f"Failed to load BM25 index: {e}")
            logger.warning("Starting with empty index")
            # Reset to empty state
            self.documents = {}
            self.tokenized_docs = []
            self.doc_ids = []
            self.index = None

