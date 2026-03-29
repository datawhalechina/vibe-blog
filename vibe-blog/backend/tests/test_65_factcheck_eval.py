#!/usr/bin/env python3
"""
[需求点 65] FactCheck Agent 事实核查 — LLM-as-Judge 特性验收

验证逻辑：
  1. 准备含已知事实错误的多章节文本 + 模拟搜索结果作为证据
  2. 调用 FactCheckAgent
  3. 用 LLM Judge 评估核查结果是否合理

检查项：
  F1 矛盾检出     — 明确错误的统计数据应被标记为 CONTRADICTED
  F2 支持检出     — 有证据支持的 Claim 应被标记为 SUPPORTED
  F3 未验证检出   — 无证据的 Claim 应被标记为 UNVERIFIED
  F4 修复指令     — CONTRADICTED Claim 应有 fix_instructions
  F5 评分合理     — overall_score 应反映问题严重程度
  F6 无误报       — 不应将正确事实标记为 CONTRADICTED

通过标准：6 项中至少 4 项 pass

用法：
  cd backend
  python tests/test_65_factcheck_eval.py
"""

import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "eval_results" / "65"
PASS_THRESHOLD = 4  # 6 项中至少 4 项 pass

# ============================================================
# 测试样本
# ============================================================

# 含已知事实错误的章节
SAMPLE_SECTIONS = [
    {
        "id": "section_1",
        "title": "Transformer 架构概述",
        "content": (
            "Transformer 架构由 OpenAI 在 2015 年提出，"  # 错误：应为 Google 2017
            "论文标题为《Attention Is All You Need》。"
            "该架构完全基于注意力机制，抛弃了传统的 RNN 和 CNN 结构。"
            "Transformer 在 WMT 2014 英德翻译任务上达到了 28.4 BLEU 分数。"  # 正确
        ),
    },
    {
        "id": "section_2",
        "title": "BERT 与 GPT 的对比",
        "content": (
            "BERT 由 Google 在 2018 年发布，使用双向 Transformer 编码器。"  # 正确
            "GPT-3 拥有 1750 亿参数，是当时最大的语言模型。"  # 正确
            "BERT-base 包含 24 层 Transformer，共 3.4 亿参数。"  # 错误：BERT-base 是 12 层 1.1 亿
            "根据最新研究，BERT 在 SuperGLUE 上的准确率达到了 97.3%。"  # 无法验证
        ),
    },
    {
        "id": "section_3",
        "title": "大模型训练成本",
        "content": (
            "GPT-4 的训练成本据估计超过 1 亿美元。"  # 大致正确
            "训练大模型需要大量 GPU 资源，通常使用 NVIDIA A100 或 H100。"
            "LLaMA 2 由 Meta 在 2023 年开源发布。"  # 正确
        ),
    },
]

# 模拟搜索结果作为证据
SAMPLE_SEARCH_RESULTS = [
    {
        "title": "Attention Is All You Need - Original Paper",
        "url": "https://arxiv.org/abs/1706.03762",
        "content": (
            "Vaswani et al. (2017) from Google Brain proposed the Transformer architecture. "
            "The model achieved 28.4 BLEU on WMT 2014 English-to-German translation. "
            "The architecture relies entirely on self-attention mechanisms."
        ),
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "url": "https://arxiv.org/abs/1810.04805",
        "content": (
            "BERT was released by Google AI Language in 2018. "
            "BERT-base has 12 layers, 768 hidden size, 12 attention heads, 110M parameters. "
            "BERT-large has 24 layers, 1024 hidden size, 16 attention heads, 340M parameters."
        ),
    },
    {
        "title": "GPT-3: Language Models are Few-Shot Learners",
        "url": "https://arxiv.org/abs/2005.14165",
        "content": (
            "GPT-3 has 175 billion parameters. "
            "It was developed by OpenAI and released in 2020."
        ),
    },
    {
        "title": "LLaMA 2: Open Foundation and Fine-Tuned Chat Models",
        "url": "https://arxiv.org/abs/2307.09288",
        "content": (
            "LLaMA 2 was released by Meta in July 2023 as an open-source model. "
            "Available in 7B, 13B, and 70B parameter sizes."
        ),
    },
]

# ============================================================
# Judge Prompt
# ============================================================

JUDGE_PROMPT = """你是一个严格的 Agent 输出质量评估专家。

你将看到一个事实核查 Agent 的输入和输出，请评估 Agent 是否正确完成了核查任务。

## 输入文档
{document}

## 证据源
{evidence}

## Agent 输出的核查报告
{report}

---

请逐项检查以下维度：

### F1 矛盾检出
文中有两处明确错误：
1. "Transformer 由 OpenAI 在 2015 年提出" — 实际是 Google 2017 年
2. "BERT-base 包含 24 层 Transformer，共 3.4 亿参数" — 实际是 12 层 1.1 亿
Agent 是否将这两处标记为 CONTRADICTED？
- pass: 至少检出 1 处 CONTRADICTED
- fail: 未检出任何 CONTRADICTED

### F2 支持检出
文中有正确事实（如 GPT-3 1750 亿参数、LLaMA 2 Meta 2023 开源、28.4 BLEU）。
Agent 是否将有证据支持的 Claim 标记为 SUPPORTED？
- pass: 至少有 1 条 SUPPORTED
- fail: 无 SUPPORTED

### F3 未验证检出
"BERT 在 SuperGLUE 上准确率 97.3%" 在证据中无法验证。
Agent 是否将无证据的 Claim 标记为 UNVERIFIED？
- pass: 至少有 1 条 UNVERIFIED
- fail: 无 UNVERIFIED

### F4 修复指令
CONTRADICTED 的 Claim 应有对应的 fix_instructions。
- pass: fix_instructions 非空且包含合理修复
- fail: fix_instructions 为空或不合理

### F5 评分合理
文中有明确错误，overall_score 不应为 5（满分）。
- pass: overall_score <= 3
- fail: overall_score > 3

### F6 无误报
Agent 不应将正确事实标记为 CONTRADICTED（如 GPT-3 1750 亿参数）。
- pass: 无明显误报
- fail: 有明显误报

---

请严格按以下 JSON 格式输出（不要输出其他内容）。每个 reason 限 20 字以内：

```json
{{
  "checks": {{
    "F1_contradiction_detected": {{"result": "pass", "reason": "..."}},
    "F2_supported_detected": {{"result": "pass", "reason": "..."}},
    "F3_unverified_detected": {{"result": "pass", "reason": "..."}},
    "F4_fix_instructions": {{"result": "pass", "reason": "..."}},
    "F5_score_reasonable": {{"result": "pass", "reason": "..."}},
    "F6_no_false_positive": {{"result": "pass", "reason": "..."}}
  }},
  "pass_count": 0,
  "total": 6,
  "verdict": "PASS 或 FAIL",
  "summary": "一句话总结"
}}
```
"""

CHECK_NAMES = {
    "F1_contradiction_detected": "F1 矛盾检出",
    "F2_supported_detected": "F2 支持检出",
    "F3_unverified_detected": "F3 未验证检出",
    "F4_fix_instructions": "F4 修复指令",
    "F5_score_reasonable": "F5 评分合理",
    "F6_no_false_positive": "F6 无误报",
}

# ============================================================
# 工具函数
# ============================================================

def get_llm_client():
    """获取 LLM 客户端"""
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
    """从 LLM 响应中提取 JSON"""
    text = text.strip()
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        text = text[start:end].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        text = text[start:end].strip()
    return json.loads(text, strict=False)


def build_document(sections):
    """将 sections 拼接为文档"""
    parts = []
    for s in sections:
        parts.append(f"[{s['id']}] ## {s['title']}\n\n{s['content']}")
    return "\n\n---\n\n".join(parts)


def build_evidence(search_results):
    """将搜索结果拼接为证据"""
    parts = []
    for i, sr in enumerate(search_results):
        parts.append(f"--- source_{i+1:03d} ---\n标题: {sr['title']}\n来源: {sr['url']}\n内容: {sr['content']}")
    return "\n\n".join(parts)


def run_factcheck(sections, search_results, llm_client):
    """运行 FactCheckAgent"""
    from services.blog_generator.agents.factcheck import FactCheckAgent
    agent = FactCheckAgent(llm_client)
    state = {
        'sections': sections,
        'search_results': search_results,
    }
    logger.info("[FactCheck] 开始核查...")
    start = time.time()
    result_state = agent.run(state)
    elapsed = time.time() - start
    report = result_state.get('factcheck_report', {})
    logger.info(f"[FactCheck] 完成 ({elapsed:.1f}s): score={report.get('overall_score', 'N/A')}")
    return report, elapsed


def call_judge(document, evidence, report, llm_client):
    """调用 LLM Judge 评估"""
    prompt = JUDGE_PROMPT.format(
        document=document,
        evidence=evidence,
        report=json.dumps(report, ensure_ascii=False, indent=2),
    )
    logger.info("  [Judge] 评估 FactCheck...")
    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return _extract_json(response)


def print_report(check_keys, check_names, eval_result, elapsed):
    """打印验收报告"""
    checks = eval_result.get("checks", {})
    pass_count = sum(1 for k in check_keys if checks.get(k, {}).get("result") == "pass")

    print(f"\n{'=' * 60}")
    print(f"  FactCheck Agent 验收报告 (耗时 {elapsed:.1f}s)")
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
    print("  65. FactCheck Agent — LLM-as-Judge 特性验收")
    print("=" * 60)

    llm_client = get_llm_client()

    # --- 运行 FactCheck ---
    doc_text = build_document(SAMPLE_SECTIONS)
    evidence_text = build_evidence(SAMPLE_SEARCH_RESULTS)
    report, elapsed = run_factcheck(SAMPLE_SECTIONS, SAMPLE_SEARCH_RESULTS, llm_client)

    # --- 打印 Agent 原始输出 ---
    print(f"\n--- FactCheck Agent 原始输出 ---")
    print(f"  overall_score: {report.get('overall_score', 'N/A')}")
    print(f"  total_claims: {report.get('total_claims', 'N/A')}")
    print(f"  supported: {report.get('supported', 'N/A')}")
    print(f"  contradicted: {report.get('contradicted', 'N/A')}")
    print(f"  unverified: {report.get('unverified', 'N/A')}")
    for claim in report.get('claims', []):
        print(f"  [{claim.get('verdict', '?')}] {claim.get('claim', '')[:60]}...")
    print(f"  fix_instructions: {len(report.get('fix_instructions', []))} 条")

    # --- Judge 评估 ---
    eval_result = call_judge(doc_text, evidence_text, report, llm_client)
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
        "feature": "65-factcheck",
        "factcheck_report": report,
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

