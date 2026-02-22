"""MCP 服务器配置模型"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class McpServerConfig(BaseModel):
    """单个 MCP 服务器配置"""

    enabled: bool = Field(default=True, description="是否启用")
    type: str = Field(default="stdio", description="传输类型: stdio / sse / http")
    command: Optional[str] = Field(default=None, description="stdio 启动命令")
    args: List[str] = Field(default_factory=list, description="stdio 命令参数")
    env: Dict[str, str] = Field(default_factory=dict, description="环境变量")
    url: Optional[str] = Field(default=None, description="sse/http 服务器 URL")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP 请求头")
    description: str = Field(default="", description="服务器描述")
    model_config = ConfigDict(extra="allow")


class McpConfig(BaseModel):
    """MCP 配置聚合"""

    mcp_servers: Dict[str, McpServerConfig] = Field(
        default_factory=dict,
        alias="mcpServers",
    )
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @classmethod
    def from_file(cls, config_path: Optional[str] = None) -> "McpConfig":
        path = cls._resolve_path(config_path)
        if path is None:
            return cls(mcp_servers={})
        with open(path) as f:
            data = json.load(f)
        cls._resolve_env_vars(data)
        return cls.model_validate(data)

    @classmethod
    def _resolve_path(cls, config_path: Optional[str] = None) -> Optional[Path]:
        if config_path:
            p = Path(config_path)
            return p if p.exists() else None
        env_path = os.getenv("VIBE_BLOG_MCP_CONFIG")
        if env_path:
            p = Path(env_path)
            return p if p.exists() else None
        for candidate in [
            Path(os.getcwd()) / "mcp_config.json",
            Path(os.getcwd()).parent / "mcp_config.json",
        ]:
            if candidate.exists():
                return candidate
        return None

    @classmethod
    def _resolve_env_vars(cls, data: Any) -> Any:
        """递归解析 $ENV_VAR 引用"""
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str) and v.startswith("$"):
                    data[k] = os.getenv(v[1:], "")
                elif isinstance(v, (dict, list)):
                    cls._resolve_env_vars(v)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    cls._resolve_env_vars(item)
        return data

    def get_enabled_servers(self) -> Dict[str, McpServerConfig]:
        return {n: c for n, c in self.mcp_servers.items() if c.enabled}
