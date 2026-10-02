#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
echo "== Linux Digital Detective preflight =="
command -v python3 >/dev/null && echo "[ok] python3" || echo "[missing] python3"
command -v systemctl >/dev/null && echo "[ok] systemd" || echo "[missing] systemd"
command -v journalctl >/dev/null && echo "[ok] journalctl" || echo "[missing] journalctl"
[[ -x .venv/bin/python ]] && echo "[ok] virtualenv" || echo "[missing] run: make install"
systemctl is-active --quiet nginx && echo "[ok] nginx active" || echo "[info] nginx is not active"
ss -lnt 2>/dev/null | grep -q ':80 ' && echo "[ok] port 80 listening" || echo "[info] port 80 not listening"
df -h /
