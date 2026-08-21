#!/bin/bash
# 从集中配置 deploy.config 渲染后端配置文件。
# 由 deploy.sh 在拉取代码之后、构建之前调用，也可单独运行。
# 前端使用相对路径（VITE_API_BASE 留空），无需写入前端配置。
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_FILE="$SCRIPT_DIR/deploy.config"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 未找到 deploy.config" >&2
    echo "请先复制模板并填写：cp deploy.config.example deploy.config" >&2
    exit 1
fi

# 载入集中配置
set -a
# shellcheck disable=SC1090
source "$CONFIG_FILE"
set +a

# ── 校验必填项 ───────────────────────────────────────────────────────────────
err=0
if [ -z "${PUBLIC_HOST:-}" ] || [ "$PUBLIC_HOST" = "http://your-domain-or-ip" ]; then
    echo "错误: PUBLIC_HOST 未设置（deploy.config）" >&2; err=1
fi
if [ -z "${DB_PASSWORD:-}" ] || [ "$DB_PASSWORD" = "change-me" ]; then
    echo "错误: DB_PASSWORD 未设置（deploy.config）" >&2; err=1
fi
[ "$err" -ne 0 ] && exit 1

# 去掉 PUBLIC_HOST 可能的结尾斜杠
PUBLIC_HOST="${PUBLIC_HOST%/}"

# 默认值兜底
DB_HOST="${DB_HOST:-mysql_db}"
DB_NAME="${DB_NAME:-fancy_agent}"
DB_USER="${DB_USER:-root}"

# 密码 URL 编码（含 @ : / 等字符会破坏 DATABASE_URL 解析）。
# 配置渲染运行在宿主机上，不应依赖项目 uv 环境；服务器只需有 Python 3。
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
else
    echo "错误: 未找到 Python 3，无法编码数据库密码" >&2
    exit 1
fi
ENC_PW="$($PYTHON_BIN -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$DB_PASSWORD")"

GEN_HEADER="# 由 configure.sh 自动生成，请勿手改；改值请编辑 deploy.config"

# ── 1. 后端 .env ──────────────────────────────────────────────────────────────
cat > "$SCRIPT_DIR/backend/.env" <<EOF
$GEN_HEADER

DATABASE_URL=mysql+asyncmy://$DB_USER:$ENC_PW@$DB_HOST:3306/$DB_NAME
OSS_URL=$PUBLIC_HOST/files
CORS_ORIGINS=$PUBLIC_HOST

SECRET_KEY=$SECRET_KEY
APP_ENCRYPTION_KEY=$APP_ENCRYPTION_KEY

UPLOAD_DIR=/data/uploads
WORKSPACE_DIR=/data/workspaces

EMAIL_ENABLED=${EMAIL_ENABLED:-false}
EMAIL_PROVIDER=${EMAIL_PROVIDER:-}
EMAIL_ADDRESS=${EMAIL_ADDRESS:-}
EMAIL_USERNAME=${EMAIL_USERNAME:-}
EMAIL_PASSWORD=${EMAIL_PASSWORD:-}
EMAIL_CHECK_INTERVAL=${EMAIL_CHECK_INTERVAL:-120}

SEARCH_PROVIDER=${SEARCH_PROVIDER:-duckduckgo}
TAVILY_API_KEY=${TAVILY_API_KEY:-}

AGENT_TOOL_CALL_LIMIT=${AGENT_TOOL_CALL_LIMIT:-15}
AGENT_MODEL_CALL_LIMIT=${AGENT_MODEL_CALL_LIMIT:-15}
EOF

# ── 2. 仓库根 .env（docker compose 自动加载，供变量插值）────────────────────────
cat > "$SCRIPT_DIR/.env" <<EOF
$GEN_HEADER
COMPOSE_PROJECT_NAME=fancy_agent_platform
DB_PASSWORD=$DB_PASSWORD
DB_NAME=$DB_NAME
EOF

echo "已生成: backend/.env, .env (PUBLIC_HOST=$PUBLIC_HOST)"
