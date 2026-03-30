# Step 1.1 叙事模式与叙事流设计 — 开发-测试-验证流程

## 一、需求目标

在 `planner.j2` 模板中引入**叙事模式体系**，让 Planner Agent 根据主题信号自动选择叙事模式，并设计叙事流（逻辑链），最终输出包含 `narrative_mode`、`narrative_flow`、`narrative_role` 的结构化大纲。

## 二、开发阶段

### 2.1 创建分支

```bash
git checkout -b feature/step-1.1-narrative-flow
```

### 2.2 修改 planner.j2

**文件**: `backend/infrastructure/prompts/blog/planner.j2`

**核心改动**:
1. 新增 6 种叙事模式定义：
   - `what-why-how` — "什么是 X" 类主题
   - `tutorial` — "手把手/搭建/实战" 类主题
   - `catalog` — "N 个/大全/清单" 类主题
   - `problem-solution` — 问题解决类
   - `before-after` — 对比类
   - `deep-dive` — 深度分析类

2. 两步设计法 Prompt：
   - Step 1: 根据**主题信号**（而非 article_type）选择叙事模式
   - Step 2: 设计逻辑链 → 展开章节

3. JSON Schema 扩展：
   ```json
   {
     "narrative_mode": "what-why-how",
     "narrative_flow": {
       "reader_start": "读者起点状态",
       "reader_end": "读者终点状态",
       "logic_chain": ["节点1", "节点2", "节点3", "节点4"]
     },
     "sections": [
       {
         "title": "章节标题",
         "narrative_role": "what"
       }
     ]
   }
   ```

### 2.3 修改 blog_service.py

**文件**: `backend/services/blog_generator/blog_service.py`

**改动**: 在 `outline_complete` SSE 事件中加入叙事字段：
```python
task_manager.send_event(task_id, 'result', {
    'type': 'outline_complete',
    'data': {
        'title': outline.get('title', ''),
        'sections_count': len(sections),
        'sections': [s.get('title', '') for s in sections],
        'narrative_mode': outline.get('narrative_mode', ''),
        'narrative_flow': outline.get('narrative_flow', {}),
        'sections_narrative_roles': [s.get('narrative_role', '') for s in sections],
    }
})
```

## 三、测试阶段

### 3.1 单元验证（test_70_1_1_planner_narrative.py）

直接调用 PlannerAgent，验证 LLM 输出的 JSON 包含新字段。

```bash
cd backend && python tests/test_70_1_1_planner_narrative.py
```

### 3.2 Playwright E2E 验证（test_70_1_1_narrative_e2e.py）

**核心流程**:
```
Playwright 浏览器打开前端
    → 输入主题
    → 点击生成按钮
    → 捕获 API 响应获取 task_id
    → 通过浏览器内 JS Hook 拦截 SSE 事件
    → 轮询 window.__sse_outline_data
    → 验证 narrative_mode / narrative_flow / narrative_role
    → 取消任务（不需要等后续写作）
```

**运行命令**:
```bash
# 启动前后端
bash docker/start-local.sh

# 有头模式（可看到浏览器操作）
cd backend && python tests/test_70_1_1_narrative_e2e.py --headed --cases 1,2,3

# 单个用例
cd backend && python tests/test_70_1_1_narrative_e2e.py --headed --cases 1
```

**三个测试用例**:

| 用例 | 主题 | 期望模式 | 验证点 |
|------|------|---------|--------|
| 1 | 什么是 RAG | what-why-how | 模式匹配 + 字段完整性 |
| 2 | 手把手搭建 RAG 系统 | tutorial | 模式匹配 + 字段完整性 |
| 3 | 10 个 RAG 性能优化技巧 | catalog | 模式匹配 + 字段完整性 |

**验证项**:
- ✅ `narrative_mode` 值在 6 种模式范围内
- ✅ 模式匹配预期（主题信号优先级）
- ✅ `narrative_flow.reader_start` 有值
- ✅ `narrative_flow.reader_end` 有值
- ✅ `narrative_flow.logic_chain` ≥ 3 个节点
- ✅ 每个 section 都有 `narrative_role`

## 四、踩坑记录

### 4.1 Flask debug 模式导致后端卡死

**现象**: `debug=True` 时 watchdog 检测到文件变化后重启，可能导致进程卡死，所有 API 请求无响应。

**解决**: 测试时用 `debug=False` 启动，或使用 `docker/start-local.sh`。

### 4.2 SSE queue 竞争问题

**现象**: 用 `sseclient` 库另建 HTTP 连接监听 SSE 时，和前端浏览器的 EventSource 共享同一个 `queue.Queue`。`queue.get()` 是消费型操作，一个连接取走事件后另一个收不到。

**根因**: `task_service.py` 中每个 task_id 只有一个 queue，多个 SSE 连接会竞争消费。

**解决**: 不另建 SSE 连接，改用 **Playwright `add_init_script` 注入 JS Hook**，在浏览器内部拦截前端已有的 EventSource 事件：

```javascript
// Hook EventSource，拦截 SSE 事件存到 window 变量
window.EventSource = function(url, opts) {
    const es = new OrigES(url, opts);
    es.addEventListener = function(type, fn, ...rest) {
        const wrapped = function(evt) {
            if (type === 'result') {
                const d = JSON.parse(evt.data);
                if (d.type === 'outline_complete') {
                    window.__sse_outline_data = d.data;
                }
            }
            return fn.call(this, evt);
        };
        return origAddEventListener(type, wrapped, ...rest);
    };
    return es;
};
```

然后在 Python 中轮询：
```python
while waited < max_wait:
    result = page.evaluate('() => window.__sse_outline_data')
    if result:
        outline_data = result
        break
    page.wait_for_timeout(3000)
```

### 4.3 用例间任务干扰

**现象**: 取消任务后后端生成线程不会立即停止（LangGraph stream 在下一个 event 循环才检查取消状态），导致下一个用例的 Researcher/Planner 被排队等待。

**解决**: 用例间等待 15 秒让后端清理；或每个用例独立运行。

## 五、验证结果

```
============================================================
📊 E2E 验证结果: 3 通过, 0 失败 (共 3)
🎉 所有测试通过！
============================================================
```

| 用例 | narrative_mode | narrative_role |
|------|---------------|----------------|
| 什么是 RAG | what-why-how ✅ | [what, why, deep_dive, summary] |
| 手把手搭建 RAG 系统 | tutorial ✅ | [what, how, how, verify] |
| 10 个 RAG 性能优化技巧 | catalog ✅ | [what, catalog_item, how, summary] |

## 六、提交记录

```
分支: feature/step-1.1-narrative-flow
提交: feat(planner): Step 1.1 叙事模式与叙事流设计

修改文件:
- backend/infrastructure/prompts/blog/planner.j2 (模板改造)
- backend/services/blog_generator/blog_service.py (SSE 事件扩展)
- backend/tests/test_70_1_1_narrative_e2e.py (Playwright E2E 测试)
- backend/tests/test_70_1_1_planner_narrative.py (单元验证脚本)
```
