#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
PYTHON="$ROOT/.venv/bin/python"
UVICORN="$ROOT/.venv/bin/uvicorn"

if [[ ! -x "$PYTHON" || ! -x "$UVICORN" ]]; then
  echo "Virtual environment missing."
  echo "Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

render_unit() {
  local src="$1" dst="$2"
  sed -e "s|__PROJECT_DIR__|$ROOT|g" -e "s|__USER__|$USER_NAME|g" "$src" | sudo tee "$dst" >/dev/null
}

render_unit "$ROOT/systemd/linux-digital-detective-agent.service" /etc/systemd/system/linux-digital-detective-agent.service
render_unit "$ROOT/systemd/linux-digital-detective-api.service" /etc/systemd/system/linux-digital-detective-api.service

sudo systemctl daemon-reload
sudo systemctl enable --now linux-digital-detective-agent.service linux-digital-detective-api.service

echo "Installed. Open http://127.0.0.1:8000/dashboard"
