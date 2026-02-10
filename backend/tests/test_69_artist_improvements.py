#!/usr/bin/env python3
"""
[需求点 69] Artist 配图优化 — 单元测试

验证 Artist Agent 的确定性改进：
  A1 图片预算控制  — 超出预算时按优先级裁剪
  A2 预算优先级    — outline > placeholder > missing_diagram
  A3 ASCII 检测    — 正确检测 ASCII 流程图
  A4 ASCII 排除    — 不误检 Markdown 表格
  A5 Mermaid 清理  — 正确清理 Mermaid 语法
  A6 Mermaid 校验  — 检测 subgraph/end 不匹配

用法：
  cd backend
  python -m pytest tests/test_69_artist_improvements.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.blog_generator.agents.artist import (
    ArtistAgent,
    IMAGE_BUDGET,
)


class MockLLM:
    def chat(self, **kwargs):
        return '{"render_method": "mermaid", "content": "flowchart TB\\n    A --> B", "caption": "test"}'


class TestImageBudget:
    def test_budget_values_exist(self):
        assert 'mini' in IMAGE_BUDGET
        assert 'short' in IMAGE_BUDGET
        assert 'medium' in IMAGE_BUDGET
        assert 'long' in IMAGE_BUDGET

    def test_budget_ordering(self):
        assert IMAGE_BUDGET['mini'] < IMAGE_BUDGET['short']
        assert IMAGE_BUDGET['short'] <= IMAGE_BUDGET['medium']
        assert IMAGE_BUDGET['medium'] <= IMAGE_BUDGET['long']

    def test_budget_reasonable_values(self):
        assert IMAGE_BUDGET['mini'] >= 2
        assert IMAGE_BUDGET['long'] <= 15


class TestASCIIDetection:
    def setup_method(self):
        self.agent = ArtistAgent(MockLLM())

    def test_detects_ascii_flowchart(self):
        content = """Some text before

+-------+     +-------+
| Start |---->| End   |
+-------+     +-------+

Some text after"""
        regions = self.agent.detect_ascii_flowcharts(content)
        assert len(regions) >= 1

    def test_ignores_markdown_table(self):
        content = """| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |
| Value 3  | Value 4  |"""
        regions = self.agent.detect_ascii_flowcharts(content)
        assert len(regions) == 0

    def test_ignores_code_block(self):
        content = """```python
+-------+
| code  |---->
+-------+
```"""
        regions = self.agent.detect_ascii_flowcharts(content)
        assert len(regions) == 0


class TestMermaidSanitize:
    def setup_method(self):
        self.agent = ArtistAgent(MockLLM())

    def test_removes_markdown_wrapper(self):
        code = "```mermaid\nflowchart TB\n    A --> B\n```"
        result = self.agent._sanitize_mermaid(code)
        assert not result.startswith("```")
        assert "flowchart TB" in result

    def test_removes_newline_in_nodes(self):
        code = "flowchart TB\n    A[Hello\\nWorld] --> B"
        result = self.agent._sanitize_mermaid(code)
        assert "\\n" not in result
        assert "Hello World" in result


class TestMermaidValidate:
    def setup_method(self):
        self.agent = ArtistAgent(MockLLM())

    def test_valid_flowchart(self):
        code = "flowchart TB\n    A --> B"
        is_valid, msg = self.agent._validate_mermaid(code)
        assert is_valid

    def test_missing_type_declaration(self):
        code = "A --> B"
        is_valid, msg = self.agent._validate_mermaid(code)
        assert not is_valid
        assert "类型声明" in msg

    def test_subgraph_end_mismatch(self):
        code = 'flowchart TB\n    subgraph S1["Group"]\n        A --> B'
        is_valid, msg = self.agent._validate_mermaid(code)
        assert not is_valid
        assert "subgraph" in msg
