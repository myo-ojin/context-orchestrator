"""
Domain data models and LLM clients for Context Orchestrator

Defines core data structures:
- Memory: Base memory data model
- Chunk: Chunked text with embeddings
- Config: System configuration

LLM clients:
- LocalLLMClient: Ollama-based local LLM
- CLILLMClient: Cloud LLM via CLI (claude/codex)
- ModelRouter: Task-based routing between local and cloud

Requirements: Requirements 2, 3, 10 (MVP - Schema, Chunking, Model Routing)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

# Import LLM clients
from .local_llm import LocalLLMClient, OllamaConnectionError, ModelNotFoundError
from .cli_llm import CLILLMClient, CLICallError
from .router import ModelRouter

# Export all public classes
__all__ = [
    # Data models
    'Memory',
    'Chunk',
    'MemoryType',
    'SchemaType',
    # LLM clients
    'LocalLLMClient',
    'CLILLMClient',
    'ModelRouter',
    # Exceptions
    'OllamaConnectionError',
    'ModelNotFoundError',
    'CLICallError',
]

# Note: Config class is now in src.config module, not here


class MemoryType(Enum):
    """Memory hierarchy types"""
    WORKING = "working"          # Current task context (数時間)
    SHORT_TERM = "short_term"    # Recent experiences (数日〜数週間)
    LONG_TERM = "long_term"      # Important knowledge (永続的)


class SchemaType(Enum):
    """Memory schema types (Requirement 2)"""
    INCIDENT = "Incident"    # Bug reports, errors, troubleshooting
    SNIPPET = "Snippet"      # Code examples with usage context
    DECISION = "Decision"    # Architectural choices, trade-offs
    PROCESS = "Process"      # Thought processes, learning


@dataclass
class Memory:
    """
    Base memory data model

    Represents a structured memory with schema classification,
    content, and metadata for search and consolidation.

    Attributes:
        id: Unique identifier (UUID)
        schema_type: Memory schema (Incident/Snippet/Decision/Process)
        content: Original content (Markdown format)
        summary: 100-token summary for quick reference
        refs: Source references (URLs, file paths, commit IDs)
        created_at: Creation timestamp (ISO 8601)
        updated_at: Last update timestamp (ISO 8601)
        strength: Memory strength (0.0-1.0, decays over time)
        importance: Importance score (0.0-1.0, for retention decisions)
        tags: Tags for categorization
        metadata: Additional metadata (flexible dict)
        memory_type: Hierarchy level (working/short_term/long_term)
        cluster_id: Cluster ID if part of a cluster
        is_representative: True if representative memory in cluster
    """
    id: str
    schema_type: SchemaType
    content: str
    summary: str
    refs: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    strength: float = 1.0
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    memory_type: MemoryType = MemoryType.WORKING
    cluster_id: Optional[str] = None
    is_representative: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'schema_type': self.schema_type.value,
            'content': self.content,
            'summary': self.summary,
            'refs': self.refs,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'strength': self.strength,
            'importance': self.importance,
            'tags': self.tags,
            'metadata': self.metadata,
            'memory_type': self.memory_type.value,
            'cluster_id': self.cluster_id,
            'is_representative': self.is_representative
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """Create Memory from dictionary"""
        return cls(
            id=data['id'],
            schema_type=SchemaType(data['schema_type']),
            content=data['content'],
            summary=data['summary'],
            refs=data.get('refs', []),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            strength=data.get('strength', 1.0),
            importance=data.get('importance', 0.5),
            tags=data.get('tags', []),
            metadata=data.get('metadata', {}),
            memory_type=MemoryType(data.get('memory_type', 'working')),
            cluster_id=data.get('cluster_id'),
            is_representative=data.get('is_representative', False)
        )


@dataclass
class Chunk:
    """
    Chunk data model (Requirement 3)

    Represents a chunked piece of text with embeddings for indexing.
    Chunks are created by splitting large content into 512-token pieces.

    Attributes:
        id: Unique chunk ID (UUID)
        memory_id: Parent memory ID
        content: Chunk content (Markdown format)
        tokens: Token count (via tiktoken)
        embedding: Embedding vector (from nomic-embed-text)
        metadata: Metadata inherited from parent memory
    """
    id: str
    memory_id: str
    content: str
    tokens: int
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'memory_id': self.memory_id,
            'content': self.content,
            'tokens': self.tokens,
            'embedding': self.embedding,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chunk':
        """Create Chunk from dictionary"""
        return cls(
            id=data['id'],
            memory_id=data['memory_id'],
            content=data['content'],
            tokens=data['tokens'],
            embedding=data.get('embedding'),
            metadata=data.get('metadata', {})
        )


# Config class moved to src.config module for better organization
