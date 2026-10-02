import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _rotate_if_needed(path: Path, max_mb: int) -> None:
    if not path.exists() or path.stat().st_size < max_mb * 1024 * 1024:
        return

    archive = path.parent / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path.rename(archive / f"{path.stem}-{stamp}{path.suffix}")


def append_jsonl(path: Path, payload: dict[str, Any], max_mb: int = 20) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _rotate_if_needed(path, max_mb)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")


def read_jsonl(path: Path, limit: int = 100) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    limit = max(1, min(limit, 5000))
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows
