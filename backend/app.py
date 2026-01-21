"""
vibe-blog 后端应用入口
技术科普绘本生成器
"""
import os
import logging
import re
import io
import json
import zipfile
import requests
from contextvars import ContextVar
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse, quote

# 加载 .env 文件
load_dotenv()

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS

from config import get_config
from services import (
    init_llm_service, get_llm_service, create_transform_service,
    init_image_service, get_image_service, AspectRatio, ImageSize, STORYBOOK_STYLE_PREFIX,
    get_task_manager, create_pipeline_service,
    init_blog_service, get_blog_service,
    init_search_service, get_search_service
)
from services.database_service import get_db_service, init_db_service
from services.file_parser_service import get_file_parser, init_file_parser
from services.knowledge_service import get_knowledge_service, init_knowledge_service
from services.image_styles import get_style_manager
from services.oss_service import get_oss_service, init_oss_service
from services.video_service import get_video_service, init_video_service

# 创建任务 ID 上下文变量
task_id_context: ContextVar[str] = ContextVar('task_id', default='')

# 自定义日志格式化器，添加任务 ID
class TaskIdFilter(logging.Filter):
    def filter(self, record):
        task_id = task_id_context.get()
        if task_id:
            record.task_id = f"[{task_id}]"
        else:
            record.task_id = ""
        return True

# 配置日志
log_format = logging.Formatter('%(asctime)s %(task_id)s - %(name)s - %(levelname)s - %(message)s')

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 添加任务 ID 过滤器
task_id_filter = TaskIdFilter()
root_logger.addFilter(task_id_filter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_format)
console_handler.addFilter(task_id_filter)
root_logger.addHandler(console_handler)

# 尝试配置文件日志，如果失败则跳过（Vercel 环境是只读的）
try:
    LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(LOG_DIR, exist_ok=True)
    LOG_FILE = os.path.join(LOG_DIR, 'app.log')
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
except (OSError, IOError):
    # Vercel 环境是只读的，无法创建日志文件，仅使用控制台日志
    pass

logger = logging.getLogger(__name__)


def create_app(config_class=None):
    """创建 Flask 应用"""
    app = Flask(__name__)
    
    # 加载配置
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    
    # 设置日志级别
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    logging.getLogger().setLevel(log_level)
    
    # CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    
    # 确保目录存在（Vercel 环境可能是只读的，所以使用 try-except）
    try:
        os.makedirs(app.config.get('OUTPUT_FOLDER', 'outputs'), exist_ok=True)
        os.makedirs(os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'images'), exist_ok=True)
    except (OSError, IOError):
        # Vercel 环境是只读的，无法创建目录，继续运行
        pass
    
    # 初始化 LLM 服务
    init_llm_service(app.config)
    
    # 初始化图片生成服务（图片保存到 outputs/images/）
    app.config['IMAGE_OUTPUT_FOLDER'] = os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'images')
    init_image_service(app.config)
    
    # 初始化 OSS 服务（用于上传图片获取公网 URL）
    init_oss_service(app.config)
    oss_service = get_oss_service()
    if oss_service and oss_service.is_available:
        logger.info("OSS 服务已初始化")
    else:
        logger.warning("OSS 服务不可用，封面动画功能将受限")
    
    # 初始化视频生成服务（视频保存到 outputs/videos/）
    try:
        os.makedirs(os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'videos'), exist_ok=True)
    except (OSError, IOError):
        pass
    init_video_service(app.config)
    video_service = get_video_service()
    if video_service and video_service.is_available():
        logger.info("视频生成服务已初始化")
    else:
        logger.warning("视频生成服务不可用")
    
    # 初始化知识源相关服务（二期）
    init_db_service()
    init_knowledge_service(
        max_content_length=app.config.get('KNOWLEDGE_MAX_CONTENT_LENGTH', 8000)
    )
    
    # 初始化文件解析服务
    mineru_token = app.config.get('MINERU_TOKEN', '')
    if mineru_token:
        upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
        try:
            os.makedirs(upload_folder, exist_ok=True)
        except (OSError, IOError):
            # Vercel 环境是只读的，无法创建目录，使用临时目录
            import tempfile
            upload_folder = tempfile.gettempdir()
            logger.warning(f"无法创建 uploads 目录，使用临时目录: {upload_folder}")
        
        init_file_parser(
            mineru_token=mineru_token,
            mineru_api_base=app.config.get('MINERU_API_BASE', 'https://mineru.net'),
            upload_folder=upload_folder,
            pdf_max_pages=int(os.getenv('PDF_MAX_PAGES', '15'))
        )
        logger.info("文件解析服务已初始化")
    else:
        logger.warning("MINERU_TOKEN 未配置，PDF 解析功能不可用")
    
    # 健康检查
    @app.route('/health')
    def health_check():
        return {'status': 'ok', 'service': 'banana-blog'}
    
    # 静态文件目录
    static_folder = os.path.join(os.path.dirname(__file__), 'static')
    outputs_folder = os.path.join(os.path.dirname(__file__), 'outputs')
    
    # 根路径 - 返回前端页面
    @app.route('/')
    def index():
        return send_from_directory(static_folder, 'index.html')
    
    # vibe-reviewer 独立页面
    @app.route('/reviewer')
    def reviewer_page():
        # 检查开关
        if os.environ.get('REVIEWER_ENABLED', 'false').lower() != 'true':
            return jsonify({'error': 'vibe-reviewer 功能未启用'}), 403
        return send_from_directory(static_folder, 'reviewer.html')
    
    # Docsify 书籍阅读器需要的 home.md
    @app.route('/home.md')
    def book_reader_home():
        return send_from_directory(static_folder, 'home.md')
    
    # Docsify 书籍阅读器需要的 _sidebar.md - 根据 book_id 动态生成
    @app.route('/_sidebar.md')
    @app.route('/static/_sidebar.md')
    def book_reader_sidebar():
        book_id = request.args.get('book_id')
        referrer = request.referrer
        logger.info(f"_sidebar.md 请求: book_id={book_id}, referrer={referrer}")
        if not book_id and referrer:
            # 从 Referer 中提取 book_id
            import re
            match = re.search(r'[?&]id=([^&#]+)', referrer)
            if match:
                book_id = match.group(1)
                logger.info(f"从 Referer 提取到 book_id: {book_id}")
        # 移除可能的 .md 后缀
        if book_id and book_id.endswith('.md'):
            book_id = book_id[:-3]
        if book_id:
            try:
                db_service = get_db_service()
                book = db_service.get_book(book_id)
                if book:
                    chapters = db_service.get_book_chapters(book_id)
                    md = f"- [**第 0 章 导读**](/)\n"
                    
                    # 按章节索引分组
                    chapter_groups = {}
                    for chapter in chapters:
                        idx = chapter.get('chapter_index', 0)
                        title = chapter.get('chapter_title', '未分类')
                        if idx not in chapter_groups:
                            chapter_groups[idx] = {'title': title, 'sections': []}
                        chapter_groups[idx]['sections'].append(chapter)
                    
                    # 按章节索引排序，生成章节和小节（不包含导读部分，由前端自动提取）
                    for idx in sorted(chapter_groups.keys()):
                        group = chapter_groups[idx]
                        md += f"- **第 {idx} 章 {group['title']}**\n"
                        for section in group['sections']:
                            chapter_id = section.get('id', '')
                            section_title = section.get('section_title', '')
                            md += f"  - [{section_title}](/chapter/{chapter_id})\n"
                    
                    return Response(md, mimetype='text/markdown')
            except Exception as e:
                logger.error(f"生成侧边栏失败: {e}")
        return Response('- [首页](/)', mimetype='text/markdown')
    
    # Docsify 书籍阅读器 - 章节内容路由（支持多种路径格式）
    @app.route('/chapter/<path:chapter_path>')
    @app.route('/chapter/<path:chapter_path>.md')
    @app.route('/static/chapter/<path:chapter_path>')
    @app.route('/static/chapter/<path:chapter_path>.md')
    def book_reader_chapter(chapter_path):
        # 返回一个占位符，实际内容由前端 beforeEach 钩子处理
        return Response('# 加载中...', mimetype='text/markdown')
    
    # 提供 outputs 目录下的图片文件
    @app.route('/outputs/images/<path:filename>')
    @app.route('/static/chapter/outputs/images/<path:filename>')  # Docsify 章节页面中的图片路径
    def serve_output_image(filename):
        images_folder = os.path.join(outputs_folder, 'images')
        return send_from_directory(images_folder, filename)
    
    # 提供 outputs 目录下的封面图片
    @app.route('/outputs/covers/<path:filename>')
    def serve_output_cover(filename):
        covers_folder = os.path.join(outputs_folder, 'covers')
        return send_from_directory(covers_folder, filename)
    
    # 提供 outputs 目录下的视频文件
    @app.route('/outputs/videos/<path:filename>')
    def serve_output_video(filename):
        videos_folder = os.path.join(outputs_folder, 'videos')
        return send_from_directory(videos_folder, filename)
    
    # API 文档页面（保留原来的简单页面）
    @app.route('/api-docs')
    def api_docs():
        html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vibe Blog - 技术科普绘本生成器</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #FF6B35; }
        h2 { color: #333; margin-top: 30px; }
        pre { background: #f5f5f5; padding: 15px; border-radius: 8px; overflow-x: auto; }
        .endpoint { background: #e8f5e9; padding: 10px; border-radius: 5px; margin: 10px 0; }
        ul { line-height: 1.8; }
    </style>
</head>
<body>
    <h1>🍌 vibe-blog</h1>
    <p>技术科普绘本生成器 - 让复杂技术变得人人都能懂</p>
    
    <h2>API 端点</h2>
    
    <div class="endpoint">
        <strong>POST /api/transform</strong> - 转化技术内容为科普绘本
    </div>
    <div class="endpoint">
        <strong>POST /api/generate-image</strong> - 生成单张图片
    </div>
    <div class="endpoint">
        <strong>POST /api/transform-with-images</strong> - 转化并生成配图
    </div>
    <div class="endpoint">
        <strong>GET /api/metaphors</strong> - 获取比喻库
    </div>
    
    <h2>使用示例</h2>
    <pre>curl -X POST http://localhost:5001/api/transform \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Redis 是一个开源的内存数据库...",
    "title": "Redis 入门",
    "page_count": 8
  }'</pre>
    
    <h2>请求参数</h2>
    <ul>
        <li><strong>content</strong> (必填): 原始技术博客内容</li>
        <li><strong>title</strong> (可选): 标题</li>
        <li><strong>target_audience</strong> (可选): 目标受众，默认"技术小白"</li>
        <li><strong>style</strong> (可选): 视觉风格，默认"可爱卡通风"</li>
        <li><strong>page_count</strong> (可选): 目标页数，默认 8</li>
    </ul>
</body>
</html>'''
        from flask import Response
        return Response(html, content_type='text/html; charset=utf-8')
    
    # 转化 API
    @app.route('/api/transform', methods=['POST'])
    def transform_content():
        """将技术内容转化为科普绘本风格"""
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
            
            # 创建转化服务
            llm_service = get_llm_service()
            if not llm_service or not llm_service.is_available():
                return jsonify({'success': False, 'error': 'LLM 服务不可用，请检查 API Key 配置'}), 500
            
            transform_service = create_transform_service(llm_service)
            
            # 执行转化
            result = transform_service.transform(
                content=content,
                title=title,
                target_audience=target_audience,
                style=style,
                page_count=page_count
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            logger.error(f"转化失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # 获取前端配置（统一的功能开关）
    @app.route('/api/config', methods=['GET'])
    def get_frontend_config():
        """
        获取前端配置
        
        统一管理所有前端功能开关，避免分散配置
        """
        return jsonify({
            'success': True,
            'config': {
                # 功能开关
                'features': {
                    'reviewer': os.environ.get('REVIEWER_ENABLED', 'false').lower() == 'true',
                    'book_scan': os.environ.get('BOOK_SCAN_ENABLED', 'false').lower() == 'true',
                    'cover_video': os.environ.get('COVER_VIDEO_ENABLED', 'true').lower() == 'true',
                },
                # 兼容旧版（后续可删除）
                'reviewer_enabled': os.environ.get('REVIEWER_ENABLED', 'false').lower() == 'true',
                'book_scan_enabled': os.environ.get('BOOK_SCAN_ENABLED', 'false').lower() == 'true'
            }
        })
    
    # 获取比喻库
    @app.route('/api/metaphors', methods=['GET'])
    def get_metaphors():
        """获取比喻库"""
        from services.transform_service import TransformService
        metaphors = []
        for concept, (metaphor, explanation) in TransformService.METAPHOR_LIBRARY.items():
            metaphors.append({
                'concept': concept,
                'metaphor': metaphor,
                'explanation': explanation
            })
        return jsonify({'success': True, 'metaphors': metaphors})
    
    # 获取图片风格列表 API
    @app.route('/api/image-styles', methods=['GET'])
    def get_image_styles():
        """获取可用的图片风格列表（供前端下拉框使用）"""
        try:
            style_manager = get_style_manager()
            styles = style_manager.get_all_styles()
            return jsonify({
                'success': True,
                'styles': styles
            })
        except Exception as e:
            logger.error(f"获取图片风格列表失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # 生成图片 API
    @app.route('/api/generate-image', methods=['POST'])
    def generate_image():
        """生成单张图片"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400
            
            prompt = data.get('prompt', '')
            if not prompt:
                return jsonify({'success': False, 'error': '请提供 prompt 参数'}), 400
            
            image_service = get_image_service()
            if not image_service or not image_service.is_available():
                return jsonify({'success': False, 'error': '图片生成服务不可用，请检查 API Key 配置'}), 500
            
            # 获取参数
            aspect_ratio_str = data.get('aspect_ratio', '16:9')
            image_size_str = data.get('image_size', '2K')
            image_style = data.get('image_style', '')  # 新增：图片风格
            use_style = data.get('use_style', True)
            download = data.get('download', True)
            
            # 转换枚举
            aspect_ratio = AspectRatio.LANDSCAPE_16_9
            for ar in AspectRatio:
                if ar.value == aspect_ratio_str:
                    aspect_ratio = ar
                    break
            
            image_size = ImageSize.SIZE_2K
            for size in ImageSize:
                if size.value == image_size_str:
                    image_size = size
                    break
            
            # 生成图片 - 支持多风格
            if image_style:
                # 使用新的风格管理器渲染 Prompt
                style_manager = get_style_manager()
                full_prompt = style_manager.render_prompt(image_style, prompt)
                result = image_service.generate(
                    prompt=full_prompt,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                    download=download
                )
            else:
                # 兼容旧逻辑
                style_prefix = STORYBOOK_STYLE_PREFIX if use_style else ""
                result = image_service.generate(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                    style_prefix=style_prefix,
                    download=download
                )
            
            if result:
                return jsonify({
                    'success': True,
                    'result': {
                        'url': result.url,
                        'local_path': result.local_path
                    }
                })
            else:
                return jsonify({'success': False, 'error': '图片生成失败'}), 500
                
        except Exception as e:
            logger.error(f"图片生成失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # 转化并生成配图 API
    @app.route('/api/transform-with-images', methods=['POST'])
    def transform_with_images():
        """将技术内容转化为科普绘本并生成配图"""
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
            generate_images = data.get('generate_images', True)
            
            # 创建转化服务
            llm_service = get_llm_service()
            if not llm_service or not llm_service.is_available():
                return jsonify({'success': False, 'error': 'LLM 服务不可用'}), 500
            
            transform_service = create_transform_service(llm_service)
            
            # 执行转化
            result = transform_service.transform(
                content=content,
                title=title,
                target_audience=target_audience,
                style=style,
                page_count=page_count
            )
            
            if not result['success']:
                return jsonify(result), 500
            
            # 生成配图
            if generate_images:
                image_service = get_image_service()
                if image_service and image_service.is_available():
                    pages = result['result'].get('pages', [])
                    for page in pages:
                        image_desc = page.get('image_description', '')
                        if image_desc:
                            logger.info(f"为第 {page.get('page_number')} 页生成配图...")
                            image_result = image_service.generate(
                                prompt=image_desc,
                                aspect_ratio=AspectRatio.LANDSCAPE_16_9,
                                image_size=ImageSize.SIZE_2K,
                                style_prefix=STORYBOOK_STYLE_PREFIX,
                                download=True
                            )
                            if image_result:
                                page['image_url'] = image_result.url
                                page['image_local_path'] = image_result.local_path
                else:
                    logger.warning("图片生成服务不可用，跳过配图生成")
            
            return jsonify(result)
                
        except Exception as e:
            logger.error(f"转化失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========== SSE 流式 API ==========
    
    # SSE 流式生成
    @app.route('/api/generate', methods=['POST'])
    def generate_storybook():
        """创建生成任务，返回 task_id 用于订阅 SSE"""
        import json as json_module
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
            
            # 检查 LLM 服务
            llm_service = get_llm_service()
            if not llm_service or not llm_service.is_available():
                return jsonify({'success': False, 'error': 'LLM 服务不可用'}), 500
            
            # 创建任务
            task_manager = get_task_manager()
            task_id = task_manager.create_task()
            
            # 创建流水线服务并异步执行
            image_service = get_image_service()
            pipeline_service = create_pipeline_service(
                llm_service=llm_service,
                image_service=image_service,
                task_manager=task_manager
            )
            
            from flask import current_app
            pipeline_service.run_pipeline_async(
                task_id=task_id,
                content=content,
                title=title,
                target_audience=target_audience,
                style=style,
                page_count=page_count,
                generate_images=generate_images,
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
    
    # SSE 进度推送端点
    @app.route('/api/tasks/<task_id>/stream')
    def stream_task_progress(task_id: str):
        """SSE 进度推送端点"""
        import json as json_module
        import time
        from queue import Empty
        
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
    
    # 获取任务状态
    @app.route('/api/tasks/<task_id>')
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
    
    # 取消任务
    @app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
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
    
    # ========== 知识源上传 API（二期） ==========
    
    import uuid
    import threading
    
    @app.route('/api/blog/upload', methods=['POST'])
    def upload_document():
        """
        上传知识文档
        
        请求: multipart/form-data, file 字段
        支持格式: PDF, MD, TXT
        
        返回:
        {
            "success": true,
            "document_id": "doc_xxx",
            "filename": "xxx.pdf",
            "status": "pending"
        }
        """
        try:
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': '请上传文件'}), 400
            
            file = request.files['file']
            if not file.filename:
                return jsonify({'success': False, 'error': '文件名为空'}), 400
            
            # 检查文件类型
            filename = file.filename
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            if ext not in ['pdf', 'md', 'txt', 'markdown']:
                return jsonify({'success': False, 'error': f'不支持的文件类型: {ext}'}), 400
            
            # 生成文档 ID
            doc_id = f"doc_{uuid.uuid4().hex[:12]}"
            
            # 保存文件
            upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, f"{doc_id}_{filename}")
            file.save(file_path)
            
            file_size = os.path.getsize(file_path)
            file_type = ext if ext != 'markdown' else 'md'
            
            # PDF 页数检查（上传时立即检查）
            if ext == 'pdf':
                file_parser = get_file_parser()
                if file_parser:
                    page_count = file_parser._get_pdf_page_count(file_path)
                    if page_count > file_parser.pdf_max_pages:
                        os.remove(file_path)  # 删除已保存的文件
                        return jsonify({
                            'success': False, 
                            'error': f'PDF 页数超过限制：{page_count} 页（最大支持 {file_parser.pdf_max_pages} 页）'
                        }), 400
            
            # 创建数据库记录
            db_service = get_db_service()
            db_service.create_document(
                doc_id=doc_id,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type
            )
            
            # 异步解析文档（二期：包含分块和图片摘要）
            def parse_async():
                try:
                    db_service.update_document_status(doc_id, 'parsing')
                    
                    file_parser = get_file_parser()
                    if not file_parser:
                        db_service.update_document_status(doc_id, 'error', '文件解析服务不可用')
                        return
                    
                    # 解析文件
                    result = file_parser.parse_file(file_path, filename)
                    
                    if not result.get('success'):
                        db_service.update_document_status(doc_id, 'error', result.get('error', '解析失败'))
                        return
                    
                    markdown = result.get('markdown', '')
                    images = result.get('images', [])
                    mineru_folder = result.get('mineru_folder')
                    
                    # 保存解析结果
                    db_service.save_parse_result(doc_id, markdown, mineru_folder)
                    
                    # 二期：知识分块
                    chunk_size = app.config.get('KNOWLEDGE_CHUNK_SIZE', 2000)
                    chunk_overlap = app.config.get('KNOWLEDGE_CHUNK_OVERLAP', 200)
                    chunks = file_parser.chunk_markdown(markdown, chunk_size, chunk_overlap)
                    db_service.save_chunks(doc_id, chunks)
                    
                    # 二期：生成文档摘要
                    llm_service = get_llm_service()
                    if llm_service:
                        summary = file_parser.generate_document_summary(markdown, llm_service)
                        if summary:
                            db_service.update_document_summary(doc_id, summary)
                    
                    # 二期：图片摘要（如果有图片）
                    if images and llm_service:
                        images_with_caption = file_parser.generate_image_captions(images, llm_service)
                        db_service.save_images(doc_id, images_with_caption)
                    elif images:
                        db_service.save_images(doc_id, images)
                    
                    logger.info(f"文档解析完成: {doc_id}, chunks={len(chunks)}, images={len(images)}")
                    
                except Exception as e:
                    logger.error(f"文档解析异常: {doc_id}, {e}", exc_info=True)
                    db_service.update_document_status(doc_id, 'error', str(e))
            
            thread = threading.Thread(target=parse_async, daemon=True)
            thread.start()
            
            return jsonify({
                'success': True,
                'document_id': doc_id,
                'filename': filename,
                'status': 'pending'
            })
            
        except Exception as e:
            logger.error(f"文档上传失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/blog/upload/<document_id>/status', methods=['GET'])
    def get_document_status(document_id):
        """获取文档解析状态"""
        db_service = get_db_service()
        doc = db_service.get_document(document_id)
        
        if not doc:
            return jsonify({'success': False, 'error': '文档不存在'}), 404
        
        # 获取分块和图片数量
        chunks = db_service.get_chunks_by_document(document_id)
        images = db_service.get_images_by_document(document_id)
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'filename': doc.get('filename'),
            'status': doc.get('status'),
            'summary': doc.get('summary'),
            'markdown_length': doc.get('markdown_length', 0),
            'chunks_count': len(chunks),
            'images_count': len(images),
            'error_message': doc.get('error_message'),
            'created_at': doc.get('created_at'),
            'parsed_at': doc.get('parsed_at')
        })
    
    @app.route('/api/blog/upload/<document_id>', methods=['DELETE'])
    def delete_document(document_id):
        """删除文档"""
        db_service = get_db_service()
        doc = db_service.get_document(document_id)
        
        if not doc:
            return jsonify({'success': False, 'error': '文档不存在'}), 404
        
        # 删除文件
        file_path = doc.get('file_path')
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # 删除数据库记录（级联删除 chunks 和 images）
        db_service.delete_document(document_id)
        
        return jsonify({'success': True, 'message': '文档已删除'})
    
    @app.route('/api/blog/documents', methods=['GET'])
    def list_documents():
        """列出所有文档"""
        db_service = get_db_service()
        status = request.args.get('status')
        docs = db_service.list_documents(status=status)
        
        return jsonify({
            'success': True,
            'documents': docs,
            'count': len(docs)
        })
    
    # ========== 长文博客生成 API ==========
    
    # 初始化搜索服务和博客生成服务
    try:
        # 初始化智谱搜索服务
        init_search_service(app.config)
        search_service = get_search_service()
        if search_service and search_service.is_available():
            logger.info("智谱搜索服务已初始化")
        else:
            logger.warning("智谱搜索服务不可用，Researcher Agent 将跳过联网搜索")
        
        # 初始化博客生成服务（传入知识服务）
        llm_service = get_llm_service()
        knowledge_service = get_knowledge_service()
        if llm_service and llm_service.is_available():
            init_blog_service(llm_service, search_service, knowledge_service)
            logger.info("博客生成服务已初始化（含知识融合支持）")
    except Exception as e:
        logger.warning(f"博客生成服务初始化失败: {e}")
    
    @app.route('/api/blog/generate', methods=['POST'])
    def generate_blog():
        """
        创建长文博客生成任务
        
        请求体:
        {
            "topic": "LangGraph 入门教程",
            "article_type": "tutorial",  // tutorial | problem-solution | comparison
            "target_audience": "intermediate",  // beginner | intermediate | advanced
            "target_length": "medium",  // short | medium | long
            "document_ids": []  // 可选，上传文档的 ID 列表
        }
        
        返回:
        {
            "success": true,
            "task_id": "xxx",
            "message": "任务已创建，请订阅 SSE 获取进度"
        }
        """
        import json as json_module
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400
            
            topic = data.get('topic', '')
            if not topic:
                return jsonify({'success': False, 'error': '请提供 topic 参数'}), 400
            
            article_type = data.get('article_type', 'tutorial')
            target_audience = data.get('target_audience', 'intermediate')
            audience_adaptation = data.get('audience_adaptation', 'default')  # 新增受众适配参数
            target_length = data.get('target_length', 'medium')
            source_material = data.get('source_material', None)
            document_ids = data.get('document_ids', [])  # 文档 ID 列表
            image_style = data.get('image_style', '')  # 图片风格 ID
            generate_cover_video = data.get('generate_cover_video', False)  # 是否生成封面动画
            custom_config = data.get('custom_config', None)  # 自定义配置（仅当 target_length='custom' 时使用）
            
            # 验证自定义配置
            if target_length == 'custom':
                if not custom_config:
                    return jsonify({'success': False, 'error': '自定义模式需要提供 custom_config 参数'}), 400
                try:
                    from config import validate_custom_config
                    validate_custom_config(custom_config)
                except ValueError as e:
                    return jsonify({'success': False, 'error': f'自定义配置验证失败: {str(e)}'}), 400
            
            # 记录请求信息
            logger.info(f"📝 博客生成请求: topic={topic}, article_type={article_type}, target_audience={target_audience}, audience_adaptation={audience_adaptation}, target_length={target_length}, document_ids={document_ids}, generate_cover_video={generate_cover_video}, custom_config={custom_config}")
            
            # 检查博客生成服务
            blog_service = get_blog_service()
            if not blog_service:
                return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500
            
            # 准备文档知识（如果有上传文档）
            document_knowledge = []
            if document_ids:
                logger.info(f"📄 接收到文档 ID 列表: {document_ids}")
                db_service = get_db_service()
                docs = db_service.get_documents_by_ids(document_ids)
                logger.info(f"📄 从数据库查询到 {len(docs)} 个已就绪的文档")
                for doc in docs:
                    markdown = doc.get('markdown_content', '')
                    logger.info(f"📄 文档 {doc.get('filename', '')}: status={doc.get('status')}, markdown_length={len(markdown)}")
                    if markdown:
                        document_knowledge.append({
                            'file_name': doc.get('filename', ''),
                            'content': markdown,
                            'source_type': 'document'
                        })
                logger.info(f"✅ 加载文档知识: {len(document_knowledge)} 条")
            
            # 创建任务
            task_manager = get_task_manager()
            task_id = task_manager.create_task()
            
            # 异步执行生成
            from flask import current_app
            blog_service.generate_async(
                task_id=task_id,
                topic=topic,
                article_type=article_type,
                target_audience=target_audience,
                audience_adaptation=audience_adaptation,
                target_length=target_length,
                source_material=source_material,
                document_ids=document_ids,
                document_knowledge=document_knowledge,
                image_style=image_style,
                generate_cover_video=generate_cover_video,
                custom_config=custom_config,
                task_manager=task_manager,
                app=current_app._get_current_object()
            )
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': '博客生成任务已创建，请订阅 /api/tasks/{task_id}/stream 获取进度',
                'document_count': len(document_knowledge)
            }), 202
            
        except Exception as e:
            logger.error(f"创建博客生成任务失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/blog/generate/mini', methods=['POST'])
    def generate_blog_mini():
        """
        创建 Mini 版博客生成任务（1个章节，完整流程）
        用于快速测试整个功能链路
        
        请求体:
        {
            "topic": "LangGraph 入门教程",
            "article_type": "tutorial",
            "generate_cover_video": true  // 可选，是否生成封面动画
        }
        
        返回:
        {
            "success": true,
            "task_id": "xxx",
            "message": "任务已创建，请订阅 SSE 获取进度"
        }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400
            
            topic = data.get('topic', '')
            if not topic:
                return jsonify({'success': False, 'error': '请提供 topic 参数'}), 400
            
            article_type = data.get('article_type', 'tutorial')
            audience_adaptation = data.get('audience_adaptation', 'default')  # 新增受众适配参数
            generate_cover_video = data.get('generate_cover_video', False)
            
            logger.info(f"📝 Mini 博客生成请求: topic={topic}, article_type={article_type}, audience_adaptation={audience_adaptation}, generate_cover_video={generate_cover_video}")
            
            # 检查博客生成服务
            blog_service = get_blog_service()
            if not blog_service:
                return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500
            
            # 创建任务
            task_manager = get_task_manager()
            task_id = task_manager.create_task()
            
            # 异步执行生成（Mini 版：使用 mini 模式，只生成 1 个章节）
            from flask import current_app
            blog_service.generate_async(
                task_id=task_id,
                topic=topic,
                article_type=article_type,
                target_audience='intermediate',
                audience_adaptation=audience_adaptation,
                target_length='mini',  # Mini 版使用 mini 模式
                source_material=None,
                document_ids=[],
                document_knowledge=[],
                image_style='',
                generate_cover_video=generate_cover_video,
                custom_config=None,
                task_manager=task_manager,
                app=current_app._get_current_object()
            )
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Mini 博客生成任务已创建（1个章节完整流程），请订阅 /api/tasks/{task_id}/stream 获取进度'
            }), 202
            
        except Exception as e:
            logger.error(f"创建 Mini 博客生成任务失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/blog/generate/sync', methods=['POST'])
    def generate_blog_sync():
        """
        同步生成长文博客 (适用于短文章或测试)
        
        请求体同 /api/blog/generate
        
        返回:
        {
            "success": true,
            "markdown": "# 完整文章...",
            "outline": {...},
            "sections_count": 5,
            "images_count": 3,
            "code_blocks_count": 4,
            "review_score": 85
        }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400
            
            topic = data.get('topic', '')
            if not topic:
                return jsonify({'success': False, 'error': '请提供 topic 参数'}), 400
            
            article_type = data.get('article_type', 'tutorial')
            target_audience = data.get('target_audience', 'intermediate')
            target_length = data.get('target_length', 'medium')
            source_material = data.get('source_material', None)
            
            # 检查博客生成服务
            blog_service = get_blog_service()
            if not blog_service:
                return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500
            
            # 同步执行生成
            result = blog_service.generate_sync(
                topic=topic,
                article_type=article_type,
                target_audience=target_audience,
                target_length=target_length,
                source_material=source_material
            )
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"博客生成失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========== 历史记录 API ==========
    
    @app.route('/api/history', methods=['GET'])
    def list_history():
        """获取历史记录列表（支持分页）"""
        try:
            page = request.args.get('page', 1, type=int)
            page_size = request.args.get('page_size', 12, type=int)
            offset = (page - 1) * page_size
            
            db_service = get_db_service()
            total = db_service.count_history()
            records = db_service.list_history(limit=page_size, offset=offset)
            total_pages = (total + page_size - 1) // page_size
            
            return jsonify({
                'success': True, 
                'records': records,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages
            })
        except Exception as e:
            logger.error(f"获取历史记录失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/history/<history_id>', methods=['GET'])
    def get_history(history_id):
        """获取单条历史记录详情"""
        try:
            db_service = get_db_service()
            record = db_service.get_history(history_id)
            if record:
                return jsonify({'success': True, 'record': record})
            else:
                return jsonify({'success': False, 'error': '记录不存在'}), 404
        except Exception as e:
            logger.error(f"获取历史记录失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/history/<history_id>', methods=['DELETE'])
    def delete_history(history_id):
        """删除历史记录"""
        try:
            db_service = get_db_service()
            deleted = db_service.delete_history(history_id)
            if deleted:
                return jsonify({'success': True, 'message': '删除成功'})
            else:
                return jsonify({'success': False, 'error': '记录不存在'}), 404
        except Exception as e:
            logger.error(f"删除历史记录失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========== 视频生成 API ==========
    
    @app.route('/api/video/generate', methods=['POST'])
    def generate_video():
        """
        生成封面动画视频
        
        请求体:
        {
            "history_id": "xxx",      // 历史记录 ID（用于更新数据库）
            "image_url": "https://...", // 封面图 URL（可选，如果提供则直接使用）
            "image_path": "/path/to/image.png", // 封面图本地路径（可选）
            "prompt": "可选的自定义提示词"
        }
        
        返回:
        {
            "success": true,
            "video_url": "/outputs/videos/xxx.mp4",
            "task_id": "veo3-task-id"
        }
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400
            
            history_id = data.get('history_id')
            image_url = data.get('image_url')
            image_path = data.get('image_path')
            prompt = data.get('prompt')
            
            # 检查视频服务
            video_service = get_video_service()
            if not video_service or not video_service.is_available():
                return jsonify({'success': False, 'error': '视频生成服务不可用'}), 503
            
            # 如果没有提供 image_url，需要从本地路径上传到 OSS
            if not image_url:
                if not image_path:
                    # 尝试从历史记录获取封面图路径
                    if history_id:
                        db_service = get_db_service()
                        record = db_service.get_history(history_id)
                        if record and record.get('cover_image'):
                            image_path = record.get('cover_image')
                
                if not image_path:
                    return jsonify({'success': False, 'error': '缺少 image_url 或 image_path 参数'}), 400
                
                # 上传到 OSS
                oss_service = get_oss_service()
                if not oss_service or not oss_service.is_available:
                    return jsonify({'success': False, 'error': 'OSS 服务不可用，无法上传图片'}), 503
                
                # 生成 OSS 路径
                import uuid
                unique_id = uuid.uuid4().hex[:8]
                filename = os.path.basename(image_path)
                remote_path = f"vibe-blog/covers/{unique_id}_{filename}"
                
                oss_result = oss_service.upload_file(
                    local_path=image_path,
                    remote_path=remote_path
                )
                
                if not oss_result.get('success'):
                    return jsonify({'success': False, 'error': f"图片上传失败: {oss_result.get('error')}"}), 500
                
                image_url = oss_result['url']
                logger.info(f"封面图已上传到 OSS: {image_url}")
            
            # 调用视频生成服务
            logger.info(f"开始生成封面动画: history_id={history_id}, image_url={image_url[:80]}...")
            
            result = video_service.generate_from_image(
                image_url=image_url,
                prompt=prompt
            )
            
            if not result:
                return jsonify({'success': False, 'error': '视频生成失败'}), 500
            
            # 构建视频访问 URL
            video_filename = os.path.basename(result.local_path) if result.local_path else None
            video_access_url = f"/outputs/videos/{video_filename}" if video_filename else result.url
            
            # 更新数据库
            if history_id:
                db_service = get_db_service()
                db_service.update_history_video(history_id, video_access_url)
            
            logger.info(f"封面动画生成成功: {video_access_url}")
            
            return jsonify({
                'success': True,
                'video_url': video_access_url,
                'task_id': result.task_id
            })
            
        except Exception as e:
            logger.error(f"视频生成失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========== Markdown 导出 API ==========
    
    def extract_image_urls(markdown_content):
        """从 Markdown 中提取所有图片 URL"""
        pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
        matches = re.findall(pattern, markdown_content)
        return matches
    
    def download_image(url, timeout=10):
        """下载图片，返回二进制内容"""
        try:
            original_url = url
            
            # 处理各种相对路径格式
            if url.startswith('./images/'):
                # ./images/xxx.png -> /outputs/images/xxx.png
                url = '/outputs/images/' + url[9:]
            elif url.startswith('/outputs/images/'):
                # 已经是正确格式
                pass
            
            if url.startswith('/'):
                # 相对路径，需要拼接完整 URL
                base_url = request.host_url.rstrip('/')
                url = base_url + url
            
            logger.info(f"下载图片: {original_url} -> {url}")
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.warning(f"下载图片失败 {url}: {e}")
            return None
    
    def get_image_filename(url):
        """从 URL 中提取文件名"""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename or '.' not in filename:
            filename = 'image.png'
        return filename
    
    @app.route('/api/export/markdown', methods=['POST'])
    def export_markdown_with_images():
        """
        导出 Markdown 文件，包含所有本地图片
        
        请求体:
        {
            "markdown": "# 标题\n![图片](url)...",
            "title": "文档标题"
        }
        
        返回: ZIP 文件，包含 markdown 文件和 images 目录
        """
        try:
            data = request.get_json()
            if not data or 'markdown' not in data:
                return jsonify({'success': False, 'error': '缺少 markdown 参数'}), 400
            
            markdown_content = data.get('markdown', '')
            title = data.get('title', 'blog')
            
            # 清理标题中的特殊字符，保留中文
            safe_title = re.sub(r'[^\w\u4e00-\u9fa5_-]', '_', title)[:50]
            
            # 提取所有图片 URL
            image_matches = extract_image_urls(markdown_content)
            
            # 创建 ZIP 文件（使用 UTF-8 编码文件名）
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # 设置 UTF-8 编码标志
                zip_file.comment = b''
                # 处理 Markdown 内容，替换图片路径
                modified_markdown = markdown_content
                image_mapping = {}  # 原始 URL -> 新文件名的映射
                
                for alt_text, img_url in image_matches:
                    # 下载图片
                    img_content = download_image(img_url)
                    if img_content:
                        # 生成新的文件名
                        original_filename = get_image_filename(img_url)
                        # 确保文件名唯一
                        base_name, ext = os.path.splitext(original_filename)
                        counter = 1
                        new_filename = original_filename
                        while new_filename in image_mapping.values():
                            new_filename = f"{base_name}_{counter}{ext}"
                            counter += 1
                        
                        # 保存到 ZIP 的 images 目录
                        zip_file.writestr(f'images/{new_filename}', img_content)
                        image_mapping[img_url] = new_filename
                        
                        # 更新 Markdown 中的图片路径为相对路径
                        old_ref = f'![{alt_text}]({img_url})'
                        new_ref = f'![{alt_text}](./images/{new_filename})'
                        modified_markdown = modified_markdown.replace(old_ref, new_ref)
                
                # 将修改后的 Markdown 写入 ZIP
                zip_file.writestr(f'{safe_title}.md', modified_markdown.encode('utf-8'))
            
            # 返回 ZIP 文件
            zip_buffer.seek(0)
            timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d')
            # 使用纯英文文件名避免编码问题
            filename = f'export_{timestamp}.zip'
            
            return Response(
                zip_buffer.getvalue(),
                mimetype='application/zip',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )
            
        except Exception as e:
            logger.error(f"导出 Markdown 失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========== 书籍 API ==========
    
    @app.route('/api/books', methods=['GET'])
    def list_books():
        """获取书籍列表"""
        try:
            db_service = get_db_service()
            status = request.args.get('status', 'active')
            limit = request.args.get('limit', 50, type=int)
            
            books = db_service.list_books(status=status, limit=limit)
            
            # 解析大纲 JSON
            for book in books:
                if book.get('outline'):
                    try:
                        book['outline'] = json.loads(book['outline'])
                    except json.JSONDecodeError:
                        book['outline'] = None
            
            return jsonify({
                'success': True,
                'books': books,
                'total': len(books)
            })
        except Exception as e:
            logger.error(f"获取书籍列表失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/books/<book_id>', methods=['GET'])
    def get_book(book_id):
        """获取书籍详情"""
        try:
            db_service = get_db_service()
            book = db_service.get_book(book_id)
            
            if not book:
                return jsonify({'success': False, 'error': '书籍不存在'}), 404
            
            # 解析大纲 JSON
            if book.get('outline'):
                try:
                    book['outline'] = json.loads(book['outline'])
                except json.JSONDecodeError:
                    book['outline'] = None
            
            # 获取章节信息
            book['chapters'] = db_service.get_book_chapters(book_id)
            
            return jsonify({'success': True, 'book': book})
        except Exception as e:
            logger.error(f"获取书籍详情失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/books/<book_id>/chapters/<chapter_id>', methods=['GET'])
    def get_book_chapter(book_id, chapter_id):
        """获取书籍章节内容"""
        try:
            db_service = get_db_service()
            chapter = db_service.get_chapter_with_content(book_id, chapter_id)
            
            if not chapter:
                return jsonify({'success': False, 'error': '章节不存在'}), 404
            
            return jsonify({
                'success': True,
                'chapter': chapter,
                'has_content': bool(chapter.get('markdown_content')),
                'markdown_content': chapter.get('markdown_content', ''),
                'chapter_title': chapter.get('chapter_title', ''),
                'section_title': chapter.get('section_title', '')
            })
        except Exception as e:
            logger.error(f"获取章节内容失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/books/regenerate', methods=['POST'])
    def regenerate_books():
        """重新生成所有书籍（清空旧数据，重新聚合）"""
        try:
            from services.book_scanner_service import BookScannerService
            
            db_service = get_db_service()
            llm_service = get_llm_service()
            
            scanner = BookScannerService(db_service, llm_service)
            result = scanner.regenerate_all_books()
            
            return jsonify({
                'success': True,
                **result
            })
        except Exception as e:
            logger.error(f"重新生成书籍失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/books/<book_id>/rescan', methods=['POST'])
    def rescan_book(book_id):
        """重新扫描单本书籍"""
        try:
            from services.book_scanner_service import BookScannerService
            
            db_service = get_db_service()
            llm_service = get_llm_service()
            
            scanner = BookScannerService(db_service, llm_service)
            result = scanner.rescan_book(book_id)
            
            return jsonify({
                'success': True,
                **result
            })
        except Exception as e:
            logger.error(f"重新扫描书籍失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/books/<book_id>/generate-intro', methods=['POST'])
    def generate_book_intro(book_id):
        """生成书籍简介"""
        try:
            from services.book_scanner_service import BookScannerService
            
            db_service = get_db_service()
            llm_service = get_llm_service()
            
            scanner = BookScannerService(db_service, llm_service)
            introduction = scanner.generate_book_introduction(book_id)
            
            if introduction:
                return jsonify({
                    'success': True,
                    'introduction': introduction
                })
            else:
                return jsonify({'success': False, 'error': '生成简介失败'}), 500
        except Exception as e:
            logger.error(f"生成书籍简介失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/books/<book_id>/generate-cover', methods=['POST'])
    def generate_book_cover(book_id):
        """生成书籍封面"""
        try:
            from services.book_scanner_service import BookScannerService
            
            db_service = get_db_service()
            
            scanner = BookScannerService(db_service)
            cover_url = scanner.generate_book_cover(book_id)
            
            if cover_url:
                return jsonify({
                    'success': True,
                    'cover_url': cover_url
                })
            else:
                return jsonify({'success': False, 'error': '生成封面失败'}), 500
        except Exception as e:
            logger.error(f"生成书籍封面失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/books/generate-all-covers', methods=['POST'])
    def generate_all_book_covers():
        """为所有书籍生成封面"""
        try:
            from services.book_scanner_service import BookScannerService
            
            db_service = get_db_service()
            
            scanner = BookScannerService(db_service)
            result = scanner.generate_covers_for_all_books()
            
            return jsonify({
                'success': True,
                **result
            })
        except Exception as e:
            logger.error(f"批量生成封面失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/books/<book_id>', methods=['DELETE'])
    def delete_book(book_id):
        """删除书籍"""
        try:
            db_service = get_db_service()
            deleted = db_service.delete_book(book_id)
            
            if deleted:
                return jsonify({'success': True, 'message': '删除成功'})
            else:
                return jsonify({'success': False, 'error': '书籍不存在'}), 404
        except Exception as e:
            logger.error(f"删除书籍失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/books/<book_id>/generate-homepage', methods=['POST'])
    def generate_book_homepage(book_id):
        """生成书籍首页内容"""
        try:
            from services.outline_expander_service import OutlineExpanderService
            from services.homepage_generator_service import HomepageGeneratorService
            
            db_service = get_db_service()
            llm_service = get_llm_service()
            search_service = get_search_service()
            
            # 创建服务
            outline_expander = OutlineExpanderService(db_service, llm_service, search_service)
            homepage_service = HomepageGeneratorService(db_service, llm_service, outline_expander)
            
            # 生成首页
            result = homepage_service.generate_homepage(book_id)
            
            if result:
                return jsonify({
                    'success': True,
                    'homepage': result
                })
            else:
                return jsonify({'success': False, 'error': '生成首页失败'}), 500
        except Exception as e:
            logger.error(f"生成书籍首页失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/books/<book_id>/expand-outline', methods=['POST'])
    def expand_book_outline(book_id):
        """扩展书籍大纲"""
        try:
            from services.outline_expander_service import OutlineExpanderService
            
            db_service = get_db_service()
            llm_service = get_llm_service()
            search_service = get_search_service()
            
            # 创建服务
            outline_expander = OutlineExpanderService(db_service, llm_service, search_service)
            
            # 扩展大纲
            result = outline_expander.expand_outline(book_id)
            
            if result:
                return jsonify({
                    'success': True,
                    'outline': result
                })
            else:
                return jsonify({'success': False, 'error': '扩展大纲失败'}), 500
        except Exception as e:
            logger.error(f"扩展书籍大纲失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/blogs/with-book-info', methods=['GET'])
    def list_blogs_with_book_info():
        """获取博客列表（包含书籍信息）"""
        try:
            db_service = get_db_service()
            page = request.args.get('page', 1, type=int)
            page_size = request.args.get('page_size', 20, type=int)
            offset = (page - 1) * page_size
            
            blogs = db_service.get_all_blogs_with_book_info(limit=page_size, offset=offset)
            total = db_service.count_history()
            
            return jsonify({
                'success': True,
                'blogs': blogs,
                'total': total,
                'page': page,
                'page_size': page_size
            })
        except Exception as e:
            logger.error(f"获取博客列表失败: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ========== vibe-reviewer 初始化 (新增) ==========
    # 检查开关
    if os.environ.get('REVIEWER_ENABLED', 'false').lower() != 'true':
        logger.info("vibe-reviewer 功能未启用 (REVIEWER_ENABLED != true)")
    else:
      try:
        from vibe_reviewer import init_reviewer_service, get_reviewer_service
        from vibe_reviewer.api import register_reviewer_routes
        
        # 获取搜索服务
        reviewer_search_service = None
        try:
            reviewer_search_service = get_search_service()
            if reviewer_search_service and reviewer_search_service.is_available():
                logger.info("vibe-reviewer 将使用智谱搜索服务进行增强评估")
            else:
                logger.warning("vibe-reviewer 搜索服务不可用，将仅使用 LLM 评估")
                reviewer_search_service = None
        except Exception as e:
            logger.warning(f"获取搜索服务失败: {e}")
        
        # 初始化 ReviewerService
        init_reviewer_service(
            llm_service=get_llm_service(),
            search_service=reviewer_search_service,
        )
        
        # 注册 API 路由
        register_reviewer_routes(app)
        
        logger.info("vibe-reviewer 模块已初始化")
      except Exception as e:
        logger.warning(f"vibe-reviewer 模块初始化失败 (可选模块): {e}")
    
    logger.info("Vibe Blog 后端应用已启动")
    return app


# 开发服务器入口
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
