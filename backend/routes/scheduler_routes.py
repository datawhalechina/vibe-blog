"""
定时任务 REST API — Flask Blueprint

接口：
- POST   /api/scheduler/tasks          创建定时任务
- GET    /api/scheduler/tasks          列出定时任务
- DELETE /api/scheduler/tasks/<id>     删除定时任务
- POST   /api/scheduler/tasks/<id>/pause   暂停
- POST   /api/scheduler/tasks/<id>/resume  恢复
- POST   /api/scheduler/parse-schedule     解析自然语言时间
"""
import logging

from flask import Blueprint, jsonify, request

from services.task_queue.cron_parser import parse_schedule

logger = logging.getLogger(__name__)

scheduler_bp = Blueprint(
    'scheduler', __name__, url_prefix='/api/scheduler'
)

_scheduler_service = None


def init_scheduler_routes(scheduler_service):
    global _scheduler_service
    _scheduler_service = scheduler_service


def _run_async(coro):
    import asyncio
    return asyncio.run(coro)


@scheduler_bp.route('/tasks', methods=['POST'])
def create_scheduled_task():
    if not _scheduler_service:
        return jsonify({'error': '调度服务未初始化'}), 503
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': '缺少 name 参数'}), 400
    if not data.get('trigger') or not data['trigger'].get('type'):
        return jsonify({'error': '缺少 trigger 配置'}), 400
    if not data.get('generation') or not data['generation'].get('topic'):
        return jsonify({'error': '缺少 generation.topic'}), 400

    task_id = _run_async(_scheduler_service.add_task(data))
    return jsonify({'task_id': task_id, 'status': 'created'}), 201


@scheduler_bp.route('/tasks', methods=['GET'])
def list_scheduled_tasks():
    if not _scheduler_service:
        return jsonify({'error': '调度服务未初始化'}), 503
    tasks = _run_async(_scheduler_service.list_tasks())
    return jsonify(tasks)


@scheduler_bp.route('/tasks/<task_id>', methods=['DELETE'])
def delete_scheduled_task(task_id):
    if not _scheduler_service:
        return jsonify({'error': '调度服务未初始化'}), 503
    _run_async(_scheduler_service.remove_task(task_id))
    return jsonify({'status': 'deleted', 'task_id': task_id})


@scheduler_bp.route('/tasks/<task_id>/pause', methods=['POST'])
def pause_task(task_id):
    if not _scheduler_service:
        return jsonify({'error': '调度服务未初始化'}), 503
    _run_async(_scheduler_service.pause_task(task_id))
    return jsonify({'status': 'paused', 'task_id': task_id})


@scheduler_bp.route('/tasks/<task_id>/resume', methods=['POST'])
def resume_task(task_id):
    if not _scheduler_service:
        return jsonify({'error': '调度服务未初始化'}), 503
    _run_async(_scheduler_service.resume_task(task_id))
    return jsonify({'status': 'resumed', 'task_id': task_id})


@scheduler_bp.route('/parse-schedule', methods=['POST'])
def parse_schedule_api():
    """解析自然语言时间"""
    data = request.get_json()
    if not data or not data.get('text'):
        return jsonify({'error': '缺少 text 参数'}), 400
    result = parse_schedule(data['text'])
    return jsonify(result)
