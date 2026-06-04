from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from threading import Lock

from netwatch.shared.config import Settings

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
_CONFIGURED = False
_LOCK = Lock()



def get_logger(name: str) -> logging.Logger:
    global _CONFIGURED

    if not _CONFIGURED:
        with _LOCK:
            if not _CONFIGURED:
                settings = Settings.load()
                log_dir = Path("~/.netwatch/logs").expanduser()
                log_dir.mkdir(parents=True, exist_ok=True)

                handler = TimedRotatingFileHandler(
                    filename=log_dir / "netwatch.log",
                    when="midnight",
                    interval=1,
                    backupCount=7,
                    encoding="utf-8",
                )
                handler.setFormatter(logging.Formatter(_FORMAT))

                root = logging.getLogger("netwatch")
                root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
                root.handlers.clear()
                root.addHandler(handler)
                root.propagate = False

                stream_handler = logging.StreamHandler()
                stream_handler.setFormatter(logging.Formatter(_FORMAT))
                root.addHandler(stream_handler)
                _CONFIGURED = True

    return logging.getLogger(f"netwatch.{name}")
