# Step 1.2: Planner 字数分配规则 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add word count allocation rules to Planner based on narrative_role, ensuring each section gets appropriate target_words based on its role in the narrative.

**Architecture:** Modify planner.j2 template to include word allocation logic, add target_words field to section schema, create E2E test to verify allocation accuracy.

**Tech Stack:** Jinja2 templates, Python, Playwright (E2E testing), pytest

---

## Task 1: Add Word Allocation Rules to planner.j2

**Files:**
- Modify: `backend/infrastructure/prompts/blog/planner.j2:100-150`
- Test: `backend/tests/test_70_1_2_word_allocation_e2e.py` (to be created)

**Step 1: Add word allocation rules table after narrative mode section**

Insert after line 130 (after narrative_role table):

```jinja2
## 字数分配规则（第二步）

### 总目标字数映射

根据 `target_length` 参数确定总目标字数：
- **mini**: 2000 字（快速测试，1个章节）
- **short**: 4000 字（2-3个章节）
- **medium**: 6000 字（4-5个章节）
- **long**: 10000 字（6-8个章节）
{% if target_word_count %}
- **custom**: {{ target_word_count }} 字（用户自定义）
{% endif %}

当前目标长度：**{{ target_length }}**
{% if target_word_count %}
总目标字数：**{{ target_word_count }} 字**
{% else %}
总目标字数：**{% if target_length == 'mini' %}2000{% elif target_length == 'short' %}4000{% elif target_length == 'medium' %}6000{% elif target_length == 'long' %}10000{% endif %} 字**
{% endif %}

### 按 narrative_role 分配字数比例

| narrative_role | 推荐比例 | 说明 |
|---------------|---------|------|
| hook | 10-15% | 引子章节，简短有力 |
| what | 15-20% | 概念定义，需要充分解释 |
| why | 10-15% | 动机说明，中等篇幅 |
| how | 25-35% | 操作步骤，最重要的核心内容 |
| deep_dive | 20-30% | 深入原理，需要详细展开 |
| verify | 10-15% | 验证测试，中等篇幅 |
| summary | 5-10% | 总结章节，简洁概括 |
| catalog_item | 按条目均分 | 清单模式下每个条目平均分配 |

### 字数分配约束

**必须严格遵守以下约束**：
1. **总和约束**：所有章节的 `target_words` 之和必须等于总目标字数（误差 ≤ 5%）
2. **最小值约束**：每个章节至少 200 字
3. **最大值约束**：单个章节不超过总字数的 40%
4. **比例约束**：每个章节的字数应符合其 narrative_role 的推荐比例

### 字数分配示例

假设总目标字数为 6000 字，有 5 个章节：
- section_1 (hook): 600 字 (10%)
- section_2 (what): 1200 字 (20%)
- section_3 (how): 2100 字 (35%)
- section_4 (verify): 900 字 (15%)
- section_5 (summary): 1200 字 (20%)
- **总和**: 6000 字 ✓
```

**Step 2: Update JSON schema to include target_words field**

Modify the sections array schema (around line 170-186):

```jinja2
  "sections": [
    {
      "id": "section_1",
      "title": "章节标题",
      "narrative_role": "本章叙事角色 (hook | what | why | how | compare | deep_dive | verify | summary | catalog_item)",
      "target_words": 整数，本章节目标字数（必须 > 200，且所有章节总和等于总目标字数）,
      "key_concept": "本章核心概念",
      "learning_objective": "本章节支撑的学习目标（可选）",
      "content_outline": ["要点1", "要点2", "要点3"],
      "verbatim_data_refs": ["需要在本章节使用的关键数据（原样引用）"],
      "image_type": "flowchart | architecture | sequence | comparison | chart | none",
      "illustration_type": "infographic | scene | flowchart | comparison | framework | timeline",
      "image_description": "图片内容描述 (用于生成，如果 image_type 不是 none)",
      "code_blocks": 代码块数量 (tutorial类型0-1，其他类型必须为0),
      "has_output_block": true/false,
      "key_quote": "章节核心结论 (用于引用块)",
      "cognitive_load": "low | medium | high"
    }
  ],
```

**Step 3: Add word allocation instructions to notes section**

Add to the 注意事项 section (around line 231):

```jinja2
9. **字数分配必须精确**：
   - 计算每个章节的 target_words 时，确保总和等于总目标字数
   - 根据 narrative_role 按推荐比例分配
   - 如果是 catalog 模式，所有 catalog_item 章节平均分配字数
   - 示例计算：总字数 6000，5个章节 → hook(10%)=600, what(20%)=1200, how(35%)=2100, verify(15%)=900, summary(20%)=1200
```

**Step 4: Verify template syntax**

Run: `python -c "from jinja2 import Template; Template(open('backend/infrastructure/prompts/blog/planner.j2').read())"`
Expected: No syntax errors

**Step 5: Commit template changes**

```bash
git add backend/infrastructure/prompts/blog/planner.j2
git commit -m "feat(planner): add word allocation rules based on narrative_role

- Add word count mapping for target_length (mini/short/medium/long)
- Add narrative_role-based allocation percentages
- Add target_words field to section schema
- Add constraints: sum must equal total, min 200, max 40%
- Ref: 70.1.2 Step1.2-字数分配规则.md"
```

---

## Task 2: Create E2E Test for Word Allocation

**Files:**
- Create: `backend/tests/test_70_1_2_word_allocation_e2e.py`

**Step 1: Write test file structure**

```python
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
    cd backend && python tests/test_70_1_2_word_allocation_e2e.py --api-only
"""

import sys
import os
import json
import argparse
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:5001"

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

# narrative_role 推荐比例
ROLE_PERCENTAGES = {
    "hook": (0.10, 0.15),
    "what": (0.15, 0.20),
    "why": (0.10, 0.15),
    "how": (0.25, 0.35),
    "deep_dive": (0.20, 0.30),
    "verify": (0.10, 0.15),
    "summary": (0.05, 0.10),
}
```

**Step 2: Implement field validation (A表)**

```python
def validate_field_completeness(outline: dict, expected_total: int) -> dict:
    """
    A表 — 字段检查
    """
    results = {
        "has_target_words": True,
        "all_positive": True,
        "sum_accuracy": None,
        "sum_error_pct": None,
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
        if "target_words" not in section:
            results["has_target_words"] = False
            results["details"].append(f"Section {i+1} missing target_words")
        else:
            tw = section["target_words"]
            if not isinstance(tw, int) or tw <= 0:
                results["all_positive"] = False
                results["details"].append(f"Section {i+1} target_words invalid: {tw}")
            total_words += tw

    # Check 2: 所有 section 的 target_words 之和
    if total_words > 0:
        error_pct = abs(total_words - expected_total) / expected_total
        results["sum_error_pct"] = error_pct
        results["sum_accuracy"] = error_pct <= 0.10  # 10% tolerance
        results["details"].append(f"Total words: {total_words}, Expected: {expected_total}, Error: {error_pct:.1%}")

    return results
```

**Step 3: Implement ratio validation (B表)**

```python
def validate_allocation_ratios(outline: dict, expected_total: int) -> dict:
    """
    B表 — 合理性检查
    """
    results = {
        "max_section_ok": True,
        "min_section_ok": True,
        "ratio_matches": 0,
        "ratio_total": 0,
        "details": []
    }

    sections = outline.get("sections", [])
    total_words = sum(s.get("target_words", 0) for s in sections)

    if total_words == 0:
        return results

    for section in sections:
        tw = section.get("target_words", 0)
        role = section.get("narrative_role", "")
        pct = tw / total_words

        # Check 1: 最大章节字数 ≤ 总字数 40%
        if pct > 0.40:
            results["max_section_ok"] = False
            results["details"].append(f"Section '{section.get('title')}' too large: {pct:.1%}")

        # Check 2: 最小章节字数 ≥ 200 字
        if tw < 200:
            results["min_section_ok"] = False
            results["details"].append(f"Section '{section.get('title')}' too small: {tw} words")

        # Check 3: 字数分配与 narrative_role 匹配
        if role in ROLE_PERCENTAGES:
            min_pct, max_pct = ROLE_PERCENTAGES[role]
            results["ratio_total"] += 1
            if min_pct <= pct <= max_pct:
                results["ratio_matches"] += 1
            else:
                results["details"].append(
                    f"Section '{section.get('title')}' ({role}) ratio {pct:.1%} "
                    f"outside expected {min_pct:.0%}-{max_pct:.0%}"
                )

    return results
```

**Step 4: Implement main test runner**

```python
def test_word_allocation(case: dict, api_only: bool = False) -> dict:
    """
    Run single test case
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing: {case['topic']} ({case['target_length']})")
    logger.info(f"{'='*60}")

    # Call API to generate outline
    response = requests.post(
        f"{BACKEND_URL}/api/blog/generate",
        json={
            "topic": case["topic"],
            "article_type": case["article_type"],
            "target_length": case["target_length"],
            "target_audience": "beginner",
        },
        stream=True
    )

    # Parse SSE stream to get outline
    outline = None
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                data = json.loads(line_str[6:])
                if data.get('type') == 'outline_complete':
                    outline = data.get('data', {}).get('outline')
                    break

    if not outline:
        return {"success": False, "error": "No outline generated"}

    # Validate
    field_results = validate_field_completeness(outline, case["expected_total_words"])
    ratio_results = validate_allocation_ratios(outline, case["expected_total_words"])

    # Determine pass/fail
    passed = (
        field_results["has_target_words"] and
        field_results["all_positive"] and
        field_results["sum_accuracy"] and
        ratio_results["max_section_ok"] and
        ratio_results["min_section_ok"]
    )

    return {
        "success": passed,
        "field_results": field_results,
        "ratio_results": ratio_results,
        "outline": outline
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headed", action="store_true", help="Run in headed mode")
    parser.add_argument("--api-only", action="store_true", help="API only, no browser")
    parser.add_argument("--cases", default="1,2,3", help="Test cases to run (e.g., '1,2,3')")
    args = parser.parse_args()

    case_indices = [int(i)-1 for i in args.cases.split(",")]
    selected_cases = [TEST_CASES[i] for i in case_indices if i < len(TEST_CASES)]

    results = []
    for case in selected_cases:
        result = test_word_allocation(case, args.api_only)
        results.append(result)

    # Summary
    passed = sum(1 for r in results if r["success"])
    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY: {passed}/{len(results)} tests passed")
    logger.info(f"{'='*60}")

    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
```

**Step 5: Run test to verify it fails (before implementation)**

Run: `cd backend && python tests/test_70_1_2_word_allocation_e2e.py --api-only --cases 1`
Expected: FAIL with "target_words field missing" or "sum_accuracy False"

**Step 6: Commit test file**

```bash
git add backend/tests/test_70_1_2_word_allocation_e2e.py
git commit -m "test(planner): add E2E test for word allocation rules

- Test field completeness (target_words present and valid)
- Test sum accuracy (within 10% tolerance)
- Test allocation ratios (match narrative_role percentages)
- Test constraints (min 200, max 40%, ratios match)
- Ref: 70.1.2 Step1.2-字数分配规则.md"
```

---

## Task 3: Verify Implementation

**Step 1: Start backend server**

Run: `cd backend && python app.py`
Expected: Server starts on port 5001

**Step 2: Run E2E test with all cases**

Run: `cd backend && python tests/test_70_1_2_word_allocation_e2e.py --api-only --cases 1,2,3`
Expected: All 3 tests PASS

**Step 3: Manual verification (optional)**

Open frontend, generate blog with different target_length values, inspect outline JSON to verify:
- Each section has target_words field
- Sum equals expected total (±10%)
- Ratios match narrative_role recommendations

**Step 4: Run existing tests to ensure no regression**

Run: `cd backend && pytest tests/test_70_1_1_*.py -v`
Expected: All existing tests still pass

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat(planner): complete word allocation implementation

- Modified planner.j2 with allocation rules and constraints
- Added target_words field to section schema
- Created E2E test with 3 test cases
- All tests passing
- Ref: 70.1.2 Step1.2-字数分配规则.md"
```

---

## Success Criteria

✅ **Field Completeness**: All 3 test topics output target_words for every section
✅ **Sum Accuracy**: All 3 topics have word sum within 10% of expected total
✅ **Ratio Reasonableness**: At least 2/3 topics have allocations matching recommended percentages
✅ **No Regression**: Existing tests (70.1.1) still pass

---

## Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| target_words all 0 | JSON schema not updated | Check section example includes target_words |
| Sum deviation large | LLM math capability | Add stronger constraint in prompt: "sum MUST equal X" |
| Unreasonable allocation | Ratio table unclear | Add concrete number examples |
| Test fails to connect | Backend not running | Start backend: `cd backend && python app.py` |

---

## Estimated Time

- Task 1 (Template): 30 minutes
- Task 2 (Test): 30 minutes
- Task 3 (Verify): 10 minutes
- **Total**: ~70 minutes
