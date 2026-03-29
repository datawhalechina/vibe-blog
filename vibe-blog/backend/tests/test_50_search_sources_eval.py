#!/usr/bin/env python3
"""
[需求点 50] 扩展搜索源 — LLM-as-Judge 特性验收

验证搜索源路由器能正确选择新增的搜索源。

检查项：
  S1 GitHub 路由    — 涉及代码实现的主题应路由到 github
  S2 HuggingFace 路由 — 涉及开源模型的主题应路由到 huggingface
  S3 Google AI 路由  — 涉及 Gemini/TensorFlow 的主题应路由到 google_ai
  S4 AWS 路由       — 涉及 AWS 服务的主题应路由到 aws
  S5 多源路由       — 复杂主题应选择多个相关源
  S6 规则备选       — 无 LLM 时规则路由也能正确匹配新源

通过标准：6 项中至少 4 项 pass

用法：
  cd backend
  python tests/test_50_search_sources_eval.py
"""

import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "eval_results" / "50"
PASS_THRESHOLD = 4

# ============================================================
# 测试用例
# ============================================================

TEST_CASES = [
    {
        "id": "S1",
        "name": "GitHub 路由",
        "topic": "如何用 Python 实现一个 Redis 连接池，附完整源码",
        "expected_sources": ["github"],
        "description": "涉及代码实现应路由到 github",
    },
    {
        "id": "S2",
        "name": "HuggingFace 路由",
        "topic": "LLaMA 3 开源模型微调实战：使用 Transformers 和 PEFT",
        "expected_sources": ["huggingface"],
        "description": "涉及开源模型应路由到 huggingface",
    },
    {
        "id": "S3",
        "name": "Google AI 路由",
        "topic": "Gemini Pro 多模态能力深度评测与 TensorFlow 集成",
        "expected_sources": ["google_ai"],
        "description": "涉及 Gemini/TensorFlow 应路由到 google_ai",
    },
    {
        "id": "S4",
        "name": "AWS 路由",
        "topic": "AWS Lambda 无服务器架构最佳实践与 SageMaker 模型部署",
        "expected_sources": ["aws"],
        "description": "涉及 AWS 服务应路由到 aws",
    },
    {
        "id": "S5",
        "name": "多源路由",
        "topic": "使用 LangChain + Claude API 构建 RAG 应用，部署到 AWS",
        "expected_sources": ["langchain", "anthropic"],
        "description": "复杂主题应选择多个相关源",
    },
]

# ============================================================
# Judge Prompt
# ============================================================

JUDGE_PROMPT = """你是一个严格的搜索路由评估专家。

你将看到一个搜索路由器对多个主题的路由结果，请评估路由是否合理。

## 路由结果
{routing_results}

---

请逐项检查以下维度：

### S1 GitHub 路由
主题"如何用 Python 实现一个 Redis 连接池，附完整源码"涉及代码实现。
路由结果中是否包含 github？
- pass: 包含 github
- fail: 不包含

### S2 HuggingFace 路由
主题"LLaMA 3 开源模型微调实战：使用 Transformers 和 PEFT"涉及开源模型。
路由结果中是否包含 huggingface？
- pass: 包含 huggingface
- fail: 不包含

### S3 Google AI 路由
主题"Gemini Pro 多模态能力深度评测与 TensorFlow 集成"涉及 Google AI。
路由结果中是否包含 google_ai？
- pass: 包含 google_ai
- fail: 不包含

### S4 AWS 路由
主题"AWS Lambda 无服务器架构最佳实践与 SageMaker 模型部署"涉及 AWS。
路由结果中是否包含 aws？
- pass: 包含 aws
- fail: 不包含

### S5 多源路由
主题"使用 LangChain + Claude API 构建 RAG 应用，部署到 AWS"涉及多个领域。
路由结果中是否包含 langchain 和 anthropic（至少其一）？
- pass: 包含 langchain 或 anthropic
- fail: 都不包含

### S6 规则备选
规则路由结果（无 LLM）是否也能正确匹配新增源？
检查规则路由结果中是否有新增源（github/huggingface/google_ai/aws/microsoft）出现。
- pass: 至少有 2 个新增源被规则路由正确匹配
- fail: 新增源匹配不足

---

请严格按以下 JSON 格式输出（不要输出其他内容）。每个 reason 限 20 字以内：

```json
{{
  "checks": {{
    "S1_github_routing": {{"result": "pass", "reason": "..."}},
    "S2_huggingface_routing": {{"result": "pass", "reason": "..."}},
    "S3_google_ai_routing": {{"result": "pass", "reason": "..."}},
    "S4_aws_routing": {{"result": "pass", "reason": "..."}},
    "S5_multi_source": {{"result": "pass", "reason": "..."}},
    "S6_rule_fallback": {{"result": "pass", "reason": "..."}}
  }},
  "pass_count": 0,
  "total": 6,
  "verdict": "PASS 或 FAIL",
  "summary": "一句话总结"
}}
```
"""

CHECK_NAMES = {
    "S1_github_routing": "S1 GitHub 路由",
    "S2_huggingface_routing": "S2 HuggingFace 路由",
    "S3_google_ai_routing": "S3 Google AI 路由",
    "S4_aws_routing": "S4 AWS 路由",
    "S5_multi_source": "S5 多源路由",
    "S6_rule_fallback": "S6 规则备选",
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


def run_routing_tests(llm_client):
    from services.blog_generator.services.smart_search_service import SmartSearchService

    service = SmartSearchService(llm_client)
    results = {}

    for tc in TEST_CASES:
        logger.info(f"[路由测试] {tc['id']}: {tc['topic'][:40]}...")
        start = time.time()

        # LLM 路由
        llm_result = service._route_search_sources(tc['topic'])
        elapsed = time.time() - start

        # 规则路由
        rule_result = service._rule_based_routing(tc['topic'])

        results[tc['id']] = {
            "topic": tc['topic'],
            "expected": tc['expected_sources'],
            "llm_sources": llm_result.get('sources', []),
            "rule_sources": rule_result.get('sources', []),
            "elapsed": elapsed,
        }
        logger.info(f"  LLM: {llm_result.get('sources', [])}")
        logger.info(f"  Rule: {rule_result.get('sources', [])}")

    return results


def call_judge(routing_results, llm_client):
    prompt = JUDGE_PROMPT.format(
        routing_results=json.dumps(routing_results, ensure_ascii=False, indent=2),
    )
    logger.info("  [Judge] 评估搜索路由...")
    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return _extract_json(response)


def print_report(check_keys, check_names, eval_result, total_elapsed):
    checks = eval_result.get("checks", {})
    pass_count = sum(1 for k in check_keys if checks.get(k, {}).get("result") == "pass")

    print(f"\n{'=' * 60}")
    print(f"  搜索源扩展 验收报告 (总耗时 {total_elapsed:.1f}s)")
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
    print("  50. 扩展搜索源 — LLM-as-Judge 特性验收")
    print("=" * 60)

    llm_client = get_llm_client()

    start = time.time()
    routing_results = run_routing_tests(llm_client)
    total_elapsed = time.time() - start

    # --- 打印路由结果 ---
    print(f"\n--- 路由结果 ---")
    for tc_id, result in routing_results.items():
        print(f"  {tc_id}: LLM={result['llm_sources']}, Rule={result['rule_sources']}")

    # --- Judge 评估 ---
    eval_result = call_judge(routing_results, llm_client)
    check_keys = list(CHECK_NAMES.keys())
    pass_count = print_report(check_keys, CHECK_NAMES, eval_result, total_elapsed)

    # --- 总结 ---
    print(f"\n{'=' * 60}")
    verdict = "PASS" if pass_count >= PASS_THRESHOLD else "FAIL"
    print(f"  总体判定: {verdict} ({pass_count}/{len(check_keys)} 项通过, 阈值 {PASS_THRESHOLD})")
    print(f"{'=' * 60}")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    eval_data = {
        "feature": "50-search-sources",
        "routing_results": routing_results,
        "judge_eval": eval_result,
        "pass_count": pass_count,
        "total": len(check_keys),
        "verdict": verdict,
        "elapsed": total_elapsed,
        "timestamp": datetime.now().isoformat(),
    }
    result_file.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2))
    logger.info(f"  评估结果已保存: {result_file}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    main()
