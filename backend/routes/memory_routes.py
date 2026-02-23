"""
记忆配置 API — Flask Blueprint

提供记忆系统配置查询和状态端点。
"""

from flask import Blueprint, jsonify

memory_bp = Blueprint("memory", __name__)


@memory_bp.route("/api/memory/config", methods=["GET"])
def get_memory_config_api():
    """返回当前记忆系统配置"""
    from services.blog_generator.memory.config import get_memory_config
    config = get_memory_config()
    return jsonify(config.model_dump())


@memory_bp.route("/api/memory/status", methods=["GET"])
def get_memory_status():
    """返回记忆系统配置 + 运行状态"""
    from services.blog_generator.memory.config import get_memory_config
    config = get_memory_config()
    return jsonify({"config": config.model_dump()})
