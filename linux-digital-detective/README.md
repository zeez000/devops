# Linux Digital Detective

A lightweight Linux observability and incident-forensics lab built for hands-on DevOps/SRE practice.

The agent continuously records small system metrics. When a threshold is crossed or nginx/port 80 changes state, it creates an incident and captures a detailed forensic snapshot containing top processes, listening ports, recent journal entries, and nginx state.

## Architecture

```text
Linux host
   |
   +-- CPU / memory / disk metrics
   +-- process state (nginx)
   +-- network state (port 80)
   |
   v
collector/agent.py
   |
   +--> data/metrics.jsonl       lightweight history
   +--> data/incidents.jsonl     state-change incidents
   |
   +-- incident trigger --> collector/forensic_capture.py
                                |
                                +--> top processes
                                +--> listening ports
                                +--> journalctl
                                +--> nginx systemd state
                                +--> data/forensics/*.json

FastAPI --> /status /metrics /incidents /forensics
```

## Quick start

```bash
git clone https://github.com/zeez000/devops.git
cd devops/linux-digital-detective

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python collector/agent.py
```

Open a second terminal for the API:

```bash
cd ~/devops/linux-digital-detective
source .venv/bin/activate
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

Then open `http://127.0.0.1:8000/docs` in the Ubuntu browser.

## Controlled incident test

With the agent running:

```bash
sudo apt install nginx -y
sudo systemctl start nginx
sudo systemctl stop nginx
sleep 10
sudo systemctl start nginx
```

The agent should record `SERVICE_DOWN`, `PORT_DOWN`, `SERVICE_RECOVERED`, and `PORT_RECOVERED`. Down events also trigger forensic snapshots.

For the complete usage map, thresholds, API routes, and troubleshooting commands, read [GUIDE.md](GUIDE.md).
