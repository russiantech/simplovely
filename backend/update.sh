#!/bin/bash
# /home/simpdinr/backend/update.sh
# Pulls only backend/ folder from shared repo, deploys in place

set -e

REPO="https://github.com/russiantech/simplovely.git"
TMP_DIR="/tmp/simplovely-backend-$$"
CLONE_DIR="$TMP_DIR/backend"

echo "[+] Fetching latest backend..."

# Shallow clone to temp, extract backend/
git clone --depth 1 "$REPO" "$TMP_DIR" 2>/dev/null || {
    echo "[!] Clone failed, retrying with fetch..."
    cd "$TMP_DIR" && git fetch --depth 1 && git reset --hard origin/main
}

# Sync backend/ contents into ~/backend (preserve env/, logs, tmp/)
rsync -avz --delete "$CLONE_DIR/" ~/backend/ \
    --exclude='.git' \
    --exclude='env' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='tmp/restart.txt' \
    --exclude='stderr.log' \
    --exclude='passenger_wsgi.py'  # keep local copy if customized

# Install dependencies
cd ~/backend
source env/bin/activate
pip install -r requirements.txt -q

# Restart Passenger
touch tmp/restart.txt

# Cleanup
rm -rf "$TMP_DIR"

echo "[+] Backend deployed at $(date)"