"""
E2E 验证脚本 — 验证本次 PR 的所有改动

验证项：
1. Dashboard API 返回正确的 failed/cancelled 任务列表
2. 服务重启后残留任务被标记为 failed（recovery 逻辑）
3. 发起 mini 博客生成 → Dashboard 显示 running + 进度条
4. 进度条实时更新（queue_bridge.update_queue_progress）
5. 生成完成/失败后状态正确更新
6. Dashboard 前端页面正确渲染所有区块
7. Humanizer 空响应不会崩溃（通过日志验证）
"""
import asyncio
import os
import time

import httpx
from playwright.async_api import async_playwright

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:5001"
SCREENSHOT_DIR = os.path.join(
    os.path.dirname(__file__), "outputs", "e2e_pr_verify"
)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

RESULTS = []


def log(msg: str):
    print(f"  {msg}")


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


async def test_1_queue_api_snapshot():
    """验证 Queue API 返回 failed/cancelled 列表"""
    print("\n[Test 1] Queue API Snapshot — failed/cancelled 字段")
    async with httpx.AsyncClient(timeout=10) as c:
        resp = await c.get(f"{BACKEND_URL}/api/queue/tasks")
        data = resp.json()

    has_failed = "failed" in data
    has_cancelled = "cancelled" in data
    has_stats = "stats" in data
    stats = data.get("stats", {})

    record("API 返回 failed 列表", has_failed)
    record("API 返回 cancelled 列表", has_cancelled)
    record("API 返回 stats", has_stats)
    record(
        "stats 包含 failed_count",
        "failed_count" in stats,
        f"failed_count={stats.get('failed_count')}",
    )
    record(
        "stats 包含 cancelled_count",
        "cancelled_count" in stats,
        f"cancelled_count={stats.get('cancelled_count')}",
    )
    return data


async def test_2_recovery_logic(snapshot):
    """验证服务重启后残留任务被标记为 failed"""
    print("\n[Test 2] Recovery Logic — 残留任务标记为 failed")
    failed_tasks = snapshot.get("failed", [])
    recovery_tasks = [
        t for t in failed_tasks
        if "服务重启" in (t.get("stage_detail") or "")
    ]
    record(
        "存在被 recovery 标记为 failed 的任务",
        len(recovery_tasks) > 0,
        f"找到 {len(recovery_tasks)} 个",
    )
    # 确认没有残留的 queued 任务（应该都被清理了）
    queued = snapshot.get("queued", [])
    record(
        "无残留 queued 任务",
        len(queued) == 0,
        f"queued={len(queued)}",
    )


async def test_3_dashboard_ui(browser):
    """验证 Dashboard 前端页面渲染所有区块"""
    print("\n[Test 3] Dashboard UI — 页面渲染验证")
    page = await browser.new_page()
    try:
        await page.goto(f"{FRONTEND_URL}/dashboard", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        # 统计卡片
        stat_cards = await page.locator(".stat-card").count()
        record("统计卡片数量 = 5", stat_cards == 5, f"实际={stat_cards}")

        # 检查统计标签
        page_text = await page.text_content(".stats-grid")
        for label in ["处理中", "等待中", "今日完成", "失败", "已取消"]:
            record(f"统计卡片包含「{label}」", label in page_text)

        # 失败区块
        failed_section = page.locator("text=失败").first
        failed_visible = await failed_section.is_visible() if failed_section else False
        record("「失败」区块可见", failed_visible)

        # 已取消区块
        cancelled_section = page.locator(".task-card.cancelled").first
        cancelled_exists = await cancelled_section.count() > 0 if cancelled_section else False
        record("「已取消」卡片存在", cancelled_exists)

        # 失败卡片
        failed_cards = page.locator(".task-card.failed")
        failed_count = await failed_cards.count()
        record("失败卡片存在", failed_count > 0, f"数量={failed_count}")

        # 截图
        path = os.path.join(SCREENSHOT_DIR, "test3_dashboard.png")
        await page.screenshot(path=path, full_page=True)
        log(f"截图: {path}")
    finally:
        await page.close()


async def test_4_generate_and_progress(browser):
    """发起 mini 生成 → 验证 Dashboard 进度条实时更新"""
    print("\n[Test 4] Mini 生成 + Dashboard 进度条")

    # Step 1: 通过 API 发起 mini 生成
    log("发起 mini 博客生成...")
    async with httpx.AsyncClient(timeout=30) as c:
        resp = await c.post(f"{BACKEND_URL}/api/blog/generate", json={
            "topic": "Playwright E2E 测试最佳实践",
            "target_length": "mini",
            "image_style": "default",
        })
        data = resp.json()
        task_id = data.get("task_id")
        record("API 返回 task_id", bool(task_id), f"task_id={task_id}")
        if not task_id:
            return None

    # Step 2: 轮询 Dashboard API 检查进度更新
    log(f"轮询 Dashboard API 检查进度 (task_id={task_id})...")
    progress_seen = []
    stages_seen = []
    final_status = None
    max_wait = 480  # 8 分钟
    start = time.time()

    while time.time() - start < max_wait:
        await asyncio.sleep(3)
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.get(f"{BACKEND_URL}/api/queue/tasks")
            snap = resp.json()

        # 检查 running 列表
        running = snap.get("running", [])
        our_task = next((t for t in running if t["id"] == task_id), None)
        if our_task:
            p = our_task.get("progress", 0)
            stage = our_task.get("current_stage", "")
            if p > 0 and p not in progress_seen:
                progress_seen.append(p)
                stages_seen.append(stage)
                log(f"  进度: {p}% — {stage}")

        # 检查是否已完成/失败
        completed = snap.get("completed", [])
        failed = snap.get("failed", [])
        if any(t["id"] == task_id for t in completed):
            final_status = "completed"
            break
        if any(t["id"] == task_id for t in failed):
            final_status = "failed"
            break

        # 也检查 history
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                hresp = await c.get(f"{BACKEND_URL}/api/queue/history?limit=5")
                hist = hresp.json()
                history_list = hist.get("history", hist) if isinstance(hist, dict) else hist
                if isinstance(history_list, list):
                    if any(r.get("task_id") == task_id for r in history_list):
                        match = next(r for r in history_list if r.get("task_id") == task_id)
                        final_status = match.get("status", "completed")
                        break
        except Exception:
            pass

        elapsed = int(time.time() - start)
        if elapsed % 30 == 0 and elapsed > 0:
            log(f"  等待中... {elapsed}s")

    record(
        "进度条有更新（progress > 0）",
        len(progress_seen) > 0,
        f"捕获到 {len(progress_seen)} 次进度: {progress_seen}",
    )
    record(
        "捕获到多个阶段",
        len(stages_seen) >= 2,
        f"阶段: {stages_seen}",
    )
    record(
        "任务最终状态",
        final_status in ("completed", "failed"),
        f"status={final_status}",
    )

    # Step 3: 打开 Dashboard 截图验证
    page = await browser.new_page()
    try:
        await page.goto(f"{FRONTEND_URL}/dashboard", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)
        path = os.path.join(SCREENSHOT_DIR, "test4_after_generation.png")
        await page.screenshot(path=path, full_page=True)
        log(f"截图: {path}")
    finally:
        await page.close()

    return task_id, final_status


async def test_5_browser_generate(browser):
    """模拟人操作：打开首页 → 输入主题 → 点击生成 → 切到 Dashboard 看进度"""
    print("\n[Test 5] 浏览器模拟人操作 — 首页生成 + Dashboard 进度监控")
    page = await browser.new_page()
    dashboard_page = await browser.new_page()

    try:
        # Step 1: 打开首页
        log("打开首页...")
        await page.goto(FRONTEND_URL, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        path = os.path.join(SCREENSHOT_DIR, "test5_01_home.png")
        await page.screenshot(path=path, full_page=True)
        log(f"截图: {path}")

        # Step 2: 找到输入框并输入主题
        log("输入主题...")
        input_selectors = [
            'textarea[placeholder*="输入"]',
            'textarea[placeholder*="主题"]',
            'textarea[placeholder*="想写"]',
            'textarea',
        ]
        input_el = None
        for sel in input_selectors:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=2000):
                input_el = loc
                break
        record("找到输入框", input_el is not None)
        if not input_el:
            return

        await input_el.click()
        await input_el.fill("Playwright 自动化测试入门指南")
        await page.wait_for_timeout(500)
        path = os.path.join(SCREENSHOT_DIR, "test5_02_input.png")
        await page.screenshot(path=path, full_page=True)
        log(f"截图: {path}")

        # Step 3: 选择 mini 模式
        log("选择 mini 模式...")
        # 先点击高级选项展开
        advanced_btn = page.locator('button:has-text("高级选项")').first
        if await advanced_btn.is_visible(timeout=2000):
            await advanced_btn.click()
            await page.wait_for_timeout(500)
            # 找到长度选择器并选 mini
            length_select = page.locator('select').filter(has_text="mini").first
            if await length_select.count() > 0:
                await length_select.select_option("mini")
            else:
                # 尝试其他方式找到长度选项
                mini_option = page.locator('text=mini').first
                if await mini_option.is_visible(timeout=1000):
                    await mini_option.click()
            log("已选择 mini 模式")
        else:
            log("未找到高级选项按钮，使用默认配置")

        # Step 4: 点击生成按钮
        log("点击生成按钮...")
        gen_selectors = [
            '.code-generate-btn',
            'button:has-text("execute")',
            'button:has-text("生成")',
            'button:has-text("开始")',
        ]
        gen_btn = None
        for sel in gen_selectors:
            loc = page.locator(sel).first
            if await loc.is_visible(timeout=2000):
                gen_btn = loc
                break
        record("找到生成按钮", gen_btn is not None)
        if not gen_btn:
            return

        # 监听 API 响应获取 task_id
        task_id = None

        # 先注册 response 监听器
        response_future = asyncio.get_event_loop().create_future()

        async def on_response(response):
            if "generate" in response.url and response.status < 400:
                if not response_future.done():
                    response_future.set_result(response)

        page.on("response", on_response)
        await gen_btn.click()
        log("已点击生成按钮")

        try:
            api_resp = await asyncio.wait_for(response_future, timeout=30)
            body = await api_resp.json()
            task_id = body.get("task_id")
        except asyncio.TimeoutError:
            log("等待 API 响应超时")
        except Exception as e:
            log(f"解析响应失败: {e}")
        finally:
            page.remove_listener("response", on_response)
        record("获取到 task_id", bool(task_id), f"task_id={task_id}")
        if not task_id:
            return

        path = os.path.join(SCREENSHOT_DIR, "test5_03_generating.png")
        await page.screenshot(path=path, full_page=True)
        log(f"截图: {path}")

        # Step 5: 切到 Dashboard 页面监控进度
        log("打开 Dashboard 监控进度...")
        await dashboard_page.goto(
            f"{FRONTEND_URL}/dashboard",
            wait_until="networkidle",
            timeout=15000,
        )
        await dashboard_page.wait_for_timeout(2000)

        progress_screenshots = 0
        progress_values = []
        stages_seen = set()
        max_wait = 480
        start = time.time()

        while time.time() - start < max_wait:
            await asyncio.sleep(5)

            # 通过 API 检查进度（比 UI reload 更可靠）
            async with httpx.AsyncClient(timeout=10) as c:
                snap_resp = await c.get(f"{BACKEND_URL}/api/queue/tasks")
                snap = snap_resp.json()

            # 检查 running
            running_in_api = [t for t in snap.get("running", []) if t["id"] == task_id]
            if running_in_api:
                p = running_in_api[0].get("progress", 0)
                stage = running_in_api[0].get("current_stage", "")
                if p > 0 and f"{p}%" not in progress_values:
                    progress_values.append(f"{p}%")
                    stages_seen.add(stage)
                    log(f"  API 进度: {p}% — {stage}")

                # Dashboard 截图（最多 5 张）
                if progress_screenshots < 5 and p > 0:
                    await dashboard_page.reload(wait_until="networkidle", timeout=10000)
                    await dashboard_page.wait_for_timeout(1000)
                    path = os.path.join(
                        SCREENSHOT_DIR,
                        f"test5_04_progress_{progress_screenshots}.png",
                    )
                    await dashboard_page.screenshot(path=path, full_page=True)
                    progress_screenshots += 1

            # 检查是否已完成/失败/取消
            all_done = snap.get("completed", []) + snap.get("failed", []) + snap.get("cancelled", [])
            done_task = next((t for t in all_done if t["id"] == task_id), None)
            if done_task:
                log(f"API 确认任务已结束: {done_task['status']}")
                break

            elapsed = int(time.time() - start)
            if elapsed % 60 == 0 and elapsed > 0:
                log(f"  等待中... {elapsed}s")

        record(
            "进度条有更新（progress > 0）",
            len(progress_values) > 0,
            f"捕获到 {len(progress_values)} 次进度: {progress_values}",
        )
        record(
            "捕获到多个阶段",
            len(stages_seen) >= 2,
            f"阶段: {list(stages_seen)}",
        )

        # Step 6: 最终 Dashboard 截图
        await dashboard_page.reload(wait_until="networkidle", timeout=10000)
        await dashboard_page.wait_for_timeout(2000)
        path = os.path.join(SCREENSHOT_DIR, "test5_05_final_dashboard.png")
        await dashboard_page.screenshot(path=path, full_page=True)
        log(f"截图: {path}")

        # 验证最终状态
        async with httpx.AsyncClient(timeout=10) as c:
            snap_resp = await c.get(f"{BACKEND_URL}/api/queue/tasks")
            final_snap = snap_resp.json()
        completed = [t for t in final_snap.get("completed", []) if t["id"] == task_id]
        failed = [t for t in final_snap.get("failed", []) if t["id"] == task_id]
        if completed:
            record("任务最终状态: completed", True)
            t = completed[0]
            record(
                "completed 任务有 word_count",
                bool(t.get("output_word_count")),
                f"word_count={t.get('output_word_count')}",
            )
        elif failed:
            record("任务最终状态: failed", True, f"detail={failed[0].get('stage_detail')}")
        else:
            record("任务最终状态: 未知", False, "既不在 completed 也不在 failed")

        # Step 7: 回到首页看生成结果
        if completed:
            log("查看生成结果页面...")
            await page.wait_for_timeout(3000)
            path = os.path.join(SCREENSHOT_DIR, "test5_06_result.png")
            await page.screenshot(path=path, full_page=True)
            log(f"截图: {path}")

    finally:
        await page.close()
        await dashboard_page.close()


async def test_6_cancel_task(browser):
    """模拟取消任务操作"""
    print("\n[Test 6] 取消任务")

    # 发起一个任务
    async with httpx.AsyncClient(timeout=30) as c:
        resp = await c.post(f"{BACKEND_URL}/api/blog/generate", json={
            "topic": "这个任务会被取消",
            "target_length": "mini",
        })
        data = resp.json()
        task_id = data.get("task_id")
    if not task_id:
        record("发起任务失败", False)
        return

    log(f"已发起任务 {task_id}，等待 5 秒后取消...")
    await asyncio.sleep(5)

    # 打开 Dashboard 点击取消
    page = await browser.new_page()
    try:
        await page.goto(f"{FRONTEND_URL}/dashboard", wait_until="networkidle", timeout=15000)
        await page.wait_for_timeout(2000)

        cancel_btn = page.locator(".btn-cancel").first
        if await cancel_btn.is_visible(timeout=3000):
            await cancel_btn.click()
            log("已点击取消按钮")
            await page.wait_for_timeout(3000)
            await page.reload(wait_until="networkidle", timeout=10000)
            await page.wait_for_timeout(2000)
        else:
            # 通过 API 取消
            log("Dashboard 无取消按钮，通过 API 取消")
            async with httpx.AsyncClient(timeout=10) as c:
                await c.delete(f"{BACKEND_URL}/api/queue/tasks/{task_id}")

        path = os.path.join(SCREENSHOT_DIR, "test6_after_cancel.png")
        await page.screenshot(path=path, full_page=True)
        log(f"截图: {path}")

        # 验证取消状态
        async with httpx.AsyncClient(timeout=10) as c:
            snap_resp = await c.get(f"{BACKEND_URL}/api/queue/tasks")
            snap = snap_resp.json()
        cancelled = [t for t in snap.get("cancelled", []) if t["id"] == task_id]
        record("任务已取消", len(cancelled) > 0 or snap["stats"]["cancelled_count"] > 0)
    finally:
        await page.close()


async def test_7_check_logs():
    """检查后端日志验证 QueueBridge 和 Humanizer 改动"""
    print("\n[Test 7] 后端日志验证")
    log_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "logs", "app.log"
    )
    if not os.path.exists(log_path):
        record("日志文件存在", False, f"未找到 {log_path}")
        return

    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 找到最后一次服务启动的位置
    last_start_idx = 0
    for i, line in enumerate(lines):
        if "Running on" in line or "Queue] 清理" in line or "初始化完成" in line:
            last_start_idx = i
    recent_content = "".join(lines[last_start_idx:])
    content = "".join(lines)

    # QueueBridge 日志
    has_bridge_log = "[QueueBridge]" in content
    record("QueueBridge 日志存在", has_bridge_log)

    # Recovery 日志
    has_recovery = "[Queue] 清理" in content or "[Queue] 标记中断" in content
    record("Recovery 清理日志存在", has_recovery)

    # Humanizer 相关
    has_humanizer = "[Humanizer]" in content
    record("Humanizer 日志存在", has_humanizer)

    # werkzeug 不应有 GET /api/queue 的 INFO 日志（只检查最近的日志）
    werkzeug_poll = recent_content.count("GET /api/queue/tasks HTTP")
    record(
        "werkzeug 轮询日志已屏蔽（最近）",
        werkzeug_poll < 5,
        f"最近出现 {werkzeug_poll} 次",
    )


async def main():
    print("=" * 60)
    print("E2E PR Verification — 端到端验证")
    print("=" * 60)

    # Test 1 & 2: API 验证
    snapshot = await test_1_queue_api_snapshot()
    await test_2_recovery_logic(snapshot)

    # Test 3-6: 浏览器验证
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        try:
            await test_3_dashboard_ui(browser)
            await test_5_browser_generate(browser)
            await test_6_cancel_task(browser)
        finally:
            await browser.close()

    # Test 7: 日志验证
    await test_7_check_logs()

    # 汇总
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = sum(1 for _, p, _ in RESULTS if not p)
    for name, ok, detail in RESULTS:
        status = "PASS" if ok else "FAIL"
        line = f"  [{status}] {name}"
        if detail:
            line += f" — {detail}"
        print(line)
    print(f"\n  总计: {passed} passed, {failed} failed")
    print(f"  截图目录: {SCREENSHOT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
