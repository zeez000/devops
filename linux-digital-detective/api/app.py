import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
METRICS_FILE = DATA_DIR / "metrics.jsonl"
INCIDENTS_FILE = DATA_DIR / "incidents.jsonl"
FORENSICS_DIR = DATA_DIR / "forensics"

app = FastAPI(title="Linux Digital Detective API", version="1.0.0")


def read_jsonl(path, limit=100):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
    rows = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


@app.get("/")
def root():
    return {"name": "Linux Digital Detective", "docs": "/docs"}


@app.get("/status")
def status():
    rows = read_jsonl(METRICS_FILE, 1)
    return rows[0] if rows else {"status": "no metrics yet"}


@app.get("/metrics")
def metrics(limit: int = 100):
    return read_jsonl(METRICS_FILE, min(max(limit, 1), 1000))


@app.get("/incidents")
def incidents(limit: int = 100):
    return read_jsonl(INCIDENTS_FILE, min(max(limit, 1), 1000))


@app.get("/forensics")
def forensics():
    if not FORENSICS_DIR.exists():
        return []
    return sorted(path.name for path in FORENSICS_DIR.glob("*.json"))


@app.get("/forensics/{filename}")
def forensic_file(filename: str):
    path = (FORENSICS_DIR / filename).resolve()
    if path.parent != FORENSICS_DIR.resolve() or not path.exists():
        raise HTTPException(status_code=404, detail="Forensic snapshot not found")
    return json.loads(path.read_text(encoding="utf-8"))
