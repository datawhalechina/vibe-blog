"""
静态兼容、输出文件和配置路由
/xhs.html, /outputs/*, /api/config, /api-docs
"""
import os

from flask import Blueprint, Response, current_app, jsonify, redirect, send_from_directory

static_bp = Blueprint('static', __name__)


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


@static_bp.route('/xhs.html')
def xhs_page():
    return redirect('/xhs', code=308)


@static_bp.route('/outputs/images/<path:filename>')
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
                'book_scan': os.environ.get('BOOK_SCAN_ENABLED', 'false').lower() == 'true',
                'cover_video': os.environ.get('COVER_VIDEO_ENABLED', 'true').lower() == 'true',
                'xhs_tab': os.environ.get('XHS_TAB_ENABLED', 'false').lower() == 'true',
            },
            'book_scan_enabled': os.environ.get('BOOK_SCAN_ENABLED', 'false').lower() == 'true'
        }
    })
