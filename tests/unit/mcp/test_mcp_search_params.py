#!/usr/bin/env python
# -*- coding: utf-8 -*-

from types import SimpleNamespace


def test_mcp_maps_filter_metadata_to_filters():
    from src.mcp.protocol_handler import MCPProtocolHandler

    calls = {}

    class _Search:
        def search(self, **kwargs):
            calls.update(kwargs)
            return []

    handler = MCPProtocolHandler(
        ingestion_service=None,
        search_service=_Search(),
        consolidation_service=None,
    )

    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "search_memory",
        "params": {"query": "foo", "top_k": 5, "filter_metadata": {"a": 1}},
    }

    resp = handler.handle_request(req)

    # mapped to 'filters'
    assert calls.get("filters") == {"a": 1}
    # not passed as 'filter_metadata'
    assert "filter_metadata" not in calls
    assert resp.get("result") is not None

