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

# ── 2. 从集中配置渲染各环境变量文件 ──────────────────────────────────────────
log "渲染配置（deploy.config → 前后端 .env）..."
if [ ! -f deploy.config ]; then
    echo "错误: deploy.config 不存在，终止部署" >&2
    echo "请先复制模板并填写：cp deploy.config.example deploy.config" >&2
    exit 1
fi
bash configure.sh

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

