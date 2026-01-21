import logging
import json as json_module
import time
from queue import Empty
from flask import Blueprint, jsonify, Response, stream_with_context

from services import get_task_manager

logger = logging.getLogger(__name__)

bp = Blueprint('tasks', __name__)

# SSE 进度推送端点
@bp.route('/api/tasks/<task_id>/stream')
def stream_task_progress(task_id: str):
    """SSE 进度推送端点"""
    
    def generate():
        task_manager = get_task_manager()
        
        # 发送连接成功事件
        yield f"event: connected\ndata: {json_module.dumps({'task_id': task_id, 'status': 'connected'})}\n\n"
        
        queue = task_manager.get_queue(task_id)
        if not queue:
            yield f"event: error\ndata: {json_module.dumps({'message': '任务不存在', 'recoverable': False})}\n\n"
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
                    yield f"event: {event_type}\ndata: {json_module.dumps(data, ensure_ascii=False)}\n\n"
                    
                    if event_type in ('complete', 'cancelled'):
                        break
                    if event_type == 'error' and not data.get('recoverable'):
                        break
                
                # 心跳保活
                if time.time() - last_heartbeat > 30:
                    yield f"event: heartbeat\ndata: {json_module.dumps({'timestamp': time.time()})}\n\n"
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

@bp.route('/api/tasks/<task_id>')
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

@bp.route('/api/tasks/<task_id>/cancel', methods=['POST'])
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
