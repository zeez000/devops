import json
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

from forensic_capture import capture

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
METRICS_FILE = DATA_DIR / "metrics.jsonl"
INCIDENTS_FILE = DATA_DIR / "incidents.jsonl"

CPU_THRESHOLD = 85.0
MEMORY_THRESHOLD = 85.0
DISK_THRESHOLD = 90.0
INTERVAL_SECONDS = 5


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path, payload):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def port_listening(port):
    try:
        for conn in psutil.net_connections(kind="inet"):
            if (
                conn.status == psutil.CONN_LISTEN
                and conn.laddr
                and conn.laddr.port == port
            ):
                return True
    except psutil.AccessDenied:
        return False
    return False


def process_running(name):
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info.get("name") == name:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def incident(
    kind,
    severity,
    message,
    value=None,
    threshold=None,
    metadata=None,
    forensic=False,
):
    payload = {
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
    if forensic:
        payload["forensic_file"] = str(capture(kind, payload).relative_to(ROOT))
    append_jsonl(INCIDENTS_FILE, payload)
    print(f"[INCIDENT] {kind}: {message}")


def main():
    states = {
        "cpu_high": False,
        "memory_high": False,
        "disk_high": False,
        "nginx_up": process_running("nginx"),
        "port80_up": port_listening(80),
    }

    print("Linux Digital Detective agent started. Press Ctrl+C to stop.")

    while True:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        nginx_up = process_running("nginx")
        port80_up = port_listening(80)

        metrics = {
            "timestamp": now_iso(),
            "hostname": socket.gethostname(),
            "cpu_percent": cpu,
            "memory_percent": memory,
            "disk_percent": disk,
            "nginx_running": nginx_up,
            "port_80_listening": port80_up,
        }
        append_jsonl(METRICS_FILE, metrics)
        print(
            f"[metrics] CPU={cpu:.1f}% MEM={memory:.1f}% "
            f"DISK={disk:.1f}% nginx={nginx_up} port80={port80_up}"
        )

        if cpu >= CPU_THRESHOLD and not states["cpu_high"]:
            incident(
                "HIGH_CPU", "warning", f"CPU usage high: {cpu:.1f}%",
                cpu, CPU_THRESHOLD, forensic=True
            )
            states["cpu_high"] = True
        elif cpu < CPU_THRESHOLD and states["cpu_high"]:
            incident(
                "CPU_RECOVERED", "info",
                f"CPU returned to normal: {cpu:.1f}%", cpu
            )
            states["cpu_high"] = False

        if memory >= MEMORY_THRESHOLD and not states["memory_high"]:
            incident(
                "HIGH_MEMORY", "warning",
                f"Memory usage high: {memory:.1f}%",
                memory, MEMORY_THRESHOLD, forensic=True
            )
            states["memory_high"] = True
        elif memory < MEMORY_THRESHOLD and states["memory_high"]:
            incident(
                "MEMORY_RECOVERED", "info",
                f"Memory returned to normal: {memory:.1f}%", memory
            )
            states["memory_high"] = False

        if disk >= DISK_THRESHOLD and not states["disk_high"]:
            incident(
                "HIGH_DISK", "critical",
                f"Disk usage critical: {disk:.1f}%",
                disk, DISK_THRESHOLD, forensic=True
            )
            states["disk_high"] = True
        elif disk < DISK_THRESHOLD and states["disk_high"]:
            incident(
                "DISK_RECOVERED", "info",
                f"Disk usage recovered: {disk:.1f}%", disk
            )
            states["disk_high"] = False

        if states["nginx_up"] and not nginx_up:
            incident(
                "SERVICE_DOWN", "high", "nginx process disappeared",
                metadata={"service": "nginx"}, forensic=True
            )
        elif not states["nginx_up"] and nginx_up:
            incident(
                "SERVICE_RECOVERED", "info", "nginx process returned",
                metadata={"service": "nginx"}
            )
        states["nginx_up"] = nginx_up

        if states["port80_up"] and not port80_up:
            incident(
                "PORT_DOWN", "high", "Port 80 stopped listening",
                metadata={"port": 80}, forensic=True
            )
        elif not states["port80_up"] and port80_up:
            incident(
                "PORT_RECOVERED", "info", "Port 80 started listening",
                metadata={"port": 80}
            )
        states["port80_up"] = port80_up

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAgent stopped.")
