#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP Protocol Handler

Handles stdio JSON-RPC communication for MCP (Model Context Protocol).
Routes requests to appropriate services and exposes MCP tools.

Requirements: Requirement 11 (MCP API)
"""

import sys
import json
import logging
from typing import Dict, Any, Optional

from src.services.ingestion import IngestionService
from src.services.search import SearchService
from src.services.consolidation import ConsolidationService
from src.services.session_manager import SessionManager
from src.services.project_manager import ProjectManager  # Phase 15
from src.services.bookmark_manager import BookmarkManager  # Phase 15

logger = logging.getLogger(__name__)

SESSION_PROJECT_CONFIDENCE_THRESHOLD = 0.55


class MCPProtocolHandler:
    """
    MCP Protocol Handler for stdio JSON-RPC communication

    Exposes tools via JSON-RPC:
    - ingest_conversation: Record conversation
    - search_memory: Search memories
    - get_memory: Get specific memory
    - list_recent_memories: List recent memories
    - consolidate_memories: Run consolidation
    - create_project, list_projects, etc.: Project management (Phase 15)
    - create_bookmark, use_bookmark, etc.: Bookmark management (Phase 15)

    Attributes:
        ingestion_service: IngestionService instance
        search_service: SearchService instance
        consolidation_service: ConsolidationService instance
        session_manager: SessionManager instance (optional)
        project_manager: ProjectManager instance (optional) - Phase 15
        bookmark_manager: BookmarkManager instance (optional) - Phase 15
    """

    def __init__(
        self,
        ingestion_service: IngestionService,
        search_service: SearchService,
        consolidation_service: ConsolidationService,
        session_manager: Optional[SessionManager] = None,
        project_manager: Optional[ProjectManager] = None,  # Phase 15
        bookmark_manager: Optional[BookmarkManager] = None  # Phase 15
    ):
        """
        Initialize MCP Protocol Handler

        Args:
            ingestion_service: IngestionService instance
            search_service: SearchService instance
            consolidation_service: ConsolidationService instance
            session_manager: Optional SessionManager instance
            project_manager: Optional ProjectManager instance (Phase 15)
            bookmark_manager: Optional BookmarkManager instance (Phase 15)
        """
        self.ingestion_service = ingestion_service
        self.search_service = search_service
        self.consolidation_service = consolidation_service
        self.session_manager = session_manager
        self.project_manager = project_manager  # Phase 15
        self.bookmark_manager = bookmark_manager  # Phase 15

        logger.info("Initialized MCPProtocolHandler")

    def start(self) -> None:
        """
        Start listening on stdin for JSON-RPC messages

        Reads JSON-RPC messages from stdin line by line and processes them.
        Writes JSON-RPC responses to stdout.

        Example:
            >>> handler = MCPProtocolHandler(...)
            >>> handler.start()  # Blocks and processes stdin
        """
        logger.info("MCP Protocol Handler started, listening on stdin...")

        try:
            for line in sys.stdin:
                line = line.strip()

                if not line:
                    continue

                try:
                    # Parse JSON-RPC request
                    request = json.loads(line)

                    # Handle request
                    response = self.handle_request(request)

                    # Write response to stdout
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = self._create_error_response(
                        None,
                        -32700,
                        "Parse error",
                        str(e)
                    )
                    sys.stdout.write(json.dumps(error_response) + "\n")
                    sys.stdout.flush()

                except Exception as e:
                    logger.error(f"Error handling request: {e}", exc_info=True)
                    error_response = self._create_error_response(
                        None,
                        -32603,
                        "Internal error",
                        str(e)
                    )
                    sys.stdout.write(json.dumps(error_response) + "\n")
                    sys.stdout.flush()

        except KeyboardInterrupt:
            logger.info("MCP Protocol Handler stopped by user")

        except Exception as e:
            logger.error(f"Fatal error in protocol handler: {e}", exc_info=True)
            raise

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming JSON-RPC request

        Args:
            request: JSON-RPC request dict with 'method' and 'params'

        Returns:
            JSON-RPC response dict with 'result' or 'error'

        Example:
            >>> request = {"jsonrpc": "2.0", "id": 1, "method": "search_memory", "params": {"query": "bug fix"}}
            >>> response = handler.handle_request(request)
            >>> print(response)  # {"jsonrpc": "2.0", "id": 1, "result": [...]}
        """
        request_id = request.get('id')
        method = request.get('method')
        params = request.get('params', {})

        # Validate JSON-RPC version
        if request.get('jsonrpc') != '2.0':
            return self._create_error_response(
                request_id,
                -32600,
                "Invalid Request",
                "jsonrpc version must be 2.0"
            )

        # Validate method
        if not method:
            return self._create_error_response(
                request_id,
                -32600,
                "Invalid Request",
                "method is required"
            )

        logger.debug(f"Handling request: method={method}, params={params}")

        try:
            # Route to appropriate service
            result = self._route_to_service(method, params)

            # Create success response
            return self._create_success_response(request_id, result)

        except ValueError as e:
            # Invalid parameters
            return self._create_error_response(
                request_id,
                -32602,
                "Invalid params",
                str(e)
            )

        except NotImplementedError:
            # Method not found
            return self._create_error_response(
                request_id,
                -32601,
                "Method not found",
                f"Unknown method: {method}"
            )

        except Exception as e:
            # Internal error
            logger.error(f"Error routing request: {e}", exc_info=True)
            return self._create_error_response(
                request_id,
                -32603,
                "Internal error",
                str(e)
            )

    def _route_to_service(self, method: str, params: Dict[str, Any]) -> Any:
        """
        Route request to appropriate service based on method name

        Args:
            method: MCP tool name
            params: Tool parameters

        Returns:
            Result from service method

        Raises:
            NotImplementedError: If method is unknown
            ValueError: If parameters are invalid
        """
        # Tool: ingest_conversation
        if method == 'ingest_conversation':
            return self._tool_ingest_conversation(params)

        # Tool: search_memory
        elif method == 'search_memory':
            return self._tool_search_memory(params)

        # Tool: get_memory
        elif method == 'get_memory':
            return self._tool_get_memory(params)

        # Tool: list_recent_memories
        elif method == 'list_recent_memories':
            return self._tool_list_recent_memories(params)

        # Tool: consolidate_memories
        elif method == 'consolidate_memories':
            return self._tool_consolidate_memories(params)

        # Tool: start_session (Phase 6)
        elif method == 'start_session':
            return self._tool_start_session(params)

        # Tool: end_session (Phase 6)
        elif method == 'end_session':
            return self._tool_end_session(params)

        # Tool: add_command (Phase 6)
        elif method == 'add_command':
            return self._tool_add_command(params)

        elif method == 'session_get_hint':
            return self._tool_session_get_hint(params)

        elif method == 'session_set_project':
            return self._tool_session_set_project(params)

        elif method == 'session_clear_project':
            return self._tool_session_clear_project(params)

        # Tool: create_project (Phase 15)
        elif method == 'create_project':
            return self._tool_create_project(params)

        # Tool: list_projects (Phase 15)
        elif method == 'list_projects':
            return self._tool_list_projects(params)

        # Tool: get_project (Phase 15)
        elif method == 'get_project':
            return self._tool_get_project(params)

        # Tool: delete_project (Phase 15)
        elif method == 'delete_project':
            return self._tool_delete_project(params)

        # Tool: search_in_project (Phase 15)
        elif method == 'search_in_project':
            return self._tool_search_in_project(params)

        # Tool: create_bookmark (Phase 15)
        elif method == 'create_bookmark':
            return self._tool_create_bookmark(params)

        # Tool: list_bookmarks (Phase 15)
        elif method == 'list_bookmarks':
            return self._tool_list_bookmarks(params)

        # Tool: use_bookmark (Phase 15)
        elif method == 'use_bookmark':
            return self._tool_use_bookmark(params)

        # Tool: get_reranker_metrics
        elif method == 'get_reranker_metrics':
            return self._tool_get_reranker_metrics(params)

        else:
            raise NotImplementedError(f"Unknown method: {method}")

    # Tool implementations

    def _tool_ingest_conversation(self, params: Dict[str, Any]) -> Dict[str, str]:
        """
        Tool: ingest_conversation

        Records a conversation and processes it into memories.

        Args:
            params: {
                'conversation': {
                    'user': str,
                    'assistant': str,
                    'timestamp': str (ISO 8601),
                    'source': str,
                    'metadata': dict (optional)
                }
            }

        Returns:
            {'memory_id': str}

        Raises:
            ValueError: If conversation is missing or invalid
        """
        conversation = params.get('conversation')

        if not conversation:
            raise ValueError("conversation parameter is required")

        if not isinstance(conversation, dict):
            raise ValueError("conversation must be a dict")

        # Validate required fields
        required_fields = ['user', 'assistant', 'timestamp', 'source']
        for field in required_fields:
            if field not in conversation:
                raise ValueError(f"conversation.{field} is required")

        # Ingest conversation
        memory_id = self.ingestion_service.ingest_conversation(conversation)

        logger.info(f"Ingested conversation: memory_id={memory_id}")

        return {'memory_id': memory_id}

    def _tool_search_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: search_memory

        Searches memories using hybrid search (vector + BM25).

        Args:
            params: {
                'query': str,
                'top_k': int (optional, default: 10),
                'filter_metadata': dict (optional),
                'session_id': str (optional, use session project hint)
            }

        Returns:
            {
                'results': [
                    {
                        'memory_id': str,
                        'content': str,
                        'score': float,
                        'metadata': dict,
                        'refs': list[str]
                    }
                ],
                'count': int
            }

        Raises:
            ValueError: If query is missing
        """
        query = params.get('query')

        if not query:
            raise ValueError("query parameter is required")

        top_k = params.get('top_k', 10)
        filters = dict(params.get('filter_metadata') or {})
        if not filters:
            filters = None

        session_id = params.get('session_id')
        filters = self._apply_session_project_filter(filters, session_id)

        # Search memories
        results = self.search_service.search(
            query=query,
            top_k=top_k,
            filters=filters
        )

        logger.info(f"Searched memories: query='{query}', results={len(results)}")

        return {
            'results': results,
            'count': len(results)
        }

    def _apply_session_project_filter(
        self,
        filters: Optional[Dict[str, Any]],
        session_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        if not session_id or not self.session_manager:
            return filters

        try:
            context = self.session_manager.get_project_context(session_id)
        except Exception as exc:  # pragma: no cover - defensive log
            logger.warning("Failed to resolve project hint for session %s: %s", session_id, exc)
            return filters

        if not context:
            return filters

        confidence = context.get('confidence', 0.0)
        if confidence < SESSION_PROJECT_CONFIDENCE_THRESHOLD:
            return filters

        project_id = context.get('project_id')
        if not project_id:
            return filters

        if filters and filters.get('project_id'):
            return filters

        merged = dict(filters) if filters else {}
        merged['project_id'] = project_id
        logger.info(
            "Session %s project filter applied (project_id=%s, confidence=%.2f)",
            session_id,
            project_id,
            confidence
        )
        return merged

    @staticmethod
    def _format_session_hint_response(
        session_id: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        context = context or {}
        return {
            'session_id': session_id,
            'project_hint': context.get('project_name') or context.get('project_hint'),
            'project_id': context.get('project_id'),
            'confidence': context.get('confidence', 0.0),
            'source': context.get('source'),
            'raw_hint': context.get('project_hint'),
        }

    def _tool_get_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: get_memory

        Gets a specific memory by ID.

        Args:
            params: {
                'memory_id': str
            }

        Returns:
            {
                'memory_id': str,
                'content': str,
                'metadata': dict,
                'chunks': list[dict] (optional)
            }

        Raises:
            ValueError: If memory_id is missing or memory not found
        """
        memory_id = params.get('memory_id')

        if not memory_id:
            raise ValueError("memory_id parameter is required")

        # Get memory
        memory = self.search_service.get_memory(memory_id)

        if not memory:
            raise ValueError(f"Memory not found: {memory_id}")

        logger.info(f"Retrieved memory: memory_id={memory_id}")

        return memory

    def _tool_list_recent_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: list_recent_memories

        Lists recent memories in chronological order.

        Args:
            params: {
                'limit': int (optional, default: 20),
                'filter_metadata': dict (optional)
            }

        Returns:
            {
                'memories': [
                    {
                        'memory_id': str,
                        'summary': str,
                        'timestamp': str,
                        'schema_type': str
                    }
                ],
                'count': int
            }
        """
        limit = params.get('limit', 20)
        filter_metadata = params.get('filter_metadata')

        # List recent memories
        memories = self.search_service.list_recent(
            limit=limit,
            filter_metadata=filter_metadata
        )

        logger.info(f"Listed recent memories: count={len(memories)}")

        return {
            'memories': memories,
            'count': len(memories)
        }

    def _tool_consolidate_memories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: consolidate_memories

        Runs memory consolidation (clustering, migration, forgetting).

        Args:
            params: {} (no parameters required)

        Returns:
            {
                'migrated': int,
                'clusters': int,
                'compressed': int,
                'forgotten': int
            }
        """
        # Run consolidation
        stats = self.consolidation_service.consolidate()

        logger.info(f"Consolidated memories: {stats}")

        return stats

    def _tool_start_session(self, params: Dict[str, Any]) -> Dict[str, str]:
        """
        Tool: start_session (Phase 6)

        Starts a new working memory session.

        Args:
            params: {
                'session_id': str (optional)
            }

        Returns:
            {'session_id': str}

        Raises:
            ValueError: If session_manager is not configured
        """
        if not self.session_manager:
            raise ValueError("SessionManager not configured")

        session_id = params.get('session_id')

        # Start session
        session_id = self.session_manager.start_session(session_id)

        logger.info(f"Started session: session_id={session_id}")

        return {'session_id': session_id}

    def _tool_end_session(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: end_session (Phase 6)

        Ends a working memory session and ingests it.

        Args:
            params: {
                'session_id': str,
                'create_obsidian_note': bool (optional, default: False)
            }

        Returns:
            {'memory_id': str}

        Raises:
            ValueError: If session_id is missing or session_manager not configured
        """
        if not self.session_manager:
            raise ValueError("SessionManager not configured")

        session_id = params.get('session_id')

        if not session_id:
            raise ValueError("session_id parameter is required")

        create_obsidian_note = params.get('create_obsidian_note', False)

        # End session
        memory_id = self.session_manager.end_session(
            session_id,
            create_obsidian_note=create_obsidian_note
        )

        if not memory_id:
            raise ValueError(f"Session not found: {session_id}")

        logger.info(f"Ended session: session_id={session_id}, memory_id={memory_id}")

        return {'memory_id': memory_id}

    def _tool_add_command(self, params: Dict[str, Any]) -> Dict[str, bool]:
        """
        Tool: add_command (Phase 6)

        Adds a command to an active session.

        Args:
            params: {
                'session_id': str,
                'command': str,
                'output': str (optional),
                'exit_code': int (optional),
                'metadata': dict (optional)
            }

        Returns:
            {'success': bool}

        Raises:
            ValueError: If session_id or command is missing, or session_manager not configured
        """
        if not self.session_manager:
            raise ValueError("SessionManager not configured")

        session_id = params.get('session_id')
        command = params.get('command')

        if not session_id:
            raise ValueError("session_id parameter is required")

        if not command:
            raise ValueError("command parameter is required")

        output = params.get('output', '')
        exit_code = params.get('exit_code', 0)
        metadata = params.get('metadata')

        # Add command
        success = self.session_manager.add_command(
            session_id,
            command,
            output,
            exit_code=exit_code,
            metadata=metadata
        )

        logger.debug(f"Added command to session: session_id={session_id}, success={success}")

        return {'success': success}

    def _tool_session_get_hint(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session_manager:
            raise ValueError("SessionManager not configured")

        session_id = params.get('session_id')
        if not session_id:
            raise ValueError("session_id parameter is required")

        context = self.session_manager.get_project_context(session_id)
        return self._format_session_hint_response(session_id, context)

    def _tool_session_set_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session_manager:
            raise ValueError("SessionManager not configured")

        session_id = params.get('session_id')
        if not session_id:
            raise ValueError("session_id parameter is required")

        project_id = params.get('project_id')
        project_name = (
            params.get('project')
            or params.get('project_name')
            or params.get('project_hint')
        )
        project_identifier = project_id or project_name
        if not project_identifier:
            raise ValueError("project_id or project name is required")

        canonical_identifier = project_identifier
        if project_id and self.project_manager:
            project = self.project_manager.get_project(project_id)
            if not project:
                raise ValueError(f"Project not found: {project_id}")
            canonical_identifier = project.name

        confidence = params.get('confidence', 0.99)
        success = self.session_manager.set_project_hint(
            session_id,
            canonical_identifier,
            confidence=confidence,
            source='manual_rpc'
        )
        if not success:
            raise ValueError("Failed to set project hint")

        context = self.session_manager.get_project_context(session_id)
        return self._format_session_hint_response(session_id, context)

    def _tool_session_clear_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session_manager:
            raise ValueError("SessionManager not configured")

        session_id = params.get('session_id')
        if not session_id:
            raise ValueError("session_id parameter is required")

        success = self.session_manager.clear_project_hint(session_id)
        if not success:
            raise ValueError(f"Session not found: {session_id}")

        response = self._format_session_hint_response(session_id, None)
        response['cleared'] = True
        return response

    # Phase 15: Project Management Tools

    def _tool_create_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: create_project (Phase 15)

        Creates a new project for organizing memories.

        Args:
            params: {
                'name': str,
                'description': str,
                'tags': list[str] (optional)
            }

        Returns:
            {
                'project_id': str,
                'name': str,
                'created_at': str
            }

        Raises:
            ValueError: If project_manager is not available or parameters invalid
        """
        if not self.project_manager:
            raise ValueError("Project management is not enabled")

        name = params.get('name')
        description = params.get('description')
        tags = params.get('tags', [])

        if not name:
            raise ValueError("name parameter is required")
        if not description:
            raise ValueError("description parameter is required")

        # Create project
        project = self.project_manager.create_project(
            name=name,
            description=description,
            tags=tags
        )

        logger.info(f"Created project: {project.id} ({project.name})")

        return {
            'project_id': project.id,
            'name': project.name,
            'description': project.description,
            'tags': project.tags,
            'created_at': project.created_at.isoformat()
        }

    def _tool_list_projects(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: list_projects (Phase 15)

        Lists all projects.

        Args:
            params: {} (no parameters)

        Returns:
            {
                'projects': [
                    {
                        'project_id': str,
                        'name': str,
                        'description': str,
                        'tags': list[str],
                        'memory_count': int,
                        'last_accessed': str
                    },
                    ...
                ]
            }

        Raises:
            ValueError: If project_manager is not available
        """
        if not self.project_manager:
            raise ValueError("Project management is not enabled")

        projects = self.project_manager.list_projects()

        project_list = [
            {
                'project_id': p.id,
                'name': p.name,
                'description': p.description,
                'tags': p.tags,
                'memory_count': p.memory_count,
                'last_accessed': p.last_accessed.isoformat()
            }
            for p in projects
        ]

        logger.debug(f"Listed {len(project_list)} projects")

        return {'projects': project_list}

    def _tool_get_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: get_project (Phase 15)

        Gets a project by ID or name.

        Args:
            params: {
                'project_id': str (optional),
                'name': str (optional)
            }

        Returns:
            {
                'project_id': str,
                'name': str,
                'description': str,
                'tags': list[str],
                'memory_count': int,
                'created_at': str,
                'last_accessed': str
            }

        Raises:
            ValueError: If project_manager is not available or project not found
        """
        if not self.project_manager:
            raise ValueError("Project management is not enabled")

        project_id = params.get('project_id')
        name = params.get('name')

        if not project_id and not name:
            raise ValueError("Either project_id or name must be provided")

        if project_id:
            project = self.project_manager.get_project(project_id)
        else:
            project = self.project_manager.get_project_by_name(name)

        if not project:
            raise ValueError(f"Project not found: {project_id or name}")

        return {
            'project_id': project.id,
            'name': project.name,
            'description': project.description,
            'tags': project.tags,
            'memory_count': project.memory_count,
            'created_at': project.created_at.isoformat(),
            'last_accessed': project.last_accessed.isoformat(),
            'metadata': project.metadata
        }

    def _tool_delete_project(self, params: Dict[str, Any]) -> Dict[str, bool]:
        """
        Tool: delete_project (Phase 15)

        Deletes a project by ID.

        Args:
            params: {
                'project_id': str
            }

        Returns:
            {'success': bool}

        Raises:
            ValueError: If project_manager is not available or project_id missing
        """
        if not self.project_manager:
            raise ValueError("Project management is not enabled")

        project_id = params.get('project_id')
        if not project_id:
            raise ValueError("project_id parameter is required")

        success = self.project_manager.delete_project(project_id)

        logger.info(f"Deleted project: {project_id}, success={success}")

        return {'success': success}

    def _tool_search_in_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: search_in_project (Phase 15)

        Searches memories within a specific project.

        Args:
            params: {
                'project_id': str,
                'query': str,
                'top_k': int (optional),
                'filters': dict (optional)
            }

        Returns:
            {
                'results': [
                    {
                        'id': str,
                        'content': str,
                        'score': float,
                        'metadata': dict
                    },
                    ...
                ]
            }

        Raises:
            ValueError: If parameters invalid
        """
        project_id = params.get('project_id')
        query = params.get('query')
        top_k = params.get('top_k')
        additional_filters = params.get('filters')

        if not project_id:
            raise ValueError("project_id parameter is required")
        if not query:
            raise ValueError("query parameter is required")

        # Search in project
        results = self.search_service.search_in_project(
            project_id=project_id,
            query=query,
            top_k=top_k,
            additional_filters=additional_filters
        )

        logger.info(f"Project search returned {len(results)} results")

        return {'results': results}

    # Phase 15: Bookmark Management Tools

    def _tool_create_bookmark(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: create_bookmark (Phase 15)

        Creates a new search bookmark.

        Args:
            params: {
                'name': str,
                'query': str,
                'filters': dict (optional),
                'description': str (optional)
            }

        Returns:
            {
                'bookmark_id': str,
                'name': str,
                'query': str,
                'created_at': str
            }

        Raises:
            ValueError: If bookmark_manager is not available or parameters invalid
        """
        if not self.bookmark_manager:
            raise ValueError("Bookmark management is not enabled")

        name = params.get('name')
        query = params.get('query')
        filters = params.get('filters', {})
        description = params.get('description', '')

        if not name:
            raise ValueError("name parameter is required")
        if not query:
            raise ValueError("query parameter is required")

        # Create bookmark
        bookmark = self.bookmark_manager.create_bookmark(
            name=name,
            query=query,
            filters=filters,
            description=description
        )

        logger.info(f"Created bookmark: {bookmark.id} ({bookmark.name})")

        return {
            'bookmark_id': bookmark.id,
            'name': bookmark.name,
            'query': bookmark.query,
            'filters': bookmark.filters,
            'created_at': bookmark.created_at.isoformat()
        }

    def _tool_list_bookmarks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: list_bookmarks (Phase 15)

        Lists all search bookmarks.

        Args:
            params: {} (no parameters)

        Returns:
            {
                'bookmarks': [
                    {
                        'bookmark_id': str,
                        'name': str,
                        'query': str,
                        'filters': dict,
                        'usage_count': int,
                        'last_used': str
                    },
                    ...
                ]
            }

        Raises:
            ValueError: If bookmark_manager is not available
        """
        if not self.bookmark_manager:
            raise ValueError("Bookmark management is not enabled")

        bookmarks = self.bookmark_manager.list_bookmarks()

        bookmark_list = [
            {
                'bookmark_id': b.id,
                'name': b.name,
                'query': b.query,
                'filters': b.filters,
                'usage_count': b.usage_count,
                'last_used': b.last_used.isoformat(),
                'description': b.description
            }
            for b in bookmarks
        ]

        logger.debug(f"Listed {len(bookmark_list)} bookmarks")

        return {'bookmarks': bookmark_list}

    def _tool_use_bookmark(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: use_bookmark (Phase 15)

        Executes a saved bookmark search.

        Args:
            params: {
                'bookmark_id': str (optional),
                'name': str (optional),
                'top_k': int (optional)
            }

        Returns:
            {
                'bookmark_name': str,
                'results': [...]  # Same as search_memory
            }

        Raises:
            ValueError: If bookmark_manager is not available or bookmark not found
        """
        if not self.bookmark_manager:
            raise ValueError("Bookmark management is not enabled")

        bookmark_id = params.get('bookmark_id')
        name = params.get('name')
        top_k = params.get('top_k')

        if not bookmark_id and not name:
            raise ValueError("Either bookmark_id or name must be provided")

        # Execute bookmark
        if bookmark_id:
            bookmark_data = self.bookmark_manager.execute_bookmark(bookmark_id)
        else:
            bookmark_data = self.bookmark_manager.execute_bookmark_by_name(name)

        if not bookmark_data:
            raise ValueError(f"Bookmark not found: {bookmark_id or name}")

        # Execute search with bookmark query and filters
        results = self.search_service.search(
            query=bookmark_data['query'],
            top_k=top_k,
            filters=bookmark_data['filters']
        )

        logger.info(f"Bookmark search '{bookmark_data['bookmark_name']}' returned {len(results)} results")

        return {
            'bookmark_name': bookmark_data['bookmark_name'],
            'query': bookmark_data['query'],
            'filters': bookmark_data['filters'],
            'results': results
        }

    def _tool_get_reranker_metrics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool: get_reranker_metrics

        Returns cache / latency statistics for the cross-encoder reranker.
        """
        return self.search_service.get_reranker_metrics()

    # Helper methods for JSON-RPC responses

    def _create_success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        """
        Create JSON-RPC success response

        Args:
            request_id: Request ID
            result: Result data

        Returns:
            JSON-RPC response dict
        """
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': result
        }

    def _create_error_response(
        self,
        request_id: Any,
        code: int,
        message: str,
        data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create JSON-RPC error response

        Args:
            request_id: Request ID
            code: Error code (JSON-RPC standard codes)
            message: Error message
            data: Optional error details

        Returns:
            JSON-RPC error response dict
        """
        error = {
            'code': code,
            'message': message
        }

        if data:
            error['data'] = data

        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': error
        }
