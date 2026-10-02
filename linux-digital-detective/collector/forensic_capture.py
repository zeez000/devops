import json
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
FORENSICS_DIR = DATA_DIR / "forensics"
FORENSICS_DIR.mkdir(parents=True, exist_ok=True)


def _run(command: list[str], timeout: int = 5) -> dict:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.splitlines(),
            "stderr": result.stderr.splitlines(),
        }
    except Exception as exc:
        return {"returncode": None, "stdout": [], "stderr": [str(exc)]}


def top_processes(limit: int = 15) -> list[dict]:
    rows = []
    for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent"]):
        try:
            rows.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    rows.sort(
        key=lambda p: ((p.get("cpu_percent") or 0), (p.get("memory_percent") or 0)),
        reverse=True,
    )
    return rows[:limit]


def listening_ports() -> list[dict]:
    rows = []
    try:
        connections = psutil.net_connections(kind="inet")
    except psutil.AccessDenied:
        return rows

    for conn in connections:
        if conn.status != psutil.CONN_LISTEN:
            continue
        rows.append({
            "local_address": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
            "pid": conn.pid,
            "family": str(conn.family),
            "type": str(conn.type),
        })
    return rows


def capture(reason: str, metadata: dict | None = None, service: str = "nginx") -> Path:
    now = datetime.now(timezone.utc)
    payload = {
        "timestamp": now.isoformat(),
        "hostname": socket.gethostname(),
        "reason": reason,
        "metadata": metadata or {},
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "boot_time": datetime.fromtimestamp(psutil.boot_time(), timezone.utc).isoformat(),
        },
        "top_processes": top_processes(),
        "listening_ports": listening_ports(),
        "service_state": _run(["systemctl", "status", service, "--no-pager", "--lines=20"]),
        "journal": _run(["journalctl", "-n", "100", "--no-pager", "-o", "short-iso"]),
        "disk": _run(["df", "-h"]),
        "memory": _run(["free", "-h"]),
    }

    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    safe_reason = "".join(
        ch if ch.isalnum() or ch in "-_" else "_" for ch in reason.lower()
    )
    path = FORENSICS_DIR / f"{stamp}_{safe_reason}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    print(capture("manual_test"))
