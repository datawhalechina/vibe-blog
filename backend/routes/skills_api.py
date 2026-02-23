"""
Skills 管理 REST API

提供技能列表、详情、启用/禁用、ZIP 安装端点。
"""
import logging
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

skills_bp = Blueprint("skills", __name__, url_prefix="/api/skills")

# 延迟初始化 loader（避免循环导入）
_loader = None


def _get_loader():
    global _loader
    if _loader is None:
        from services.blog_generator.skills.loader import UnifiedSkillLoader
        _loader = UnifiedSkillLoader()
        _loader.load(enabled_only=False)
    return _loader


def _skill_to_dict(skill):
    return {
        "name": skill.name,
        "description": skill.description,
        "source": skill.source.value,
        "category": skill.category.value,
        "enabled": skill.enabled,
        "license": skill.license,
        "post_process": skill.post_process,
        "auto_run": skill.auto_run,
    }


@skills_bp.route("", methods=["GET"])
def list_skills():
    """列出所有技能"""
    loader = _get_loader()
    loader.load(enabled_only=False)
    skills = loader.list_skills()
    return jsonify({"skills": [_skill_to_dict(s) for s in skills]})


@skills_bp.route("/<skill_name>", methods=["GET"])
def get_skill(skill_name):
    """获取单个技能详情"""
    loader = _get_loader()
    skill = loader.get_skill(skill_name)
    if skill is None:
        return jsonify({"error": f"技能 '{skill_name}' 不存在"}), 404
    data = _skill_to_dict(skill)
    data["content"] = skill.content
    data["allowed_tools"] = skill.allowed_tools
    return jsonify(data)


@skills_bp.route("/<skill_name>", methods=["PUT"])
def update_skill(skill_name):
    """更新技能启用/禁用状态"""
    loader = _get_loader()
    body = request.get_json(silent=True) or {}
    enabled = body.get("enabled")
    if enabled is None:
        return jsonify({"error": "缺少 enabled 字段"}), 400
    ok = loader.set_enabled(skill_name, bool(enabled))
    if not ok:
        return jsonify({"error": f"技能 '{skill_name}' 不存在"}), 404
    return jsonify({"success": True, "name": skill_name, "enabled": bool(enabled)})


@skills_bp.route("/install", methods=["POST"])
def install_skill():
    """从 .skill ZIP 归档安装自定义技能"""
    if "file" not in request.files:
        return jsonify({"success": False, "message": "缺少 file 字段"}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.endswith(".skill"):
        return jsonify({"success": False, "message": "文件必须为 .skill 格式"}), 400

    with tempfile.NamedTemporaryFile(suffix=".skill", delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = Path(tmp.name)

    try:
        loader = _get_loader()
        result = loader.install_from_zip(tmp_path)
        status = 200 if result["success"] else 400
        return jsonify(result), status
    finally:
        tmp_path.unlink(missing_ok=True)
