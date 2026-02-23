"""
播客生成 API 路由
POST /api/podcast/generate — 启动播客生成任务
GET  /api/podcast/transcript/<task_id> — 获取文字稿
GET  /api/podcast/download/<task_id> — 下载 MP3
"""
import logging
import os
import threading

from flask import Blueprint, jsonify, request, send_file

from services.podcast_service import get_podcast_service
from services.task_service import get_task_manager

logger = logging.getLogger(__name__)

podcast_bp = Blueprint('podcast', __name__)

# 存储任务结果
_task_results = {}


@podcast_bp.route('/api/podcast/generate', methods=['POST'])
def generate_podcast():
    """启动播客生成任务"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400

    content = data.get('content', '')
    if not content:
        return jsonify({'success': False, 'error': '请提供 content 参数'}), 400

    podcast_service = get_podcast_service()
    if not podcast_service or not podcast_service.is_available():
        return jsonify({'success': False, 'error': '播客服务不可用'}), 503

    title = data.get('title', '')
    locale = data.get('locale', 'zh')

    # 创建异步任务
    task_manager = get_task_manager()
    task_id = task_manager.create_task(task_type='podcast')
    task_manager.set_running(task_id)

    def _run():
        try:
            result = podcast_service.generate_podcast(
                task_id=task_id,
                content=content,
                title=title,
                locale=locale,
                task_manager=task_manager,
            )
            _task_results[task_id] = result
            if result.get('success'):
                task_manager.send_complete(task_id, result)
            else:
                task_manager.send_error(task_id, 'podcast', result.get('error', '未知错误'))
        except Exception as e:
            logger.error(f"播客任务失败: {e}", exc_info=True)
            _task_results[task_id] = {'success': False, 'error': str(e)}
            task_manager.send_error(task_id, 'podcast', str(e))

    threading.Thread(target=_run, daemon=True).start()

    return jsonify({'success': True, 'task_id': task_id})


@podcast_bp.route('/api/podcast/transcript/<task_id>', methods=['GET'])
def get_transcript(task_id):
    """获取播客文字稿"""
    result = _task_results.get(task_id)
    if not result:
        return jsonify({'success': False, 'error': '任务不存在或未完成'}), 404

    transcript = result.get('transcript', '')
    return jsonify({'success': True, 'transcript': transcript, 'script': result.get('script')})


@podcast_bp.route('/api/podcast/download/<task_id>', methods=['GET'])
def download_podcast(task_id):
    """下载播客 MP3"""
    result = _task_results.get(task_id)
    if not result:
        return jsonify({'success': False, 'error': '任务不存在或未完成'}), 404

    audio_path = result.get('audio_path')
    if not audio_path or not os.path.exists(audio_path):
        return jsonify({'success': False, 'error': '音频文件不存在'}), 404

    return send_file(audio_path, mimetype='audio/mpeg', as_attachment=True,
                     download_name=f'podcast_{task_id}.mp3')
