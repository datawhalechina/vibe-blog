#!/usr/bin/env python3
"""
[需求点 66] Reviewer 拆分精简 — LLM-as-Judge 特性验收

验证精简后的 Reviewer 仍能正确检测：
  R1 大纲覆盖     — 遗漏章节应被检出
  R2 逻辑连贯     — 逻辑断裂应被检出
  R3 Verbatim 违规 — 数据被改写应被检出
  R4 学习目标缺失  — 未覆盖的学习目标应被检出
  R5 通过判定     — 完整文档应通过审核
  R6 精简有效     — Prompt 长度应显著减少

通过标准：6 项中至少 4 项 pass

用法：
  cd backend
  python tests/test_66_reviewer_eval.py
"""

import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "eval_results" / "66"
PASS_THRESHOLD = 4

# ============================================================
# 测试样本：有问题的文档（遗漏章节 + Verbatim 违规）
# ============================================================

SAMPLE_OUTLINE = {
    "title": "Redis 缓存实战指南",
    "sections": [
        {"id": "section_1", "title": "Redis 基础概念"},
        {"id": "section_2", "title": "缓存策略与模式"},
        {"id": "section_3", "title": "性能优化"},
        {"id": "section_4", "title": "高可用部署"},
    ]
}

# 文档故意遗漏 section_4（高可用部署）
SAMPLE_DOCUMENT = """## Redis 基础概念

Redis 是一个开源的内存数据库，支持多种数据结构。它的读写速度约为每秒 10 万次操作。

---

## 缓存策略与模式

常见的缓存策略包括 Cache-Aside、Write-Through 和 Write-Behind。
选择合适的策略取决于业务场景。

---

## 性能优化

Redis 的性能优化主要包括内存管理、持久化配置和网络优化。
通过合理配置 maxmemory-policy 可以控制内存使用。
"""

SAMPLE_VERBATIM_DATA = [
    {"type": "statistic", "value": "110,000 QPS", "source": "Redis 官方基准测试"},
    {"type": "quote", "value": "Redis is not just a cache", "source": "Antirez Blog"},
]

SAMPLE_LEARNING_OBJECTIVES = [
    {"type": "primary", "objective": "理解 Redis 核心数据结构和使用场景"},
    {"type": "primary", "objective": "掌握 Redis 高可用部署方案（Sentinel/Cluster）"},
    {"type": "secondary", "objective": "了解 Redis 性能优化技巧"},
]

# ============================================================
# Judge Prompt
# ============================================================

JUDGE_PROMPT = """你是一个严格的 Agent 输出质量评估专家。

你将看到一个质量审核 Agent 的输入和输出，请评估 Agent 是否正确完成了审核任务。

## 输入大纲
{outline}

## 输入文档
{document}

## Verbatim Data
{verbatim_data}

## 学习目标
{learning_objectives}

## Agent 输出
{agent_output}

---

请逐项检查以下维度：

### R1 大纲覆盖
大纲有 4 个章节，但文档遗漏了"高可用部署"。Agent 是否检出遗漏？
- pass: 检出遗漏章节
- fail: 未检出

### R2 逻辑连贯
文档的三个章节之间过渡较为生硬。Agent 是否提出逻辑/过渡问题？
- pass: 提出了逻辑或过渡相关问题
- fail: 未提出（可接受，因为过渡问题不严重）

### R3 Verbatim 违规
Verbatim Data 要求 "110,000 QPS"，但文档写成"约 10 万次操作"。Agent 是否检出？
- pass: 检出 Verbatim 违规
- fail: 未检出

### R4 学习目标缺失
学习目标要求"掌握 Redis 高可用部署方案"，但文档无此内容。Agent 是否检出？
- pass: 检出学习目标未覆盖
- fail: 未检出

### R5 通过判定
文档有明显遗漏和 Verbatim 违规，approved 应为 false。
- pass: approved = false
- fail: approved = true

### R6 精简有效
Agent 输出的 issue_type 应仅包含 completeness/logic/verbatim_violation/learning_objective_gap，
不应包含 hallucination/accuracy_mismatch/expression_quality 等已移除的类型。
- pass: issue_type 仅包含精简后的类型
- fail: 包含已移除的类型

---

请严格按以下 JSON 格式输出（不要输出其他内容）。每个 reason 限 20 字以内：

```json
{{
  "checks": {{
    "R1_outline_coverage": {{"result": "pass", "reason": "..."}},
    "R2_logic_coherence": {{"result": "pass", "reason": "..."}},
    "R3_verbatim_violation": {{"result": "pass", "reason": "..."}},
    "R4_learning_objective": {{"result": "pass", "reason": "..."}},
    "R5_approval_correct": {{"result": "pass", "reason": "..."}},
    "R6_simplified_types": {{"result": "pass", "reason": "..."}}
  }},
  "pass_count": 0,
  "total": 6,
  "verdict": "PASS 或 FAIL",
  "summary": "一句话总结"
}}
```
"""

CHECK_NAMES = {
    "R1_outline_coverage": "R1 大纲覆盖检出",
    "R2_logic_coherence": "R2 逻辑连贯检出",
    "R3_verbatim_violation": "R3 Verbatim 违规检出",
    "R4_learning_objective": "R4 学习目标缺失检出",
    "R5_approval_correct": "R5 通过判定正确",
    "R6_simplified_types": "R6 精简有效",
}


def get_llm_client():
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.llm_service import get_llm_service, init_llm_service
    llm = get_llm_service()
    if llm is None:
        from config import get_config
        cfg = get_config()
        llm = init_llm_service({
            'AI_PROVIDER_FORMAT': cfg.AI_PROVIDER_FORMAT,
            'OPENAI_API_KEY': cfg.OPENAI_API_KEY,
            'OPENAI_API_BASE': cfg.OPENAI_API_BASE,
            'GOOGLE_API_KEY': getattr(cfg, 'GOOGLE_API_KEY', ''),
            'TEXT_MODEL': cfg.TEXT_MODEL,
        })
    return llm


def _extract_json(text: str) -> dict:
    text = text.strip()
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
        else:
            text = text[start:].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
        else:
            text = text[start:].strip()
    return json.loads(text, strict=False)


def run_reviewer(document, outline, verbatim_data, learning_objectives, llm_client):
    from services.blog_generator.agents.reviewer import ReviewerAgent
    agent = ReviewerAgent(llm_client)
    logger.info("[Reviewer] 开始审核...")
    start = time.time()
    result = agent.review(
        document=document,
        outline=outline,
        verbatim_data=verbatim_data,
        learning_objectives=learning_objectives,
    )
    elapsed = time.time() - start
    logger.info(f"[Reviewer] 完成 ({elapsed:.1f}s): score={result.get('score')}")
    return result, elapsed


def call_judge(outline, document, verbatim_data, learning_objectives, agent_output, llm_client):
    prompt = JUDGE_PROMPT.format(
        outline=json.dumps(outline, ensure_ascii=False, indent=2),
        document=document,
        verbatim_data=json.dumps(verbatim_data, ensure_ascii=False, indent=2),
        learning_objectives=json.dumps(learning_objectives, ensure_ascii=False, indent=2),
        agent_output=json.dumps(agent_output, ensure_ascii=False, indent=2),
    )
    logger.info("  [Judge] 评估 Reviewer...")
    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return _extract_json(response)


def print_report(check_keys, check_names, eval_result, elapsed):
    checks = eval_result.get("checks", {})
    pass_count = sum(1 for k in check_keys if checks.get(k, {}).get("result") == "pass")

    print(f"\n{'=' * 60}")
    print(f"  Reviewer Agent 验收报告 (耗时 {elapsed:.1f}s)")
    print(f"{'=' * 60}")

    for key in check_keys:
        check = checks.get(key, {})
        result = check.get("result", "unknown")
        icon = "PASS" if result == "pass" else "FAIL"
        print(f"  [{icon}] {check_names[key]}: {check.get('reason', 'N/A')}")

    print(f"\n  判定: {pass_count}/{len(check_keys)} 项通过")
    print(f"{'=' * 60}")
    return pass_count


def main():
    print("=" * 60)
    print("  66. Reviewer 拆分精简 — LLM-as-Judge 特性验收")
    print("=" * 60)

    llm_client = get_llm_client()

    # --- 运行 Reviewer ---
    result, elapsed = run_reviewer(
        SAMPLE_DOCUMENT, SAMPLE_OUTLINE,
        SAMPLE_VERBATIM_DATA, SAMPLE_LEARNING_OBJECTIVES,
        llm_client
    )

    # --- 打印 Agent 原始输出 ---
    print(f"\n--- Reviewer Agent 原始输出 ---")
    print(f"  score: {result.get('score')}")
    print(f"  approved: {result.get('approved')}")
    print(f"  issues: {len(result.get('issues', []))} 条")
    for issue in result.get('issues', []):
        print(f"    [{issue.get('severity')}] {issue.get('issue_type')}: {issue.get('description', '')[:60]}")
    print(f"  summary: {result.get('summary', '')}")

    # --- Judge 评估 ---
    eval_result = call_judge(
        SAMPLE_OUTLINE, SAMPLE_DOCUMENT,
        SAMPLE_VERBATIM_DATA, SAMPLE_LEARNING_OBJECTIVES,
        result, llm_client
    )
    check_keys = list(CHECK_NAMES.keys())
    pass_count = print_report(check_keys, CHECK_NAMES, eval_result, elapsed)

    # --- 总结 ---
    print(f"\n{'=' * 60}")
    verdict = "PASS" if pass_count >= PASS_THRESHOLD else "FAIL"
    print(f"  总体判定: {verdict} ({pass_count}/{len(check_keys)} 项通过, 阈值 {PASS_THRESHOLD})")
    print(f"{'=' * 60}")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    eval_data = {
        "feature": "66-reviewer-simplify",
        "reviewer_output": result,
        "judge_eval": eval_result,
        "pass_count": pass_count,
        "total": len(check_keys),
        "verdict": verdict,
        "elapsed": elapsed,
        "timestamp": datetime.now().isoformat(),
    }
    result_file.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2))
    logger.info(f"  评估结果已保存: {result_file}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    main()
