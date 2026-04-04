"""
[需求点 70.1.1] Step 1.1 Planner 叙事流设计 — 单元验证脚本

对齐方案文档：vibe-blog-plan-方案/70.1.1. Phase1叙事流验证方案.md

⚠️ 同步警告：
  - 修改本测试文件时，必须同步更新方案文档 70.1.1 的验证方案部分
  - 修改方案文档 70.1.1 的检查清单/通过标准时，必须同步更新本文件的验证逻辑
  - 测试主题矩阵（TEST_CASES）与方案文档中的"测试主题矩阵"表格一一对应

用 3 个主题直接调用 PlannerAgent 生成大纲，检查：
A. 字段完整性（narrative_mode / narrative_flow / narrative_role）
B. 模式匹配（主题 → 期望模式）

用法：
  uv run tests/backend/test_70_1_1_planner_narrative.py
"""

import os
import json

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from services.llm_service import LLMService
from services.blog_generator.agents.planner import PlannerAgent

# ── 测试主题矩阵 ──────────────────────────────────────────────
TEST_CASES = [
    {
        "topic": "什么是 RAG",
        "article_type": "tutorial",
        "expected_modes": ["what-why-how", "tutorial"],
        "target_length": "medium",
    },
    {
        "topic": "手把手搭建 RAG 系统",
        "article_type": "tutorial",
        "expected_modes": ["tutorial"],
        "target_length": "medium",
    },
    {
        "topic": "10 个 RAG 性能优化技巧",
        "article_type": "tutorial",
        "expected_modes": ["catalog"],
        "target_length": "medium",
    },
]

VALID_MODES = ["what-why-how", "problem-solution", "before-after", "tutorial", "deep-dive", "catalog"]
VALID_ROLES = ["hook", "what", "why", "how", "compare", "deep_dive", "verify", "summary", "catalog_item"]


def validate_outline(outline: dict, expected_modes: list) -> list:
    """验证大纲字段完整性和模式匹配"""
    results = []

    # A1: narrative_mode
    mode = outline.get("narrative_mode", "")
    if not mode:
        results.append("❌ 缺少 narrative_mode")
    elif mode not in VALID_MODES:
        results.append(f"⚠️ narrative_mode 值不在预期范围: {mode}")
    else:
        results.append(f"✅ narrative_mode = {mode}")

    # A2: 模式匹配
    if mode in expected_modes:
        results.append(f"✅ 模式匹配预期 {expected_modes}")
    else:
        results.append(f"⚠️ 模式不匹配: 实际={mode}, 期望={expected_modes}")

    # A3: narrative_flow
    flow = outline.get("narrative_flow", {})
    if not flow:
        results.append("❌ 缺少 narrative_flow")
    else:
        if flow.get("reader_start"):
            results.append(f"✅ reader_start = {flow['reader_start'][:50]}...")
        else:
            results.append("❌ 缺少 narrative_flow.reader_start")

        if flow.get("reader_end"):
            results.append(f"✅ reader_end = {flow['reader_end'][:50]}...")
        else:
            results.append("❌ 缺少 narrative_flow.reader_end")

        chain = flow.get("logic_chain", [])
        if len(chain) >= 3:
            results.append(f"✅ logic_chain = {len(chain)} 个节点")
        else:
            results.append(f"❌ logic_chain 不足 3 个节点: {len(chain)}")

    # A4: sections narrative_role
    sections = outline.get("sections", [])
    roles_ok = 0
    roles_missing = 0
    roles_list = []
    for i, sec in enumerate(sections):
        role = sec.get("narrative_role", "")
        if role and role in VALID_ROLES:
            roles_ok += 1
            roles_list.append(role)
        elif role:
            roles_list.append(f"?{role}")
            roles_ok += 1  # 有值但不在标准列表，算部分通过
        else:
            roles_missing += 1
            roles_list.append("❌")

    if roles_missing == 0:
        results.append(f"✅ 所有 {len(sections)} 个 section 都有 narrative_role: {roles_list}")
    else:
        results.append(f"⚠️ {roles_missing}/{len(sections)} 个 section 缺少 narrative_role: {roles_list}")

    # A5: 首尾章节角色检查
    if roles_list:
        first = roles_list[0]
        last = roles_list[-1]
        if first in ["hook", "what", "overview", "❌"]:
            results.append(f"✅ 第一章角色合理: {first}")
        else:
            results.append(f"⚠️ 第一章角色不太常见: {first}")
        if last in ["summary", "verify", "how", "❌"]:
            results.append(f"✅ 最后一章角色合理: {last}")
        else:
            results.append(f"⚠️ 最后一章角色不太常见: {last}")

    return results


def run_test():
    """运行验证"""
    # 初始化 LLM
    llm = LLMService(
        provider_format=os.getenv("AI_PROVIDER_FORMAT", "openai"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_api_base=os.getenv("OPENAI_API_BASE", ""),
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        text_model=os.getenv("TEXT_MODEL", "gpt-4o"),
    )

    if not llm.is_available():
        print("❌ LLM 服务不可用，请检查 .env 配置")
        return

    planner = PlannerAgent(llm)
    all_passed = True

    for i, case in enumerate(TEST_CASES):
        print(f"\n{'='*60}")
        print(f"测试 {i+1}/{len(TEST_CASES)}: {case['topic']}")
        print(f"期望模式: {case['expected_modes']}")
        print(f"{'='*60}")

        try:
            outline = planner.generate_outline(
                topic=case["topic"],
                article_type=case["article_type"],
                target_audience="intermediate",
                target_length=case["target_length"],
            )

            # 打印大纲摘要
            print(f"\n标题: {outline.get('title', '无')}")
            print(f"章节数: {len(outline.get('sections', []))}")

            # 验证
            results = validate_outline(outline, case["expected_modes"])
            print(f"\n--- 验证结果 ---")
            for r in results:
                print(f"  {r}")
                if r.startswith("❌"):
                    all_passed = False

            # 保存完整大纲到文件
            output_file = os.path.join(
                os.path.dirname(__file__),
                f"outline_{i+1}_{case['topic'].replace(' ', '_')}.json"
            )
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(outline, f, ensure_ascii=False, indent=2)
            print(f"\n📄 完整大纲已保存: {output_file}")

        except Exception as e:
            print(f"❌ 生成失败: {e}")
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试未通过，请检查上方输出")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_test()
