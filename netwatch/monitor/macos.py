from __future__ import annotations

import asyncio
import subprocess
from datetime import UTC, datetime
from typing import Any

import psutil

from netwatch.monitor.base import AbstractMonitor
from netwatch.shared.logger import get_logger
from netwatch.shared.models import ConnectionEvent

logger = get_logger("monitor.macos")


class MacOSMonitor(AbstractMonitor):
    """macOS monitor using psutil and lsof.

    Full packet capture requires sudo/root and packet inspection tools.
    Connection-level monitoring through psutil and lsof works for user-owned processes without sudo.
    """

    async def run(self, queue: asyncio.Queue[ConnectionEvent]) -> None:
        while True:
            events = await self.collect_once()
            for event in events:
                await queue.put(event)
            await asyncio.sleep(self.poll_interval_seconds)

    async def collect_once(self) -> list[ConnectionEvent]:
        lsof_map = await asyncio.to_thread(self._read_lsof_process_map)
        snapshot = await asyncio.to_thread(psutil.net_connections, "inet")
        now = datetime.now(tz=UTC)

        events: list[ConnectionEvent] = []
        for conn in snapshot:
            if not conn.raddr:
                continue

            remote_ip, remote_port = _extract_ip_port(conn.raddr)
            local_ip, local_port = _extract_ip_port(conn.laddr)
            pid = conn.pid or -1
            process_name = lsof_map.get(pid, "unknown")
            if process_name == "unknown" and pid > 0:
                process_name = _safe_process_name(pid)

            events.append(
                ConnectionEvent(
                    timestamp=now,
                    pid=pid,
                    process_name=process_name,
                    local_addr=f"{local_ip}:{local_port}" if local_port else local_ip,
                    remote_addr=remote_ip,
                    remote_port=remote_port,
                    bytes_sent=0,
                    bytes_recv=0,
                )
            )

        return events

    def _read_lsof_process_map(self) -> dict[int, str]:
        command = ["lsof", "-i", "-n", "-P", "-F", "pc"]
        try:
            output = subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            logger.warning("Failed to execute lsof: %s", exc)
            return {}

        result: dict[int, str] = {}
        current_pid: int | None = None
        for line in output.splitlines():
            if not line:
                continue
            prefix = line[0]
            value = line[1:]
            if prefix == "p":
                try:
                    current_pid = int(value)
                except ValueError:
                    current_pid = None
            elif prefix == "c" and current_pid is not None and current_pid not in result:
                result[current_pid] = value
        return result



def _extract_ip_port(addr: Any) -> tuple[str, int]:
    if isinstance(addr, tuple):
        if len(addr) >= 2:
            return str(addr[0]), int(addr[1])
        if len(addr) == 1:
            return str(addr[0]), 0
    ip = getattr(addr, "ip", "")
    port = int(getattr(addr, "port", 0) or 0)
    return str(ip), port



def _safe_process_name(pid: int) -> str:
    try:
        return psutil.Process(pid).name()
    except (psutil.Error, OSError):
        return "unknown"
