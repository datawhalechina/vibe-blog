# 80 移动端对话式写作 — Phase 1 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 vibe-blog 增加对话式写作 REST API，支持 NanoClaw 通过 MCP → Bridge → HTTP 驱动多轮协作式博客写作。
**Architecture:** 三层架构 — WritingSession(数据层) + AgentDispatcher(分发层) + chat_routes(API层)。vibe-blog 只暴露 REST API，不引入 MCP 协议。
**Tech Stack:** Flask Blueprint + SQLite + 现有 Agent 底层方法

---

## Task 1: WritingSession 数据层 + 测试

**Files:**
- Create: `backend/services/chat/__init__.py`
- Create: `backend/services/chat/writing_session.py`
- Create: `backend/tests/test_writing_session.py`

**Step 1: 创建 chat 模块入口**
```python
# backend/services/chat/__init__.py
# 空模块入口
```

**Step 2: 实现 WritingSession dataclass + WritingSessionManager**

WritingSession 字段：
- `session_id`: str (ws_ 前缀, uuid4)
- `topic`: str
- `article_type`: str = "problem-solution"
- `target_audience`: str = "beginner"
- `target_length`: str = "medium"
- `outline`: Optional[dict] = None
- `sections`: List[dict] = []
- `search_results`: List[dict] = []
- `research_summary`: Optional[str] = None
- `key_concepts`: List[str] = []
- `code_blocks`: List[dict] = []
- `images`: List[dict] = []
- `status`: str = "created" (created/researching/outlining/writing/reviewing/assembling/completed)
- `created_at`: str (ISO format)
- `updated_at`: str (ISO format)

WritingSessionManager 方法：
- `__init__(self, db_path: str = ":memory:")` — 创建 SQLite 连接 + 建表
- `create(self, topic: str, **kwargs) -> WritingSession` — 创建新会话
- `get(self, session_id: str) -> Optional[WritingSession]` — 获取会话
- `update(self, session_id: str, **kwargs) -> WritingSession` — 更新会话字段
- `list(self, limit: int = 20, offset: int = 0) -> List[WritingSession]` — 列出会话
- `delete(self, session_id: str) -> bool` — 删除会话

SQLite 表结构：
```sql
CREATE TABLE IF NOT EXISTS writing_sessions (
    session_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    article_type TEXT DEFAULT 'problem-solution',
    target_audience TEXT DEFAULT 'beginner',
    target_length TEXT DEFAULT 'medium',
    outline TEXT,          -- JSON
    sections TEXT,         -- JSON
    search_results TEXT,   -- JSON
    research_summary TEXT,
    key_concepts TEXT,     -- JSON
    code_blocks TEXT,      -- JSON
    images TEXT,           -- JSON
    status TEXT DEFAULT 'created',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Step 3: 编写测试 (TDD — 先写测试)**

测试用例 WS1-WS11：
- WS1: 创建会话 — session_id 以 ws_ 开头
- WS2: 创建会话 — 默认字段值正确
- WS3: 获取会话 — 存在的 session_id
- WS4: 获取会话 — 不存在返回 None
- WS5: 更新会话 — 更新 topic
- WS6: 更新会话 — 更新 outline (JSON 字段)
- WS7: 更新会话 — 更新 sections (JSON 列表)
- WS8: 更新会话 — updated_at 自动更新
- WS9: 列出会话 — limit/offset 分页
- WS10: 删除会话 — 成功删除
- WS11: 删除会话 — 不存在返回 False

**验收标准:** `pytest tests/test_writing_session.py -v` 全部通过

---

## Task 2: AgentDispatcher 基础框架 + 调研方法 + 测试

**Files:**
- Create: `backend/services/chat/agent_dispatcher.py`
- Create: `backend/tests/test_agent_dispatcher.py`

**Step 1: 实现 AgentDispatcher 基础框架**

```python
class AgentDispatcher:
    def __init__(self, llm_client, search_service=None, knowledge_service=None, image_service=None):
        self.researcher = ResearcherAgent(llm_client, search_service, knowledge_service)
        self.search_coordinator = SearchCoordinator(llm_client, search_service)
        self.planner = PlannerAgent(llm_client)
        self.writer = WriterAgent(llm_client)
        self.coder = CoderAgent(llm_client)
        self.artist = ArtistAgent(llm_client)
        self.reviewer = ReviewerAgent(llm_client)
        self.factcheck = FactCheckAgent(llm_client)
        self.humanizer = HumanizerAgent(llm_client)
        self.assembler = AssemblerAgent()
```

**Step 2: 实现调研阶段方法**

```python
async def search(self, session: WritingSession, **kwargs) -> dict:
    """调研 — 调用 ResearcherAgent.search()"""
    results = self.researcher.search(session.topic, session.target_audience, **kwargs)
    return {"search_results": results}

async def detect_knowledge_gaps(self, session: WritingSession, content: str = "") -> dict:
    """知识缺口检测 — 调用 SearchCoordinator.detect_knowledge_gaps()"""
    gaps = self.search_coordinator.detect_knowledge_gaps(
        content=content,
        existing_knowledge=session.research_summary or "",
        topic=session.topic
    )
    return {"knowledge_gaps": gaps}
```

**Step 3: 编写测试 (TDD)**

测试用例 AD1-AD3：
- AD1: AgentDispatcher 初始化 — 所有 Agent 实例化成功
- AD2: search() — Mock ResearcherAgent，返回搜索结果
- AD3: detect_knowledge_gaps() — Mock SearchCoordinator，返回知识缺口

**验收标准:** `pytest tests/test_agent_dispatcher.py::TestResearch -v` 全部通过

---

## Task 3: AgentDispatcher 大纲 + 写作方法 + 测试

**Files:**
- Modify: `backend/services/chat/agent_dispatcher.py`
- Modify: `backend/tests/test_agent_dispatcher.py`

**Step 1: 实现大纲阶段方法**

```python
async def generate_outline(self, session: WritingSession) -> dict:
    """生成大纲 — 调用 PlannerAgent.generate_outline()"""
    outline = self.planner.generate_outline(
        topic=session.topic,
        article_type=session.article_type,
        target_audience=session.target_audience,
        target_length=session.target_length,
        background_knowledge=session.research_summary or "",
        key_concepts=session.key_concepts or []
    )
    return {"outline": outline}

async def edit_outline(self, session: WritingSession, changes: dict) -> dict:
    """编辑大纲 — 直接修改 outline 结构"""
    outline = session.outline or {}
    # 应用 changes 到 outline
    return {"outline": outline}
```

**Step 2: 实现写作阶段方法**

```python
async def write_section(self, session: WritingSession, section_id: str) -> dict:
    """写作单个章节 — 调用 WriterAgent.write_section()"""

async def edit_section(self, session: WritingSession, section_id: str, instructions: str) -> dict:
    """编辑章节 — 调用 WriterAgent.improve_section()"""

async def enhance_section(self, session: WritingSession, section_id: str) -> dict:
    """增强章节 — 调用 WriterAgent.enhance_section()"""
```

**Step 3: 编写测试 (TDD)**

测试用例 AD4-AD12：
- AD4: generate_outline() — Mock PlannerAgent
- AD5: edit_outline() — 修改标题
- AD6: edit_outline() — 添加/删除章节
- AD7: write_section() — Mock WriterAgent.write_section()
- AD8: write_section() — 传递上下文（前后章节摘要）
- AD9: edit_section() — Mock WriterAgent.improve_section()
- AD10: enhance_section() — Mock WriterAgent.enhance_section()
- AD11: write_section() — section_id 不存在返回错误
- AD12: edit_section() — 章节未写作返回错误

**验收标准:** `pytest tests/test_agent_dispatcher.py::TestOutline tests/test_agent_dispatcher.py::TestWriting -v` 全部通过

---

## Task 4: AgentDispatcher 代码/配图/质量/组装方法 + 测试

**Files:**
- Modify: `backend/services/chat/agent_dispatcher.py`
- Modify: `backend/tests/test_agent_dispatcher.py`

**Step 1: 实现代码 & 配图方法**

```python
async def generate_code(self, session: WritingSession, description: str, language: str = "python") -> dict:
    """生成代码 — 调用 CoderAgent.generate_code()"""

async def generate_image(self, session: WritingSession, description: str, image_type: str = "diagram") -> dict:
    """生成配图 — 调用 ArtistAgent.generate_image()"""
```

**Step 2: 实现质量检查方法**

```python
async def review(self, session: WritingSession) -> dict:
    """审核 — 调用 ReviewerAgent.review()"""

async def factcheck(self, session: WritingSession) -> dict:
    """事实核查 — 调用 FactCheckAgent.check()"""

async def humanize(self, session: WritingSession, section_id: str = None) -> dict:
    """去AI味 — 调用 HumanizerAgent._rewrite_section()"""
```

**Step 3: 实现组装 & 管理方法**

```python
async def assemble(self, session: WritingSession) -> dict:
    """组装最终文档 — 调用 AssemblerAgent.assemble()"""

async def get_preview(self, session: WritingSession) -> dict:
    """获取预览 — 返回当前已写章节的 Markdown"""

async def publish(self, session: WritingSession) -> dict:
    """发布 — 标记会话为 completed"""
```

**Step 4: 编写测试 (TDD)**

测试用例 AD13-AD20：
- AD13: generate_code() — Mock CoderAgent
- AD14: generate_image() — Mock ArtistAgent
- AD15: review() — Mock ReviewerAgent，组装全文后调用
- AD16: factcheck() — Mock FactCheckAgent
- AD17: humanize() — Mock HumanizerAgent，指定 section_id
- AD18: humanize() — 全文 humanize
- AD19: assemble() — Mock AssemblerAgent
- AD20: get_preview() — 返回已写章节拼接

**验收标准:** `pytest tests/test_agent_dispatcher.py -v` 全部 20 个用例通过

---

## Task 5: conftest.py 共享 fixtures

**Files:**
- Modify: `backend/tests/conftest.py` (追加，不覆盖)

**追加 fixtures:**

```python
# ============ Chat Fixtures ============

@pytest.fixture
def session_mgr():
    """In-memory WritingSessionManager for testing."""
    from services.chat.writing_session import WritingSessionManager
    return WritingSessionManager(db_path=":memory:")

@pytest.fixture
def session_id(session_mgr):
    """Create a test session and return its ID."""
    session = session_mgr.create(topic="测试主题：AI 入门指南")
    return session.session_id

@pytest.fixture
def sample_outline():
    """Sample outline for testing."""
    return {
        "title": "AI 入门指南",
        "sections": [
            {"id": "s1", "title": "什么是 AI", "key_points": ["定义", "历史"]},
            {"id": "s2", "title": "机器学习基础", "key_points": ["监督学习", "无监督学习"]},
            {"id": "s3", "title": "深度学习", "key_points": ["神经网络", "CNN", "RNN"]},
        ]
    }

@pytest.fixture
def mock_dispatcher():
    """Mock AgentDispatcher with all agents mocked."""
    from services.chat.agent_dispatcher import AgentDispatcher
    dispatcher = AgentDispatcher.__new__(AgentDispatcher)
    dispatcher.researcher = MagicMock()
    dispatcher.search_coordinator = MagicMock()
    dispatcher.planner = MagicMock()
    dispatcher.writer = MagicMock()
    dispatcher.coder = MagicMock()
    dispatcher.artist = MagicMock()
    dispatcher.reviewer = MagicMock()
    dispatcher.factcheck_agent = MagicMock()
    dispatcher.humanizer = MagicMock()
    dispatcher.assembler = MagicMock()
    return dispatcher

@pytest.fixture
def chat_app(monkeypatch, mock_dispatcher, session_mgr):
    """Flask app with chat services initialized."""
    # ... 创建 app 并注入 mock_dispatcher + session_mgr

@pytest.fixture
def chat_client(chat_app):
    """Flask test client for chat API."""
    return chat_app.test_client()
```

**验收标准:** fixtures 可被后续测试文件正常导入使用

---

## Task 6: chat_routes.py REST API 全部端点 + 测试

**Files:**
- Create: `backend/routes/chat_routes.py`
- Create: `backend/tests/test_chat_routes.py`

**Step 1: 实现 chat_routes.py 基础框架**

```python
from flask import Blueprint, request, jsonify

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

_session_mgr = None
_dispatcher = None

def init_chat_service(session_mgr, dispatcher):
    global _session_mgr, _dispatcher
    _session_mgr = session_mgr
    _dispatcher = dispatcher

def get_session_or_404(session_id):
    session = _session_mgr.get(session_id)
    if not session:
        return None, (jsonify({"error": "Session not found"}), 404)
    return session, None
```

**Step 2: 实现会话 + 调研 + 大纲端点**

| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/chat/session` | 创建会话 |
| GET | `/api/chat/sessions` | 列出会话 |
| GET | `/api/chat/session/<id>` | 获取会话详情 |
| POST | `/api/chat/session/<id>/search` | 调研 |
| POST | `/api/chat/session/<id>/knowledge-gaps` | 知识缺口检测 |
| POST | `/api/chat/session/<id>/outline` | 生成大纲 |
| POST | `/api/chat/session/<id>/outline/edit` | 编辑大纲 |

**Step 3: 实现写作 + 代码 + 配图端点**

| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/chat/session/<id>/write` | 写作章节 |
| POST | `/api/chat/session/<id>/edit` | 编辑章节 |
| POST | `/api/chat/session/<id>/enhance` | 增强章节 |
| POST | `/api/chat/session/<id>/code` | 生成代码 |
| POST | `/api/chat/session/<id>/image` | 生成配图 |

**Step 4: 实现质量 + 组装 + 预览端点**

| Method | Path | Handler |
|--------|------|---------|
| POST | `/api/chat/session/<id>/review` | 审核 |
| POST | `/api/chat/session/<id>/factcheck` | 事实核查 |
| POST | `/api/chat/session/<id>/humanize` | 去AI味 |
| POST | `/api/chat/session/<id>/assemble` | 组装 |
| POST | `/api/chat/session/<id>/publish` | 发布 |
| GET | `/api/chat/session/<id>/preview` | 预览 |

**Step 5: 编写路由测试 (TDD)**

测试用例 T4 (8 个基础路由测试)：
- RT1: POST /session — 创建会话成功 201
- RT2: GET /sessions — 列出会话 200
- RT3: GET /session/<id> — 获取会话 200
- RT4: GET /session/<bad_id> — 404
- RT5: POST /session/<id>/search — 调研 200
- RT6: POST /session/<id>/outline — 生成大纲 200
- RT7: POST /session/<id>/write — 写作 200
- RT8: POST /session/<id>/assemble — 组装 200

**验收标准:** `pytest tests/test_chat_routes.py -v` 全部通过

---

## Task 7: Blueprint 注册 + app.py 初始化

**Files:**
- Modify: `backend/routes/__init__.py`
- Modify: `backend/app.py`

**Step 1: 注册 chat_bp**

在 `routes/__init__.py` 中：
```python
from routes.chat_routes import chat_bp
# 在 register_all_blueprints 中添加：
app.register_blueprint(chat_bp)
```

**Step 2: app.py 初始化 chat 服务**

在 `create_app()` 中，Blueprint 注册之前：
```python
# 初始化对话式写作服务
from services.chat.writing_session import WritingSessionManager
from services.chat.agent_dispatcher import AgentDispatcher
from routes.chat_routes import init_chat_service

chat_session_mgr = WritingSessionManager(
    db_path=os.path.join(os.path.dirname(__file__), 'data', 'writing_sessions.db')
)
chat_dispatcher = AgentDispatcher(
    llm_client=get_llm_service(),
    search_service=get_search_service(),
)
init_chat_service(chat_session_mgr, chat_dispatcher)
```

**验收标准:** Flask app 启动无报错，`/api/chat/sessions` 返回 200

---

## Task 8: 搜索/大纲 API 集成测试

**Files:**
- Create: `backend/tests/test_chat_search.py`

测试用例 CS1-CS10：
- CS1: 创建会话 → 搜索 → 返回 search_results
- CS2: 搜索 → 会话 search_results 已更新
- CS3: 搜索 → 知识缺口检测 → 返回 gaps
- CS4: 搜索 → 生成大纲 → 返回 outline
- CS5: 生成大纲 → 会话 outline 已更新
- CS6: 编辑大纲 → 修改标题
- CS7: 编辑大纲 → 添加章节
- CS8: 编辑大纲 → 删除章节
- CS9: 未搜索直接生成大纲 → 仍可成功（无背景知识）
- CS10: 搜索失败 → 返回 500 + 错误信息

**验收标准:** `pytest tests/test_chat_search.py -v` 全部通过

---

## Task 9: 写作/编辑 API 集成测试

**Files:**
- Create: `backend/tests/test_chat_write.py`

测试用例 CW1-CW11：
- CW1: 写作第一个章节 → 返回 section content
- CW2: 写作 → 会话 sections 已更新
- CW3: 写作多个章节 → sections 列表增长
- CW4: 编辑章节 → 返回修改后内容
- CW5: 增强章节 → 返回增强后内容
- CW6: 生成代码 → 返回 code block
- CW7: 生成配图 → 返回 image info
- CW8: 写作不存在的 section_id → 400
- CW9: 编辑未写作的章节 → 400
- CW10: 写作 → 状态变为 writing
- CW11: 全部章节写完 → 可以组装

**验收标准:** `pytest tests/test_chat_write.py -v` 全部通过

---

## Task 10: NanoClaw VibeBlogBridge + 配置

**Files:**
- Create: `nanoclaw/src/vibe-blog-bridge.ts`
- Modify: `nanoclaw/src/config.ts`

**Step 1: 添加 VIBE_BLOG_URL 配置**

```typescript
// src/config.ts
export const VIBE_BLOG_URL = process.env.VIBE_BLOG_URL || 'http://localhost:5001';
```

**Step 2: 实现 VibeBlogBridge**

19 个方法，每个对应一个 chat API 端点：
```typescript
export class VibeBlogBridge {
    private baseUrl: string;

    constructor(baseUrl?: string) {
        this.baseUrl = baseUrl || VIBE_BLOG_URL;
    }

    async createSession(topic: string, options?: SessionOptions): Promise<Session> {}
    async listSessions(): Promise<Session[]> {}
    async getSession(sessionId: string): Promise<Session> {}
    async search(sessionId: string, options?: SearchOptions): Promise<SearchResult> {}
    async detectKnowledgeGaps(sessionId: string, content?: string): Promise<GapResult> {}
    async generateOutline(sessionId: string): Promise<OutlineResult> {}
    async editOutline(sessionId: string, changes: OutlineChanges): Promise<OutlineResult> {}
    async writeSection(sessionId: string, sectionId: string): Promise<SectionResult> {}
    async editSection(sessionId: string, sectionId: string, instructions: string): Promise<SectionResult> {}
    async enhanceSection(sessionId: string, sectionId: string): Promise<SectionResult> {}
    async generateCode(sessionId: string, description: string, language?: string): Promise<CodeResult> {}
    async generateImage(sessionId: string, description: string, imageType?: string): Promise<ImageResult> {}
    async review(sessionId: string): Promise<ReviewResult> {}
    async factcheck(sessionId: string): Promise<FactcheckResult> {}
    async humanize(sessionId: string, sectionId?: string): Promise<HumanizeResult> {}
    async assemble(sessionId: string): Promise<AssembleResult> {}
    async publish(sessionId: string): Promise<PublishResult> {}
    async getPreview(sessionId: string): Promise<PreviewResult> {}
    async generate(sessionId: string): Promise<GenerateResult> {} // 一键生成
}
```

**验收标准:** TypeScript 编译通过，类型定义完整

---

## Task 11: NanoClaw 19 个 MCP 工具 + IPC 处理

**Files:**
- Modify: `nanoclaw/container/agent-runner/src/ipc-mcp.ts`
- Modify: `nanoclaw/src/index.ts`

**Step 1: 在 ipc-mcp.ts 注册 19 个 blog_* 工具**

每个工具通过 IPC 文件传递到 Host，Host 调用 VibeBlogBridge：
- blog_session_create, blog_session_list, blog_session_get
- blog_search, blog_knowledge_gaps
- blog_outline, blog_outline_edit
- blog_write, blog_edit, blog_enhance
- blog_code, blog_image
- blog_review, blog_factcheck, blog_humanize
- blog_assemble, blog_publish, blog_preview
- blog_generate (一键生成)

**Step 2: Host 进程 IPC 处理**

在 `src/index.ts` 的 IPC watcher 中新增 blog 类型处理：
- 读取 IPC 文件 → 解析 blog_* 工具调用 → 调用 VibeBlogBridge → 写回结果

**验收标准:** NanoClaw 编译通过，MCP 工具注册成功

---

## Task 12: CLAUDE.md 写作助手指令

**Files:**
- Modify: `nanoclaw/groups/{name}/CLAUDE.md`

添加多轮协作式写作助手行为指令，指导 Claude Agent 如何使用 blog_* 工具进行对话式写作。

**验收标准:** CLAUDE.md 包含完整的写作助手指令

---

## 执行顺序

```
Task 1 (WritingSession) → Task 2 (Dispatcher 基础+调研)
    → Task 3 (Dispatcher 大纲+写作) → Task 4 (Dispatcher 代码/质量/组装)
        → Task 5 (conftest fixtures) → Task 6 (chat_routes)
            → Task 7 (Blueprint 注册) → Task 8/9 (集成测试, 可并行)
                → Task 10 (NanoClaw Bridge) → Task 11 (MCP 工具)
                    → Task 12 (CLAUDE.md)
```

## 验证命令

```bash
# vibe-blog 侧 — 运行全部 chat 测试
cd /tmp/vibe-blog-chat-80/backend && pytest tests/test_writing_session.py tests/test_agent_dispatcher.py tests/test_chat_routes.py tests/test_chat_search.py tests/test_chat_write.py -v --cov=services/chat --cov=routes/chat_routes --cov-report=term-missing --cov-fail-under=80
```
