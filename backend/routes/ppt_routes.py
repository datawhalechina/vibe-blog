"""
PPT 演示文稿生成 API 路由
POST /api/ppt/generate — 启动 PPT 生成任务
GET  /api/ppt/styles — 获取可用风格列表
GET  /api/ppt/download/<task_id> — 下载 PPTX
"""
import logging
import os
import threading

from flask import Blueprint, jsonify, request, send_file

from services.ppt_service import get_ppt_service, SlideStyle
from services.task_service import get_task_manager

logger = logging.getLogger(__name__)

ppt_bp = Blueprint('ppt', __name__)

_task_results = {}


@ppt_bp.route('/api/ppt/styles', methods=['GET'])
def get_styles():
    """获取可用 PPT 风格列表"""
    styles = [{"value": s.value, "label": s.value} for s in SlideStyle]
    return jsonify({'success': True, 'styles': styles})


@ppt_bp.route('/api/ppt/generate', methods=['POST'])
def generate_ppt():
    """启动 PPT 生成任务"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400

    sections = data.get('sections', [])
    title = data.get('title', '')
    if not sections and not data.get('content'):
        return jsonify({'success': False, 'error': '请提供 sections 或 content'}), 400

    ppt_service = get_ppt_service()
    if not ppt_service:
        return jsonify({'success': False, 'error': 'PPT 服务不可用'}), 503

    style = data.get('style', 'keynote')
    aspect_ratio = data.get('aspect_ratio', '16:9')

    task_manager = get_task_manager()
    task_id = task_manager.create_task(task_type='ppt')
    task_manager.set_running(task_id)

    def _run():
        try:
            result = ppt_service.generate(
                task_id=task_id,
                title=title,
                sections=sections,
                style=style,
                aspect_ratio=aspect_ratio,
                task_manager=task_manager,
            )
            _task_results[task_id] = result
            if result.get('success'):
                task_manager.send_complete(task_id, result)
            else:
                task_manager.send_error(task_id, 'ppt', result.get('error', '未知错误'))
        except Exception as e:
            logger.error(f"PPT 任务失败: {e}", exc_info=True)
            _task_results[task_id] = {'success': False, 'error': str(e)}
            task_manager.send_error(task_id, 'ppt', str(e))

    threading.Thread(target=_run, daemon=True).start()

    return jsonify({'success': True, 'task_id': task_id})


@ppt_bp.route('/api/ppt/download/<task_id>', methods=['GET'])
def download_ppt(task_id):
    """下载 PPTX 文件"""
    result = _task_results.get(task_id)
    if not result:
        return jsonify({'success': False, 'error': '任务不存在或未完成'}), 404

    pptx_path = result.get('pptx_path')
    if not pptx_path or not os.path.exists(pptx_path):
        return jsonify({'success': False, 'error': 'PPTX 文件不存在'}), 404

    return send_file(
        pptx_path,
        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
        as_attachment=True,
        download_name=f'presentation_{task_id}.pptx',
    )
