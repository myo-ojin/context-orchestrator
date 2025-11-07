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
    'Project',
    'SearchBookmark',
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
    project_id: Optional[str] = None  # Phase 15: Project association

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
            'is_representative': self.is_representative,
            'project_id': self.project_id
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
            is_representative=data.get('is_representative', False),
            project_id=data.get('project_id')  # Phase 15: backward compatible
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


@dataclass
class Project:
    """
    Project data model (Phase 15: Project Management)

    Represents a project for organizing memories by topic/codebase.
    Inspired by NotebookLM's library management approach.

    Attributes:
        id: Unique identifier (UUID)
        name: Project name
        description: Project description
        tags: Tags for categorization (e.g., ["react", "typescript"])
        created_at: Creation timestamp
        updated_at: Last update timestamp
        memory_count: Number of memories associated with this project
        last_accessed: Last time project was accessed/searched
        metadata: Additional metadata (flexible dict)
    """
    id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    memory_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'memory_count': self.memory_count,
            'last_accessed': self.last_accessed.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create Project from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            tags=data.get('tags', []),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            memory_count=data.get('memory_count', 0),
            last_accessed=datetime.fromisoformat(data.get('last_accessed', data['updated_at'])),
            metadata=data.get('metadata', {})
        )


@dataclass
class SearchBookmark:
    """
    Search bookmark data model (Phase 15: Search Enhancement)

    Represents a saved search query for quick access to frequently used searches.
    Similar to NotebookLM's smart query approach.

    Attributes:
        id: Unique identifier (UUID)
        name: Bookmark name (e.g., "React Errors")
        query: Search query string
        filters: Search filters (e.g., {"schema_type": "Incident"})
        created_at: Creation timestamp
        usage_count: Number of times this bookmark has been used
        last_used: Last time bookmark was executed
        description: Optional description
    """
    id: str
    name: str
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    last_used: datetime = field(default_factory=datetime.now)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'query': self.query,
            'filters': self.filters,
            'created_at': self.created_at.isoformat(),
            'usage_count': self.usage_count,
            'last_used': self.last_used.isoformat(),
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchBookmark':
        """Create SearchBookmark from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            query=data['query'],
            filters=data.get('filters', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            usage_count=data.get('usage_count', 0),
            last_used=datetime.fromisoformat(data.get('last_used', data['created_at'])),
            description=data.get('description', "")
        )


# Config class moved to src.config module for better organization
