#!/usr/bin/env python3
"""
[需求点 63] Humanizer Agent 去 AI 味 — LLM-as-Judge 特性验收

对齐方案文档：vibe-blog-plan-方案/63.02.需求文档.md

验证逻辑：
  1. 准备一段典型的 AI 味文本（含已知 AI 写作痕迹）
  2. 调用 HumanizerAgent 处理
  3. 把「原文 + 改写后文本」交给 LLM Judge 评估
  4. LLM 逐项检查改写是否消除了 AI 痕迹，同时保留了内容完整性

检查项（对齐 63.02 需求文档）：
  C1 AI 词汇消除   — 改写后是否消除了 AI 高频词汇（此外、至关重要、格局等）
  C2 填充短语消除   — 改写后是否消除了填充短语（值得注意的是、为了实现这一目标等）
  C3 结构去公式化   — 改写后是否打破了三段式、否定式排比等公式结构
  C4 内容完整性     — 改写后是否保留了核心事实、数据和技术细节
  C5 占位符保留     — 改写后是否保留了 {source_NNN}、[IMAGE: xxx] 等占位符
  C6 自然度提升     — 改写后读起来是否更像人类写的

通过标准：6 项中至少 5 项 pass

用法：
  cd backend
  python tests/test_63_humanizer_eval.py
  python tests/test_63_humanizer_eval.py --skip-generate  # 跳过生成，直接用样本测试
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# 配置
# ============================================================

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5001")
RESULTS_DIR = Path(__file__).parent / "eval_results" / "63"
PASS_THRESHOLD = 5  # 6 项中至少 5 项 pass

# ============================================================
# 测试样本：典型 AI 味文本（含已知 AI 写作痕迹）
# ============================================================

AI_FLAVORED_SAMPLES = [
    {
        "title": "LangGraph 框架深度解析",
        "content": """### LangGraph 框架深度解析

此外，LangGraph 作为一个至关重要的多 Agent 编排框架，在不断演变的 AI 格局中发挥着关键性的作用。它不仅仅是一个简单的工具，而是一种全新的范式，标志着 AI 应用开发的重要转折点。{source_001}

值得注意的是，LangGraph 的核心设计理念体现了对状态管理、流程控制和可观测性的深刻理解。这一框架为开发者提供了无缝、直观和强大的开发体验——确保用户能够高效地构建复杂的 AI 工作流。

[IMAGE: langgraph_architecture]

从简单的线性流程到复杂的多 Agent 协作，LangGraph 展示了其在不同场景下的充满活力的适应能力。行业专家认为，这一框架将对整个 AI 开发生态产生持久影响，彰显了 LangChain 团队在技术创新方面的关键作用。{source_002}

**关键特性：** LangGraph 拥有以下核心能力：
- **状态管理：** 提供了丰富的状态管理机制，确保数据在节点间的无缝流转
- **检查点：** 支持开创性的检查点功能，为长时间运行的工作流提供可靠保障
- **人机协作：** 实现了令人叹为观止的人机协作模式，增强了系统的灵活性

[CODE: langgraph_example]

尽管 LangGraph 面临着一些挑战，包括学习曲线和性能优化，但凭借其战略位置和正在进行的改进，LangGraph 继续蓬勃发展。未来展望令人期待，激动人心的时代即将到来。🚀""",
        "audience_adaptation": "technical-beginner",
    },
]

# ============================================================
# LLM-as-Judge Prompt
# ============================================================

JUDGE_PROMPT = """你是一个严格的 AI 写作痕迹检测专家。

你将看到一段文本的「原文」和经过 Humanizer Agent 处理后的「改写版」。
你需要检查改写是否有效消除了 AI 写作痕迹，同时保留了内容完整性。

## 原文
{original}

## 改写后
{humanized}

---

请逐项检查以下 6 个维度：

### C1 AI 词汇消除
检查：改写后是否消除了 AI 高频词汇？
常见 AI 词汇：此外、至关重要、格局、关键性的、充满活力的、不断演变的、深刻的、无缝、开创性的、令人叹为观止的
- pass: 上述词汇在改写后基本消除（残留 ≤ 1 个）
- fail: 仍有 2 个以上 AI 高频词汇

### C2 填充短语消除
检查：改写后是否消除了填充短语？
常见填充短语：值得注意的是、为了实现这一目标、在这个时间点、由于...的事实
- pass: 填充短语在改写后基本消除
- fail: 仍有明显的填充短语

### C3 结构去公式化
检查：改写后是否打破了 AI 公式化结构？
常见公式：三段式列举、否定式排比（不仅仅是...而是...）、通用积极结论（未来展望令人期待）
- pass: 公式化结构被打破或重写
- fail: 仍保留明显的公式化结构

### C4 内容完整性
检查：改写后是否保留了核心事实、数据和技术细节？
- pass: 核心技术信息（LangGraph 的功能、特性）完整保留，没有事实性错误
- fail: 丢失了重要的技术信息或引入了事实性错误

### C5 占位符保留
检查：改写后是否保留了所有占位符？
需要保留的占位符：{{source_001}}、{{source_002}}、[IMAGE: langgraph_architecture]、[CODE: langgraph_example]
- pass: 所有占位符完整保留
- fail: 有占位符丢失或被修改

### C6 自然度提升
检查：改写后读起来是否更像人类写的？
- pass: 句式更自然、节奏有变化、不像机器生成
- fail: 仍然读起来像 AI 生成的文本

---

请严格按以下 JSON 格式输出（不要输出其他内容）。每个 reason 限 20 字以内：

```json
{{
  "checks": {{
    "C1_ai_vocabulary": {{"result": "pass", "reason": "..."}},
    "C2_filler_phrases": {{"result": "pass", "reason": "..."}},
    "C3_structure": {{"result": "pass", "reason": "..."}},
    "C4_content_integrity": {{"result": "pass", "reason": "..."}},
    "C5_placeholders": {{"result": "pass", "reason": "..."}},
    "C6_naturalness": {{"result": "pass", "reason": "..."}}
  }},
  "pass_count": 0,
  "total": 6,
  "verdict": "PASS 或 FAIL",
  "summary": "一句话总结"
}}
```
"""

# ============================================================
# 检查项定义
# ============================================================

CHECK_NAMES = {
    "C1_ai_vocabulary": "C1 AI 词汇消除",
    "C2_filler_phrases": "C2 填充短语消除",
    "C3_structure": "C3 结构去公式化",
    "C4_content_integrity": "C4 内容完整性",
    "C5_placeholders": "C5 占位符保留",
    "C6_naturalness": "C6 自然度提升",
}
CHECK_KEYS = list(CHECK_NAMES.keys())


# ============================================================
# 工具函数
# ============================================================

def get_llm_client():
    """获取 LLM 客户端"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.llm_service import get_llm_service, init_llm_service

    llm = get_llm_service()
    if llm is None:
        # 未通过 Flask app 初始化，手动从 config 初始化
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


def run_humanizer(sample: dict, llm_client) -> dict:
    """调用 HumanizerAgent 处理样本"""
    from services.blog_generator.agents.humanizer import HumanizerAgent

    agent = HumanizerAgent(llm_client)
    state = {
        'sections': [{
            'id': 'test_section',
            'title': sample['title'],
            'content': sample['content'],
        }],
        'audience_adaptation': sample.get('audience_adaptation', 'technical-beginner'),
    }

    logger.info(f"  [Humanizer] 处理章节: {sample['title']}")
    start = time.time()
    result_state = agent.run(state)
    elapsed = time.time() - start

    section = result_state['sections'][0]
    humanized_content = section.get('content', '')
    skipped = section.get('humanizer_skipped', False)
    score_before = section.get('humanizer_score_before', section.get('humanizer_score', 0))
    score_after = section.get('humanizer_score_after', score_before)

    logger.info(
        f"  [Humanizer] 完成 ({elapsed:.1f}s): "
        f"评分 {score_before} → {score_after}, "
        f"{'跳过' if skipped else '已改写'}"
    )

    return {
        'original': sample['content'],
        'humanized': humanized_content,
        'skipped': skipped,
        'score_before': score_before,
        'score_after': score_after,
        'elapsed': elapsed,
    }


def call_judge(original: str, humanized: str, llm_client) -> dict:
    """调用 LLM Judge 评估改写效果"""
    prompt = JUDGE_PROMPT.format(
        original=original,
        humanized=humanized,
    )

    logger.info("  [Judge] LLM 评估中...")
    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    text = response.strip()
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        text = text[start:end].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        text = text[start:end].strip()

    return json.loads(text, strict=False)


def print_eval_report(sample: dict, humanizer_result: dict, eval_result: dict):
    """打印验收报告"""
    checks = eval_result.get("checks", {})
    pass_count = sum(1 for k in CHECK_KEYS if checks.get(k, {}).get("result") == "pass")
    verdict = "PASS" if pass_count >= PASS_THRESHOLD else "FAIL"

    # 覆盖 LLM 返回的 pass_count 和 verdict（以实际计算为准）
    eval_result["pass_count"] = pass_count
    eval_result["verdict"] = verdict

    print("\n" + "=" * 70)
    print(f"📊 Humanizer 验收报告: {sample['title']}")
    print(f"   方案: 63 — Humanizer Agent 去 AI 味")
    print(f"   评分: {humanizer_result['score_before']} → {humanizer_result['score_after']}/50")
    print(f"   耗时: {humanizer_result['elapsed']:.1f}s")
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


def run_eval(sample: dict, llm_client) -> dict | None:
    """运行完整的验收流程"""
    print(f"\n📝 测试样本: {sample['title']}")

    # 1. Humanizer 处理
    humanizer_result = run_humanizer(sample, llm_client)

    if humanizer_result['skipped']:
        print(f"  ⚠️ Humanizer 跳过了改写（评分 {humanizer_result['score_before']} >= 阈值）")
        print(f"  这说明样本 AI 味不够重，或阈值设置过低")
        return None

    # 检查内容是否实际发生了变化
    if humanizer_result['original'].strip() == humanizer_result['humanized'].strip():
        print(f"  ⚠️ Humanizer 未改变内容（可能 LLM 调用失败），跳过 Judge 评估")
        return None

    # 2. LLM Judge 评估
    eval_result = call_judge(
        humanizer_result['original'],
        humanizer_result['humanized'],
        llm_client,
    )

    # 3. 输出报告
    print_eval_report(sample, humanizer_result, eval_result)

    # 4. 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    eval_data = {
        "sample_title": sample['title'],
        "feature": "63-humanizer-agent",
        "humanizer_result": {
            "skipped": humanizer_result['skipped'],
            "score_before": humanizer_result['score_before'],
            "score_after": humanizer_result['score_after'],
            "elapsed": humanizer_result['elapsed'],
        },
        "eval_result": eval_result,
        "timestamp": datetime.now().isoformat(),
    }
    result_file.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2))
    logger.info(f"  💾 评估结果已保存: {result_file}")

    return eval_data


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="[63] Humanizer Agent — LLM-as-Judge 特性验收")
    parser.add_argument("--backend-url", type=str, default=None, help="后端 URL")
    args = parser.parse_args()

    if args.backend_url:
        global BACKEND_URL
        BACKEND_URL = args.backend_url

    print("=" * 70)
    print("🧪 特性验收（63 号方案 — Humanizer Agent 去 AI 味）")
    print("=" * 70)

    llm_client = get_llm_client()

    all_pass = True
    for sample in AI_FLAVORED_SAMPLES:
        eval_data = run_eval(sample, llm_client)
        if eval_data is None:
            all_pass = False
        elif eval_data["eval_result"].get("verdict") != "PASS":
            all_pass = False

    print("\n" + "=" * 70)
    if all_pass:
        print("🎉 所有样本验收通过！Humanizer Agent 有效消除了 AI 写作痕迹。")
    else:
        print("💥 部分样本验收未通过，请检查上方报告中的失败项。")
    print("=" * 70)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    main()
