import os
import logging
import re
from flask import Blueprint, send_from_directory, request, Response, jsonify, current_app

from services.database_service import get_db_service

logger = logging.getLogger(__name__)

bp = Blueprint('pages', __name__)

def get_static_folder():
    # backend/api/routes/pages.py -> backend/static
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(current_dir))
    return os.path.join(backend_dir, 'static')

@bp.route('/')
def index():
    return send_from_directory(get_static_folder(), 'index.html')

@bp.route('/reviewer')
def reviewer_page():
    # Check if feature is enabled
    # We can check env var directly or via config
    if os.environ.get('REVIEWER_ENABLED', 'false').lower() != 'true':
        return jsonify({'error': 'vibe-reviewer 功能未启用'}), 403
    return send_from_directory(get_static_folder(), 'reviewer.html')

@bp.route('/home.md')
def book_reader_home():
    return send_from_directory(get_static_folder(), 'home.md')

@bp.route('/_sidebar.md')
@bp.route('/static/_sidebar.md')
def book_reader_sidebar():
    book_id = request.args.get('book_id')
    referrer = request.referrer
    logger.info(f"_sidebar.md 请求: book_id={book_id}, referrer={referrer}")
    if not book_id and referrer:
        # 从 Referer 中提取 book_id
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

@bp.route('/chapter/<path:chapter_path>')
@bp.route('/chapter/<path:chapter_path>.md')
@bp.route('/static/chapter/<path:chapter_path>')
@bp.route('/static/chapter/<path:chapter_path>.md')
def book_reader_chapter(chapter_path):
    # 返回一个占位符，实际内容由前端 beforeEach 钩子处理
    return Response('# 加载中...', mimetype='text/markdown')
