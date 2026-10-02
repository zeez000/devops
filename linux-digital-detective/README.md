# Linux Digital Detective

A Linux observability and incident-forensics lab built for hands-on DevOps/SRE practice.

It now includes a lightweight monitoring agent, stateful incident detection, on-demand forensic capture, automatic data rotation, a live dashboard, a FastAPI API, Prometheus-compatible metrics, systemd services, CI tests, preflight checks, and controlled incident demos.

## What it monitors

- CPU, memory, and root-disk usage
- A configurable systemd service (default: nginx)
- A configurable TCP port (default: 80)
- Startup failures as well as runtime state changes
- Recovery transitions after incidents

## Incident evidence

High-resource events and service/port failures can capture:

- hottest processes
- listening ports
- recent journal entries
- service status
- disk usage
- memory usage
- hostname and timestamp

A cooldown prevents duplicate forensic captures during one incident burst, and old forensic snapshots are capped by retention settings.

## Quick start

```bash
git clone https://github.com/zeez000/devops.git
cd devops/linux-digital-detective

make install
make check
```

Terminal 1:

```bash
make agent
```

Terminal 2:

```bash
make api
```

Open:

```text
http://127.0.0.1:8000/dashboard
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Prometheus-style metrics:

```text
http://127.0.0.1:8000/metrics
```

## Controlled demo

With the agent running:

```bash
make demo
```

The demo stops nginx briefly and starts it again so you can watch `SERVICE_DOWN`, `PORT_DOWN`, recovery events, and forensic capture appear in the dashboard.

## Run permanently with systemd

After `make install`:

```bash
make systemd
```

Then check:

```bash
systemctl status linux-digital-detective-agent
systemctl status linux-digital-detective-api
```

## Configuration

Copy values from `.env.example` into your shell environment or service configuration. Important settings include thresholds, polling interval, monitored service/port, JSONL rotation limits, forensic cooldown, and forensic snapshot retention.

## Project map

```text
linux-digital-detective/
├── collector/          monitoring + forensic capture
├── api/                FastAPI API
├── dashboard/          live browser dashboard
├── scripts/            preflight, demo, systemd installer
├── systemd/            service unit templates
├── tests/              storage tests
├── data/               runtime files, ignored by Git
├── config.py           environment-based settings
├── storage.py          JSONL storage + rotation
├── Makefile            common commands
├── README.md
└── GUIDE.md
```

For the full usage map, troubleshooting commands, and architecture notes, read [GUIDE.md](GUIDE.md).
