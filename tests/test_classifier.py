from __future__ import annotations

from pathlib import Path

from netwatch.aggregator.classifier import DomainClassifier
from netwatch.aggregator.storage import init_db
from netwatch.shared.config import Settings


class _MockResponse:
    def __init__(self, payload: dict[str, str]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return self._payload


class _MockClient:
    def __init__(self, payload: dict[str, str] | Exception):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def post(self, *args, **kwargs):
        if isinstance(self.payload, Exception):
            raise self.payload
        return _MockResponse(self.payload)



def _settings(tmp_path: Path, rules_path: Path) -> Settings:
    return Settings(
        poll_interval_seconds=5,
        ollama_endpoint="http://localhost:11434",
        ollama_model="llama3",
        db_path=str(tmp_path / "netwatch.db"),
        rules_path=str(rules_path),
        log_level="INFO",
    )



def test_rules_engine_match(tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(
        """
productive:
  - "*.github.com"
distracting: []
background: []
system: []
""",
        encoding="utf-8",
    )
    settings = _settings(tmp_path, rules_path)
    init_db(settings.resolved_db_path())
    classifier = DomainClassifier(settings=settings, db_path=settings.resolved_db_path())

    assert classifier.classify("api.github.com") == "productive"



def test_ollama_fallback_and_cache(monkeypatch, tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(
        """
productive: []
distracting: []
background: []
system: []
""",
        encoding="utf-8",
    )
    settings = _settings(tmp_path, rules_path)
    init_db(settings.resolved_db_path())

    calls = {"count": 0}

    def _client_factory(*args, **kwargs):
        calls["count"] += 1
        return _MockClient({"response": "background"})

    monkeypatch.setattr("netwatch.aggregator.classifier.httpx.Client", _client_factory)
    classifier = DomainClassifier(settings=settings, db_path=settings.resolved_db_path())

    assert classifier.classify("unknown.domain") == "background"
    assert classifier.classify("unknown.domain") == "background"
    assert calls["count"] == 1



def test_ollama_unavailable_returns_unknown(monkeypatch, tmp_path: Path) -> None:
    rules_path = tmp_path / "rules.yaml"
    rules_path.write_text(
        """
productive: []
distracting: []
background: []
system: []
""",
        encoding="utf-8",
    )
    settings = _settings(tmp_path, rules_path)
    init_db(settings.resolved_db_path())

    def _client_factory(*args, **kwargs):
        return _MockClient(RuntimeError("offline"))

    monkeypatch.setattr("netwatch.aggregator.classifier.httpx.Client", _client_factory)
    classifier = DomainClassifier(settings=settings, db_path=settings.resolved_db_path())

    assert classifier.classify("new.domain") == "unknown"
