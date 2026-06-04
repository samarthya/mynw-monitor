# NetWatch

NetWatch is a local-first, privacy-focused network activity monitor for software engineers. It captures local network connections, enriches and classifies destinations, stores data in SQLite, and renders a Streamlit dashboard.

## Architecture

The project is split into four independent layers plus shared utilities:

- `netwatch/monitor/` — raw connection collection (platform adapters)
- `netwatch/aggregator/` — enrichment, classification, SQLite persistence
- `netwatch/analytics/` — typed read/query + scoring logic
- `netwatch/ui/` — Streamlit display layer
- `netwatch/shared/` — config, models, logger, theme

## Requirements

- Python 3.11+
- macOS first-class support (Apple Silicon + Intel)
- [uv](https://docs.astral.sh/uv/) for dependency and environment management

## Setup

```bash
curl -Lsf https://astral.sh/uv/install.sh | sh
cd /tmp/workspace/samarthya/mynw-monitor
uv sync --extra dev
cp .env.example .env
```

## Run monitor daemon

```bash
uv run netwatch-monitor
```

This starts polling every 5 seconds (default), enriches/classifies each destination, and writes to `~/.netwatch/netwatch.db`.

## Run UI

In a separate terminal:

```bash
cd /tmp/workspace/samarthya/mynw-monitor
uv run streamlit run netwatch/ui/app.py
```

## Configuration

- `config/settings.yaml` for app defaults
- `.env` for per-machine overrides
- `config/rules.yaml` for category domain patterns

## Classification flow

1. Match hostname against `config/rules.yaml`
2. If unmatched, query local Ollama endpoint (`http://localhost:11434`, model `llama3`)
3. Cache result in SQLite (`domain_classifications`)
4. If Ollama is unavailable, classify as `unknown`

## Testing and linting

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## macOS permission notes

- Connection-level monitoring with `psutil` + `lsof` works without sudo for user-owned processes.
- Full packet capture is not used in NetWatch and would require elevated privileges and different tooling.

## Platform status

- `monitor/macos.py`: implemented
- `monitor/linux.py`: stub (`NotImplementedError`, Phase 2)
- `monitor/windows.py`: stub (`NotImplementedError`, Phase 2)
