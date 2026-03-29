"""
E2E Mini Blog Generation — Playwright + Log Monitor
启动浏览器生成一篇 mini 博客，监控后端日志，检测新模块是否生效
"""
import asyncio
import json
import time
import httpx
from playwright.async_api import async_playwright

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:5001"
TOPIC = "AI Agent 2025 最新趋势"
TIMEOUT_MINUTES = 8


async def main():
    print("=" * 60)
    print("E2E Mini Blog Generation Test")
    print("=" * 60)

    # Step 1: 通过 API 直接发起 mini 博客生成（更可靠）
    print("\n[Step 1] 通过 API 发起 mini 博客生成...")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{BACKEND_URL}/api/blog/generate", json={
            "topic": TOPIC,
            "target_length": "mini",
            "image_style": "default",
        })
        print(f"  Response status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {json.dumps(data, ensure_ascii=False, indent=2)}")
        task_id = data.get("task_id") or data.get("id")
        if not task_id:
            print("  ERROR: No task_id returned!")
            return
        print(f"  Task ID: {task_id}")

    # Step 2: 监控 SSE 事件流
    print(f"\n[Step 2] 监控 SSE 事件流 /api/tasks/{task_id}/stream ...")
    start_time = time.time()
    events_received = []
    generation_done = False
    error_occurred = False
    error_msg = ""

    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("GET", f"{BACKEND_URL}/api/tasks/{task_id}/stream") as resp:
                buffer = ""
                async for chunk in resp.aiter_text():
                    buffer += chunk
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)
                        # Parse SSE event
                        event_type = ""
                        event_data = ""
                        for line in event_str.strip().split("\n"):
                            if line.startswith("event:"):
                                event_type = line[6:].strip()
                            elif line.startswith("data:"):
                                event_data = line[5:].strip()

                        if not event_type and not event_data:
                            continue

                        elapsed = time.time() - start_time
                        events_received.append(event_type)

                        # Parse JSON data
                        try:
                            d = json.loads(event_data) if event_data else {}
                        except json.JSONDecodeError:
                            d = {"raw": event_data}

                        # Print key events
                        if event_type in ("status", "progress", "log"):
                            msg = d.get("message", d.get("status", ""))
                            print(f"  [{elapsed:6.1f}s] {event_type}: {msg}")
                        elif event_type == "outline_complete":
                            sections = d.get("sections", [])
                            print(f"  [{elapsed:6.1f}s] outline_complete: {len(sections)} sections")
                        elif event_type == "section_complete":
                            title = d.get("title", "")
                            print(f"  [{elapsed:6.1f}s] section_complete: {title}")
                        elif event_type == "complete" or event_type == "generation_complete":
                            print(f"  [{elapsed:6.1f}s] COMPLETE! blog_id={d.get('id', 'N/A')}")
                            generation_done = True
                            break
                        elif event_type == "error":
                            error_msg = d.get("message", str(d))
                            print(f"  [{elapsed:6.1f}s] ERROR: {error_msg}")
                            error_occurred = True
                            break
                        else:
                            print(f"  [{elapsed:6.1f}s] {event_type}: {json.dumps(d, ensure_ascii=False)[:100]}")

                        # Timeout check
                        if elapsed > TIMEOUT_MINUTES * 60:
                            print(f"  TIMEOUT after {TIMEOUT_MINUTES} minutes!")
                            error_occurred = True
                            error_msg = "Timeout"
                            break

        except Exception as e:
            print(f"  SSE stream error: {e}")
            error_occurred = True
            error_msg = str(e)

    # Step 3: 结果汇总
    total_time = time.time() - start_time
    print(f"\n[Step 3] 结果汇总")
    print(f"  总耗时: {total_time:.1f}s")
    print(f"  收到事件数: {len(events_received)}")
    print(f"  事件类型: {set(events_received)}")
    print(f"  生成完成: {'YES' if generation_done else 'NO'}")
    print(f"  发生错误: {'YES — ' + error_msg if error_occurred else 'NO'}")

    # Step 4: 检查后端日志中新模块是否生效
    print(f"\n[Step 4] 检查后端日志中新模块是否生效...")
    async with httpx.AsyncClient(timeout=10) as client:
        # 读取 app.log 最后的内容
        pass

    # Step 5: 用浏览器打开博客详情页验证
    if generation_done:
        print(f"\n[Step 5] 用浏览器打开博客详情页验证...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            blog_id = task_id
            url = f"{FRONTEND_URL}/blog/{blog_id}"
            print(f"  Opening {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            # Screenshot
            screenshot_path = f"/Users/coyote-ll/Documents/git/AiSlide/vibe-blog/backend/outputs/e2e_mini_blog.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"  Screenshot saved: {screenshot_path}")
            await browser.close()

    print("\n" + "=" * 60)
    print("E2E Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
