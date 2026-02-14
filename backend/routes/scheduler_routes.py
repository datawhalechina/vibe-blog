"""
定时任务 REST API — Flask Blueprint

接口：
- POST   /api/scheduler/tasks              创建定时任务
- GET    /api/scheduler/tasks              列出定时任务
- DELETE /api/scheduler/tasks/<id>         删除定时任务
- POST   /api/scheduler/tasks/<id>/pause   暂停
- POST   /api/scheduler/tasks/<id>/resume  恢复
- POST   /api/scheduler/tasks/<id>/retry   重试（重置错误计数）
- POST   /api/scheduler/tasks/<id>/run     手动触发
- GET    /api/scheduler/status             调度器状态
- POST   /api/scheduler/parse-schedule     解析自然语言时间
"""
import logging

from flask import Blueprint, jsonify, request

from services.task_queue.cron_parser import parse_schedule

logger = logging.getLogger(__name__)

scheduler_bp = Blueprint(
    'scheduler', __name__, url_prefix='/api/scheduler'
)

_scheduler = None


def init_scheduler_routes(scheduler):
    global _scheduler
    _scheduler = scheduler


def _run_async(coro):
    import asyncio
    return asyncio.run(coro)


@scheduler_bp.route('/tasks', methods=['POST'])
def create_scheduled_task():
    if not _scheduler:
        return jsonify({'error': '调度服务未初始化'}), 503
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': '缺少 name 参数'}), 400
    if not data.get('trigger') or not data['trigger'].get('type'):
        return jsonify({'error': '缺少 trigger 配置'}), 400
    if not data.get('generation') or not data['generation'].get('topic'):
        return jsonify({'error': '缺少 generation.topic'}), 400

    job = _run_async(_scheduler.add(data))
    return jsonify({
        'task_id': job.id,
        'status': 'created',
        'next_run_at': job.state.next_run_at.isoformat()
            if job.state.next_run_at else None,
    }), 201


@scheduler_bp.route('/tasks', methods=['GET'])
def list_scheduled_tasks():
    if not _scheduler:
        return jsonify({'error': '调度服务未初始化'}), 503
    include_disabled = request.args.get('include_disabled', 'true').lower() == 'true'
    jobs = _run_async(_scheduler.list_jobs(include_disabled=include_disabled))
    return jsonify([
        {
            'id': j.id,
            'name': j.name,
            'description': j.description,
            'enabled': j.enabled,
            'schedule': j.schedule.model_dump(),
            'next_run_at': j.state.next_run_at.isoformat()
                if j.state.next_run_at else None,
            'last_run_at': j.state.last_run_at.isoformat()
                if j.state.last_run_at else None,
            'last_status': j.state.last_status.value
                if j.state.last_status else None,
            'last_error': j.state.last_error,
            'consecutive_errors': j.state.consecutive_errors,
            'generation': j.generation.model_dump(),
            'tags': j.tags,
        }
        for j in jobs
    ])


@scheduler_bp.route('/tasks/<task_id>', methods=['DELETE'])
def delete_scheduled_task(task_id):
    if not _scheduler:
        return jsonify({'error': '调度服务未初始化'}), 503
    deleted = _run_async(_scheduler.remove(task_id))
    if deleted:
        return jsonify({'status': 'deleted', 'task_id': task_id})
    return jsonify({'error': '任务不存在'}), 404


@scheduler_bp.route('/tasks/<task_id>/pause', methods=['POST'])
def pause_task(task_id):
    if not _scheduler:
        return jsonify({'error': '调度服务未初始化'}), 503
    try:
        _run_async(_scheduler.pause(task_id))
        return jsonify({'status': 'paused', 'task_id': task_id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@scheduler_bp.route('/tasks/<task_id>/resume', methods=['POST'])
def resume_task(task_id):
    if not _scheduler:
        return jsonify({'error': '调度服务未初始化'}), 503
    try:
        _run_async(_scheduler.resume(task_id))
        return jsonify({'status': 'resumed', 'task_id': task_id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@scheduler_bp.route('/tasks/<task_id>/retry', methods=['POST'])
def retry_task(task_id):
    if not _scheduler:
        return jsonify({'error': '调度服务未初始化'}), 503
    try:
        _run_async(_scheduler.retry(task_id))
        return jsonify({'status': 'retrying', 'task_id': task_id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@scheduler_bp.route('/tasks/<task_id>/run', methods=['POST'])
def run_task(task_id):
    if not _scheduler:
        return jsonify({'error': '调度服务未初始化'}), 503
    mode = request.args.get('mode', 'force')
    result = _run_async(_scheduler.run(task_id, mode=mode))
    if result.get('ok'):
        return jsonify({'status': 'executed', 'task_id': task_id})
    return jsonify({'error': result.get('error', 'unknown')}), 400


@scheduler_bp.route('/status', methods=['GET'])
def scheduler_status():
    if not _scheduler:
        return jsonify({'error': '调度服务未初始化'}), 503
    status = _run_async(_scheduler.status())
    return jsonify(status)


@scheduler_bp.route('/parse-schedule', methods=['POST'])
def parse_schedule_api():
    """解析自然语言时间"""
    data = request.get_json()
    if not data or not data.get('text'):
        return jsonify({'error': '缺少 text 参数'}), 400
    result = parse_schedule(data['text'])
    return jsonify(result)
