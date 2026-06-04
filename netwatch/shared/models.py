from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

Category = Literal["productive", "distracting", "background", "system", "unknown"]


@dataclass
class ConnectionEvent:
    timestamp: datetime
    pid: int
    process_name: str
    local_addr: str
    remote_addr: str
    remote_port: int
    bytes_sent: int
    bytes_recv: int
    hostname: str = ""
    category: Category = "unknown"


@dataclass
class DomainStat:
    hostname: str
    category: Category
    connection_count: int
    total_bytes: int


@dataclass
class ProductivityScore:
    date: date
    score: float
    productive_seconds: int
    distracting_seconds: int
    unknown_seconds: int


@dataclass
class HourlyBucket:
    hour: int
    productive_seconds: int
    distracting_seconds: int
    background_seconds: int
    system_seconds: int
    unknown_seconds: int


@dataclass
class DayStat:
    day: date
    productive_seconds: int
    distracting_seconds: int
    background_seconds: int
    system_seconds: int
    unknown_seconds: int
    score: float
