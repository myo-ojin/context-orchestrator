#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
E2E Smoke Test

Runs a minimal end-to-end flow using the real runtime:
- Initialize storage/models/services
- Optionally create a Project (Phase 15)
- Ingest a small conversation (with project_id if available)
- Run search and (if available) search_in_project
- Print concise results to stdout
"""

from datetime import datetime

from src.config import load_config
from src.main import init_storage, init_models, init_processing, init_services
from src.utils.logger import setup_logger


def main() -> int:
    logger = setup_logger('e2e_smoke', 'INFO')

    config = load_config('config.yaml')

    # Initialize runtime
    vector_db, bm25_index = init_storage(config)
    model_router = init_models(config)
    classifier, chunker, indexer = init_processing(model_router, vector_db, bm25_index)

    services = init_services(
        config=config,
        model_router=model_router,
        vector_db=vector_db,
        bm25_index=bm25_index,
        classifier=classifier,
        chunker=chunker,
        indexer=indexer,
    )

    (
        ingestion_service,
        search_service,
        consolidation_service,
        session_manager,
        obsidian_watcher,
        project_manager,
        bookmark_manager,
    ) = services

    # Create a project if manager is available
    project_id = None
    if project_manager:
        project = project_manager.create_project(
            name=f"Smoke Test Project {datetime.now().strftime('%H%M%S')}",
            description="Temporary project for e2e smoke test",
            tags=["smoke", "test"],
        )
        project_id = project.id
        logger.info(f"Created project: {project_id}")

    # Ingest a small conversation
    conversation = {
        'user': 'How do I fix a TypeError in Python when adding string and int?',
        'assistant': (
            'A TypeError occurs when operating on incompatible types.\n'
            'Example:\n```python\nx = "5"\ny = 10\nresult = x + y  # TypeError\n```\n'
            'Fix by converting types:\n```python\nresult = int(x) + y\n```'
        ),
        'timestamp': datetime.now().isoformat(),
        'source': 'smoke_test',
        'refs': ['https://docs.python.org/3/tutorial/errors.html#typeerror'],
        'metadata': {'origin': 'smoke'},
    }
    if project_id:
        conversation['project_id'] = project_id

    memory_id = ingestion_service.ingest_conversation(conversation)
    print(f"Ingested memory: {memory_id}")

    # Global search
    results = search_service.search('Python TypeError fix', top_k=5)
    print(f"Global search results: {len(results)}")
    if results:
        top = results[0]
        snippet = (top.get('content') or '')[:120].replace('\n', ' ')
        print(f"Top: id={top.get('id')} score={top.get('score', top.get('combined_score'))} -> {snippet}")

    # Project-scoped search (Phase 15)
    if project_id:
        proj_results = search_service.search_in_project(project_id, 'TypeError', top_k=5)
        print(f"Project search results: {len(proj_results)} (project_id={project_id})")
        if proj_results:
            top = proj_results[0]
            snippet = (top.get('content') or '')[:120].replace('\n', ' ')
            print(f"Project Top: id={top.get('id')} score={top.get('score', top.get('combined_score'))} -> {snippet}")

    print('OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

