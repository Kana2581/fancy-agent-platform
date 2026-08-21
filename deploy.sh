#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# ── 1. 拉取最新代码（只允许快进，保护服务器现场改动）──────────────────────────
log "拉取最新代码..."
git fetch origin
DEFAULT_BRANCH="${DEPLOY_BRANCH:-$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)}"
DEFAULT_BRANCH="${DEFAULT_BRANCH#origin/}"
if [ -z "$DEFAULT_BRANCH" ]; then
    echo "错误: 无法确定部署分支，请设置 DEPLOY_BRANCH" >&2
    exit 1
fi
CURRENT_BRANCH="$(git branch --show-current)"
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "错误: 工作区存在未提交改动，已停止部署以保护现场" >&2
    echo "请先提交、暂存或清理改动后重试" >&2
    exit 1
fi
if [ "$CURRENT_BRANCH" != "$DEFAULT_BRANCH" ]; then
    log "切换到部署分支: $DEFAULT_BRANCH"
    git switch "$DEFAULT_BRANCH"
fi
git pull --ff-only origin "$DEFAULT_BRANCH"

# ── 2. 从集中配置渲染各环境变量文件 ──────────────────────────────────────────
log "渲染配置（deploy.config → 前后端 .env）..."
if [ ! -f deploy.config ]; then
    echo "错误: deploy.config 不存在，终止部署" >&2
    echo "请先复制模板并填写：cp deploy.config.example deploy.config" >&2
    exit 1
fi
bash configure.sh

# ── 3. 停止旧容器，为前端构建释放内存 ─────────────────────────────────────────
# 1.8GiB 小规格机器上，MySQL + 后端常驻会让 Vite 构建被 OOM Killer 杀掉。
log "停止旧容器（释放前端构建内存）..."
docker compose down

STACK_STARTED=false
restore_stack() {
    rc=$?
    if [ "$STACK_STARTED" = false ]; then
        log "部署失败，尝试恢复服务..."
        docker compose up -d >/dev/null 2>&1 || true
    fi
    exit "$rc"
}
trap restore_stack EXIT

# ── 4. 前端构建 ──────────────────────────────────────────────────────────────
log "安装前端依赖并构建..."
cd "$SCRIPT_DIR/frontend"
npm install --prefer-offline
npm run build

# ── 5. 重启容器 ──────────────────────────────────────────────────────────────
cd "$SCRIPT_DIR"
log "启动新容器..."
docker compose up -d --build

STACK_STARTED=true
trap - EXIT
log "部署完成 ✓"

