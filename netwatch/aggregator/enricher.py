from __future__ import annotations

import atexit
import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from functools import lru_cache

from netwatch.shared.models import ConnectionEvent

_EXECUTOR = ThreadPoolExecutor(max_workers=4)
atexit.register(_EXECUTOR.shutdown, wait=False, cancel_futures=True)


@lru_cache(maxsize=2000)
def reverse_dns(ip_address: str) -> str:
    future = _EXECUTOR.submit(socket.gethostbyaddr, ip_address)
    try:
        hostname, _, _ = future.result(timeout=0.1)
        return hostname
    except (TimeoutError, socket.herror, socket.gaierror, OSError):
        return ""



def enrich_event(event: ConnectionEvent) -> ConnectionEvent:
    if event.hostname:
        return event
    event.hostname = reverse_dns(event.remote_addr)
    return event
