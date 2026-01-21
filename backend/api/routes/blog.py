import logging
import json
from flask import Blueprint, jsonify, request, current_app

from services import (
    get_llm_service, get_task_manager, get_blog_service
)
from services.database_service import get_db_service

logger = logging.getLogger(__name__)

bp = Blueprint('blog', __name__)

# ========== 长文博客生成 API ==========

@bp.route('/api/blog/generate', methods=['POST'])
def generate_blog():
    """
    创建长文博客生成任务
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
        logger.info(f"📝 博客生成请求: topic={topic}, article_type={article_type}, target_audience={target_audience}, target_length={target_length}, document_ids={document_ids}, generate_cover_video={generate_cover_video}, custom_config={custom_config}")
        
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
        # pass current_app via proxy or get_current_object
        real_app = current_app._get_current_object()
        
        blog_service.generate_async(
            task_id=task_id,
            topic=topic,
            article_type=article_type,
            target_audience=target_audience,
            target_length=target_length,
            source_material=source_material,
            document_ids=document_ids,
            document_knowledge=document_knowledge,
            image_style=image_style,
            generate_cover_video=generate_cover_video,
            custom_config=custom_config,
            task_manager=task_manager,
            app=real_app
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

@bp.route('/api/blog/generate/mini', methods=['POST'])
def generate_blog_mini():
    """
    创建 Mini 版博客生成任务（1个章节，完整流程）
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': '请提供 JSON 数据'}), 400
        
        topic = data.get('topic', '')
        if not topic:
            return jsonify({'success': False, 'error': '请提供 topic 参数'}), 400
        
        article_type = data.get('article_type', 'tutorial')
        generate_cover_video = data.get('generate_cover_video', False)
        
        logger.info(f"📝 Mini 博客生成请求: topic={topic}, article_type={article_type}, generate_cover_video={generate_cover_video}")
        
        # 检查博客生成服务
        blog_service = get_blog_service()
        if not blog_service:
            return jsonify({'success': False, 'error': '博客生成服务不可用'}), 500
        
        # 创建任务
        task_manager = get_task_manager()
        task_id = task_manager.create_task()
        
        # 异步执行生成
        real_app = current_app._get_current_object()
        
        blog_service.generate_async(
            task_id=task_id,
            topic=topic,
            article_type=article_type,
            target_audience='intermediate',
            target_length='mini',  # Mini 版使用 mini 模式
            source_material=None,
            document_ids=[],
            document_knowledge=[],
            image_style='',
            generate_cover_video=generate_cover_video,
            custom_config=None,
            task_manager=task_manager,
            app=real_app
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Mini 博客生成任务已创建（1个章节完整流程），请订阅 /api/tasks/{task_id}/stream 获取进度'
        }), 202
        
    except Exception as e:
        logger.error(f"创建 Mini 博客生成任务失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/blog/generate/sync', methods=['POST'])
def generate_blog_sync():
    """
    同步生成长文博客 (适用于短文章或测试)
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

@bp.route('/api/blogs/with-book-info', methods=['GET'])
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

# ========== 历史记录 API ==========

@bp.route('/api/history', methods=['GET'])
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

@bp.route('/api/history/<history_id>', methods=['GET'])
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

@bp.route('/api/history/<history_id>', methods=['DELETE'])
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
