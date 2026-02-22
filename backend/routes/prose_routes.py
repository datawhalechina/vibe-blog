"""
Prose 编辑 API 路由
POST /api/prose/edit — 同步 AI 编辑（6 种模式）
"""
import logging

from flask import Blueprint, jsonify, request

from services.llm_service import get_llm_service
from services.blog_generator.agents.prose_editor import ProseEditorAgent, VALID_OPTIONS

logger = logging.getLogger(__name__)

prose_bp = Blueprint('prose', __name__)


@prose_bp.route('/api/prose/edit', methods=['POST'])
def edit_prose():
    """AI 行内编辑 — 6 种模式"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400

    content = data.get('content', '').strip()
    option = data.get('option', '').strip()
    command = data.get('command', '')
    memory_context = data.get('memory_context', '')

    if not content:
        return jsonify({'success': False, 'error': '请提供 content 参数'}), 400
    if not option:
        return jsonify({'success': False, 'error': '请提供 option 参数'}), 400
    if option not in VALID_OPTIONS:
        return jsonify({'success': False, 'error': f'无效的编辑模式: {option}，支持: {", ".join(sorted(VALID_OPTIONS))}'}), 400

    llm_service = get_llm_service()
    if not llm_service or not llm_service.is_available():
        return jsonify({'success': False, 'error': 'LLM 服务不可用'}), 503

    try:
        agent = ProseEditorAgent(llm_service)
        result = agent.edit(
            content=content,
            option=option,
            command=command,
            memory_context=memory_context,
        )
        if result is None:
            return jsonify({'success': False, 'error': 'LLM 返回为空'}), 500

        return jsonify({
            'success': True,
            'output': result,
            'option': option,
        })
    except Exception as e:
        logger.error(f"Prose 编辑失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
