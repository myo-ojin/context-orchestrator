#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP stdio runner (smoke)

Initializes runtime (config, storage, models, services) and starts the
MCPProtocolHandler on stdio. Useful for local JSON-RPC smoke tests:

  echo {"jsonrpc":"2.0","id":1,"method":"search_memory","params":{"query":"test","top_k":3}} | \
      python -m scripts.mcp_stdio
"""

from src.config import load_config
from src.main import init_storage, init_models, init_processing, init_services
from src.mcp.protocol_handler import MCPProtocolHandler
from src.utils.logger import setup_root_logger


def main() -> int:
    setup_root_logger('INFO')
    config = load_config('config.yaml')

    vector_db, bm25_index = init_storage(config)
    model_router = init_models(config)
    classifier, chunker, indexer = init_processing(model_router, vector_db, bm25_index)

    (
        ingestion_service,
        search_service,
        consolidation_service,
        session_manager,
        obsidian_watcher,
        project_manager,
        bookmark_manager,
    ) = init_services(
        config=config,
        model_router=model_router,
        vector_db=vector_db,
        bm25_index=bm25_index,
        classifier=classifier,
        chunker=chunker,
        indexer=indexer,
    )

    handler = MCPProtocolHandler(
        ingestion_service=ingestion_service,
        search_service=search_service,
        consolidation_service=consolidation_service,
        session_manager=session_manager,
        project_manager=project_manager,
        bookmark_manager=bookmark_manager,
    )

    handler.start()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

