"""
博客生成路由
/api/blog/upload, /api/blog/generate, /api/blog/documents, etc.
"""
import os
import uuid
import logging
import threading

from flask import Blueprint, jsonify, request, current_app

from services import (
    get_llm_service, get_blog_service,
    get_task_manager, init_blog_service,
    init_search_service, get_search_service,
)
from services.database_service import get_db_service
from services.file_parser_service import get_file_parser
from services.knowledge_service import get_knowledge_service

logger = logging.getLogger(__name__)

blog_bp = Blueprint('blog', __name__)

# 支持的上传文件类型
ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown', 'ppt', 'pptx',
                      'xls', 'xlsx', 'doc', 'docx'}


def _record_task_to_queue(task_id: str, topic: str, article_type: str,
                          target_length: str, image_style: str = ""):
    """将任务记录到 TaskQueueManager（Dashboard 统计用）"""
    try:
        app = current_app._get_current_object()
        queue_manager = getattr(app, 'queue_manager', None)
        if not queue_manager:
            return
        import asyncio
        from services.task_queue.models import (
            BlogTask, BlogGenerationConfig, QueueStatus,
        )
        task = BlogTask(
            id=task_id,
            name=f"博客: {topic[:30]}",
            generation=BlogGenerationConfig(
                topic=topic,
                article_type=article_type,
                target_length=target_length,
                image_style=image_style or None,
            ),
            status=QueueStatus.RUNNING,
        )
        task.started_at = task.created_at
        asyncio.run(queue_manager.db.save_task(task))
    except Exception as e:
        logger.debug(f"记录任务到排队系统失败 (非关键): {e}")


def init_blog_services(app_config):
    """初始化搜索服务和博客生成服务（在 create_app 中调用）"""
    try:
        init_search_service(app_config)
        search_service = get_search_service()
        if search_service and search_service.is_available():
            logger.info("智谱搜索服务已初始化")
        else:
            logger.warning("智谱搜索服务不可用，Researcher Agent 将跳过联网搜索")

        # 75.02 Serper Google 搜索
        try:
            from services.blog_generator.services.serper_search_service import init_serper_service
            serper = init_serper_service(app_config)
            if serper and serper.is_available():
                logger.info("Serper Google 搜索服务已初始化")
        except Exception as e:
            logger.warning(f"Serper 服务初始化跳过: {e}")

        # 75.07 搜狗搜索（腾讯云 SearchPro）
        try:
            from services.blog_generator.services.sogou_search_service import init_sogou_service
            sogou = init_sogou_service(app_config)
            if sogou:
                logger.info("搜狗搜索服务已初始化")
        except Exception as e:
            logger.warning(f"搜狗服务初始化跳过: {e}")

        llm_service = get_llm_service()
        knowledge_service = get_knowledge_service()
        if llm_service and llm_service.is_available():
            init_blog_service(llm_service, search_service, knowledge_service)
            logger.info("博客生成服务已初始化（含知识融合支持）")
    except Exception as e:
        logger.warning(f"博客生成服务初始化失败: {e}")


@blog_bp.route('/api/blog/upload', methods=['POST'])
def upload_document():
    """上传知识文档"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '请上传文件'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'success': False, 'error': '文件名为空'}), 400

        filename = file.filename
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({'success': False, 'error': f'不支持的文件类型: {ext}'}), 400

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"

        upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, f"{doc_id}_{filename}")
        file.save(file_path)

        file_size = os.path.getsize(file_path)
        file_type = ext if ext != 'markdown' else 'md'

        if ext == 'pdf':
            file_parser = get_file_parser()
            if file_parser:
                page_count = file_parser._get_pdf_page_count(file_path)
                if page_count > file_parser.pdf_max_pages:
                    os.remove(file_path)
                    return jsonify({
                        'success': False,
                        'error': f'PDF 页数超过限制：{page_count} 页（最大支持 {file_parser.pdf_max_pages} 页）'
                    }), 400

        db_service = get_db_service()
        db_service.create_document(
            doc_id=doc_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type
        )

        app = current_app._get_current_object()

        def parse_async():
            with app.app_context():
                try:
                    db_service.update_document_status(doc_id, 'parsing')

                    file_parser = get_file_parser()
                    if not file_parser:
                        db_service.update_document_status(doc_id, 'error', '文件解析服务不可用')
                        return

                    result = file_parser.parse_file(file_path, filename)

                    if not result.get('success'):
                        db_service.update_document_status(doc_id, 'error', result.get('error', '解析失败'))
                        return

                    markdown = result.get('markdown', '')
                    images = result.get('images', [])
                    mineru_folder = result.get('mineru_folder')

                    db_service.save_parse_result(doc_id, markdown, mineru_folder)

                    chunk_size = app.config.get('KNOWLEDGE_CHUNK_SIZE', 2000)
                    chunk_overlap = app.config.get('KNOWLEDGE_CHUNK_OVERLAP', 200)
                    chunks = file_parser.chunk_markdown(markdown, chunk_size, chunk_overlap)
                    db_service.save_chunks(doc_id, chunks)

                    llm_service = get_llm_service()
                    if llm_service:
                        summary = file_parser.generate_document_summary(markdown, llm_service)
                        if summary:
                            db_service.update_document_summary(doc_id, summary)

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


@blog_bp.route('/api/blog/upload/<document_id>/status', methods=['GET'])
def get_document_status(document_id):
    """获取文档解析状态"""
    db_service = get_db_service()
    doc = db_service.get_document(document_id)

    if not doc:
        return jsonify({'success': False, 'error': '文档不存在'}), 404

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


@blog_bp.route('/api/blog/upload/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """删除文档"""
    db_service = get_db_service()
    doc = db_service.get_document(document_id)

    if not doc:
        return jsonify({'success': False, 'error': '文档不存在'}), 404

    file_path = doc.get('file_path')
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    db_service.delete_document(document_id)

    return jsonify({'success': True, 'message': '文档已删除'})


@blog_bp.route('/api/blog/documents', methods=['GET'])
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


@blog_bp.route('/api/blog/generate', methods=['POST'])
def generate_blog():
    """创建长文博客生成任务"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400

        topic = data.get('topic', '')
        if not topic:
            return jsonify({'success': False, 'error': '请提供 topic 参数'}), 400

        article_type = data.get('article_type', 'tutorial')
        target_audience = data.get('target_audience', 'intermediate')
        audience_adaptation = data.get('audience_adaptation', 'default')
        target_length = data.get('target_length', 'medium')
        source_material = data.get('source_material', None)
        document_ids = data.get('document_ids', [])
        image_style = data.get('image_style', '')
        generate_cover_video = data.get('generate_cover_video', False)
        video_aspect_ratio = data.get('video_aspect_ratio', '16:9')
        custom_config = data.get('custom_config', None)
        deep_thinking = data.get('deep_thinking', False)
        background_investigation = data.get('background_investigation', True)
        interactive = data.get('interactive', False)

        if target_length == 'custom':
            if not custom_config:
                return jsonify({'success': False, 'error': '自定义模式需要提供 custom_config 参数'}), 400
            try:
                from config import validate_custom_config
                validate_custom_config(custom_config)
            except ValueError as e:
                return jsonify({'success': False, 'error': f'自定义配置验证失败: {str(e)}'}), 400

        logger.info(f"📝 博客生成请求: topic={topic}, article_type={article_type}, target_audience={target_audience}, audience_adaptation={audience_adaptation}, target_length={target_length}, document_ids={document_ids}, image_style={image_style}, generate_cover_video={generate_cover_video}, video_aspect_ratio={video_aspect_ratio}, custom_config={custom_config}")

        blog_service = get_blog_service()
        if not blog_service:
            return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500

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

        task_manager = get_task_manager()
        task_id = task_manager.create_task()

        _record_task_to_queue(task_id, topic, article_type, target_length, image_style)

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
            video_aspect_ratio=video_aspect_ratio,
            custom_config=custom_config,
            deep_thinking=deep_thinking,
            background_investigation=background_investigation,
            interactive=interactive,
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


@blog_bp.route('/api/blog/generate/mini', methods=['POST'])
def generate_blog_mini():
    """创建 Mini 版博客生成任务（1个章节，完整流程）"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400

        topic = data.get('topic', '')
        if not topic:
            return jsonify({'success': False, 'error': '请提供 topic 参数'}), 400

        article_type = data.get('article_type', 'tutorial')
        audience_adaptation = data.get('audience_adaptation', 'default')
        image_style = data.get('image_style', '')
        generate_cover_video = data.get('generate_cover_video', False)
        video_aspect_ratio = data.get('video_aspect_ratio', '16:9')

        logger.info(f"📝 Mini 博客生成请求: topic={topic}, article_type={article_type}, audience_adaptation={audience_adaptation}, image_style={image_style}, generate_cover_video={generate_cover_video}, video_aspect_ratio={video_aspect_ratio}")

        blog_service = get_blog_service()
        if not blog_service:
            return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500

        task_manager = get_task_manager()
        task_id = task_manager.create_task()

        _record_task_to_queue(task_id, topic, article_type, 'mini', image_style)

        blog_service.generate_async(
            task_id=task_id,
            topic=topic,
            article_type=article_type,
            target_audience='intermediate',
            audience_adaptation=audience_adaptation,
            target_length='mini',
            source_material=None,
            document_ids=[],
            document_knowledge=[],
            image_style=image_style,
            generate_cover_video=generate_cover_video,
            video_aspect_ratio=video_aspect_ratio,
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


@blog_bp.route('/api/blog/generate/sync', methods=['POST'])
def generate_blog_sync():
    """同步生成长文博客 (适用于短文章或测试)"""
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

        blog_service = get_blog_service()
        if not blog_service:
            return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500

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


@blog_bp.route('/api/blog/enhance-topic', methods=['POST'])
def enhance_topic():
    """优化用户输入的主题（Prompt 增强）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400

        topic = data.get('topic', '').strip()
        if not topic:
            return jsonify({'success': False, 'error': '请提供 topic 参数'}), 400

        blog_service = get_blog_service()
        if not blog_service:
            return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500

        enhanced = blog_service.enhance_topic(topic)

        return jsonify({
            'success': True,
            'enhanced_topic': enhanced or topic,
            'original': topic,
        })

    except Exception as e:
        logger.error(f"主题优化失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@blog_bp.route('/api/tasks/<task_id>/resume', methods=['POST'])
def resume_task(task_id):
    """恢复中断的任务（101.113 LangGraph interrupt 方案）"""
    try:
        data = request.get_json() or {}
        action = data.get('action', 'accept')
        outline = data.get('outline', None)
        clarification_responses = data.get('clarification_responses', None)

        if action not in ('accept', 'edit', 'clarify_response'):
            return jsonify({'success': False, 'error': 'action 必须是 accept、edit 或 clarify_response'}), 400

        if action == 'edit' and not outline:
            return jsonify({'success': False, 'error': 'edit 操作需要提供 outline'}), 400

        if action == 'clarify_response' and not clarification_responses:
            return jsonify({'success': False, 'error': 'clarify_response 操作需要提供 clarification_responses'}), 400

        blog_service = get_blog_service()
        if not blog_service:
            return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500

        success = blog_service.resume_generation(
            task_id, action=action, outline=outline,
            clarification_responses=clarification_responses,
        )
        if not success:
            return jsonify({'success': False, 'error': '任务不存在或未在等待确认'}), 404

        return jsonify({'success': True, 'message': '任务已恢复'})

    except Exception as e:
        logger.error(f"任务恢复失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@blog_bp.route('/api/tasks/<task_id>/confirm-outline', methods=['POST'])
def confirm_outline(task_id):
    """确认大纲 — 兼容旧接口，内部转发到 resume"""
    return resume_task(task_id)


@blog_bp.route('/api/blog/<blog_id>/evaluate', methods=['POST'])
def evaluate_article(blog_id):
    """评估文章质量"""
    try:
        db_service = get_db_service()
        blog = db_service.get_history(blog_id)
        if not blog:
            return jsonify({'success': False, 'error': '文章不存在'}), 404

        blog_service = get_blog_service()
        if not blog_service:
            return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500

        content = blog.get('markdown_content', '') or blog.get('content', '')
        title = blog.get('topic', '') or blog.get('title', '')
        article_type = blog.get('article_type', '')

        evaluation = blog_service.evaluate_article(content, title=title, article_type=article_type)

        return jsonify({
            'success': True,
            'evaluation': evaluation,
        })

    except Exception as e:
        logger.error(f"文章评估失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
