#!/bin/bash
# Fetch main, publish atomically on success, and retry failed versions next run.
set -Eeuo pipefail
REPO_DIR="${DASHBOARD_REPO_DIR:-/opt/dashboard/repo}"
APP_DIR="${DASHBOARD_APP_DIR:-/opt/dashboard/app}"
ROOT_DIR="${DASHBOARD_ROOT_DIR:-/opt/dashboard}"
LOG_FILE="$ROOT_DIR/deploy-pull.log"
SERVICE="dashboard.service"
MARKER="$ROOT_DIR/deployed-commit"
log(){ echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" >> "$LOG_FILE"; }
exec 9>"$ROOT_DIR/deploy-pull.lock"
flock -n 9 || exit 0
cd "$REPO_DIR"
git fetch origin main --quiet 2>>"$LOG_FILE"
git reset --hard origin/main --quiet 2>>"$LOG_FILE"
TARGET=$(git rev-parse HEAD)
DEPLOYED=$(cat "$MARKER" 2>/dev/null || true)
[ "$DEPLOYED" != "$TARGET" ] || exit 0
SRC_DIR="$REPO_DIR/应用"
# Validate syntax without importing the app or reading runtime secrets.
"$ROOT_DIR/venv/bin/python" -m compileall -q "$SRC_DIR" >>"$LOG_FILE" 2>&1
mkdir -p "$ROOT_DIR/releases" "$APP_DIR"
BACKUP=$(mktemp -d "$ROOT_DIR/releases/$(date -u '+%Y%m%dT%H%M%S')-previous.XXXXXX")
rsync -a "$APP_DIR/" "$BACKUP/"
rollback(){
    log "ERROR: release $TARGET failed; restoring application files"
    rsync -ac --delete "$BACKUP/" "$APP_DIR/" || return 1
    if [ "$DEPENDENCIES_CHANGED" = 1 ] && [ -f "$BACKUP/requirements.txt" ]; then
        "$ROOT_DIR/venv/bin/pip" install -q -r "$BACKUP/requirements.txt" >>"$LOG_FILE" 2>&1 || log 'ERROR: dependency restore failed; manual inspection required'
    fi
    systemctl restart "$SERVICE" || log 'ERROR: previous service restart failed'
}
DEPENDENCIES_CHANGED=0
if ! cmp -s "$SRC_DIR/requirements.txt" "$APP_DIR/requirements.txt"; then
    DEPENDENCIES_CHANGED=1
    if ! "$ROOT_DIR/venv/bin/pip" install -q -r "$SRC_DIR/requirements.txt" >>"$LOG_FILE" 2>&1; then
        rollback;exit 1
    fi
fi
if ! rsync -ac --delete --exclude '__pycache__/' --exclude '*.pyc' --exclude 'README.md' --exclude 'tests/' --exclude 'deployment/' --exclude 'requirements-lock.txt' "$SRC_DIR/" "$APP_DIR/"; then
    rollback;exit 1
fi
if ! systemctl restart "$SERVICE"; then rollback;exit 1;fi
healthy=0
for ((attempt=1;attempt<=${DASHBOARD_HEALTH_ATTEMPTS:-10};attempt++)); do
    if curl --fail --silent --max-time 3 http://127.0.0.1:8321/dashboard/health >/dev/null; then healthy=1;break;fi
    sleep "${DASHBOARD_HEALTH_DELAY:-1}"
done
if [ "$healthy" != 1 ]; then rollback;exit 1;fi
printf '%s\n' "$TARGET" > "$MARKER.tmp"
mv "$MARKER.tmp" "$MARKER"
log "DEPLOYED $TARGET (previous=$DEPLOYED); health check passed"
