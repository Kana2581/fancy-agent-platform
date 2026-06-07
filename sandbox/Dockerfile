# 代码执行沙箱镜像。
# 注意：build context 是仓库根目录（见 docker-compose.yml 的 sandbox.build.context: .），
# 这样才能 COPY 到 backend 下的共享 runner，保持单一事实来源、不与 backend 漂移。
FROM python:3.12-slim

WORKDIR /app

COPY sandbox/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 共享 runner（纯 stdlib，无 app 依赖）+ 沙箱服务
COPY backend/app/utils/sandbox_runner.py /app/sandbox_runner.py
COPY sandbox/server.py /app/server.py

EXPOSE 9000

# 说明：容器内以 root 运行。共享 workspaces 卷由 backend(root) 创建，沙箱需写入产物，
# 切到非 root 用户会因卷 UID 不一致而无法写。隔离主要由容器边界 + 软沙箱 open() 提供；
# 容器内 root 仅在叠加内核逃逸时才危险（超出本项目威胁模型）。详见 docs/sandbox-architecture.md。
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9000"]
