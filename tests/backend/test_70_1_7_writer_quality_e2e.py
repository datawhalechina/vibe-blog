"""
[需求点 70.1.7] Step 1.7 writer.j2 完整重构 — 模板渲染 + Playwright E2E 验证

对齐方案文档：vibe-blog-plan-方案/70.1.7. Step1.7-writer.j2完整重构.md

⚠️ 同步警告：
  - 修改本测试文件时，必须同步更新方案文档 70.1.7 的验证方案部分
  - 修改方案文档 70.1.7 的检查清单/通过标准时，必须同步更新本文件的验证逻辑

验证内容：
  A表 — 模板渲染检查（10项，不需要 LLM）
  B表 — 生成质量检查（5项，需要完整生成流程）
  通过标准：
    - 模板渲染：A 表 10 项全部通过
    - 向后兼容：空字段不报错，回退到默认行为
    - 生成质量：B 表 5 项中至少 3 项通过

用法：
    # 仅模板渲染验证（秒级，不需要前后端服务）
    cd backend && python tests/test_70_1_7_writer_quality_e2e.py --render-only

    # 完整 E2E 验证（需要前后端服务）
    cd backend && python tests/test_70_1_7_writer_quality_e2e.py --headed
    cd backend && python tests/test_70_1_7_writer_quality_e2e.py  # 无头模式
"""

import sys
import re
import argparse
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:5001"
FRONTEND_URL = "http://localhost:5173"

# 9 种 narrative_role
ALL_ROLES = ["hook", "what", "why", "how", "compare", "deep_dive", "verify", "summary", "catalog_item"]

# 每种 role 对应的写作策略关键词（用于 A 表断言）
ROLE_STRATEGY_KEYWORDS = {
    "hook": "引子/痛点",
    "what": "概念定义",
    "why": "动机/价值",
    "how": "操作步骤",
    "compare": "对比分析",
    "deep_dive": "深入原理",
    "verify": "验证/测试",
    "summary": "总结/展望",
    "catalog_item": "清单条目",
}

# 硬编码项目名（应已删除）
HARDCODED_NAMES = ["Claude Cowork", "Eigent", "Veo3", "ViMax"]

# AI 高频词黑名单（应在模板中出现作为禁止提示）
AI_BLACKLIST_WORDS = ["至关重要", "此外", "深入探讨", "不可或缺"]

# B 表：生成质量检查的前言黑名单
PREAMBLE_PATTERNS = ["好的", "我来写", "以下是", "当然", "没问题"]


# ═══════════════════════════════════════════════════════════════
# A 表：模板渲染检查（不需要 LLM）
# ═══════════════════════════════════════════════════════════════

def run_render_checks() -> dict:
    """A 表：模板渲染检查（10 项）+ 向后兼容检查"""
    from infrastructure.prompts.prompt_manager import PromptManager
    pm = PromptManager()

    results = []
    compat_results = []

    # ── 完整字段渲染 ──────────────────────────────────────────
    section_full = {
        "id": "section_1",
        "title": "每次都要重复说明？你需要 Skill",
        "narrative_role": "hook",
        "core_question": "读者有没有遇到过每次让 AI 写代码都要重复说明项目规范的痛苦？",
        "target_words": 800,
        "content_outline": ["重复配置的日常场景", "时间浪费的量化", "引出 Skill 的概念"],
        "image_type": "scene",
        "image_description": "开发者反复向 AI 解释项目规范的场景对比图",
        "code_blocks": 0,
    }

    prompt = pm.render_writer(
        section_outline=section_full,
        narrative_mode="what-why-how",
        narrative_flow={
            "reader_start": "知道 Claude Code 但不知道 Skill 是什么",
            "reader_end": "能独立创建和调试 Skill",
            "logic_chain": ["引起兴趣", "建立概念", "感受价值", "动手实践"],
        },
    )

    # A1: 输出规则模块
    a1 = "禁止前言" in prompt
    results.append(("PASS" if a1 else "FAIL", "A1: 输出规则模块（禁止前言）"))

    # A2: 核心问题模块
    a2 = "读者有没有遇到" in prompt
    results.append(("PASS" if a2 else "FAIL", "A2: 核心问题模块（core_question 内容）"))

    # A3: 字数目标模块
    a3 = "800" in prompt and "字" in prompt
    results.append(("PASS" if a3 else "FAIL", "A3: 字数目标模块（target_words）"))

    # A4: 叙事角色策略
    a4 = ROLE_STRATEGY_KEYWORDS["hook"] in prompt
    results.append(("PASS" if a4 else "FAIL", "A4: 叙事角色策略（hook → 引子/痛点）"))

    # A5: 散文优先模块
    a5 = "散文文档" in prompt
    results.append(("PASS" if a5 else "FAIL", "A5: 散文优先模块"))

    # A6: Claim 校准表
    a6 = "最有效的之一" in prompt
    results.append(("PASS" if a6 else "FAIL", "A6: Claim 校准表"))

    # A7: 去 AI 味黑名单
    a7 = all(w in prompt for w in AI_BLACKLIST_WORDS)
    results.append(("PASS" if a7 else "FAIL", "A7: 去 AI 味黑名单（作为禁止提示出现）"))

    # A8: 配图标记模块
    a8 = "[IMAGE:" in prompt and "[CODE:" in prompt
    results.append(("PASS" if a8 else "FAIL", "A8: 配图与代码标记模块"))

    # A9: 无硬编码项目名
    a9 = all(name not in prompt for name in HARDCODED_NAMES)
    results.append(("PASS" if a9 else "FAIL", f"A9: 无硬编码项目名 {HARDCODED_NAMES}"))

    # A10: 9 种 narrative_role 都能渲染
    a10_pass = True
    a10_details = []
    for role in ALL_ROLES:
        sec = {"id": "s1", "title": "test", "narrative_role": role, "content_outline": []}
        try:
            p = pm.render_writer(section_outline=sec)
            keyword = ROLE_STRATEGY_KEYWORDS[role]
            if keyword not in p:
                a10_pass = False
                a10_details.append(f"{role}→缺少'{keyword}'")
        except Exception as e:
            a10_pass = False
            a10_details.append(f"{role}→异常: {e}")
    detail = "全部通过" if a10_pass else f"失败: {', '.join(a10_details)}"
    results.append(("PASS" if a10_pass else "FAIL", f"A10: 9 种 role 渲染 ({detail})"))

    # ── 向后兼容检查 ──────────────────────────────────────────
    section_old = {"id": "s1", "title": "test", "content_outline": ["要点1", "要点2"]}

    try:
        p_old = pm.render_writer(section_outline=section_old)
        compat_results.append(("PASS", "C1: 空字段不报错"))
    except Exception as e:
        compat_results.append(("FAIL", f"C1: 空字段报错: {e}"))

    # C2: 输出规则始终存在
    c2 = "禁止前言" in p_old
    compat_results.append(("PASS" if c2 else "FAIL", "C2: 输出规则始终存在"))

    # C3: 核心问题模块被跳过
    c3 = "核心问题" not in p_old
    compat_results.append(("PASS" if c3 else "FAIL", "C3: 空 core_question 时跳过核心问题模块"))

    # C4: 回退到默认字数范围
    c4 = "500-1500" in p_old or "300-800" in p_old or "400-1000" in p_old or "600-2000" in p_old
    compat_results.append(("PASS" if c4 else "FAIL", "C4: 回退到默认字数范围"))

    return {"a_table": results, "compat": compat_results}


def print_render_results(results: dict) -> bool:
    """打印 A 表 + 兼容性检查结果，返回是否全部通过"""
    all_pass = True

    print("\n" + "=" * 60)
    print("📋 A 表：模板渲染检查")
    print("=" * 60)
    for status, msg in results["a_table"]:
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {msg}")
        if status == "FAIL":
            all_pass = False

    print("\n" + "-" * 60)
    print("🔄 向后兼容检查")
    print("-" * 60)
    for status, msg in results["compat"]:
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {msg}")
        if status == "FAIL":
            all_pass = False

    a_pass = sum(1 for s, _ in results["a_table"] if s == "PASS")
    a_total = len(results["a_table"])
    c_pass = sum(1 for s, _ in results["compat"] if s == "PASS")
    c_total = len(results["compat"])

    print("\n" + "=" * 60)
    verdict = "🎉 全部通过" if all_pass else "⚠️ 存在失败项"
    print(f"📊 A 表: {a_pass}/{a_total} 通过 | 兼容性: {c_pass}/{c_total} 通过 | {verdict}")
    print("=" * 60)

    return all_pass


# ═══════════════════════════════════════════════════════════════
# B 表：生成质量检查（需要完整 E2E 流程）
# ═══════════════════════════════════════════════════════════════

def check_writer_quality(content: str) -> list:
    """B 表：对单个章节的生成内容进行质量检查（5 项）"""
    results = []

    # B1: 无前言
    first_line = content.strip().split("\n")[0] if content.strip() else ""
    b1 = not any(p in first_line for p in PREAMBLE_PATTERNS)
    results.append(("PASS" if b1 else "FAIL", f"B1: 无前言 (首行: '{first_line[:50]}')"))

    # B2: 散文为主（列表占比 < 30%）
    lines = [l for l in content.strip().split("\n") if l.strip()]
    list_lines = [l for l in lines if re.match(r'^\s*[-*•]\s', l) or re.match(r'^\s*\d+\.\s', l)]
    list_ratio = len(list_lines) / max(len(lines), 1)
    b2 = list_ratio < 0.30
    results.append(("PASS" if b2 else "WARN", f"B2: 散文为主 (列表占比: {list_ratio:.0%})"))

    # B3: 无夸张用词
    exaggerations = ["革命性的", "彻底改变了", "完美的", "毫无疑问"]
    found = [w for w in exaggerations if w in content]
    b3 = len(found) == 0
    results.append(("PASS" if b3 else "WARN", f"B3: 无夸张用词 (发现: {found})"))

    # B4: 无 AI 高频词
    ai_words = ["此外", "至关重要", "深入探讨", "不可或缺", "赋能", "值得注意的是", "总而言之", "综上所述"]
    found_ai = [w for w in ai_words if w in content]
    b4 = len(found_ai) == 0
    results.append(("PASS" if b4 else "WARN", f"B4: 无 AI 高频词 (发现: {found_ai})"))

    # B5: 字数合理（至少 200 字）
    char_count = len(content.replace(" ", "").replace("\n", ""))
    b5 = char_count >= 200
    results.append(("PASS" if b5 else "FAIL", f"B5: 字数合理 ({char_count} 字)"))

    return results


def run_e2e_quality_check(headed: bool = False) -> dict:
    """通过 Playwright 运行完整生成流程，检查 Writer 输出质量
    
    复用 e2e_utils 共享模块的 SSE Hook 和前端交互逻辑
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("需要安装 playwright: pip install playwright && playwright install chromium")
        return {"passed": False, "b_table": []}

    # 导入共享的 E2E 工具
    from tests.e2e_utils import SSE_HOOK_JS, run_playwright_generation, cancel_task

    topic = "什么是 RAG"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed, slow_mo=200)
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = context.new_page()
        page.set_default_timeout(300000)

        # 注入共享的 SSE Hook
        page.add_init_script(SSE_HOOK_JS)

        # 使用共享的前端交互流程，等待至少一个章节完成
        result = run_playwright_generation(
            page=page,
            topic=topic,
            wait_for="section",  # 等待 section_complete
            max_wait=1800,
            screenshot_prefix="70_1_7"
        )

        # 取消任务
        cancel_task(result.get("task_id"))
        browser.close()

    if not result["success"] or not result["sections"]:
        logger.error(f"E2E 失败: {result.get('error', '未收到章节')}")
        return {"passed": False, "b_table": [], "error": result.get("error")}

    # 获取第一个章节的内容
    first_section = result["sections"][0]
    content = first_section.get("content", "") if isinstance(first_section, dict) else str(first_section)

    # 对第一个章节做 B 表检查（原定 5 项质量检查）
    b_results = check_writer_quality(content)
    b_pass = sum(1 for s, _ in b_results if s == "PASS")

    return {"passed": b_pass >= 3, "b_table": b_results, "sections_count": len(result["sections"])}


def print_e2e_results(results: dict) -> bool:
    """打印 B 表结果"""
    print("\n" + "=" * 60)
    print("📋 B 表：生成质量检查")
    print("=" * 60)

    if not results.get("b_table"):
        print("  ❌ 未获取到生成内容，无法检查")
        return False

    for status, msg in results["b_table"]:
        icon = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
        print(f"  {icon} {msg}")

    b_pass = sum(1 for s, _ in results["b_table"] if s == "PASS")
    b_total = len(results["b_table"])
    passed = b_pass >= 3

    print(f"\n  📊 B 表: {b_pass}/{b_total} 通过 (需 ≥3)")
    print(f"  📄 共收到 {results.get('sections_count', 0)} 个章节")
    print("=" * 60)

    return passed


# ═══════════════════════════════════════════════════════════════
# main
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="[70.1.7] writer.j2 重构验证")
    parser.add_argument("--render-only", action="store_true", help="仅运行模板渲染检查（不需要前后端服务）")
    parser.add_argument("--headed", action="store_true", help="有头模式运行 Playwright")
    args = parser.parse_args()

    overall_pass = True

    # A 表：模板渲染检查（始终运行）
    logger.info("开始 A 表：模板渲染检查...")
    render_results = run_render_checks()
    a_pass = print_render_results(render_results)
    if not a_pass:
        overall_pass = False

    # B 表：生成质量检查（仅非 render-only 模式）
    if not args.render_only:
        logger.info("\n开始 B 表：Playwright E2E 生成质量检查...")
        e2e_results = run_e2e_quality_check(headed=args.headed)
        b_pass = print_e2e_results(e2e_results)
        if not b_pass:
            overall_pass = False
    else:
        logger.info("\n跳过 B 表（--render-only 模式）")

    # 最终判定
    print("\n" + "=" * 60)
    if overall_pass:
        print("🎉 [70.1.7] writer.j2 重构验证：全部通过")
    else:
        print("⚠️  [70.1.7] writer.j2 重构验证：存在失败项")
    print("=" * 60)

    sys.exit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
