# Changelog

All notable changes to the Vibe Blog project will be documented in this file.

---

## 2026-02-16

### Added
- 📋 **101.11 DeerFlow 前端交互全面对齐方案** — 系统梳理 DeerFlow vs vibe-blog 前端差异
  - 宏观交互差异 8 维度对比（InputBox / ConversationStarter / 工具栏 / 多轮对话 / Settings / Replay / 主题 / 微交互）
  - 深度研究推送样式差异 11 项（搜索骨架屏 / 搜索卡片 / 爬取卡片 / ThoughtBlock / PlanCard / ResearchCard / 活动排版 / 日志行 / 右栏工具栏 / QualityDialog / Tab）
  - vibe-blog 优势特性 9 项保留清单（终端任务头 / 时间戳 / 最小化栏 / 章节颜色标记 / 引用悬浮 / 移动端响应 / prose 排版 / 6 维评估 / 前端导出）
  - 可复用组件盘点（shadcn-vue 对照表 / 自定义组件 / Magic UI / lucide 图标 / Zustand→Pinia 映射）
  - P0/P1/P2 实施清单（9 + 6 + 4 = 19 项）
- 📋 **103.00 Vue → Next.js 改造成本评估** — 评估前端框架迁移成本（~19,766 行业务代码，6-10 天工时）

---

## 2026-02-14

### Added
- ✨ **后端 deep_thinking / background_investigation 逻辑** — `BlogService` 支持深度思考模式（LLM thinking mode）和跳过背景调查（skip_researcher）
- ✨ **writing_chunk SSE 事件** — 章节写完后推送累积 markdown，前端可实时预览
- ✨ **citations 字段持久化** — 合并 search_results + top_references（URL 去重），保存到历史记录
- ✨ **Word 导出 API** — `POST /api/export/word`，Markdown → Word(.docx) 转换，支持标题/列表/引用/段落
- ✨ **Generate 页面** — `/generate/:taskId` 路由 + `Generate.vue` 页面，集成 ProgressDrawer 实时预览
- ✨ **useTaskStream composable** — SSE 连接 + 事件处理 + 大纲确认 + 预览节流
- ✨ **useExport composable** — 多格式导出（Markdown/HTML/TXT/Word）
- ✨ **citationMatcher 工具** — 前端引用链接匹配工具函数
- ✨ **ProgressDrawer 搜索/爬取卡片** — 搜索结果卡片（favicon + 域名 + 标题，限 8 条）+ 爬取完成卡片（标题/URL/大小）+ 动画控制（前 6 张有动画，延迟上限 300ms）

### Changed
- 🔧 **enhance-topic 响应增加 original 字段** — `blog_routes.py` 返回原始 topic 便于前端对比
- 🔧 **enhance_topic 3 秒超时保护** — `blog_service.py` 用 `concurrent.futures.ThreadPoolExecutor` + `future.result(timeout=3)` 防止 LLM 阻塞
- 🔧 **enhance_topic 返回值去除引号/书名号** — `.strip('"\'《》「」')` 清理 LLM 输出格式
- 🔧 **AdvancedOptionsPanel isLoading disabled** — 所有 select/checkbox 加 `:disabled="isLoading"` 防止生成中修改参数
- 🔧 **ExportMenu 点击外部关闭菜单** — `onClickOutside` + `document.addEventListener('click')` 实现
- 🔧 **CitationTooltip Teleport + 移动端隐藏** — 渲染到 body 避免 overflow 裁剪，移动端 `< 768px` 自动隐藏
- 🔧 **CitationTooltip hover 延迟** — 200ms 延迟显示 + 100ms 延迟隐藏 + keep-visible/request-hide 事件
- 🔧 **Generate.vue 移动端 Tab 栏** — 活动日志/文章预览 Tab 切换，`< 768px` 自适应
- 🔧 **Generate.vue 双栏宽度比例** — 左栏 40% / 右栏 60%（原为固定 420px）
- 🔧 **useExport 新增 PDF/Image 导出** — 动态 `import('jspdf')` + `import('html2canvas')` + `windowHeight` 长文章支持
- 🔧 **Researcher SSE 事件推送** — `search_started`/`search_results`/`crawl_completed` 事件实时推送到前端
- 🔧 **Writer 流式写作** — `chat_stream` + `writing_chunk` SSE 事件实时推送章节内容
- 🔧 **大纲编辑确认** — `confirm_outline(action='edit')` 支持修改后大纲替换 state 重新写作
- 🔧 **任务取消清理** — 取消时清理 `_outline_events`/`_outline_confirmations` 防止线程永久阻塞
- 🔧 **Home.vue 导航** — 博客/Mini 任务创建成功后跳转到 Generate 页面，绘本任务保持原有 SSE 逻辑
- 🔧 **vite.config.ts / tsconfig.json** — 添加 `@/` 路径别名
- 🔧 **env.d.ts** — 添加 `.vue` 模块类型声明

### Tests
- ✅ **ProgressDrawer 搜索/爬取/动画测试** — 14 个新用例（搜索卡片 6 + 爬取卡片 4 + 混合渲染 1 + 动画控制 3）
- ✅ **api.test.ts** — 3 个新用例（confirmOutline accept/edit + interactive 参数传递）
- ✅ **AdvancedOptionsPanel interactive 测试** — 2 个新用例（checkbox 渲染 + emit）
- ✅ **Home.toggles.test.ts** — 2 个新用例（deepThinking/backgroundInvestigation 参数传递到 API 请求体）
- ✅ **后端 test_blog_api.py** — 新增 deep_thinking/background_investigation/interactive/confirm-outline/Word 导出测试
- ✅ **Home.enhance.test.ts** — 3 个新用例（enhance-topic API 调用/成功替换/失败处理）
- ✅ **citationMatcher.test.ts** — 引用匹配工具函数测试
- ✅ **inlineParser.test.ts** — 4 个新用例（粗体/斜体/行内代码/链接解析）
- ✅ **markdownParser.test.ts** — 5 个新用例（h1/h2/h3/列表/段落+空行跳过）
- ✅ **useExport.test.ts** — 4 个新用例（Markdown/HTML/TXT 导出 + isDownloading 状态锁）
- ✅ **throttle.test.ts** — 2 个新用例（100ms 节流 + 窗口内中间调用丢弃）
- ✅ **sse-events.test.ts** — 5 个新用例（SSE 事件解析）
- ✅ **useTaskStream.test.ts** — SSE 连接流程测试
- ✅ **AdvancedOptionsPanel isLoading 测试** — 2 个新用例（disabled/not disabled）
- ✅ **全量测试** — 26 文件 / 362 用例全部通过

---

## 2026-02-13

### Added
- ✨ **任务排队系统** (#85) — 零外部依赖（SQLite + asyncio），不引入 Redis
  - `TaskQueueManager`：asyncio.PriorityQueue + Semaphore(2) 并发控制，支持入队/取消/进度更新/事件回调
  - `TaskDB`：aiosqlite 异步 CRUD，3 张表（task_queue/scheduled_tasks/execution_history）+ 5 索引
  - Pydantic v2 数据模型：BlogTask/ExecutionRecord/SchedulerConfig 等，8 字符短 ID
  - 启动恢复：RUNNING→QUEUED 自动恢复，QUEUED 任务重新入队
- ✨ **定时调度** (#85) — APScheduler AsyncIOScheduler 封装
  - `CronParser`：中文自然语言时间 → cron/date 解析（每天/每周/每月/每N小时等 7 种模式）
  - `SchedulerService`：cron/once 触发，一次性任务自动清理，APScheduler 可选依赖优雅降级
- ✨ **发布流水线** (#85) — `PublishPipeline` 质量检查→发布→通知三步流程
- ✨ **Dashboard 任务中心** (#85) — Vue 3 前端页面
  - 统计卡片（处理中/等待中/今日完成/失败）、运行中任务进度条、等待队列、完成历史
  - 定时任务管理（新建/暂停/恢复/删除）、自然语言时间解析
  - 暗黑模式支持、3 秒轮询刷新、移动端响应式
- ✨ **REST API** (#85) — 2 个 Blueprint
  - `queue_bp`：POST/GET/DELETE /api/queue/tasks, GET /api/queue/history
  - `scheduler_bp`：CRUD /api/scheduler/tasks, pause/resume, parse-schedule
- ✅ 56 个单元测试全部通过（models 8 + db 10 + manager 15 + cron_parser 11 + pipeline 6 + scheduler 6）
- ✅ Dashboard E2E 测试 TC-13（7 个用例：页面加载/统计卡片/定时任务表单/暗黑模式/API 请求/导航）
- ✨ **LLM 响应截断自动扩容** (#37.32) — max_tokens 自动扩容 + 智能重试，解决长文生成截断问题
- ✨ **上下文长度动态估算与自动回退** (#37.33) — 根据模型上下文窗口动态估算可用空间，超限自动降级
- ✨ **统一 Token 追踪与成本分析** (#37.31) — TokenTracker 全局追踪 LLM 调用 token 用量与费用
- ✨ **结构化任务日志** (#37.08) — BlogTaskLog + StepLog + StepTimer，每步耗时精确记录
- ✨ **性能聚合统计** (#37.08) — BlogPerformanceSummary 汇总各阶段耗时、token、成本
- ✨ **SSE 流式事件增量优化** (#37.34) — 事件去重、增量推送、断线重连
- ✨ **统一 ToolManager** (#37.09) — 工具注册、超时保护、黑名单、调用日志 + 参数自动修复
- ✨ **多提供商 LLM 客户端工厂** (#37.29) — OpenAI/Anthropic/DeepSeek/Qwen/智谱统一接口
- ✨ **上下文压缩策略** (#37.06) — 工具结果保留、搜索裁剪、多级降级
- ✨ **重复查询检测与回滚保护** (#37.04) — QueryDeduplicator + SmartSearch 集成
- ✨ **博客生成分层架构** (#37.12) — 7 层定义、LayerValidator、YAML→JSON 迁移、DeclarativeEngine
- ✨ **Skill 与 Agent 混合能力** (#37.14) — SkillRegistry + SkillExecutor
- ✨ **博客衍生物体系** (#37.16) — MindMap/Flashcard/StudyNote Skills
- ✨ **推理引擎 Extended Thinking** (#37.03) — thinking_config、Anthropic API 集成
- ✨ **写作模板体系** (#37.13) — TemplateLoader/StyleLoader/PromptComposer + 6 模板 6 风格预置
- ✨ **Serper Google 搜索集成** (#75.02) — API 调用、重试、SmartSearch 路由
- ✨ **搜狗搜索集成** (#75.07) — 腾讯云 SearchPro API、微信公众号标记、SmartSearch 路由
- ✨ **Jina 深度抓取** (#75.03) — JinaReader + HttpxScraper 降级 + DeepScraper 统一入口
- ✨ **知识空白检测与多轮搜索** (#75.04) — KnowledgeGapDetector + MultiRoundSearcher
- ✨ **Searcher 智能搜索改造** (#71) — 扩展源 + SourceCurator + 健康检查
- ✨ **Crawl4AI 主动爬取** (#75.06) — LocalMaterialStore + BlogCrawler
- ✅ Playwright E2E 测试套件 — 12 个测试用例覆盖 TC-1~TC-12
- ✨ **飞书机器人集成** — 对话式写作入口，私聊/群聊 @bot 触发
  - `feishu_routes.py`：Webhook 事件订阅、意图解析、vibe-blog API 调用、卡片消息回复
  - 富文本卡片消息：帮助/任务启动/进度/完成/失败 5 种卡片，lark_md 格式
  - 进度轮询推送：后台线程轮询 SSE 任务状态，自动推送进度到飞书
  - 模板优先降级：支持 template_id + variables，无模板时降级为代码构建卡片
  - 多用户隔离：按 open_id 隔离写作会话
  - Docker 部署支持：docker-compose.yml 添加飞书环境变量
- 📄 **飞书部署文档** — `docs/feishu-deploy.md` 本地开发/远程部署/多用户隔离/故障排查

### Changed
- 🔧 **Dashboard 任务中心增强** — 新增失败/已取消任务列表、进度百分比显示、cancelled_count 统计
- 🔧 **任务排队恢复策略** — 服务重启时 RUNNING/QUEUED 任务标记为 FAILED（而非重新入队），避免僵尸任务
- 🔧 **生成进度同步到排队系统** — `update_queue_progress()` 桥接 SSE 进度到 Dashboard 进度条
- 🔧 **Humanizer 改写重试** — JSON 解析失败时最多重试 3 次，最终失败保留原文
- 🔧 **Planner 素材分配日志** — 打印每个章节的素材分配情况
- 🔧 **LLMClientAdapter** — 透传 token_tracker 属性
- 🔧 **WritingSession 用户隔离** — get/list 支持 user_id 过滤
- 🔧 **WhatsApp 网关启动脚本** — start-local.sh 支持 ENABLE_WHATSAPP 可选启动
- 🔧 **mini 模式默认开启 humanizer/fact_check** — StyleProfile.mini() 调整

### Fixed
- 🐛 **Humanizer 空响应崩溃** — 增加空字符串检查，避免 JSON 解析异常

---

## 2026-02-12

### Added
- ✨ **首页 Fullpage 卡片滑动** — Hero 首屏与历史记录区域之间整屏滑动切换，支持鼠标滚轮、触摸滑动、键盘方向键、侧边圆点指示器；第二屏内容可正常滚动，滚到顶部上滑回首屏
- ✨ **Searcher 智能搜索改造** (#71) — 新增 5 个 AI 博客源（DeepMind/Meta AI/Mistral/xAI/MS Research），AI 话题自动增强，StyleProfile.enable_ai_boost 控制
- ✨ **Planner 章节编号体系** — 中文数字主章节编号（一、二、三...）+ 阿拉伯数字子标题（1.1/1.2）+ 子子标题（1.1.1），subsections 结构化规划
- ✨ **Assembler 多级目录** — extract_subheadings 支持 ###/#### 多级标题提取，assembler_header.j2 渲染嵌套可点击目录

### Fixed
- 🐛 **LLM 429 速率限制防护** — 全局请求限流器 + max_retries=6 + 应用层 429 重试（5s/10s 退避），chat/chat_stream/chat_with_image 全覆盖
- 🐛 **Planner JSON 截断修复增强** — 3 轮渐进式修复策略（直接补全→回退截断→再补全），处理未闭合字符串和不完整 key-value
- 🐛 **博客表格不渲染** — BlogDetailContent.vue 添加 table/th/td 完整 CSS 样式
- 🐛 **[IMAGE:] 占位符未替换** — artist.py Mermaid 图片关联条件修复，render_method=='mermaid' 无需 rendered_path 也关联到章节
- 🐛 **ASCII 拓扑图被破坏** — _fix_markdown_separators 改为逐行扫描，跳过代码块内 `---`，同时处理 `---##` 连写拆分（前后端同步修复）
- 🐛 **chat_stream 缺少 response_format 透传** — LLMClientAdapter.chat_stream 新增 response_format 参数

---

## 2026-02-11

### Added
- ✨ **Humanizer Agent 去AI味** (#63) — 独立后处理 Agent，两步流程（评分→改写），24 条去 AI 味规则，支持环境变量开关
- ✨ **ThreadChecker + VoiceChecker 一致性检查** (#70.2) — 全文视角检查叙事连贯性（术语/交叉引用/Claim矛盾）和语气统一性（人称/正式度），并行执行
- ✨ **Mermaid 语法自动修复管线** (#69.01) — `_sanitize_mermaid` → `_validate_mermaid` → `_repair_mermaid` 三步管线，正则预处理 + LLM 修复（最多 2 次重试）
- ✨ **FactCheck Agent 事实核查** (#65) — 从全文提取可验证 Claim，与 assigned_materials 交叉验证，输出核查报告（overall_score + claims + fix_instructions）
- ✨ **TextCleanup 确定性清理管道** (#67) — 纯正则预处理 AI 痕迹（填充词/空洞强化词/Meta评论/冗余短语），降低 Humanizer 工作量
- ✨ **SummaryGenerator 博客导读+SEO** (#67) — TL;DR 导读 + SEO 关键词 + 社交摘要 + Meta Description，集成到工作流 assembler→summary_generator→END
- ✨ **扩展搜索源** (#50) — 新增 7 个专业搜索源（HuggingFace/GitHub/Google AI/Dev.to/StackOverflow/AWS/Microsoft），LLM 智能路由 + 规则兜底
- ✨ **Artist 图片预算控制** (#69) — IMAGE_BUDGET 按 target_length 限制总图片数，优先级裁剪（outline > placeholder > missing_diagram），caption 质量改进

### Refactored
- ♻️ **Reviewer 精简** (#66) — 从 417 行巨型 Prompt 精简为 ~90 行，聚焦结构完整性 + verbatim 数据 + 学习目标覆盖，已被 Thread/FactCheck/Humanizer 覆盖的职责移除
- ♻️ **SharedState 架构治理** (#68) — 新增 factcheck_report/seo_keywords/social_summary/meta_description/section_images 字段，ReviewIssue.issue_type 更新为 4 种精简类型

### Fixed
- 🐛 全局 `_extract_json` 修复 — 解决 qwen3-max thinking mode 将 JSON 包裹在 markdown code block 中导致解析失败的问题，涉及 reviewer/artist/search_router/summary_generator 等多个 Agent

---

## 2026-02-10

### Added
- ✨ **Phase 1 核心骨架实施** (#70.1) — Planner + Writer 全面增强
  - Step 1.1 叙事流设计：6 种叙事模式 + narrative_flow + narrative_role
  - Step 1.2 字数分配规则：按 narrative_role 推荐比例分配 target_words
  - Step 1.4 核心问题指导：core_question 设计规则 + 推荐模板
  - Step 1.5 扩展输出 JSON Schema：统一定义所有新字段
  - Step 1.6 planner.py 解析新字段：setdefault() 向后兼容
  - Step 1.7 writer.j2 完整重构（289行）：核心问题/素材使用/字数目标/叙事策略/散文优先/Claim校准/去AI味黑名单
  - Step 1.8 writer.py 接收新字段：narrative_mode/narrative_flow 传递 + assigned_materials 富化
- ✨ **搜索结果提炼与缺口分析** — distill() 结构化提炼 + analyze_gaps() 缺口分析，含语义去重
- ✨ **素材预分配到章节** — Planner 为每章分配 1-3 条精选素材，引入 {source_NNN} 占位符

### Fixed
- 🐛 修复 target_words JSON schema 语法错误
- 🐛 修复 blog_service outline_complete 事件缺少完整 sections 数据

---

## 2026-02-08

### Added
- ✨ **Type×Style 二维配图系统**（参考 46 号方案）
  - 新增 6 种 illustration_type 模板：infographic、scene、flowchart、comparison、framework、timeline
  - 新增 `type_signals.py` 内容信号自动推荐模块，基于关键词和正则匹配推荐 illustration_type
  - `ImageStyleManager` 支持二维渲染（先 Type 骨架 → 再 Style 皮肤）、兼容性检查、自动降级
  - `styles.yaml` 增加 types、best_types、compatibility 配置
  - `artist.j2` / `planner.j2` 模板增加 illustration_type 字段
  - `prompt_manager.py` 的 `render_artist()` 支持 illustration_type 参数
  - `artist.py` 的 `generate_image` / `render_ai_image` / `run` 方法支持 illustration_type
  - 完全向后兼容：illustration_type 为空时退回纯 Style 模式
- ✅ Playwright 浏览器 E2E 自动化测试脚本 (`backend/tests/test_browser_e2e.py`)
  - 六步流程：打开首页 → 输入主题 → 选配图风格 → 点击生成 → 等待完成 → 验证结果
  - 自动捕获 task_id、博客详情页 URL、Markdown 文件路径
  - 支持 headed/headless 模式、自定义主题和风格、超时配置

### Fixed
- 🐛 后端 `complete` 事件缺少 `id` 字段，导致前端生成完成后不自动跳转到博客详情页
  - `blog_service.py` 的 `send_event('complete', ...)` 添加 `'id': task_id`
  - 前端 `Home.vue` 依赖 `d.id` 执行 `router.push('/blog/${d.id}')`
- 🐛 **Markdown 分隔线排版修复**：修复 `---##` 连写和文本紧挨 `---` 导致 Setext 标题误判（加粗）的问题
  - 后端 `assembler.py` 新增 `_fix_markdown_separators()` 后处理，确保所有 `---` 前后都有空行
  - 前端 `useMarkdownRenderer.ts` 新增 `fixMarkdownSeparators()` 预处理，修复已有文章数据的渲染

---

## 2026-02-07

### Refactored
- ♻️ 后端 `app.py` 拆分为 Blueprint 模块化架构（2729 行 → ~175 行）
  - 新增 `routes/` 包，含 8 个 Blueprint：static、transform、task、blog、history、book、xhs、publish
  - 新增 `logging_config.py`：日志配置抽取
  - 新增 `exceptions.py`：自定义异常层级（VibeBlogError / ValidationError / NotFoundError / ServiceUnavailableError）
  - 更新 `conftest.py` 和测试文件的 monkeypatch 路径适配 Blueprint 模块
  - `pytest.ini` 新增 `--cov=routes` 覆盖范围
  - 零功能变更，全部 110 个测试通过

### Added
- ✨ **Langfuse LLM 调用链路追踪**（参考 47 号方案）
  - 集成 Langfuse Cloud，通过 `CallbackHandler` 自动追踪 LangGraph 工作流
  - 支持 Trace 视图、调用树、耗时统计、Token 费用分析
  - 环境变量 `TRACE_ENABLED=true` 开启，`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` 配置
  - 每个 Agent 节点（Planner/Writer/Deepener/Coder/Reviewer/Artist）独立追踪
- ✨ 底部 `scroll ↓` 提示动画，引导用户下滑查看历史记录
- ✨ 滚动触发 `terminal-boot` 淡入上滑动画（0.8s）
- ✨ 卡片打字机效果，每张卡片依次出现（间隔 120ms）
- ✨ 高级选项面板绝对定位浮层 + CSS `slide-down` 过渡动画
- ✅ 完成前端 P1 组件集成测试
- ✅ Pinia Store 集成测试（37 tests, 92.82% 覆盖率）
- ✅ DatabaseService 单元测试（24 tests, 54.70% 覆盖率）

### Changed
- 🎨 首屏占满视口（PPT 翻页式），Hero + 输入框 flex 垂直居中
- 🎨 execute 按钮移至输入框右侧，底部工具栏精简
- 🎨 分页组件替换为 SHOW MORE 追加加载模式
- 🎨 统一前端配色方案，对齐 main 分支

### Fixed
- 🐛 Langfuse `ThreadPoolExecutor` 上下文丢失：追踪模式下改为串行执行，直接调用 `@observe` 装饰的方法以保持上下文链路
  - 涉及 `writer.py`、`questioner.py`、`coder.py`、`artist.py`、`generator.py`
  - 添加 `_should_use_parallel()` 方法，`TRACE_ENABLED=true` 时自动切换串行模式
- 🐛 高级选项展开/收起时 history 区域跳动问题
- 🐛 历史记录封面图片居中显示

---

## 2026-02-06

### Fixed
- 🐛 更新 Mini 模式配置 - 章节数 2→4，配图数 3→5

---

## 2026-02-05

### Added
- ✨ Mini 博客改造完成 - 动画视频生成和测试验证 (tag: v2.1.0-mini-blog-animation)
- ✨ `correct_section()` 方法 - Mini 模式只更正不扩展
- ✅ Mini 博客 v2 单元测试

### Fixed
- 🐛 限制 Mini 模式最多修订 1 轮
- 🐛 修复背景知识为空的问题

---

## 2026-02-04

### Added
- ✨ 实现 Mini 博客动画 v2 核心功能

### Fixed
- 🐛 修复测试脚本的返回值解析

---

## 2026-01-31

### Fixed
- 🐛 图片水印/宽高比透传 + 日志清理 + 网络来源链接

---

## 2026-01-30

### Added
- ✨ 多图序列视频生成功能
- 🔧 添加 GitHub Actions 自动构建前端
- 🔧 本地预构建前端，服务器直接部署静态文件

### Changed
- 🎨 优化 UI/UX：进度面板自适应、博客列表折叠按钮统计信息

### Fixed
- 🐛 添加 Node.js 内存限制避免服务器 OOM
- 🐛 修复 XhsCreator.vue 缺少关闭标签导致构建失败

---

## 2026-01-28

### Changed
- 🎨 优化终端侧边栏和博客卡片 UI

---

## 2026-01-26

### Added
- ✨ 集成 Sora2 视频服务和续创作模式（实验性）
- ✨ 优化吉卜力模板 + 大纲生成 2000 字短文

---

## 2026-01-25

### Added
- ✨ 添加小红书生成服务和宫崎骏夏日漫画风格模板

---

## 2026-01-23 (v0.1.6)

### Added
- ✨ 新增 CSDN 一键发布功能
- ✨ 新增缺失图表检测器，自动识别需要补充图表的位置
- ✨ 新增 OSS 服务，支持阿里云 OSS 图片上传

### Changed
- 🔧 优化图片服务，重构代码结构
- 🔧 优化视频服务，改进封面动画生成逻辑
- 🔧 优化博客生成器模板和代理逻辑

---

## 2026-01-19 (v0.1.5.1)

### Added
- ✨ 新增多种受众适配的技术风格博客支持（技术小白版、儿童版、高中生版、职场版）

---

## 2026-01-18 (v0.1.5)

### Added
- ✨ 新增智能书籍聚合系统，博客自动组织成技术书籍
- ✨ 智能大纲生成：LLM 分析博客内容，自动生成章节结构
- ✨ Docsify 书籍阅读器：类 GitBook 的在线阅读体验
- ✨ 添加图片生成重试机制和书籍处理进度日志

### Fixed
- 🐛 修复 Docsify 侧边栏重复问题
- 🐛 修复数据库迁移顺序问题
- 🐛 封面视频生成直接使用图片服务返回的外网 URL

---

## 2026-01-17 (v0.1.4.2)

### Added
- ✨ 新增封面动画生成功能：让静态的信息图动起来
- ✨ 新增多风格配图系统：8 种配图风格可选
- ✨ 支持卡通手绘、水墨古风、科研学术、Chiikawa萌系等风格

### Changed
- 🔧 支持自定义配置面板：章节数、配图数、代码块、目标字数
- 🔧 增强 Mermaid 图表渲染：特殊字符处理、双引号转义

---

## 2026-01-10 (v0.1.3)

### Added
- ✨ 新增 vibe-reviewer 教程评估模块
- ✨ Git 仓库教程质量评估：深度检查 + 质量审核 + 可读性分析
- ✨ 支持搜索增强评估、SSE 实时进度、Markdown 报告导出
- ✨ 三栏对比视图：文件列表 + Markdown 渲染 + 问题批注

---

## 2026-01-05 (v0.1.2)

### Added
- ✨ 新增自定义知识源 2 期
- ✨ PDF/MD/TXT 文件解析 + 知识分块
- ✨ 图片摘要提取（基于 Qwen-VL）
- ✨ 知识融合写作增强
- ✨ 实现多轮搜索能力

### Fixed
- 🐛 提高审核通过阈值至 91 分，high 级别问题直接拦截
- 🐛 添加防御性检查防止前置步骤失败导致后续 Agent 崩溃

---

## 2025-12-30 (v0.1.0)

### Added
- 🚀 vibe-blog 首次发布
- ✨ 多 Agent 协作架构（10 个 Agent）
- ✨ 联网搜索 + 多轮深度调研
- ✨ Mermaid 图表 + AI 封面图生成
- ✨ SSE 实时进度推送 + Markdown 渲染
