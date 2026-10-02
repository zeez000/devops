#!/usr/bin/env bash
set -euo pipefail
echo "This controlled demo stops nginx for 10 seconds, then starts it again."
read -r -p "Continue? [y/N] " answer
[[ "$answer" =~ ^[Yy]$ ]] || exit 0
sudo systemctl start nginx
sleep 5
sudo systemctl stop nginx
sleep 10
sudo systemctl start nginx
echo "Demo complete. Check data/incidents.jsonl and data/forensics/."
