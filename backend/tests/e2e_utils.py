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
INPUT_SELECTORS = [
    'textarea[placeholder*="输入"]',
    'textarea[placeholder*="主题"]',
    'textarea[placeholder*="想写"]',
    'input[placeholder*="技术主题"]',
    'input[placeholder*="主题"]',
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
        
        input_el.click()
        input_el.fill(topic)
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
