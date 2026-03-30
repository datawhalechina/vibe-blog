#!/usr/bin/env python3
"""
[需求点 52] 搜索结果提炼与缺口分析 — LLM-as-Judge 特性验收

对齐方案文档：vibe-blog-plan-方案/52. searcher.搜索结果提炼与缺口分析方案.md

⚠️ 同步警告：
  - 修改本测试文件时，必须同步更新方案文档 52 的验证方案部分
  - 检查项与方案文档"六、效果预期"中声称的指标一一对应

验证逻辑：
  1. 用指定主题调 /api/blog/generate/sync 生成文章
  2. 把「输入请求 + 输出文章」交给 LLM 评估
  3. LLM 逐项检查文章是否体现了 52 号方案声称的 6 个特性
  4. 每项给出 pass/fail + 证据引用，总体判定是否达标

检查项（对齐 52 号方案效果预期）：
  C1 素材利用率   — 文章是否整合了多个来源的信息，而非纯 LLM 生成
  C2 文章深度     — 是否有独特角度、覆盖了缺口，而非停留在概念介绍
  C3 数据引用准确 — 是否有具体数据/数字，且标注了来源
  C4 大纲定制化   — 章节结构是否针对主题定制，而非通用模板
  C5 差异化视角   — 是否有别人没讲的方面、争议点讨论
  C6 缺口覆盖     — 是否覆盖了常见文章容易忽略的方面

通过标准：6 项中至少 4 项 pass

用法：
  cd backend
  python tests/test_52_ab_quality_eval.py
  python tests/test_52_ab_quality_eval.py --topic "LangGraph 完全指南"
"""

import os
import sys
import json
import time
import argparse
import logging
import requests
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5001")
RESULTS_DIR = Path(__file__).parent / "eval_results" / "52"

PASS_THRESHOLD = 4  # 6 项中至少 4 项 pass

# 测试主题（选需要搜索素材支撑的话题，方便验证素材利用率和数据引用）
DEFAULT_TOPICS = [
    {
        "topic": "LangGraph 与 CrewAI 深度对比：多 Agent 框架该怎么选",
        "article_type": "tutorial",
        "target_audience": "intermediate",
        "target_length": "medium",
    },
]

# ============================================================
# LLM-as-Judge 特性验收 Prompt
# ============================================================

JUDGE_PROMPT = """你是一个严格的技术博客质量验收员。

用户用以下请求生成了一篇博客文章。你需要检查这篇文章是否体现了「搜索结果深度提炼与缺口分析」功能的预期效果。

## 生成请求
- 主题: {topic}
- 文章类型: {article_type}
- 目标读者: {target_audience}
- 目标长度: {target_length}

## 生成的文章
{article}

---

请逐项检查以下 6 个特性是否在文章中得到体现：

### C1 素材利用率
检查：文章是否整合了**多个不同来源**的信息？
- pass: 文章中能看到来自不同来源的观点、数据或案例被整合在一起（至少 3 个不同来源的信息）
- fail: 文章像是纯 LLM 生成，看不到外部信息的痕迹，或只引用了 1-2 个来源

### C2 文章深度
检查：文章是否超越了"概念介绍"层面，有独到的分析？
- pass: 文章有深入分析（如：优劣对比、适用场景分析、踩坑经验、性能考量等），不只是"X 是什么"
- fail: 文章停留在概念介绍和功能罗列，像 API 文档或 Wikipedia 摘要

### C3 数据引用准确
检查：文章中是否有**具体的数据**（数字、统计、性能指标），且标注了来源？
- pass: 至少有 2 处具体数据引用，且有来源标注（链接、文献名或出处说明）
- fail: 没有具体数据，全是定性描述；或有数据但没有来源标注

### C4 大纲定制化
检查：文章的章节结构是否**针对主题定制**，而非套用通用模板？
- pass: 章节标题和结构明显是为这个主题设计的（如对比类主题有对比维度章节，教程类有分步骤章节）
- fail: 明显的通用模板结构（简介→特点→用法→总结），换个主题也能用

### C5 差异化视角
检查：文章是否提供了**独特的切入点**或覆盖了别人容易忽略的方面？
- pass: 有至少 1 个独特视角（如：争议点讨论、冷门但重要的方面、实战踩坑经验）
- fail: 完全是常见观点的复述，没有任何新东西

### C6 缺口覆盖
检查：文章是否覆盖了**常见文章容易忽略的方面**（如性能、局限性、迁移成本等）？
- pass: 文章主动覆盖了至少 1 个"别人不怎么讲"的方面，且有实质内容
- fail: 只覆盖了最常见的方面，没有任何补充

---

请严格按以下 JSON 格式输出（不要输出其他内容）：

```json
{{
  "checks": {{
    "C1_material_utilization": {{
      "result": "pass 或 fail",
      "evidence": "从文章中引用具体段落或数据作为证据",
      "reason": "判断理由"
    }},
    "C2_depth": {{
      "result": "pass 或 fail",
      "evidence": "从文章中引用具体段落作为证据",
      "reason": "判断理由"
    }},
    "C3_citation_accuracy": {{
      "result": "pass 或 fail",
      "evidence": "列出文章中的数据引用和来源标注",
      "reason": "判断理由"
    }},
    "C4_structure_customization": {{
      "result": "pass 或 fail",
      "evidence": "列出文章的章节标题",
      "reason": "判断理由"
    }},
    "C5_differentiation": {{
      "result": "pass 或 fail",
      "evidence": "指出文章中的独特视角",
      "reason": "判断理由"
    }},
    "C6_gap_coverage": {{
      "result": "pass 或 fail",
      "evidence": "指出文章覆盖了哪些容易忽略的方面",
      "reason": "判断理由"
    }}
  }},
  "pass_count": 0,
  "total": 6,
  "verdict": "PASS 或 FAIL",
  "summary": "一句话总结这篇文章在搜索结果提炼与缺口分析方面的表现"
}}
```
"""


# ============================================================
# 检查项定义
# ============================================================

CHECK_NAMES = {
    "C1_material_utilization": "C1 素材利用率",
    "C2_depth": "C2 文章深度",
    "C3_citation_accuracy": "C3 数据引用准确",
    "C4_structure_customization": "C4 大纲定制化",
    "C5_differentiation": "C5 差异化视角",
    "C6_gap_coverage": "C6 缺口覆盖",
}
CHECK_KEYS = list(CHECK_NAMES.keys())


# ============================================================
# 工具函数
# ============================================================

def generate_article(topic_config: dict) -> dict:
    """调用 vibe-blog 同步 API 生成文章，返回完整结果"""
    logger.info(f"  🚀 开始生成: {topic_config['topic']}")
    start = time.time()

    resp = requests.post(
        f"{BACKEND_URL}/api/blog/generate/sync",
        json=topic_config,
        timeout=600,
    )
    resp.raise_for_status()
    result = resp.json()

    elapsed = time.time() - start
    md = result.get('markdown', '')
    logger.info(f"  ✅ 生成完成 ({elapsed:.0f}s), 字数: {len(md)}")
    return result


def call_judge(topic_config: dict, article: str) -> dict:
    """调用 LLM 评估文章是否体现 52 号方案特性"""
    prompt = JUDGE_PROMPT.format(
        topic=topic_config["topic"],
        article_type=topic_config.get("article_type", "tutorial"),
        target_audience=topic_config.get("target_audience", "intermediate"),
        target_length=topic_config.get("target_length", "medium"),
        article=article[:15000],
    )

    logger.info("  🧑‍⚖️ LLM Judge 特性验收中...")

    resp = requests.post(
        f"{BACKEND_URL}/api/chat",
        json={
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        },
        timeout=120,
    )

    if resp.status_code == 200:
        result = resp.json()
        response_text = result.get("response", result.get("content", ""))
    else:
        logger.warning(f"  ⚠️ /api/chat 不可用 ({resp.status_code})，尝试直接调用 LLM...")
        from services.llm_service import get_llm_service
        llm = get_llm_service()
        response_text = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

    # 解析 JSON
    text = response_text.strip()
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        text = text[start:end].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        text = text[start:end].strip()

    return json.loads(text)


def print_eval_report(topic_config: dict, eval_result: dict):
    """打印特性验收报告"""
    checks = eval_result["checks"]
    pass_count = eval_result.get("pass_count", 0)
    verdict = eval_result.get("verdict", "UNKNOWN")

    print("\n" + "=" * 70)
    print(f"📊 特性验收报告: {topic_config['topic']}")
    print(f"   方案: 52 — 搜索结果提炼与缺口分析")
    print(f"   通过标准: {PASS_THRESHOLD}/{len(CHECK_KEYS)} 项 pass")
    print("=" * 70)

    for key in CHECK_KEYS:
        check = checks.get(key, {})
        result = check.get("result", "unknown")
        icon = "✅" if result == "pass" else "❌"
        print(f"\n  {icon} {CHECK_NAMES[key]}: {result.upper()}")
        print(f"     证据: {check.get('evidence', 'N/A')}")
        print(f"     理由: {check.get('reason', 'N/A')}")

    print(f"\n{'=' * 70}")
    verdict_icon = "🎉" if verdict == "PASS" else "💥"
    print(f"  {verdict_icon} 总体判定: {verdict} ({pass_count}/{len(CHECK_KEYS)} 项通过)")
    print(f"  📝 总结: {eval_result.get('summary', 'N/A')}")
    print("=" * 70)


def run_eval(topic_config: dict) -> dict | None:
    """运行完整的特性验收流程"""
    # 1. 生成文章
    print(f"\n📝 生成文章: {topic_config['topic']}")
    result = generate_article(topic_config)
    md = result.get("markdown", "")

    if not md:
        logger.error("  ❌ 文章内容为空，跳过评估")
        return None

    # 2. LLM 评估
    eval_result = call_judge(topic_config, md)

    # 3. 输出报告
    print_eval_report(topic_config, eval_result)

    # 4. 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    eval_data = {
        "topic_config": topic_config,
        "feature": "52-搜索结果提炼与缺口分析",
        "article_length": len(md),
        "eval_result": eval_result,
        "timestamp": datetime.now().isoformat(),
    }
    result_file.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2))
    logger.info(f"  💾 评估结果已保存: {result_file}")

    # 5. 返回是否通过
    verdict = eval_result.get("verdict", "FAIL")
    if verdict != "PASS":
        failed = [CHECK_NAMES[k] for k in CHECK_KEYS
                  if eval_result["checks"].get(k, {}).get("result") != "pass"]
        logger.warning(f"  ⚠️ 未通过的检查项: {failed}")

    return eval_data


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="[52] 搜索结果提炼与缺口分析 — 特性验收")
    parser.add_argument("--topic", type=str, default=None, help="自定义主题")
    parser.add_argument("--backend-url", type=str, default=None, help="后端 URL")
    args = parser.parse_args()

    if args.backend_url:
        global BACKEND_URL
        BACKEND_URL = args.backend_url

    if args.topic:
        topics = [{
            "topic": args.topic,
            "article_type": "tutorial",
            "target_audience": "intermediate",
            "target_length": "medium",
        }]
    else:
        topics = DEFAULT_TOPICS

    print("=" * 70)
    print("� 特性验收（52 号方案 — 搜索结果提炼与缺口分析）")
    print("=" * 70)

    all_pass = True
    for tc in topics:
        eval_data = run_eval(tc)
        if eval_data and eval_data["eval_result"].get("verdict") != "PASS":
            all_pass = False

    print("\n" + "=" * 70)
    if all_pass:
        print("🎉 所有主题验收通过！52 号方案特性已在文章中体现。")
    else:
        print("💥 部分主题验收未通过，请检查上方报告中的失败项。")
    print("=" * 70)


if __name__ == "__main__":
    main()
