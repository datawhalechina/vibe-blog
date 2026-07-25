# Docker 部署指南

本文档说明如何使用 Docker 一键部署 vibe-blog 应用（前端 + 后端）。

## 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                      Nginx (:80)                        │
│  - /api/* → 后端 (Flask)                                │
│  - /outputs/* → 后端静态资源                            │
│  - /* → 前端 (Vue)                                      │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────┐    ┌─────────────────────┐
│   Backend (:5000)   │    │  Frontend (:3000)   │
│   Flask + Gunicorn  │    │   Vue + Nginx       │
└─────────────────────┘    └─────────────────────┘
```

## 常用命令

```bash
# 一键重部署（推荐）
./docker/redeploy.sh

# 仅重部署后端
./docker/redeploy.sh backend

# 仅重部署前端
./docker/redeploy.sh frontend

# 手动部署
cd ~/vibe-blog
git pull
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d --build
```

## 前置条件

- 安装 Docker（[下载地址](https://www.docker.com/products/docker-desktop)）
- 安装 Docker Compose（通常随 Docker Desktop 一起安装）
- 配置好 `.env` 文件（参考 `backend/.env.example`）

## 快速开始

### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并填写必要的配置：

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填写以下关键配置：

```env
# AI Provider 配置
AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# 智谱 Web Search API
ZAI_SEARCH_API_KEY=your_search_key
ZAI_SEARCH_API_BASE=https://open.bigmodel.cn/api/paas/v4/web_search

# 图片生成服务（可选）
DASHSCOPE_API_KEY=your_dashscope_key
```

### 2. 构建并启动容器

**开发环境**（仅启动后端）：

```bash
docker compose -f docker/docker-compose.yml up -d backend
```

**生产环境**（启动后端 + Nginx）：

```bash
docker compose -f docker/docker-compose.yml up -d
```

### 3. 验证部署

检查容器状态：

```bash
docker compose -f docker/docker-compose.yml ps
```

测试健康检查：

```bash
curl http://localhost:5000/health
```

## 常用命令

### 查看日志

```bash
# 查看所有服务日志
docker compose -f docker/docker-compose.yml logs -f

# 查看特定服务日志
docker compose -f docker/docker-compose.yml logs -f backend

# 查看最近 100 行日志
docker compose -f docker/docker-compose.yml logs --tail=100 backend
```

### 停止和启动

```bash
# 停止所有容器
docker compose -f docker/docker-compose.yml down

# 停止并删除数据卷
docker compose -f docker/docker-compose.yml down -v

# 重启服务
docker compose -f docker/docker-compose.yml restart backend

# 重新构建镜像
docker compose -f docker/docker-compose.yml build --no-cache
```

### 进入容器

```bash
# 进入后端容器
docker exec -it vibe-blog-backend bash

# 运行 Python 命令
docker exec -it vibe-blog-backend python -c "import sys; print(sys.version)"
```

## 生产环境部署

### 配置 SSL 证书

如果使用 Nginx（生产环境推荐），需要配置 SSL 证书：

1. 创建 `ssl` 目录：
```bash
mkdir -p ssl
```

2. 放置证书文件：
```bash
# 将你的证书放在 ssl 目录下
ssl/cert.pem      # 证书文件
ssl/key.pem       # 私钥文件
```

3. 修改 `nginx.conf` 中的 `server_name` 为你的域名

### 启动完整堆栈

```bash
docker compose -f docker/docker-compose.yml up -d
```

此时应用将在以下地址可访问：
- HTTP: `http://localhost` (自动重定向到 HTTPS)
- HTTPS: `https://localhost`

### 配置自定义域名

1. 在阿里云 DNS 中添加 A 记录，指向服务器 IP
2. 修改 `nginx.conf` 中的 `server_name` 为你的域名
3. 重启 Nginx：
```bash
docker compose -f docker/docker-compose.yml restart nginx
```

## 故障排查

### 容器无法启动

查看详细错误日志：

```bash
docker compose -f docker/docker-compose.yml logs backend
```

常见问题：
- **端口被占用**：修改 `docker-compose.yml` 中的端口映射
- **内存不足**：增加 Docker 的内存分配
- **权限问题**：确保有读写 `outputs` 和 `logs` 目录的权限

### 应用响应缓慢

检查资源使用情况：

```bash
docker stats
```

如果 CPU 或内存使用率过高，可以调整 `docker-compose.yml` 中的资源限制。

### 日志文件过大

Docker 已配置日志轮转（最大 50MB，保留 3 个文件）。如需手动清理：

```bash
docker compose -f docker/docker-compose.yml logs --tail=0 -f backend
```

## 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FLASK_ENV` | Flask 环境 | `production` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `VIBE_RUNTIME_DIR` | 统一运行目录 | `/app/var` |
| `BLOG_LOGS_DIR` | 可选的任务日志目录覆盖 | `/app/var/logs/blog_tasks` |
| `OUTPUT_FOLDER` | 可选的输出目录覆盖 | `/app/var/outputs` |
| `UPLOAD_FOLDER` | 可选的上传目录覆盖 | `/app/var/uploads` |

## 数据持久化

Docker Compose 配置了以下数据卷：

- `./var` - 日志、生成输出、上传、缓存和截图
- `./backend/data` - 博客、任务和写作会话数据库

这些目录会自动创建，数据在容器重启后保留。

## 清理资源

删除所有容器和镜像：

```bash
# 停止并删除容器
docker compose -f docker/docker-compose.yml down

# 删除镜像
docker rmi vibe-blog-backend

# 删除未使用的资源
docker system prune -a
```

## 更多帮助

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [项目 README](./README.md)
