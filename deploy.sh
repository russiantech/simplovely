#!/bin/bash
# /home/simpdinr/deploy.sh

set -e
REPO="https://github.com/russiantech/simplovely.git"
TMP_DIR="/tmp/simplovely-deploy-$$"

# Clone fresh to temp
git clone --depth 1 "$REPO" "$TMP_DIR"

# Deploy backend
echo "[+] Deploying backend..."
rsync -avz --delete "$TMP_DIR/backend/" ~/backend/ \
  --exclude='.git' --exclude='__pycache__' --exclude='env'
cd ~/backend
source env/bin/activate
pip install -r requirements.txt -q
touch tmp/restart.txt 2>/dev/null || true

# Deploy frontend  
echo "[+] Deploying frontend..."
rsync -avz --delete "$TMP_DIR/frontend/" ~/frontend/ \
  --exclude='.git' --exclude='node_modules'
cd ~/frontend
touch tmp/restart.txt 2>/dev/null || true

# Cleanup
rm -rf "$TMP_DIR"
echo "[+] Both apps deployed successfully"