#!/bin/bash
# /home/simpdinr/frontend/update.sh
# Pulls only frontend/ folder from shared repo, deploys in place

set -e

REPO="https://github.com/russiantech/simplovely.git"
TMP_DIR="/tmp/simplovely-frontend-$$"
CLONE_DIR="$TMP_DIR/frontend"

echo "[+] Fetching latest frontend..."

# Shallow clone to temp, extract frontend/
git clone --depth 1 "$REPO" "$TMP_DIR" 2>/dev/null || {
    echo "[!] Clone failed, retrying with fetch..."
    cd "$TMP_DIR" && git fetch --depth 1 && git reset --hard origin/main
}

# Sync frontend/ contents into ~/frontend (preserve local config, logs)
rsync -avz --delete "$CLONE_DIR/" ~/frontend/ \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='tmp/restart.txt' \
    --exclude='stderr.log' \
    --exclude='passenger_wsgi.py'  # keep local copy if customized

# Restart Passenger (if frontend runs under Passenger)
touch ~/frontend/tmp/restart.txt 2>/dev/null || true

# Cleanup
rm -rf "$TMP_DIR"

echo "[+] Frontend deployed at $(date)"

