from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from netwatch.shared.config import Settings
from netwatch.shared.models import Category, ConnectionEvent


@contextmanager
def get_db(db_path: str | Path | None = None):
    settings = Settings.load()
    path = Path(db_path).expanduser() if db_path else settings.resolved_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()



def init_db(db_path: str | Path | None = None) -> None:
    with get_db(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        migrations_dir = Path(__file__).resolve().parent / "migrations"
        for migration in sorted(migrations_dir.glob("*.sql")):
            version = migration.stem
            exists = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?", (version,)
            ).fetchone()
            if exists:
                continue
            sql = migration.read_text(encoding="utf-8")
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))



def insert_connection_event(event: ConnectionEvent, db_path: str | Path | None = None) -> None:
    payload = asdict(event)
    with get_db(db_path) as conn:
        conn.execute(
            """
            INSERT INTO connection_events (
                timestamp, pid, process_name, local_addr, remote_addr,
                remote_port, bytes_sent, bytes_recv, hostname, category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["timestamp"].isoformat(),
                payload["pid"],
                payload["process_name"],
                payload["local_addr"],
                payload["remote_addr"],
                payload["remote_port"],
                payload["bytes_sent"],
                payload["bytes_recv"],
                payload["hostname"],
                payload["category"],
            ),
        )



def get_cached_category(hostname: str, db_path: str | Path | None = None) -> Category | None:
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT category FROM domain_classifications WHERE hostname = ?", (hostname.lower(),)
        ).fetchone()
        if not row:
            return None
        return row["category"]



def set_cached_category(hostname: str, category: Category, db_path: str | Path | None = None) -> None:
    with get_db(db_path) as conn:
        conn.execute(
            """
            INSERT INTO domain_classifications(hostname, category, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(hostname) DO UPDATE SET
                category = excluded.category,
                updated_at = CURRENT_TIMESTAMP
            """,
            (hostname.lower(), category),
        )
