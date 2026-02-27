#!/usr/bin/env python3
"""External Brain Runtime — Playbook API (Composer layer).

LLM が Playbook にアクセスする際、自動で referenced ログを記録し、
学習ループのデータ基盤を仕組みで保証する。

Usage:
    brain search "tailscale remote access" --domain openclaw
    brain get "Playbooks/Decision_OpenClaw_Tailscale_Remote_Access.md"
    brain record "Playbooks/..." used "判断に使用" --result success
    brain list --domain openclaw --sort confidence
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

JST = timezone(timedelta(hours=9))

DEFAULT_VAULT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Frontmatter parser (stdlib only, flat key-value)
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter delimited by '---'.

    Returns (metadata_dict, body_text). Handles flat key-value pairs
    and simple inline lists like ``tags: [a, b, c]``.
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta: dict = {}
    for line in parts[1].strip().splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        # inline list: [a, b, c]
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
            meta[key] = [i for i in items if i]
        else:
            # try numeric
            try:
                meta[key] = float(value) if "." in value else int(value)
            except ValueError:
                meta[key] = value

    body = parts[2].lstrip("\n")
    return meta, body


def _serialize_frontmatter(meta: dict) -> str:
    """Serialize a metadata dict back to YAML-like frontmatter string."""
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, list):
            inner = ", ".join(str(v) for v in value)
            lines.append(f"{key}: [{inner}]")
        elif isinstance(value, float):
            lines.append(f"{key}: {value:.4f}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---\n")
    return "\n".join(lines)


def _update_frontmatter(abs_path: Path, key: str, value) -> None:
    """Update a single frontmatter key, preserving the rest (with flock)."""
    fd = os.open(str(abs_path), os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        raw = os.read(fd, os.path.getsize(str(abs_path)))
        text = raw.decode("utf-8")
        meta, body = parse_frontmatter(text)
        new_meta = {**meta, key: value}
        new_text = _serialize_frontmatter(new_meta) + body
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, new_text.encode("utf-8"))
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


# ---------------------------------------------------------------------------
# Event logging (JSONL + flock)
# ---------------------------------------------------------------------------

def _log_event(vault: Path, event: dict) -> None:
    """Append an event to logs/events.jsonl with file locking."""
    log_dir = vault / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "events.jsonl"

    line = json.dumps(event, ensure_ascii=False) + "\n"

    fd = os.open(str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.write(fd, line.encode("utf-8"))
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# PlaybookAPI
# ---------------------------------------------------------------------------

class PlaybookAPI:
    """Core API for searching, reading, and logging Playbook usage."""

    # ---- confidence time decay (Feature 2) ----
    DECAY_THRESHOLD_DAYS = 90    # days without reference before decay starts
    DECAY_RATE_PER_MONTH = 0.05  # confidence reduction per month past threshold
    MIN_CONFIDENCE_FLOOR = 0.1   # decay never goes below this

    def __init__(self, vault: Path, session_id: Optional[str] = None):
        self.vault = Path(vault)
        self.playbooks_dir = self.vault / "Playbooks"
        self.session_id = (
            session_id
            or os.environ.get("BRAIN_SESSION_ID")
            or uuid.uuid4().hex[:12]
        )

    # ---- helpers ----

    MAX_TITLE_LENGTH = 200

    def _sanitize_path(self, rel_path: str) -> Path:
        """Validate and resolve a relative path, preventing traversal outside vault."""
        if ".." in rel_path:
            raise ValueError(f"Path must not contain '..': {rel_path}")
        abs_path = (self.vault / rel_path).resolve()
        if not str(abs_path).startswith(str(self.vault.resolve())):
            raise ValueError(f"Path escapes vault: {rel_path}")
        return abs_path

    def _load_playbook(self, rel_path: str) -> tuple[dict, str, Path]:
        """Load a playbook by relative path. Returns (meta, body, abs_path)."""
        abs_path = self._sanitize_path(rel_path)
        if not abs_path.is_file():
            raise FileNotFoundError(f"Playbook not found: {rel_path}")
        text = abs_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        return meta, body, abs_path

    def _all_playbooks(self) -> list[tuple[str, dict, str]]:
        """Yield (rel_path, meta, body) for every .md in Playbooks/."""
        if not self.playbooks_dir.is_dir():
            return []
        results = []
        for md in sorted(self.playbooks_dir.glob("**/*.md")):
            rel = str(md.relative_to(self.vault))
            text = md.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(text)
            results.append((rel, meta, body))
        return results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lowercase tokenization for search scoring."""
        return re.findall(r"[a-z0-9\u3040-\u9fff]+", text.lower())

    @staticmethod
    def _score(query_tokens: list[str], target_text: str) -> float:
        """Simple term-frequency scoring."""
        target_lower = target_text.lower()
        score = 0.0
        for token in query_tokens:
            score += target_lower.count(token)
        return score

    # ---- confidence update (H1) ----

    CONFIDENCE_ALPHA = 0.1  # EWA smoothing factor

    def update_confidence(self, rel_path: str) -> float:
        """Recalculate confidence from used/rejected events via EWA.

        Returns the new confidence value.
        """
        meta, _, abs_path = self._load_playbook(rel_path)
        current = meta.get("confidence", 0.5)
        if not isinstance(current, (int, float)):
            current = 0.5

        log_path = self.vault / "logs" / "events.jsonl"
        if not log_path.exists():
            return float(current)

        signals: list[float] = []
        for line in log_path.read_text(encoding="utf-8").strip().splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("playbook_id") != rel_path:
                continue
            if event.get("type") == "used":
                signals.append(1.0)
            elif event.get("type") == "rejected":
                signals.append(0.0)

        if not signals:
            return float(current)

        conf = float(current)
        for signal in signals:
            conf = self.CONFIDENCE_ALPHA * signal + (1 - self.CONFIDENCE_ALPHA) * conf

        new_confidence = round(max(0.0, min(1.0, conf)), 4)

        _update_frontmatter(abs_path, "confidence", new_confidence)

        _log_event(self.vault, {
            "ts": _now_iso(),
            "type": "confidence_updated",
            "playbook_id": rel_path,
            "old_confidence": current,
            "new_confidence": new_confidence,
            "session_id": self.session_id,
        })

        return new_confidence

    # ---- confidence time decay ----

    def apply_time_decay(self, rel_path: str) -> float:
        """Apply time-based confidence decay. Returns (possibly updated) confidence."""
        meta, _, abs_path = self._load_playbook(rel_path)
        conf = meta.get("confidence", 0.5)
        if not isinstance(conf, (int, float)):
            return 0.5

        last_ref = meta.get("last_referenced", meta.get("created", ""))
        if not last_ref:
            return float(conf)

        try:
            last_dt = datetime.fromisoformat(str(last_ref))
        except (ValueError, TypeError):
            return float(conf)

        now = datetime.now(JST)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=JST)
        days_since = (now - last_dt).days
        if days_since <= self.DECAY_THRESHOLD_DAYS:
            return float(conf)

        months_over = (days_since - self.DECAY_THRESHOLD_DAYS) / 30
        decayed = max(self.MIN_CONFIDENCE_FLOOR, conf - self.DECAY_RATE_PER_MONTH * months_over)
        decayed = round(decayed, 4)

        if decayed != conf:
            _update_frontmatter(abs_path, "confidence", decayed)
            _log_event(self.vault, {
                "ts": _now_iso(),
                "type": "confidence_decayed",
                "playbook_id": rel_path,
                "old_confidence": conf,
                "new_confidence": decayed,
                "days_since_reference": days_since,
            })

        return decayed

    def _calculate_decay_value(self, meta: dict) -> float:
        """Calculate decayed confidence WITHOUT writing to disk (pure function)."""
        conf = meta.get("confidence", 0.5)
        if not isinstance(conf, (int, float)):
            return 0.5

        last_ref = meta.get("last_referenced", meta.get("created", ""))
        if not last_ref:
            return float(conf)

        try:
            last_dt = datetime.fromisoformat(str(last_ref))
        except (ValueError, TypeError):
            return float(conf)

        now = datetime.now(JST)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=JST)
        days_since = (now - last_dt).days
        if days_since <= self.DECAY_THRESHOLD_DAYS:
            return float(conf)

        months_over = (days_since - self.DECAY_THRESHOLD_DAYS) / 30
        decayed = max(self.MIN_CONFIDENCE_FLOOR, conf - self.DECAY_RATE_PER_MONTH * months_over)
        return round(decayed, 4)

    # ---- inbox suggestion (H7) ----

    def _suggest_inbox(self, query: str, domain: Optional[str] = None) -> Path:
        """Create an Inbox candidate when search returns zero results."""
        inbox_dir = self.vault / "Inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"Candidate_{ts}.md"
        filepath = inbox_dir / filename

        meta = {
            "type": "candidate",
            "query": query,
            "created": _now_iso(),
        }
        if domain:
            meta["domain"] = domain

        body = (
            f"# Knowledge Gap: {query}\n\n"
            f"検索で見つからなかった知識候補。\n"
            f"A knowledge candidate that was not found by search.\n"
        )

        content = _serialize_frontmatter(meta) + body
        filepath.write_text(content, encoding="utf-8")

        _log_event(self.vault, {
            "ts": _now_iso(),
            "type": "knowledge_gap",
            "query": query,
            "domain": domain or "",
            "inbox_file": str(filepath.relative_to(self.vault)),
            "session_id": self.session_id,
        })

        return filepath

    # ---- public API ----

    VALID_TYPES = ("decision-record", "troubleshooting", "checklist", "pattern", "runbook")
    VALID_DOMAINS = (
        "infra", "frontend", "dev-process", "security",
        "kaggle", "geo-audit", "openclaw",
    )

    def create(
        self,
        *,
        type: str,
        domain: str,
        title: str,
        body: str = "",
        tags: Optional[list[str]] = None,
        confidence: float = 0.5,
    ) -> dict:
        """Create a new Playbook file and log a 'created' event.

        Returns dict with playbook_id, meta, and abs_path.
        Raises FileExistsError if a playbook with the same filename exists.
        Raises ValueError for invalid type or domain.
        """
        if type not in self.VALID_TYPES:
            raise ValueError(f"Invalid type '{type}'. Must be one of: {self.VALID_TYPES}")
        if domain not in self.VALID_DOMAINS:
            raise ValueError(f"Invalid domain '{domain}'. Must be one of: {self.VALID_DOMAINS}")
        if not title or not title.strip():
            raise ValueError("Title must not be empty")
        if len(title) > self.MAX_TITLE_LENGTH:
            raise ValueError(f"Title too long ({len(title)} chars). Max: {self.MAX_TITLE_LENGTH}")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got: {confidence}")

        # Generate filename from type and title — strip path separators
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", title).strip("_")
        # Capitalize each segment: "decision-record" -> "Decision_Record"
        type_prefix = "_".join(w.capitalize() for w in type.split("-"))
        filename = f"{type_prefix}_{slug}.md"
        abs_path = self.playbooks_dir / filename
        rel_path = f"Playbooks/{filename}"

        if abs_path.exists():
            raise FileExistsError(f"Playbook already exists: {rel_path}")

        self.playbooks_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "type": type,
            "created": _now_iso(),
            "domain": domain,
            "confidence": confidence,
        }
        if tags:
            meta["tags"] = tags

        content = _serialize_frontmatter(meta) + body
        abs_path.write_text(content, encoding="utf-8")

        _log_event(self.vault, {
            "ts": _now_iso(),
            "type": "created",
            "playbook_id": rel_path,
            "domain": domain,
            "session_id": self.session_id,
        })

        return {
            "playbook_id": rel_path,
            "meta": meta,
            "abs_path": str(abs_path),
        }

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """Search playbooks by query string. Does NOT log (search ≠ usage)."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        results = []
        for rel_path, meta, body in self._all_playbooks():
            # domain filter
            if domain and meta.get("domain", "") != domain:
                continue

            full_text = f"{rel_path} {body}"
            tags = meta.get("tags", [])
            if isinstance(tags, list):
                full_text += " " + " ".join(tags)

            s = self._score(query_tokens, full_text)
            if s > 0:
                results.append({
                    "playbook_id": rel_path,
                    "score": s,
                    "domain": meta.get("domain", ""),
                    "confidence": self._calculate_decay_value(meta),
                    "title": body.split("\n", 1)[0].lstrip("# ").strip() if body else rel_path,
                })

        results.sort(key=lambda r: r["score"], reverse=True)
        top = results[:limit]

        if not top and query_tokens:
            self._suggest_inbox(query, domain)

        return top

    def get(self, rel_path: str, caller: str = "cli") -> dict:
        """Read a playbook and auto-log 'referenced' event."""
        meta, body, abs_path = self._load_playbook(rel_path)

        # Track last_referenced for confidence decay
        now_iso = _now_iso()
        _update_frontmatter(abs_path, "last_referenced", now_iso)
        updated_meta = {**meta, "last_referenced": now_iso}

        _log_event(self.vault, {
            "ts": now_iso,
            "type": "referenced",
            "playbook_id": rel_path,
            "caller": caller,
            "session_id": self.session_id,
        })

        return {
            "playbook_id": rel_path,
            "meta": updated_meta,
            "body": body,
        }

    def record(
        self,
        rel_path: str,
        action: str,
        context: str = "",
        result: str = "",
        related_playbooks: Optional[list[str]] = None,
    ) -> dict:
        """Record 'used' or 'rejected' for a playbook."""
        if action not in ("used", "rejected"):
            raise ValueError(f"action must be 'used' or 'rejected', got: {action}")

        # verify playbook exists
        self._load_playbook(rel_path)

        event = {
            "ts": _now_iso(),
            "type": action,
            "playbook_id": rel_path,
            "session_id": self.session_id,
        }
        if context:
            event["context"] = context
        if result:
            event["result"] = result
        if related_playbooks:
            event["related_playbooks"] = related_playbooks

        _log_event(self.vault, event)

        self.update_confidence(rel_path)

        return event

    def promote(
        self,
        inbox_path: str,
        *,
        type: str,
        domain: str,
        title: str,
        body: Optional[str] = None,
        tags: Optional[list[str]] = None,
        confidence: float = 0.5,
    ) -> dict:
        """Promote an Inbox candidate to a Playbook.

        Reads the Inbox candidate, creates a Playbook, and marks the
        candidate as promoted. If body is not provided, uses the
        candidate's body.
        """
        inbox_abs = self._sanitize_path(inbox_path)
        if not inbox_abs.is_file():
            raise FileNotFoundError(f"Inbox candidate not found: {inbox_path}")

        inbox_text = inbox_abs.read_text(encoding="utf-8")
        inbox_meta, inbox_body = parse_frontmatter(inbox_text)

        result = self.create(
            type=type,
            domain=domain,
            title=title,
            body=body if body is not None else inbox_body,
            tags=tags,
            confidence=confidence,
        )

        _update_frontmatter(inbox_abs, "status", "promoted")
        _update_frontmatter(inbox_abs, "promoted_to", result["playbook_id"])

        _log_event(self.vault, {
            "ts": _now_iso(),
            "type": "promoted",
            "inbox_file": inbox_path,
            "playbook_id": result["playbook_id"],
            "session_id": self.session_id,
        })

        return result

    def audit(
        self,
        domain: Optional[str] = None,
        min_count: int = 3,
    ) -> dict:
        """Audit brain coverage by domain and report readiness.

        Returns a dict with per-domain stats, inbox pending count,
        and overall health assessment.
        """
        all_pb = self._all_playbooks()

        # Per-domain stats
        domain_counts: dict[str, list[dict]] = {d: [] for d in self.VALID_DOMAINS}
        for rel_path, meta, body in all_pb:
            d = meta.get("domain", "")
            if d in domain_counts:
                conf = meta.get("confidence", 0)
                if not isinstance(conf, (int, float)):
                    conf = 0
                domain_counts[d].append({
                    "playbook_id": rel_path,
                    "confidence": conf,
                })

        domains_report = {}
        for d, playbooks in domain_counts.items():
            if domain and d != domain:
                continue
            count = len(playbooks)
            avg_conf = (
                round(sum(p["confidence"] for p in playbooks) / count, 2)
                if count > 0 else 0.0
            )
            domains_report[d] = {
                "count": count,
                "ready": count >= min_count,
                "avg_confidence": avg_conf,
                "min_required": min_count,
            }

        # Inbox pending (both Candidate_ and Learn_ prefixes)
        inbox_dir = self.vault / "Inbox"
        pending_candidates = []
        if inbox_dir.is_dir():
            for candidate in sorted(inbox_dir.glob("*.md")):
                text = candidate.read_text(encoding="utf-8")
                meta, _ = parse_frontmatter(text)
                if meta.get("status") in ("promoted", "resolved"):
                    continue
                pending_candidates.append({
                    "file": str(candidate.relative_to(self.vault)),
                    "query": meta.get("query", meta.get("title", "")),
                    "domain": meta.get("domain", ""),
                    "created": meta.get("created", ""),
                })

        # Stale playbook detection
        stale_playbooks = []
        now = datetime.now(JST)
        for rel_path, meta, body in all_pb:
            if domain and meta.get("domain", "") != domain:
                continue
            last_ref = meta.get("last_referenced", meta.get("created", ""))
            if not last_ref:
                continue
            try:
                last_dt = datetime.fromisoformat(str(last_ref))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=JST)
                days_since = (now - last_dt).days
                if days_since > self.DECAY_THRESHOLD_DAYS:
                    stale_playbooks.append({
                        "playbook_id": rel_path,
                        "days_since_reference": days_since,
                        "confidence": meta.get("confidence", 0),
                    })
            except (ValueError, TypeError):
                continue

        # Working memory count
        wm_dir = self.vault / "WorkingMemory"
        wm_count = len(list(wm_dir.glob("*.md"))) if wm_dir.is_dir() else 0

        # Overall health
        total_domains = len(domains_report)
        ready_domains = sum(1 for d in domains_report.values() if d["ready"])
        total_playbooks = sum(d["count"] for d in domains_report.values())

        return {
            "domains": domains_report,
            "inbox_pending": pending_candidates,
            "stale_playbooks": stale_playbooks,
            "summary": {
                "total_playbooks": total_playbooks,
                "total_domains": total_domains,
                "ready_domains": ready_domains,
                "health_pct": round(ready_domains / total_domains * 100) if total_domains else 0,
                "inbox_pending_count": len(pending_candidates),
                "stale_count": len(stale_playbooks),
                "working_memory_count": wm_count,
            },
        }

    def learn(
        self,
        *,
        title: str,
        body: str,
        domain: str = "",
        tags: Optional[list[str]] = None,
        source: str = "manual",
    ) -> dict:
        """Create a structured Inbox candidate for later review and promotion.

        Unlike _suggest_inbox (triggered by search miss), learn() creates
        richer candidates with explicit title, body, domain, and tags.
        Returns dict with inbox_file path and metadata.
        """
        if not title or not title.strip():
            raise ValueError("Title must not be empty")

        inbox_dir = self.vault / "Inbox"
        inbox_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S_%f")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", title)[:60].strip("_")
        filename = f"Learn_{ts}_{slug}.md"
        filepath = inbox_dir / filename
        rel_path = f"Inbox/{filename}"

        meta: dict = {
            "type": "learned",
            "status": "pending_review",
            "source": source,
            "created": _now_iso(),
            "title": title,
        }
        if domain:
            meta["domain"] = domain
        if tags:
            meta["tags"] = tags

        content = _serialize_frontmatter(meta) + body
        filepath.write_text(content, encoding="utf-8")

        _log_event(self.vault, {
            "ts": _now_iso(),
            "type": "learned",
            "inbox_file": rel_path,
            "title": title,
            "domain": domain,
            "source": source,
            "session_id": self.session_id,
        })

        return {
            "inbox_file": rel_path,
            "abs_path": str(filepath),
            "meta": meta,
        }

    def list_playbooks(
        self,
        domain: Optional[str] = None,
        sort_by: str = "confidence",
    ) -> list[dict]:
        """List all playbooks, optionally filtered by domain."""
        results = []
        for rel_path, meta, body in self._all_playbooks():
            if domain and meta.get("domain", "") != domain:
                continue
            results.append({
                "playbook_id": rel_path,
                "domain": meta.get("domain", ""),
                "confidence": meta.get("confidence", ""),
                "type": meta.get("type", ""),
                "tags": meta.get("tags", []),
                "title": body.split("\n", 1)[0].lstrip("# ").strip() if body else rel_path,
            })

        if sort_by == "confidence":
            results.sort(
                key=lambda r: (r["confidence"] if isinstance(r["confidence"], (int, float)) else 0),
                reverse=True,
            )
        else:
            results.sort(key=lambda r: r["playbook_id"])

        return results

    # ---- working memory (Feature 4) ----

    DEFAULT_TTL_DAYS = 7
    MAX_WM_ENTRIES = 500
    MAX_TTL_DAYS = 365
    MAX_KEY_LENGTH = 200

    def remember(self, key: str, body: str, ttl_days: int = DEFAULT_TTL_DAYS) -> dict:
        """Store a working memory entry."""
        if not key or not key.strip():
            raise ValueError("Memory key must not be empty")
        if ttl_days < 1 or ttl_days > self.MAX_TTL_DAYS:
            raise ValueError(f"ttl_days must be between 1 and {self.MAX_TTL_DAYS}")
        wm_dir = self.vault / "WorkingMemory"
        wm_dir.mkdir(parents=True, exist_ok=True)
        existing_count = len(list(wm_dir.glob("*.md")))
        safe_key = re.sub(r"[^a-zA-Z0-9_-]", "_", key)
        if not safe_key:
            raise ValueError("Memory key sanitizes to empty string")
        if len(safe_key) > self.MAX_KEY_LENGTH:
            raise ValueError(f"Memory key too long (max {self.MAX_KEY_LENGTH} chars after sanitization)")
        # Allow overwrite of existing key without counting against limit
        target = wm_dir / f"{safe_key}.md"
        if not target.exists() and existing_count >= self.MAX_WM_ENTRIES:
            raise RuntimeError(f"Working memory limit ({self.MAX_WM_ENTRIES}) reached")
        filepath = wm_dir / f"{safe_key}.md"
        meta = {
            "type": "working-memory",
            "key": key,
            "created": _now_iso(),
            "expires": (datetime.now(JST) + timedelta(days=ttl_days)).isoformat(),
            "ttl_days": ttl_days,
        }
        content = _serialize_frontmatter(meta) + body
        filepath.write_text(content, encoding="utf-8")
        _log_event(self.vault, {
            "ts": _now_iso(),
            "type": "remembered",
            "key": key,
            "session_id": self.session_id,
        })
        return {"key": key, "path": str(filepath), "expires": meta["expires"]}

    def recall(self, key: str) -> dict:
        """Retrieve a working memory entry."""
        filepath = self._wm_path(key)
        if not filepath.is_file():
            raise FileNotFoundError(f"Working memory key not found: {key}")
        text = filepath.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        expires = meta.get("expires", "")
        if expires and datetime.fromisoformat(str(expires)) < datetime.now(JST):
            filepath.unlink()
            raise FileNotFoundError(f"Working memory expired: {key}")
        return {"key": key, "meta": meta, "body": body}

    def forget(self, key: str) -> bool:
        """Remove a working memory entry."""
        filepath = self._wm_path(key)
        if filepath.is_file():
            filepath.unlink()
            _log_event(self.vault, {
                "ts": _now_iso(),
                "type": "forgotten",
                "key": key,
                "session_id": self.session_id,
            })
            return True
        return False

    def context(self) -> list[dict]:
        """List all active working memory entries, auto-purging expired ones."""
        wm_dir = self.vault / "WorkingMemory"
        if not wm_dir.is_dir():
            return []
        results = []
        now = datetime.now(JST)
        for md in sorted(wm_dir.glob("*.md")):
            text = md.read_text(encoding="utf-8")
            meta, body = parse_frontmatter(text)
            expires = meta.get("expires", "")
            if expires:
                try:
                    if datetime.fromisoformat(str(expires)) < now:
                        md.unlink()  # auto-purge
                        continue
                except (ValueError, TypeError):
                    pass
            results.append({
                "key": meta.get("key", md.stem),
                "expires": expires,
                "preview": body[:100],
            })
        return results

    def _wm_path(self, key: str) -> Path:
        safe_key = re.sub(r"[^a-zA-Z0-9_-]", "_", key)
        return self.vault / "WorkingMemory" / f"{safe_key}.md"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="brain",
        description="External Brain Runtime — Playbook API",
    )
    parser.add_argument(
        "--vault", type=Path, default=DEFAULT_VAULT,
        help="Path to Obsidian vault (default: auto-detect)",
    )
    parser.add_argument(
        "--session-id", default=None,
        help="Session ID for event correlation",
    )

    sub = parser.add_subparsers(dest="command")

    # search
    p_search = sub.add_parser("search", help="Search playbooks")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--domain", default=None)
    p_search.add_argument("--limit", type=int, default=5)

    # get
    p_get = sub.add_parser("get", help="Read a playbook (auto-logs referenced)")
    p_get.add_argument("path", help="Relative path to playbook")
    p_get.add_argument("--caller", default="cli")

    # record
    p_record = sub.add_parser("record", help="Record used/rejected")
    p_record.add_argument("path", help="Relative path to playbook")
    p_record.add_argument("action", choices=["used", "rejected"])
    p_record.add_argument("context", nargs="?", default="")
    p_record.add_argument("--result", default="")
    p_record.add_argument("--related", nargs="*", default=None)

    # create
    p_create = sub.add_parser("create", help="Create a new playbook")
    p_create.add_argument("--type", required=True,
                          choices=list(PlaybookAPI.VALID_TYPES),
                          help="Playbook type")
    p_create.add_argument("--domain", required=True,
                          choices=list(PlaybookAPI.VALID_DOMAINS),
                          help="Knowledge domain")
    p_create.add_argument("--title", required=True, help="Playbook title")
    p_create.add_argument("--tags", default="", help="Comma-separated tags")
    p_create.add_argument("--confidence", type=float, default=0.5,
                          help="Initial confidence (0.0-1.0, default 0.5)")
    p_create.add_argument("--body", default="", help="Playbook body text")
    p_create.add_argument("--stdin", action="store_true",
                          help="Read body from stdin")

    # promote
    p_promote = sub.add_parser("promote", help="Promote Inbox candidate to Playbook")
    p_promote.add_argument("inbox_path", help="Relative path to Inbox candidate")
    p_promote.add_argument("--type", required=True,
                           choices=list(PlaybookAPI.VALID_TYPES))
    p_promote.add_argument("--domain", required=True,
                           choices=list(PlaybookAPI.VALID_DOMAINS))
    p_promote.add_argument("--title", required=True)
    p_promote.add_argument("--tags", default="")
    p_promote.add_argument("--confidence", type=float, default=0.5)
    p_promote.add_argument("--body", default=None,
                           help="Override body (default: use candidate body)")

    # audit
    p_audit = sub.add_parser("audit", help="Audit brain coverage by domain")
    p_audit.add_argument("--domain", default=None)
    p_audit.add_argument("--min-count", type=int, default=3,
                         help="Minimum playbooks per domain to be 'ready'")

    # learn
    p_learn = sub.add_parser("learn", help="Create a structured Inbox candidate")
    p_learn.add_argument("--title", required=True, help="Title of the learning")
    p_learn.add_argument("--domain", default="",
                         help="Knowledge domain (optional)")
    p_learn.add_argument("--tags", default="", help="Comma-separated tags")
    p_learn.add_argument("--source", default="manual",
                         help="Source: manual, auto, session (default: manual)")
    p_learn.add_argument("--body", default="", help="Body text")
    p_learn.add_argument("--stdin", action="store_true",
                         help="Read body from stdin")

    # list
    p_list = sub.add_parser("list", help="List all playbooks")
    p_list.add_argument("--domain", default=None)
    p_list.add_argument("--sort", default="confidence", choices=["confidence", "name"])

    # remember (working memory)
    p_remember = sub.add_parser("remember", help="Store a working memory entry")
    p_remember.add_argument("key", help="Memory key")
    p_remember.add_argument("--body", required=True, help="Memory content")
    p_remember.add_argument("--ttl", type=int, default=7, help="TTL in days (default: 7)")

    # recall (working memory)
    p_recall = sub.add_parser("recall", help="Retrieve a working memory entry")
    p_recall.add_argument("key", help="Memory key")

    # forget (working memory)
    p_forget = sub.add_parser("forget", help="Remove a working memory entry")
    p_forget.add_argument("key", help="Memory key")

    # context (working memory)
    sub.add_parser("context", help="List all active working memory entries")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    api = PlaybookAPI(vault=args.vault, session_id=args.session_id)

    if args.command == "search":
        results = api.search(args.query, domain=args.domain, limit=args.limit)
        if not results:
            print("No matching playbooks found.")
            return 0
        for r in results:
            print(f"  [{r['score']:.1f}] {r['playbook_id']}")
            print(f"        {r['title']}")
        return 0

    if args.command == "get":
        result = api.get(args.path, caller=args.caller)
        print(f"--- {result['playbook_id']} ---")
        if result["meta"]:
            for k, v in result["meta"].items():
                print(f"  {k}: {v}")
            print()
        print(result["body"])
        return 0

    if args.command == "record":
        event = api.record(
            args.path,
            args.action,
            context=args.context,
            result=args.result,
            related_playbooks=args.related,
        )
        print(f"Recorded: {event['type']} → {event['playbook_id']}")
        return 0

    if args.command == "create":
        body = args.body
        if args.stdin:
            body = sys.stdin.read()
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
        result = api.create(
            type=args.type,
            domain=args.domain,
            title=args.title,
            body=body,
            tags=tags,
            confidence=args.confidence,
        )
        print(f"Created: {result['playbook_id']}")
        return 0

    if args.command == "promote":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
        result = api.promote(
            args.inbox_path,
            type=args.type,
            domain=args.domain,
            title=args.title,
            body=args.body,
            tags=tags,
            confidence=args.confidence,
        )
        print(f"Promoted: {args.inbox_path} → {result['playbook_id']}")
        return 0

    if args.command == "audit":
        report = api.audit(domain=args.domain, min_count=args.min_count)
        summary = report["summary"]
        print(f"Brain Health: {summary['health_pct']}% "
              f"({summary['ready_domains']}/{summary['total_domains']} domains ready, "
              f"{summary['total_playbooks']} playbooks)")
        print()
        for d, stats in report["domains"].items():
            status = "READY" if stats["ready"] else "NOT READY"
            bar = "#" * stats["count"] + "." * max(0, stats["min_required"] - stats["count"])
            print(f"  {d:15s} [{bar}] {stats['count']:2d} playbooks "
                  f"(avg conf: {stats['avg_confidence']:.2f}) — {status}")
        if report["inbox_pending"]:
            print(f"\nInbox pending: {len(report['inbox_pending'])} candidates")
            for c in report["inbox_pending"][:5]:
                print(f"  - {c['file']}  query=\"{c['query']}\"  domain={c['domain']}")
            if len(report["inbox_pending"]) > 5:
                print(f"  ... and {len(report['inbox_pending']) - 5} more")
        if report.get("stale_playbooks"):
            print(f"\nStale playbooks (>{PlaybookAPI.DECAY_THRESHOLD_DAYS}d): "
                  f"{len(report['stale_playbooks'])}")
            for s in report["stale_playbooks"][:5]:
                print(f"  - {s['playbook_id']}  "
                      f"({s['days_since_reference']}d, conf={s['confidence']})")
        if summary.get("working_memory_count", 0) > 0:
            print(f"\nWorking memory entries: {summary['working_memory_count']}")
        return 0

    if args.command == "learn":
        body = args.body
        if args.stdin:
            body = sys.stdin.read()
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
        result = api.learn(
            title=args.title,
            body=body,
            domain=args.domain,
            tags=tags,
            source=args.source,
        )
        print(f"Learned: {result['inbox_file']}")
        return 0

    if args.command == "list":
        results = api.list_playbooks(domain=args.domain, sort_by=args.sort)
        if not results:
            print("No playbooks found.")
            return 0
        for r in results:
            conf = f"[{r['confidence']}]" if r["confidence"] != "" else "[—]"
            print(f"  {conf} {r['playbook_id']}")
            print(f"        {r['title']}  ({r['domain']})")
        return 0

    if args.command == "remember":
        result = api.remember(args.key, args.body, ttl_days=args.ttl)
        print(f"Remembered: {result['key']} (expires: {result['expires']})")
        return 0

    if args.command == "recall":
        try:
            result = api.recall(args.key)
            print(f"--- {result['key']} ---")
            for k, v in result["meta"].items():
                print(f"  {k}: {v}")
            print()
            print(result["body"])
        except FileNotFoundError as e:
            print(f"Not found: {e}")
            return 1
        return 0

    if args.command == "forget":
        if api.forget(args.key):
            print(f"Forgotten: {args.key}")
        else:
            print(f"Not found: {args.key}")
            return 1
        return 0

    if args.command == "context":
        entries = api.context()
        if not entries:
            print("No active working memory entries.")
            return 0
        print(f"Working memory ({len(entries)} entries):\n")
        for e in entries:
            print(f"  [{e['key']}] expires: {e['expires']}")
            if e["preview"]:
                print(f"    {e['preview']}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except (FileNotFoundError, FileExistsError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"System error: {e}", file=sys.stderr)
        sys.exit(1)
