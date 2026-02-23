"""
TDD 测试 — 1003.06 代码执行沙箱
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.blog_generator.tools.code_executor import (
    ImportGuard, CodeExecutionError, WorkspaceManager, run_code_sync, run_code,
)


# ── ImportGuard 测试 ──

class TestImportGuard:
    def test_allows_safe_imports(self):
        code = "import math\nimport json\nprint(math.pi)"
        ImportGuard.validate(code)  # 不应抛异常

    def test_blocks_dangerous_imports(self):
        code = "import os\nos.system('ls')"
        with pytest.raises(CodeExecutionError, match="不在允许列表中"):
            ImportGuard.validate(code)

    def test_blocks_from_import(self):
        code = "from subprocess import run"
        with pytest.raises(CodeExecutionError, match="不在允许列表中"):
            ImportGuard.validate(code)

    def test_syntax_error(self):
        code = "def foo(:"
        with pytest.raises(CodeExecutionError, match="语法错误"):
            ImportGuard.validate(code)

    def test_custom_allowed(self):
        code = "import numpy"
        ImportGuard.validate(code, allowed_imports=["numpy"])

    def test_no_imports_passes(self):
        code = "x = 1 + 2\nprint(x)"
        ImportGuard.validate(code)


# ── WorkspaceManager 测试 ──

class TestWorkspaceManager:
    def test_creates_temp_dir(self, tmp_path):
        ws = WorkspaceManager(workspace_dir=str(tmp_path))
        with ws.create_temp_dir() as td:
            assert td.exists()
            assert str(td).startswith(str(tmp_path))
        assert not td.exists()

    def test_collect_artifacts(self, tmp_path):
        ws = WorkspaceManager(workspace_dir=str(tmp_path))
        (tmp_path / "output.png").write_text("fake image")
        (tmp_path / "code.py").write_text("print(1)")
        names, paths = ws.collect_artifacts(tmp_path)
        assert "output.png" in names
        assert "code.py" not in names

    def test_collect_artifacts_empty(self, tmp_path):
        ws = WorkspaceManager(workspace_dir=str(tmp_path))
        names, paths = ws.collect_artifacts(tmp_path)
        assert names == []


# ── run_code_sync 测试 ──

class TestRunCodeSync:
    def test_simple_print(self, tmp_path):
        result = run_code_sync("print('hello')", workspace_dir=str(tmp_path))
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_math_calculation(self, tmp_path):
        result = run_code_sync("import math\nprint(math.pi)", workspace_dir=str(tmp_path))
        assert result["exit_code"] == 0
        assert "3.14" in result["stdout"]

    def test_runtime_error(self, tmp_path):
        result = run_code_sync("raise ValueError('test error')", workspace_dir=str(tmp_path))
        assert result["exit_code"] != 0
        assert "ValueError" in result["stderr"]

    def test_blocked_import(self, tmp_path):
        result = run_code_sync("import os\nos.listdir('.')", workspace_dir=str(tmp_path))
        assert result["exit_code"] == -1
        assert "不在允许列表中" in result["stderr"]

    def test_timeout(self, tmp_path):
        # time 不在默认白名单中，但我们可以用 while True 测试
        # 用自定义白名单允许 time
        result = run_code_sync(
            "import time\ntime.sleep(30)",
            timeout=1,
            allowed_imports=["time"],
            workspace_dir=str(tmp_path),
        )
        assert result["exit_code"] == -1
        assert "超时" in result["stderr"]

    def test_elapsed_ms(self, tmp_path):
        result = run_code_sync("print(1)", workspace_dir=str(tmp_path))
        assert result["elapsed_ms"] >= 0


# ── run_code async 测试 ──

class TestRunCodeAsync:
    @pytest.mark.asyncio
    async def test_simple_print(self):
        result = await run_code("print('async hello')")
        assert result["exit_code"] == 0
        assert "async hello" in result["stdout"]

    @pytest.mark.asyncio
    async def test_blocked_import(self):
        result = await run_code("import os")
        assert result["exit_code"] == -1
        assert "不在允许列表中" in result["stderr"]

    @pytest.mark.asyncio
    async def test_runtime_error(self):
        result = await run_code("1/0")
        assert result["exit_code"] != 0
        assert "ZeroDivisionError" in result["stderr"]
