<div align="center">

<img width="256" src="./logo/banana-vibe-blog.png">

*Turn complex tech into stories everyone can understand.*

**中文 | [English](README_EN.md)**

<p>

[![Version](https://img.shields.io/badge/version-v0.1.0-4CAF50.svg)](https://github.com/Anionex/banana-vibe-blog)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)

</p>

<b>一个基于多 Agent 架构的 AI 长文博客生成器，支持深度调研、智能配图、Mermaid 图表，<br></b>
<b>将技术知识转化为通俗易懂的科普文章，让每个人都能轻松理解复杂技术</b>

<b>🎯 降低技术写作门槛，让知识传播更简单</b>

<br>

*如果该项目对你有用, 欢迎 star🌟 & fork🍴*

<br>

</div>


## ✨ 项目缘起

你是否也曾陷入这样的困境：想写一篇技术博客，但不知道如何让非技术人员也能看懂；脑中有很多技术知识，却苦于无法用生动的比喻来解释？

传统的技术博客写作存在以下痛点：

- 1️⃣ **耗时费力**：一篇高质量的技术科普文章需要数小时甚至数天
- 2️⃣ **配图困难**：找不到合适的配图，Mermaid 图表语法复杂
- 3️⃣ **深度不足**：缺乏时间进行深度调研，内容容易流于表面
- 4️⃣ **受众单一**：难以针对不同技术水平的读者调整内容深度
- 5️⃣ **分发繁琐**：需要手动适配不同平台的格式要求

Banana Vibe Blog 应运而生，基于多 Agent 协作架构，自动完成调研、规划、写作、配图的全流程，让你专注于知识本身。

## 👨‍💻 适用场景

1. **技术博主**：快速生成高质量技术科普文章，节省写作时间
2. **技术布道者**：将复杂技术转化为通俗易懂的内容，扩大影响力
3. **教育工作者**：生成教学材料，用生活化比喻帮助学生理解
4. **产品经理**：快速了解技术概念，与开发团队更好沟通
5. **技术小白**：通过 AI 生成的科普文章，轻松入门新技术


## 🖼️ 效果展示

### 首页 - 简洁优雅的输入界面

![首页](./backend/outputs/images/首页图.png)

*输入主题，选择文章类型和长度，一键生成*

**文章类型**：
- 📚 **教程型**：手把手教学，从零到一掌握技术
- 🔧 **问题解决**：针对具体问题，提供解决方案
- 📊 **对比分析**：多方案对比，帮助技术选型

**文章长度**：

| 长度 | 章节数 | 阅读时间 | 追问深度 | 适用场景 |
|:---:|:---:|:---:|:---:|:---|
| 📄 **短文** | 3-5 章节 | ~30 分钟 | shallow | 概念介绍，快速入门 |
| 📑 **中等** | 5-8 章节 | ~60 分钟 | medium | 具体示例+步骤说明，深入学习 |
| 📚 **长文** | 8-12 章节 | ~90+ 分钟 | deep | 原理分析+数据支撑+边界情况，全面掌握 |

> 💡 **追问深度**：系统会根据文章长度自动调整内容审核标准。长文会触发更严格的深度检查，确保每个概念都有数据支撑和原理分析。

### AI 工作状态 - 实时追踪生成进度

<div align="center">
<table>
<tr>
<td><img src="./backend/outputs/images/中间运行过程图-1.png" width="400"/></td>
<td><img src="./backend/outputs/images/中间运行过程图-2.png" width="400"/></td>
</tr>
<tr>
<td align="center"><b>Step 1: 素材收集</b><br>智能搜索网络资料</td>
<td align="center"><b>Step 2-3: 大纲规划 & 内容撰写</b><br>生成结构化大纲，逐章节撰写</td>
</tr>
<tr>
<td><img src="./backend/outputs/images/中间运行过程图-4.png" width="400"/></td>
<td><img src="./backend/outputs/images/中间运行过程图-5.png" width="400"/></td>
</tr>
<tr>
<td align="center"><b>Step 4: 深度追问</b><br>检查内容深度，补充细节</td>
<td align="center"><b>Step 5: 代码生成</b><br>生成可运行的示例代码</td>
</tr>
<tr>
<td><img src="./backend/outputs/images/中间运行过程图-6.png" width="400"/></td>
<td><img src="./backend/outputs/images/中间运行过程图-7.png" width="400"/></td>
</tr>
<tr>
<td align="center"><b>Step 6: 配图生成</b><br>Mermaid 图表 + AI 配图</td>
<td align="center"><b>Step 7: 质量审核</b><br>评分并给出改进建议</td>
</tr>
<tr>
<td><img src="./backend/outputs/images/中间运行过程图-8.png" width="400"/></td>
<td><img src="./backend/outputs/images/中间运行过程图-9.png" width="400"/></td>
</tr>
<tr>
<td align="center"><b>Step 8: 文档组装</b><br>组装完整文档，提炼摘要</td>
<td align="center"><b>🎉 生成完成</b><br>自动保存 Markdown 文件</td>
</tr>
</table>
</div>

### 博客输出 - 专业排版的技术文章

![博客结果](./backend/outputs/images/技术博客结果图.png)

*完整博客内容预览，支持导出图片和下载 Markdown*

---

## 🎨 技术博客产出案例

| 博客标题 | 本地预览 | 网络博客 |
|:---|:---:|:---:|
| **Triton 部署实战指南：从设计思想到生产落地** | [Markdown](./backend/outputs/Triton%20部署实战指南_从设计思想到生产落地_20251231_034839.md) | [查看](https://blog.csdn.net/ll1042668699/article/details/156437086) |
| **vLLM推理引擎深度拆解：核心加速机制与组件原理实战指南** | [Markdown](./backend/outputs/vLLM推理引擎深度拆解_核心加速机制与组件原理实战指南_20251231_031953.md) | [查看](https://blog.csdn.net/ll1042668699/article/details/156436798) |
| **消息队列入门实战：从零搭建异步通信系统** | [Markdown](./backend/outputs/消息队列入门实战_从零搭建异步通信系统_20251230_045909.md) | [查看](https://blog.csdn.net/ll1042668699/article/details/156406666) |
| **分布式锁实战指南：30分钟掌握高并发下的资源同步控制** | [Markdown](./backend/outputs/分布式锁实战指南_30分钟掌握高并发下的资源同步控制_20251230_052151.md) | [查看](https://blog.csdn.net/ll1042668699/article/details/156406394) |
| **图解RAG进化：传统RAG vs Graph RAG架构实战对比** | [Markdown](./backend/outputs/图解RAG进化_传统RAG%20vs%20Graph%20RAG架构实战对比_20251231_042358.md) | [查看](https://blog.csdn.net/ll1042668699/article/details/156437897) |
| **Redis 快速上手实战教程：从零搭建高性能缓存系统** | [Markdown](./backend/outputs/Redis%20快速上手实战教程_从零搭建高性能缓存系统_20251230_043948.md) | [查看](https://blog.csdn.net/ll1042668699/article/details/156438172) |


## 🎯 功能介绍

### 1. 多 Agent 协作架构
基于 LangGraph 构建的多 Agent 工作流，各司其职，高效协作。
- **Researcher Agent**：深度调研，搜索网络获取最新资料
- **Planner Agent**：智能规划，生成结构清晰的文章大纲
- **Writer Agent**：内容创作，撰写通俗易懂的章节内容
- **Coder Agent**：代码生成，提供可运行的示例代码
- **Artist Agent**：智能配图，生成 Mermaid 图表和 AI 配图

### 2. 深度调研能力
- **智谱搜索集成**：自动搜索网络获取最新技术资料
- **知识提取**：从搜索结果中提取关键信息
- **引用标注**：自动标注信息来源，确保内容可信

### 3. 智能配图系统
- **Mermaid 图表**：自动生成流程图、架构图、时序图
- **AI 封面图**：基于 nano-banana-pro 生成卡通风格封面
- **上下文感知**：根据章节内容生成独特的配图

### 4. 多格式导出
- **Markdown**：标准 Markdown 格式，支持直接发布
- **图片导出**：一键将文章导出为长图
- **实时预览**：前端实时渲染 Markdown 和 Mermaid 图表


## 🤖 多 Agent 协作架构

<div align="center">

<img width="800" src="./logo/multi-agent-architecture.png">

</div>

Banana Vibe Blog 采用多 Agent 协作架构，各个 Agent 分工明确，协同高效：

- **Orchestrator Agent**（总指挥）：协调整个工作流程
- **Researcher Agent**（调研员）：深度搜索和知识提取
- **Planner Agent**（规划师）：生成结构化大纲
- **Writer Agent**（写手）：撰写章节内容
- **Coder Agent**（代码员）：生成示例代码
- **Artist Agent**（配图师）：生成 Mermaid 图表和 AI 配图
- **Reviewer Agent**（审核员）：质量检查和优化
- **Assembler Agent**（组装员）：最终文档组装

所有 Agent 共享统一的状态管理和 Prompt 模板库，确保高效协作和一致的输出质量。


## 🗺️ 开发计划

| # | 状态 | 里程碑 |
| --- | --- | --- |
| 1 | ✅ 已完成 | 多 Agent 架构实现（Researcher/Planner/Writer/Coder/Artist） |
| 2 | ✅ 已完成 | 联网搜索服务集成 |
| 3 | ✅ 已完成 | Mermaid 图表自动生成 |
| 4 | ✅ 已完成 | AI 封面架构图生成 |
| 5 | ✅ 已完成 | SSE 实时进度推送 |
| 6 | ✅ 已完成 | Markdown 实时渲染预览 |
| 7 | ✅ 已完成 | 文章导出为图片 |
| 8 | ✅ 已完成 | 多轮搜索能力 - 支持迭代式深度调研 |
| 9 | 🧭 规划中 | 自定义知识源整合 - 支持 PDF、Markdown 等多格式输入, 知识解析与深度调研 |
| 9.1 | 🧭 规划中 | 自定义知识源整合(一期) - PDF/MD/TXT 文件解析 + 知识融合 MVP |
| 9.2 | 🧭 规划中 | 自定义知识源整合(二期) - 知识分块 + 两级结构 + 图片摘要 |
| 9.3 | 🧭 规划中 | 自定义知识源整合(三期) - 多文件上传 + 文档预览 + 性能优化 |
| 10 | 🧭 规划中 | 自定义网页输入参考 - 支持用户指定参考资料来源, 从指定 URL 中下载网页内容作为知识来源. |
| 11 | 🧭 规划中 | 多源输入集成 - B 站技术视频字幕整理、多平台内容聚合 |
| 12 | 🧭 规划中 | GitHub 仓库代码解析 - 集成代码仓库，自动分析和原理解读 |
| 13 | 🧭 规划中 | 论文解读与长文翻译 - 英文论文秒变中文技术方案 |
| 14 | 🧭 规划中 | 自定义封面排版样式 - 以图生图，参考样式配置 |
| 15 | 🧭 规划中 | 灵活配图选项 - 一章一图、多章一图等多种模式 |
| 16 | 🧭 规划中 | 网站服务化 - 构建完整的在线服务平台 |
| 17 | 🧭 规划中 | 外挂知识库能力 - 接入指定知识库源(待定-如何搭建知识库) |
| 18 | 🧭 规划中 | 分享功能 - 支持文章、书籍的社交分享 |
| 19 | 🧭 规划中 | 视频讲解能力 - 将书籍和论文转化为易理解的解释视频 |
| 20 | 🧭 规划中 | 调研原文图表整合 - 增进调研原文中图与表的整合能力，将原始图表混合插入技术文章 |
| 21 | 🧭 规划中 | 播客形式输出（TTS 语音合成） |
| 22 | 🧭 规划中 | 多受众适配（高中生/儿童/职场版） |
| 23 | 🧭 规划中 | 漫画形式输出 |
| 24 | 🧭 规划中 | 自定义编辑与持续优化能力建设, 类似于代码的 agent 模式一样, 选定内容后可以语言指令去优化博客内容, 比如插入新图片等 |
| 25 | 🧭 规划中 | 自媒体平台一键发布（小红书/微信公众号/知乎） |
| 26 | 🧭 规划中 | AI 智能导读 - 思维导图 + 交互式阅读 |
| 27 | 🧭 规划中 | 博客类型细分 - 概述总览综述型、技术专题深究型、实战教程型、源码解析型等多种写作风格 |
| 28 | 🎯 终极目标 | 技术知识共创平台 - 从单一博客到共创技术书籍、问题聚合、Knowledge Graph |


## � 使用方法

### 快速开始

1. **克隆代码仓库**
```bash
git clone https://github.com/Anionex/banana-blog
cd banana-blog
```

2. **安装依赖**
```bash
cd backend
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置必要的环境变量：
```env
# AI Provider 格式配置 (openai)
AI_PROVIDER_FORMAT=openai

# OpenAI 格式配置
OPENAI_API_KEY=your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
TEXT_MODEL=gpt-4o

# 智谱搜索 API（可选，用于深度调研）
ZHIPU_API_KEY=your-zhipu-api-key

# Nano Banana Pro API（可选，用于 AI 封面图）
NANO_BANANA_API_KEY=your-nano-banana-api-key
```

4. **启动服务**
```bash
python app.py
```

5. **访问应用**
- 前端：http://localhost:5001
- API：http://localhost:5001/api


## 🛠️ 技术架构


### AI 模型与服务
| 功能 | 服务商 | 模型/API | 说明 |
|------|--------|---------|------|
| **文本生成** | 阿里云百炼 | Qwen (千问) | 用于 Agent 的文本生成和推理 |
| **联网搜索** | 智谱 | Web Search API | 用于 Researcher Agent 的深度调研 |
| **AI 配图** | Nano Banana | nano-banana-pro | 用于生成 AI 封面图和配图 |

### API 调用端点
- **文本模型**：OpenAI 兼容 API 格式
- **搜索服务**：`https://open.bigmodel.cn/api/paas/v4/web_search`
- **图片生成**：我这里使用的是grsai模型服务: `https://api.grsai.com`

### 前端技术栈
- **渲染**：原生 HTML + JavaScript
- **Markdown**：marked.js
- **代码高亮**：highlight.js
- **图表渲染**：Mermaid.js


## 📁 项目结构

```
banana-blog/
├── backend/                              # Flask 后端应用
│   ├── app.py                            # Flask 应用入口 + API 路由
│   ├── config.py                         # 配置文件
│   ├── requirements.txt                  # Python 依赖
│   ├── .env.example                      # 环境变量示例
│   ├── static/
│   │   └── index.html                    # 前端页面 (HTML + JS)
│   ├── outputs/                          # 生成的文章输出目录
│   │   └── images/                       # AI 生成的配图
│   └── services/
│       ├── llm_service.py                # LLM 服务封装
│       ├── image_service.py              # 图片生成服务 (Nano Banana)
│       ├── task_service.py               # SSE 任务管理
│       └── blog_generator/               # 博客生成器核心
│           ├── blog_service.py           # 博客生成服务入口
│           ├── generator.py              # LangGraph 工作流定义
│           ├── agents/                   # 8 个 Agent 实现
│           │   ├── researcher.py         # 调研 Agent - 联网搜索
│           │   ├── planner.py            # 规划 Agent - 大纲生成
│           │   ├── writer.py             # 写作 Agent - 内容撰写
│           │   ├── questioner.py         # 追问 Agent - 深度检查
│           │   ├── coder.py              # 代码 Agent - 示例生成
│           │   ├── artist.py             # 配图 Agent - Mermaid + AI 图
│           │   ├── reviewer.py           # 审核 Agent - 质量评分
│           │   └── assembler.py          # 组装 Agent - 文档合成
│           ├── templates/                # Jinja2 Prompt 模板
│           │   ├── researcher.j2         # 调研 Prompt
│           │   ├── planner.j2            # 规划 Prompt
│           │   ├── writer.j2             # 写作 Prompt
│           │   ├── questioner.j2         # 追问 Prompt
│           │   ├── coder.j2              # 代码 Prompt
│           │   ├── artist.j2             # 配图 Prompt
│           │   └── reviewer.j2           # 审核 Prompt
│           ├── prompts/
│           │   └── prompt_manager.py     # Prompt 渲染管理
│           ├── schemas/
│           │   └── state.py              # 共享状态定义
│           ├── post_processors/
│           │   └── markdown_formatter.py # Markdown 后处理
│           ├── utils/
│           │   └── helpers.py            # 工具函数
│           └── services/
│               └── search_service.py     # 智谱搜索服务
├── logo/                                 # Logo 资源
└── README.md
```


## 🔧 环境变量

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `FLASK_ENV` | Flask 运行环境 | development |
| `SECRET_KEY` | Flask 密钥 | banana-blog-secret-key |
| `AI_PROVIDER_FORMAT` | AI Provider 格式 (openai/gemini) | openai |
| `TEXT_MODEL` | 文本生成模型 | qwen3-max-preview |
| `OPENAI_API_KEY` | OpenAI 兼容 API Key | - |
| `OPENAI_API_BASE` | OpenAI 兼容 API 基础 URL | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| `LOG_LEVEL` | 日志级别 | INFO |
| `CORS_ORIGINS` | CORS 允许的源 | * |
| `NANO_BANANA_API_KEY` | Nano Banana 图片生成 API Key（可选） | - |
| `NANO_BANANA_API_BASE` | Nano Banana API 基础 URL | https://api.grsai.com(国内我使用的是这个模型代理网站) |
| `NANO_BANANA_MODEL` | Nano Banana 模型名称 | nano-banana-pro |
| `ZAI_SEARCH_API_KEY` | 智谱 Web Search API Key（可选） | - |
| `ZAI_SEARCH_API_BASE` | 智谱搜索 API 基础 URL | https://open.bigmodel.cn/api/paas/v4/web_search |
| `ZAI_SEARCH_ENGINE` | 智谱搜索引擎类型 | search_pro_quark |
| `ZAI_SEARCH_MAX_RESULTS` | 搜索最大结果数 | 5 |
| `ZAI_SEARCH_CONTENT_SIZE` | 搜索内容大小 | medium |
| `ZAI_SEARCH_RECENCY_FILTER` | 搜索时效过滤 | noLimit |


## 🤝 贡献指南

欢迎通过
[Issue](https://github.com/Anionex/banana-blog/issues)
和
[Pull Request](https://github.com/Anionex/banana-blog/pulls)
为本项目贡献力量！


## 📄 许可证

MIT License
