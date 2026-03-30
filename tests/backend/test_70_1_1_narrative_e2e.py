"""
[需求点 70.1.1] Step 1.1 Planner 叙事流设计 — Playwright E2E 验证

对齐方案文档：vibe-blog-plan-方案/70.1.1. Phase1叙事流验证方案.md

⚠️ 同步警告：
  - 修改本测试文件时，必须同步更新方案文档 70.1.1 的验证方案部分
  - 修改方案文档 70.1.1 的检查清单/通过标准时，必须同步更新本文件的验证逻辑
  - 测试主题矩阵（TEST_CASES）与方案文档中的"测试主题矩阵"表格一一对应

验证内容：
  A表 — 字段完整性检查（6项）
  B表 — 大纲质量检查（5项）
  通过标准：
    - 字段完整性：3 个主题全部输出 narrative_mode + narrative_flow + narrative_role
    - 模式匹配：3 个主题的 narrative_mode 至少 2 个匹配预期
    - 大纲质量：B 表 5 项检查中至少 3 项通过

用法：
    cd backend && python tests/test_70_1_1_narrative_e2e.py --headed
    cd backend && python tests/test_70_1_1_narrative_e2e.py --headed --cases 1
    cd backend && python tests/test_70_1_1_narrative_e2e.py  # 无头模式
"""

import sys
import os
import json
import time
import argparse
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:5001"
FRONTEND_URL = "http://localhost:5173"

VALID_MODES = ["what-why-how", "problem-solution", "before-after", "tutorial", "deep-dive", "catalog"]
VALID_ROLES = ["hook", "what", "why", "how", "compare", "deep_dive", "verify", "summary", "catalog_item"]

# 测试主题矩阵 — 对齐 70.1.1 验证方案
TEST_CASES = [
    {
        "topic": "什么是 RAG",
        "article_type": "tutorial",
        "expected_modes": ["what-why-how", "tutorial"],
        "target_length": "mini",
        "verify_focus": "是否先定义、再讲价值、再讲用法",
        "expected_structure": {
            "first_role_hint": ["hook", "what"],       # 第一章应是引子或概念定义
            "last_role_hint": ["summary", "how"],       # 最后一章应是总结或实践
            "should_have_roles": ["what"],               # 必须包含概念定义章节
        },
    },
    {
        "topic": "手把手搭建 RAG 系统",
        "article_type": "tutorial",
        "expected_modes": ["tutorial"],
        "target_length": "mini",
        "verify_focus": "是否有目标预览、前置条件、分步骤、验证",
        "expected_structure": {
            "first_role_hint": ["hook", "what"],
            "last_role_hint": ["summary", "verify"],
            "should_have_roles": ["how"],                # 必须包含操作步骤章节
        },
    },
    {
        "topic": "10 个 RAG 性能优化技巧",
        "article_type": "tutorial",
        "expected_modes": ["catalog"],
        "target_length": "mini",
        "verify_focus": "是否有前置说明、条目结构一致、全局总结",
        "expected_structure": {
            "first_role_hint": ["hook", "what", "catalog_item"],
            "last_role_hint": ["summary", "catalog_item"],
            "should_have_roles": ["catalog_item"],       # 必须包含清单条目章节
        },
    },
]


def validate_field_completeness(data: dict, expected_modes: list) -> list:
    """A表：字段完整性检查（6项，对齐验证方案 A 表）"""
    results = []

    # A1: 顶层有 narrative_mode 字段，值为 6 种模式之一
    mode = data.get("narrative_mode", "")
    if not mode:
        results.append(("FAIL", "A1: 缺少 narrative_mode"))
    elif mode not in VALID_MODES:
        results.append(("WARN", f"A1: narrative_mode 值不在预期范围: {mode}"))
    else:
        results.append(("PASS", f"A1: narrative_mode = {mode}"))

    # A2: narrative_mode 与主题匹配
    if mode in expected_modes:
        results.append(("PASS", f"A2: 模式匹配预期 {expected_modes}"))
    else:
        results.append(("WARN", f"A2: 模式不匹配: 实际={mode}, 期望={expected_modes}"))

    # A3: narrative_flow.reader_start 非空
    flow = data.get("narrative_flow", {})
    if not flow:
        results.append(("FAIL", "A3: 缺少 narrative_flow"))
        results.append(("FAIL", "A4: 缺少 narrative_flow"))
        results.append(("FAIL", "A5: 缺少 narrative_flow"))
    else:
        if flow.get("reader_start"):
            results.append(("PASS", f"A3: reader_start = {flow['reader_start'][:50]}"))
        else:
            results.append(("FAIL", "A3: 缺少 narrative_flow.reader_start"))

        # A4: narrative_flow.reader_end 非空
        if flow.get("reader_end"):
            results.append(("PASS", f"A4: reader_end = {flow['reader_end'][:50]}"))
        else:
            results.append(("FAIL", "A4: 缺少 narrative_flow.reader_end"))

        # A5: narrative_flow.logic_chain ≥3 个节点
        chain = flow.get("logic_chain", [])
        if len(chain) >= 3:
            results.append(("PASS", f"A5: logic_chain = {len(chain)} 个节点"))
        else:
            results.append(("FAIL", f"A5: logic_chain 不足 3 个节点: {len(chain)}"))

    # A6: 每个 section 有 narrative_role
    roles = data.get("sections_narrative_roles", [])
    if not roles:
        results.append(("FAIL", "A6: 缺少 sections_narrative_roles"))
    else:
        missing = sum(1 for r in roles if not r)
        if missing == 0:
            results.append(("PASS", f"A6: 所有 {len(roles)} 个 section 都有 narrative_role: {roles}"))
        else:
            results.append(("WARN", f"A6: {missing}/{len(roles)} 个 section 缺少 narrative_role"))

    return results, mode, roles


def validate_outline_quality(data: dict, case: dict, roles: list) -> list:
    """B表：大纲质量检查（5项，对齐验证方案 B 表）"""
    results = []
    sections = data.get("sections", [])
    expected = case.get("expected_structure", {})

    # B1: 第一章是否有"钩子"作用（从读者痛点/场景切入）
    if roles:
        first_role = roles[0]
        hints = expected.get("first_role_hint", ["hook", "what"])
        if first_role in hints:
            results.append(("PASS", f"B1: 第一章角色 '{first_role}' 符合预期（钩子/引入）"))
        else:
            results.append(("WARN", f"B1: 第一章角色 '{first_role}' 不在预期 {hints} 中"))
    else:
        results.append(("FAIL", "B1: 无法检查（缺少 roles）"))

    # B2: 章节顺序是否有逻辑递进（从浅到深、从概念到实践）
    role_order_score = _check_role_progression(roles)
    if role_order_score >= 0.6:
        results.append(("PASS", f"B2: 章节逻辑递进合理（得分 {role_order_score:.0%}）"))
    elif role_order_score >= 0.4:
        results.append(("WARN", f"B2: 章节逻辑递进一般（得分 {role_order_score:.0%}）"))
    else:
        results.append(("FAIL", f"B2: 章节逻辑递进不足（得分 {role_order_score:.0%}）"))

    # B3: 最后一章是否有总结/展望
    if roles:
        last_role = roles[-1]
        hints = expected.get("last_role_hint", ["summary"])
        if last_role in hints:
            results.append(("PASS", f"B3: 最后一章角色 '{last_role}' 符合预期（总结/收尾）"))
        else:
            results.append(("WARN", f"B3: 最后一章角色 '{last_role}' 不在预期 {hints} 中"))
    else:
        results.append(("FAIL", "B3: 无法检查（缺少 roles）"))

    # B4: 是否包含该模式必需的角色
    should_have = expected.get("should_have_roles", [])
    if should_have:
        found = [r for r in should_have if r in roles]
        if len(found) == len(should_have):
            results.append(("PASS", f"B4: 包含必需角色 {should_have}"))
        else:
            missing = [r for r in should_have if r not in roles]
            results.append(("WARN", f"B4: 缺少必需角色 {missing}（实际: {roles}）"))
    else:
        results.append(("PASS", "B4: 无特定角色要求"))

    # B5: 整体结构感（章节数合理 + 角色多样性）
    unique_roles = set(roles) if roles else set()
    section_count = data.get("sections_count", len(sections))
    if section_count >= 3 and len(unique_roles) >= 2:
        results.append(("PASS", f"B5: 结构合理（{section_count} 章节，{len(unique_roles)} 种角色）"))
    elif section_count >= 2:
        results.append(("WARN", f"B5: 结构偏简单（{section_count} 章节，{len(unique_roles)} 种角色）"))
    else:
        results.append(("FAIL", f"B5: 结构不足（{section_count} 章节）"))

    return results


def _check_role_progression(roles: list) -> float:
    """检查角色顺序是否符合逻辑递进，返回 0-1 分数"""
    if not roles or len(roles) < 2:
        return 0.0

    # 定义角色的"深度"权重，越大越深入
    depth = {
        'hook': 1, 'what': 2, 'why': 3, 'how': 4,
        'compare': 4, 'deep_dive': 5, 'verify': 5,
        'summary': 6, 'catalog_item': 3,
    }

    # 计算相邻章节的递进比例
    progressions = 0
    for i in range(len(roles) - 1):
        d1 = depth.get(roles[i], 3)
        d2 = depth.get(roles[i + 1], 3)
        if d2 >= d1:  # 后一章深度 ≥ 前一章 = 递进
            progressions += 1

    return progressions / (len(roles) - 1)


def validate_outline_from_sse(data: dict, case: dict) -> list:
    """完整验证：A表（字段完整性）+ B表（大纲质量），对齐 70.1.1 验证方案"""
    expected_modes = case["expected_modes"]

    # A表：字段完整性
    a_results, mode, roles = validate_field_completeness(data, expected_modes)

    # B表：大纲质量
    b_results = validate_outline_quality(data, case, roles)

    return a_results + b_results, mode


def _print_and_check_results(results: list) -> bool:
    """打印验证结果（A表/B表分组），返回是否全部通过"""
    a_results = [r for r in results if r[1].startswith("A")]
    b_results = [r for r in results if r[1].startswith("B")]

    all_pass = True

    logger.info(f"\n  --- A表：字段完整性 ---")
    for status, msg in a_results:
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}[status]
        logger.info(f"    {icon} {msg}")
        if status == "FAIL":
            all_pass = False

    a_pass = sum(1 for s, _ in a_results if s == "PASS")
    logger.info(f"    📊 A表: {a_pass}/{len(a_results)} 通过")

    logger.info(f"\n  --- B表：大纲质量 ---")
    for status, msg in b_results:
        icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}[status]
        logger.info(f"    {icon} {msg}")
        if status == "FAIL":
            all_pass = False

    b_pass = sum(1 for s, _ in b_results if s == "PASS")
    b_threshold = 3  # 验证方案要求：B表 5 项中至少 3 项通过
    b_ok = b_pass >= b_threshold
    logger.info(f"    📊 B表: {b_pass}/{len(b_results)} 通过（阈值 ≥{b_threshold}）{'✅' if b_ok else '⚠️'}")

    return all_pass


def run_api_e2e(case: dict, case_idx: int) -> dict:
    """通过后端 API + SSE 流进行 E2E 验证，返回 {passed, mode_matched, results}"""
    topic = case["topic"]
    logger.info(f"\n{'='*60}")
    logger.info(f"测试 {case_idx}: {topic}")
    logger.info(f"期望模式: {case['expected_modes']}")
    logger.info(f"验证重点: {case.get('verify_focus', '')}")
    logger.info(f"{'='*60}")

    # 1. 调用异步生成 API
    try:
        resp = requests.post(f"{BACKEND_URL}/api/blog/generate", json={
            "topic": topic,
            "article_type": case["article_type"],
            "target_length": case["target_length"],
            "target_audience": "intermediate",
            "image_style": "",  # 不生成图片
        }, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        task_id = result.get("task_id")
        if not task_id:
            logger.error(f"  ❌ 未获取到 task_id: {result}")
            return {"passed": False, "mode_matched": False, "results": []}
        logger.info(f"  📡 task_id: {task_id}")
    except Exception as e:
        logger.error(f"  ❌ API 调用失败: {e}")
        return {"passed": False, "mode_matched": False, "results": []}

    # 2. 监听 SSE 流，等待 outline_complete 事件
    logger.info(f"  ⏳ 监听 SSE 流等待大纲生成...")
    outline_data = None
    try:
        sse_resp = requests.get(
            f"{BACKEND_URL}/api/tasks/{task_id}/stream",
            stream=True, timeout=300
        )
        client = sseclient.SSEClient(sse_resp)

        for event in client.events():
            if event.event == "result":
                data = json.loads(event.data)
                if data.get("type") == "outline_complete":
                    outline_data = data.get("data", {})
                    logger.info(f"  🎉 收到 outline_complete 事件")
                    logger.info(f"     标题: {outline_data.get('title', '')}")
                    logger.info(f"     章节数: {outline_data.get('sections_count', 0)}")
                    break
            elif event.event == "error":
                data = json.loads(event.data)
                logger.error(f"  ❌ SSE 错误: {data.get('message', '')}")
                return {"passed": False, "mode_matched": False, "results": []}
            elif event.event in ("complete", "cancelled"):
                break

    except Exception as e:
        logger.error(f"  ❌ SSE 监听失败: {e}")
        return {"passed": False, "mode_matched": False, "results": []}

    if not outline_data:
        logger.error(f"  ❌ 未收到 outline_complete 事件")
        return {"passed": False, "mode_matched": False, "results": []}

    # 3. 验证字段（A表 + B表）
    results, mode = validate_outline_from_sse(outline_data, case)
    all_pass = _print_and_check_results(results)
    mode_matched = mode in case["expected_modes"]

    # 4. 取消任务（不需要等后续写作）
    try:
        requests.post(f"{BACKEND_URL}/api/tasks/{task_id}/cancel", timeout=5)
        logger.info(f"  🛑 已取消任务 {task_id}（只需验证大纲）")
    except Exception:
        pass

    return {"passed": all_pass, "mode_matched": mode_matched, "results": results}


# JS 代码：注入到浏览器中，hook EventSource 拦截 SSE 事件
SSE_HOOK_JS = """
(() => {
    window.__sse_outline_data = null;
    window.__sse_events = [];
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
                    }
                } catch(e) {}
                return fn.call(this, evt);
            };
            return origAddEventListener(type, wrapped, ...rest);
        };
        // Also hook onmessage
        const origOnMsg = Object.getOwnPropertyDescriptor(OrigES.prototype, 'onmessage');
        return es;
    };
    window.EventSource.CONNECTING = OrigES.CONNECTING;
    window.EventSource.OPEN = OrigES.OPEN;
    window.EventSource.CLOSED = OrigES.CLOSED;
})();
"""


def run_playwright_e2e(case: dict, case_idx: int, headed: bool) -> dict:
    """通过 Playwright 浏览器进行 E2E 验证，返回 {passed, mode_matched, results}"""
    _fail = {"passed": False, "mode_matched": False, "results": []}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright 未安装，回退到 API E2E 模式")
        return run_api_e2e(case, case_idx)

    topic = case["topic"]
    logger.info(f"\n{'='*60}")
    logger.info(f"🌐 Playwright E2E 测试 {case_idx}: {topic}")
    logger.info(f"期望模式: {case['expected_modes']}")
    logger.info(f"验证重点: {case.get('verify_focus', '')}")
    logger.info(f"{'='*60}")

    outline_data = None
    captured_task_id = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed, slow_mo=200)
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = context.new_page()
        page.set_default_timeout(300000)

        try:
            # Step 1: 打开首页并注入 SSE Hook
            logger.info("  📌 Step 1: 打开首页")
            # 在页面加载前注入 JS hook
            page.add_init_script(SSE_HOOK_JS)
            page.goto(FRONTEND_URL, wait_until='domcontentloaded')
            page.wait_for_timeout(3000)
            logger.info(f"    ✅ 首页加载成功: {page.title()}")
            page.screenshot(path=f'/tmp/e2e_case{case_idx}_step1.png')

            # Step 2: 输入主题
            logger.info(f"  📌 Step 2: 输入主题: {topic}")
            input_selectors = [
                'textarea[placeholder*="输入"]', 'textarea[placeholder*="主题"]',
                'textarea[placeholder*="想写"]', 'textarea',
            ]
            input_found = False
            for selector in input_selectors:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        el.fill(topic)
                        logger.info(f"    ✅ 已输入主题 (selector: {selector})")
                        input_found = True
                        break
                except Exception:
                    continue
            if not input_found:
                logger.error("    ❌ 未找到输入框")
                page.screenshot(path=f'/tmp/e2e_case{case_idx}_step2_fail.png')
                return _fail

            # Step 3: 点击生成
            logger.info(f"  📌 Step 3: 点击生成")
            gen_selectors = [
                '.code-generate-btn', 'button:has-text("execute")',
                'button:has-text("生成")', 'button:has-text("开始")',
                'button:has-text("Generate")', 'button[type="submit"]',
            ]
            gen_btn = None
            for selector in gen_selectors:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=3000) and el.is_enabled(timeout=1000):
                        gen_btn = el
                        logger.info(f"    找到生成按钮: {selector}")
                        break
                except Exception:
                    continue
            if not gen_btn:
                logger.error("    ❌ 未找到生成按钮")
                page.screenshot(path=f'/tmp/e2e_case{case_idx}_step3_fail.png')
                return _fail

            with page.expect_response(
                lambda resp: 'generate' in resp.url and resp.status < 400,
                timeout=60000
            ) as response_info:
                gen_btn.click()
                logger.info(f"    ✅ 已点击生成按钮")

            api_response = response_info.value
            logger.info(f"    🔗 API响应: {api_response.status} {api_response.url}")
            try:
                body = api_response.json()
                captured_task_id = body.get('task_id', '')
            except Exception as e:
                logger.error(f"    ❌ 解析API响应失败: {e}")
                return _fail

            if not captured_task_id:
                logger.error(f"    ❌ 响应中无 task_id: {body}")
                return _fail
            logger.info(f"    📡 task_id: {captured_task_id}")
            page.screenshot(path=f'/tmp/e2e_case{case_idx}_step3.png')

            # Step 4: 轮询浏览器中的 SSE hook 数据，等待 outline_complete
            logger.info(f"  📌 Step 4: 等待大纲生成（通过浏览器内 SSE hook）...")
            max_wait = 300  # 最多等 5 分钟
            poll_interval = 3  # 每 3 秒检查一次
            waited = 0
            while waited < max_wait:
                result = page.evaluate('() => window.__sse_outline_data')
                if result:
                    outline_data = result
                    logger.info(f"    🎉 收到 outline_complete")
                    logger.info(f"       标题: {outline_data.get('title', '')}")
                    logger.info(f"       章节数: {outline_data.get('sections_count', 0)}")
                    break
                page.wait_for_timeout(poll_interval * 1000)
                waited += poll_interval
                if waited % 30 == 0:
                    event_count = page.evaluate('() => window.__sse_events.length')
                    logger.info(f"    ⏳ 已等待 {waited}s，收到 {event_count} 个 SSE 事件")

            page.screenshot(path=f'/tmp/e2e_case{case_idx}_step4.png')

            # 取消任务
            if captured_task_id:
                try:
                    requests.post(f"{BACKEND_URL}/api/tasks/{captured_task_id}/cancel", timeout=5)
                    logger.info(f"  🛑 已取消任务（只需验证大纲）")
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"  ❌ Playwright 异常: {e}")
            return _fail
        finally:
            browser.close()

    if not outline_data:
        logger.error(f"  ❌ 未收到 outline_complete 事件")
        return {"passed": False, "mode_matched": False, "results": []}

    # 验证（A表 + B表）
    results, mode = validate_outline_from_sse(outline_data, case)
    all_pass = _print_and_check_results(results)
    mode_matched = mode in case["expected_modes"]

    return {"passed": all_pass, "mode_matched": mode_matched, "results": results}


def main():
    parser = argparse.ArgumentParser(description="Phase 1 叙事流 E2E 验证（对齐 70.1.1 验证方案）")
    parser.add_argument("--headed", action="store_true", help="Playwright 有头模式")
    parser.add_argument("--api-only", action="store_true", help="仅用 API 模式（不启动浏览器）")
    parser.add_argument("--cases", type=str, default="1,2,3", help="要运行的测试用例编号，逗号分隔")
    args = parser.parse_args()

    case_indices = [int(x) for x in args.cases.split(",")]
    case_results = []  # 收集每个用例的详细结果

    for i, idx in enumerate(case_indices):
        if idx < 1 or idx > len(TEST_CASES):
            continue
        case = TEST_CASES[idx - 1]

        # 用例间等待，确保前一个任务完全清理
        if i > 0:
            logger.info(f"\n⏳ 等待 15 秒让后端清理前一个任务...")
            time.sleep(15)

        if args.api_only:
            result = run_api_e2e(case, idx)
        else:
            result = run_playwright_e2e(case, idx, args.headed)

        # 兼容旧的 bool 返回值
        if isinstance(result, bool):
            result = {"passed": result, "mode_matched": result, "results": []}

        result["topic"] = case["topic"]
        result["case_idx"] = idx
        case_results.append(result)

    # ============================================================
    # 汇总判定 — 对齐 70.1.1 验证方案通过标准
    # ============================================================
    total = len(case_results)
    field_pass = sum(1 for r in case_results if r["passed"])
    mode_match = sum(1 for r in case_results if r["mode_matched"])

    # B表通过数：每个用例的 B 表项中 PASS 的数量
    b_pass_counts = []
    for r in case_results:
        b_items = [item for item in r.get("results", []) if item[1].startswith("B")]
        b_pass = sum(1 for s, _ in b_items if s == "PASS")
        b_pass_counts.append(b_pass)

    print(f"\n{'='*60}")
    print(f"📊 Phase 1 叙事流 E2E 验证汇总")
    print(f"{'='*60}")

    # 逐用例摘要
    for r in case_results:
        icon = "✅" if r["passed"] else "❌"
        mode_icon = "✅" if r["mode_matched"] else "⚠️"
        print(f"  {icon} 用例 {r['case_idx']}: {r['topic']}  模式匹配: {mode_icon}")

    print(f"\n{'─'*60}")
    print(f"  通过标准（对齐 70.1.1 验证方案）：")

    # 标准 1：字段完整性 — 全部主题输出 narrative_mode + narrative_flow + narrative_role
    s1_ok = field_pass == total
    print(f"    {'✅' if s1_ok else '❌'} 字段完整性: {field_pass}/{total} 主题通过（要求全部）")

    # 标准 2：模式匹配 — 至少 2/3 匹配预期
    s2_threshold = max(1, total * 2 // 3)  # 至少 2/3
    s2_ok = mode_match >= s2_threshold
    print(f"    {'✅' if s2_ok else '❌'} 模式匹配: {mode_match}/{total} 匹配（要求 ≥{s2_threshold}）")

    # 标准 3：大纲质量 — 每个用例 B 表 ≥3/5 通过
    s3_ok = all(c >= 3 for c in b_pass_counts) if b_pass_counts else False
    b_detail = ", ".join(f"用例{r['case_idx']}={c}/5" for r, c in zip(case_results, b_pass_counts))
    print(f"    {'✅' if s3_ok else '❌'} 大纲质量: {b_detail}（每个要求 ≥3/5）")

    print(f"{'─'*60}")
    overall = s1_ok and s2_ok and s3_ok
    if overall:
        print(f"  🎉 总体判定：通过")
    else:
        print(f"  ⚠️  总体判定：未通过")
    print(f"{'='*60}")

    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
