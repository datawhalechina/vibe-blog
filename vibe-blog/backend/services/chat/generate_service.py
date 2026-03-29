"""
一键生成服务 — 编排 AgentDispatcher 完成端到端博客生成
复用 TaskManager SSE 推送进度，支持前端/NanoClaw 订阅。
"""
import logging
from threading import Thread
from typing import Optional

from services.chat.agent_dispatcher import AgentDispatcher
from services.chat.writing_session import WritingSession, WritingSessionManager
from services.task_service import TaskManager

logger = logging.getLogger(__name__)

# 进度阶段映射
STAGES = {
    'search': {'percent': 10, 'message': '正在调研素材...'},
    'outline': {'percent': 25, 'message': '正在生成大纲...'},
    'writing': {'percent': 40, 'message': '正在撰写章节...'},
    'review': {'percent': 70, 'message': '正在审核内容...'},
    'factcheck': {'percent': 80, 'message': '正在事实核查...'},
    'humanize': {'percent': 88, 'message': '正在优化文风...'},
    'assemble': {'percent': 95, 'message': '正在组装文档...'},
}


def _report(task_manager: TaskManager, task_id: str, stage: str, extra_msg: str = ''):
    """发送进度事件"""
    info = STAGES.get(stage, {'percent': 0, 'message': stage})
    msg = extra_msg or info['message']
    task_manager.send_event(task_id, 'progress', {
        'percent': info['percent'],
        'message': msg,
        'stage': stage,
    })


def run_chat_generate(
    session_id: str,
    session_mgr: WritingSessionManager,
    dispatcher: AgentDispatcher,
    task_manager: TaskManager,
    task_id: str,
    app=None,
):
    """在后台线程中执行一键生成全流程。

    流程: search → outline → write all sections → review → factcheck → humanize → assemble
    """
    def _run():
        ctx = app.app_context() if app else None
        if ctx:
            ctx.push()
        try:
            task_manager.set_running(task_id)
            session = session_mgr.get(session_id)
            if not session:
                task_manager.send_error(task_id, 'init', f'会话 {session_id} 不存在')
                return

            # 1. 调研
            _report(task_manager, task_id, 'search')
            search_result = dispatcher.search(session)
            search_results = search_result.get('search_results', [])
            session_mgr.update(session_id, search_results=search_results, status='researching')
            session = session_mgr.get(session_id)
            task_manager.send_result(task_id, 'search', 'search_complete', {
                'result_count': len(search_results),
            })

            # 2. 大纲
            _report(task_manager, task_id, 'outline')
            outline_result = dispatcher.generate_outline(session)
            outline = outline_result.get('outline')
            if not outline:
                task_manager.send_error(task_id, 'outline', '大纲生成失败')
                return
            sections_init = [
                {'id': s.get('id'), 'title': s.get('title'), 'content': ''}
                for s in outline.get('sections', [])
            ]
            session_mgr.update(session_id, outline=outline, sections=sections_init, status='outlining')
            session = session_mgr.get(session_id)
            task_manager.send_result(task_id, 'outline', 'outline_complete', {
                'outline': outline,
            })

            # 3. 逐章写作
            section_defs = outline.get('sections', [])
            total = len(section_defs)
            for idx, sec_def in enumerate(section_defs):
                sid = sec_def.get('id', f's{idx+1}')
                pct = 40 + int(30 * idx / max(total, 1))
                task_manager.send_event(task_id, 'progress', {
                    'percent': pct,
                    'message': f'正在撰写第 {idx+1}/{total} 章：{sec_def.get("title", "")}',
                    'stage': 'writing',
                })
                write_result = dispatcher.write_section(session, sid)
                if 'error' in write_result:
                    logger.warning('写作章节 %s 失败: %s', sid, write_result['error'])
                    continue
                # 更新 session sections
                section_data = write_result.get('section', {})
                sections = list(session.sections or [])
                updated = False
                for i, s in enumerate(sections):
                    if s.get('id') == sid:
                        sections[i] = section_data
                        updated = True
                        break
                if not updated:
                    sections.append(section_data)
                session_mgr.update(session_id, sections=sections, status='writing')
                session = session_mgr.get(session_id)

            # 4. 审核
            _report(task_manager, task_id, 'review')
            review_result = dispatcher.review(session)
            session_mgr.update(session_id, status='reviewing')
            session = session_mgr.get(session_id)
            task_manager.send_result(task_id, 'review', 'review_complete', review_result)

            # 5. 事实核查
            _report(task_manager, task_id, 'factcheck')
            factcheck_result = dispatcher.factcheck(session)
            task_manager.send_result(task_id, 'factcheck', 'factcheck_complete', factcheck_result)

            # 6. 去 AI 味
            _report(task_manager, task_id, 'humanize')
            dispatcher.humanize(session)
            session = session_mgr.get(session_id)

            # 7. 组装
            _report(task_manager, task_id, 'assemble')
            assemble_result = dispatcher.assemble(session)
            session_mgr.update(session_id, status='completed')

            task_manager.send_complete(task_id, {
                'session_id': session_id,
                'markdown': assemble_result.get('markdown'),
            })

        except Exception as e:
            logger.error('一键生成失败 [%s]: %s', task_id, e, exc_info=True)
            task_manager.send_error(task_id, 'unknown', str(e))
        finally:
            if ctx:
                ctx.pop()

    thread = Thread(target=_run, daemon=True)
    thread.start()
    return thread
