from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class Settings:
    poll_interval_seconds: int = 5
    ollama_endpoint: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    db_path: str = "~/.netwatch/netwatch.db"
    rules_path: str = "config/rules.yaml"
    log_level: str = "INFO"

    @classmethod
    def load(cls) -> Settings:
        project_root = get_project_root()
        load_dotenv(project_root / ".env", override=False)

        yaml_data = _read_settings_yaml(project_root / "config" / "settings.yaml")
        env_data = _read_env_overrides()
        merged = {**yaml_data, **env_data}
        return cls(**{k: v for k, v in merged.items() if k in cls.__annotations__})

    def resolved_db_path(self) -> Path:
        db_path = Path(self.db_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

    def resolved_rules_path(self) -> Path:
        candidate = Path(self.rules_path)
        if candidate.is_absolute():
            return candidate
        return get_project_root() / candidate



def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]



def _read_settings_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        return {}
    return loaded



def _read_env_overrides() -> dict[str, Any]:
    import os

    mapping: dict[str, str] = {
        "NETWATCH_POLL_INTERVAL_SECONDS": "poll_interval_seconds",
        "NETWATCH_OLLAMA_ENDPOINT": "ollama_endpoint",
        "NETWATCH_OLLAMA_MODEL": "ollama_model",
        "NETWATCH_DB_PATH": "db_path",
        "NETWATCH_RULES_PATH": "rules_path",
        "NETWATCH_LOG_LEVEL": "log_level",
    }

    out: dict[str, Any] = {}
    for env_key, setting_key in mapping.items():
        value = os.getenv(env_key)
        if value is None:
            continue
        if setting_key == "poll_interval_seconds":
            out[setting_key] = int(value)
        else:
            out[setting_key] = value
    return out
