"""
队列 REST API — Flask Blueprint

接口：
- POST /api/queue/tasks   提交任务入队
- GET  /api/queue/tasks   获取队列快照
- GET  /api/queue/tasks/<id>  获取单个任务
- DELETE /api/queue/tasks/<id>  取消任务
- GET  /api/queue/history  获取执行历史
"""
import asyncio
import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

queue_bp = Blueprint('queue', __name__, url_prefix='/api/queue')

# 全局引用，由 Flask 启动时注入
_queue_manager = None


def init_queue_routes(queue_manager):
    global _queue_manager
    _queue_manager = queue_manager


def _run_async(coro):
    """在同步 Flask 上下文中运行异步协程"""
    return asyncio.run(coro)


@queue_bp.route('/tasks', methods=['POST'])
def submit_task():
    """提交任务入队"""
    if not _queue_manager:
        return jsonify({'error': '队列服务未初始化'}), 503

    data = request.get_json()
    if not data or not data.get('topic'):
        return jsonify({'error': '缺少 topic 参数'}), 400

    from services.task_queue.models import (
        BlogTask, BlogGenerationConfig, PublishConfig,
        TriggerConfig, TaskPriority,
    )

    generation = BlogGenerationConfig(
        topic=data['topic'],
        article_type=data.get('article_type', 'tutorial'),
        target_length=data.get('target_length', 'medium'),
        image_style=data.get('image_style'),
    )
    priority_val = data.get('priority', 5)
    priority = TaskPriority(priority_val) if priority_val in (0, 5, 10) \
        else TaskPriority.NORMAL

    task = BlogTask(
        name=data.get('name', f"博客: {data['topic'][:30]}"),
        description=data.get('description'),
        generation=generation,
        publish=PublishConfig(**data.get('publish', {})),
        priority=priority,
        tags=data.get('tags', []),
        user_id=data.get('user_id'),
    )

    task_id = _run_async(_queue_manager.enqueue(task))
    return jsonify({
        'task_id': task_id,
        'status': 'queued',
        'queue_position': task.queue_position,
    }), 201


@queue_bp.route('/tasks', methods=['GET'])
def get_queue_snapshot():
    """获取队列快照（Dashboard 用）"""
    if not _queue_manager:
        return jsonify({'error': '队列服务未初始化'}), 503
    snapshot = _run_async(_queue_manager.get_queue_snapshot())
    return jsonify(snapshot)


@queue_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取单个任务详情"""
    if not _queue_manager:
        return jsonify({'error': '队列服务未初始化'}), 503
    task = _run_async(_queue_manager.get_task(task_id))
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify(task.model_dump(mode='json'))


@queue_bp.route('/tasks/<task_id>', methods=['DELETE'])
def cancel_task(task_id):
    """取消任务"""
    if not _queue_manager:
        return jsonify({'error': '队列服务未初始化'}), 503
    result = _run_async(_queue_manager.cancel(task_id))
    if result:
        return jsonify({'status': 'cancelled', 'task_id': task_id})
    return jsonify({'error': '无法取消（任务不存在或已完成）'}), 400


@queue_bp.route('/history', methods=['GET'])
def get_history():
    """获取执行历史"""
    if not _queue_manager:
        return jsonify({'error': '队列服务未初始化'}), 503
    task_id = request.args.get('task_id')
    limit = int(request.args.get('limit', 50))
    history = _run_async(
        _queue_manager.db.get_execution_history(task_id, limit)
    )
    return jsonify([r.model_dump(mode='json') for r in history])
