# Linux Digital Detective - Guide Map

## 1. Install

```bash
sudo apt update
sudo apt install -y python3 python3-venv nginx make
cd ~/devops/linux-digital-detective
make install
make check
```

## 2. Run

Terminal 1:

```bash
make agent
```

Terminal 2:

```bash
make api
```

Open the live dashboard:

```text
http://127.0.0.1:8000/dashboard
```

The page refreshes every few seconds and shows CPU, memory, disk, service/port health, recent incidents, and forensic count.

## 3. Architecture

```text
Linux host
   |
   +--> lightweight metrics --------------------> data/metrics.jsonl
   |
   +--> state engine
          |
          +--> incident transitions ------------> data/incidents.jsonl
          |
          +--> forensic trigger
                   |
                   +--> processes
                   +--> sockets
                   +--> journalctl
                   +--> systemctl
                   +--> df/free
                   |
                   +----------------------------> data/forensics/*.json

FastAPI
   +--> /api/status
   +--> /api/summary
   +--> /api/metrics
   +--> /api/incidents
   +--> /api/forensics
   +--> /metrics       Prometheus format
   +--> /dashboard     browser UI
```

## 4. Default monitoring rules

| Signal | Default trigger |
|---|---:|
| CPU | >= 85% |
| Memory | >= 85% |
| Root disk | >= 90% |
| systemd service | nginx |
| TCP port | 80 |

The detector is stateful. It emits a HIGH/DOWN event once, then a RECOVERED event when the system returns to normal. If the monitored service or port is already down when the agent starts, that startup problem is recorded too.

## 5. Configuration

Environment variables:

```text
LDD_CPU_THRESHOLD
LDD_MEMORY_THRESHOLD
LDD_DISK_THRESHOLD
LDD_INTERVAL_SECONDS
LDD_METRICS_MAX_MB
LDD_INCIDENTS_MAX_MB
LDD_FORENSIC_COOLDOWN_SECONDS
LDD_FORENSIC_MAX_FILES
LDD_MONITORED_SERVICE
LDD_MONITORED_PORT
```

Example:

```bash
export LDD_CPU_THRESHOLD=80
export LDD_MONITORED_SERVICE=nginx
export LDD_MONITORED_PORT=80
make agent
```

## 6. Data safety

Metrics and incidents rotate automatically when their configured size limit is reached. Archived JSONL files go into `data/archive/`.

Forensic snapshots are capped by `LDD_FORENSIC_MAX_FILES` so they cannot grow forever.

Runtime data is excluded from Git.

## 7. Controlled nginx incident

Start the agent, then:

```bash
make demo
```

Or do it manually:

```bash
sudo systemctl start nginx
sleep 5
sudo systemctl stop nginx
sleep 10
sudo systemctl start nginx
```

Inspect:

```bash
tail -n 20 data/incidents.jsonl
ls -lt data/forensics | head
```

## 8. CPU incident test

In another terminal:

```bash
python3 -c 'while True: pass'
```

Stop with `Ctrl+C`. On multi-vCPU systems one busy process may not exceed the total threshold.

## 9. API

Useful routes:

| Route | Purpose |
|---|---|
| `GET /api/status` | latest health state |
| `GET /api/summary` | dashboard summary |
| `GET /api/metrics?limit=100` | recent metrics |
| `GET /api/incidents?limit=100` | recent incidents |
| `GET /api/forensics` | list snapshots |
| `GET /api/forensics/{filename}` | inspect one snapshot |
| `GET /metrics` | Prometheus text metrics |
| `GET /dashboard` | live dashboard |
| `GET /docs` | Swagger UI |

## 10. Run automatically at boot

```bash
make systemd
```

Then:

```bash
systemctl status linux-digital-detective-agent
systemctl status linux-digital-detective-api
journalctl -u linux-digital-detective-agent -f
```

The API binds to `127.0.0.1:8000` by default.

## 11. Developer checks

```bash
make test
python -m py_compile config.py storage.py collector/agent.py collector/forensic_capture.py api/app.py
```

A GitHub Actions workflow runs syntax checks and tests automatically when the project changes.

## 12. Useful investigation commands

```bash
systemctl status nginx
journalctl -u nginx --since '10 minutes ago'
ss -lntup
ps aux --sort=-%cpu | head
ps aux --sort=-%mem | head
df -h
free -h
```

## 13. Daily workflow

```text
make check
   |
make agent
   |
watch dashboard
   |
incident occurs
   |
inspect timeline + forensic JSON
   |
use journal/process/socket evidence
   |
verify recovery
```

## 14. Remaining expansion ideas

The current version is usable as a local Linux observability lab. Good next-stage additions would be SQLite/PostgreSQL storage, Grafana/Prometheus integration, alert delivery, OpenTelemetry, multi-host agents, and a richer incident correlation engine.
