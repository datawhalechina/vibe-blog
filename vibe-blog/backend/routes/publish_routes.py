"""
多平台发布路由
/api/publish/..., /api/history/<id>/to-xhs, /api/publish/sync
"""
import asyncio
import json
import uuid
import logging

from flask import Blueprint, Response, jsonify, request

from services import get_llm_service, get_image_service
from services.database_service import get_db_service
from services.video_service import get_video_service
from services.publishers import Publisher

logger = logging.getLogger(__name__)

publish_bp = Blueprint('publish', __name__)


@publish_bp.route('/api/publish/platforms', methods=['GET'])
def get_publish_platforms():
    """获取支持的发布平台列表"""
    try:
        publisher = Publisher()
        platforms = publisher.get_supported_platforms()
        return jsonify({
            'success': True,
            'platforms': platforms
        })
    except Exception as e:
        logger.error(f"获取发布平台列表失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@publish_bp.route('/api/publish/stream', methods=['POST'])
def publish_article_stream():
    """SSE 流式发布文章到指定平台"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400

    platform = data.get('platform')
    cookies = data.get('cookies', [])
    title = data.get('title', '')
    content = data.get('content', '')

    if not platform:
        return jsonify({'success': False, 'error': '请指定发布平台'}), 400
    if not cookies:
        return jsonify({'success': False, 'error': '请提供登录 Cookie'}), 400
    if not content:
        return jsonify({'success': False, 'error': '请提供文章内容'}), 400

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'progress', 'step': '初始化', 'message': '正在启动浏览器...'})}\n\n"

            publisher = Publisher()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                yield f"data: {json.dumps({'type': 'progress', 'step': '导航', 'message': '正在打开编辑器页面...'})}\n\n"

                result = loop.run_until_complete(publisher.publish(
                    platform_id=platform,
                    cookies=cookies,
                    title=title,
                    content=content,
                    tags=data.get('tags'),
                    category=data.get('category'),
                    article_type=data.get('article_type', 'original'),
                    pub_type=data.get('pub_type', 'public'),
                    headless=data.get('headless', True)
                ))
            finally:
                loop.close()

            yield f"data: {json.dumps({'type': 'result', **result})}\n\n"

        except Exception as e:
            logger.error(f"发布文章失败: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@publish_bp.route('/api/publish', methods=['POST'])
def publish_article():
    """发布文章到指定平台（非流式）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400

        platform = data.get('platform')
        cookies = data.get('cookies', [])
        title = data.get('title', '')
        content = data.get('content', '')

        if not platform:
            return jsonify({'success': False, 'error': '请指定发布平台'}), 400
        if not cookies:
            return jsonify({'success': False, 'error': '请提供登录 Cookie'}), 400
        if not content:
            return jsonify({'success': False, 'error': '请提供文章内容'}), 400

        publisher = Publisher()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(publisher.publish(
                platform_id=platform,
                cookies=cookies,
                title=title,
                content=content,
                tags=data.get('tags'),
                category=data.get('category'),
                article_type=data.get('article_type', 'original'),
                pub_type=data.get('pub_type', 'public'),
                headless=data.get('headless', False)
            ))
        finally:
            loop.close()

        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"发布文章失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@publish_bp.route('/api/publish/blog/<blog_id>', methods=['POST'])
def publish_blog_to_platform(blog_id: str):
    """发布已生成的博客到指定平台"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400

        platform = data.get('platform')
        cookies = data.get('cookies', [])

        if not platform:
            return jsonify({'success': False, 'error': '请指定发布平台'}), 400
        if not cookies:
            return jsonify({'success': False, 'error': '请提供登录 Cookie'}), 400

        db_service = get_db_service()
        blog = db_service.get_history_by_id(blog_id)

        if not blog:
            return jsonify({'success': False, 'error': '博客不存在'}), 404

        title = blog.get('title', '')
        content = blog.get('markdown', '') or blog.get('content', '')

        if not content:
            return jsonify({'success': False, 'error': '博客内容为空'}), 400

        publisher = Publisher()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(publisher.publish(
                platform_id=platform,
                cookies=cookies,
                title=title,
                content=content,
                tags=data.get('tags'),
                category=data.get('category'),
                article_type=data.get('article_type', 'original'),
                pub_type=data.get('pub_type', 'public'),
                headless=True
            ))
        finally:
            loop.close()

        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"发布博客失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@publish_bp.route('/api/history/<history_id>/to-xhs', methods=['POST'])
def convert_blog_to_xhs(history_id):
    """将博客转换为小红书系列"""
    try:
        data = request.get_json() or {}
        style = data.get('style', 'hand_drawn')
        count = data.get('count', 4)
        generate_video = data.get('generate_video', True)

        db_service = get_db_service()
        blog_record = db_service.get_history(history_id)

        if not blog_record:
            return jsonify({'success': False, 'error': '博客记录不存在'}), 404

        if blog_record.get('content_type') == 'xhs':
            return jsonify({'success': False, 'error': '该记录已经是小红书类型'}), 400

        from services.xhs_service import get_xhs_service
        xhs_service = get_xhs_service()

        if not xhs_service:
            return jsonify({'success': False, 'error': '小红书服务未初始化'}), 503

        topic = blog_record.get('topic', '')
        content = blog_record.get('markdown_content', '')
        outline = blog_record.get('outline', '')

        reference_content = outline if outline else content[:2000]

        logger.info(f"开始将博客转换为小红书: {history_id} -> {topic}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(xhs_service.generate_series(
                topic=topic,
                count=count,
                style=style,
                content=reference_content,
                generate_video=generate_video
            ))
        finally:
            loop.close()

        xhs_id = f"xhs_{uuid.uuid4().hex[:12]}"

        db_service.save_xhs_record(
            history_id=xhs_id,
            topic=topic,
            style=style,
            layout_type='auto',
            image_urls=result.image_urls,
            copy_text=result.copywriting,
            hashtags=result.tags,
            cover_image=result.image_urls[0] if result.image_urls else None,
            cover_video=result.video_url,
            source_id=history_id
        )

        logger.info(f"博客转小红书完成: {history_id} -> {xhs_id}")

        return jsonify({
            'success': True,
            'data': {
                'xhs_id': xhs_id,
                'source_id': history_id,
                'image_urls': result.image_urls,
                'video_url': result.video_url,
                'titles': result.titles,
                'copywriting': result.copywriting,
                'tags': result.tags
            }
        })

    except Exception as e:
        logger.error(f"博客转小红书失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@publish_bp.route('/api/publish/sync', methods=['POST'])
def sync_publish():
    """同步发布到多个平台"""
    try:
        data = request.get_json()
        record_id = data.get('record_id')
        blog_platforms = data.get('blog_platforms', [])
        xhs_enabled = data.get('xhs_enabled', False)
        xhs_options = data.get('xhs_options', {})
        cookies = data.get('cookies', {})

        if not record_id:
            return jsonify({'success': False, 'error': '请提供记录ID'}), 400

        db_service = get_db_service()
        record = db_service.get_history(record_id)

        if not record:
            return jsonify({'success': False, 'error': '记录不存在'}), 404

        results = {
            'blog': {},
            'xhs': None
        }

        from services.publishers.publisher import Publisher
        publisher = Publisher()

        for platform in blog_platforms:
            platform_cookies = cookies.get(platform, [])
            if not platform_cookies:
                results['blog'][platform] = {'success': False, 'error': '未提供Cookie'}
                continue

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(publisher.publish(
                        platform_id=platform,
                        cookies=platform_cookies,
                        title=record.get('topic', ''),
                        content=record.get('markdown_content', ''),
                        headless=True
                    ))
                    results['blog'][platform] = result

                    if result.get('success'):
                        from datetime import datetime
                        db_service.update_publish_platforms(record_id, platform, {
                            'status': 'published',
                            'url': result.get('url', ''),
                            'published_at': datetime.now().isoformat()
                        })
                finally:
                    loop.close()
            except Exception as e:
                results['blog'][platform] = {'success': False, 'error': str(e)}

        if xhs_enabled:
            xhs_cookies = cookies.get('xiaohongshu', [])

            from services.xhs_service import get_xhs_service
            xhs_service = get_xhs_service()

            if xhs_service:
                try:
                    style = xhs_options.get('style', 'hand_drawn')
                    count = xhs_options.get('count', 4)
                    generate_video = xhs_options.get('generate_video', True)

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        xhs_result = loop.run_until_complete(xhs_service.generate_series(
                            topic=record.get('topic', ''),
                            count=count,
                            style=style,
                            content=record.get('outline', '') or record.get('markdown_content', '')[:2000],
                            generate_video=generate_video
                        ))
                    finally:
                        loop.close()

                    xhs_id = f"xhs_{uuid.uuid4().hex[:12]}"
                    db_service.save_xhs_record(
                        history_id=xhs_id,
                        topic=record.get('topic', ''),
                        style=style,
                        image_urls=xhs_result.image_urls,
                        copy_text=xhs_result.copywriting,
                        hashtags=xhs_result.tags,
                        cover_image=xhs_result.image_urls[0] if xhs_result.image_urls else None,
                        cover_video=xhs_result.video_url,
                        source_id=record_id
                    )

                    results['xhs'] = {
                        'success': True,
                        'xhs_id': xhs_id,
                        'image_urls': xhs_result.image_urls,
                        'video_url': xhs_result.video_url,
                        'titles': xhs_result.titles,
                        'copywriting': xhs_result.copywriting,
                        'tags': xhs_result.tags
                    }

                    if xhs_cookies and xhs_result.image_urls:
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                publish_result = loop.run_until_complete(publisher.publish(
                                    platform_id='xiaohongshu',
                                    cookies=xhs_cookies,
                                    title=xhs_result.titles[0] if xhs_result.titles else record.get('topic', ''),
                                    content=xhs_result.copywriting,
                                    tags=xhs_result.tags,
                                    images=xhs_result.image_urls,
                                    headless=True
                                ))

                                if publish_result.get('success'):
                                    results['xhs']['publish_url'] = publish_result.get('url', '')
                                    db_service.update_xhs_publish_url(xhs_id, publish_result.get('url', ''))
                            finally:
                                loop.close()
                        except Exception as e:
                            results['xhs']['publish_error'] = str(e)

                except Exception as e:
                    results['xhs'] = {'success': False, 'error': str(e)}
            else:
                results['xhs'] = {'success': False, 'error': '小红书服务未初始化'}

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        logger.error(f"同步发布失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
