from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

import httpx
import yaml

from netwatch.aggregator.storage import get_cached_category, set_cached_category
from netwatch.shared.config import Settings
from netwatch.shared.logger import get_logger
from netwatch.shared.models import Category

logger = get_logger("aggregator.classifier")

_ALLOWED_CATEGORIES: tuple[Category, ...] = (
    "productive",
    "distracting",
    "background",
    "system",
    "unknown",
)


class DomainClassifier:
    def __init__(self, settings: Settings | None = None, db_path: str | Path | None = None) -> None:
        self.settings = settings or Settings.load()
        self.db_path = db_path
        self.rules = load_rules(self.settings.resolved_rules_path())

    def classify(self, hostname: str) -> Category:
        normalized = hostname.strip().lower()
        if not normalized:
            return "unknown"

        rule_match = _classify_from_rules(normalized, self.rules)
        if rule_match:
            return rule_match

        cached = get_cached_category(normalized, self.db_path)
        if cached:
            return cached

        classified = self._classify_with_ollama(normalized)
        set_cached_category(normalized, classified, self.db_path)
        return classified

    def _classify_with_ollama(self, hostname: str) -> Category:
        prompt = (
            "Classify this network destination for a software engineer: "
            f"{hostname}. Reply with exactly one word from: productive, distracting, "
            "background, system."
        )
        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        url = self.settings.ollama_endpoint.rstrip("/") + "/api/generate"

        try:
            with httpx.Client(timeout=1.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Ollama unavailable; using unknown for %s (%s)", hostname, exc)
            return "unknown"

        raw = str(data.get("response", "")).strip().lower()
        if raw in _ALLOWED_CATEGORIES and raw != "unknown":
            return raw  # type: ignore[return-value]

        logger.warning("Unexpected Ollama response %r for %s", raw, hostname)
        return "unknown"



def load_rules(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {cat: [] for cat in _ALLOWED_CATEGORIES if cat != "unknown"}

    with path.open("r", encoding="utf-8") as handle:
        loaded: dict[str, Any] = yaml.safe_load(handle) or {}

    out: dict[str, list[str]] = {}
    for category in ("productive", "distracting", "background", "system"):
        values = loaded.get(category, [])
        if not isinstance(values, list):
            values = []
        out[category] = [str(v).strip().lower() for v in values if str(v).strip()]
    return out



def _classify_from_rules(hostname: str, rules: dict[str, list[str]]) -> Category | None:
    for category in ("productive", "distracting", "background", "system"):
        patterns = rules.get(category, [])
        for pattern in patterns:
            if fnmatch.fnmatch(hostname, pattern):
                return category  # type: ignore[return-value]
            if hostname == pattern:
                return category  # type: ignore[return-value]
    return None
