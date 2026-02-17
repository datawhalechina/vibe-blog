"""
设置 REST API — Flask Blueprint

接口：
- GET  /api/settings       获取所有可配置项的当前值
- PUT  /api/settings       批量更新配置（运行时覆盖 os.environ）
"""
import os
import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

# 可前端配置的环境变量白名单（key → 元数据）
# type: str / int / bool / select
# tab: model / search / generation / agent / feature
SETTINGS_SCHEMA = {
    # ── 模型 ──
    'TEXT_MODEL': {
        'tab': 'model', 'type': 'str', 'label': '文本模型',
        'default': 'qwen3-max-preview',
    },
    'DEFAULT_LLM_PROVIDER': {
        'tab': 'model', 'type': 'select', 'label': 'LLM 提供商',
        'default': 'openai',
        'options': ['openai', 'anthropic', 'deepseek', 'dashscope', 'zhipu'],
    },
    'IMAGE_CAPTION_MODEL': {
        'tab': 'model', 'type': 'str', 'label': '多模态模型',
        'default': 'qwen3-vl-plus-2025-12-19',
    },
    'LLM_MAX_TOKENS': {
        'tab': 'model', 'type': 'int', 'label': '最大生成 Token',
        'default': 8192, 'min': 1024, 'max': 65536,
    },

    # ── 搜索 ──
    'SMART_SEARCH_ENABLED': {
        'tab': 'search', 'type': 'bool', 'label': '智能搜索',
        'default': True,
    },
    'AI_BOOST_ENABLED': {
        'tab': 'search', 'type': 'bool', 'label': 'AI 增强搜索',
        'default': True,
    },
    'MULTI_ROUND_SEARCH_ENABLED': {
        'tab': 'search', 'type': 'bool', 'label': '多轮搜索',
        'default': True,
    },
    'ZAI_SEARCH_MAX_RESULTS': {
        'tab': 'search', 'type': 'int', 'label': '智谱搜索结果数',
        'default': 5, 'min': 1, 'max': 20,
    },
    'ZAI_SEARCH_RECENCY_FILTER': {
        'tab': 'search', 'type': 'select', 'label': '时间过滤',
        'default': 'noLimit',
        'options': ['noLimit', 'oneDay', 'oneWeek', 'oneMonth', 'threeMonths', 'oneYear'],
    },
    'SERPER_MAX_RESULTS': {
        'tab': 'search', 'type': 'int', 'label': 'Google 搜索结果数',
        'default': 10, 'min': 1, 'max': 30,
    },
    'DEEP_SCRAPE_ENABLED': {
        'tab': 'search', 'type': 'bool', 'label': 'Jina 深度抓取',
        'default': False,
    },
    'DEEP_SCRAPE_TOP_N': {
        'tab': 'search', 'type': 'int', 'label': '抓取 Top N',
        'default': 3, 'min': 1, 'max': 10,
    },

    # ── 生成 ──
    'BLOG_GENERATOR_MAX_WORKERS': {
        'tab': 'generation', 'type': 'int', 'label': '并行生成数',
        'default': 3, 'min': 1, 'max': 8,
    },
    'THINKING_ENABLED': {
        'tab': 'generation', 'type': 'bool', 'label': '推理引擎深度思考',
        'default': False,
    },
    'THINKING_BUDGET_TOKENS': {
        'tab': 'generation', 'type': 'int', 'label': '思考预算 Token',
        'default': 19000, 'min': 1000, 'max': 100000,
    },
    'CONTEXT_COMPRESSION_ENABLED': {
        'tab': 'generation', 'type': 'bool', 'label': '上下文压缩',
        'default': True,
    },

    # ── Agent ──
    'HUMANIZER_ENABLED': {
        'tab': 'agent', 'type': 'bool', 'label': '人性化润色',
        'default': True,
    },
    'FACTCHECK_ENABLED': {
        'tab': 'agent', 'type': 'bool', 'label': '事实核查',
        'default': True,
    },
    'FACTCHECK_AUTO_FIX': {
        'tab': 'agent', 'type': 'bool', 'label': '自动修复',
        'default': True,
    },
    'TEXT_CLEANUP_ENABLED': {
        'tab': 'agent', 'type': 'bool', 'label': '文本清理',
        'default': True,
    },
    'SUMMARY_GENERATOR_ENABLED': {
        'tab': 'agent', 'type': 'bool', 'label': '摘要生成',
        'default': True,
    },
    'THREAD_CHECK_ENABLED': {
        'tab': 'agent', 'type': 'bool', 'label': '行文逻辑检查',
        'default': True,
    },
    'VOICE_CHECK_ENABLED': {
        'tab': 'agent', 'type': 'bool', 'label': '语气一致性检查',
        'default': True,
    },

    # ── 功能 ──
    'COVER_VIDEO_ENABLED': {
        'tab': 'feature', 'type': 'bool', 'label': '封面动画',
        'default': True,
    },
    'XHS_TAB_ENABLED': {
        'tab': 'feature', 'type': 'bool', 'label': '小红书 Tab',
        'default': False,
    },
    'REVIEWER_ENABLED': {
        'tab': 'feature', 'type': 'bool', 'label': 'Reviewer 页面',
        'default': False,
    },
    'BOOK_SCAN_ENABLED': {
        'tab': 'feature', 'type': 'bool', 'label': '书籍扫描',
        'default': False,
    },
    'IMAGE_ENHANCEMENT_ENABLED': {
        'tab': 'feature', 'type': 'bool', 'label': '配图增强',
        'default': False,
    },
    'IMAGE_REFINE_ENABLED': {
        'tab': 'feature', 'type': 'bool', 'label': '配图精修',
        'default': False,
    },
    'IMAGE_REFINE_MAX_ROUNDS': {
        'tab': 'feature', 'type': 'int', 'label': '精修轮数',
        'default': 2, 'min': 1, 'max': 5,
    },
}


def _get_current_value(key: str, meta: dict):
    """从 os.environ 读取当前值，按类型转换"""
    raw = os.environ.get(key)
    if raw is None:
        return meta['default']

    t = meta['type']
    if t == 'bool':
        return raw.lower() in ('true', '1', 'yes')
    elif t == 'int':
        try:
            return int(raw)
        except (ValueError, TypeError):
            return meta['default']
    else:
        return raw


@settings_bp.route('', methods=['GET'])
def get_settings():
    """获取所有可配置项"""
    settings = {}
    for key, meta in SETTINGS_SCHEMA.items():
        settings[key] = {
            **meta,
            'value': _get_current_value(key, meta),
        }
    return jsonify({'success': True, 'settings': settings})


@settings_bp.route('', methods=['PUT'])
def update_settings():
    """批量更新配置（运行时覆盖 os.environ）"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求体为空'}), 400

    updated = []
    errors = []

    for key, value in data.items():
        if key not in SETTINGS_SCHEMA:
            errors.append(f'{key}: 不在白名单中')
            continue

        meta = SETTINGS_SCHEMA[key]
        t = meta['type']

        # 类型校验
        if t == 'bool':
            if not isinstance(value, bool):
                errors.append(f'{key}: 需要 bool 类型')
                continue
            os.environ[key] = str(value).lower()
        elif t == 'int':
            if not isinstance(value, (int, float)):
                errors.append(f'{key}: 需要 int 类型')
                continue
            v = int(value)
            if 'min' in meta and v < meta['min']:
                errors.append(f'{key}: 最小值 {meta["min"]}')
                continue
            if 'max' in meta and v > meta['max']:
                errors.append(f'{key}: 最大值 {meta["max"]}')
                continue
            os.environ[key] = str(v)
        elif t == 'select':
            if 'options' in meta and value not in meta['options']:
                errors.append(f'{key}: 可选值 {meta["options"]}')
                continue
            os.environ[key] = str(value)
        else:
            os.environ[key] = str(value)

        updated.append(key)

    logger.info(f"设置已更新: {updated}")
    if errors:
        logger.warning(f"设置更新错误: {errors}")

    return jsonify({
        'success': True,
        'updated': updated,
        'errors': errors,
    })
