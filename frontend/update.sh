#!/bin/bash
# Deploys the frontend/ folder of the shared repo in place (cPanel / Passenger).
# Server-only state (.env, virtualenv, logs) is protected from rsync --delete.
set -euo pipefail

REPO="https://github.com/russiantech/simplovely.git"
TMP_DIR="$(mktemp -d /tmp/simplovely-frontend-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[+] Fetching latest frontend..."
git clone --depth 1 "$REPO" "$TMP_DIR"

rsync -az --delete "$TMP_DIR/frontend/" ~/frontend/ \
    --exclude='.git' \
    --exclude='env/' \
    --exclude='.env' \
    --exclude='web/.env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='tmp/' \
    --exclude='stderr.log' \
    --exclude='passenger_wsgi.py'

cd ~/frontend
if [ -d env ]; then source env/bin/activate && pip install -r requirements.txt -q; fi
mkdir -p tmp && touch tmp/restart.txt
echo "[+] Frontend deployed at $(date)"
