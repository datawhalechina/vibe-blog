"""
Banana Vibe Blog 后端配置文件
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
