"""
书籍管理路由
/api/books/...
"""
import json
import logging

from flask import Blueprint, jsonify, request

from services import get_llm_service, get_search_service
from services.database_service import get_db_service

logger = logging.getLogger(__name__)

book_bp = Blueprint('book', __name__)


@book_bp.route('/api/books', methods=['GET'])
def list_books():
    """获取书籍列表"""
    try:
        db_service = get_db_service()
        status = request.args.get('status', 'active')
        limit = request.args.get('limit', 50, type=int)

        books = db_service.list_books(status=status, limit=limit)

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


@book_bp.route('/api/books/<book_id>', methods=['GET'])
def get_book(book_id):
    """获取书籍详情"""
    try:
        db_service = get_db_service()
        book = db_service.get_book(book_id)

        if not book:
            return jsonify({'success': False, 'error': '书籍不存在'}), 404

        if book.get('outline'):
            try:
                book['outline'] = json.loads(book['outline'])
            except json.JSONDecodeError:
                book['outline'] = None

        book['chapters'] = db_service.get_book_chapters(book_id)

        return jsonify({'success': True, 'book': book})
    except Exception as e:
        logger.error(f"获取书籍详情失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@book_bp.route('/api/books/<book_id>/chapters/<chapter_id>', methods=['GET'])
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


@book_bp.route('/api/books/regenerate', methods=['POST'])
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


@book_bp.route('/api/books/<book_id>/rescan', methods=['POST'])
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


@book_bp.route('/api/books/<book_id>/generate-intro', methods=['POST'])
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


@book_bp.route('/api/books/<book_id>/generate-cover', methods=['POST'])
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


@book_bp.route('/api/books/generate-all-covers', methods=['POST'])
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


@book_bp.route('/api/books/<book_id>', methods=['DELETE'])
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


@book_bp.route('/api/books/<book_id>/generate-homepage', methods=['POST'])
def generate_book_homepage(book_id):
    """生成书籍首页内容"""
    try:
        from services.outline_expander_service import OutlineExpanderService
        from services.homepage_generator_service import HomepageGeneratorService

        db_service = get_db_service()
        llm_service = get_llm_service()
        search_service = get_search_service()

        outline_expander = OutlineExpanderService(db_service, llm_service, search_service)
        homepage_service = HomepageGeneratorService(db_service, llm_service, outline_expander)

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


@book_bp.route('/api/books/<book_id>/expand-outline', methods=['POST'])
def expand_book_outline(book_id):
    """扩展书籍大纲"""
    try:
        from services.outline_expander_service import OutlineExpanderService

        db_service = get_db_service()
        llm_service = get_llm_service()
        search_service = get_search_service()

        outline_expander = OutlineExpanderService(db_service, llm_service, search_service)

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


@book_bp.route('/api/blogs/with-book-info', methods=['GET'])
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
