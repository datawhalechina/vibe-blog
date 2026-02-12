"""
WorkflowEngine — 声明式工作流引擎

从 YAML 配置加载工作流定义，根据 StyleProfile 过滤可选 Agent，
返回解析后的工作流配置（active phases + agents）。

阶段 2 的核心：把工作流图结构从代码硬编码变为 YAML 声明式配置。
新增 Agent 只需编辑 YAML，无需改代码。

用法：
    engine = WorkflowEngine()
    config = engine.resolve("medium")
    config = engine.resolve("medium", style=StyleProfile.mini())
"""

import logging
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from .style_profile import StyleProfile

logger = logging.getLogger(__name__)

# 默认配置目录
_DEFAULT_CONFIGS_DIR = Path(__file__).parent / "workflow_configs"


@dataclass
class AgentMeta:
    """Agent 元数据（从 agent_registry.yaml 加载）"""
    name: str
    class_path: str
    agent_type: str  # "critical" | "enhancement"
    phase: str
    style_switch: str = ""  # 对应 StyleProfile 的 enable_* 字段名


@dataclass
class ResolvedWorkflow:
    """解析后的工作流配置"""
    name: str
    description: str
    default_style: Dict[str, Any]
    phases: Dict[str, List[str]]  # phase_name → [agent_name, ...]
    active_agents: List[str]  # 扁平化的活跃 agent 列表（按 phase 顺序）
    skipped_agents: List[str]  # 被 StyleProfile 过滤掉的 agent


class WorkflowEngine:
    """
    声明式工作流引擎 — 从 YAML 配置解析工作流

    职责：
    1. 加载 agent_registry.yaml（所有可用 Agent 的元数据）
    2. 加载 workflow YAML（每种预设的 phase → agent 列表）
    3. 根据 StyleProfile 过滤可选 Agent
    4. 返回 ResolvedWorkflow（可用于构建 LangGraph 或其他执行引擎）
    """

    def __init__(self, configs_dir: str = None):
        self.configs_dir = Path(configs_dir) if configs_dir else _DEFAULT_CONFIGS_DIR
        self._agent_registry: Dict[str, AgentMeta] = {}
        self._workflow_cache: Dict[str, dict] = {}
        self._load_agent_registry()

    def _load_agent_registry(self):
        """加载 agent_registry.yaml"""
        registry_path = self.configs_dir / "agent_registry.yaml"
        if not registry_path.exists():
            logger.warning(f"Agent registry not found: {registry_path}")
            return

        with open(registry_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        for name, meta in data.get('agents', {}).items():
            self._agent_registry[name] = AgentMeta(
                name=name,
                class_path=meta.get('class', ''),
                agent_type=meta.get('type', 'enhancement'),
                phase=meta.get('phase', ''),
                style_switch=meta.get('style_switch', ''),
            )

        logger.debug(f"Loaded {len(self._agent_registry)} agents from registry")

    def _load_workflow_yaml(self, name: str) -> dict:
        """加载并缓存工作流 YAML"""
        if name in self._workflow_cache:
            return self._workflow_cache[name]

        yaml_path = self.configs_dir / f"{name}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"工作流配置不存在: {yaml_path}")

        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self._workflow_cache[name] = config
        return config

    def list_workflows(self) -> Dict[str, str]:
        """列出所有可用的工作流（扫描 YAML 文件）"""
        result = {}
        for yaml_file in sorted(self.configs_dir.glob("*.yaml")):
            if yaml_file.name == "agent_registry.yaml":
                continue
            try:
                config = self._load_workflow_yaml(yaml_file.stem)
                result[config['name']] = config.get('description', '')
            except Exception as e:
                logger.warning(f"Failed to load workflow {yaml_file.name}: {e}")
        return result

    def get_agent_registry(self) -> Dict[str, AgentMeta]:
        """获取 Agent 注册表"""
        return dict(self._agent_registry)

    def resolve(
        self,
        name: str,
        style: Optional[StyleProfile] = None,
    ) -> ResolvedWorkflow:
        """
        解析工作流：加载 YAML + 根据 StyleProfile 过滤 Agent

        Args:
            name: 工作流名称（对应 YAML 文件名）
            style: 用户风格覆盖（不传则使用 YAML 中的 default_style）

        Returns:
            ResolvedWorkflow 包含活跃的 phases 和 agents
        """
        config = self._load_workflow_yaml(name)
        final_style = style or self._build_style_from_yaml(config)

        phases = config.get('phases', {})
        active_phases: Dict[str, List[str]] = {}
        active_agents: List[str] = []
        skipped_agents: List[str] = []

        for phase_name, agents in phases.items():
            phase_active = []
            for agent_name in agents:
                if self._is_agent_active(agent_name, final_style):
                    phase_active.append(agent_name)
                else:
                    skipped_agents.append(agent_name)

            if phase_active:
                active_phases[phase_name] = phase_active
                active_agents.extend(phase_active)

        return ResolvedWorkflow(
            name=config.get('name', name),
            description=config.get('description', ''),
            default_style=config.get('default_style', {}),
            phases=active_phases,
            active_agents=active_agents,
            skipped_agents=skipped_agents,
        )

    def _is_agent_active(self, agent_name: str, style: StyleProfile) -> bool:
        """判断 Agent 是否应该激活"""
        meta = self._agent_registry.get(agent_name)

        # 未注册的 agent 默认激活（向前兼容）
        if not meta:
            return True

        # critical agent 始终激活
        if meta.agent_type == "critical":
            return True

        # enhancement agent 根据 style_switch 判断
        if meta.style_switch:
            return getattr(style, meta.style_switch, True)

        # 无 style_switch 的 enhancement agent 默认激活
        return True

    def _build_style_from_yaml(self, config: dict) -> StyleProfile:
        """从 YAML 的 default_style 构建 StyleProfile"""
        style_dict = config.get('default_style', {})
        # 只传入 StyleProfile 支持的字段
        valid_fields = {f.name for f in StyleProfile.__dataclass_fields__.values()}
        filtered = {k: v for k, v in style_dict.items() if k in valid_fields}
        return StyleProfile(**filtered)
