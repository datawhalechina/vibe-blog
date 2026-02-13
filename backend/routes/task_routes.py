"""
任务管理路由
/api/generate, /api/tasks/<id>/stream, /api/tasks/<id>, /api/tasks/<id>/cancel
"""
import json
import time
import logging
from queue import Empty

from flask import Blueprint, Response, jsonify, request, stream_with_context, current_app

from services import (
    get_llm_service, get_image_service,
    get_task_manager, create_pipeline_service,
)

logger = logging.getLogger(__name__)

task_bp = Blueprint('task', __name__)


@task_bp.route('/api/generate', methods=['POST'])
def generate_storybook():
    """创建生成任务，返回 task_id 用于订阅 SSE"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400

        content = data.get('content', '')
        if not content:
            return jsonify({'success': False, 'error': '请提供 content 参数'}), 400

        title = data.get('title', '')
        target_audience = data.get('target_audience', '技术小白')
        style = data.get('style', '可爱卡通风')
        page_count = data.get('page_count', 8)
        generate_images = data.get('generate_images', False)
        aspect_ratio = data.get('aspect_ratio', '16:9')

        llm_service = get_llm_service()
        if not llm_service or not llm_service.is_available():
            return jsonify({'success': False, 'error': 'LLM 服务不可用'}), 500

        task_manager = get_task_manager()
        task_id = task_manager.create_task()

        image_service = get_image_service()
        pipeline_service = create_pipeline_service(
            llm_service=llm_service,
            image_service=image_service,
            task_manager=task_manager
        )

        pipeline_service.run_pipeline_async(
            task_id=task_id,
            content=content,
            title=title,
            target_audience=target_audience,
            style=style,
            page_count=page_count,
            generate_images=generate_images,
            aspect_ratio=aspect_ratio,
            app=current_app._get_current_object()
        )

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '任务已创建，请订阅 SSE 获取进度'
        }), 202

    except Exception as e:
        logger.error(f"创建生成任务失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@task_bp.route('/api/tasks/<task_id>/stream')
def stream_task_progress(task_id: str):
    """SSE 进度推送端点"""
    def generate():
        task_manager = get_task_manager()

        yield f"event: connected\ndata: {json.dumps({'task_id': task_id, 'status': 'connected'})}\n\n"

        queue = task_manager.get_queue(task_id)
        if not queue:
            yield f"event: error\ndata: {json.dumps({'message': '任务不存在', 'recoverable': False})}\n\n"
            return

        last_heartbeat = time.time()

        while True:
            try:
                try:
                    message = queue.get(timeout=1)
                except Empty:
                    message = None

                if message:
                    event_type = message.get('event', 'progress')
                    data = message.get('data', {})
                    event_id = message.get('id', '')
                    timestamp = message.get('timestamp')
                    if timestamp:
                        data['_ts'] = timestamp
                    lines = []
                    if event_id:
                        lines.append(f"id: {event_id}")
                    lines.append(f"event: {event_type}")
                    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
                    yield "".join(line + "\n" for line in lines) + "\n"

                    if event_type in ('complete', 'cancelled'):
                        break
                    if event_type == 'error' and not data.get('recoverable'):
                        break

                if time.time() - last_heartbeat > 30:
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': time.time()})}\n\n"
                    last_heartbeat = time.time()

            except GeneratorExit:
                logger.info(f"SSE 连接关闭: {task_id}")
                break
            except Exception as e:
                logger.error(f"SSE 错误: {e}")
                break

        task_manager.cleanup_task(task_id)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*'
        }
    )


@task_bp.route('/api/tasks/<task_id>')
def get_task_status(task_id: str):
    """获取任务状态"""
    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)

    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    return jsonify({
        'success': True,
        'task': {
            'task_id': task.task_id,
            'status': task.status,
            'current_stage': task.current_stage,
            'stage_progress': task.stage_progress,
            'overall_progress': task.overall_progress,
            'message': task.message,
            'error': task.error
        }
    })


@task_bp.route('/api/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id: str):
    """取消正在执行的任务"""
    task_manager = get_task_manager()

    if task_manager.cancel_task(task_id):
        return jsonify({
            'success': True,
            'message': '任务已取消',
            'task_id': task_id
        })
    else:
        task = task_manager.get_task(task_id)
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        return jsonify({
            'success': False,
            'error': f'无法取消任务，当前状态: {task.status}'
        }), 400
