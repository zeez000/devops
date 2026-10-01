# Linux Digital Detective - Guide Map

## 1. What this project does

Linux Digital Detective is a small monitoring and incident-forensics system for an Ubuntu workstation or VM. It is intentionally split into two data paths:

```text
NORMAL OPERATION
Linux -> lightweight metrics -> metrics.jsonl

INCIDENT
threshold/service change -> incidents.jsonl -> forensic snapshot
```

This avoids the original problem of saving every process, socket, and journal line every five seconds.

## 2. Project map

```text
linux-digital-detective/
├── collector/
│   ├── agent.py               # main monitoring loop + incident state engine
│   └── forensic_capture.py    # detailed capture only when needed
├── api/
│   └── app.py                 # FastAPI read-only API
├── data/
│   └── .gitkeep               # runtime files are ignored by Git
├── requirements.txt
├── .gitignore
├── README.md
└── GUIDE.md
```

## 3. Install

```bash
sudo apt update
sudo apt install -y python3 python3-venv nginx

cd linux-digital-detective
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Run the monitoring agent

```bash
source .venv/bin/activate
python collector/agent.py
```

Expected output:

```text
Linux Digital Detective agent started. Press Ctrl+C to stop.
[metrics] CPU=5.2% MEM=22.3% DISK=72.5% nginx=True port80=True
```

Stop it with `Ctrl+C`.

## 5. What is monitored

Default thresholds in `collector/agent.py`:

| Signal | Trigger |
|---|---:|
| CPU | >= 85% |
| Memory | >= 85% |
| Root disk | >= 90% |
| nginx | running -> stopped / stopped -> running |
| TCP port 80 | listening -> closed / closed -> listening |

The detector is stateful. It emits a HIGH event once when a threshold is crossed, and a RECOVERED event when the system returns to normal instead of writing the same alert every five seconds.

## 6. Data files

`data/metrics.jsonl` stores small continuous measurements: CPU, memory, disk, nginx and port 80 state.

`data/incidents.jsonl` stores only incident transitions:

```text
HIGH_CPU
CPU_RECOVERED
HIGH_MEMORY
MEMORY_RECOVERED
HIGH_DISK
DISK_RECOVERED
SERVICE_DOWN
SERVICE_RECOVERED
PORT_DOWN
PORT_RECOVERED
```

`data/forensics/*.json` contains detailed snapshots created on important failure/high-resource events.

## 7. What a forensic snapshot contains

Each snapshot includes:

```text
reason + timestamp + hostname
CPU / memory / disk
15 hottest processes
listening TCP/UDP sockets
systemctl is-active nginx
last 80 journalctl entries
```

Manual test:

```bash
python collector/forensic_capture.py
ls -lh data/forensics
```

## 8. Test a service outage

Terminal 1:

```bash
python collector/agent.py
```

Terminal 2:

```bash
sudo systemctl start nginx
sleep 10
sudo systemctl stop nginx
sleep 10
sudo systemctl start nginx
```

Inspect:

```bash
tail -n 20 data/incidents.jsonl
ls -lt data/forensics | head
```

Expected flow:

```text
nginx running
    |
stop nginx
    v
SERVICE_DOWN + forensic capture
PORT_DOWN    + forensic capture
    |
start nginx
    v
SERVICE_RECOVERED
PORT_RECOVERED
```

## 9. Test high CPU safely

Run the agent, then in another terminal:

```bash
python3 -c 'while True: pass'
```

Stop the load with `Ctrl+C`. Depending on VM CPU count, one process may not push total CPU above 85%; if it does not, run one load process per vCPU in separate terminals.

Expected sequence:

```text
HIGH_CPU -> forensic snapshot -> CPU_RECOVERED
```

## 10. Run the API

Keep the agent running and start a second terminal:

```bash
source .venv/bin/activate
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

Routes:

| Route | Purpose |
|---|---|
| `GET /status` | latest metric snapshot |
| `GET /metrics?limit=100` | recent metric history |
| `GET /incidents?limit=100` | recent incidents |
| `GET /forensics` | list forensic files |
| `GET /forensics/{filename}` | inspect one snapshot |

## 11. Useful Linux investigation commands

```bash
systemctl status nginx
journalctl -u nginx --since '10 minutes ago'
ss -lntup
ps aux --sort=-%cpu | head
ps aux --sort=-%mem | head
df -h
free -h
```

## 12. Disk-space safety

```bash
du -sh data
ls -lh data
```

The new agent stores lightweight metrics instead of full snapshots continuously, so growth should be much slower than the original `events.jsonl` collector.

To archive old runtime data:

```bash
mkdir -p data/archive
mv data/metrics.jsonl data/archive/metrics-$(date +%F).jsonl
mv data/incidents.jsonl data/archive/incidents-$(date +%F).jsonl
```

Restart the agent and new files will be created automatically.

## 13. Daily workflow map

```text
1. source .venv/bin/activate
          |
2. python collector/agent.py
          |
3. create/observe an incident
          |
4. tail data/incidents.jsonl
          |
5. inspect data/forensics/<snapshot>.json
          |
6. uvicorn api.app:app --port 8000
          |
7. inspect /docs and API output
```

## 14. Next expansion path

```text
current JSONL storage
      -> SQLite/PostgreSQL
      -> Prometheus metrics endpoint
      -> Grafana dashboard
      -> Docker packaging
      -> systemd service for the agent
      -> alert notifications
      -> OpenTelemetry
      -> visual incident timeline / Linux process map
```

The important design rule is to keep the collector lightweight and capture expensive forensic detail only when an incident occurs.
