#!/usr/bin/env bash
set -Eeuo pipefail

RELEASE_ARCHIVE="${1:-}"
DEPLOY_PATH="${DEPLOY_PATH:-}"
SERVICE_NAME="${SERVICE_NAME:-sc-training-backend}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://127.0.0.1/health}"
NGINX_SERVICE="${NGINX_SERVICE:-nginx}"

log() {
  printf '[deploy] %s\n' "$*"
}

fail() {
  printf '[deploy][error] %s\n' "$*" >&2
  exit 1
}

print_diagnostics() {
  local exit_code=$?
  printf '[deploy][error] Deployment failed at line %s with exit code %s.\n' "${BASH_LINENO[0]:-unknown}" "$exit_code" >&2
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl --no-pager --full status "$SERVICE_NAME" || true
  fi
  if command -v journalctl >/dev/null 2>&1; then
    sudo journalctl -u "$SERVICE_NAME" -n 80 --no-pager || true
  fi
}

trap print_diagnostics ERR

if [[ -z "$RELEASE_ARCHIVE" ]]; then
  fail "Missing release archive path. Usage: DEPLOY_PATH=/opt/sc-training-system bash scripts/deploy.sh /tmp/sc-training-release.tgz"
fi

if [[ -z "$DEPLOY_PATH" ]]; then
  fail "Missing DEPLOY_PATH environment variable."
fi

if [[ ! -f "$RELEASE_ARCHIVE" ]]; then
  fail "Release archive not found: $RELEASE_ARCHIVE"
fi

if ! command -v rsync >/dev/null 2>&1; then
  fail "rsync is not installed on the server. Install it with: sudo apt install -y rsync"
fi

if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 is not installed on the server."
fi

if ! command -v curl >/dev/null 2>&1; then
  fail "curl is not installed on the server."
fi

WORK_DIR="$(mktemp -d /tmp/sc-training-deploy.XXXXXX)"
cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

log "Extracting release archive."
tar -xzf "$RELEASE_ARCHIVE" -C "$WORK_DIR"

log "Preparing deploy path: $DEPLOY_PATH"
mkdir -p "$DEPLOY_PATH"

log "Syncing application files without touching production env, database, backups, or virtualenv."
rsync -a --delete \
  --exclude='.git' \
  --exclude='.github' \
  --exclude='backend/.env' \
  --exclude='backend/.venv' \
  --exclude='backend/training.db*' \
  --exclude='backend/*.db' \
  --exclude='backend/*.db-*' \
  --exclude='backend/*.sqlite3' \
  --exclude='backend/backups' \
  --exclude='frontend/node_modules' \
  --exclude='logs' \
  "$WORK_DIR"/ "$DEPLOY_PATH"/

if [[ ! -f "$DEPLOY_PATH/backend/.env" ]]; then
  fail "Production backend .env is missing at $DEPLOY_PATH/backend/.env. Create it before deploying."
fi

log "Installing backend dependencies."
cd "$DEPLOY_PATH/backend"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log "Running database migrations."
python scripts/migrate_db.py ensure
deactivate

log "Verifying frontend build output."
if [[ ! -f "$DEPLOY_PATH/frontend/dist/index.html" ]]; then
  fail "Frontend build output missing: $DEPLOY_PATH/frontend/dist/index.html"
fi

log "Testing Nginx configuration."
sudo nginx -t

log "Restarting backend service: $SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

log "Reloading Nginx service: $NGINX_SERVICE"
sudo systemctl reload "$NGINX_SERVICE"

log "Running health check: $HEALTHCHECK_URL"
for attempt in {1..12}; do
  if curl --fail --silent --show-error --max-time 5 "$HEALTHCHECK_URL" >/tmp/sc-training-healthcheck.out; then
    log "Health check passed."
    rm -f /tmp/sc-training-healthcheck.out "$RELEASE_ARCHIVE"
    exit 0
  fi
  log "Health check attempt $attempt failed; retrying in 5 seconds."
  sleep 5
done

cat /tmp/sc-training-healthcheck.out 2>/dev/null || true
fail "Health check failed after 12 attempts. Check backend service, Nginx proxy, and $HEALTHCHECK_URL."
