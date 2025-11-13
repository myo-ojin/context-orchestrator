#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from scripts.train_rerank_weights import (
    FEATURE_COLUMNS,
    load_feature_rows,
    normalize_weights,
    train_weights,
)


def _write_features(tmp_path: Path) -> Path:
    path = tmp_path / "features.csv"
    lines = [
        "memory_strength,recency,refs_reliability,bm25_score,vector_similarity,metadata_bonus,is_relevant",
        "0.9,0.8,0.5,0.7,0.6,0.05,1",
        "0.2,0.2,0.1,0.6,0.3,0.02,0",
        "0.85,0.4,0.2,0.5,0.7,0.01,1",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_load_feature_rows(tmp_path: Path):
    feature_path = _write_features(tmp_path)
    rows = load_feature_rows([feature_path])
    assert len(rows) == 3
    assert rows[0]["label"] == 1.0
    assert rows[1]["memory_strength"] == 0.2


def test_train_weights_prefers_informative_feature(tmp_path: Path):
    feature_path = _write_features(tmp_path)
    rows = load_feature_rows([feature_path])
    weights = train_weights(rows, epochs=100, learning_rate=0.15, l2=0.0)
    normalized = normalize_weights(weights)
    assert normalized["memory_strength"] > normalized["refs_reliability"]
