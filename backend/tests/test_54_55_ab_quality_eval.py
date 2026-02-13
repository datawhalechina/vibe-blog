#!/usr/bin/env python3
"""
[需求点 54+55] 素材预分配 + 核心问题驱动 — LLM-as-Judge A/B 质量评估

对齐方案文档：
  - vibe-blog-plan-方案/54. 素材预分配到章节方案.md
  - vibe-blog-plan-方案/55. 每章核心问题驱动写作方案.md

⚠️ 同步警告：
  - 修改本测试文件时，必须同步更新方案文档 54/55 的验证方案部分
  - 评估维度与方案文档中声称的效果指标一一对应

验证内容：
  1. 用同一主题调 /api/blog/generate/sync 跑两次（旧版 baseline vs 新版）
  2. 把两份输出匿名化（A/B 随机分配），送给 LLM 做盲评
  3. LLM 按 5 个维度打分，输出结构化评估报告
  4. 断言新版在关键维度上得分 ≥ 旧版

用法：
  cd backend
  # 第一步：改代码前，保存 baseline
  python tests/test_54_55_ab_quality_eval.py --save-baseline

  # 第二步：改完代码后，对比评估
  python tests/test_54_55_ab_quality_eval.py --compare

  # 自定义主题
  python tests/test_54_55_ab_quality_eval.py --compare --topic "LangGraph 完全指南"
"""

import os
import sys
import json
import time
import random
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
BASELINE_DIR = Path(__file__).parent / "ab_baselines"

# 测试主题（选有明确承诺的标题，方便验证标题兑现 + 素材引用）
DEFAULT_TOPICS = [
    {
        "topic": "LangGraph 完全指南：从入门到精通",
        "article_type": "tutorial",
        "target_audience": "intermediate",
        "target_length": "medium",
    },
]

# ============================================================
# LLM-as-Judge 评估 Prompt
# ============================================================

JUDGE_PROMPT = """你是一个严格的技术博客质量评审员。

下面有两篇文章（文章 A 和文章 B），它们是用同一个主题生成的，但使用了不同的生成策略。
你不知道哪篇是新版、哪篇是旧版。请完全基于内容质量做出判断。

## 主题
{topic}

## 文章 A
{article_a}

## 文章 B
{article_b}

---

请按以下 5 个维度分别打分（1-10 分），并说明理由：

### 维度 1：内容连贯性（对应 55 号方案 — 核心问题驱动）
文章是围绕一条主线连贯论述的，还是要点堆砌、像文档一样逐个展开？
- 1-3 分：明显的要点堆砌，各段独立，像 API 文档
- 4-6 分：有一定连贯性，但部分段落之间缺乏过渡
- 7-10 分：围绕核心问题连贯论述，段落之间自然衔接

### 维度 2：章节递进感（对应 55 号方案 — 核心问题逻辑链）
相邻章节之间是否有逻辑递进（如：为什么 → 是什么 → 怎么做），还是平铺罗列？
- 1-3 分：章节之间没有逻辑关系，可以任意调换顺序
- 4-6 分：有基本的顺序，但递进感不强
- 7-10 分：章节之间有明确的逻辑递进，读者跟着走有"渐入佳境"的感觉

### 维度 3：素材引用质量（对应 54 号方案 — 素材预分配）
文章中引用的数据、案例、来源是否准确、有来源标注、且用在了合适的位置？
- 1-3 分：没有引用任何外部数据/案例，或数据明显编造
- 4-6 分：有一些引用但缺少来源标注，或引用位置不太合适
- 7-10 分：引用准确、有来源标注、放在了最能支撑论点的位置

### 维度 4：标题承诺兑现（对应 56 号方案 — 标题承诺审计）
标题中的每个关键词承诺是否在内容中被兑现？
（例如："完全指南"是否覆盖了所有方面？"从入门到精通"是否有递进？）
- 1-3 分：标题严重过度承诺，内容只覆盖了一小部分
- 4-6 分：大部分承诺兑现，但有明显遗漏
- 7-10 分：标题的每个承诺都在内容中有对应章节支撑

### 维度 5：整体可读性
作为一个目标读者，读完这篇文章的体验如何？
- 1-3 分：读不下去，枯燥或混乱
- 4-6 分：能读完，但没有惊喜
- 7-10 分：读起来流畅，有收获感

---

请严格按以下 JSON 格式输出（不要输出其他内容）：

```json
{{
  "article_a": {{
    "coherence": {{"score": 0, "reason": ""}},
    "progression": {{"score": 0, "reason": ""}},
    "citation_quality": {{"score": 0, "reason": ""}},
    "title_fulfillment": {{"score": 0, "reason": ""}},
    "readability": {{"score": 0, "reason": ""}},
    "total": 0
  }},
  "article_b": {{
    "coherence": {{"score": 0, "reason": ""}},
    "progression": {{"score": 0, "reason": ""}},
    "citation_quality": {{"score": 0, "reason": ""}},
    "title_fulfillment": {{"score": 0, "reason": ""}},
    "readability": {{"score": 0, "reason": ""}},
    "total": 0
  }},
  "winner": "A 或 B 或 平局",
  "summary": "一句话总结两篇文章的核心差异"
}}
```
"""


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


def save_baseline(topic_config: dict, result: dict):
    """保存 baseline 结果到文件"""
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    topic_hash = abs(hash(topic_config["topic"])) % (10**8)
    filepath = BASELINE_DIR / f"baseline_{topic_hash}.json"

    data = {
        "topic_config": topic_config,
        "result": result,
        "saved_at": datetime.now().isoformat(),
    }
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    logger.info(f"  💾 Baseline 已保存: {filepath}")
    return filepath


def load_baseline(topic_config: dict) -> dict | None:
    """加载 baseline 结果"""
    topic_hash = abs(hash(topic_config["topic"])) % (10**8)
    filepath = BASELINE_DIR / f"baseline_{topic_hash}.json"

    if not filepath.exists():
        logger.warning(f"  ⚠️ Baseline 不存在: {filepath}")
        return None

    data = json.loads(filepath.read_text())
    logger.info(f"  📂 Baseline 已加载 (保存于 {data['saved_at']})")
    return data["result"]


def call_judge(topic: str, article_a: str, article_b: str) -> dict:
    """调用 LLM 做盲评（通过 vibe-blog 后端的 LLM 服务）"""
    prompt = JUDGE_PROMPT.format(
        topic=topic,
        article_a=article_a[:15000],
        article_b=article_b[:15000],
    )

    logger.info("  🧑‍⚖️ LLM Judge 评估中...")

    # 通过 vibe-blog 后端的 chat API 调用 LLM
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
        # 降级：直接用 requests 调本地 LLM
        logger.warning(f"  ⚠️ /api/chat 不可用 ({resp.status_code})，尝试直接调用 LLM...")
        sys.path.insert(0, str(Path(__file__).parent.parent))
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


DIM_NAMES = {
    "coherence": "内容连贯性",
    "progression": "章节递进感",
    "citation_quality": "素材引用质量",
    "title_fulfillment": "标题承诺兑现",
    "readability": "整体可读性",
}
DIMS = list(DIM_NAMES.keys())


def print_eval_report(topic: str, eval_result: dict, label_map: dict):
    """打印评估报告"""
    print("\n" + "=" * 70)
    print(f"📊 评估报告: {topic}")
    print("=" * 70)

    for label in ["article_a", "article_b"]:
        display = label.replace("article_", "").upper()
        version = label_map[display]
        scores = eval_result[label]

        print(f"\n  文章 {display} ({version}):")
        for dim in DIMS:
            dim_data = scores[dim]
            print(f"    {DIM_NAMES[dim]}: {dim_data['score']}/10 — {dim_data['reason']}")
        print(f"    总分: {scores['total']}/50")

    print(f"\n  🏆 胜者: {eval_result['winner']}")
    print(f"  📝 总结: {eval_result['summary']}")
    print("=" * 70)


def run_comparison(topic_config: dict):
    """运行完整的 A/B 对比评估"""
    topic = topic_config["topic"]

    # 1. 加载 baseline
    baseline_result = load_baseline(topic_config)
    if not baseline_result:
        logger.error("  ❌ 没有 baseline，请先运行 --save-baseline")
        return None

    baseline_md = baseline_result.get("markdown", "")

    # 2. 生成新版
    print("\n📝 生成新版文章...")
    new_result = generate_article(topic_config)
    new_md = new_result.get("markdown", "")

    if not baseline_md or not new_md:
        logger.error("  ❌ 文章内容为空，跳过评估")
        return None

    # 3. 随机分配 A/B（盲评）
    if random.random() > 0.5:
        article_a, article_b = baseline_md, new_md
        label_map = {"A": "baseline（旧版）", "B": "new（新版）"}
        new_label = "article_b"
    else:
        article_a, article_b = new_md, baseline_md
        label_map = {"A": "new（新版）", "B": "baseline（旧版）"}
        new_label = "article_a"

    # 4. LLM 盲评
    eval_result = call_judge(topic, article_a, article_b)

    # 5. 输出报告
    print_eval_report(topic, eval_result, label_map)

    # 6. 保存评估结果
    eval_dir = BASELINE_DIR / "evals"
    eval_dir.mkdir(parents=True, exist_ok=True)
    eval_file = eval_dir / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    eval_data = {
        "topic": topic,
        "label_map": label_map,
        "eval_result": eval_result,
        "new_label": new_label,
        "timestamp": datetime.now().isoformat(),
    }
    eval_file.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2))
    logger.info(f"\n  💾 评估结果已保存: {eval_file}")

    # 7. 对比分析
    new_scores = eval_result[new_label]
    old_label = "article_a" if new_label == "article_b" else "article_b"
    old_scores = eval_result[old_label]

    print("\n📊 新旧版对比:")
    regressions = []
    improvements = []
    for dim in DIMS:
        new_s = new_scores[dim]["score"]
        old_s = old_scores[dim]["score"]
        diff = new_s - old_s
        arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
        print(f"  {DIM_NAMES[dim]}: {old_s} → {new_s} ({arrow}{abs(diff)})")
        if diff < -1:
            regressions.append(dim)
        if diff > 0:
            improvements.append(dim)

    total_diff = new_scores["total"] - old_scores["total"]
    print(f"\n  总分: {old_scores['total']} → {new_scores['total']} (差值: {total_diff:+d})")

    if regressions:
        print(f"\n  ⚠️ 以下维度出现退步（>1分）: {[DIM_NAMES[r] for r in regressions]}")
    if improvements:
        print(f"  ✅ 以下维度有改善: {[DIM_NAMES[i] for i in improvements]}")

    return eval_data


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="[54+55] A/B 质量评估测试")
    parser.add_argument("--save-baseline", action="store_true", help="保存当前版本为 baseline")
    parser.add_argument("--compare", action="store_true", help="生成新版并与 baseline 对比")
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

    if args.save_baseline:
        print("=" * 70)
        print("📦 保存 Baseline")
        print("=" * 70)
        for tc in topics:
            print(f"\n📝 主题: {tc['topic']}")
            result = generate_article(tc)
            save_baseline(tc, result)
        print("\n✅ Baseline 保存完成")

    elif args.compare:
        print("=" * 70)
        print("🔬 A/B 质量对比评估")
        print("=" * 70)
        for tc in topics:
            print(f"\n📝 主题: {tc['topic']}")
            run_comparison(tc)
        print("\n✅ 评估完成")

    else:
        parser.print_help()
        print("\n示例:")
        print("  # 第一步：改代码前，保存 baseline")
        print("  python tests/test_54_55_ab_quality_eval.py --save-baseline")
        print("")
        print("  # 第二步：改完代码后，对比评估")
        print("  python tests/test_54_55_ab_quality_eval.py --compare")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    main()
