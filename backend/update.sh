#!/bin/bash
# Deploys the backend/ folder of the shared repo in place (cPanel / Passenger).
# Server-only state is PROTECTED from rsync --delete: .env files, the virtualenv, logs and uploads.
set -euo pipefail

REPO="https://github.com/russiantech/simplovely.git"
TMP_DIR="$(mktemp -d /tmp/simplovely-backend-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[+] Fetching latest backend..."
git clone --depth 1 "$REPO" "$TMP_DIR"

rsync -az --delete "$TMP_DIR/backend/" ~/backend/ \
    --exclude='.git' \
    --exclude='env/' \
    --exclude='.env' \
    --exclude='.env.production' \
    --exclude='web/.env' \
    --exclude='web/.env.production' \
    --exclude='web/static/images/' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='tmp/' \
    --exclude='stderr.log' \
    --exclude='passenger_wsgi.py'

cd ~/backend
if [ ! -f .env ] && [ ! -f web/.env ] && [ ! -f .env.production ]; then
    echo "[!] No .env found in ~/backend: create one from .env.example before the app can start." >&2
fi

echo "[+] Installing dependencies..."
source env/bin/activate
pip install -r requirements.txt -q

echo "[+] Restarting Passenger..."
mkdir -p tmp && touch tmp/restart.txt

echo "[+] Backend deployed at $(date). Health check: curl -s https://api.simplylovely.ng/api/health"
