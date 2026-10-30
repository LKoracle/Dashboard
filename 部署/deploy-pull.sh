#!/bin/bash
# Dashboard 自动部署脚本：从 GitHub 拉取代码，检测变化后同步并重启服务
# 用法：手动执行 或 由 crontab 每 5 分钟调用

set -uo pipefail

REPO_DIR="/opt/dashboard/repo"
APP_DIR="/opt/dashboard/app"
SRC_DIR="$REPO_DIR/应用"
LOG_FILE="/opt/dashboard/deploy-pull.log"
SERVICE="dashboard.service"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# 1. 拉取最新代码
cd "$REPO_DIR" || { log "ERROR: 无法进入 $REPO_DIR"; exit 1; }

BEFORE=$(git rev-parse HEAD)
git fetch origin main --quiet 2>>"$LOG_FILE"
git reset --hard origin/main --quiet 2>>"$LOG_FILE"
AFTER=$(git rev-parse HEAD)

# 2. 判断是否有变化
if [ "$BEFORE" = "$AFTER" ]; then
    # 无变化，静默退出（不写日志避免刷屏，可去掉下面注释以保留记录）
    # log "无更新，跳过"
    exit 0
fi

log "检测到代码更新：$BEFORE -> $AFTER"

# 3. 同步运行目录（排除 __pycache__、.gitignore、README、tests、deployment 等非运行文件）
if ! rsync -a --delete \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.gitignore' \
    --exclude 'README.md' \
    --exclude 'tests/' \
    --exclude 'deployment/' \
    --exclude 'requirements-lock.txt' \
    "$SRC_DIR/" "$APP_DIR/"; then
    log "ERROR: rsync 同步失败"
    exit 1
fi

# 4. 如有依赖变更，重新安装依赖（requirements.txt 变化时）
if [ -f "$APP_DIR/requirements.txt" ]; then
    /opt/dashboard/venv/bin/pip install -q -r "$APP_DIR/requirements.txt" >>"$LOG_FILE" 2>&1 \
        && log "依赖已同步" || log "WARN: 依赖安装失败（可能无网络）"
fi

# 5. 重启服务
if systemctl restart "$SERVICE"; then
    log "服务 $SERVICE 已重启"
else
    log "ERROR: 重启 $SERVICE 失败"
    exit 1
fi

log "部署完成"
exit 0
