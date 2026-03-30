#!/usr/bin/env python3
"""
[需求点 57] 博客骨架设计完整方案 — 三层验证

对齐方案文档：vibe-blog-plan-方案/57. vibe-blog博客骨架设计完整方案.md

借鉴 OpenDraft 测试体系的三层验证模式：
  Layer 1: Prompt 静态检查（借鉴 test_ticket016_title_promise.py 等）
           → 检查 planner.j2 / writer.j2 / reviewer.j2 是否包含六层设计指导
  Layer 2: 输出结构审计（借鉴 audit_output.py 的 OutputAuditor）
           → 生成文章后用正则规则检查大纲和文章的结构化字段
  Layer 3: LLM 特性验收（借鉴 test_52 的 LLM-as-Judge 模式）
           → 用 LLM 评估文章是否体现六层骨架设计的效果

用法：
  cd backend
  # 只跑 Layer 1（不调 LLM，秒级完成）
  python tests/test_57_skeleton_design.py --layer 1

  # 跑 Layer 1 + Layer 2（调 API 生成文章，用正则审计）
  python tests/test_57_skeleton_design.py --layer 2

  # 跑全部三层（调 API 生成 + LLM 评估）
  python tests/test_57_skeleton_design.py --layer 3

  # 自定义主题
  python tests/test_57_skeleton_design.py --layer 3 --topic "LangGraph 完全指南"
"""

import os
import sys
import re
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
PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = PROJECT_ROOT / "infrastructure" / "prompts" / "blog"
RESULTS_DIR = Path(__file__).parent / "eval_results" / "57"

DEFAULT_TOPICS = [
    {
        "topic": "Claude Code Skill 完全指南：从入门到精通",
        "article_type": "tutorial",
        "target_audience": "intermediate",
        "target_length": "medium",
    },
]


# ============================================================
# Layer 1: Prompt 静态检查
# （借鉴 OpenDraft test_ticket016_title_promise.py 模式）
# ============================================================

def load_prompt(filename: str) -> str:
    """加载 Prompt 模板文件"""
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {path}")
    return path.read_text(encoding='utf-8')


def check_planner_prompt() -> list:
    """检查 planner.j2 是否包含六层设计指导"""
    results = []
    try:
        prompt = load_prompt("planner.j2")
    except FileNotFoundError as e:
        return [("FAIL", f"planner.j2 不存在: {e}")]

    # ① 叙事流设计（53 号方案）
    checks_layer1 = [
        ("narrative_mode" in prompt or "叙事模式" in prompt,
         "L1.1 planner.j2 包含叙事模式选择指导"),
        ("narrative_flow" in prompt or "叙事流" in prompt,
         "L1.2 planner.j2 包含叙事流设计"),
        ("reader_start" in prompt or "读者起点" in prompt,
         "L1.3 planner.j2 包含读者起点/终点设计"),
        ("logic_chain" in prompt or "逻辑链" in prompt or "逻辑节点" in prompt,
         "L1.4 planner.j2 包含逻辑链设计"),
    ]

    # ② 章节字数分配（51 号方案）
    checks_layer2 = [
        ("target_words" in prompt or "目标字数" in prompt,
         "L1.5 planner.j2 包含每章字数目标"),
        ("narrative_role" in prompt or "叙事角色" in prompt,
         "L1.6 planner.j2 包含叙事角色分配"),
    ]

    # ③ 标题承诺审计（56 号方案）
    checks_layer3 = [
        ("title_audit" in prompt or "标题承诺" in prompt or "标题审计" in prompt,
         "L1.7 planner.j2 包含标题承诺审计"),
        (any(kw in prompt for kw in ["完全指南", "从零开始", "深入理解", "实战", "对比", "最佳实践",
                                      "Complete Guide", "From Scratch", "Deep Dive"]),
         "L1.8 planner.j2 包含承诺关键词审计表"),
    ]

    # ④ 素材预分配（54 号方案）
    checks_layer4 = [
        ("assigned_materials" in prompt or "素材预分配" in prompt or "素材分配" in prompt,
         "L1.9 planner.j2 包含素材预分配指导"),
        (any(kw in prompt for kw in ["must_use", "recommended", "optional", "use_as"]),
         "L1.10 planner.j2 包含素材优先级/用途分类"),
    ]

    # ⑤ 每章核心问题（55 号方案）
    checks_layer5 = [
        ("core_question" in prompt or "核心问题" in prompt,
         "L1.11 planner.j2 包含每章核心问题指导"),
    ]

    # ⑥ 视觉规划
    checks_layer6 = [
        ("image_type" in prompt or "illustration_type" in prompt or "视觉规划" in prompt,
         "L1.12 planner.j2 包含视觉规划"),
        ("cognitive_load" in prompt or "认知负荷" in prompt,
         "L1.13 planner.j2 包含认知负荷控制"),
    ]

    all_checks = checks_layer1 + checks_layer2 + checks_layer3 + checks_layer4 + checks_layer5 + checks_layer6
    for condition, description in all_checks:
        results.append(("PASS" if condition else "FAIL", description))

    return results


def check_writer_prompt() -> list:
    """检查 writer.j2 是否接收新字段"""
    results = []
    try:
        prompt = load_prompt("writer.j2")
    except FileNotFoundError as e:
        return [("FAIL", f"writer.j2 不存在: {e}")]

    checks = [
        ("core_question" in prompt or "核心问题" in prompt,
         "L1.14 writer.j2 展示 core_question"),
        ("target_words" in prompt or "目标字数" in prompt,
         "L1.15 writer.j2 展示 target_words"),
        ("assigned_materials" in prompt or "素材" in prompt,
         "L1.16 writer.j2 展示 assigned_materials"),
        ("narrative_role" in prompt or "叙事角色" in prompt,
         "L1.17 writer.j2 展示 narrative_role"),
    ]

    for condition, description in checks:
        results.append(("PASS" if condition else "FAIL", description))

    return results


def check_reviewer_prompt() -> list:
    """检查 reviewer.j2 是否包含标题承诺审计"""
    results = []
    try:
        prompt = load_prompt("reviewer.j2")
    except FileNotFoundError as e:
        return [("FAIL", f"reviewer.j2 不存在: {e}")]

    checks = [
        ("title_audit" in prompt or "标题承诺" in prompt or "标题审计" in prompt or "承诺" in prompt,
         "L1.18 reviewer.j2 包含标题承诺审计模块"),
    ]

    for condition, description in checks:
        results.append(("PASS" if condition else "FAIL", description))

    return results


def run_layer1() -> dict:
    """Layer 1: Prompt 静态检查"""
    print("\n" + "=" * 70)
    print("🔍 Layer 1: Prompt 静态检查（借鉴 OpenDraft ticket 测试模式）")
    print("   不调 LLM，检查 Prompt 模板是否包含六层设计指导")
    print("=" * 70)

    all_results = []

    print("\n📄 检查 planner.j2...")
    planner_results = check_planner_prompt()
    all_results.extend(planner_results)
    for status, desc in planner_results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {desc}")

    print("\n📄 检查 writer.j2...")
    writer_results = check_writer_prompt()
    all_results.extend(writer_results)
    for status, desc in writer_results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {desc}")

    print("\n📄 检查 reviewer.j2...")
    reviewer_results = check_reviewer_prompt()
    all_results.extend(reviewer_results)
    for status, desc in reviewer_results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {desc}")

    passed = sum(1 for s, _ in all_results if s == "PASS")
    total = len(all_results)

    print(f"\n{'=' * 70}")
    print(f"  Layer 1 结果: {passed}/{total} 通过")
    if passed == total:
        print("  ✅ Layer 1 PASSED — 所有 Prompt 模板包含六层设计指导")
    else:
        failed = [(s, d) for s, d in all_results if s == "FAIL"]
        print(f"  ❌ Layer 1 FAILED — {len(failed)} 项未通过:")
        for _, desc in failed:
            print(f"     - {desc}")
    print("=" * 70)

    return {"layer": 1, "passed": passed, "total": total, "results": all_results}


# ============================================================
# Layer 2: 输出结构审计
# （借鉴 OpenDraft audit_output.py 的 OutputAuditor 模式）
# ============================================================

class OutlineAuditor:
    """审计大纲输出的结构化字段（正则规则驱动，不依赖 LLM）"""

    def __init__(self, outline: dict):
        self.outline = outline
        self.results = []

    def audit_all(self) -> list:
        self.audit_narrative_flow()
        self.audit_sections_structure()
        self.audit_title_audit()
        self.audit_word_count_plan()
        return self.results

    def audit_narrative_flow(self):
        """检查叙事流字段"""
        nf = self.outline.get("narrative_flow", {})
        mode = self.outline.get("narrative_mode", "")

        self.results.append(
            ("PASS" if mode else "FAIL",
             f"L2.1 大纲包含 narrative_mode（值: {mode or '缺失'}）"))

        self.results.append(
            ("PASS" if nf.get("reader_start") else "FAIL",
             "L2.2 大纲包含 narrative_flow.reader_start"))

        self.results.append(
            ("PASS" if nf.get("reader_end") else "FAIL",
             "L2.3 大纲包含 narrative_flow.reader_end"))

        chain = nf.get("logic_chain", [])
        self.results.append(
            ("PASS" if len(chain) >= 3 else "FAIL",
             f"L2.4 logic_chain ≥ 3 个节点（实际: {len(chain)}）"))

    def audit_sections_structure(self):
        """检查每个 section 的新字段"""
        sections = self.outline.get("sections", [])
        if not sections:
            self.results.append(("FAIL", "L2.5 大纲缺少 sections"))
            return

        has_role = sum(1 for s in sections if s.get("narrative_role"))
        has_cq = sum(1 for s in sections if s.get("core_question"))
        has_tw = sum(1 for s in sections if s.get("target_words"))
        has_am = sum(1 for s in sections if s.get("assigned_materials"))
        total = len(sections)

        self.results.append(
            ("PASS" if has_role == total else "FAIL",
             f"L2.5 所有 section 有 narrative_role（{has_role}/{total}）"))

        self.results.append(
            ("PASS" if has_cq == total else "FAIL",
             f"L2.6 所有 section 有 core_question（{has_cq}/{total}）"))

        self.results.append(
            ("PASS" if has_tw == total else "FAIL",
             f"L2.7 所有 section 有 target_words（{has_tw}/{total}）"))

        self.results.append(
            ("PASS" if has_am >= 1 else "FAIL",
             f"L2.8 至少 1 个 section 有 assigned_materials（{has_am}/{total}）"))

        # 检查 narrative_role 是否合法
        valid_roles = {"hook", "what", "why", "how", "compare", "deep_dive",
                       "verify", "summary", "catalog_item"}
        roles = [s.get("narrative_role", "") for s in sections]
        invalid = [r for r in roles if r and r not in valid_roles]
        self.results.append(
            ("PASS" if not invalid else "FAIL",
             f"L2.9 narrative_role 值合法（非法值: {invalid or '无'}）"))

        # 检查 core_question 是否为疑问句
        cqs = [s.get("core_question", "") for s in sections if s.get("core_question")]
        has_question_mark = sum(1 for q in cqs if "？" in q or "?" in q)
        self.results.append(
            ("PASS" if has_question_mark >= len(cqs) * 0.5 else "FAIL",
             f"L2.10 core_question 多数为疑问句（{has_question_mark}/{len(cqs)}）"))

    def audit_title_audit(self):
        """检查标题承诺审计字段"""
        ta = self.outline.get("title_audit", {})
        self.results.append(
            ("PASS" if ta else "FAIL",
             "L2.11 大纲包含 title_audit 字段"))

        if ta:
            promises = ta.get("promises", [])
            self.results.append(
                ("PASS" if promises else "FAIL",
                 f"L2.12 title_audit 包含 promises（{len(promises)} 个）"))

            fulfilled = ta.get("all_fulfilled", None)
            self.results.append(
                ("PASS" if fulfilled is True else "FAIL",
                 f"L2.13 title_audit.all_fulfilled = {fulfilled}"))

    def audit_word_count_plan(self):
        """检查字数分配"""
        wcp = self.outline.get("word_count_plan", {})
        sections = self.outline.get("sections", [])

        if wcp:
            total_words = wcp.get("total", 0)
            self.results.append(
                ("PASS" if total_words > 0 else "FAIL",
                 f"L2.14 word_count_plan.total > 0（值: {total_words}）"))
        elif sections:
            total_words = sum(s.get("target_words", 0) for s in sections)
            self.results.append(
                ("PASS" if total_words > 0 else "FAIL",
                 f"L2.14 sections 字数总和 > 0（值: {total_words}）"))
        else:
            self.results.append(("FAIL", "L2.14 无字数分配信息"))


class ArticleAuditor:
    """审计文章输出的质量（正则规则驱动，借鉴 OpenDraft OutputAuditor）"""

    def __init__(self, markdown: str, outline: dict):
        self.text = markdown
        self.outline = outline
        self.results = []

    def audit_all(self) -> list:
        self.audit_section_count()
        self.audit_source_references()
        self.audit_no_planning_leakage()
        self.audit_word_count()
        return self.results

    def audit_section_count(self):
        """检查文章章节数与大纲一致"""
        outline_sections = len(self.outline.get("sections", []))
        # 用 ## 标题计数（排除 # 一级标题）
        md_sections = len(re.findall(r'^## ', self.text, re.MULTILINE))
        self.results.append(
            ("PASS" if md_sections >= outline_sections else "FAIL",
             f"L2.15 文章章节数 ≥ 大纲章节数（文章: {md_sections}, 大纲: {outline_sections}）"))

    def audit_source_references(self):
        """检查文章是否有来源引用"""
        # 检查链接引用
        links = re.findall(r'\[([^\]]+)\]\(https?://[^\)]+\)', self.text)
        # 检查 source 占位符
        source_refs = re.findall(r'\{source_\d+\}', self.text)
        # 检查"来源"/"参考"等标注
        source_mentions = len(re.findall(r'来源|参考|引用|出处|Source|Reference', self.text))

        total_refs = len(links) + len(source_refs) + source_mentions
        self.results.append(
            ("PASS" if total_refs >= 2 else "FAIL",
             f"L2.16 文章有来源引用（链接: {len(links)}, 占位符: {len(source_refs)}, 标注: {source_mentions}）"))

    def audit_no_planning_leakage(self):
        """检查文章没有规划内容泄漏（借鉴 OpenDraft audit_planning_leakage）"""
        leakage_patterns = [
            (r'narrative_role', "narrative_role 泄漏到文章"),
            (r'core_question', "core_question 泄漏到文章"),
            (r'assigned_materials', "assigned_materials 泄漏到文章"),
            (r'target_words', "target_words 泄漏到文章"),
            (r'cognitive_load', "cognitive_load 泄漏到文章"),
            (r'\{source_\d+\}', "{source_NNN} 占位符未替换"),
        ]

        leaked = []
        for pattern, desc in leakage_patterns:
            if re.search(pattern, self.text):
                leaked.append(desc)

        self.results.append(
            ("PASS" if not leaked else "FAIL",
             f"L2.17 无规划内容泄漏（{'无' if not leaked else '、'.join(leaked)}）"))

    def audit_word_count(self):
        """检查文章字数是否在合理范围"""
        # 中文字数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', self.text))
        # 英文单词
        english_words = len(re.findall(r'[a-zA-Z]+', self.text))
        total_words = chinese_chars + english_words

        sections = self.outline.get("sections", [])
        target = sum(s.get("target_words", 0) for s in sections)

        if target > 0:
            ratio = total_words / target
            self.results.append(
                ("PASS" if 0.5 <= ratio <= 2.0 else "FAIL",
                 f"L2.18 文章字数在目标范围内（实际: {total_words}, 目标: {target}, 比例: {ratio:.0%}）"))
        else:
            self.results.append(
                ("PASS" if total_words > 500 else "FAIL",
                 f"L2.18 文章字数 > 500（实际: {total_words}）"))


def generate_article(topic_config: dict) -> dict:
    """调用 vibe-blog 同步 API 生成文章"""
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
    logger.info(f"  ✅ 生成完成 ({elapsed:.0f}s)")
    return result


def run_layer2(topic_config: dict) -> dict:
    """Layer 2: 输出结构审计"""
    print("\n" + "=" * 70)
    print("📐 Layer 2: 输出结构审计（借鉴 OpenDraft OutputAuditor 模式）")
    print("   调 API 生成文章，用正则规则审计大纲和文章结构")
    print("=" * 70)

    result = generate_article(topic_config)
    outline = result.get("outline", {})
    markdown = result.get("markdown", "")

    all_results = []

    # 审计大纲
    print(f"\n📋 审计大纲结构...")
    outline_auditor = OutlineAuditor(outline)
    outline_results = outline_auditor.audit_all()
    all_results.extend(outline_results)
    for status, desc in outline_results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {desc}")

    # 审计文章
    print(f"\n📝 审计文章输出...")
    article_auditor = ArticleAuditor(markdown, outline)
    article_results = article_auditor.audit_all()
    all_results.extend(article_results)
    for status, desc in article_results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {desc}")

    passed = sum(1 for s, _ in all_results if s == "PASS")
    total = len(all_results)

    print(f"\n{'=' * 70}")
    print(f"  Layer 2 结果: {passed}/{total} 通过")
    if passed == total:
        print("  ✅ Layer 2 PASSED — 大纲和文章结构完整")
    else:
        failed = [(s, d) for s, d in all_results if s == "FAIL"]
        print(f"  ❌ Layer 2 FAILED — {len(failed)} 项未通过:")
        for _, desc in failed:
            print(f"     - {desc}")
    print("=" * 70)

    return {
        "layer": 2, "passed": passed, "total": total,
        "results": all_results, "outline": outline, "markdown": markdown,
    }


# ============================================================
# Layer 3: LLM 特性验收
# （借鉴 test_52 的 LLM-as-Judge 模式）
# ============================================================

JUDGE_PROMPT = """你是一个严格的技术博客质量验收员。

用户用以下请求生成了一篇博客文章。你需要检查这篇文章是否体现了「六层骨架设计」的预期效果。

## 生成请求
- 主题: {topic}
- 文章类型: {article_type}
- 目标读者: {target_audience}

## 生成的文章
{article}

---

请逐项检查以下 6 个特性是否在文章中得到体现：

### C1 叙事流连贯性（对应 53 号方案）
文章是否围绕一条叙事主线展开，而非要点堆砌？
- pass: 文章有明确的叙事线（如：从问题到方案到验证），段落之间自然衔接
- fail: 文章像文档一样逐个展开要点，各段独立，缺乏过渡

### C2 章节递进感（对应 51 号方案）
相邻章节之间是否有逻辑递进？
- pass: 章节之间有明确的递进关系（如：概念→价值→实践→进阶），读者跟着走有"渐入佳境"的感觉
- fail: 章节之间可以任意调换顺序，没有逻辑关系

### C3 标题承诺兑现（对应 56 号方案）
标题中的每个关键词承诺是否在内容中被兑现？
- pass: 标题的每个承诺都有对应内容支撑（如"完全指南"覆盖了所有方面，"从入门到精通"有递进）
- fail: 标题严重过度承诺，内容只覆盖了一小部分

### C4 素材引用质量（对应 54 号方案）
文章中是否有具体的数据、案例引用，且标注了来源？
- pass: 至少有 2 处具体数据/案例引用，且有来源标注
- fail: 没有具体数据，全是定性描述

### C5 核心问题驱动（对应 55 号方案）
每个章节是否围绕一个核心问题展开，而非简单罗列要点？
- pass: 每个章节读完后，读者能清楚知道一个问题的答案
- fail: 章节只是要点罗列，读完后不知道回答了什么问题

### C6 视觉规划合理（对应视觉规划层）
文章中的图表/代码块是否与内容匹配，分布是否合理？
- pass: 图表/代码块出现在需要的位置，类型与内容匹配
- fail: 图表/代码块缺失、位置不当、或与内容不匹配

---

请严格按以下 JSON 格式输出（不要输出其他内容）：

```json
{{
  "checks": {{
    "C1_narrative_flow": {{
      "result": "pass 或 fail",
      "evidence": "从文章中引用具体段落作为证据",
      "reason": "判断理由"
    }},
    "C2_progression": {{
      "result": "pass 或 fail",
      "evidence": "列出章节标题展示递进关系",
      "reason": "判断理由"
    }},
    "C3_title_fulfillment": {{
      "result": "pass 或 fail",
      "evidence": "列出标题承诺和对应内容",
      "reason": "判断理由"
    }},
    "C4_citation_quality": {{
      "result": "pass 或 fail",
      "evidence": "列出文章中的数据引用和来源",
      "reason": "判断理由"
    }},
    "C5_core_question": {{
      "result": "pass 或 fail",
      "evidence": "指出每个章节回答了什么问题",
      "reason": "判断理由"
    }},
    "C6_visual_planning": {{
      "result": "pass 或 fail",
      "evidence": "列出图表/代码块的位置和类型",
      "reason": "判断理由"
    }}
  }},
  "pass_count": 0,
  "total": 6,
  "verdict": "PASS 或 FAIL",
  "summary": "一句话总结这篇文章在六层骨架设计方面的表现"
}}
```
"""

CHECK_NAMES = {
    "C1_narrative_flow": "C1 叙事流连贯性",
    "C2_progression": "C2 章节递进感",
    "C3_title_fulfillment": "C3 标题承诺兑现",
    "C4_citation_quality": "C4 素材引用质量",
    "C5_core_question": "C5 核心问题驱动",
    "C6_visual_planning": "C6 视觉规划合理",
}
CHECK_KEYS = list(CHECK_NAMES.keys())
PASS_THRESHOLD = 4


def call_judge(topic_config: dict, article: str) -> dict:
    """调用 LLM 评估文章"""
    prompt = JUDGE_PROMPT.format(
        topic=topic_config["topic"],
        article_type=topic_config.get("article_type", "tutorial"),
        target_audience=topic_config.get("target_audience", "intermediate"),
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


def run_layer3(topic_config: dict, markdown: str = None) -> dict:
    """Layer 3: LLM 特性验收"""
    print("\n" + "=" * 70)
    print("🧑‍⚖️ Layer 3: LLM 特性验收（借鉴 LLM-as-Judge 模式）")
    print("   用 LLM 评估文章是否体现六层骨架设计的效果")
    print("=" * 70)

    if not markdown:
        result = generate_article(topic_config)
        markdown = result.get("markdown", "")

    if not markdown:
        print("  ❌ 文章内容为空，跳过 Layer 3")
        return {"layer": 3, "passed": 0, "total": 6, "results": []}

    eval_result = call_judge(topic_config, markdown)
    checks = eval_result.get("checks", {})
    pass_count = eval_result.get("pass_count", 0)
    verdict = eval_result.get("verdict", "UNKNOWN")

    print(f"\n📊 LLM 特性验收报告:")
    for key in CHECK_KEYS:
        check = checks.get(key, {})
        result_val = check.get("result", "unknown")
        icon = "✅" if result_val == "pass" else "❌"
        print(f"\n  {icon} {CHECK_NAMES[key]}: {result_val.upper()}")
        print(f"     证据: {check.get('evidence', 'N/A')}")
        print(f"     理由: {check.get('reason', 'N/A')}")

    print(f"\n{'=' * 70}")
    verdict_icon = "✅" if verdict == "PASS" else "❌"
    print(f"  {verdict_icon} Layer 3 结果: {verdict} ({pass_count}/{len(CHECK_KEYS)} 项通过)")
    print(f"  📝 总结: {eval_result.get('summary', 'N/A')}")
    print("=" * 70)

    return {
        "layer": 3, "passed": pass_count, "total": len(CHECK_KEYS),
        "eval_result": eval_result,
    }


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="[57] 博客骨架设计 — 三层验证")
    parser.add_argument("--layer", type=int, default=1, choices=[1, 2, 3],
                        help="验证层级: 1=Prompt静态检查, 2=+输出审计, 3=+LLM验收")
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
    print("🔬 57 号方案验证 — 博客骨架设计完整方案")
    print(f"   验证层级: Layer 1{' + Layer 2' if args.layer >= 2 else ''}{' + Layer 3' if args.layer >= 3 else ''}")
    print("=" * 70)

    all_layer_results = []

    # Layer 1: 始终运行
    l1 = run_layer1()
    all_layer_results.append(l1)

    # Layer 2 + 3: 需要生成文章
    if args.layer >= 2:
        for tc in topics:
            l2 = run_layer2(tc)
            all_layer_results.append(l2)

            if args.layer >= 3:
                markdown = l2.get("markdown", "")
                l3 = run_layer3(tc, markdown)
                all_layer_results.append(l3)

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    save_data = {
        "feature": "57-博客骨架设计完整方案",
        "max_layer": args.layer,
        "layers": [
            {"layer": r["layer"], "passed": r["passed"], "total": r["total"]}
            for r in all_layer_results
        ],
        "timestamp": datetime.now().isoformat(),
    }
    result_file.write_text(json.dumps(save_data, ensure_ascii=False, indent=2))

    # 总结
    print("\n" + "=" * 70)
    print("📊 总体验证结果")
    print("=" * 70)
    all_pass = True
    for r in all_layer_results:
        layer = r["layer"]
        passed = r["passed"]
        total = r["total"]
        icon = "✅" if passed == total else "❌"
        print(f"  {icon} Layer {layer}: {passed}/{total} 通过")
        if passed < total:
            all_pass = False

    if all_pass:
        print("\n🎉 所有层级验证通过！57 号方案特性已完整实现。")
    else:
        print("\n💥 部分验证未通过，请检查上方报告。")
    print("=" * 70)


if __name__ == "__main__":
    main()
