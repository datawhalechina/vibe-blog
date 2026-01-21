import os
import logging
from flask import Blueprint, jsonify, request, send_from_directory

from services import (
    get_image_service, AspectRatio, ImageSize, STORYBOOK_STYLE_PREFIX
)
from services.image_styles import get_style_manager

logger = logging.getLogger(__name__)

bp = Blueprint('media', __name__)

def get_outputs_folder():
    # backend/api/routes/pages.py -> backend/outputs
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(current_dir))
    return os.path.join(backend_dir, 'outputs')

@bp.route('/api/generate-image', methods=['POST'])
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

# 提供 outputs 目录下的图片文件
@bp.route('/outputs/images/<path:filename>')
@bp.route('/static/chapter/outputs/images/<path:filename>')  # Docsify 章节页面中的图片路径
def serve_output_image(filename):
    images_folder = os.path.join(get_outputs_folder(), 'images')
    return send_from_directory(images_folder, filename)

# 提供 outputs 目录下的封面图片
@bp.route('/outputs/covers/<path:filename>')
def serve_output_cover(filename):
    covers_folder = os.path.join(get_outputs_folder(), 'covers')
    return send_from_directory(covers_folder, filename)

# 提供 outputs 目录下的视频文件
@bp.route('/outputs/videos/<path:filename>')
def serve_output_video(filename):
    videos_folder = os.path.join(get_outputs_folder(), 'videos')
    return send_from_directory(videos_folder, filename)
