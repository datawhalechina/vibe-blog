# 飞书机器人部署指南

## 架构

```
飞书用户 @机器人 "写 AI趋势"
        ↓
飞书服务器 POST → https://your-domain/api/feishu/webhook
        ↓
Nginx → Flask 后端 → /api/chat/* 对话式写作 API
        ↓
飞书 API ← 回复消息到群聊
```

## 多用户隔离

每个飞书用户（open_id）独立一个写作会话，互不干扰：
- 用户 A 在群里发 "写 AI趋势" → 只影响 A 的会话
- 用户 B 在同一群里发 "写 区块链" → 只影响 B 的会话
- 后端 WritingSession 按 user_id 过滤

## 本地开发

```bash
# 1. 配置 .env
FEISHU_APP_ID=cli_xxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxx

# 2. 启动后端
cd backend && python app.py

# 3. 暴露公网（二选一）
npx localtunnel --port 5001     # 免注册
ngrok http 5001                  # 需注册

# 4. 飞书后台配置 webhook URL
# https://xxxx.loca.lt/api/feishu/webhook
```

## 远程服务器部署（Docker）

### 前置条件
- 服务器有公网 IP 或域名
- 已安装 Docker + Docker Compose
- 域名已解析到服务器（推荐）

### 步骤

```bash
# 1. 克隆代码
git clone <repo> && cd vibe-blog

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env，填入飞书凭证和其他 API Key

# 3. 启动
cd docker
docker compose up -d

# 4. 飞书后台配置 webhook URL
# https://your-domain/api/feishu/webhook
# Nginx 已自动将 /api/ 代理到后端
```

### 环境变量（也可通过 docker-compose 传入）

```bash
# docker compose 启动时传入
FEISHU_APP_ID=xxx FEISHU_APP_SECRET=xxx docker compose up -d

# 或在 .env 文件中配置（推荐）
```

## 飞书开发者后台配置

1. 打开 https://open.feishu.cn/app → 创建企业自建应用
2. 添加应用能力 → **机器人**
3. 凭证与基础信息 → 复制 App ID / App Secret
4. 事件与回调 → 请求地址: `https://your-domain/api/feishu/webhook`
5. 添加事件 → `im.message.receive_v1`（接收消息 v2.0）
6. 权限管理 → 开通:
   - `im:message` — 以应用身份发消息
   - `im:message.receive_v1` — 接收消息
7. 版本管理与发布 → 创建版本 → 发布
8. 在飞书群中添加机器人

## 飞书指令

| 指令 | 功能 |
|------|------|
| `写 <主题>` | 一键生成完整博客 |
| `新话题 <主题>` | 创建写作会话 |
| `搜索` | 调研当前主题 |
| `大纲` | 生成文章大纲 |
| `写作` | 开始一键生成 |
| `预览` | 预览文章 |
| `发布` | 发布文章 |
| `状态` | 查看当前进度 |
| `列表` | 查看所有文章 |
| `帮助` | 显示帮助 |
| 直接发主题 | 自动创建并一键生成 |

## 故障排查

```bash
# 检查 webhook 是否可达
curl -X POST https://your-domain/api/feishu/webhook \
  -H "Content-Type: application/json" \
  -d '{"challenge": "test123"}'
# 应返回: {"challenge": "test123"}

# 查看后端日志
docker logs vibe-blog-backend -f --tail 50
```
