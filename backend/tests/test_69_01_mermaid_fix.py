#!/usr/bin/env python3
"""
[需求点 69.01] Mermaid 语法自动修复 — 单元测试

验证逻辑：
  1. _sanitize_mermaid 能修复常见静态问题
  2. _validate_mermaid 能检出语法错误
  3. 修复链整体工作正常

用法：
  cd backend
  python tests/test_69_01_mermaid_fix.py
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_sanitize_mermaid():
    """测试静态预处理"""
    from services.blog_generator.agents.artist import ArtistAgent

    class FakeLLM:
        def chat(self, **kwargs): return ""

    agent = ArtistAgent(FakeLLM())

    # 测试 1: 移除 ```mermaid 标记
    code = "```mermaid\nflowchart TB\n  A --> B\n```"
    result = agent._sanitize_mermaid(code)
    assert not result.startswith('```'), f"应移除 ```mermaid 标记: {result}"
    assert result.startswith('flowchart'), f"应以 flowchart 开头: {result}"
    print("  [PASS] 移除 ```mermaid 标记")

    # 测试 2: 移除节点文本中的 \n
    code = 'flowchart TB\n  A[第一行\\n第二行] --> B'
    result = agent._sanitize_mermaid(code)
    assert '\\n' not in result, f"应移除 \\n: {result}"
    assert '第一行 第二行' in result, f"应替换为空格: {result}"
    print("  [PASS] 移除节点文本中的 \\n")

    # 测试 3: 修复重复箭头
    code = 'flowchart TB\n  A --> --> B'
    result = agent._sanitize_mermaid(code)
    assert '-->' in result and '--> -->' not in result, f"应修复重复箭头: {result}"
    print("  [PASS] 修复重复箭头")

    return True


def test_validate_mermaid():
    """测试语法校验"""
    from services.blog_generator.agents.artist import ArtistAgent

    class FakeLLM:
        def chat(self, **kwargs): return ""

    agent = ArtistAgent(FakeLLM())

    # 测试 1: 正常代码应通过
    code = "flowchart TB\n  A --> B\n  B --> C"
    is_valid, msg = agent._validate_mermaid(code)
    assert is_valid, f"正常代码应通过: {msg}"
    print("  [PASS] 正常代码通过校验")

    # 测试 2: 缺少图表类型声明
    code = "A --> B\n  B --> C"
    is_valid, msg = agent._validate_mermaid(code)
    assert not is_valid, "缺少声明应失败"
    assert "图表类型" in msg, f"应提示缺少声明: {msg}"
    print("  [PASS] 检出缺少图表类型声明")

    # 测试 3: subgraph 不匹配
    code = "flowchart TB\n  subgraph A\n    X --> Y"
    is_valid, msg = agent._validate_mermaid(code)
    assert not is_valid, "subgraph 不匹配应失败"
    assert "subgraph" in msg, f"应提示 subgraph 不匹配: {msg}"
    print("  [PASS] 检出 subgraph 不匹配")

    # 测试 4: sequenceDiagram 应通过
    code = "sequenceDiagram\n  Alice->>Bob: Hello"
    is_valid, msg = agent._validate_mermaid(code)
    assert is_valid, f"sequenceDiagram 应通过: {msg}"
    print("  [PASS] sequenceDiagram 通过校验")

    return True


def test_full_pipeline():
    """测试完整修复链（含 sanitize + validate）"""
    from services.blog_generator.agents.artist import ArtistAgent

    class FakeLLM:
        def chat(self, **kwargs): return ""

    agent = ArtistAgent(FakeLLM())

    # 含多种问题的代码
    code = "```mermaid\nflowchart TB\n  A[步骤一\\n详情] --> --> B[步骤二]\n  subgraph 子图\n    C --> D\n  end\n```"
    sanitized = agent._sanitize_mermaid(code)
    is_valid, msg = agent._validate_mermaid(sanitized)

    assert is_valid, f"修复后应通过校验: {msg}"
    assert '\\n' not in sanitized, "应移除 \\n"
    assert '```' not in sanitized, "应移除 ``` 标记"
    print("  [PASS] 完整修复链工作正常")

    return True


def main():
    print("=" * 60)
    print("  69.01 Mermaid 语法自动修复 — 单元测试")
    print("=" * 60)

    all_pass = True
    tests = [
        ("sanitize_mermaid", test_sanitize_mermaid),
        ("validate_mermaid", test_validate_mermaid),
        ("full_pipeline", test_full_pipeline),
    ]

    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            result = test_fn()
            if not result:
                all_pass = False
        except Exception as e:
            print(f"  [FAIL] 异常: {e}")
            all_pass = False

    print(f"\n{'=' * 60}")
    if all_pass:
        print("  所有测试通过！Mermaid 语法修复功能正常。")
    else:
        print("  部分测试失败，请检查上方报告。")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
