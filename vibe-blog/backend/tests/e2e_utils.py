"""
E2E 测试共享工具模块

⚠️ 所有 Playwright E2E 测试都应该复用这个模块的 SSE Hook 和前端交互逻辑。
   不要在各个测试文件中重写这些逻辑！

包含：
  - SSE_HOOK_JS: 完整的 EventSource 代理脚本
  - run_playwright_generation(): 通用的前端交互流程（输入主题 → 点击生成 → 等待 SSE 事件）
"""

import logging
import requests

logger = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:5001"
FRONTEND_URL = "http://localhost:5173"

# ═══════════════════════════════════════════════════════════════
# SSE Hook JS（从 test_70_1_1_narrative_e2e.py 提取的成熟版本）
# ═══════════════════════════════════════════════════════════════

SSE_HOOK_JS = """
(() => {
    window.__sse_outline_data = null;
    window.__sse_sections = [];
    window.__sse_events = [];
    window.__sse_generation_done = false;
    const OrigES = window.EventSource;
    window.EventSource = function(url, opts) {
        const es = new OrigES(url, opts);
        const origAddEventListener = es.addEventListener.bind(es);
        es.addEventListener = function(type, fn, ...rest) {
            const wrapped = function(evt) {
                try {
                    window.__sse_events.push({type: type, data: evt.data});
                    if (type === 'result') {
                        const d = JSON.parse(evt.data);
                        if (d.type === 'outline_complete') {
                            window.__sse_outline_data = d.data;
                        }
                        if (d.type === 'section_complete' && d.data) {
                            window.__sse_sections.push(d.data);
                        }
                        if (d.type === 'generation_complete') {
                            window.__sse_generation_done = true;
                        }
                    }
                } catch(e) {}
                return fn.call(this, evt);
            };
            return origAddEventListener(type, wrapped, ...rest);
        };
        return es;
    };
    window.EventSource.CONNECTING = OrigES.CONNECTING;
    window.EventSource.OPEN = OrigES.OPEN;
    window.EventSource.CLOSED = OrigES.CLOSED;
})();
"""

# 输入框选择器列表（按优先级）
# 前端使用 TipTap (ProseMirror) 富文本编辑器，输入区域是 contenteditable div
INPUT_SELECTORS = [
    'div.ProseMirror[contenteditable="true"]',
    '.tiptap.ProseMirror',
    '.code-input-textarea .ProseMirror',
    'textarea[placeholder*="输入"]',
    'textarea[placeholder*="主题"]',
    'textarea',
]

# 生成按钮选择器列表（按优先级）
GENERATE_BTN_SELECTORS = [
    '.code-generate-btn',
    'button:has-text("execute")',
    'button:has-text("生成")',
    'button:has-text("开始")',
    'button:has-text("Generate")',
    'button[type="submit"]',
]


def find_element(page, selectors: list, timeout: int = 3000):
    """尝试多个选择器找到可见元素"""
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=timeout):
                return el, selector
        except Exception:
            continue
    return None, None


def fill_input(page, el, text: str):
    """向输入元素填入文本，兼容 TipTap contenteditable 和普通 input/textarea。

    TipTap 的 ProseMirror 是 contenteditable div，不支持 .fill()，
    需要先 click 聚焦，再用 keyboard.type() 输入。
    """
    tag = el.evaluate("e => e.tagName")
    is_contenteditable = el.evaluate("e => e.contentEditable === 'true'")

    if is_contenteditable or tag == "DIV":
        el.click()
        # 清空已有内容
        page.keyboard.press("Meta+a")
        page.keyboard.press("Backspace")
        page.keyboard.type(text, delay=20)
    else:
        el.click()
        el.fill(text)


def clear_input(page, el):
    """清空输入元素内容，兼容 TipTap contenteditable。"""
    tag = el.evaluate("e => e.tagName")
    is_contenteditable = el.evaluate("e => e.contentEditable === 'true'")

    if is_contenteditable or tag == "DIV":
        el.click()
        page.keyboard.press("Meta+a")
        page.keyboard.press("Backspace")
    else:
        el.fill("")


def run_playwright_generation(
    page,
    topic: str,
    wait_for: str = "outline",
    max_wait: int = 300,
    screenshot_prefix: str = "e2e"
) -> dict:
    """
    通用的前端交互流程：输入主题 → 点击生成 → 等待 SSE 事件
    
    Args:
        page: Playwright page 对象（已注入 SSE_HOOK_JS）
        topic: 要输入的主题
        wait_for: 等待的事件类型 ("outline" | "section" | "complete")
        max_wait: 最大等待秒数
        screenshot_prefix: 截图文件名前缀
    
    Returns:
        {
            "success": bool,
            "task_id": str,
            "outline": dict | None,
            "sections": list,
            "error": str | None
        }
    """
    result = {
        "success": False,
        "task_id": None,
        "outline": None,
        "sections": [],
        "error": None
    }

    try:
        # Step 1: 打开首页
        logger.info(f"  📌 Step 1: 打开首页")
        page.goto(FRONTEND_URL, wait_until='domcontentloaded')
        page.wait_for_timeout(3000)
        logger.info(f"    ✅ 首页加载成功: {page.title()}")
        page.screenshot(path=f'/tmp/{screenshot_prefix}_step1.png')

        # Step 2: 输入主题
        logger.info(f"  📌 Step 2: 输入主题: {topic}")
        input_el, selector = find_element(page, INPUT_SELECTORS)
        if not input_el:
            result["error"] = "未找到输入框"
            logger.error(f"    ❌ {result['error']}")
            page.screenshot(path=f'/tmp/{screenshot_prefix}_step2_fail.png')
            return result
        
        fill_input(page, input_el, topic)
        logger.info(f"    ✅ 已输入主题 (selector: {selector})")

        # Step 3: 点击生成
        logger.info(f"  📌 Step 3: 点击生成")
        gen_btn, btn_selector = find_element(page, GENERATE_BTN_SELECTORS)
        if not gen_btn:
            result["error"] = "未找到生成按钮"
            logger.error(f"    ❌ {result['error']}")
            page.screenshot(path=f'/tmp/{screenshot_prefix}_step3_fail.png')
            return result

        # 等待 API 响应获取 task_id
        with page.expect_response(
            lambda resp: 'generate' in resp.url and resp.status < 400,
            timeout=60000
        ) as response_info:
            gen_btn.click()
            logger.info(f"    ✅ 已点击生成按钮 (selector: {btn_selector})")

        api_response = response_info.value
        logger.info(f"    🔗 API响应: {api_response.status} {api_response.url}")
        try:
            body = api_response.json()
            result["task_id"] = body.get('task_id', '')
        except Exception as e:
            result["error"] = f"解析API响应失败: {e}"
            logger.error(f"    ❌ {result['error']}")
            return result

        if not result["task_id"]:
            result["error"] = f"响应中无 task_id: {body}"
            logger.error(f"    ❌ {result['error']}")
            return result
        logger.info(f"    📡 task_id: {result['task_id']}")
        page.screenshot(path=f'/tmp/{screenshot_prefix}_step3.png')

        # Step 4: 轮询 SSE 事件
        logger.info(f"  📌 Step 4: 等待 SSE 事件 (wait_for={wait_for})...")
        poll_interval = 3
        waited = 0
        
        while waited < max_wait:
            # 检查目标事件
            if wait_for == "outline":
                data = page.evaluate('() => window.__sse_outline_data')
                if data:
                    result["outline"] = data
                    result["success"] = True
                    logger.info(f"    🎉 收到 outline_complete")
                    break
            elif wait_for == "section":
                sections = page.evaluate('() => window.__sse_sections || []')
                if len(sections) >= 1:
                    result["sections"] = sections
                    result["success"] = True
                    logger.info(f"    🎉 收到 {len(sections)} 个 section_complete")
                    break
            elif wait_for == "complete":
                done = page.evaluate('() => window.__sse_generation_done')
                if done:
                    result["outline"] = page.evaluate('() => window.__sse_outline_data')
                    result["sections"] = page.evaluate('() => window.__sse_sections || []')
                    result["success"] = True
                    logger.info(f"    🎉 收到 generation_complete")
                    break
            
            page.wait_for_timeout(poll_interval * 1000)
            waited += poll_interval
            if waited % 30 == 0:
                event_count = page.evaluate('() => window.__sse_events.length')
                logger.info(f"    ⏳ 已等待 {waited}s，收到 {event_count} 个 SSE 事件")

        page.screenshot(path=f'/tmp/{screenshot_prefix}_step4.png')

        if not result["success"]:
            result["error"] = f"超时：未收到 {wait_for} 事件"
            logger.error(f"    ❌ {result['error']}")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"  ❌ Playwright 异常: {e}")

    return result


def cancel_task(task_id: str):
    """通过 API 取消任务"""
    if not task_id:
        return
    try:
        requests.post(f"{BACKEND_URL}/api/tasks/{task_id}/cancel", timeout=5)
        logger.info(f"  🛑 已取消任务: {task_id}")
    except Exception as e:
        logger.warning(f"  ⚠️ 取消任务失败: {e}")


# ═══════════════════════════════════════════════════════════════
# 详情页内容验证
# ═══════════════════════════════════════════════════════════════

def verify_blog_detail_page(page, topic: str = None) -> dict:
    """
    验证博客详情页内容是否正确渲染。

    Returns:
        {
            "title": str | None,
            "sections_count": int,
            "content_length": int,
            "has_images": bool,
            "has_code_blocks": bool,
            "errors": list[str],
        }
    """
    result = {
        "title": None,
        "sections_count": 0,
        "content_length": 0,
        "has_images": False,
        "has_code_blocks": False,
        "errors": [],
    }

    # 等待内容区域渲染
    try:
        page.locator(".blog-content.prose, .content-card-body").first.wait_for(
            state="visible", timeout=10000
        )
    except Exception:
        result["errors"].append("详情页内容区域未渲染")
        return result

    # 标题
    title_el = page.locator("h1.blog-title, .title-section h1").first
    try:
        result["title"] = title_el.text_content(timeout=5000)
    except Exception:
        result["errors"].append("未找到博客标题")

    if topic and result["title"]:
        # 标题应包含主题关键词（至少部分匹配）
        topic_words = [w for w in topic.split() if len(w) > 1]
        if topic_words and not any(w in result["title"] for w in topic_words):
            result["errors"].append(
                f"标题 '{result['title']}' 与主题 '{topic}' 不匹配"
            )

    # 正文内容
    content_el = page.locator(".blog-content.prose, .content-card-body").first
    try:
        content_text = content_el.text_content(timeout=5000)
        result["content_length"] = len(content_text or "")
        if result["content_length"] < 100:
            result["errors"].append(
                f"正文内容过短: {result['content_length']} 字符"
            )
    except Exception:
        result["errors"].append("无法读取正文内容")

    # 章节标题 (h2/h3)
    headings = page.locator(".blog-content h2, .blog-content h3, .content-card-body h2, .content-card-body h3")
    result["sections_count"] = headings.count()
    if result["sections_count"] == 0:
        result["errors"].append("未找到章节标题 (h2/h3)")

    # 图片
    images = page.locator(".blog-content img, .content-card-body img")
    result["has_images"] = images.count() > 0

    # 代码块
    code_blocks = page.locator(".blog-content pre code, .content-card-body pre code")
    result["has_code_blocks"] = code_blocks.count() > 0

    return result


# ═══════════════════════════════════════════════════════════════
# 后端日志 & 任务状态采集
# ═══════════════════════════════════════════════════════════════

def get_task_status(task_id: str) -> dict | None:
    """通过 API 获取任务状态"""
    try:
        resp = requests.get(f"{BACKEND_URL}/api/tasks/{task_id}", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("task")
    except Exception as e:
        logger.warning(f"获取任务状态失败: {e}")
    return None


def get_blog_detail_api(blog_id: str) -> dict | None:
    """通过 API 获取博客详情（用于后端数据验证）"""
    try:
        resp = requests.get(f"{BACKEND_URL}/api/history/{blog_id}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning(f"获取博客详情失败: {e}")
    return None


# ═══════════════════════════════════════════════════════════════
# 特性验证机制
# ═══════════════════════════════════════════════════════════════

# 特性验证注册表：迁移新特性后，在此注册验证函数
# 格式: { "feature_name": callable(page, blog_data) -> (bool, str) }
_feature_checks = {}


def register_feature_check(name: str, check_fn):
    """注册一个特性验证函数。

    check_fn 签名: (page, blog_data: dict) -> (passed: bool, message: str)
    - page: Playwright page（已在详情页）
    - blog_data: 后端 API 返回的博客数据（可能为 None）
    """
    _feature_checks[name] = check_fn
    logger.info(f"注册特性验证: {name}")


def run_feature_checks(page, blog_data: dict = None) -> list[dict]:
    """运行所有已注册的特性验证。

    Returns:
        [{"feature": str, "passed": bool, "message": str}, ...]
    """
    results = []
    for name, fn in _feature_checks.items():
        try:
            passed, msg = fn(page, blog_data)
            results.append({"feature": name, "passed": passed, "message": msg})
            status = "PASS" if passed else "FAIL"
            logger.info(f"  特性验证 [{status}] {name}: {msg}")
        except Exception as e:
            results.append({"feature": name, "passed": False, "message": str(e)})
            logger.error(f"  特性验证 [ERROR] {name}: {e}")
    return results
