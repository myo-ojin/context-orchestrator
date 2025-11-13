#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Train linear reranking weights from feature exports produced by scripts.mcp_replay.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Dict, List

import yaml

FEATURE_COLUMNS = [
    "memory_strength",
    "recency",
    "refs_reliability",
    "bm25_score",
    "vector_similarity",
    "metadata_bonus",
]


def load_feature_rows(paths: List[Path]) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            if reader.fieldnames is None:
                continue
            missing = [col for col in FEATURE_COLUMNS + ["is_relevant"] if col not in reader.fieldnames]
            if missing:
                raise ValueError(f"{path} is missing columns: {missing}")

            for record in reader:
                try:
                    label = float(record.get("is_relevant", 0) or 0)
                except ValueError:
                    continue
                feature_row = {
                    col: float(record.get(col, 0) or 0.0)
                    for col in FEATURE_COLUMNS
                }
                feature_row["label"] = 1.0 if label >= 0.5 else 0.0
                rows.append(feature_row)
    return rows


def train_weights(
    rows: List[Dict[str, float]],
    epochs: int = 400,
    learning_rate: float = 0.2,
    l2: float = 0.01,
) -> Dict[str, float]:
    if not rows:
        raise ValueError("No feature rows loaded")

    weights = {col: 0.1 for col in FEATURE_COLUMNS}
    bias = 0.0
    n = len(rows)

    for _ in range(epochs):
        grad = {col: 0.0 for col in FEATURE_COLUMNS}
        grad_bias = 0.0

        for row in rows:
            z = bias
            for col in FEATURE_COLUMNS:
                z += weights[col] * row[col]
            pred = 1.0 / (1.0 + math.exp(-z))
            error = pred - row["label"]
            grad_bias += error
            for col in FEATURE_COLUMNS:
                grad[col] += error * row[col] + (l2 * weights[col])

        bias -= learning_rate * (grad_bias / n)
        for col in FEATURE_COLUMNS:
            weights[col] -= learning_rate * (grad[col] / n)

    weights["bias"] = bias
    return weights


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    # Drop bias for config output, clamp to >= 0 and normalize to sum 1.
    positive = {
        col: max(0.0, weights.get(col, 0.0))
        for col in FEATURE_COLUMNS
    }
    total = sum(positive.values())
    if total <= 0:
        total = len(FEATURE_COLUMNS)
        positive = {col: 1.0 for col in FEATURE_COLUMNS}

    normalized = {col: positive[col] / total for col in FEATURE_COLUMNS}
    return normalized


def update_config_file(config_path: Path, normalized: Dict[str, float]) -> None:
    data = {}
    if config_path.exists():
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    data.setdefault("reranking_weights", {})
    for key, value in normalized.items():
        data["reranking_weights"][key] = round(value, 6)

    config_path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train reranking weights from feature CSVs")
    parser.add_argument("--features", nargs="+", required=True, help="CSV files produced by scripts.mcp_replay --export-features")
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.2)
    parser.add_argument("--l2", type=float, default=0.01, help="L2 regularization factor")
    parser.add_argument("--config", help="Optional config.yaml to update in-place")
    args = parser.parse_args()

    feature_rows = load_feature_rows([Path(p) for p in args.features])
    raw_weights = train_weights(
        feature_rows,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
    )
    normalized = normalize_weights(raw_weights)

    print("Trained reranking weights:")
    for key in FEATURE_COLUMNS:
        print(f"- {key}: {normalized[key]:.4f}")

    if args.config:
        update_config_file(Path(args.config), normalized)
        print(f"Updated reranking_weights in {args.config}")


if __name__ == "__main__":
    main()
