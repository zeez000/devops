.PHONY: install test agent api demo check systemd

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

test:
	PYTHONPATH=. .venv/bin/pytest -q

agent:
	.venv/bin/python collector/agent.py

api:
	.venv/bin/uvicorn api.app:app --host 127.0.0.1 --port 8000

demo:
	bash scripts/demo_incident.sh

check:
	bash scripts/check.sh

systemd:
	bash scripts/install_systemd.sh
