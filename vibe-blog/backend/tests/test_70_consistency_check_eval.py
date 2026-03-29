#!/usr/bin/env python3
"""
[需求点 70.2] ThreadChecker + VoiceChecker 一致性检查 — LLM-as-Judge 特性验收

验证逻辑：
  1. 准备含已知叙事/语气问题的多章节文本
  2. 分别调用 ThreadCheckerAgent 和 VoiceCheckerAgent
  3. 用 LLM Judge 评估检查结果是否合理

ThreadChecker 检查项：
  T1 承诺兑现检出   — 引言承诺 vs 正文覆盖
  T2 事实一致性     — 跨章节数据矛盾
  T3 术语一致性     — 同一概念不同术语
  T4 无误报         — 正常文章不应有 high severity

VoiceChecker 检查项：
  V1 人称混乱检出   — 跨章节人称切换
  V2 正式度波动     — 口语化 vs 学术化混用
  V3 自称不一致     — 混用"本文"/"这篇博客"等
  V4 无误报         — 正常文章不应有 high severity

通过标准：8 项中至少 6 项 pass

用法：
  cd backend
  python tests/test_70_consistency_check_eval.py
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "eval_results" / "70"
PASS_THRESHOLD = 6  # 8 项中至少 6 项 pass

# ============================================================
# 测试样本
# ============================================================

THREAD_SAMPLE_SECTIONS = [
    {
        "id": "section_1",
        "title": "引言：5 种 RAG 优化方案",
        "content": "本文将介绍 5 种常见的 RAG 优化方案，帮助你全面提升检索增强生成的效果。RAG 技术通过结合检索和生成，在知识密集型任务中表现出色。根据测试，RAG 方案可以将准确率提升 40%。",
    },
    {
        "id": "section_2",
        "title": "向量检索优化",
        "content": "向量检索是 RAG 系统的核心。通过优化 embedding 模型和索引结构，可以显著提升检索质量。常用的向量数据库包括 Milvus、Pinecone 等。在我们的测试中，优化后的 RAG 系统准确率提升了 25%。",
    },
    {
        "id": "section_3",
        "title": "Chunk 策略",
        "content": "分块策略直接影响检索效果。常见的分块方法包括固定长度分块、语义分块和递归分块。选择合适的 chunk size 需要根据具体场景调优。",
    },
]

THREAD_SAMPLE_OUTLINE = {
    "narrative_mode": "tutorial",
    "narrative_flow": {
        "logic_chain": ["RAG 基础概念", "向量检索优化", "Chunk 策略", "重排序", "查询改写", "评估方法"]
    },
    "sections": [
        {"id": "section_1", "core_question": "RAG 的基本原理是什么？"},
        {"id": "section_2", "core_question": "如何优化向量检索？"},
        {"id": "section_3", "core_question": "Chunk 策略有哪些？"},
    ],
}

VOICE_SAMPLE_SECTIONS = [
    {
        "id": "section_1",
        "title": "什么是 Docker？",
        "content": "你好！今天我们来聊聊 Docker。Docker 超好用的，搞定容器化部署简直不要太爽！这篇博客会带你从零开始学习 Docker 的核心概念。其实 Docker 就是一个容器引擎，然后你可以用它来打包应用。",
    },
    {
        "id": "section_2",
        "title": "Docker 镜像与容器",
        "content": "综上所述，Docker 镜像是一个只读模板，包含了运行应用所需的所有依赖。开发者可以通过 Dockerfile 定义镜像的构建过程。本教程建议使用多阶段构建来优化镜像大小。容器是镜像的运行实例，具有独立的文件系统和网络命名空间。",
    },
    {
        "id": "section_3",
        "title": "Docker Compose 编排",
        "content": "本文接下来介绍 Docker Compose。我觉得 Compose 是管理多容器应用的最佳工具。你只需要写一个 docker-compose.yml 文件，然后运行 docker-compose up 就搞定了。其实非常简单，然后你就可以一键启动所有服务了。",
    },
]

# ============================================================
# Judge Prompt
# ============================================================

JUDGE_PROMPT = """你是一个严格的 Agent 输出质量评估专家。

你将看到一个一致性检查 Agent 的输入和输出，请评估 Agent 是否正确检出了问题。

## Agent 类型: {agent_type}

## 输入文档
{document}

## Agent 输出的 issues
{issues}

---

请逐项检查以下维度：

{check_items}

---

请严格按以下 JSON 格式输出（不要输出其他内容）。每个 reason 限 20 字以内：

```json
{{
  "checks": {{
{check_json_template}
  }},
  "pass_count": 0,
  "total": {total},
  "verdict": "PASS 或 FAIL",
  "summary": "一句话总结"
}}
```
"""

THREAD_CHECKS = {
    "T1_promise_fulfillment": "T1 承诺兑现检出",
    "T2_fact_consistency": "T2 事实一致性",
    "T3_terminology": "T3 术语一致性",
    "T4_no_false_positive": "T4 无误报",
}

THREAD_CHECK_ITEMS = """### T1 承诺兑现检出
引言说"5 种方案"，正文只有 2 种（向量检索、Chunk 策略）。Agent 是否检出了这个问题？
- pass: issues 中包含 promise_fulfillment 或类似描述
- fail: 未检出

### T2 事实一致性
第 1 章说"准确率提升 40%"，第 2 章说"准确率提升 25%"。Agent 是否检出了数据矛盾？
- pass: issues 中包含 fact_consistency 或类似描述
- fail: 未检出

### T3 术语一致性
文中是否存在术语不一致？如果没有明显术语问题，Agent 未报告也算 pass。
- pass: 合理（检出真实问题或无问题时不报告）
- fail: 误报了不存在的术语问题

### T4 无误报
Agent 输出的 issues 中是否有明显的误报（报告了不存在的问题）？
- pass: 无明显误报
- fail: 有明显误报"""

VOICE_CHECKS = {
    "V1_person_consistency": "V1 人称混乱检出",
    "V2_formality_consistency": "V2 正式度波动",
    "V3_self_reference": "V3 自称不一致",
    "V4_no_false_positive": "V4 无误报",
}

VOICE_CHECK_ITEMS = """### V1 人称混乱检出
第 1 章用"你/我们"，第 2 章用"开发者"，第 3 章用"我"。Agent 是否检出了人称混乱？
- pass: issues 中包含 person_consistency 或类似描述
- fail: 未检出

### V2 正式度波动
第 1 章口语化（"超好用"），第 2 章学术化（"综上所述"）。Agent 是否检出了正式度波动？
- pass: issues 中包含 formality_consistency 或类似描述
- fail: 未检出

### V3 自称不一致
混用了"这篇博客"、"本教程"、"本文"。Agent 是否检出了自称不一致？
- pass: issues 中包含 self_reference 或类似描述
- fail: 未检出

### V4 无误报
Agent 输出的 issues 中是否有明显的误报？
- pass: 无明显误报
- fail: 有明显误报"""

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


def run_thread_checker(sections, outline, llm_client):
    """运行 ThreadChecker"""
    from services.blog_generator.agents.thread_checker import ThreadCheckerAgent
    agent = ThreadCheckerAgent(llm_client)
    state = {
        'sections': sections,
        'outline': outline,
    }
    logger.info("[ThreadChecker] 开始检查...")
    start = time.time()
    result_state = agent.run(state)
    elapsed = time.time() - start
    issues = result_state.get('thread_issues', [])
    logger.info(f"[ThreadChecker] 完成 ({elapsed:.1f}s): {len(issues)} 个问题")
    return issues, elapsed


def run_voice_checker(sections, audience, llm_client):
    """运行 VoiceChecker"""
    from services.blog_generator.agents.voice_checker import VoiceCheckerAgent
    agent = VoiceCheckerAgent(llm_client)
    state = {
        'sections': sections,
        'audience_adaptation': audience,
    }
    logger.info("[VoiceChecker] 开始检查...")
    start = time.time()
    result_state = agent.run(state)
    elapsed = time.time() - start
    issues = result_state.get('voice_issues', [])
    logger.info(f"[VoiceChecker] 完成 ({elapsed:.1f}s): {len(issues)} 个问题")
    return issues, elapsed


def call_judge(agent_type, document, issues, check_names, check_items_text, llm_client):
    """调用 LLM Judge 评估"""
    check_keys = list(check_names.keys())
    total = len(check_keys)
    check_json_lines = []
    for k in check_keys:
        check_json_lines.append(f'    "{k}": {{"result": "pass", "reason": "..."}}')
    check_json_template = ",\n".join(check_json_lines)

    prompt = JUDGE_PROMPT.format(
        agent_type=agent_type,
        document=document,
        issues=json.dumps(issues, ensure_ascii=False, indent=2),
        check_items=check_items_text,
        check_json_template=check_json_template,
        total=total,
    )

    logger.info(f"  [Judge] 评估 {agent_type}...")
    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return _extract_json(response), check_keys, check_names


def print_report(agent_type, check_keys, check_names, eval_result, elapsed):
    """打印验收报告"""
    checks = eval_result.get("checks", {})
    pass_count = sum(1 for k in check_keys if checks.get(k, {}).get("result") == "pass")

    print(f"\n{'=' * 60}")
    print(f"  {agent_type} 验收报告 (耗时 {elapsed:.1f}s)")
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
    print("  70.2 一致性检查 Agent — LLM-as-Judge 特性验收")
    print("=" * 60)

    llm_client = get_llm_client()
    all_pass_count = 0
    all_total = 0

    # --- ThreadChecker ---
    thread_doc = build_document(THREAD_SAMPLE_SECTIONS)
    thread_issues, t_elapsed = run_thread_checker(
        THREAD_SAMPLE_SECTIONS, THREAD_SAMPLE_OUTLINE, llm_client
    )
    t_eval, t_keys, t_names = call_judge(
        "ThreadChecker", thread_doc, thread_issues,
        THREAD_CHECKS, THREAD_CHECK_ITEMS, llm_client
    )
    t_pass = print_report("ThreadChecker", t_keys, t_names, t_eval, t_elapsed)
    all_pass_count += t_pass
    all_total += len(t_keys)

    # --- VoiceChecker ---
    voice_doc = build_document(VOICE_SAMPLE_SECTIONS)
    voice_issues, v_elapsed = run_voice_checker(
        VOICE_SAMPLE_SECTIONS, "default", llm_client
    )
    v_eval, v_keys, v_names = call_judge(
        "VoiceChecker", voice_doc, voice_issues,
        VOICE_CHECKS, VOICE_CHECK_ITEMS, llm_client
    )
    v_pass = print_report("VoiceChecker", v_keys, v_names, v_eval, v_elapsed)
    all_pass_count += v_pass
    all_total += len(v_keys)

    # --- 总结 ---
    print(f"\n{'=' * 60}")
    verdict = "PASS" if all_pass_count >= PASS_THRESHOLD else "FAIL"
    print(f"  总体判定: {verdict} ({all_pass_count}/{all_total} 项通过, 阈值 {PASS_THRESHOLD})")
    print(f"{'=' * 60}")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    eval_data = {
        "feature": "70.2-consistency-check",
        "thread_checker": {"issues": thread_issues, "eval": t_eval, "elapsed": t_elapsed},
        "voice_checker": {"issues": voice_issues, "eval": v_eval, "elapsed": v_elapsed},
        "pass_count": all_pass_count,
        "total": all_total,
        "verdict": verdict,
        "timestamp": datetime.now().isoformat(),
    }
    result_file.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2))
    logger.info(f"  评估结果已保存: {result_file}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    main()
