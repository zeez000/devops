from pathlib import Path

from storage import append_jsonl, read_jsonl


def test_jsonl_round_trip(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    append_jsonl(path, {"a": 1}, max_mb=1)
    append_jsonl(path, {"a": 2}, max_mb=1)
    assert read_jsonl(path, 1) == [{"a": 2}]
