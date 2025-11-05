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

logger = logging.getLogger(__name__)


class MCPProtocolHandler:
    """
    MCP Protocol Handler for stdio JSON-RPC communication

    Exposes tools via JSON-RPC:
    - ingest_conversation: Record conversation
    - search_memory: Search memories
    - get_memory: Get specific memory
    - list_recent_memories: List recent memories
    - consolidate_memories: Run consolidation

    Attributes:
        ingestion_service: IngestionService instance
        search_service: SearchService instance
        consolidation_service: ConsolidationService instance
        session_manager: SessionManager instance (optional)
    """

    def __init__(
        self,
        ingestion_service: IngestionService,
        search_service: SearchService,
        consolidation_service: ConsolidationService,
        session_manager: Optional[SessionManager] = None
    ):
        """
        Initialize MCP Protocol Handler

        Args:
            ingestion_service: IngestionService instance
            search_service: SearchService instance
            consolidation_service: ConsolidationService instance
            session_manager: Optional SessionManager instance
        """
        self.ingestion_service = ingestion_service
        self.search_service = search_service
        self.consolidation_service = consolidation_service
        self.session_manager = session_manager

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
                'filter_metadata': dict (optional)
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
        filter_metadata = params.get('filter_metadata')

        # Search memories
        results = self.search_service.search(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata
        )

        logger.info(f"Searched memories: query='{query}', results={len(results)}")

        return {
            'results': results,
            'count': len(results)
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
