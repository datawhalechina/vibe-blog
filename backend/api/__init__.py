import os
import logging
from flask import Flask
from flask_cors import CORS

from config import get_config
from services import (
    init_llm_service, init_image_service, init_blog_service, init_search_service,
    get_search_service, get_llm_service, get_image_service
)
from services.oss_service import init_oss_service, get_oss_service
from services.video_service import init_video_service, get_video_service
from services.database_service import init_db_service
from services.file_parser_service import init_file_parser
from services.knowledge_service import init_knowledge_service, get_knowledge_service

# Import Blueprints
from api.routes import blog, media, tasks, knowledge, system, pages

logger = logging.getLogger(__name__)

def create_app(config_class=None):
    """创建 Flask 应用"""
    app = Flask(__name__, 
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
    
    # 加载配置
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    
    # 设置日志级别
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    logging.getLogger().setLevel(log_level)
    
    # CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    
    # 确保目录存在
    try:
        os.makedirs(app.config.get('OUTPUT_FOLDER', 'outputs'), exist_ok=True)
        os.makedirs(os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'images'), exist_ok=True)
        os.makedirs(os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'videos'), exist_ok=True)
    except (OSError, IOError):
        pass
    
    # 初始化各种服务
    init_services(app)
    
    # 注册 Blueprints
    register_blueprints(app)
    
    logger.info("Vibe Blog 后端应用已启动")
    return app

def init_services(app):
    """初始化应用服务"""
    # 1. LLM
    init_llm_service(app.config)
    
    # 2. Image
    app.config['IMAGE_OUTPUT_FOLDER'] = os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'images')
    init_image_service(app.config)
    
    # 3. OSS
    init_oss_service(app.config)
    oss_service = get_oss_service()
    if oss_service and oss_service.is_available:
        logger.info("OSS 服务已初始化")
    else:
        logger.warning("OSS 服务不可用，封面动画功能将受限")
        
    # 4. Video
    init_video_service(app.config)
    video_service = get_video_service()
    if video_service and video_service.is_available():
        logger.info("视频生成服务已初始化")
    else:
        logger.warning("视频生成服务不可用")
        
    # 5. DB & Knowledge
    init_db_service()
    init_knowledge_service(
        max_content_length=app.config.get('KNOWLEDGE_MAX_CONTENT_LENGTH', 8000)
    )
    
    # 6. Search & Blog
    try:
        init_search_service(app.config)
        search_service = get_search_service()
        if search_service and search_service.is_available():
            logger.info("智谱搜索服务已初始化")
        else:
            logger.warning("智谱搜索服务不可用，Researcher Agent 将跳过联网搜索")
            
        llm_service = get_llm_service()
        knowledge_service = get_knowledge_service()
        if llm_service and llm_service.is_available():
            init_blog_service(llm_service, search_service, knowledge_service)
            logger.info("博客生成服务已初始化（含知识融合支持）")
    except Exception as e:
        logger.warning(f"博客生成服务初始化失败: {e}")
        
    # 7. File Parser
    mineru_token = app.config.get('MINERU_TOKEN', '')
    if mineru_token:
        # Uploads relative to backend root
        upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        try:
            os.makedirs(upload_folder, exist_ok=True)
        except (OSError, IOError):
             # Vercel fallback
            import tempfile
            upload_folder = tempfile.gettempdir()
            logger.warning(f"无法创建 uploads 目录，使用临时目录: {upload_folder}")
        
        init_file_parser(
            mineru_token=mineru_token,
            mineru_api_base=app.config.get('MINERU_API_BASE', 'https://mineru.net'),
            upload_folder=upload_folder,
            pdf_max_pages=int(os.getenv('PDF_MAX_PAGES', '15'))
        )
        logger.info("文件解析服务已初始化")
    else:
        logger.warning("MINERU_TOKEN 未配置，PDF 解析功能不可用")

    # 8. Reviewer (Optional)
    if os.environ.get('REVIEWER_ENABLED', 'false').lower() == 'true':
        try:
            from vibe_reviewer import init_reviewer_service
            
            reviewer_search_service = None
            try:
                reviewer_search_service = get_search_service()
            except:
                pass
                
            init_reviewer_service(
                llm_service=get_llm_service(),
                search_service=reviewer_search_service,
            )
            # Reviewer routes are registered in register_blueprints via special handling or just here?
            # Reviewer module usually has its own register function.
            # In original app.py: register_reviewer_routes(app)
            # We will handle this in register_blueprints
            logger.info("vibe-reviewer 模块已初始化")
        except Exception as e:
            logger.warning(f"vibe-reviewer 模块初始化失败: {e}")

def register_blueprints(app):
    """注册路由蓝图"""
    app.register_blueprint(blog.bp)
    app.register_blueprint(media.bp)
    app.register_blueprint(tasks.bp)
    app.register_blueprint(knowledge.bp)
    app.register_blueprint(system.bp)
    app.register_blueprint(pages.bp)
    
    # Reviewer Routes (External module)
    if os.environ.get('REVIEWER_ENABLED', 'false').lower() == 'true':
        try:
            from vibe_reviewer.api import register_reviewer_routes
            register_reviewer_routes(app)
        except ImportError:
            pass
