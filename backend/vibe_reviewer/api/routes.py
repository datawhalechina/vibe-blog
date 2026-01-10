"""
vibe-reviewer API 路由定义

所有路由使用 /api/reviewer/ 前缀
"""
import os
import logging
import json
import time
import threading
from queue import Queue, Empty
from flask import Blueprint, request, jsonify, Response, stream_with_context

from ..reviewer_service import get_reviewer_service
from ..schemas import TutorialRequest

logger = logging.getLogger(__name__)

# 评估任务队列管理
_evaluation_queues = {}
_evaluation_lock = threading.Lock()

# 创建 Blueprint
reviewer_bp = Blueprint('reviewer', __name__, url_prefix='/api/reviewer')

logger.info("vibe-reviewer API 路由已注册")


@reviewer_bp.route('/config', methods=['GET'])
def get_config():
    """获取 vibe-reviewer 配置"""
    max_chapters = int(os.environ.get('REVIEWER_MAX_CHAPTERS', 5))
    return jsonify({
        'success': True,
        'config': {
            'max_chapters': max_chapters
        }
    })


def register_reviewer_routes(app):
    """
    注册 vibe-reviewer 路由到 Flask app
    
    Args:
        app: Flask 应用实例
    """
    app.register_blueprint(reviewer_bp)
    logger.info("vibe-reviewer API 路由已注册")


# ========== 教程管理 API ==========

@reviewer_bp.route('/tutorials', methods=['POST'])
def add_tutorial():
    """添加教程"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400
        
        git_url = data.get('git_url')
        if not git_url:
            return jsonify({'success': False, 'error': '请提供 git_url'}), 400
        
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        req = TutorialRequest(
            git_url=git_url,
            name=data.get('name'),
            branch=data.get('branch', 'main'),
            enable_search=data.get('enable_search', True),
            max_search_rounds=data.get('max_search_rounds', 2),
        )
        
        result = service.add_tutorial(req)
        
        return jsonify({
            'success': True,
            'tutorial': {
                'id': result.id,
                'name': result.name,
                'git_url': result.git_url,
                'status': result.status,
            }
        })
        
    except Exception as e:
        logger.error(f"添加教程失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@reviewer_bp.route('/tutorials', methods=['GET'])
def list_tutorials():
    """获取教程列表"""
    try:
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        tutorials = service.list_tutorials()
        
        return jsonify({
            'success': True,
            'tutorials': [
                {
                    'id': t.id,
                    'name': t.name,
                    'git_url': t.git_url,
                    'status': t.status,
                    'overall_score': t.overall_score,
                    'total_chapters': t.total_chapters,
                    'total_issues': t.total_issues,
                    'high_issues': t.high_issues,
                    'medium_issues': t.medium_issues,
                    'low_issues': t.low_issues,
                    'created_at': t.created_at,
                    'last_evaluated': t.last_evaluated,
                }
                for t in tutorials
            ]
        })
        
    except Exception as e:
        logger.error(f"获取教程列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@reviewer_bp.route('/tutorials/<int:tutorial_id>', methods=['GET'])
def get_tutorial(tutorial_id):
    """获取教程详情"""
    try:
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        tutorial = service.get_tutorial(tutorial_id)
        if not tutorial:
            return jsonify({'success': False, 'error': '教程不存在'}), 404
        
        return jsonify({
            'success': True,
            'tutorial': {
                'id': tutorial.id,
                'name': tutorial.name,
                'git_url': tutorial.git_url,
                'status': tutorial.status,
                'overall_score': tutorial.overall_score,
                'total_chapters': tutorial.total_chapters,
                'total_issues': tutorial.total_issues,
                'high_issues': tutorial.high_issues,
                'medium_issues': tutorial.medium_issues,
                'low_issues': tutorial.low_issues,
                'created_at': tutorial.created_at,
                'last_evaluated': tutorial.last_evaluated,
            }
        })
        
    except Exception as e:
        logger.error(f"获取教程详情失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@reviewer_bp.route('/tutorials/<int:tutorial_id>', methods=['DELETE'])
def delete_tutorial(tutorial_id):
    """删除教程"""
    try:
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        success = service.delete_tutorial(tutorial_id)
        if not success:
            return jsonify({'success': False, 'error': '教程不存在'}), 404
        
        return jsonify({'success': True, 'message': '教程已删除'})
        
    except Exception as e:
        logger.error(f"删除教程失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@reviewer_bp.route('/tutorials/<int:tutorial_id>/evaluate', methods=['POST'])
def evaluate_tutorial(tutorial_id):
    """触发教程评估 (同步执行)"""
    try:
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        # 获取参数
        data = request.get_json() or {}
        default_max = int(os.environ.get('REVIEWER_MAX_CHAPTERS', 5))
        max_chapters = data.get('max_chapters', default_max)
        
        # 同步执行评估
        result = service.evaluate_tutorial_sync(
            tutorial_id=tutorial_id,
            max_chapters=max_chapters,
        )
        
        return jsonify({
            'success': True,
            'result': result,
        })
        
    except Exception as e:
        logger.error(f"评估失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@reviewer_bp.route('/tutorials/<int:tutorial_id>/evaluate-stream', methods=['GET'])
def evaluate_tutorial_stream(tutorial_id):
    """触发教程评估 (SSE 流式进度推送)"""
    try:
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        # 获取参数 (从 URL 查询参数)
        default_max = int(os.environ.get('REVIEWER_MAX_CHAPTERS', 5))
        max_chapters = request.args.get('max_chapters', default_max, type=int)
        # 0 表示全部评估
        if max_chapters == 0:
            max_chapters = 1000  # 实际上不限制
        
        # 创建进度队列
        queue = Queue()
        task_id = f"eval_{tutorial_id}_{int(time.time())}"
        
        with _evaluation_lock:
            _evaluation_queues[task_id] = queue
        
        def on_progress(event):
            """进度回调"""
            queue.put(event)
        
        def run_evaluation():
            """在后台线程运行评估"""
            try:
                result = service.evaluate_tutorial_sync(
                    tutorial_id=tutorial_id,
                    on_progress=on_progress,
                    max_chapters=max_chapters,
                )
                queue.put({'type': 'complete', 'result': result})
            except Exception as e:
                logger.error(f"评估失败: {e}", exc_info=True)
                queue.put({'type': 'error', 'message': str(e)})
            finally:
                # 清理队列
                with _evaluation_lock:
                    if task_id in _evaluation_queues:
                        del _evaluation_queues[task_id]
        
        # 启动后台评估线程
        thread = threading.Thread(target=run_evaluation, daemon=True)
        thread.start()
        
        def generate():
            """SSE 生成器"""
            yield f"event: connected\ndata: {json.dumps({'task_id': task_id, 'tutorial_id': tutorial_id})}\n\n"
            
            last_heartbeat = time.time()
            
            while True:
                try:
                    try:
                        message = queue.get(timeout=1)
                    except Empty:
                        message = None
                    
                    if message:
                        event_type = message.get('type', 'progress')
                        yield f"event: {event_type}\ndata: {json.dumps(message, ensure_ascii=False)}\n\n"
                        
                        if event_type in ('complete', 'error'):
                            break
                    
                    # 心跳保活
                    if time.time() - last_heartbeat > 10:
                        yield f"event: heartbeat\ndata: {json.dumps({'timestamp': time.time()})}\n\n"
                        last_heartbeat = time.time()
                        
                except GeneratorExit:
                    logger.info(f"SSE 连接关闭: {task_id}")
                    break
                except Exception as e:
                    logger.error(f"SSE 错误: {e}")
                    break
        
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
        
    except Exception as e:
        logger.error(f"触发评估失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 章节管理 API ==========

@reviewer_bp.route('/tutorials/<int:tutorial_id>/chapters', methods=['GET'])
def list_chapters(tutorial_id):
    """获取教程的所有章节"""
    try:
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        chapters = service.get_chapters(tutorial_id)
        
        return jsonify({
            'success': True,
            'chapters': chapters,
        })
        
    except Exception as e:
        logger.error(f"获取章节列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@reviewer_bp.route('/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter(chapter_id):
    """获取章节详情"""
    try:
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        chapter = service.get_chapter(chapter_id)
        if not chapter:
            return jsonify({'success': False, 'error': '章节不存在'}), 404
        
        return jsonify({
            'success': True,
            'chapter': chapter,
        })
        
    except Exception as e:
        logger.error(f"获取章节详情失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 问题管理 API ==========

@reviewer_bp.route('/tutorials/<int:tutorial_id>/issues', methods=['GET'])
def list_tutorial_issues(tutorial_id):
    """获取教程的所有问题"""
    try:
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        severity = request.args.get('severity')
        issues = service.get_issues(tutorial_id=tutorial_id, severity=severity)
        
        return jsonify({
            'success': True,
            'issues': issues,
        })
        
    except Exception as e:
        logger.error(f"获取问题列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@reviewer_bp.route('/chapters/<int:chapter_id>/issues', methods=['GET'])
def list_chapter_issues(chapter_id):
    """获取章节的所有问题"""
    try:
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        # 获取章节信息
        chapter = service.get_chapter(chapter_id)
        if not chapter:
            return jsonify({'success': False, 'error': '章节不存在'}), 404
        
        # 获取问题列表
        issues = service.get_issues(chapter_id=chapter_id)
        
        return jsonify({
            'success': True,
            'chapter': chapter,
            'issues': issues,
        })
        
    except Exception as e:
        logger.error(f"获取问题列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@reviewer_bp.route('/issues/<int:issue_id>', methods=['PATCH'])
def update_issue(issue_id):
    """更新问题状态"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400
        
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        is_resolved = data.get('is_resolved')
        if is_resolved is not None:
            service.mark_issue_resolved(issue_id, is_resolved)
        
        return jsonify({'success': True, 'message': '问题状态已更新'})
        
    except Exception as e:
        logger.error(f"更新问题状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== 报告导出 ==========

@reviewer_bp.route('/tutorials/<int:tutorial_id>/export', methods=['GET'])
def export_report(tutorial_id):
    """导出评估报告为 Markdown"""
    try:
        service = get_reviewer_service()
        if not service:
            return jsonify({'success': False, 'error': 'ReviewerService 未初始化'}), 500
        
        # 获取教程信息
        tutorial = service.get_tutorial(tutorial_id)
        if not tutorial:
            return jsonify({'success': False, 'error': '教程不存在'}), 404
        
        # 获取章节列表
        chapters = service.get_chapters(tutorial_id)
        
        # 生成 Markdown 报告
        md_content = generate_markdown_report(tutorial, chapters, service)
        
        # 返回 Markdown 文件
        response = Response(
            md_content,
            mimetype='text/markdown',
            headers={
                'Content-Disposition': f'attachment; filename="{tutorial.name}_report.md"',
                'Content-Type': 'text/markdown; charset=utf-8'
            }
        )
        return response
        
    except Exception as e:
        logger.error(f"导出报告失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def generate_markdown_report(tutorial, chapters, service):
    """生成 Markdown 格式的评估报告"""
    lines = []
    
    # 标题 (tutorial 是 TutorialResponse 对象)
    lines.append(f"# 📊 教程评估报告: {tutorial.name}")
    lines.append("")
    lines.append(f"> 生成时间: {tutorial.last_evaluated or '未评估'}")
    lines.append(f"> Git 仓库: {tutorial.git_url}")
    lines.append("")
    
    # 总体评分
    lines.append("## 📈 总体评分")
    lines.append("")
    overall_score = tutorial.overall_score or 0
    score_emoji = "🟢" if overall_score >= 80 else "🟡" if overall_score >= 60 else "🔴"
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 综合评分 | {score_emoji} **{overall_score:.1f}** |")
    lines.append(f"| 评估章节 | {tutorial.total_chapters or 0} |")
    lines.append(f"| 发现问题 | {tutorial.total_issues or 0} |")
    lines.append(f"| 高优先级 | 🔴 {tutorial.high_issues or 0} |")
    lines.append(f"| 中优先级 | 🟡 {tutorial.medium_issues or 0} |")
    lines.append(f"| 低优先级 | 🟢 {tutorial.low_issues or 0} |")
    lines.append("")
    
    # 章节详情
    lines.append("## 📚 章节详情")
    lines.append("")
    
    for chapter in chapters:
        # chapter 是字典
        chapter_score = chapter.get('overall_score', 0)
        score_emoji = "🟢" if chapter_score >= 80 else "🟡" if chapter_score >= 60 else "🔴"
        
        lines.append(f"### {score_emoji} {chapter.get('title') or chapter.get('file_name')}")
        lines.append("")
        lines.append(f"- **文件**: `{chapter.get('file_path')}`")
        lines.append(f"- **评分**: {chapter_score}")
        lines.append(f"- **问题数**: {chapter.get('total_issues', 0)} (🔴{chapter.get('high_issues', 0)} 🟡{chapter.get('medium_issues', 0)} 🟢{chapter.get('low_issues', 0)})")
        lines.append("")
        
        # 获取该章节的问题
        issues = service.get_issues(chapter_id=chapter['id'])
        if issues:
            lines.append("#### 发现的问题")
            lines.append("")
            for issue in issues:
                severity_emoji = "🔴" if issue['severity'] == 'high' else "🟡" if issue['severity'] == 'medium' else "🟢"
                lines.append(f"##### {severity_emoji} [{issue['category']}/{issue['issue_type']}] {issue.get('location', '')}")
                lines.append("")
                lines.append(f"**问题描述**: {issue['description']}")
                lines.append("")
                if issue.get('suggestion'):
                    lines.append(f"**改进建议**: {issue['suggestion']}")
                    lines.append("")
                if issue.get('reference'):
                    lines.append(f"**参考资料**: {issue['reference']}")
                    lines.append("")
        lines.append("---")
        lines.append("")
    
    # 总结
    lines.append("## 📝 总结")
    lines.append("")
    total_issues = tutorial.total_issues or 0
    if total_issues == 0:
        lines.append("✅ 恭喜！本教程未发现明显问题。")
    else:
        lines.append(f"本次评估共发现 **{total_issues}** 个问题，其中：")
        lines.append(f"- 🔴 高优先级问题 {tutorial.high_issues or 0} 个，建议优先修复")
        lines.append(f"- 🟡 中优先级问题 {tutorial.medium_issues or 0} 个，建议尽快修复")
        lines.append(f"- 🟢 低优先级问题 {tutorial.low_issues or 0} 个，可选优化")
    lines.append("")
    lines.append("---")
    lines.append("*本报告由 vibe-reviewer 自动生成*")
    
    return "\n".join(lines)


# ========== 健康检查 ==========

@reviewer_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    service = get_reviewer_service()
    return jsonify({
        'status': 'ok',
        'service': 'vibe-reviewer',
        'initialized': service is not None,
    })
