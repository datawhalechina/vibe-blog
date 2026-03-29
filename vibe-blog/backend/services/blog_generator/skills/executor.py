"""
37.14 Skill 执行器

SkillExecutor — 统一执行入口，含超时保护和日志记录。
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SkillExecutor:
    """Skill 统一执行器"""

    def __init__(self, registry, task_log=None):
        self.registry = registry
        self.task_log = task_log

    def execute(self, skill_name: str, input_data: Any) -> Dict[str, Any]:
        """执行单个 Skill"""
        defn = self.registry.get_skill(skill_name)
        if not defn:
            return {"success": False, "error": f"Skill 不存在: {skill_name}", "result": None}

        start = time.monotonic()
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(defn.func, input_data)
                result = future.result(timeout=defn.timeout)
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info(f"[Skill] {skill_name} 执行成功 ({duration_ms}ms)")
            return {"success": True, "result": result, "duration_ms": duration_ms}
        except FuturesTimeout:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.warning(f"[Skill] {skill_name} 超时 ({defn.timeout}s)")
            return {"success": False, "error": f"超时 ({defn.timeout}s)", "result": None, "duration_ms": duration_ms}
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error(f"[Skill] {skill_name} 执行失败: {e}")
            return {"success": False, "error": str(e), "result": None, "duration_ms": duration_ms}

    def execute_batch(self, skill_names: List[str], blog_state: Any) -> Dict[str, Dict]:
        """批量执行多个 Skills"""
        results: Dict[str, Dict] = {}
        for name in skill_names:
            results[name] = self.execute(name, blog_state)
        return results
