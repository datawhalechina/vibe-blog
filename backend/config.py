"""
vibe-blog 后端配置文件
技术科普绘本生成器
"""
import os
from datetime import timedelta

# 基础路径配置
_current_file = os.path.realpath(__file__)
BASE_DIR = os.path.dirname(_current_file)
PROJECT_ROOT = os.path.dirname(BASE_DIR)


class Config:
    """基础配置"""
    # Flask 配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'banana-blog-secret-key')
    
    # 文件存储配置
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    
    # AI 配置（从 .env 读取）
    AI_PROVIDER_FORMAT = os.getenv('AI_PROVIDER_FORMAT', 'openai')
    TEXT_MODEL = os.getenv('TEXT_MODEL', 'qwen3-max-preview')
    
    # OpenAI 兼容 API（用于文本生成）
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # CORS 配置
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Prompt 模板目录
    PROMPTS_DIR = os.path.join(BASE_DIR, 'services', 'blog_generator', 'templates')
    
    # Nano Banana 图片生成 API
    NANO_BANANA_API_KEY = os.getenv('NANO_BANANA_API_KEY', '')
    NANO_BANANA_API_BASE = os.getenv('NANO_BANANA_API_BASE', 'https://api.grsai.com')
    NANO_BANANA_MODEL = os.getenv('NANO_BANANA_MODEL', 'nano-banana-pro')
    
    # 智谱 Web Search API
    ZAI_SEARCH_API_KEY = os.getenv('ZAI_SEARCH_API_KEY', '')
    ZAI_SEARCH_API_BASE = os.getenv('ZAI_SEARCH_API_BASE', 'https://open.bigmodel.cn/api/paas/v4/web_search')
    ZAI_SEARCH_ENGINE = os.getenv('ZAI_SEARCH_ENGINE', 'search_pro_quark')
    ZAI_SEARCH_MAX_RESULTS = int(os.getenv('ZAI_SEARCH_MAX_RESULTS', '5'))
    ZAI_SEARCH_CONTENT_SIZE = os.getenv('ZAI_SEARCH_CONTENT_SIZE', 'medium')
    ZAI_SEARCH_RECENCY_FILTER = os.getenv('ZAI_SEARCH_RECENCY_FILTER', 'noLimit')
    
    # MinerU PDF 解析 API
    MINERU_TOKEN = os.getenv('MINERU_TOKEN', '')
    MINERU_API_BASE = os.getenv('MINERU_API_BASE', 'https://mineru.net')
    
    # 知识融合配置
    KNOWLEDGE_MAX_CONTENT_LENGTH = int(os.getenv('KNOWLEDGE_MAX_CONTENT_LENGTH', '8000'))
    KNOWLEDGE_MAX_DOC_ITEMS = int(os.getenv('KNOWLEDGE_MAX_DOC_ITEMS', '10'))  # 文档知识最大条目数
    KNOWLEDGE_CHUNK_SIZE = int(os.getenv('KNOWLEDGE_CHUNK_SIZE', '2000'))  # 知识分块大小（字符）
    KNOWLEDGE_CHUNK_OVERLAP = int(os.getenv('KNOWLEDGE_CHUNK_OVERLAP', '200'))  # 分块重叠大小
    
    # 多模态模型配置（用于图片摘要）
    IMAGE_CAPTION_MODEL = os.getenv('IMAGE_CAPTION_MODEL', 'qwen3-vl-plus-2025-12-19')
    
    # 阿里云 OSS 配置 (用于上传图片获取公网 URL)
    OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')
    OSS_ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', '')
    OSS_BUCKET_NAME = os.getenv('OSS_BUCKET_NAME', '')
    OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', 'oss-cn-hangzhou.aliyuncs.com')
    
    # Veo3 视频生成配置
    VEO3_MODEL = os.getenv('VEO3_MODEL', 'veo3.1-fast')
    VIDEO_OUTPUT_FOLDER = os.getenv('VIDEO_OUTPUT_FOLDER', '')
    
    # 小红书 Tab 配置
    XHS_TAB_ENABLED = os.getenv('XHS_TAB_ENABLED', 'false').lower() == 'true'


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """根据环境变量获取配置"""
    env = os.getenv('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)


# ========== 文章长度配置 ==========

# 文章长度预设配置
ARTICLE_LENGTH_PRESETS = {
    'mini': {
        'sections_count': 4,        # 2-4 个知识点章节
        'images_count': 5,          # 每章节 1 张配图 + 1 张封面图
        'code_blocks_count': 0,
        'target_word_count': 800,
        'description': '精品短文（2-4个知识点章节）'
    },
    'short': {
        'sections_count': 2,
        'images_count': 2,
        'code_blocks_count': 0,
        'target_word_count': 1500,
        'description': '短文（2-3个章节）'
    },
    'medium': {
        'sections_count': 4,
        'images_count': 4,
        'code_blocks_count': 2,
        'target_word_count': 3500,
        'description': '中等长度（4-5个章节）'
    },
    'long': {
        'sections_count': 6,
        'images_count': 8,
        'code_blocks_count': 4,
        'target_word_count': 6000,
        'description': '长文（6-8个章节）'
    }
}

# 自定义模式的验证规则
CUSTOM_CONFIG_LIMITS = {
    'sections_count': {'min': 1, 'max': 12},
    'images_count': {'min': 0, 'max': 20},
    'code_blocks_count': {'min': 0, 'max': 10},
    'target_word_count': {'min': 300, 'max': 15000}
}


def get_article_config(target_length: str, custom_config: dict = None) -> dict:
    """
    获取文章生成配置
    
    Args:
        target_length: 预设长度 (mini/short/medium/long) 或 'custom'
        custom_config: 自定义配置（仅当 target_length='custom' 时使用）
    
    Returns:
        {
            'sections_count': int,
            'images_count': int,
            'code_blocks_count': int,
            'target_word_count': int
        }
    """
    if target_length in ARTICLE_LENGTH_PRESETS:
        config = ARTICLE_LENGTH_PRESETS[target_length].copy()
        return {
            'sections_count': config['sections_count'],
            'images_count': config['images_count'],
            'code_blocks_count': config['code_blocks_count'],
            'target_word_count': config['target_word_count']
        }
    elif target_length == 'custom' and custom_config:
        return validate_custom_config(custom_config)
    else:
        # 默认使用 medium
        config = ARTICLE_LENGTH_PRESETS['medium'].copy()
        return {
            'sections_count': config['sections_count'],
            'images_count': config['images_count'],
            'code_blocks_count': config['code_blocks_count'],
            'target_word_count': config['target_word_count']
        }


def validate_custom_config(custom_config: dict) -> dict:
    """
    验证并返回自定义配置
    
    Args:
        custom_config: 用户提供的自定义配置
        
    Returns:
        验证后的配置字典
        
    Raises:
        ValueError: 如果配置无效
    """
    if not custom_config:
        raise ValueError("自定义配置不能为空")
    
    validated = {}
    errors = []
    
    for key, limits in CUSTOM_CONFIG_LIMITS.items():
        value = custom_config.get(key)
        if value is None:
            # 使用 medium 预设的默认值
            validated[key] = ARTICLE_LENGTH_PRESETS['medium'][key]
        else:
            try:
                value = int(value)
                if value < limits['min'] or value > limits['max']:
                    errors.append(f"{key} 必须在 {limits['min']}-{limits['max']} 之间，当前值: {value}")
                else:
                    validated[key] = value
            except (TypeError, ValueError):
                errors.append(f"{key} 必须是整数，当前值: {value}")
    
    if errors:
        raise ValueError("; ".join(errors))
    
    return validated
