"""Tests for playbook_api.py"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Allow import from parent
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playbook_api import (
    PlaybookAPI,
    parse_frontmatter,
    _serialize_frontmatter,
    _update_frontmatter,
    _log_event,
    _now_iso,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PLAYBOOK = """\
---
type: decision-record
created: 2026-02-24
domain: openclaw
confidence: 0.9
tags: [openclaw, tailscale, remote-access]
---

# Decision: OpenClaw Remote Access

## Decision
Use local connection only.

## Context
Tailscale Serve does not work with OpenClaw v2026.1.30.
"""

SAMPLE_PLAYBOOK_2 = """\
---
type: decision-record
created: 2026-02-20
domain: kaggle
confidence: 0.7
tags: [kaggle, akkadian, nlp]
---

# Decision: Akkadian Translation Strategy

## Decision
Use TR-TRY with Sentences_Oare direct concatenation.
"""


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Create a temporary vault with sample playbooks."""
    playbooks = tmp_path / "Playbooks"
    playbooks.mkdir()
    (playbooks / "OpenClaw_Tailscale.md").write_text(SAMPLE_PLAYBOOK, encoding="utf-8")
    (playbooks / "Akkadian_Strategy.md").write_text(SAMPLE_PLAYBOOK_2, encoding="utf-8")
    (tmp_path / "logs").mkdir()
    return tmp_path


@pytest.fixture
def api(vault: Path) -> PlaybookAPI:
    return PlaybookAPI(vault=vault, session_id="test-session-001")


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:

    def test_basic_parsing(self):
        meta, body = parse_frontmatter(SAMPLE_PLAYBOOK)
        assert meta["type"] == "decision-record"
        assert meta["created"] == "2026-02-24"
        assert meta["domain"] == "openclaw"
        assert meta["confidence"] == 0.9
        assert meta["tags"] == ["openclaw", "tailscale", "remote-access"]
        assert body.startswith("# Decision: OpenClaw Remote Access")

    def test_no_frontmatter(self):
        meta, body = parse_frontmatter("# Just a heading\n\nSome text.")
        assert meta == {}
        assert body == "# Just a heading\n\nSome text."

    def test_incomplete_frontmatter(self):
        meta, body = parse_frontmatter("---\nkey: value\nno closing delimiter")
        assert meta == {}

    def test_empty_string(self):
        meta, body = parse_frontmatter("")
        assert meta == {}
        assert body == ""

    def test_integer_value(self):
        meta, _ = parse_frontmatter("---\ncount: 42\n---\nbody")
        assert meta["count"] == 42
        assert isinstance(meta["count"], int)

    def test_float_value(self):
        meta, _ = parse_frontmatter("---\nscore: 3.14\n---\nbody")
        assert meta["score"] == 3.14
        assert isinstance(meta["score"], float)

    def test_inline_list_with_quotes(self):
        meta, _ = parse_frontmatter("---\ntags: ['foo', \"bar\", baz]\n---\nbody")
        assert meta["tags"] == ["foo", "bar", "baz"]


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

class TestSearch:

    def test_finds_matching_playbook(self, api: PlaybookAPI):
        results = api.search("tailscale")
        assert len(results) == 1
        assert "OpenClaw_Tailscale" in results[0]["playbook_id"]
        assert results[0]["score"] > 0

    def test_domain_filter(self, api: PlaybookAPI):
        results = api.search("decision", domain="kaggle")
        assert all(r["domain"] == "kaggle" for r in results)

    def test_no_match(self, api: PlaybookAPI):
        results = api.search("xyznonexistent")
        assert results == []

    def test_limit(self, api: PlaybookAPI):
        results = api.search("decision", limit=1)
        assert len(results) <= 1

    def test_empty_query(self, api: PlaybookAPI):
        results = api.search("")
        assert results == []

    def test_search_does_not_log(self, api: PlaybookAPI, vault: Path):
        # Ensure last_referenced is recent so apply_time_decay won't fire
        api.get("Playbooks/OpenClaw_Tailscale.md")
        log_path = vault / "logs" / "events.jsonl"
        before = log_path.read_text() if log_path.exists() else ""
        api.search("tailscale")
        after = log_path.read_text() if log_path.exists() else ""
        assert before == after

    def test_scores_sorted_descending(self, api: PlaybookAPI):
        results = api.search("decision")
        if len(results) >= 2:
            assert results[0]["score"] >= results[1]["score"]


# ---------------------------------------------------------------------------
# get (auto-log referenced)
# ---------------------------------------------------------------------------

class TestGet:

    def test_returns_content(self, api: PlaybookAPI):
        result = api.get("Playbooks/OpenClaw_Tailscale.md")
        assert result["playbook_id"] == "Playbooks/OpenClaw_Tailscale.md"
        assert result["meta"]["domain"] == "openclaw"
        assert "local connection" in result["body"]

    def test_auto_logs_referenced(self, api: PlaybookAPI, vault: Path):
        api.get("Playbooks/OpenClaw_Tailscale.md")

        log_path = vault / "logs" / "events.jsonl"
        lines = log_path.read_text().strip().splitlines()
        event = json.loads(lines[-1])
        assert event["type"] == "referenced"
        assert event["playbook_id"] == "Playbooks/OpenClaw_Tailscale.md"
        assert event["caller"] == "cli"
        assert event["session_id"] == "test-session-001"

    def test_not_found(self, api: PlaybookAPI):
        with pytest.raises(FileNotFoundError):
            api.get("Playbooks/NonExistent.md")

    def test_custom_caller(self, api: PlaybookAPI, vault: Path):
        api.get("Playbooks/OpenClaw_Tailscale.md", caller="claude-code")

        log_path = vault / "logs" / "events.jsonl"
        lines = log_path.read_text().strip().splitlines()
        event = json.loads(lines[-1])
        assert event["caller"] == "claude-code"


# ---------------------------------------------------------------------------
# record (used / rejected)
# ---------------------------------------------------------------------------

class TestRecord:

    def test_record_used(self, api: PlaybookAPI, vault: Path):
        event = api.record(
            "Playbooks/OpenClaw_Tailscale.md",
            "used",
            context="判断に使用",
            result="success",
        )
        assert event["type"] == "used"

        log_path = vault / "logs" / "events.jsonl"
        lines = log_path.read_text().strip().splitlines()
        used_events = [json.loads(l) for l in lines if '"type": "used"' in l]
        assert len(used_events) >= 1
        logged = used_events[-1]
        assert logged["type"] == "used"
        assert logged["context"] == "判断に使用"
        assert logged["result"] == "success"
        assert logged["session_id"] == "test-session-001"

    def test_record_rejected(self, api: PlaybookAPI, vault: Path):
        event = api.record(
            "Playbooks/OpenClaw_Tailscale.md",
            "rejected",
            context="状況が変わった",
        )
        assert event["type"] == "rejected"

    def test_record_with_related(self, api: PlaybookAPI, vault: Path):
        event = api.record(
            "Playbooks/OpenClaw_Tailscale.md",
            "used",
            related_playbooks=["Playbooks/Akkadian_Strategy.md"],
        )

        log_path = vault / "logs" / "events.jsonl"
        lines = log_path.read_text().strip().splitlines()
        used_events = [json.loads(l) for l in lines if '"type": "used"' in l]
        logged = used_events[-1]
        assert logged["related_playbooks"] == ["Playbooks/Akkadian_Strategy.md"]

    def test_record_invalid_action(self, api: PlaybookAPI):
        with pytest.raises(ValueError, match="must be 'used' or 'rejected'"):
            api.record("Playbooks/OpenClaw_Tailscale.md", "invalid")

    def test_record_nonexistent_playbook(self, api: PlaybookAPI):
        with pytest.raises(FileNotFoundError):
            api.record("Playbooks/NonExistent.md", "used")


# ---------------------------------------------------------------------------
# list_playbooks
# ---------------------------------------------------------------------------

class TestListPlaybooks:

    def test_lists_all(self, api: PlaybookAPI):
        results = api.list_playbooks()
        assert len(results) == 2

    def test_domain_filter(self, api: PlaybookAPI):
        results = api.list_playbooks(domain="openclaw")
        assert len(results) == 1
        assert results[0]["domain"] == "openclaw"

    def test_sort_by_confidence(self, api: PlaybookAPI):
        results = api.list_playbooks(sort_by="confidence")
        assert results[0]["confidence"] >= results[1]["confidence"]

    def test_sort_by_name(self, api: PlaybookAPI):
        results = api.list_playbooks(sort_by="name")
        assert results[0]["playbook_id"] <= results[1]["playbook_id"]


# ---------------------------------------------------------------------------
# _log_event (file locking)
# ---------------------------------------------------------------------------

class TestLogEvent:

    def test_creates_log_file(self, tmp_path: Path):
        vault = tmp_path
        _log_event(vault, {"type": "test", "ts": _now_iso()})

        log_path = vault / "logs" / "events.jsonl"
        assert log_path.exists()
        event = json.loads(log_path.read_text().strip())
        assert event["type"] == "test"

    def test_append_mode(self, tmp_path: Path):
        vault = tmp_path
        _log_event(vault, {"seq": 1})
        _log_event(vault, {"seq": 2})

        log_path = vault / "logs" / "events.jsonl"
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["seq"] == 1
        assert json.loads(lines[1])["seq"] == 2

    def test_unicode_content(self, tmp_path: Path):
        vault = tmp_path
        _log_event(vault, {"msg": "日本語テスト 🧠"})

        log_path = vault / "logs" / "events.jsonl"
        event = json.loads(log_path.read_text().strip())
        assert event["msg"] == "日本語テスト 🧠"


# ---------------------------------------------------------------------------
# CLI (main function)
# ---------------------------------------------------------------------------

class TestCLI:

    def test_no_command_returns_1(self):
        from playbook_api import main
        assert main([]) == 1

    def test_search_cli(self, vault: Path):
        from playbook_api import main
        ret = main(["--vault", str(vault), "search", "tailscale"])
        assert ret == 0

    def test_get_cli(self, vault: Path):
        from playbook_api import main
        ret = main(["--vault", str(vault), "get", "Playbooks/OpenClaw_Tailscale.md"])
        assert ret == 0

    def test_record_cli(self, vault: Path):
        from playbook_api import main
        ret = main([
            "--vault", str(vault),
            "record", "Playbooks/OpenClaw_Tailscale.md", "used", "テスト",
        ])
        assert ret == 0

    def test_list_cli(self, vault: Path):
        from playbook_api import main
        ret = main(["--vault", str(vault), "list"])
        assert ret == 0


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

class TestCreate:

    def test_create_basic(self, api: PlaybookAPI, vault: Path):
        result = api.create(
            type="troubleshooting",
            domain="infra",
            title="ECS External API Timeout",
            tags=["ecs", "timeout", "sg"],
            confidence=0.7,
            body="# ECS External API Timeout\n\n## Symptoms\n- TCP SYN 30s timeout\n\n## Fix\n- Add egress rule\n",
        )
        assert result["playbook_id"] == "Playbooks/Troubleshooting_ECS_External_API_Timeout.md"
        abs_path = Path(result["abs_path"])
        assert abs_path.exists()

        text = abs_path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        assert meta["type"] == "troubleshooting"
        assert meta["domain"] == "infra"
        assert meta["confidence"] == 0.7
        assert meta["tags"] == ["ecs", "timeout", "sg"]
        assert "TCP SYN" in body

    def test_create_logs_event(self, api: PlaybookAPI, vault: Path):
        api.create(
            type="pattern",
            domain="frontend",
            title="React Hook Pattern",
            body="# React Hook Pattern\n",
        )

        log_path = vault / "logs" / "events.jsonl"
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        created_events = [json.loads(l) for l in lines if '"created"' in l]
        assert len(created_events) >= 1
        event = created_events[-1]
        assert event["type"] == "created"
        assert "React_Hook_Pattern" in event["playbook_id"]
        assert event["session_id"] == "test-session-001"

    def test_create_duplicate_raises(self, api: PlaybookAPI, vault: Path):
        api.create(
            type="runbook",
            domain="infra",
            title="Deploy Steps",
            body="# Deploy Steps\n",
        )
        with pytest.raises(FileExistsError):
            api.create(
                type="runbook",
                domain="infra",
                title="Deploy Steps",
                body="# Deploy Steps\n",
            )

    def test_create_searchable(self, api: PlaybookAPI, vault: Path):
        api.create(
            type="troubleshooting",
            domain="infra",
            title="Redis Connection Failure",
            tags=["redis", "connection"],
            body="# Redis Connection Failure\n\nRedis TLS handshake timeout\n",
        )
        results = api.search("redis connection")
        assert len(results) >= 1
        assert any("Redis_Connection_Failure" in r["playbook_id"] for r in results)

    def test_create_empty_title_raises(self, api: PlaybookAPI):
        with pytest.raises(ValueError, match="must not be empty"):
            api.create(type="pattern", domain="infra", title="", body="test")

    def test_create_whitespace_title_raises(self, api: PlaybookAPI):
        with pytest.raises(ValueError, match="must not be empty"):
            api.create(type="pattern", domain="infra", title="   ", body="test")

    def test_create_long_title_raises(self, api: PlaybookAPI):
        with pytest.raises(ValueError, match="Title too long"):
            api.create(type="pattern", domain="infra", title="A" * 201, body="test")

    def test_create_confidence_out_of_range_raises(self, api: PlaybookAPI):
        with pytest.raises(ValueError, match="confidence must be between"):
            api.create(type="pattern", domain="infra", title="High Conf", confidence=1.5)
        with pytest.raises(ValueError, match="confidence must be between"):
            api.create(type="pattern", domain="infra", title="Neg Conf", confidence=-0.1)

    def test_create_path_separators_sanitized(self, api: PlaybookAPI, vault: Path):
        result = api.create(
            type="pattern", domain="infra",
            title="foo/bar\\baz", body="# Test\n",
        )
        # Path separators should be converted to underscores in slug
        assert "/" not in Path(result["abs_path"]).name
        assert "\\" not in Path(result["abs_path"]).name
        assert Path(result["abs_path"]).parent == vault / "Playbooks"


# ---------------------------------------------------------------------------
# Path sanitization
# ---------------------------------------------------------------------------

class TestPathSanitization:

    def test_dotdot_path_rejected(self, api: PlaybookAPI):
        with pytest.raises(ValueError, match="must not contain"):
            api.get("Playbooks/../secrets.md")

    def test_dotdot_record_rejected(self, api: PlaybookAPI):
        with pytest.raises(ValueError, match="must not contain"):
            api.record("Playbooks/../secrets.md", "used")

    def test_normal_path_works(self, api: PlaybookAPI):
        result = api.get("Playbooks/OpenClaw_Tailscale.md")
        assert result["playbook_id"] == "Playbooks/OpenClaw_Tailscale.md"


# ---------------------------------------------------------------------------
# Promote
# ---------------------------------------------------------------------------

class TestPromote:

    def _create_inbox_candidate(self, vault: Path, query: str = "kubernetes helm") -> str:
        """Helper: create an Inbox candidate file and return its relative path."""
        inbox_dir = vault / "Inbox"
        inbox_dir.mkdir(exist_ok=True)
        candidate = inbox_dir / "Candidate_test_promote.md"
        content = (
            "---\n"
            "type: candidate\n"
            f"query: {query}\n"
            "status: pending\n"
            "created: 2026-02-26\n"
            "---\n"
            "\n"
            "# Knowledge Gap\n"
            f"Query: {query}\n"
        )
        candidate.write_text(content, encoding="utf-8")
        return str(candidate.relative_to(vault))

    def test_promote_basic(self, api: PlaybookAPI, vault: Path):
        inbox_path = self._create_inbox_candidate(vault)
        result = api.promote(
            inbox_path,
            type="pattern",
            domain="infra",
            title="Kubernetes Helm Deployment",
        )
        assert "playbook_id" in result
        assert "Kubernetes_Helm_Deployment" in result["playbook_id"]
        assert Path(result["abs_path"]).is_file()

    def test_promote_marks_candidate(self, api: PlaybookAPI, vault: Path):
        inbox_path = self._create_inbox_candidate(vault)
        api.promote(
            inbox_path,
            type="pattern",
            domain="infra",
            title="Helm Deploy Mark Test",
        )
        # Candidate should be marked as promoted
        candidate_text = (vault / inbox_path).read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(candidate_text)
        assert meta["status"] == "promoted"
        assert "promoted_to" in meta

    def test_promote_uses_candidate_body(self, api: PlaybookAPI, vault: Path):
        inbox_path = self._create_inbox_candidate(vault, query="docker compose")
        result = api.promote(
            inbox_path,
            type="runbook",
            domain="infra",
            title="Docker Compose Setup",
        )
        # The playbook body should contain the candidate's body
        pb = api.get(result["playbook_id"])
        assert "Knowledge Gap" in pb["body"]

    def test_promote_body_override(self, api: PlaybookAPI, vault: Path):
        inbox_path = self._create_inbox_candidate(vault, query="redis cluster")
        result = api.promote(
            inbox_path,
            type="troubleshooting",
            domain="infra",
            title="Redis Cluster Override",
            body="# Custom Body\n\nOverridden content.\n",
        )
        pb = api.get(result["playbook_id"])
        assert "Custom Body" in pb["body"]
        assert "Knowledge Gap" not in pb["body"]

    def test_promote_logs_event(self, api: PlaybookAPI, vault: Path):
        inbox_path = self._create_inbox_candidate(vault, query="nginx config")
        api.promote(
            inbox_path,
            type="pattern",
            domain="infra",
            title="Nginx Config Promote Log",
        )
        events_file = vault / "logs" / "events.jsonl"
        events = [json.loads(line) for line in events_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        promoted_events = [e for e in events if e.get("type") == "promoted"]
        assert len(promoted_events) >= 1
        last = promoted_events[-1]
        assert last["inbox_file"] == inbox_path
        assert "Nginx_Config_Promote_Log" in last["playbook_id"]

    def test_promote_missing_file_raises(self, api: PlaybookAPI):
        with pytest.raises(FileNotFoundError):
            api.promote(
                "Inbox/Nonexistent.md",
                type="pattern",
                domain="infra",
                title="Should Fail",
            )

    def test_promote_searchable(self, api: PlaybookAPI, vault: Path):
        inbox_path = self._create_inbox_candidate(vault, query="terraform modules")
        api.promote(
            inbox_path,
            type="runbook",
            domain="infra",
            title="Terraform Module Registry",
            body="# Terraform Module Registry\n\nHow to publish terraform modules.\n",
        )
        results = api.search("terraform module registry")
        assert len(results) >= 1
        assert any("Terraform_Module_Registry" in r["playbook_id"] for r in results)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class TestAudit:

    def test_audit_returns_all_domains(self, api: PlaybookAPI):
        report = api.audit()
        assert "domains" in report
        assert "summary" in report
        for d in PlaybookAPI.VALID_DOMAINS:
            assert d in report["domains"]

    def test_audit_domain_filter(self, api: PlaybookAPI):
        report = api.audit(domain="infra")
        assert "infra" in report["domains"]
        assert len(report["domains"]) == 1

    def test_audit_ready_threshold(self, api: PlaybookAPI, vault: Path):
        # Create enough playbooks in security domain (currently 0)
        for i in range(3):
            api.create(
                type="pattern",
                domain="security",
                title=f"Security Audit Test {i}",
                body=f"# Security Pattern {i}\n",
            )
        report = api.audit(min_count=3)
        assert report["domains"]["security"]["ready"] is True
        assert report["domains"]["security"]["count"] >= 3

    def test_audit_not_ready_domain(self, api: PlaybookAPI):
        report = api.audit(min_count=100)
        # With min_count=100, no domain should be ready
        for d, stats in report["domains"].items():
            assert stats["ready"] is False

    def test_audit_summary_health(self, api: PlaybookAPI):
        report = api.audit(min_count=3)
        summary = report["summary"]
        assert "total_playbooks" in summary
        assert "total_domains" in summary
        assert "ready_domains" in summary
        assert "health_pct" in summary
        assert "inbox_pending_count" in summary
        assert 0 <= summary["health_pct"] <= 100

    def test_audit_inbox_pending(self, api: PlaybookAPI, vault: Path):
        # Create inbox candidates
        inbox_dir = vault / "Inbox"
        inbox_dir.mkdir(exist_ok=True)
        for i in range(2):
            candidate = inbox_dir / f"Candidate_audit_test_{i}.md"
            candidate.write_text(
                f"---\ntype: candidate\nquery: test query {i}\nstatus: pending\ncreated: 2026-02-26\n---\n\n# Knowledge Gap\n",
                encoding="utf-8",
            )
        report = api.audit()
        assert report["summary"]["inbox_pending_count"] >= 2

    def test_audit_excludes_promoted_inbox(self, api: PlaybookAPI, vault: Path):
        inbox_dir = vault / "Inbox"
        inbox_dir.mkdir(exist_ok=True)
        # Create a promoted candidate
        promoted = inbox_dir / "Candidate_promoted_test.md"
        promoted.write_text(
            "---\ntype: candidate\nquery: old query\nstatus: promoted\npromoted_to: Playbooks/X.md\ncreated: 2026-02-26\n---\n\n# Done\n",
            encoding="utf-8",
        )
        report = api.audit()
        promoted_files = [c for c in report["inbox_pending"] if "promoted_test" in c["file"]]
        assert len(promoted_files) == 0

    def test_audit_avg_confidence(self, api: PlaybookAPI, vault: Path):
        # Create 2 playbooks with known confidence
        api.create(type="pattern", domain="security", title="Conf Test A", body="A", confidence=0.8)
        api.create(type="pattern", domain="security", title="Conf Test B", body="B", confidence=0.6)
        report = api.audit(domain="security")
        avg = report["domains"]["security"]["avg_confidence"]
        assert 0.6 <= avg <= 0.8  # Should be around 0.7


# ---------------------------------------------------------------------------
# H1: Confidence auto-update (EWA)
# ---------------------------------------------------------------------------

class TestConfidenceUpdate:

    def test_confidence_updates_on_used(self, api: PlaybookAPI, vault: Path):
        target = "Playbooks/OpenClaw_Tailscale.md"
        before = api.get(target)["meta"]["confidence"]
        assert before == 0.9

        api.record(target, "used", context="test")

        after = api.get(target)["meta"]["confidence"]
        assert after > before

    def test_confidence_updates_on_rejected(self, api: PlaybookAPI, vault: Path):
        target = "Playbooks/Akkadian_Strategy.md"
        before = api.get(target)["meta"]["confidence"]
        assert before == 0.7

        api.record(target, "rejected", context="test")

        after = api.get(target)["meta"]["confidence"]
        assert after < before

    def test_confidence_ewma_bounds(self, api: PlaybookAPI, vault: Path):
        target = "Playbooks/OpenClaw_Tailscale.md"

        for _ in range(50):
            api.record(target, "rejected", context="bound test")

        after = api.get(target)["meta"]["confidence"]
        assert 0.0 <= after <= 1.0

        for _ in range(100):
            api.record(target, "used", context="bound test")

        after2 = api.get(target)["meta"]["confidence"]
        assert 0.0 <= after2 <= 1.0


# ---------------------------------------------------------------------------
# H7: Inbox suggestion on zero search results
# ---------------------------------------------------------------------------

class TestInboxSuggestion:

    def test_search_zero_creates_inbox(self, api: PlaybookAPI, vault: Path):
        inbox_dir = vault / "Inbox"
        inbox_dir.mkdir(exist_ok=True)
        before = list(inbox_dir.glob("Candidate_*.md"))

        api.search("kubernetes helm chart")

        after = list(inbox_dir.glob("Candidate_*.md"))
        assert len(after) == len(before) + 1

    def test_search_hit_no_inbox(self, api: PlaybookAPI, vault: Path):
        inbox_dir = vault / "Inbox"
        inbox_dir.mkdir(exist_ok=True)
        before = list(inbox_dir.glob("Candidate_*.md"))

        api.search("tailscale")

        after = list(inbox_dir.glob("Candidate_*.md"))
        assert len(after) == len(before)

    def test_inbox_content_format(self, api: PlaybookAPI, vault: Path):
        inbox_dir = vault / "Inbox"
        inbox_dir.mkdir(exist_ok=True)

        api.search("machine learning pytorch")

        candidates = sorted(inbox_dir.glob("Candidate_*.md"))
        assert len(candidates) >= 1

        text = candidates[-1].read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        assert meta["type"] == "candidate"
        assert meta["query"] == "machine learning pytorch"
        assert "Knowledge Gap" in body


# ---------------------------------------------------------------------------
# H3: BRAIN_SESSION_ID environment variable
# ---------------------------------------------------------------------------

class TestSessionIdEnv:

    def test_session_id_from_env(self, vault: Path, monkeypatch):
        monkeypatch.setenv("BRAIN_SESSION_ID", "env-session-42")
        api = PlaybookAPI(vault=vault)
        assert api.session_id == "env-session-42"

    def test_session_id_explicit_overrides_env(self, vault: Path, monkeypatch):
        monkeypatch.setenv("BRAIN_SESSION_ID", "env-session-42")
        api = PlaybookAPI(vault=vault, session_id="explicit-session")
        assert api.session_id == "explicit-session"

    def test_session_id_auto_generated(self, vault: Path, monkeypatch):
        monkeypatch.delenv("BRAIN_SESSION_ID", raising=False)
        api = PlaybookAPI(vault=vault)
        assert len(api.session_id) == 12


# ---------------------------------------------------------------------------
# _serialize_frontmatter / _update_frontmatter
# ---------------------------------------------------------------------------

class TestSerializeFrontmatter:

    def test_roundtrip(self):
        original = SAMPLE_PLAYBOOK
        meta, body = parse_frontmatter(original)
        serialized = _serialize_frontmatter(meta) + body
        meta2, body2 = parse_frontmatter(serialized)
        assert meta2["type"] == meta["type"]
        assert meta2["domain"] == meta["domain"]
        assert meta2["tags"] == meta["tags"]
        assert body2 == body

    def test_update_frontmatter(self, tmp_path: Path):
        fp = tmp_path / "test.md"
        fp.write_text(SAMPLE_PLAYBOOK, encoding="utf-8")

        _update_frontmatter(fp, "confidence", 0.42)

        meta, _ = parse_frontmatter(fp.read_text(encoding="utf-8"))
        assert abs(meta["confidence"] - 0.42) < 0.001


# ---------------------------------------------------------------------------
# Confidence Decay (Feature 2)
# ---------------------------------------------------------------------------

class TestConfidenceDecay:

    def _create_old_playbook(self, vault: Path, days_ago: int, confidence: float = 0.8,
                             last_referenced: bool = True) -> str:
        """Helper: create a playbook with a last_referenced date in the past."""
        from playbook_api import JST
        past_dt = (datetime.now(JST) - timedelta(days=days_ago)).isoformat()
        meta_lines = [
            "---",
            "type: pattern",
            f"created: {past_dt}",
            "domain: infra",
            f"confidence: {confidence}",
        ]
        if last_referenced:
            meta_lines.append(f"last_referenced: {past_dt}")
        meta_lines.extend(["---", "", "# Old Playbook", ""])
        playbooks = vault / "Playbooks"
        playbooks.mkdir(exist_ok=True)
        filename = f"Old_Playbook_{days_ago}d.md"
        (playbooks / filename).write_text("\n".join(meta_lines), encoding="utf-8")
        return f"Playbooks/{filename}"

    def test_no_decay_within_threshold(self, api: PlaybookAPI, vault: Path):
        rel = self._create_old_playbook(vault, days_ago=30, confidence=0.8)
        result = api.apply_time_decay(rel)
        assert result == 0.8

    def test_decay_after_threshold(self, api: PlaybookAPI, vault: Path):
        rel = self._create_old_playbook(vault, days_ago=120, confidence=0.8)
        result = api.apply_time_decay(rel)
        assert result < 0.8

    def test_decay_floor(self, api: PlaybookAPI, vault: Path):
        # 3 years = 1095 days, massive decay
        rel = self._create_old_playbook(vault, days_ago=1095, confidence=0.8)
        result = api.apply_time_decay(rel)
        assert result >= PlaybookAPI.MIN_CONFIDENCE_FLOOR

    def test_decay_uses_last_referenced(self, api: PlaybookAPI, vault: Path):
        """last_referenced should be used over created when available."""
        from playbook_api import JST
        # created 200 days ago, last_referenced 30 days ago
        created_dt = (datetime.now(JST) - timedelta(days=200)).isoformat()
        ref_dt = (datetime.now(JST) - timedelta(days=30)).isoformat()
        playbooks = vault / "Playbooks"
        playbooks.mkdir(exist_ok=True)
        content = (
            f"---\ntype: pattern\ncreated: {created_dt}\n"
            f"last_referenced: {ref_dt}\ndomain: infra\nconfidence: 0.80\n"
            f"---\n\n# Test\n"
        )
        (playbooks / "Decay_LR_Test.md").write_text(content, encoding="utf-8")
        result = api.apply_time_decay("Playbooks/Decay_LR_Test.md")
        # last_referenced is 30 days ago, within threshold — no decay
        assert result == 0.8

    def test_get_updates_last_referenced(self, api: PlaybookAPI, vault: Path):
        api.get("Playbooks/OpenClaw_Tailscale.md")
        text = (vault / "Playbooks" / "OpenClaw_Tailscale.md").read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        assert "last_referenced" in meta
        # Should be a recent ISO string
        ref_dt = datetime.fromisoformat(str(meta["last_referenced"]))
        assert (datetime.now(ref_dt.tzinfo) - ref_dt).total_seconds() < 10

    def test_decay_logs_event(self, api: PlaybookAPI, vault: Path):
        rel = self._create_old_playbook(vault, days_ago=150, confidence=0.8)
        api.apply_time_decay(rel)
        log_path = vault / "logs" / "events.jsonl"
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        decay_events = [json.loads(l) for l in lines if "confidence_decayed" in l]
        assert len(decay_events) >= 1
        assert decay_events[-1]["type"] == "confidence_decayed"
        assert decay_events[-1]["old_confidence"] == 0.8
        assert decay_events[-1]["new_confidence"] < 0.8


# ---------------------------------------------------------------------------
# Working Memory (Feature 4)
# ---------------------------------------------------------------------------

class TestWorkingMemory:

    def test_remember_creates_file(self, api: PlaybookAPI, vault: Path):
        result = api.remember("current-task", "ECS deploy 作業中")
        assert result["key"] == "current-task"
        wm_dir = vault / "WorkingMemory"
        assert (wm_dir / "current-task.md").is_file()

    def test_recall_returns_body(self, api: PlaybookAPI, vault: Path):
        api.remember("test-key", "some content here")
        result = api.recall("test-key")
        assert result["key"] == "test-key"
        assert "some content here" in result["body"]

    def test_forget_removes_file(self, api: PlaybookAPI, vault: Path):
        api.remember("temp-key", "temporary")
        assert api.forget("temp-key") is True
        assert not (vault / "WorkingMemory" / "temp-key.md").is_file()

    def test_recall_nonexistent_raises(self, api: PlaybookAPI):
        with pytest.raises(FileNotFoundError):
            api.recall("nonexistent-key")

    def test_context_lists_all(self, api: PlaybookAPI, vault: Path):
        api.remember("key-a", "alpha")
        api.remember("key-b", "beta")
        entries = api.context()
        keys = [e["key"] for e in entries]
        assert "key-a" in keys
        assert "key-b" in keys

    def test_expired_entry_auto_purged(self, api: PlaybookAPI, vault: Path):
        # Create an entry that already expired
        from playbook_api import JST
        wm_dir = vault / "WorkingMemory"
        wm_dir.mkdir(parents=True, exist_ok=True)
        expired_dt = (datetime.now(JST) - timedelta(days=1)).isoformat()
        content = (
            f"---\ntype: working-memory\nkey: old-entry\n"
            f"created: {expired_dt}\nexpires: {expired_dt}\nttl_days: 1\n"
            f"---\nExpired content\n"
        )
        (wm_dir / "old-entry.md").write_text(content, encoding="utf-8")
        entries = api.context()
        keys = [e["key"] for e in entries]
        assert "old-entry" not in keys
        assert not (wm_dir / "old-entry.md").is_file()

    def test_recall_expired_raises(self, api: PlaybookAPI, vault: Path):
        from playbook_api import JST
        wm_dir = vault / "WorkingMemory"
        wm_dir.mkdir(parents=True, exist_ok=True)
        expired_dt = (datetime.now(JST) - timedelta(days=1)).isoformat()
        content = (
            f"---\ntype: working-memory\nkey: exp-key\n"
            f"created: {expired_dt}\nexpires: {expired_dt}\nttl_days: 1\n"
            f"---\nExpired\n"
        )
        (wm_dir / "exp-key.md").write_text(content, encoding="utf-8")
        with pytest.raises(FileNotFoundError, match="expired"):
            api.recall("exp-key")

    def test_remember_overwrites(self, api: PlaybookAPI, vault: Path):
        api.remember("overwrite-key", "version 1")
        api.remember("overwrite-key", "version 2")
        result = api.recall("overwrite-key")
        assert "version 2" in result["body"]


# ---------------------------------------------------------------------------
# Learn (Feature 1 tests)
# ---------------------------------------------------------------------------

class TestLearn:

    def test_learn_creates_inbox_file(self, api: PlaybookAPI, vault: Path):
        result = api.learn(title="Docker Caching Pattern", body="# Docker Caching\n\nUse multi-stage builds.")
        assert "inbox_file" in result
        assert Path(result["abs_path"]).is_file()
        assert result["inbox_file"].startswith("Inbox/Learn_")

    def test_learn_with_domain_and_tags(self, api: PlaybookAPI, vault: Path):
        result = api.learn(
            title="ECS Health Check",
            body="# ECS Health\n",
            domain="infra",
            tags=["ecs", "health"],
        )
        text = Path(result["abs_path"]).read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        assert meta["domain"] == "infra"
        assert meta["tags"] == ["ecs", "health"]

    def test_learn_logs_event(self, api: PlaybookAPI, vault: Path):
        api.learn(title="Test Log Learn", body="body")
        log_path = vault / "logs" / "events.jsonl"
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        learn_events = [json.loads(l) for l in lines if '"learned"' in l]
        assert len(learn_events) >= 1
        assert learn_events[-1]["type"] == "learned"
        assert learn_events[-1]["title"] == "Test Log Learn"

    def test_learn_empty_title_raises(self, api: PlaybookAPI):
        with pytest.raises(ValueError, match="must not be empty"):
            api.learn(title="", body="body")

    def test_learn_auto_source(self, api: PlaybookAPI, vault: Path):
        result = api.learn(title="Auto Pattern", body="body", source="auto")
        text = Path(result["abs_path"]).read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        assert meta["source"] == "auto"


# ---------------------------------------------------------------------------
# Field-weighted scoring (P1-2)
# ---------------------------------------------------------------------------

class TestFieldWeightedScoring:

    def test_title_match_scores_higher_than_body(self, api: PlaybookAPI, vault: Path):
        """A query matching the title should score higher than one matching only body text."""
        # OpenClaw_Tailscale has "OpenClaw Remote Access" in title
        # Create a playbook with "tailscale" only in the body, not title
        api.create(
            type="pattern", domain="infra",
            title="Network Config Pattern",
            tags=["network"],
            body="# Network Config Pattern\n\nUse tailscale for VPN tunnels.\n",
        )
        results = api.search("tailscale")
        # OpenClaw_Tailscale has "tailscale" in title AND tags AND body
        # Network_Config has "tailscale" only in body
        assert len(results) >= 2
        tailscale_scores = {r["playbook_id"]: r["score"] for r in results}
        oc_score = tailscale_scores.get("Playbooks/OpenClaw_Tailscale.md", 0)
        net_score = tailscale_scores.get("Playbooks/Pattern_Network_Config_Pattern.md", 0)
        assert oc_score > net_score

    def test_tag_match_boosts_score(self, api: PlaybookAPI, vault: Path):
        """A playbook with matching tags should score higher than one without."""
        api.create(
            type="pattern", domain="infra",
            title="Deploy A",
            tags=["redis", "cache"],
            body="# Deploy A\n\nSome deployment steps.\n",
        )
        api.create(
            type="pattern", domain="infra",
            title="Deploy B",
            tags=["postgres"],
            body="# Deploy B\n\nRedis is mentioned in body only.\n",
        )
        results = api.search("redis")
        scores = {r["playbook_id"]: r["score"] for r in results}
        a_score = scores.get("Playbooks/Pattern_Deploy_A.md", 0)
        b_score = scores.get("Playbooks/Pattern_Deploy_B.md", 0)
        assert a_score > b_score

    def test_path_contributes_to_score(self, api: PlaybookAPI, vault: Path):
        """The path component should also contribute to scoring."""
        # "Akkadian" appears in the path Playbooks/Akkadian_Strategy.md
        results = api.search("akkadian")
        assert len(results) >= 1
        assert any("Akkadian" in r["playbook_id"] for r in results)


# ---------------------------------------------------------------------------
# find_by_title (P2-1)
# ---------------------------------------------------------------------------

class TestFindByTitle:

    def test_find_basic_match(self, api: PlaybookAPI):
        results = api.find_by_title("OpenClaw")
        assert len(results) == 1
        assert "OpenClaw_Tailscale" in results[0]["playbook_id"]
        assert "OpenClaw Remote Access" in results[0]["title"]

    def test_find_case_insensitive(self, api: PlaybookAPI):
        results = api.find_by_title("openclaw")
        assert len(results) == 1
        assert "OpenClaw_Tailscale" in results[0]["playbook_id"]

    def test_find_no_match(self, api: PlaybookAPI):
        results = api.find_by_title("xyznonexistent")
        assert results == []

    def test_find_empty_query(self, api: PlaybookAPI):
        results = api.find_by_title("")
        assert results == []

    def test_find_returns_confidence_and_domain(self, api: PlaybookAPI):
        results = api.find_by_title("Akkadian")
        assert len(results) == 1
        assert "confidence" in results[0]
        assert results[0]["domain"] == "kaggle"

    def test_find_limit(self, api: PlaybookAPI, vault: Path):
        # Create 3 playbooks with "Test" in title
        for i in range(3):
            api.create(
                type="pattern", domain="infra",
                title=f"Test Pattern {i}",
                body=f"# Test Pattern {i}\n",
            )
        results = api.find_by_title("Test Pattern", limit=2)
        assert len(results) == 2

    def test_find_cli(self, vault: Path):
        from playbook_api import main
        ret = main(["--vault", str(vault), "find", "OpenClaw"])
        assert ret == 0
