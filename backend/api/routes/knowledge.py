import os
import logging
import uuid
import threading
import json
from flask import Blueprint, jsonify, request, current_app

from services.database_service import get_db_service
from services.file_parser_service import get_file_parser
from services.book_scanner_service import BookScannerService
from services import get_llm_service

logger = logging.getLogger(__name__)

bp = Blueprint('knowledge', __name__)

@bp.route('/api/blog/upload', methods=['POST'])
def upload_document():
    """
    上传知识文档
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
        # Use current_app.config or relative path?
        # uploads is usually sibling to static
        # app.py: upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
        # We need to replicate this logic or use config
        upload_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads')
        
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
                chunk_size = current_app.config.get('KNOWLEDGE_CHUNK_SIZE', 2000)
                chunk_overlap = current_app.config.get('KNOWLEDGE_CHUNK_OVERLAP', 200)
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
        
        # Need to capture current app for use inside thread if it uses current_app context?
        # parse_async needs current_app.config. 
        # But current_app is proxy. Inside thread it might fail if context not pushed.
        # But app.py didn't use app context explicitly in thread, 
        # however parse_async used 'app.config' where 'app' was the Flask object in closure.
        # Here we use 'current_app'. We should extract config values outside.
        
        # Better: pass app to thread or use copy_current_request_context (if request context needed, but here app context)
        # We can pass the real app object.
        real_app = current_app._get_current_object()
        
        def parse_async_with_context(app_obj):
            with app_obj.app_context():
                parse_async()

        # Update parse_async to use current_app (which will work inside app_context)
        # Or just pass config dict.
        
        thread = threading.Thread(target=parse_async_with_context, args=(real_app,), daemon=True)
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

@bp.route('/api/blog/upload/<document_id>/status', methods=['GET'])
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

@bp.route('/api/blog/upload/<document_id>', methods=['DELETE'])
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

@bp.route('/api/blog/documents', methods=['GET'])
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

# ========== 书籍 API ==========

@bp.route('/api/books', methods=['GET'])
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

@bp.route('/api/books/<book_id>', methods=['GET'])
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

@bp.route('/api/books/<book_id>/chapters/<chapter_id>', methods=['GET'])
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

@bp.route('/api/books/regenerate', methods=['POST'])
def regenerate_books():
    """重新生成所有书籍（清空旧数据，重新聚合）"""
    try:
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

@bp.route('/api/books/<book_id>/rescan', methods=['POST'])
def rescan_book(book_id):
    """重新扫描单本书籍"""
    try:
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

@bp.route('/api/books/<book_id>/generate-intro', methods=['POST'])
def generate_book_intro(book_id):
    """生成书籍简介"""
    try:
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
