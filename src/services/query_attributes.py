#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Query Attribute Extraction

Lightweight heuristics inspired by QAM (Query Attribute Modeling) to infer
topic/type/project hints from a free-form query. These hints can be used to
prefilter hybrid search candidates and to boost metadata alignment scores
before the heavier reranking stages kick in.

Phase target: feed SearchService with richer context without blocking on a
full LLM integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Set, Dict
import re


@dataclass
class QueryAttributes:
    """Structured hints parsed from the user query."""

    topic: Optional[str] = None
    doc_type: Optional[str] = None
    project_name: Optional[str] = None
    severity: Optional[str] = None
    keywords: Set[str] = field(default_factory=set)

    def has_hints(self) -> bool:
        return any([self.topic, self.doc_type, self.project_name, self.severity])


class QueryAttributeExtractor:
    """Rule-based attribute extractor (placeholder for future LLM/QAM hook)."""

    PROJECT_KEYWORDS: Dict[str, str] = {
        "appbrain": "AppBrain",
        "bugfixer": "BugFixer",
        "insightops": "InsightOps",
        "phase sync": "PhaseSync",
        "phasesync": "PhaseSync",
    }

    TOPIC_KEYWORDS: Dict[str, str] = {
        "timeline": "timeline",
        "release": "release",
        "rerank": "rerank",
        "chunker": "chunker",
        "dashboard": "dashboard",
        "governance": "governance",
        "policy": "policy",
        "obsidian": "obsidian",
        "retention": "policy",
        "change feed": "ingestion",
        "consolidation": "consolidation",
    }

    DOC_TYPE_KEYWORDS: Dict[str, str] = {
        "checklist": "checklist",
        "runbook": "checklist",
        "experiment": "experiment",
        "postmortem": "postmortem",
        "template": "template",
        "guide": "guide",
        "report": "report",
        "incident": "incident",
    }

    SEVERITY_KEYWORDS: Dict[str, str] = {
        "sev1": "high",
        "sev2": "medium",
        "sev3": "low",
        "critical": "high",
        "high priority": "high",
        "major": "medium",
    }

    INC_PATTERN = re.compile(r"(inc[-_ ]?\d+)", re.IGNORECASE)

    def extract(self, query: str) -> QueryAttributes:
        """Return structured hints derived from the free-form query."""
        attributes = QueryAttributes()
        normalized = query.lower()
        attributes.keywords = set(
            token for token in re.split(r"[^\w-]+", normalized) if token
        )

        attributes.topic = self._lookup(normalized, self.TOPIC_KEYWORDS)
        attributes.doc_type = self._lookup(normalized, self.DOC_TYPE_KEYWORDS)
        attributes.project_name = self._lookup(normalized, self.PROJECT_KEYWORDS)
        attributes.severity = self._lookup(normalized, self.SEVERITY_KEYWORDS)

        # Incident-style identifiers imply incident topic/type
        if self.INC_PATTERN.search(normalized):
            attributes.topic = attributes.topic or "incident"
            attributes.doc_type = attributes.doc_type or "incident"
            attributes.severity = attributes.severity or "high"

        return attributes

    @staticmethod
    def _lookup(text: str, table: Dict[str, str]) -> Optional[str]:
        for needle, value in table.items():
            if needle in text:
                return value
        return None

