import json
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from storage import read_jsonl

DATA_DIR = ROOT / "data"
METRICS_FILE = DATA_DIR / "metrics.jsonl"
INCIDENTS_FILE = DATA_DIR / "incidents.jsonl"
FORENSICS_DIR = DATA_DIR / "forensics"
DASHBOARD = ROOT / "dashboard" / "index.html"

app = FastAPI(title="Linux Digital Detective API", version="2.0.0")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    if not DASHBOARD.exists():
        raise HTTPException(status_code=404, detail="Dashboard file missing")
    return FileResponse(DASHBOARD)


@app.get("/api/status")
def status():
    rows = read_jsonl(METRICS_FILE, 1)
    if not rows:
        return {"status": "waiting", "message": "No metrics yet. Start collector/agent.py."}

    latest = rows[-1]
    unhealthy = (
        latest.get("cpu_percent", 0) >= settings.cpu_threshold
        or latest.get("memory_percent", 0) >= settings.memory_threshold
        or latest.get("disk_percent", 0) >= settings.disk_threshold
        or not latest.get("service_running", True)
        or not latest.get("port_listening", True)
    )
    return {"status": "degraded" if unhealthy else "healthy", "latest": latest}


@app.get("/api/summary")
def summary():
    latest = read_jsonl(METRICS_FILE, 1)
    incidents = read_jsonl(INCIDENTS_FILE, 500)
    problem_events = [
        x
        for x in incidents
        if x.get("type", "").startswith("HIGH_")
        or x.get("type") in {"SERVICE_DOWN", "PORT_DOWN"}
    ]
    return {
        "latest": latest[-1] if latest else None,
        "incident_count": len(incidents),
        "forensic_count": (
            len(list(FORENSICS_DIR.glob("*.json"))) if FORENSICS_DIR.exists() else 0
        ),
        "recent_problem_events": len(problem_events[-50:]),
        "thresholds": {
            "cpu": settings.cpu_threshold,
            "memory": settings.memory_threshold,
            "disk": settings.disk_threshold,
        },
    }


@app.get("/api/metrics")
def metrics(limit: int = Query(120, ge=1, le=2000)):
    return read_jsonl(METRICS_FILE, limit)


@app.get("/api/incidents")
def incidents(limit: int = Query(100, ge=1, le=2000)):
    return list(reversed(read_jsonl(INCIDENTS_FILE, limit)))


@app.get("/api/forensics")
def forensics():
    if not FORENSICS_DIR.exists():
        return []
    return [
        {
            "filename": path.name,
            "size": path.stat().st_size,
            "modified": path.stat().st_mtime,
        }
        for path in sorted(FORENSICS_DIR.glob("*.json"), reverse=True)
    ]


@app.get("/api/forensics/{filename}")
def forensic_file(filename: str):
    path = (FORENSICS_DIR / filename).resolve()
    if (
        path.parent != FORENSICS_DIR.resolve()
        or not path.exists()
        or path.suffix != ".json"
    ):
        raise HTTPException(status_code=404, detail="Forensic snapshot not found")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    rows = read_jsonl(METRICS_FILE, 1)
    if not rows:
        return "# Linux Digital Detective: no metrics yet\n"

    metric = rows[-1]
    values = {
        "ldd_cpu_percent": metric.get("cpu_percent", 0),
        "ldd_memory_percent": metric.get("memory_percent", 0),
        "ldd_disk_percent": metric.get("disk_percent", 0),
        "ldd_service_running": 1 if metric.get("service_running") else 0,
        "ldd_port_listening": 1 if metric.get("port_listening") else 0,
    }
    return "\n".join(f"{key} {value}" for key, value in values.items()) + "\n"
