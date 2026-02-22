"""
1003.06 代码执行沙箱

在隔离环境中执行 Python 代码并收集结果。
安全机制：ImportGuard AST 白名单 + WorkspaceManager 路径隔离 + subprocess 超时。
"""

import ast
import asyncio
import logging
import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
DEFAULT_WORKSPACE = "backend/data/code_workspace"
CODE_EXECUTOR_WORKSPACE_ENV = "CODE_EXECUTOR_WORKSPACE"


class CodeExecutionError(Exception):
    """代码执行错误"""


class ImportGuard:
    """AST 静态分析，限制可导入模块"""

    DEFAULT_ALLOWED = [
        "math", "statistics", "collections", "itertools", "functools",
        "json", "csv", "datetime", "re", "string", "textwrap",
        "random", "decimal", "fractions", "operator", "copy",
        "dataclasses", "typing", "enum", "abc",
    ]

    @staticmethod
    def validate(code: str, allowed_imports: Optional[list] = None):
        if allowed_imports is None:
            allowed_imports = ImportGuard.DEFAULT_ALLOWED
        allowed = set(allowed_imports)
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise CodeExecutionError(f"代码语法错误: {exc}") from exc

        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module.split(".")[0])

        unauthorized = sorted({name for name in imported if name not in allowed})
        if unauthorized:
            raise CodeExecutionError(
                f"以下模块不在允许列表中: {', '.join(unauthorized)}"
            )


class WorkspaceManager:
    """管理隔离工作空间"""

    def __init__(self, workspace_dir: Optional[str] = None):
        env_path = os.getenv(CODE_EXECUTOR_WORKSPACE_ENV)
        if env_path:
            self.base_dir = Path(env_path).expanduser().resolve()
        elif workspace_dir:
            self.base_dir = Path(workspace_dir).resolve()
        else:
            project_root = Path(__file__).resolve().parents[4]
            self.base_dir = (project_root / DEFAULT_WORKSPACE).resolve()

        self.allowed_roots = [self.base_dir]
        self._initialized = False

    def initialize(self):
        if not self._initialized:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self._initialized = True

    @contextmanager
    def create_temp_dir(self):
        self.initialize()
        with tempfile.TemporaryDirectory(dir=self.base_dir) as td:
            yield Path(td)

    def collect_artifacts(self, work_dir: Path):
        names, paths = [], []
        if not work_dir or not work_dir.exists():
            return names, paths
        for f in work_dir.iterdir():
            if f.is_file() and f.name not in (".gitkeep", "code.py"):
                names.append(f.name)
                paths.append(str(f.resolve()))
        return names, paths


class CodeExecutionEnvironment:
    """封装 subprocess 执行逻辑"""

    def __init__(self, workspace: WorkspaceManager):
        self.workspace = workspace

    def run_python(self, code: str, timeout: int, work_dir: Optional[Path] = None):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        with self.workspace.create_temp_dir() as temp_dir:
            code_file = temp_dir / "code.py"
            code_file.write_text(code, encoding="utf-8")
            cwd = work_dir if work_dir else temp_dir
            start = time.time()
            result = subprocess.run(
                [sys.executable, str(code_file)],
                check=False, capture_output=True,
                text=True, encoding="utf-8", errors="replace",
                timeout=timeout, cwd=str(cwd), env=env,
            )
            elapsed_ms = (time.time() - start) * 1000
            return result.stdout, result.stderr, result.returncode, elapsed_ms


# 模块级单例
_workspace = None
_exec_env = None


def _get_workspace() -> WorkspaceManager:
    global _workspace
    if _workspace is None:
        _workspace = WorkspaceManager()
    return _workspace


def _get_exec_env() -> CodeExecutionEnvironment:
    global _exec_env
    if _exec_env is None:
        _exec_env = CodeExecutionEnvironment(_get_workspace())
    return _exec_env


def run_code_sync(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
    allowed_imports: Optional[list] = None,
    workspace_dir: Optional[str] = None,
) -> dict:
    """同步执行 Python 代码"""
    ws = WorkspaceManager(workspace_dir) if workspace_dir else _get_workspace()
    ws.initialize()

    try:
        ImportGuard.validate(code, allowed_imports)
    except CodeExecutionError as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1, "elapsed_ms": 0.0}

    exec_env = CodeExecutionEnvironment(ws)
    try:
        stdout, stderr, exit_code, elapsed_ms = exec_env.run_python(code, timeout)
        return {"stdout": stdout, "stderr": stderr, "exit_code": exit_code, "elapsed_ms": elapsed_ms}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"代码执行超时 ({timeout} 秒)", "exit_code": -1, "elapsed_ms": timeout * 1000}
    except Exception as exc:
        return {"stdout": "", "stderr": f"执行失败: {exc}", "exit_code": -1, "elapsed_ms": 0.0}


async def run_code(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
    allowed_imports: Optional[list] = None,
) -> dict:
    """异步执行 Python 代码"""
    try:
        ImportGuard.validate(code, allowed_imports)
    except CodeExecutionError as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1, "elapsed_ms": 0.0}

    ws = _get_workspace()
    ws.initialize()
    exec_env = _get_exec_env()
    loop = asyncio.get_running_loop()

    def _execute():
        return exec_env.run_python(code, timeout)

    try:
        stdout, stderr, exit_code, elapsed_ms = await loop.run_in_executor(None, _execute)
        return {"stdout": stdout, "stderr": stderr, "exit_code": exit_code, "elapsed_ms": elapsed_ms}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"代码执行超时 ({timeout} 秒)", "exit_code": -1, "elapsed_ms": timeout * 1000}
    except Exception as exc:
        return {"stdout": "", "stderr": f"执行失败: {exc}", "exit_code": -1, "elapsed_ms": 0.0}
