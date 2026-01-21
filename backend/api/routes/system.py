import os
import logging
from flask import Blueprint, jsonify, request, Response

# Services
from services.image_styles import get_style_manager
from services.transform_service import TransformService

logger = logging.getLogger(__name__)

bp = Blueprint('system', __name__)

@bp.route('/health')
def health_check():
    return {'status': 'ok', 'service': 'banana-blog'}

@bp.route('/api/config', methods=['GET'])
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

@bp.route('/api/metaphors', methods=['GET'])
def get_metaphors():
    """获取比喻库"""
    metaphors = []
    for concept, (metaphor, explanation) in TransformService.METAPHOR_LIBRARY.items():
        metaphors.append({
            'concept': concept,
            'metaphor': metaphor,
            'explanation': explanation
        })
    return jsonify({'success': True, 'metaphors': metaphors})

@bp.route('/api/image-styles', methods=['GET'])
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

@bp.route('/api-docs')
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
