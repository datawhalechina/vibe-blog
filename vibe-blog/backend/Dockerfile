# 使用官方 Python 运行时作为基础镜像
FROM python:3.10-slim

# 构建参数：是否启用发布功能（默认禁用以减小镜像体积）
ARG ENABLE_PUBLISHER=false

# 设置工作目录
WORKDIR /app

# 设置环境变量，优化 pip 和 uv 缓存
ENV PIP_NO_CACHE_DIR=1
ENV UV_NO_CACHE=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"

# 使用阿里云镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list 2>/dev/null || true

# 安装基础系统依赖（包含 file 命令）
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    wget \
    git \
    file \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv (快速的 Python 包管理器，仅用于依赖安装)
RUN pip install --no-cache-dir uv==0.11.3 && \
    uv --version

# 条件安装 Playwright 系统依赖
RUN if [ "$ENABLE_PUBLISHER" = "true" ]; then \
    apt-get update && apt-get install -y \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpango-1.0-0 \
        libcairo2 \
        libatspi2.0-0 \
        && rm -rf /var/lib/apt/lists/*; \
    fi

# 复制 pyproject.toml 和 uv.lock 并使用 uv 安装 Python 依赖
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable && \
    uv cache clean

# 条件安装 Playwright 浏览器（仅 Chromium，约 167 MB）
RUN if [ "$ENABLE_PUBLISHER" = "true" ]; then \
    /app/.venv/bin/playwright install chromium; \
    fi

# 复制后端代码（从构建上下文的 vibe-blog/backend 目录复制）
COPY vibe-blog/backend/. .

# 暴露端口
EXPOSE 5000

# 设置应用环境变量
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# 启动应用（使用虚拟环境中的 Python 直接运行 gunicorn）
# workers=1 + threads=4: 单进程多线程，确保任务状态共享，支持4个并发请求
# timeout=600: 博客生成任务需要较长时间
CMD ["/app/.venv/bin/python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--worker-class", "gthread", "--timeout", "600", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
