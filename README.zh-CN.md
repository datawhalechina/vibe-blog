<div align="center">

> **Alpha 内测版本：** Vibe Blog 正在快速开发中，功能和数据格式可能发生变化。请通过 [GitHub Issues](https://github.com/datawhalechina/vibe-blog/issues) 反馈问题。

<img width="220" src="docs/assets/brand/vibe-blog.png" alt="Vibe Blog 标志">

# Vibe Blog

_把复杂技术写成长文，让更多人真正读懂。_

**[English](README.md) | 简体中文**

[![Version](https://img.shields.io/badge/version-v0.1.0-4CAF50.svg)](https://github.com/datawhalechina/vibe-blog)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-42b883?logo=vuedotjs&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3-000000?logo=flask&logoColor=white)
![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-1f2937)

一个面向技术长文的 AI 写作工作台，协同完成调研、大纲、写作、代码示例、配图、审核和文档组装。

[快速开始](#快速开始) · [技术架构](#技术架构) · [测试](#测试) · [更新日志](CHANGELOG.md)

</div>

## 项目简介

Vibe Blog 是一个基于 Flask、Vue 3 和 LangGraph 多 Agent 工作流构建的应用。输入主题或补充素材，选择文章类型后，即可通过 Server-Sent Events（SSE）实时查看生成过程。最终结果保存为 Markdown，并可在 Web 界面中审阅、编辑和导出。

项目适合技术博主、开发者关系团队、教育工作者、产品团队，以及需要比简短对话回答更完整内容的学习者。

```text
主题与参考素材
        ↓
调研与知识缺口发现
        ↓
大纲规划与可选人工确认
        ↓
分章节写作、追问与审核
        ↓
代码示例与视觉素材
        ↓
文档组装、历史记录与导出
```

## 核心能力

| 领域 | 当前能力 |
| --- | --- |
| 调研 | 多轮联网调研、来源筛选、可选深度抓取和本地素材检索 |
| 规划 | 结构化大纲、受众与学习目标分析、大纲确认流程 |
| 写作 | 分章节生成、深度追问、修订、事实检查和语言清理 |
| 视觉 | Mermaid 图表，以及可选的 AI 封面、正文配图和封面动画 |
| 知识 | 文件解析、知识素材复用、文章历史和博客聚合成书 |
| 运行 | SSE 进度、任务取消、任务恢复、Dashboard 和定时生成 |
| 可观测性 | 结构化任务日志、Token 追踪和可选 Langfuse 链路追踪 |

可选和实验性集成只有在环境变量与功能开关配置后才会生效。完整配置以 [`backend/.env.example`](backend/.env.example) 为准。

## 产品预览

### 写作工作台

![Vibe Blog 首页](docs/assets/screenshots/首页图.png)

从主题开始，选择文章类型和长度，按需添加素材，并可在完整生成流程继续前确认大纲。

### 文章输出

![生成的技术文章](docs/assets/screenshots/技术博客结果图.png)

详情页在同一阅读界面中呈现 Markdown、代码高亮、Mermaid 图表、参考资料和生成媒体。

### 博客聚合成书

<table>
<tr>
<td width="50%"><img src="docs/assets/screenshots/book-reader-preview.png" alt="书籍列表"></td>
<td width="50%"><img src="docs/assets/screenshots/book-details-reader-preview.png" alt="书籍阅读器"></td>
</tr>
</table>

相关主题文章可以整理为书籍结构，并通过内置阅读器浏览。书籍扫描功能由 `BOOK_SCAN_ENABLED` 控制。

## 多 Agent 工作流

![多 Agent 架构](docs/assets/diagrams/multi-agent-architecture.png)

工作流由共享类型状态上的专业 Agent 共同完成：

| Agent 分组 | 职责 |
| --- | --- |
| Researcher 与 Search Coordinator | 收集来源、细化查询并补齐知识缺口 |
| Planner | 将证据与目标转换为结构化大纲 |
| Writer | 面向目标受众逐章节撰写内容 |
| Questioner、Reviewer 与 Fact Checker | 检查深度、质量、一致性和事实依据 |
| Coder 与 Artist | 生成代码示例、图表和可选媒体 |
| Humanizer、Voice Checker 与 Thread Checker | 优化语气、表达风格和章节连贯性 |
| Assembler 与 Summary Generator | 组装最终文档并生成摘要 |

Agent 由 LangGraph 编排，并通过共享的 Pydantic/TypedDict 状态契约通信。浏览器通过 SSE 接收进度和终态事件。

## 技术架构

| 层级 | 技术 | 用途 |
| --- | --- | --- |
| 前端 | Vue 3、Vite、Pinia、TipTap | 生成控制、实时进度、编辑、历史、书籍与 Dashboard |
| API | Flask、Pydantic | HTTP/SSE 接口、校验、任务生命周期和兼容边界 |
| 工作流 | LangGraph、LangChain | Agent 编排、重试、上下文管理和工具执行 |
| 服务层 | Python 服务包 | LLM、调研、文档、媒体、发布、审核与调度 |
| 运行产物 | 默认位于 `var/` | 日志、生成文件、上传内容、缓存和截图 |
| 持久数据 | `backend/data/` | 文章、任务、定时调度和写作会话的 SQLite 数据库 |

```text
vibe-blog/
├── backend/                 # Flask API、Agent、服务与测试
│   └── data/                # 持久化 SQLite 数据库
├── frontend/                # Vue 3 应用与 Vitest 测试
├── tests/e2e/               # Playwright 端到端场景
├── docker/                  # 本地与容器启动工具
├── docs/                    # 架构、测试文档和项目资源
└── var/                     # 本地运行数据（按需创建）
```

详细边界文档位于 [`docs/architecture/`](docs/architecture/)。

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Node.js 20 或更高版本及 npm
- 至少一个已配置文本模型提供商的 API 凭据
- 在 macOS/Linux 使用本地启动脚本时需要 `lsof`

### 1. 克隆并安装

```bash
git clone https://github.com/datawhalechina/vibe-blog.git
cd vibe-blog

python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Windows 请使用 `.venv\Scripts\activate` 激活虚拟环境。

### 2. 配置

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`。最小 OpenAI 兼容配置如下：

```env
AI_PROVIDER_FORMAT=openai
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://your-provider.example/v1
TEXT_MODEL=your-model-name
```

请勿提交 `.env` 或真实凭据。

### 3. 在 macOS、Linux 或 WSL 启动前后端

```bash
bash docker/start-local.sh
```

脚本会安装缺失的前端依赖、启动两个服务，并将日志写入 `${VIBE_RUNTIME_DIR:-var}/logs/`。

- 前端：<http://localhost:5173>
- 后端：<http://localhost:5001>

在启动终端按 `Ctrl+C` 可停止两个服务。脚本依赖 Bash 和 `lsof`，会占用 5173 和 5001 端口，并终止此前占用这些端口的进程。

### 4. 手动启动（包括 Windows）

在两个独立终端中分别运行后端和前端：

```bash
# Terminal 1
cd backend
python app.py
```

```bash
# Terminal 2
cd frontend
npm install
npm run dev
```

访问地址与上文相同。请在各自终端中停止对应进程。

### Docker

创建 `backend/.env` 后，使用仓库中的 Compose 配置启动：

```bash
docker compose -f docker/docker-compose.yml up -d --build
docker compose -f docker/docker-compose.yml ps
```

- 反向代理：<http://localhost>
- 前端直连：<http://localhost:3000>
- 后端直连：<http://localhost:5000>

当前 Nginx 配置仅在 80 端口提供 HTTP。对公网开放前，请先在 Nginx 中配置 TLS。

## 配置说明

仓库中的 [`backend/.env.example`](backend/.env.example) 是配置事实来源，主要分组如下：

| 分组 | 代表变量 | 是否必需 |
| --- | --- | --- |
| 文本模型 | `AI_PROVIDER_FORMAT`、`OPENAI_API_KEY`、`OPENAI_API_BASE`、`TEXT_MODEL` | 使用 OpenAI 兼容路径时必需 |
| 联网调研 | `ZAI_SEARCH_API_KEY`、`SERPER_API_KEY`、`JINA_API_KEY` | 可选 |
| 文档处理 | `MINERU_TOKEN`、本地素材设置 | 可选 |
| 媒体生成 | `NANO_BANANA_API_KEY`、OSS 和视频设置 | 可选 |
| 链路追踪 | `TRACE_ENABLED`、`LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY` | 可选 |
| 功能开关 | 书籍、小红书、衍生内容、深度抓取和 Agent 开关 | 可选 |

凭据应保存在 `backend/.env`。除非设置 `VIBE_RUNTIME_DIR`，生成产物、日志、上传内容和缓存位于 `var/`；持久化 SQLite 数据库仍位于 `backend/data/`。

## 测试

### 前端单元测试

```bash
cd frontend
npm test
```

### 后端测试

```bash
cd backend
python -m pytest tests/ -v
```

### 端到端测试

先启动应用，然后在仓库根目录运行：

```bash
RUN_E2E_TESTS=1 python -m pytest tests/e2e/ -v
```

设置 `E2E_HEADED=1` 可显示浏览器。截图会写入配置的运行输出区域。更多说明见 [`docs/testing/README.md`](docs/testing/README.md)。

## 参与贡献

欢迎提交 Issue 和 Pull Request：

- 通过 [GitHub Issues](https://github.com/datawhalechina/vibe-blog/issues) 报告问题或提出功能建议。
- 保持实现范围清晰，并根据改动风险补充相应测试。
- 每次提交都按仓库贡献规范同步更新 [`CHANGELOG.md`](CHANGELOG.md)。

Datawhale 项目支持和治理说明见 [Datawhale 开源项目管理委员会](https://github.com/datawhalechina/DOPMC)。

<div align="center">
<img width="260" src="docs/assets/community/project-wechat.png" alt="Vibe Blog 项目交流群二维码">
</div>

## 许可证

本项目采用[知识共享署名-非商业性使用-相同方式共享 4.0 国际许可协议](LICENSE)。
