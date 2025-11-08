#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Load synthetic scenario conversations into the knowledge base."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from src.config import load_config
from src.main import init_storage, init_models, init_processing, init_services
from src.utils.logger import setup_root_logger


def ingest_conversation(ingestion_service, conversation, project_manager=None):
    convo = {
        "user": conversation["user"],
        "assistant": conversation["assistant"],
        "source": conversation.get("source", "scenario"),
        "refs": conversation.get("refs", []),
        "metadata": conversation.get("metadata", {}),
        "timestamp": conversation.get("timestamp")
            or datetime.now().isoformat(),
    }

    if project_manager and conversation.get("project"):
        convo["project_id"] = ensure_project(project_manager, conversation["project"])

    ingestion_service.ingest_conversation(convo)


_project_cache = {}


def ensure_project(project_manager, project_name):
    if project_name in _project_cache:
        return _project_cache[project_name]

    existing = project_manager.get_project_by_name(project_name)
    if existing:
        _project_cache[project_name] = existing.id
        return existing.id

    project = project_manager.create_project(project_name, f"Scenario project: {project_name}")
    _project_cache[project_name] = project.id
    return project.id


def main():
    parser = argparse.ArgumentParser(description="Load scenario conversations")
    parser.add_argument("--file", default="tests/scenarios/scenario_data.json")
    args = parser.parse_args()

    setup_root_logger("INFO")
    config = load_config()

    vector_db, bm25_index = init_storage(config)
    model_router = init_models(config)
    classifier, chunker, indexer = init_processing(model_router, vector_db, bm25_index)
    services = init_services(config, model_router, vector_db, bm25_index, classifier, chunker, indexer)
    ingestion_service, search_service, consolidation_service, session_manager, obsidian_watcher, project_manager, bookmark_manager = services

    data_path = Path(args.file)
    with data_path.open("r", encoding="utf-8") as fp:
        scenario = json.load(fp)

    for project in scenario.get("projects", []):
        if project_manager:
            ensure_project(project_manager, project["name"])

    for conv in scenario.get("conversations", []):
        ingest_conversation(ingestion_service, conv, project_manager)

    print(f"Loaded {len(scenario.get('conversations', []))} conversations from {data_path}")


if __name__ == "__main__":
    main()
