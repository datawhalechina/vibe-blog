"""
[需求点 70.1.2] Step 1.2 Planner 字数分配规则 — E2E 验证

对齐方案文档：vibe-blog-plan-方案/70.1.2. Step1.2-字数分配规则.md

⚠️ 同步警告：
  - 修改本测试文件时，必须同步更新方案文档 70.1.2 的验证方案部分
  - 修改方案文档 70.1.2 的检查清单/通过标准时，必须同步更新本文件的验证逻辑

验证内容：
  A表 — 字段检查（5项）
  B表 — 合理性检查（3项）
  通过标准：
    - 字段完整性：3 个主题全部输出 target_words
    - 总和准确：3 个主题的字数总和误差均 ≤10%
    - 比例合理：至少 2/3 主题的字数分配符合推荐比例

用法：
    cd backend && python tests/test_70_1_2_word_allocation_e2e.py --headed
    cd backend && python tests/test_70_1_2_word_allocation_e2e.py --headed --cases 1
    cd backend && python tests/test_70_1_2_word_allocation_e2e.py  # 无头模式
    cd backend && python tests/test_70_1_2_word_allocation_e2e.py --api-only  # 仅 API 模式

注意：
    - 本测试使用 Playwright 进行真实浏览器自动化
    - 支持 --headed（有头模式）、--headless（无头模式）、--api-only（仅 API）
    - 测试会等待 outline_complete 事件，然后验证字数分配
"""

import sys
import os
import json
import time
import argparse
import logging
import requests

# 添加当前目录到 Python 路径，以便导入 e2e_utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e2e_utils import (
    SSE_HOOK_JS, run_playwright_generation, cancel_task,
    BACKEND_URL, FRONTEND_URL
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# 测试主题矩阵 — 对齐 70.1.2 验证方案
TEST_CASES = [
    {
        "topic": "什么是 RAG",
        "article_type": "tutorial",
        "target_length": "mini",
        "expected_total_words": 2000,
        "tolerance": 0.10,  # 10% tolerance
    },
    {
        "topic": "手把手搭建 RAG 系统",
        "article_type": "tutorial",
        "target_length": "medium",
        "expected_total_words": 6000,
        "tolerance": 0.10,
    },
    {
        "topic": "10 个 RAG 性能优化技巧",
        "article_type": "tutorial",
        "target_length": "long",
        "expected_total_words": 10000,
        "tolerance": 0.10,
    },
]

# narrative_role 推荐比例（对齐 planner.j2）
ROLE_PERCENTAGES = {
    "hook": (0.10, 0.15),
    "what": (0.15, 0.20),
    "why": (0.10, 0.15),
    "how": (0.25, 0.35),
    "deep_dive": (0.20, 0.30),
    "compare": (0.15, 0.20),
    "verify": (0.10, 0.15),
    "summary": (0.05, 0.10),
}


def validate_field_completeness(outline: dict, expected_total: int) -> dict:
    """
    A表 — 字段检查（对齐 70.1.2 验证方案 A 表）

    检查项：
    1. 每个 section 有 target_words 字段（整数，> 0）
    2. 所有 section 的 target_words 之和与总目标字数误差 ≤10%
    """
    results = {
        "has_target_words": True,
        "all_positive": True,
        "sum_accuracy": None,
        "sum_error_pct": None,
        "total_words": 0,
        "details": []
    }

    sections = outline.get("sections", [])
    if not sections:
        results["has_target_words"] = False
        results["details"].append("No sections found")
        return results

    # Check 1: 每个 section 有 target_words 字段
    total_words = 0
    for i, section in enumerate(sections):
        # 确保 section 是字典类型
        if not isinstance(section, dict):
            results["has_target_words"] = False
            results["details"].append(f"Section {i+1} is not a dict: {type(section)}")
            continue

        if "target_words" not in section:
            results["has_target_words"] = False
            results["details"].append(f"Section {i+1} '{section.get('title', '')}' missing target_words")
        else:
            tw = section["target_words"]
            if not isinstance(tw, (int, float)) or tw <= 0:
                results["all_positive"] = False
                results["details"].append(f"Section {i+1} '{section.get('title', '')}' target_words invalid: {tw}")
            else:
                total_words += int(tw)

    results["total_words"] = total_words

    # Check 2: 所有 section 的 target_words 之和
    if total_words > 0:
        error_pct = abs(total_words - expected_total) / expected_total
        results["sum_error_pct"] = error_pct
        results["sum_accuracy"] = error_pct <= 0.10  # 10% tolerance
        results["details"].append(
            f"Total words: {total_words}, Expected: {expected_total}, Error: {error_pct:.1%}"
        )
    else:
        results["sum_accuracy"] = False
        results["details"].append("Total words is 0")

    return results


def validate_allocation_ratios(outline: dict, expected_total: int) -> dict:
    """
    B表 — 合理性检查（对齐 70.1.2 验证方案 B 表）

    检查项：
    1. 最大章节字数 ≤ 总字数 40%
    2. 最小章节字数 ≥ 200 字
    3. 字数分配与 narrative_role 匹配
    """
    results = {
        "max_section_ok": True,
        "min_section_ok": True,
        "ratio_matches": 0,
        "ratio_total": 0,
        "details": []
    }

    sections = outline.get("sections", [])
    # 确保所有 sections 都是字典
    sections = [s for s in sections if isinstance(s, dict)]
    total_words = sum(s.get("target_words", 0) for s in sections)

    if total_words == 0:
        results["details"].append("Total words is 0, cannot validate ratios")
        return results

    for section in sections:
        tw = section.get("target_words", 0)
        role = section.get("narrative_role", "")
        title = section.get("title", "")
        pct = tw / total_words if total_words > 0 else 0

        # Check 1: 最大章节字数 ≤ 总字数 40%
        if pct > 0.40:
            results["max_section_ok"] = False
            results["details"].append(f"Section '{title}' too large: {pct:.1%} (>{40}%)")

        # Check 2: 最小章节字数 ≥ 200 字
        if tw < 200:
            results["min_section_ok"] = False
            results["details"].append(f"Section '{title}' too small: {tw} words (<200)")

        # Check 3: 字数分配与 narrative_role 匹配
        if role in ROLE_PERCENTAGES:
            min_pct, max_pct = ROLE_PERCENTAGES[role]
            results["ratio_total"] += 1
            if min_pct <= pct <= max_pct:
                results["ratio_matches"] += 1
            else:
                results["details"].append(
                    f"Section '{title}' ({role}) ratio {pct:.1%} "
                    f"outside expected {min_pct:.0%}-{max_pct:.0%}"
                )

    return results


def run_api_e2e(case: dict, case_idx: int) -> dict:
    """
    通过后端 API + SSE 流进行 E2E 验证

    Returns:
        {
            "passed": bool,
            "field_results": dict,
            "ratio_results": dict,
            "outline": dict | None
        }
    """
    topic = case["topic"]
    logger.info(f"\n{'='*60}")
    logger.info(f"🔧 API E2E 测试 {case_idx}: {topic}")
    logger.info(f"目标长度: {case['target_length']} ({case['expected_total_words']} 字)")
    logger.info(f"{'='*60}")

    # Step 1: 调用异步生成 API
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
            return {"passed": False, "field_results": {}, "ratio_results": {}, "outline": None}
        logger.info(f"  📡 task_id: {task_id}")
    except Exception as e:
        logger.error(f"  ❌ API 调用失败: {e}")
        return {"passed": False, "field_results": {}, "ratio_results": {}, "outline": None}

    # Step 2: 监听 SSE 流，等待 outline_complete 事件
    logger.info(f"  ⏳ 监听 SSE 流等待大纲生成...")
    outline_data = None
    try:
        sse_resp = requests.get(
            f"{BACKEND_URL}/api/tasks/{task_id}/stream",
            stream=True, timeout=300
        )
        sse_resp.raise_for_status()

        # 解析 SSE 流
        for line in sse_resp.iter_lines():
            if not line:
                continue
            line_str = line.decode('utf-8')

            # SSE format: "event: <type>\ndata: <json>"
            if line_str.startswith('data: '):
                try:
                    data = json.loads(line_str[6:])
                    event_type = data.get('type')

                    if event_type == 'outline_complete':
                        outline_data = data.get('data', {})
                        # 调试：打印原始数据结构
                        logger.info(f"  🔍 DEBUG: outline_data keys: {list(outline_data.keys())}")
                        logger.info(f"  🔍 DEBUG: sections type: {type(outline_data.get('sections'))}")
                        if outline_data.get('sections'):
                            logger.info(f"  🔍 DEBUG: first section type: {type(outline_data['sections'][0])}")
                        logger.info(f"  🎉 收到 outline_complete 事件")
                        logger.info(f"     标题: {outline_data.get('title', '')}")
                        logger.info(f"     章节数: {len(outline_data.get('sections', []))}")
                        break
                    elif event_type == 'error':
                        logger.error(f"  ❌ SSE 错误: {data.get('message', '')}")
                        return {"passed": False, "field_results": {}, "ratio_results": {}, "outline": None}
                    elif event_type == 'complete':
                        # 如果收到 complete 但没有 outline，尝试从 data 中提取
                        if not outline_data:
                            final_data = data.get('data', {})
                            outline_data = final_data.get('outline')
                        break
                except json.JSONDecodeError:
                    continue

    except Exception as e:
        logger.error(f"  ❌ SSE 监听失败: {e}")
        return {"passed": False, "field_results": {}, "ratio_results": {}, "outline": None}

    # 取消任务（不需要等后续写作）
    cancel_task(task_id)

    if not outline_data:
        logger.error(f"  ❌ 未收到 outline_complete 事件")
        return {"passed": False, "field_results": {}, "ratio_results": {}, "outline": None}

    # Step 3: 验证字段（A表 + B表）
    field_results = validate_field_completeness(outline_data, case["expected_total_words"])
    ratio_results = validate_allocation_ratios(outline_data, case["expected_total_words"])

    # 打印验证结果
    _print_validation_results(field_results, ratio_results)

    # 判定通过/失败
    passed = (
        field_results["has_target_words"] and
        field_results["all_positive"] and
        field_results["sum_accuracy"] and
        ratio_results["max_section_ok"] and
        ratio_results["min_section_ok"]
    )

    logger.info(f"\n  {'✅ PASS' if passed else '❌ FAIL'}")

    return {
        "passed": passed,
        "field_results": field_results,
        "ratio_results": ratio_results,
        "outline": outline_data
    }


def run_playwright_e2e(case: dict, case_idx: int, headed: bool) -> dict:
    """
    通过 Playwright 浏览器进行 E2E 验证

    Returns:
        {
            "passed": bool,
            "field_results": dict,
            "ratio_results": dict,
            "outline": dict | None
        }
    """
    _fail = {"passed": False, "field_results": {}, "ratio_results": {}, "outline": None}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright 未安装，回退到 API E2E 模式")
        return run_api_e2e(case, case_idx)

    topic = case["topic"]
    logger.info(f"\n{'='*60}")
    logger.info(f"🌐 Playwright E2E 测试 {case_idx}: {topic}")
    logger.info(f"目标长度: {case['target_length']} ({case['expected_total_words']} 字)")
    logger.info(f"{'='*60}")

    outline_data = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed, slow_mo=200)
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = context.new_page()
        page.set_default_timeout(300000)

        try:
            # 注入 SSE Hook
            page.add_init_script(SSE_HOOK_JS)

            # 使用共享的前端交互流程
            result = run_playwright_generation(
                page=page,
                topic=topic,
                wait_for="outline",
                max_wait=300,
                screenshot_prefix=f"word_alloc_case{case_idx}"
            )

            if not result["success"]:
                logger.error(f"  ❌ {result['error']}")
                return _fail

            outline_data = result["outline"]
            task_id = result["task_id"]

            # 取消任务
            cancel_task(task_id)

        except Exception as e:
            logger.error(f"  ❌ Playwright 异常: {e}")
            return _fail
        finally:
            browser.close()

    if not outline_data:
        logger.error(f"  ❌ 未收到 outline_complete 事件")
        return _fail

    # 验证字段（A表 + B表）
    field_results = validate_field_completeness(outline_data, case["expected_total_words"])
    ratio_results = validate_allocation_ratios(outline_data, case["expected_total_words"])

    # 打印验证结果
    _print_validation_results(field_results, ratio_results)

    # 判定通过/失败
    passed = (
        field_results["has_target_words"] and
        field_results["all_positive"] and
        field_results["sum_accuracy"] and
        ratio_results["max_section_ok"] and
        ratio_results["min_section_ok"]
    )

    logger.info(f"\n  {'✅ PASS' if passed else '❌ FAIL'}")

    return {
        "passed": passed,
        "field_results": field_results,
        "ratio_results": ratio_results,
        "outline": outline_data
    }


def _print_validation_results(field_results: dict, ratio_results: dict):
    """打印验证结果（A表 + B表）"""
    logger.info(f"\n  --- A表：字段检查 ---")

    # A1: target_words 字段存在
    icon = "✅" if field_results["has_target_words"] else "❌"
    logger.info(f"    {icon} A1: 每个 section 有 target_words 字段")

    # A2: target_words 值为正整数
    icon = "✅" if field_results["all_positive"] else "❌"
    logger.info(f"    {icon} A2: 所有 target_words 为正整数")

    # A3: 总和准确性
    if field_results.get("sum_error_pct") is not None:
        icon = "✅" if field_results.get("sum_accuracy") else "❌"
        error_pct = field_results["sum_error_pct"]
        logger.info(f"    {icon} A3: 字数总和准确性（误差 {error_pct:.1%}）")
    else:
        logger.info(f"    ❌ A3: 字数总和准确性（无法计算）")

    # 详细信息
    for detail in field_results["details"]:
        logger.info(f"       {detail}")

    a_pass = sum([
        field_results["has_target_words"],
        field_results["all_positive"],
        field_results["sum_accuracy"] or False
    ])
    logger.info(f"    📊 A表: {a_pass}/3 通过")

    logger.info(f"\n  --- B表：合理性检查 ---")

    # B1: 最大章节 ≤ 40%
    icon = "✅" if ratio_results["max_section_ok"] else "❌"
    logger.info(f"    {icon} B1: 最大章节字数 ≤ 总字数 40%")

    # B2: 最小章节 ≥ 200 字
    icon = "✅" if ratio_results["min_section_ok"] else "❌"
    logger.info(f"    {icon} B2: 最小章节字数 ≥ 200 字")

    # B3: 比例匹配
    ratio_ok = (ratio_results["ratio_matches"] >= ratio_results["ratio_total"] * 0.6) if ratio_results["ratio_total"] > 0 else False
    icon = "✅" if ratio_ok else "⚠️"
    logger.info(f"    {icon} B3: 字数分配与 narrative_role 匹配 ({ratio_results['ratio_matches']}/{ratio_results['ratio_total']})")

    # 详细信息
    for detail in ratio_results["details"]:
        logger.info(f"       {detail}")

    b_pass = sum([
        ratio_results["max_section_ok"],
        ratio_results["min_section_ok"],
        ratio_ok
    ])
    logger.info(f"    📊 B表: {b_pass}/3 通过")


def main():
    parser = argparse.ArgumentParser(description="Step 1.2 字数分配规则 E2E 验证（对齐 70.1.2 验证方案）")
    parser.add_argument("--headed", action="store_true", help="Playwright 有头模式")
    parser.add_argument("--api-only", action="store_true", help="仅用 API 模式（不启动浏览器）")
    parser.add_argument("--cases", type=str, default="1,2,3", help="要运行的测试用例编号，逗号分隔")
    args = parser.parse_args()

    case_indices = [int(x) for x in args.cases.split(",")]
    case_results = []

    for i, idx in enumerate(case_indices):
        if idx < 1 or idx > len(TEST_CASES):
            logger.warning(f"跳过无效用例编号: {idx}")
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

        result["topic"] = case["topic"]
        result["case_idx"] = idx
        result["expected_total"] = case["expected_total_words"]
        case_results.append(result)

    # ============================================================
    # 汇总判定 — 对齐 70.1.2 验证方案通过标准
    # ============================================================
    total = len(case_results)
    field_pass = sum(1 for r in case_results if r["passed"])

    # 统计总和准确性
    sum_accurate = sum(
        1 for r in case_results
        if r.get("field_results", {}).get("sum_accuracy", False)
    )

    # 统计比例合理性
    ratio_reasonable = sum(
        1 for r in case_results
        if r.get("ratio_results", {}).get("ratio_matches", 0) >=
           r.get("ratio_results", {}).get("ratio_total", 1) * 0.6
    )

    print(f"\n{'='*60}")
    print(f"📊 Step 1.2 字数分配规则 E2E 验证汇总")
    print(f"{'='*60}")

    # 逐用例摘要
    for r in case_results:
        icon = "✅" if r["passed"] else "❌"
        total_words = r.get("field_results", {}).get("total_words", 0)
        expected = r.get("expected_total", 0)
        print(f"  {icon} 用例 {r['case_idx']}: {r['topic']}")
        print(f"      实际字数: {total_words}, 期望: {expected}")

    print(f"\n{'─'*60}")
    print(f"  通过标准（对齐 70.1.2 验证方案）：")

    # 标准 1：字段完整性 — 全部主题输出 target_words
    s1_ok = field_pass == total
    print(f"    {'✅' if s1_ok else '❌'} 字段完整性: {field_pass}/{total} 主题通过（要求全部）")

    # 标准 2：总和准确 — 全部主题字数总和误差 ≤10%
    s2_ok = sum_accurate == total
    print(f"    {'✅' if s2_ok else '❌'} 总和准确: {sum_accurate}/{total} 主题误差 ≤10%（要求全部）")

    # 标准 3：比例合理 — 至少 2/3 主题字数分配符合推荐比例
    s3_threshold = max(1, total * 2 // 3)
    s3_ok = ratio_reasonable >= s3_threshold
    print(f"    {'✅' if s3_ok else '❌'} 比例合理: {ratio_reasonable}/{total} 主题符合比例（要求 ≥{s3_threshold}）")

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
