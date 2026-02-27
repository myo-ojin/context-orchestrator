#!/usr/bin/env python3
"""A/B benchmark: Compare search behavior with/without side effects.

Measures:
1. Search precision@1 (same as sim_driver)
2. Log integrity (does search write to log?)
3. Decay behavior (does search persist decay?)
4. Performance (search latency)
5. Repeated search consistency

Usage:
    python ab_benchmark.py          # Run and save results
    python ab_benchmark.py --json   # Output JSON to stdout
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RUNTIME_DIR))

from playbook_api import PlaybookAPI, parse_frontmatter, _serialize_frontmatter
from tests.simulation.seed_vault import generate_vault
from tests.simulation.sim_scenarios import get_scenarios_by_category

JST = timezone(timedelta(hours=9))
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _fresh_vault() -> Path:
    vault = Path("/tmp/brain-ab-test")
    if vault.exists():
        shutil.rmtree(vault)
    generate_vault(vault)
    return vault


def test_precision(vault: Path) -> dict:
    """Measure precision@1 for all precision scenarios."""
    api = PlaybookAPI(vault=vault, session_id="ab-precision")
    total, correct = 0, 0
    details = []

    for sc in get_scenarios_by_category("precision"):
        hits = api.search(sc.query, domain=sc.domain, limit=5)
        top_id = hits[0]["playbook_id"] if hits else None
        is_correct = top_id == sc.expected_id
        total += 1
        if is_correct:
            correct += 1
        details.append({
            "query": sc.query,
            "expected": sc.expected_id,
            "got": top_id,
            "correct": is_correct,
            "score": hits[0]["score"] if hits else 0,
        })

    return {
        "precision_at_1": correct / total if total else 0,
        "correct": correct,
        "total": total,
        "details": details,
    }


def test_log_integrity(vault: Path) -> dict:
    """Check if search writes to event log."""
    api = PlaybookAPI(vault=vault, session_id="ab-log")
    log_path = vault / "logs" / "events.jsonl"

    # Count log lines before search
    before = len(log_path.read_text().strip().splitlines()) if log_path.exists() else 0

    # Run 10 searches
    queries = ["ECS deploy", "CSS layout", "CI pipeline", "docker", "Next.js",
               "troubleshoot", "checklist", "security", "terraform", "PR review"]
    for q in queries:
        api.search(q)

    after = len(log_path.read_text().strip().splitlines()) if log_path.exists() else 0
    new_events = after - before

    return {
        "searches_performed": len(queries),
        "log_events_before": before,
        "log_events_after": after,
        "new_events_from_search": new_events,
        "search_is_pure": new_events == 0,
    }


def test_decay_persistence(vault: Path) -> dict:
    """Check if search persists confidence decay to disk."""
    # Create a playbook with old last_referenced (> 90 days)
    playbooks_dir = vault / "Playbooks"
    old_date = (datetime.now(JST) - timedelta(days=180)).isoformat()
    content = (
        f"---\ntype: pattern\ncreated: {old_date}\n"
        f"last_referenced: {old_date}\ndomain: infra\nconfidence: 0.8000\n"
        f"tags: [decay-test]\n---\n\n# Decay Test Playbook\n\nOld playbook for decay testing.\n"
    )
    test_file = playbooks_dir / "Pattern_Decay_AB_Test.md"
    test_file.write_text(content, encoding="utf-8")

    api = PlaybookAPI(vault=vault, session_id="ab-decay")

    # Read confidence before search
    text_before = test_file.read_text(encoding="utf-8")
    meta_before, _ = parse_frontmatter(text_before)
    conf_before = meta_before.get("confidence", 0.5)

    # Search for it
    results = api.search("decay test", limit=10)

    # Read confidence after search (from disk)
    text_after = test_file.read_text(encoding="utf-8")
    meta_after, _ = parse_frontmatter(text_after)
    conf_after = meta_after.get("confidence", 0.5)

    # Find it in search results
    search_conf = None
    for r in results:
        if "Decay_AB_Test" in r["playbook_id"]:
            search_conf = r["confidence"]
            break

    return {
        "confidence_on_disk_before": conf_before,
        "confidence_on_disk_after": conf_after,
        "confidence_in_search_result": search_conf,
        "disk_changed_by_search": conf_before != conf_after,
        "search_shows_decayed": search_conf is not None and search_conf < conf_before,
    }


def test_performance(vault: Path) -> dict:
    """Benchmark search latency."""
    api = PlaybookAPI(vault=vault, session_id="ab-perf")
    queries = ["ECS deploy", "CSS layout", "CI pipeline", "docker build",
               "conventional commits", "troubleshoot error", "PR review"]

    # Warmup
    for q in queries:
        api.search(q)

    # Measure
    times = []
    for _ in range(3):  # 3 rounds
        for q in queries:
            start = time.monotonic()
            api.search(q)
            elapsed = time.monotonic() - start
            times.append(elapsed * 1000)  # ms

    return {
        "total_searches": len(times),
        "avg_ms": round(sum(times) / len(times), 3),
        "min_ms": round(min(times), 3),
        "max_ms": round(max(times), 3),
        "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 3),
    }


def test_repeated_consistency(vault: Path) -> dict:
    """Search same query 5 times, check if scores/order change."""
    api = PlaybookAPI(vault=vault, session_id="ab-consistency")
    query = "ECS deploy checklist"

    runs = []
    for i in range(5):
        hits = api.search(query, limit=5)
        runs.append([(h["playbook_id"], h["score"], h["confidence"]) for h in hits])

    # Compare all runs to first
    consistent_order = all(
        [r[0] for r in run] == [r[0] for r in runs[0]] for run in runs
    )
    consistent_scores = all(
        [r[1] for r in run] == [r[1] for r in runs[0]] for run in runs
    )
    consistent_confidence = all(
        [r[2] for r in run] == [r[2] for r in runs[0]] for run in runs
    )

    return {
        "query": query,
        "num_runs": 5,
        "consistent_order": consistent_order,
        "consistent_scores": consistent_scores,
        "consistent_confidence": consistent_confidence,
        "first_run": [{"id": r[0], "score": r[1], "conf": r[2]} for r in runs[0]],
        "last_run": [{"id": r[0], "score": r[1], "conf": r[2]} for r in runs[-1]],
    }


def run_benchmark() -> dict:
    """Run all A/B benchmark tests."""
    vault = _fresh_vault()

    results = {
        "branch": "unknown",  # filled by caller or CI
        "timestamp": datetime.now(JST).isoformat(),
        "tests": {},
    }

    print("=" * 50)
    print("A/B Benchmark: Search Side Effects")
    print("=" * 50)

    print("\n[1] Precision@1")
    results["tests"]["precision"] = test_precision(vault)
    print(f"  {results['tests']['precision']['precision_at_1']:.0%}")

    print("\n[2] Log Integrity")
    # Fresh vault for log test
    vault2 = _fresh_vault()
    results["tests"]["log_integrity"] = test_log_integrity(vault2)
    li = results["tests"]["log_integrity"]
    print(f"  search_is_pure={li['search_is_pure']}, new_events={li['new_events_from_search']}")

    print("\n[3] Decay Persistence")
    vault3 = _fresh_vault()
    results["tests"]["decay_persistence"] = test_decay_persistence(vault3)
    dp = results["tests"]["decay_persistence"]
    print(f"  disk_changed={dp['disk_changed_by_search']}, search_shows_decayed={dp['search_shows_decayed']}")

    print("\n[4] Performance")
    vault4 = _fresh_vault()
    results["tests"]["performance"] = test_performance(vault4)
    perf = results["tests"]["performance"]
    print(f"  avg={perf['avg_ms']:.1f}ms, p95={perf['p95_ms']:.1f}ms")

    print("\n[5] Repeated Consistency")
    vault5 = _fresh_vault()
    results["tests"]["consistency"] = test_repeated_consistency(vault5)
    cons = results["tests"]["consistency"]
    print(f"  order={cons['consistent_order']}, scores={cons['consistent_scores']}, conf={cons['consistent_confidence']}")

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"  Precision@1:       {results['tests']['precision']['precision_at_1']:.0%}")
    print(f"  Search is pure:    {li['search_is_pure']}")
    print(f"  Decay on disk:     {dp['disk_changed_by_search']}")
    print(f"  Avg latency:       {perf['avg_ms']:.1f}ms")
    print(f"  Consistent:        order={cons['consistent_order']}, conf={cons['consistent_confidence']}")

    return results


def main():
    results = run_benchmark()

    if "--json" in sys.argv:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out = RESULTS_DIR / "ab_benchmark.json"
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nResults saved to: {out}")


if __name__ == "__main__":
    main()
