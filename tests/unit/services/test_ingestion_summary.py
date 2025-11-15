from unittest.mock import MagicMock

import pytest

from src.services.ingestion import IngestionService
from src.services import ingestion as ingestion_module


def _make_service(route_return=None, route_side_effect=None, supported_languages=None):
    vector_db = MagicMock()
    classifier = MagicMock()
    chunker = MagicMock()
    indexer = MagicMock()
    model_router = MagicMock()

    if route_side_effect is not None:
        model_router.route.side_effect = route_side_effect
    else:
        model_router.route.return_value = route_return

    model_router.generate_embedding.return_value = [0.1]

    service = IngestionService(
        vector_db=vector_db,
        classifier=classifier,
        chunker=chunker,
        indexer=indexer,
        model_router=model_router,
        supported_languages=supported_languages,
    )
    return service, model_router


def test_generate_summary_structured_success():
    structured = (
        "Topic: release\n"
        "DocType: checklist\n"
        "Project: OrchestratorX\n"
        "KeyActions:\n"
        "- Run smoke tests and flip traffic once metrics are green."
    )
    service, _ = _make_service(route_return=structured)
    conversation = {
        "user": "リリース手順を確認したい",
        "assistant": "チェックリスト通りにデプロイし、Smoke Test 完了後に 50% Traffic へ切り替える。",
        "metadata": {"topic": "release", "doc_type": "checklist"},
        "project": "OrchestratorX",
    }

    summary = service._generate_summary(conversation)

    assert summary.startswith("Topic: release")
    assert "KeyActions:" in summary
    assert "\n-" in summary


def test_generate_summary_fallback_when_llm_fails():
    service, _ = _make_service(route_side_effect=RuntimeError("llm down"))
    conversation = {
        "user": "¿Cómo exportamos los reportes?",
        "assistant": "Usa el comando export --latest y guarda en S3.",
        "metadata": {"topic": "reporting", "doc_type": "guide"},
        "project": "InsightOps",
    }

    summary = service._generate_summary(conversation)

    assert summary.startswith("Topic: reporting")
    assert "KeyActions:" in summary
    assert "\n-" in summary


def test_detect_language_heuristics(monkeypatch):
    monkeypatch.setattr(ingestion_module, "_langdetect_detect", None)
    assert IngestionService._detect_language("これは監査ログです") == "ja"
    assert IngestionService._detect_language("¿Podemos revisar el backlog?") == "es"
    assert IngestionService._detect_language("Need to rerun the job") == "en"


def test_generate_summary_routes_to_cloud_for_unsupported_language(monkeypatch):
    structured = (
        "Topic: reporting\n"
        "DocType: guide\n"
        "Project: InsightOps\n"
        "KeyActions:\n"
        "- Use export command."
    )
    service, router = _make_service(
        route_return=structured,
        supported_languages=["en"],
    )
    monkeypatch.setattr(ingestion_module, "_langdetect_detect", lambda _: "fr")
    conversation = {
        "user": "Bonjour, pouvez-vous résumer la politique?",
        "assistant": "Collectez les rapports financiers et partagez-les.",
        "metadata": {"topic": "reporting", "doc_type": "guide"},
        "project": "InsightOps",
    }

    service._generate_summary(conversation)
    assert router.route.call_args.kwargs.get("force_routing") == "cloud"


def test_language_override_via_metadata(monkeypatch):
    structured = (
        "Topic: release\n"
        "DocType: checklist\n"
        "Project: OrchestratorX\n"
        "KeyActions:\n"
        "- Deploy after smoke tests."
    )
    service, router = _make_service(
        route_return=structured,
        supported_languages=["ja"],
    )
    monkeypatch.setattr(ingestion_module, "_langdetect_detect", lambda *_: "en")
    conversation = {
        "user": "Please prep the release?",
        "assistant": "Check the matrix and promote.",
        "metadata": {
            "topic": "release",
            "doc_type": "checklist",
            "project": "OrchestratorX",
            "language_override": "ja",
        },
    }

    service._generate_summary(conversation)
    assert router.route.call_args.kwargs.get("force_routing") == "local"


def test_language_override_via_env(monkeypatch):
    structured = (
        "Topic: finance\n"
        "DocType: memo\n"
        "Project: InsightOps\n"
        "KeyActions:\n"
        "- Summarize reports."
    )
    service, router = _make_service(
        route_return=structured,
        supported_languages=["fr"],
    )
    monkeypatch.setattr(ingestion_module, "_langdetect_detect", lambda *_: "es")
    monkeypatch.setenv("CONTEXT_ORCHESTRATOR_LANG_OVERRIDE", "fr")
    conversation = {
        "user": "Bonjour, puis-je obtenir un résumé ?",
        "assistant": "Oui, voici la synthèse.",
        "metadata": {"topic": "finance", "doc_type": "memo", "project": "InsightOps"},
    }

    try:
        service._generate_summary(conversation)
        assert router.route.call_args.kwargs.get("force_routing") == "local"
    finally:
        monkeypatch.delenv("CONTEXT_ORCHESTRATOR_LANG_OVERRIDE", raising=False)
