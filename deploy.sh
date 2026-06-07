#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# ── 1. 拉取最新代码 ──────────────────────────────────────────────────────────
log "拉取最新代码..."
git fetch origin
git reset --hard origin/main

# ── 2. 覆盖环境变量 ──────────────────────────────────────────────────────────
log "覆盖 .env..."
if [ ! -f backend/.env.prd ]; then
    echo "错误: backend/.env.prd 不存在，终止部署" >&2
    exit 1
fi
cp backend/.env.prd backend/.env

# ── 3. 前端构建 ──────────────────────────────────────────────────────────────
log "安装前端依赖并构建..."
cd "$SCRIPT_DIR/frontend"
npm install --prefer-offline
npm run build

# ── 4. 重启容器 ──────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR"
log "停止旧容器..."
docker compose down

log "启动新容器..."
docker compose up -d --build

log "部署完成 ✓"

