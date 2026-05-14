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

if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 is not installed on the server."
fi

if ! command -v curl >/dev/null 2>&1; then
  fail "curl is not installed on the server."
fi

DEPLOY_PATH="${DEPLOY_PATH%/}"
RELEASES_DIR="$DEPLOY_PATH/releases"
CURRENT_LINK="$DEPLOY_PATH/current"
SHARED_BACKEND_DIR="$DEPLOY_PATH/shared/backend"
SHARED_ENV="$SHARED_BACKEND_DIR/.env"
TIMESTAMP="$(date -u +%Y%m%d%H%M%S)"
RELEASE_DIR="$RELEASES_DIR/$TIMESTAMP"
PREVIOUS_CURRENT=""
MIGRATION_BACKUP_OUTPUT=""
MIGRATION_BACKUP_PATH=""

switch_current() {
  local target_dir="$1"
  local tmp_link="$DEPLOY_PATH/.current.tmp.$$"

  rm -f "$tmp_link"
  ln -s "$target_dir" "$tmp_link"
  mv -Tf "$tmp_link" "$CURRENT_LINK"
}

print_database_restore_prompt() {
  printf '[deploy][manual-action] Deployment failed after migration may have changed the SQLite database.\n' >&2
  if [[ -n "$MIGRATION_BACKUP_PATH" ]]; then
    printf '[deploy][manual-action] Migration backup created before this deploy: %s\n' "$MIGRATION_BACKUP_PATH" >&2
  else
    printf '[deploy][manual-action] Migration backup output:\n%s\n' "$MIGRATION_BACKUP_OUTPUT" >&2
  fi
  printf '[deploy][manual-action] If the previous backend cannot run against the migrated database, stop the service and restore this backup manually after confirming no training is in progress.\n' >&2
}

rollback_current() {
  local reason="$1"

  printf '[deploy][error] %s\n' "$reason" >&2
  if [[ -n "$PREVIOUS_CURRENT" && -d "$PREVIOUS_CURRENT" ]]; then
    log "Rolling current symlink back to previous release: $PREVIOUS_CURRENT"
    if ! switch_current "$PREVIOUS_CURRENT"; then
      printf '[deploy][error] Failed to switch current symlink back to previous release.\n' >&2
    elif ! sudo systemctl restart "$SERVICE_NAME"; then
      printf '[deploy][error] Backend restart failed after code rollback. Check systemd logs before continuing.\n' >&2
    fi
  else
    printf '[deploy][error] No previous current release was available for automatic code rollback.\n' >&2
  fi
  print_database_restore_prompt
}

run_health_check() {
  log "Running health check: $HEALTHCHECK_URL"
  for attempt in {1..12}; do
    if curl --fail --silent --show-error --max-time 5 "$HEALTHCHECK_URL" >/tmp/sc-training-healthcheck.out; then
      log "Health check passed."
      rm -f /tmp/sc-training-healthcheck.out
      return 0
    fi
    log "Health check attempt $attempt failed; retrying in 5 seconds."
    sleep 5
  done

  cat /tmp/sc-training-healthcheck.out 2>/dev/null || true
  return 1
}

cleanup_old_releases() {
  local releases_to_delete=()

  mapfile -t releases_to_delete < <(
    find "$RELEASES_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' \
      | sort -rn \
      | awk 'NR > 5 { $1=""; sub(/^ /, ""); print }'
  )

  for old_release in "${releases_to_delete[@]}"; do
    if [[ -n "$old_release" && "$old_release" != "$RELEASE_DIR" ]]; then
      log "Removing old release: $old_release"
      rm -rf "$old_release"
    fi
  done
}

log "Preparing release directories under: $DEPLOY_PATH"
mkdir -p "$RELEASES_DIR" "$SHARED_BACKEND_DIR"

if [[ -L "$CURRENT_LINK" ]]; then
  PREVIOUS_CURRENT="$(readlink -f "$CURRENT_LINK" || true)"
elif [[ -e "$CURRENT_LINK" ]]; then
  fail "$CURRENT_LINK exists but is not a symlink. Move it aside before using release-based deployment."
fi

if [[ ! -f "$SHARED_ENV" ]]; then
  fail "Production backend .env is missing at $SHARED_ENV. Create it before deploying."
fi

if [[ -e "$RELEASE_DIR" ]]; then
  fail "Release directory already exists: $RELEASE_DIR"
fi

log "Extracting release archive to: $RELEASE_DIR"
mkdir -p "$RELEASE_DIR"
tar -xzf "$RELEASE_ARCHIVE" -C "$RELEASE_DIR"

if [[ ! -d "$RELEASE_DIR/backend" ]]; then
  fail "Release archive is missing backend directory."
fi

if [[ ! -f "$RELEASE_DIR/frontend/dist/index.html" ]]; then
  fail "Frontend build output missing: $RELEASE_DIR/frontend/dist/index.html"
fi

log "Linking release backend .env to shared backend .env."
rm -f "$RELEASE_DIR/backend/.env"
ln -s "$SHARED_ENV" "$RELEASE_DIR/backend/.env"

log "Installing backend dependencies."
cd "$RELEASE_DIR/backend"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log "Creating pre-migration database backup."
MIGRATION_BACKUP_OUTPUT="$(python scripts/create_backup.py --trigger before_migration --label "deploy_${TIMESTAMP}" 2>&1)"
printf '%s\n' "$MIGRATION_BACKUP_OUTPUT"
MIGRATION_BACKUP_PATH="$(printf '%s\n' "$MIGRATION_BACKUP_OUTPUT" | sed -n 's/^\[BACKUP\] Created: //p' | tail -n 1)"

log "Running database migrations."
python scripts/migrate_db.py ensure
deactivate

log "Switching current symlink to: $RELEASE_DIR"
switch_current "$RELEASE_DIR"

log "Restarting backend service: $SERVICE_NAME"
if ! sudo systemctl restart "$SERVICE_NAME"; then
  rollback_current "Backend service restart failed after switching current release."
  exit 1
fi

log "Testing Nginx configuration."
if ! sudo nginx -t; then
  rollback_current "Nginx configuration test failed after switching current release."
  exit 1
fi

log "Reloading Nginx service: $NGINX_SERVICE"
if ! sudo systemctl reload "$NGINX_SERVICE"; then
  rollback_current "Nginx reload failed after switching current release."
  exit 1
fi

if ! run_health_check; then
  rollback_current "Health check failed after 12 attempts."
  exit 1
fi

cleanup_old_releases
rm -f "$RELEASE_ARCHIVE"
log "Deployment completed: $RELEASE_DIR"
