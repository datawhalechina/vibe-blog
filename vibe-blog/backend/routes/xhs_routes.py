"""
小红书生成路由
/api/xhs/...
"""
import os
import json
import time
import uuid
import asyncio
import logging
from queue import Empty

from flask import Blueprint, Response, jsonify, request, stream_with_context, current_app

from services import (
    get_llm_service, get_image_service,
    get_task_manager,
)
from services.database_service import get_db_service
from services.oss_service import get_oss_service
from services.video_service import get_video_service

logger = logging.getLogger(__name__)

xhs_bp = Blueprint('xhs', __name__)


@xhs_bp.route('/api/xhs/generate', methods=['POST'])
def xhs_generate():
    """生成小红书系列（异步版本，返回 task_id，通过 SSE 获取进度）"""
    try:
        data = request.get_json()
        topic = data.get('topic')

        if not topic:
            return jsonify({'success': False, 'error': '请提供主题'}), 400

        count = data.get('count', 4)
        style = data.get('style', 'hand_drawn')
        content = data.get('content')
        generate_video = data.get('generate_video', True)

        task_id = f"xhs_{uuid.uuid4().hex[:12]}"

        task_manager = get_task_manager()
        task_manager.create_task(task_id, 'xhs_generate')

        from services.xhs_service import XHSService

        xhs_service = XHSService(
            llm_client=get_llm_service(),
            image_service=get_image_service(),
            video_service=get_video_service(),
            oss_service=None
        )

        xhs_service.generate_async(
            task_id=task_id,
            topic=topic,
            count=count,
            style=style,
            content=content,
            generate_video=generate_video,
            task_manager=task_manager,
            app=current_app._get_current_object()
        )

        logger.info(f"小红书生成任务已创建: {task_id}")

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '任务已创建，请通过 SSE 接口获取进度'
        })

    except Exception as e:
        logger.error(f"小红书生成任务创建失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@xhs_bp.route('/api/xhs/stream/<task_id>')
def xhs_stream(task_id: str):
    """SSE 流式推送小红书生成进度"""
    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)

    if not task:
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    queue = task_manager.get_queue(task_id)

    def generate():
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
                    yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

                    if event_type in ('complete', 'cancelled'):
                        break
                    if event_type == 'error' and not data.get('recoverable'):
                        break

                if time.time() - last_heartbeat > 30:
                    yield f"event: heartbeat\ndata: {json.dumps({'timestamp': time.time()})}\n\n"
                    last_heartbeat = time.time()

            except GeneratorExit:
                logger.info(f"XHS SSE 连接关闭: {task_id}")
                break
            except Exception as e:
                logger.error(f"XHS SSE 错误: {e}")
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


@xhs_bp.route('/api/xhs/tasks/<task_id>/cancel', methods=['POST'])
def cancel_xhs_task(task_id: str):
    """取消小红书生成任务"""
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


@xhs_bp.route('/api/xhs/explanation-video', methods=['POST'])
def xhs_explanation_video():
    """从图片序列生成讲解视频"""
    try:
        data = request.get_json()
        images = data.get('images', [])
        scripts = data.get('scripts', [])

        if not images:
            return jsonify({'success': False, 'error': '请提供图片列表'}), 400

        if len(images) != len(scripts):
            return jsonify({'success': False, 'error': '图片数量与文案数量不匹配'}), 400

        style = data.get('style', 'ghibli_summer')
        target_duration = data.get('target_duration', 60.0)
        bgm_url = data.get('bgm_url')
        video_model = data.get('video_model', 'veo3')

        from services.xhs_service import XHSService
        xhs_service = XHSService(
            llm_client=get_llm_service(),
            image_service=get_image_service(),
            video_service=get_video_service(),
            oss_service=get_oss_service()
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            video_url = loop.run_until_complete(xhs_service.generate_explanation_video(
                images=images,
                scripts=scripts,
                style=style,
                target_duration=target_duration,
                bgm_url=bgm_url,
                video_model=video_model
            ))
        finally:
            loop.close()

        if video_url:
            return jsonify({
                'success': True,
                'video_url': video_url,
                'video_model': video_model,
                'message': '讲解视频生成成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '视频生成失败'
            }), 500

    except Exception as e:
        logger.error(f"讲解视频生成失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@xhs_bp.route('/api/xhs/outline', methods=['POST'])
def xhs_outline():
    """仅生成小红书大纲（不生成图片）"""
    try:
        data = request.get_json()
        topic = data.get('topic')

        if not topic:
            return jsonify({'success': False, 'error': '请提供主题'}), 400

        count = data.get('count', 4)
        content = data.get('content')

        from services.xhs_service import XHSService

        xhs_service = XHSService(
            llm_client=get_llm_service(),
            image_service=None,
            video_service=None,
            oss_service=None
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            outline, pages, article = loop.run_until_complete(xhs_service._generate_outline(
                topic=topic,
                count=count,
                content=content
            ))
        finally:
            loop.close()

        return jsonify({
            'success': True,
            'data': {
                'outline': outline,
                'article': article,
                'pages': [
                    {
                        'index': p.index,
                        'page_type': p.page_type,
                        'content': p.content
                    } for p in pages
                ]
            }
        })

    except Exception as e:
        logger.error(f"小红书大纲生成失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@xhs_bp.route('/api/xhs/publish', methods=['POST'])
def xhs_publish():
    """发布小红书笔记"""
    try:
        data = request.get_json()
        cookies = data.get('cookies', [])
        title = data.get('title', '')
        content = data.get('content', '')
        tags = data.get('tags', [])
        images = data.get('images', [])

        if not cookies:
            return jsonify({'success': False, 'error': '请提供小红书登录 Cookie'}), 400

        if not images:
            return jsonify({'success': False, 'error': '请提供至少一张图片'}), 400

        import tempfile
        import requests as req

        temp_dir = tempfile.mkdtemp()
        local_images = []

        for i, img_url in enumerate(images):
            try:
                if img_url.startswith('http'):
                    resp = req.get(img_url, timeout=30)
                    if resp.status_code == 200:
                        ext = '.jpg' if 'jpeg' in resp.headers.get('content-type', '') or 'jpg' in img_url else '.png'
                        local_path = os.path.join(temp_dir, f'image_{i}{ext}')
                        with open(local_path, 'wb') as f:
                            f.write(resp.content)
                        local_images.append(local_path)
                        logger.info(f"下载图片成功: {img_url} -> {local_path}")
                elif os.path.exists(img_url):
                    local_images.append(img_url)
            except Exception as e:
                logger.warning(f"下载图片失败: {img_url}, {e}")

        if not local_images:
            return jsonify({'success': False, 'error': '没有可用的图片'}), 400

        from services.publishers.publisher import Publisher

        publisher = Publisher()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(publisher.publish(
                platform_id='xiaohongshu',
                cookies=cookies,
                title=title,
                content=content,
                tags=tags,
                images=local_images,
                headless=False
            ))
        finally:
            loop.close()
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"小红书发布失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
