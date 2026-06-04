from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from netwatch.aggregator.storage import init_db, insert_connection_event
from netwatch.analytics.engine import (
    get_hourly_breakdown,
    get_productivity_score,
    get_top_domains,
    get_weekly_trend,
)
from netwatch.shared.models import ConnectionEvent



def _event(ts: datetime, hostname: str, category: str) -> ConnectionEvent:
    return ConnectionEvent(
        timestamp=ts,
        pid=123,
        process_name="python",
        local_addr="127.0.0.1:5000",
        remote_addr="1.1.1.1",
        remote_port=443,
        bytes_sent=100,
        bytes_recv=200,
        hostname=hostname,
        category=category,  # type: ignore[arg-type]
    )



def test_productivity_score_and_top_domains(tmp_path: Path) -> None:
    db_path = tmp_path / "netwatch.db"
    init_db(db_path)
    base = datetime(2026, 1, 10, 10, 0, 0)

    insert_connection_event(_event(base, "github.com", "productive"), db_path)
    insert_connection_event(_event(base + timedelta(minutes=5), "github.com", "productive"), db_path)
    insert_connection_event(_event(base + timedelta(minutes=10), "youtube.com", "distracting"), db_path)

    score = get_productivity_score(date(2026, 1, 10), db_path=db_path)
    assert round(score.score, 2) == 66.67

    top = get_top_domains(limit=2, db_path=db_path)
    assert top[0].hostname == "github.com"
    assert top[0].connection_count == 2



def test_hourly_and_weekly_trend(tmp_path: Path) -> None:
    db_path = tmp_path / "netwatch.db"
    init_db(db_path)
    now = datetime.now().replace(minute=0, second=0, microsecond=0)

    insert_connection_event(_event(now, "github.com", "productive"), db_path)
    insert_connection_event(_event(now + timedelta(hours=1), "youtube.com", "distracting"), db_path)

    hourly = get_hourly_breakdown(now.date(), db_path=db_path)
    assert len(hourly) == 24
    assert hourly[now.hour].productive_seconds > 0

    trend = get_weekly_trend(weeks=1, db_path=db_path)
    assert trend
    assert any(day.day == now.date() for day in trend)
