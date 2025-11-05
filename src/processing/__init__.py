"""
Processing components for classification, chunking, and indexing

Components:
- SchemaClassifier: Classify content into schema types (Incident/Snippet/Decision/Process)
- Chunker: Split text into 512-token chunks with Markdown structure preservation
- Indexer: Index chunks in vector DB (Chroma) and BM25 index

Requirements: Requirements 2, 3 (MVP - Schema Classification, Chunking, Indexing)
"""

from .classifier import SchemaClassifier
from .chunker import Chunker
from .indexer import Indexer

__all__ = [
    'SchemaClassifier',
    'Chunker',
    'Indexer',
]
