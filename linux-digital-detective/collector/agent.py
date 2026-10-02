import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from storage import append_jsonl
from collector.forensic_capture import capture

DATA_DIR = ROOT / "data"
METRICS_FILE = DATA_DIR / "metrics.jsonl"
INCIDENTS_FILE = DATA_DIR / "incidents.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def service_active(name: str) -> bool:
    result = subprocess.run(
        ["systemctl", "is-active", "--quiet", name],
        capture_output=True,
    )
    return result.returncode == 0


def port_listening(port: int) -> bool:
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == port:
                return True
    except psutil.AccessDenied:
        return False
    return False


class IncidentWriter:
    def __init__(self) -> None:
        self._last_forensic_at = 0.0

    def write(
        self,
        kind: str,
        severity: str,
        message: str,
        *,
        value=None,
        threshold=None,
        metadata: dict | None = None,
        forensic: bool = False,
    ) -> dict:
        payload = {
            "id": str(uuid.uuid4()),
            "timestamp": now_iso(),
            "type": kind,
            "severity": severity,
            "message": message,
        }
        if value is not None:
            payload["value"] = value
        if threshold is not None:
            payload["threshold"] = threshold
        if metadata:
            payload.update(metadata)

        if (
            forensic
            and time.monotonic() - self._last_forensic_at
            >= settings.forensic_cooldown_seconds
        ):
            path = capture(kind, payload, settings.monitored_service)
            payload["forensic_file"] = str(path.relative_to(ROOT))
            self._last_forensic_at = time.monotonic()

        append_jsonl(INCIDENTS_FILE, payload, settings.incidents_max_mb)
        print(f"[INCIDENT] {kind}: {message}")
        return payload


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    writer = IncidentWriter()

    states = {
        "cpu_high": False,
        "memory_high": False,
        "disk_high": False,
        "service_up": service_active(settings.monitored_service),
        "port_up": port_listening(settings.monitored_port),
    }

    print(
        "Linux Digital Detective started | "
        f"CPU>={settings.cpu_threshold}% MEM>={settings.memory_threshold}% "
        f"DISK>={settings.disk_threshold}% | "
        f"service={settings.monitored_service} port={settings.monitored_port}"
    )

    while True:
        loop_started = time.monotonic()

        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        service_up = service_active(settings.monitored_service)
        port_up = port_listening(settings.monitored_port)

        metrics = {
            "timestamp": now_iso(),
            "hostname": socket.gethostname(),
            "cpu_percent": cpu,
            "memory_percent": memory,
            "disk_percent": disk,
            "service": settings.monitored_service,
            "service_running": service_up,
            "monitored_port": settings.monitored_port,
            "port_listening": port_up,
        }
        append_jsonl(METRICS_FILE, metrics, settings.metrics_max_mb)

        print(
            f"[metrics] CPU={cpu:.1f}% MEM={memory:.1f}% DISK={disk:.1f}% "
            f"{settings.monitored_service}={service_up} "
            f"port{settings.monitored_port}={port_up}"
        )

        if cpu >= settings.cpu_threshold and not states["cpu_high"]:
            writer.write(
                "HIGH_CPU",
                "warning",
                f"CPU usage high: {cpu:.1f}%",
                value=cpu,
                threshold=settings.cpu_threshold,
                forensic=True,
            )
            states["cpu_high"] = True
        elif cpu < settings.cpu_threshold and states["cpu_high"]:
            writer.write(
                "CPU_RECOVERED",
                "info",
                f"CPU returned to normal: {cpu:.1f}%",
                value=cpu,
            )
            states["cpu_high"] = False

        if memory >= settings.memory_threshold and not states["memory_high"]:
            writer.write(
                "HIGH_MEMORY",
                "warning",
                f"Memory usage high: {memory:.1f}%",
                value=memory,
                threshold=settings.memory_threshold,
                forensic=True,
            )
            states["memory_high"] = True
        elif memory < settings.memory_threshold and states["memory_high"]:
            writer.write(
                "MEMORY_RECOVERED",
                "info",
                f"Memory returned to normal: {memory:.1f}%",
                value=memory,
            )
            states["memory_high"] = False

        if disk >= settings.disk_threshold and not states["disk_high"]:
            writer.write(
                "HIGH_DISK",
                "critical",
                f"Disk usage critical: {disk:.1f}%",
                value=disk,
                threshold=settings.disk_threshold,
                forensic=True,
            )
            states["disk_high"] = True
        elif disk < settings.disk_threshold and states["disk_high"]:
            writer.write(
                "DISK_RECOVERED",
                "info",
                f"Disk usage recovered: {disk:.1f}%",
                value=disk,
            )
            states["disk_high"] = False

        if states["service_up"] and not service_up:
            writer.write(
                "SERVICE_DOWN",
                "high",
                f"{settings.monitored_service} stopped",
                metadata={"service": settings.monitored_service},
                forensic=True,
            )
        elif not states["service_up"] and service_up:
            writer.write(
                "SERVICE_RECOVERED",
                "info",
                f"{settings.monitored_service} recovered",
                metadata={"service": settings.monitored_service},
            )
        states["service_up"] = service_up

        if states["port_up"] and not port_up:
            writer.write(
                "PORT_DOWN",
                "high",
                f"Port {settings.monitored_port} stopped listening",
                metadata={"port": settings.monitored_port},
                forensic=True,
            )
        elif not states["port_up"] and port_up:
            writer.write(
                "PORT_RECOVERED",
                "info",
                f"Port {settings.monitored_port} started listening",
                metadata={"port": settings.monitored_port},
            )
        states["port_up"] = port_up

        sleep_for = max(
            0.0,
            settings.interval_seconds - (time.monotonic() - loop_started),
        )
        time.sleep(sleep_for)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAgent stopped.")
