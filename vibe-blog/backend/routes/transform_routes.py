"""
内容转化路由
/api/transform, /api/generate-image, /api/image-styles, /api/metaphors, /api/transform-with-images
"""
import logging

from flask import Blueprint, jsonify, request

from services import (
    get_llm_service, create_transform_service,
    get_image_service, AspectRatio, ImageSize, STORYBOOK_STYLE_PREFIX,
)
from services.image_styles import get_style_manager

logger = logging.getLogger(__name__)

transform_bp = Blueprint('transform', __name__)


@transform_bp.route('/api/transform', methods=['POST'])
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

        llm_service = get_llm_service()
        if not llm_service or not llm_service.is_available():
            return jsonify({'success': False, 'error': 'LLM 服务不可用，请检查 API Key 配置'}), 500

        transform_service = create_transform_service(llm_service)

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


@transform_bp.route('/api/metaphors', methods=['GET'])
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


@transform_bp.route('/api/image-styles', methods=['GET'])
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


@transform_bp.route('/api/generate-image', methods=['POST'])
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

        aspect_ratio_str = data.get('aspect_ratio', '16:9')
        image_size_str = data.get('image_size', '2K')
        image_style = data.get('image_style', '')
        use_style = data.get('use_style', True)
        download = data.get('download', True)

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

        if image_style:
            style_manager = get_style_manager()
            full_prompt = style_manager.render_prompt(image_style, prompt)
            result = image_service.generate(
                prompt=full_prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                download=download
            )
        else:
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


@transform_bp.route('/api/transform-with-images', methods=['POST'])
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

        llm_service = get_llm_service()
        if not llm_service or not llm_service.is_available():
            return jsonify({'success': False, 'error': 'LLM 服务不可用'}), 500

        transform_service = create_transform_service(llm_service)

        result = transform_service.transform(
            content=content,
            title=title,
            target_audience=target_audience,
            style=style,
            page_count=page_count
        )

        if not result['success']:
            return jsonify(result), 500

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
