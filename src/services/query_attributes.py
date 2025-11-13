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
from typing import Optional, Set, Dict, Any, TYPE_CHECKING
import json
import logging
import re
import time

if TYPE_CHECKING:  # pragma: no cover - typing helper
    from src.models import ModelRouter

logger = logging.getLogger(__name__)


@dataclass
class QueryAttributes:
    """Structured hints parsed from the user query."""

    topic: Optional[str] = None
    doc_type: Optional[str] = None
    project_name: Optional[str] = None
    severity: Optional[str] = None
    keywords: Set[str] = field(default_factory=set)
    confidence: Dict[str, float] = field(default_factory=dict)

    def has_hints(self) -> bool:
        return any([self.topic, self.doc_type, self.project_name, self.severity])

    def apply(self, key: str, value: Optional[str], confidence: float) -> None:
        """Set attribute value with an associated confidence score."""
        if not value:
            return
        setattr(self, key, value)
        if confidence > 0:
            self.confidence[key] = confidence


class QueryAttributeExtractor:
    """Hybrid heuristic + LLM attribute extractor inspired by QAM."""

    PROJECT_KEYWORDS: Dict[str, str] = {
        "appbrain": "AppBrain",
        "orchestrator": "AppBrain",
        "pilot": "AppBrain",
        "demo": "AppBrain",
        "bugfixer": "BugFixer",
        "再発防止": "BugFixer",
        "再デプロイ": "BugFixer",
        "insightops": "InsightOps",
        "guardrails": "InsightOps",
        "observability": "InsightOps",
        "phase sync": "PhaseSync",
        "phasesync": "PhaseSync",

        # Phase 3.1: Japanese Project Keywords
        "バグフィクサー": "BugFixer",
        "フェーズシンク": "PhaseSync",
    }

    TOPIC_KEYWORDS: Dict[str, str] = {
        # Existing
        "timeline": "timeline",
        "release": "release",
        "rerank": "rerank",
        "chunker": "chunker",
        "dashboard": "dashboard",
        "governance": "governance",
        "policy": "policy",
        "obsidian": "obsidian",
        "retention": "policy",
        "retention policy": "policy",
        "change feed": "ingestion",
        "consolidation": "consolidation",
        "doctor report": "health",
        "doctor": "health",
        "再発防止": "chunker",
        "再デプロイ": "chunker",

        # Phase 1.1: Release/Deployment
        "deployment": "deployment",
        "deploy": "deployment",
        "rollout": "deployment",
        "canary": "deployment",
        "blue-green": "deployment",
        "blue green": "deployment",
        "release notes": "release",
        "hotfix": "release",
        "patch": "release",
        "version": "release",

        # Phase 1.2: Incident/Monitoring
        "alert": "monitoring",
        "monitoring": "monitoring",
        "sla": "monitoring",
        "downtime": "incident",
        "outage": "incident",
        "degradation": "incident",
        "incident response": "incident",
        "root cause": "incident",
        "rca": "incident",

        # Phase 1.3: Audit/Compliance/Security
        "audit": "audit",
        "compliance": "compliance",
        "security": "security",
        "vulnerability": "security",
        "pen test": "security",
        "penetration": "security",

        # Phase 1.4: Development/Tech Debt
        "refactor": "development",
        "tech debt": "development",
        "technical debt": "development",
        "prototype": "development",
        "poc": "development",
        "proof of concept": "development",

        # Phase 2.1: Operations/Reliability
        "backup": "operations",
        "disaster recovery": "operations",
        "failover": "operations",
        "scaling": "operations",
        "capacity": "operations",
        "performance": "operations",
        "optimization": "optimization",

        # Phase 2.2: Data Management
        "data migration": "data",
        "etl": "data",
        "pipeline": "data",
        "streaming": "ingestion",
        "migration": "development",  # Generic migration (after "data migration")

        # Phase 3.1: Japanese Topic Keywords
        "タイムライン": "timeline",
        "リリース": "release",
        "デプロイ": "deployment",
        "障害": "incident",
        "監査": "audit",
        "開発": "development",

        # Phase 3.2: Spanish Topic Keywords
        "despliegue": "deployment",
        "lanzamiento": "release",
        "incidente": "incident",
        "incidentes": "incident",
        "auditoría": "audit",
    }

    DOC_TYPE_KEYWORDS: Dict[str, str] = {
        # Existing
        "checklist": "checklist",
        "runbook": "checklist",
        "experiment": "experiment",
        "postmortem": "postmortem",
        "template": "template",
        "guide": "guide",
        "report": "report",
        "doctor report": "report",
        "change log": "runbook",
        "retention policy": "policy",

        # Phase 1.1: Deployment/Release docs
        "deployment guide": "guide",
        "rollout plan": "checklist",
        "release notes": "changelog",
        "changelog": "changelog",

        # Phase 1.2: Incident docs
        "incident report": "incident",
        "rca": "postmortem",
        "root cause analysis": "postmortem",
        "incident log": "report",

        # Phase 1.3: Audit/Compliance docs
        "audit report": "report",
        "compliance checklist": "checklist",
        "security policy": "policy",

        # Phase 1.4: Development docs
        "design doc": "design",
        "architecture": "design",
        "rfc": "design",
        "proposal": "design",

        # Phase 3.1: Japanese DocType Keywords
        "手順書": "guide",
        "チェックリスト": "checklist",
        "報告書": "report",
        "テンプレート": "template",

        # Phase 3.2: Spanish DocType Keywords
        "lista de verificación": "checklist",
        "guía": "guide",
        "informe": "report",

        # Generic keywords (should be after more specific phrases)
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
    PROMPT_TEMPLATE = """You are an assistant that labels search queries for a knowledge base.
Return a compact JSON object with keys: topic, doc_type, project_name, severity, and confidence.
confidence must itself be a JSON object mapping attribute names to a float 0-1.
If an attribute is unknown, use null.

Query:
{query}
JSON:"""

    def __init__(
        self,
        model_router: Optional["ModelRouter"] = None,
        min_llm_confidence: float = 0.4,
        llm_enabled: bool = True
    ) -> None:
        self.model_router = model_router
        self.min_llm_confidence = min_llm_confidence
        self.llm_enabled = llm_enabled

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

        if self._should_call_llm(attributes):
            self._enrich_with_llm(query, attributes)
        return attributes

    def _should_call_llm(self, attributes: QueryAttributes) -> bool:
        if not self.llm_enabled or not self._can_use_llm():
            return False

        # Skip LLM if primary hints (topic + project or topic + doc_type) already揃う
        topic_ready = bool(attributes.topic)
        doc_ready = bool(attributes.doc_type)
        project_ready = bool(attributes.project_name)

        if project_ready and topic_ready:
            return False

        if topic_ready and doc_ready and project_ready:
            return False

        # Call LLM when project名が不明 or topic/doc_type が欠けている
        return (not project_ready) or (not topic_ready and not doc_ready)

    def _enrich_with_llm(self, query: str, attributes: QueryAttributes) -> None:
        if not query or not self._can_use_llm():
            return
        try:
            start = time.perf_counter()
            payload = self._call_llm(query)
            duration = (time.perf_counter() - start) * 1000
            logger.debug("LLM attribute extraction completed in %.0f ms", duration)
        except Exception as exc:  # pragma: no cover - defensive log
            logger.debug("LLM attribute extraction failed: %s", exc)
            return

        if not isinstance(payload, dict):
            return

        confidence = payload.get("confidence", {}) if isinstance(payload.get("confidence"), dict) else {}
        for field in ("topic", "doc_type", "project_name", "severity"):
            value = payload.get(field)
            if not value:
                continue

            current = getattr(attributes, field)
            field_conf = float(confidence.get(field, 0.0))
            if current and field_conf < self.min_llm_confidence:
                # Keep heuristic value unless LLM is confident.
                continue

            attributes.apply(field, value.strip(), field_conf)

    def _call_llm(self, query: str) -> Dict[str, Any]:
        prompt = self.PROMPT_TEMPLATE.format(query=query.strip())
        raw = self.model_router.route(
            task_type='short_summary',
            prompt=prompt,
            max_tokens=200,
            temperature=0.0
        )
        if raw is None:
            raise ValueError("LLM returned no content")

        return self._safe_json_parse(raw)

    def _can_use_llm(self) -> bool:
        if not self.model_router:
            return False
        route_fn = getattr(self.model_router, "route", None)
        return callable(route_fn)

    def _safe_json_parse(self, raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        text = str(raw).strip()
        if not text:
            raise ValueError("Empty LLM response")

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Some models wrap JSON in prose; extract substring between braces.
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1:
                raise
            data = json.loads(text[start:end + 1])
        return data

    @staticmethod
    def _lookup(text: str, table: Dict[str, str]) -> Optional[str]:
        for needle, value in table.items():
            if needle in text:
                return value
        return None
