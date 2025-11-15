#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit tests for MCPProtocolHandler

Tests MCP protocol handling including:
- JSON-RPC request/response format
- Method routing
- Tool implementations
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from io import StringIO
from types import SimpleNamespace

from src.mcp.protocol_handler import MCPProtocolHandler


class TestMCPProtocolHandler:
    """Test suite for MCPProtocolHandler"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for MCPProtocolHandler"""
        ingestion_service = Mock()
        search_service = Mock()
        consolidation_service = Mock()
        session_manager = Mock()
        project_manager = Mock()

        return {
            'ingestion_service': ingestion_service,
            'search_service': search_service,
            'consolidation_service': consolidation_service,
            'session_manager': session_manager,
            'project_manager': project_manager
        }

    @pytest.fixture
    def handler(self, mock_dependencies):
        """Create MCPProtocolHandler instance with mocks"""
        return MCPProtocolHandler(
            ingestion_service=mock_dependencies['ingestion_service'],
            search_service=mock_dependencies['search_service'],
            consolidation_service=mock_dependencies['consolidation_service'],
            session_manager=mock_dependencies['session_manager'],
            project_manager=mock_dependencies['project_manager']
        )

    def test_init(self, handler, mock_dependencies):
        """Test handler initialization"""
        assert handler.ingestion_service == mock_dependencies['ingestion_service']
        assert handler.search_service == mock_dependencies['search_service']
        assert handler.consolidation_service == mock_dependencies['consolidation_service']
        assert handler.session_manager == mock_dependencies['session_manager']

    def test_handle_request_success(self, handler, mock_dependencies):
        """Test successful request handling"""
        request = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'search_memory',
            'params': {'query': 'test query', 'top_k': 5}
        }

        mock_dependencies['search_service'].search.return_value = [
            {'memory_id': 'mem-1', 'content': 'result 1', 'score': 0.9}
        ]

        response = handler.handle_request(request)

        assert response['jsonrpc'] == '2.0'
        assert response['id'] == 1
        assert 'result' in response
        assert response['result']['count'] == 1

    def test_handle_request_missing_jsonrpc_version(self, handler):
        """Test request without jsonrpc version"""
        request = {
            'id': 1,
            'method': 'search_memory',
            'params': {}
        }

        response = handler.handle_request(request)

        assert 'error' in response
        assert response['error']['code'] == -32600
        assert response['error']['message'] == 'Invalid Request'
        assert 'jsonrpc version' in response['error']['data']

    def test_handle_request_missing_method(self, handler):
        """Test request without method"""
        request = {
            'jsonrpc': '2.0',
            'id': 1,
            'params': {}
        }

        response = handler.handle_request(request)

        assert 'error' in response
        assert response['error']['code'] == -32600
        assert response['error']['message'] == 'Invalid Request'
        assert 'method is required' in response['error']['data']

    def test_handle_request_unknown_method(self, handler):
        """Test request with unknown method"""
        request = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'unknown_method',
            'params': {}
        }

        response = handler.handle_request(request)

        assert 'error' in response
        assert response['error']['code'] == -32601
        assert 'Method not found' in response['error']['message']

    def test_handle_request_invalid_params(self, handler):
        """Test request with invalid params"""
        request = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'search_memory',
            'params': {}  # Missing required 'query'
        }

        response = handler.handle_request(request)

        assert 'error' in response
        assert response['error']['code'] == -32602

    def test_tool_ingest_conversation(self, handler, mock_dependencies):
        """Test ingest_conversation tool"""
        params = {
            'conversation': {
                'user': 'How do I fix this bug?',
                'assistant': 'Try this solution...',
                'timestamp': '2025-01-15T10:00:00Z',
                'source': 'cli',
                'metadata': {}
            }
        }

        mock_dependencies['ingestion_service'].ingest_conversation.return_value = 'mem-123'

        result = handler._tool_ingest_conversation(params)

        assert result['memory_id'] == 'mem-123'
        mock_dependencies['ingestion_service'].ingest_conversation.assert_called_once()

    def test_tool_ingest_conversation_missing_conversation(self, handler):
        """Test ingest_conversation without conversation param"""
        with pytest.raises(ValueError, match='conversation parameter is required'):
            handler._tool_ingest_conversation({})

    def test_tool_ingest_conversation_missing_fields(self, handler):
        """Test ingest_conversation with missing required fields"""
        params = {
            'conversation': {
                'user': 'test'
                # Missing assistant, timestamp, source
            }
        }

        with pytest.raises(ValueError, match='is required'):
            handler._tool_ingest_conversation(params)

    def test_tool_search_memory(self, handler, mock_dependencies):
        """Test search_memory tool"""
        params = {
            'query': 'bug fix',
            'top_k': 10
        }

        mock_dependencies['search_service'].search.return_value = [
            {'memory_id': 'mem-1', 'content': 'result 1', 'score': 0.9},
            {'memory_id': 'mem-2', 'content': 'result 2', 'score': 0.8}
        ]

        result = handler._tool_search_memory(params)

        assert result['count'] == 2
        assert len(result['results']) == 2
        mock_dependencies['search_service'].search.assert_called_once_with(
            query='bug fix',
            top_k=10,
            filters=None
        )

    def test_tool_search_memory_missing_query(self, handler):
        """Test search_memory without query param"""
        with pytest.raises(ValueError, match='query parameter is required'):
            handler._tool_search_memory({})

    def test_tool_search_memory_with_filter(self, handler, mock_dependencies):
        """Test search_memory with metadata filter"""
        params = {
            'query': 'test',
            'filter_metadata': {'schema_type': 'Incident'}
        }

        mock_dependencies['search_service'].search.return_value = []

        handler._tool_search_memory(params)

        mock_dependencies['search_service'].search.assert_called_once_with(
            query='test',
            top_k=10,
            filters={'schema_type': 'Incident'}
        )

    def test_tool_search_memory_applies_session_project_hint(self, handler, mock_dependencies):
        """Session project hint should inject project_id filter."""
        params = {
            'query': 'timeline',
            'session_id': 'session-1'
        }

        mock_dependencies['session_manager'].get_project_context.return_value = {
            'project_id': 'proj-xyz',
            'confidence': 0.9
        }
        mock_dependencies['search_service'].search.return_value = []

        handler._tool_search_memory(params)

        mock_dependencies['search_service'].search.assert_called_once_with(
            query='timeline',
            top_k=10,
            filters={'project_id': 'proj-xyz'}
        )

    def test_tool_search_memory_does_not_override_user_project_filter(self, handler, mock_dependencies):
        params = {
            'query': 'timeline',
            'session_id': 'session-1',
            'filter_metadata': {'project_id': 'user-proj'}
        }
        mock_dependencies['session_manager'].get_project_context.return_value = {
            'project_id': 'proj-xyz',
            'confidence': 0.95
        }
        mock_dependencies['search_service'].search.return_value = []

        handler._tool_search_memory(params)

        mock_dependencies['search_service'].search.assert_called_once_with(
            query='timeline',
            top_k=10,
            filters={'project_id': 'user-proj'}
        )

    def test_tool_session_get_hint(self, handler, mock_dependencies):
        params = {'session_id': 'session-123'}
        mock_dependencies['session_manager'].get_project_context.return_value = {
            'project_name': 'OrchestratorX',
            'project_id': 'proj-1',
            'confidence': 0.9,
            'source': 'metadata'
        }

        result = handler._tool_session_get_hint(params)

        assert result['project_hint'] == 'OrchestratorX'
        assert result['project_id'] == 'proj-1'
        mock_dependencies['session_manager'].get_project_context.assert_called_once_with('session-123')

    def test_tool_session_set_project_uses_project_manager(self, handler, mock_dependencies):
        params = {
            'session_id': 'session-1',
            'project_id': 'proj-777',
            'confidence': 0.8
        }
        mock_dependencies['project_manager'].get_project.return_value = SimpleNamespace(
            id='proj-777',
            name='OrchestratorX'
        )
        mock_dependencies['session_manager'].set_project_hint.return_value = True
        mock_dependencies['session_manager'].get_project_context.return_value = {
            'project_name': 'OrchestratorX',
            'project_id': 'proj-777',
            'confidence': 0.8,
            'source': 'manual_rpc'
        }

        result = handler._tool_session_set_project(params)

        assert result['project_hint'] == 'OrchestratorX'
        mock_dependencies['project_manager'].get_project.assert_called_once_with('proj-777')
        mock_dependencies['session_manager'].set_project_hint.assert_called_once_with(
            'session-1',
            'OrchestratorX',
            confidence=0.8,
            source='manual_rpc'
        )

    def test_tool_session_clear_project(self, handler, mock_dependencies):
        params = {'session_id': 'session-1'}
        mock_dependencies['session_manager'].clear_project_hint.return_value = True

        result = handler._tool_session_clear_project(params)

        assert result['cleared'] is True
        assert result['project_hint'] is None
        mock_dependencies['session_manager'].clear_project_hint.assert_called_once_with('session-1')

    def test_tool_get_memory(self, handler, mock_dependencies):
        """Test get_memory tool"""
        params = {'memory_id': 'mem-123'}

        mock_dependencies['search_service'].get_memory.return_value = {
            'memory_id': 'mem-123',
            'content': 'Memory content',
            'metadata': {'schema_type': 'Snippet'}
        }

        result = handler._tool_get_memory(params)

        assert result['memory_id'] == 'mem-123'
        assert result['content'] == 'Memory content'
        mock_dependencies['search_service'].get_memory.assert_called_once_with('mem-123')

    def test_tool_get_memory_missing_id(self, handler):
        """Test get_memory without memory_id param"""
        with pytest.raises(ValueError, match='memory_id parameter is required'):
            handler._tool_get_memory({})

    def test_tool_get_memory_not_found(self, handler, mock_dependencies):
        """Test get_memory for nonexistent memory"""
        params = {'memory_id': 'nonexistent'}

        mock_dependencies['search_service'].get_memory.return_value = None

        with pytest.raises(ValueError, match='Memory not found'):
            handler._tool_get_memory(params)

    def test_tool_list_recent_memories(self, handler, mock_dependencies):
        """Test list_recent_memories tool"""
        params = {'limit': 5}

        mock_dependencies['search_service'].list_recent.return_value = [
            {'memory_id': 'mem-1', 'summary': 'Recent memory 1'},
            {'memory_id': 'mem-2', 'summary': 'Recent memory 2'}
        ]

        result = handler._tool_list_recent_memories(params)

        assert result['count'] == 2
        assert len(result['memories']) == 2
        mock_dependencies['search_service'].list_recent.assert_called_once_with(
            limit=5,
            filter_metadata=None
        )

    def test_tool_list_recent_memories_default_limit(self, handler, mock_dependencies):
        """Test list_recent_memories with default limit"""
        mock_dependencies['search_service'].list_recent.return_value = []

        handler._tool_list_recent_memories({})

        mock_dependencies['search_service'].list_recent.assert_called_once_with(
            limit=20,
            filter_metadata=None
        )

    def test_tool_consolidate_memories(self, handler, mock_dependencies):
        """Test consolidate_memories tool"""
        mock_dependencies['consolidation_service'].consolidate.return_value = {
            'migrated': 5,
            'clusters': 3,
            'compressed': 10,
            'forgotten': 2
        }

        result = handler._tool_consolidate_memories({})

        assert result['migrated'] == 5
        assert result['clusters'] == 3
        assert result['compressed'] == 10
        assert result['forgotten'] == 2
        mock_dependencies['consolidation_service'].consolidate.assert_called_once()

    def test_tool_start_session(self, handler, mock_dependencies):
        """Test start_session tool"""
        mock_dependencies['session_manager'].start_session.return_value = 'session-123'

        result = handler._tool_start_session({})

        assert result['session_id'] == 'session-123'
        mock_dependencies['session_manager'].start_session.assert_called_once()

    def test_tool_start_session_with_custom_id(self, handler, mock_dependencies):
        """Test start_session with custom session ID"""
        params = {'session_id': 'my-session'}

        mock_dependencies['session_manager'].start_session.return_value = 'my-session'

        result = handler._tool_start_session(params)

        assert result['session_id'] == 'my-session'
        mock_dependencies['session_manager'].start_session.assert_called_once_with('my-session')

    def test_tool_start_session_no_manager(self, handler):
        """Test start_session without session manager"""
        handler.session_manager = None

        with pytest.raises(ValueError, match='SessionManager not configured'):
            handler._tool_start_session({})

    def test_tool_end_session(self, handler, mock_dependencies):
        """Test end_session tool"""
        params = {'session_id': 'session-123'}

        mock_dependencies['session_manager'].end_session.return_value = 'mem-456'

        result = handler._tool_end_session(params)

        assert result['memory_id'] == 'mem-456'
        mock_dependencies['session_manager'].end_session.assert_called_once_with(
            'session-123',
            create_obsidian_note=False
        )

    def test_tool_end_session_with_obsidian_note(self, handler, mock_dependencies):
        """Test end_session with Obsidian note creation"""
        params = {
            'session_id': 'session-123',
            'create_obsidian_note': True
        }

        mock_dependencies['session_manager'].end_session.return_value = 'mem-456'

        handler._tool_end_session(params)

        mock_dependencies['session_manager'].end_session.assert_called_once_with(
            'session-123',
            create_obsidian_note=True
        )

    def test_tool_end_session_missing_id(self, handler):
        """Test end_session without session_id"""
        with pytest.raises(ValueError, match='session_id parameter is required'):
            handler._tool_end_session({})

    def test_tool_end_session_not_found(self, handler, mock_dependencies):
        """Test end_session for nonexistent session"""
        params = {'session_id': 'nonexistent'}

        mock_dependencies['session_manager'].end_session.return_value = None

        with pytest.raises(ValueError, match='Session not found'):
            handler._tool_end_session(params)

    def test_tool_add_command(self, handler, mock_dependencies):
        """Test add_command tool"""
        params = {
            'session_id': 'session-123',
            'command': 'python test.py',
            'output': 'All tests passed',
            'exit_code': 0
        }

        mock_dependencies['session_manager'].add_command.return_value = True

        result = handler._tool_add_command(params)

        assert result['success'] is True
        mock_dependencies['session_manager'].add_command.assert_called_once_with(
            'session-123',
            'python test.py',
            'All tests passed',
            exit_code=0,
            metadata=None
        )

    def test_tool_add_command_missing_params(self, handler):
        """Test add_command with missing params"""
        # Missing command
        with pytest.raises(ValueError, match='command parameter is required'):
            handler._tool_add_command({'session_id': 'session-123'})

        # Missing session_id
        with pytest.raises(ValueError, match='session_id parameter is required'):
            handler._tool_add_command({'command': 'test'})

    def test_create_success_response(self, handler):
        """Test success response creation"""
        response = handler._create_success_response(1, {'data': 'test'})

        assert response['jsonrpc'] == '2.0'
        assert response['id'] == 1
        assert response['result'] == {'data': 'test'}

    def test_create_error_response(self, handler):
        """Test error response creation"""
        response = handler._create_error_response(
            1,
            -32600,
            'Invalid Request',
            'Additional error data'
        )

        assert response['jsonrpc'] == '2.0'
        assert response['id'] == 1
        assert 'error' in response
        assert response['error']['code'] == -32600
        assert response['error']['message'] == 'Invalid Request'
        assert response['error']['data'] == 'Additional error data'

    def test_create_error_response_without_data(self, handler):
        """Test error response without data field"""
        response = handler._create_error_response(1, -32601, 'Method not found')

        assert 'data' not in response['error']

    def test_route_to_service_all_methods(self, handler, mock_dependencies):
        """Test routing for all supported methods"""
        # Mock all service methods
        mock_dependencies['ingestion_service'].ingest_conversation.return_value = 'mem-1'
        mock_dependencies['search_service'].search.return_value = []
        mock_dependencies['search_service'].get_memory.return_value = {'memory_id': 'mem-1'}
        mock_dependencies['search_service'].list_recent.return_value = []
        mock_dependencies['consolidation_service'].consolidate.return_value = {}
        mock_dependencies['session_manager'].start_session.return_value = 'session-1'
        mock_dependencies['session_manager'].end_session.return_value = 'mem-1'
        mock_dependencies['session_manager'].add_command.return_value = True

        # Test all methods
        methods = [
            ('ingest_conversation', {
                'conversation': {
                    'user': 'test',
                    'assistant': 'response',
                    'timestamp': '2025-01-15T10:00:00Z',
                    'source': 'cli'
                }
            }),
            ('search_memory', {'query': 'test'}),
            ('get_memory', {'memory_id': 'mem-1'}),
            ('list_recent_memories', {}),
            ('consolidate_memories', {}),
            ('start_session', {}),
            ('end_session', {'session_id': 'session-1'}),
            ('add_command', {'session_id': 'session-1', 'command': 'test'})
        ]

        for method, params in methods:
            result = handler._route_to_service(method, params)
            assert result is not None

    def test_full_request_response_cycle(self, handler, mock_dependencies):
        """Test full request/response cycle"""
        request = {
            'jsonrpc': '2.0',
            'id': 42,
            'method': 'search_memory',
            'params': {'query': 'test query'}
        }

        mock_dependencies['search_service'].search.return_value = [
            {'memory_id': 'mem-1', 'content': 'result', 'score': 0.9}
        ]

        response = handler.handle_request(request)

        # Verify response structure
        assert response['jsonrpc'] == '2.0'
        assert response['id'] == 42
        assert 'result' in response
        assert response['result']['count'] == 1
        assert len(response['result']['results']) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
