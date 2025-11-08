#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cross-encoder style reranker scaffold.

Uses the existing ModelRouter to score query/result pairs via an LLM prompt.
Designed as an interim solution until a dedicated cross-encoder model is
available (e.g., BGE). Keeps the contract simple: pass in candidates,
receive a re-ordered list with `cross_score`.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import logging

from src.models import ModelRouter

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """LLM-backed reranker that assigns a 0-1 relevance score per candidate."""

    def __init__(
        self,
        model_router: ModelRouter,
        max_candidates: int = 5,
        enabled: bool = True
    ):
        self.model_router = model_router
        self.max_candidates = max_candidates
        self.enabled = enabled

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not self.enabled or not candidates or not query:
            return candidates

        top_slice = candidates[: self.max_candidates]
        rescored: List[Dict[str, Any]] = []

        for entry in top_slice:
            score = self._score_pair(query, entry.get('content', ''))
            enriched = entry.copy()
            enriched['cross_score'] = score
            rescored.append(enriched)

        rescored.sort(key=lambda item: item.get('cross_score', 0.0), reverse=True)

        return rescored + candidates[self.max_candidates :]

    def _score_pair(self, query: str, candidate_text: str) -> float:
        if not candidate_text:
            return 0.0

        prompt = (
            "You are a reranker that scores how well a retrieved passage answers a query.\n"
            "Return only a floating-point number between 0.0 (irrelevant) and 1.0 (perfect match).\n"
            f"Query:\n{query}\n\nCandidate Passage:\n{candidate_text[:2000]}\n\n"
            "Score (0.0-1.0):"
        )

        try:
            raw = self.model_router.route(
                task_type='short_summary',
                prompt=prompt,
                max_tokens=20,
                temperature=0.0
            )
            score = float(str(raw).strip().split()[0])
            if score < 0.0 or score > 1.5:
                raise ValueError("score out of range")
            return max(0.0, min(1.0, score))
        except Exception as exc:  # pragma: no cover - LLM/CLI failures
            logger.warning(f"Cross-encoder scoring failed: {exc}")
            return 0.0
