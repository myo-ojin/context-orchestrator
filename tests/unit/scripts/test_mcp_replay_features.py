#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import json

from scripts.mcp_replay import export_rerank_features


def test_export_rerank_features(tmp_path: Path):
    results = [
        {
            "request": {"id": 1, "method": "search_memory"},
            "response": {
                "result": {
                    "results": [
                        {
                            "id": "mem-1",
                            "score": 0.8,
                            "metadata": {"memory_id": "mem-1", "topic": "release"},
                            "components": {
                                "memory_strength": 0.9,
                                "recency": 0.7,
                                "refs_reliability": 0.2,
                                "bm25": 0.6,
                                "vector": 0.5,
                                "metadata": 0.05,
                            },
                        }
                    ]
                }
            },
            "relevance": {"topic": ["release"], "ideal_hits": 1},
        }
    ]

    out_csv = tmp_path / "features.csv"
    export_rerank_features(results, out_csv)

    content = out_csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(content) == 2  # header + row
    header = content[0].split(",")
    assert "is_relevant" in header
