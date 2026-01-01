"""
Banana Vibe Blog 后端应用入口
技术科普绘本生成器
"""
import os
import logging
from dotenv import load_dotenv

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

# 配置日志
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_format)
root_logger.addHandler(console_handler)

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_format)
root_logger.addHandler(file_handler)

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
    
    # 确保目录存在
    os.makedirs(app.config.get('OUTPUT_FOLDER', 'outputs'), exist_ok=True)
    os.makedirs(os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'images'), exist_ok=True)
    
    # 初始化 LLM 服务
    init_llm_service(app.config)
    
    # 初始化图片生成服务（图片保存到 outputs/images/）
    app.config['IMAGE_OUTPUT_FOLDER'] = os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'images')
    init_image_service(app.config)
    
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
    
    # 提供 outputs 目录下的图片文件
    @app.route('/outputs/images/<path:filename>')
    def serve_output_image(filename):
        images_folder = os.path.join(outputs_folder, 'images')
        return send_from_directory(images_folder, filename)
    
    # API 文档页面（保留原来的简单页面）
    @app.route('/api-docs')
    def api_docs():
        html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Banana Blog - 技术科普绘本生成器</title>
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
    <h1>🍌 Banana Vibe Blog</h1>
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
            
            # 生成图片
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
        
        # 初始化博客生成服务
        llm_service = get_llm_service()
        if llm_service and llm_service.is_available():
            init_blog_service(llm_service, search_service)
            logger.info("博客生成服务已初始化")
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
            target_length = data.get('target_length', 'medium')
            source_material = data.get('source_material', None)
            document_ids = data.get('document_ids', [])  # 新增：文档 ID 列表
            
            # 检查博客生成服务
            blog_service = get_blog_service()
            if not blog_service:
                return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500
            
            # 准备文档知识（如果有上传文档）
            document_knowledge = []
            if document_ids:
                db_service = get_db_service()
                docs = db_service.get_documents_by_ids(document_ids)
                for doc in docs:
                    if doc.get('markdown_content'):
                        document_knowledge.append({
                            'file_name': doc.get('filename', ''),
                            'content': doc.get('markdown_content', ''),
                            'source_type': 'document'
                        })
                logger.info(f"加载文档知识: {len(document_knowledge)} 条")
            
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
                target_length=target_length,
                source_material=source_material,
                document_ids=document_ids,
                document_knowledge=document_knowledge,
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
    
    logger.info("Banana Blog 后端应用已启动")
    return app


# 开发服务器入口
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
