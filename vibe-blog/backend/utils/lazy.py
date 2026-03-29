"""
懒初始化描述符（102.10 迁移特性 F）

线程安全的泛型懒初始化描述符，首次访问时调用 factory 创建资源，
后续访问返回缓存值。支持 reset() 清理和 cleanup 回调。
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional


class LazyResource:
    """
    线程安全的懒初始化描述符。

    用法：
        class Service:
            db = LazyResource(factory=lambda self: create_db_connection())

        svc = Service()
        svc.db  # 首次访问时创建
        svc.db  # 返回缓存值
        type(svc).db.reset(svc)  # 清理并重置
    """

    def __init__(
        self,
        factory: Callable[[Any], Any],
        cleanup: Optional[Callable[[Any], None]] = None,
    ):
        self.factory = factory
        self.cleanup = cleanup
        self._attr_name = f"_lazy_{id(self)}"
        self._lock = threading.Lock()

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr_name = f"_lazy_{name}"

    def __get__(self, obj: Any, objtype: type = None) -> Any:
        if obj is None:
            return self
        # 快速路径：已初始化
        try:
            return obj.__dict__[self._attr_name]
        except KeyError:
            pass
        # 慢路径：加锁初始化
        with self._lock:
            # 双重检查
            try:
                return obj.__dict__[self._attr_name]
            except KeyError:
                value = self.factory(obj)
                obj.__dict__[self._attr_name] = value
                return value

    def reset(self, obj: Any) -> None:
        """清理缓存值，下次访问重新创建。"""
        with self._lock:
            old = obj.__dict__.pop(self._attr_name, None)
            if old is not None and self.cleanup:
                self.cleanup(old)
