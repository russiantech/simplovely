# #!/bin/bash
# # /home/simpdinr/deploy.sh

# set -e
# REPO="https://github.com/russiantech/simplovely.git"
# TMP_DIR="/tmp/simplovely-deploy-$$"

# # Clone fresh to temp
# git clone --depth 1 "$REPO" "$TMP_DIR"

# # Deploy backend
# echo "[+] Deploying backend..."
# rsync -avz --delete "$TMP_DIR/backend/" ~/backend/ \
#   --exclude='.git' --exclude='__pycache__' --exclude='env'

# cd ~/backend
# source env/bin/activate
# pip install -r requirements.txt -q
# touch tmp/restart.txt 2>/dev/null || true

# # Deploy frontend  
# echo "[+] Deploying frontend..."
# rsync -avz --delete "$TMP_DIR/frontend/" ~/frontend/ \
#   --exclude='.git' --exclude='node_modules'

# cd ~/frontend
# touch tmp/restart.txt 2>/dev/null || true

# # Cleanup
# rm -rf "$TMP_DIR"
# echo "[+] Both apps deployed successfully"




# v2 - Deploy script for backend and frontend, with optional target argument.
# Usage: ./deploy.sh [backend|frontend|all]
# Keep just one file but tell it exactly what to deploy, existing script to looks for arguments (like ./deploy.sh backend or ./deploy.sh frontend).

#!/bin/bash
set -e
REPO="https://github.com"
TMP_DIR="/tmp/simplovely-deploy-$$"
TARGET=$1 # Accepts 'backend', 'frontend', or 'all'

if [ -z "$TARGET" ]; then
  echo "Usage: $0 [backend|frontend|all]"
  exit 1
fi

# Clone fresh to temp
git clone --depth 1 "$REPO" "$TMP_DIR"

# Deploy backend if requested
if [ "$TARGET" = "backend" ] || [ "$TARGET" = "all" ]; then
  echo "[+] Deploying backend..."
  rsync -avz --delete "$TMP_DIR/backend/" ~/backend/ \
    --exclude='.git' --exclude='__pycache__' --exclude='env'

  cd ~/backend
  source env/bin/activate
  pip install -r requirements.txt -q
  touch tmp/restart.txt 2>/dev/null || true
fi

# Deploy frontend if requested
if [ "$TARGET" = "frontend" ] || [ "$TARGET" = "all" ]; then
  echo "[+] Deploying frontend..."
  rsync -avz --delete "$TMP_DIR/frontend/" ~/frontend/ \
    --exclude='.git' --exclude='node_modules'

  cd ~/frontend
  touch tmp/restart.txt 2>/dev/null || true
fi

# Cleanup
rm -rf "$TMP_DIR"
echo "[+] Deployment processing finished for: $TARGET"

