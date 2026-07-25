"""
静态文件和页面路由
/, /xhs.html, /reviewer, /outputs/*, /api/config, /api-docs
"""
import os
import re
import logging

from flask import Blueprint, Response, current_app, jsonify, request, send_from_directory

from services.database_service import get_db_service

logger = logging.getLogger(__name__)

static_bp = Blueprint('static', __name__)

# 静态文件目录
_static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')


def _serve_output(directory, filename):
    folders = [current_app.config['OUTPUT_FOLDER']]
    legacy = current_app.config.get('LEGACY_OUTPUT_FOLDER')
    if legacy and legacy not in folders:
        folders.append(legacy)
    for folder in folders:
        candidate = os.path.join(folder, directory, filename)
        if os.path.isfile(candidate):
            return send_from_directory(os.path.join(folder, directory), filename)
    return send_from_directory(os.path.join(folders[0], directory), filename)


@static_bp.route('/')
def index():
    return send_from_directory(_static_folder, 'index.html')


@static_bp.route('/xhs.html')
def xhs_page():
    return send_from_directory(_static_folder, 'xhs.html')


@static_bp.route('/reviewer')
def reviewer_page():
    if os.environ.get('REVIEWER_ENABLED', 'false').lower() != 'true':
        return jsonify({'error': 'vibe-reviewer 功能未启用'}), 403
    return send_from_directory(_static_folder, 'reviewer.html')


@static_bp.route('/home.md')
def book_reader_home():
    return send_from_directory(_static_folder, 'home.md')


@static_bp.route('/_sidebar.md')
@static_bp.route('/static/_sidebar.md')
def book_reader_sidebar():
    book_id = request.args.get('book_id')
    referrer = request.referrer
    logger.info(f"_sidebar.md 请求: book_id={book_id}, referrer={referrer}")
    if not book_id and referrer:
        match = re.search(r'[?&]id=([^&#]+)', referrer)
        if match:
            book_id = match.group(1)
            logger.info(f"从 Referer 提取到 book_id: {book_id}")
    if book_id and book_id.endswith('.md'):
        book_id = book_id[:-3]
    if book_id:
        try:
            db_service = get_db_service()
            book = db_service.get_book(book_id)
            if book:
                chapters = db_service.get_book_chapters(book_id)
                md = f"- [**第 0 章 导读**](/)\n"

                chapter_groups = {}
                for chapter in chapters:
                    idx = chapter.get('chapter_index', 0)
                    title = chapter.get('chapter_title', '未分类')
                    if idx not in chapter_groups:
                        chapter_groups[idx] = {'title': title, 'sections': []}
                    chapter_groups[idx]['sections'].append(chapter)

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


@static_bp.route('/chapter/<path:chapter_path>')
@static_bp.route('/chapter/<path:chapter_path>.md')
@static_bp.route('/static/chapter/<path:chapter_path>')
@static_bp.route('/static/chapter/<path:chapter_path>.md')
def book_reader_chapter(chapter_path):
    return Response('# 加载中...', mimetype='text/markdown')


@static_bp.route('/outputs/images/<path:filename>')
@static_bp.route('/static/chapter/outputs/images/<path:filename>')
def serve_output_image(filename):
    return _serve_output('images', filename)


@static_bp.route('/outputs/covers/<path:filename>')
def serve_output_cover(filename):
    return _serve_output('covers', filename)


@static_bp.route('/outputs/videos/<path:filename>')
def serve_output_video(filename):
    return _serve_output('videos', filename)


@static_bp.route('/api-docs')
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
    return Response(html, content_type='text/html; charset=utf-8')


@static_bp.route('/api/config', methods=['GET'])
def get_frontend_config():
    """获取前端配置"""
    return jsonify({
        'success': True,
        'config': {
            'features': {
                'reviewer': os.environ.get('REVIEWER_ENABLED', 'false').lower() == 'true',
                'book_scan': os.environ.get('BOOK_SCAN_ENABLED', 'false').lower() == 'true',
                'cover_video': os.environ.get('COVER_VIDEO_ENABLED', 'true').lower() == 'true',
                'xhs_tab': os.environ.get('XHS_TAB_ENABLED', 'false').lower() == 'true',
            },
            'reviewer_enabled': os.environ.get('REVIEWER_ENABLED', 'false').lower() == 'true',
            'book_scan_enabled': os.environ.get('BOOK_SCAN_ENABLED', 'false').lower() == 'true'
        }
    })
