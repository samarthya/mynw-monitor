from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable

from netwatch.shared.config import Settings
from netwatch.shared.models import DayStat, DomainStat, HourlyBucket, ProductivityScore


@dataclass
class _TimeRange:
    start: datetime
    end: datetime



def get_hourly_breakdown(
    target_date: date,
    start_dt: datetime | None = None,
    end_dt: datetime | None = None,
    db_path: str | Path | None = None,
) -> list[HourlyBucket]:
    start, end = _effective_range(target_date, start_dt, end_dt)
    query = """
        SELECT
            CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
            category,
            COUNT(*) * ? AS seconds
        FROM connection_events
        WHERE timestamp >= ? AND timestamp < ?
        GROUP BY hour, category
    """
    buckets = {
        hour: {
            "productive": 0,
            "distracting": 0,
            "background": 0,
            "system": 0,
            "unknown": 0,
        }
        for hour in range(24)
    }

    with _connect(db_path) as conn:
        rows = conn.execute(query, (_sample_seconds(), start.isoformat(), end.isoformat())).fetchall()

    for row in rows:
        category = row["category"]
        if category not in buckets[row["hour"]]:
            category = "unknown"
        buckets[row["hour"]][category] = int(row["seconds"])

    return [
        HourlyBucket(
            hour=hour,
            productive_seconds=values["productive"],
            distracting_seconds=values["distracting"],
            background_seconds=values["background"],
            system_seconds=values["system"],
            unknown_seconds=values["unknown"],
        )
        for hour, values in buckets.items()
    ]



def get_top_domains(
    limit: int = 20,
    category: str | None = None,
    start_dt: datetime | None = None,
    end_dt: datetime | None = None,
    db_path: str | Path | None = None,
) -> list[DomainStat]:
    where = ["hostname != ''"]
    params: list[object] = []

    if start_dt:
        where.append("timestamp >= ?")
        params.append(start_dt.isoformat())
    if end_dt:
        where.append("timestamp < ?")
        params.append(end_dt.isoformat())
    if category:
        where.append("category = ?")
        params.append(category)

    params.append(limit)
    query = f"""
        SELECT hostname, category, COUNT(*) AS connection_count,
               SUM(bytes_sent + bytes_recv) AS total_bytes
        FROM connection_events
        WHERE {' AND '.join(where)}
        GROUP BY hostname, category
        ORDER BY connection_count DESC
        LIMIT ?
    """

    with _connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        DomainStat(
            hostname=row["hostname"],
            category=row["category"],
            connection_count=int(row["connection_count"]),
            total_bytes=int(row["total_bytes"] or 0),
        )
        for row in rows
    ]



def get_productivity_score(
    target_date: date,
    start_dt: datetime | None = None,
    end_dt: datetime | None = None,
    db_path: str | Path | None = None,
) -> ProductivityScore:
    start, end = _effective_range(target_date, start_dt, end_dt)

    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT category, COUNT(*) * ? AS seconds
            FROM connection_events
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY category
            """,
            (_sample_seconds(), start.isoformat(), end.isoformat()),
        ).fetchall()

    seconds = {"productive": 0, "distracting": 0, "unknown": 0}
    for row in rows:
        category = row["category"]
        value = int(row["seconds"])
        if category in seconds:
            seconds[category] = value
        elif category not in ("background", "system"):
            seconds["unknown"] += value

    denominator = seconds["productive"] + seconds["distracting"]
    score = 0.0 if denominator == 0 else (seconds["productive"] / denominator) * 100.0

    return ProductivityScore(
        date=target_date,
        score=round(score, 2),
        productive_seconds=seconds["productive"],
        distracting_seconds=seconds["distracting"],
        unknown_seconds=seconds["unknown"],
    )



def get_weekly_trend(
    weeks: int = 4,
    start_dt: datetime | None = None,
    end_dt: datetime | None = None,
    db_path: str | Path | None = None,
) -> list[DayStat]:
    if start_dt and end_dt:
        start_day = start_dt.date()
        end_day = end_dt.date()
    else:
        end_day = date.today()
        start_day = end_day - timedelta(days=max(1, weeks) * 7 - 1)

    daily = _get_daily_counts(start_day, end_day, db_path)

    result: list[DayStat] = []
    day = start_day
    while day <= end_day:
        counts = daily.get(
            day,
            {
                "productive": 0,
                "distracting": 0,
                "background": 0,
                "system": 0,
                "unknown": 0,
            },
        )
        denominator = counts["productive"] + counts["distracting"]
        score = 0.0 if denominator == 0 else (counts["productive"] / denominator) * 100.0
        result.append(
            DayStat(
                day=day,
                productive_seconds=counts["productive"],
                distracting_seconds=counts["distracting"],
                background_seconds=counts["background"],
                system_seconds=counts["system"],
                unknown_seconds=counts["unknown"],
                score=round(score, 2),
            )
        )
        day += timedelta(days=1)

    return result



def _get_daily_counts(start_day: date, end_day: date, db_path: str | Path | None) -> dict[date, dict[str, int]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DATE(timestamp) AS day, category, COUNT(*) * ? AS seconds
            FROM connection_events
            WHERE DATE(timestamp) >= DATE(?) AND DATE(timestamp) <= DATE(?)
            GROUP BY day, category
            """,
            (_sample_seconds(), start_day.isoformat(), end_day.isoformat()),
        ).fetchall()

    out: dict[date, dict[str, int]] = {}
    for row in rows:
        day_key = date.fromisoformat(row["day"])
        out.setdefault(
            day_key,
            {
                "productive": 0,
                "distracting": 0,
                "background": 0,
                "system": 0,
                "unknown": 0,
            },
        )
        category = row["category"]
        if category not in out[day_key]:
            category = "unknown"
        out[day_key][category] += int(row["seconds"])
    return out



def _effective_range(target_date: date, start_dt: datetime | None, end_dt: datetime | None) -> _TimeRange:
    start = start_dt or datetime.combine(target_date, time.min)
    end = end_dt or (start + timedelta(days=1))
    return _TimeRange(start=start, end=end)



def _sample_seconds() -> int:
    settings = Settings.load()
    return max(1, settings.poll_interval_seconds)



def _connect(db_path: str | Path | None) -> sqlite3.Connection:
    settings = Settings.load()
    path = Path(db_path).expanduser() if db_path else settings.resolved_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn
