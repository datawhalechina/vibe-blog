"""
vibe-blog 后端应用入口
技术科普绘本生成器
"""
import os
import logging
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from logging_config import setup_logging, task_id_context, get_logger

# 先用环境变量做一次基础日志配置，避免 import 期日志裸奔
setup_logging(os.getenv('LOG_LEVEL', 'INFO'))

# === Langfuse 追踪初始化 ===
_langfuse_handler = None
if os.environ.get('TRACE_ENABLED', 'false').lower() == 'true':
    try:
        from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler

        _langfuse_handler = LangfuseCallbackHandler()
        print("🔍 Langfuse 追踪已启用，打开 Langfuse 控制台查看调用链路")
    except ImportError:
        print("⚠️ TRACE_ENABLED=true 但未安装 Langfuse，请运行: pip install langfuse")
    except Exception as e:
        print(f"⚠️ Langfuse 初始化失败: {e}")


def get_langfuse_handler():
    """获取 Langfuse CallbackHandler（未启用时返回 None）"""
    return _langfuse_handler


from flask import Flask, jsonify
from flask_cors import CORS

from config import get_config
from logging_config import setup_logging, task_id_context
from services import (
    init_llm_service, get_llm_service,
    init_image_service, get_image_service,
    get_search_service,
)
from services.database_service import get_db_service, init_db_service
from services.file_parser_service import get_file_parser, init_file_parser
from services.knowledge_service import init_knowledge_service
from services.oss_service import get_oss_service, init_oss_service
from services.video_service import get_video_service, init_video_service

# 初始化日志
setup_logging()

logger = logging.getLogger(__name__)


def create_app(config_class=None):
    """创建 Flask 应用"""
    app = Flask(__name__)

    # 加载配置
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # 根据配置再次校准日志级别（setup_logging 是幂等的）
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    setup_logging(log_level)

    # CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))

    # 确保目录存在
    try:
        os.makedirs(app.config.get('OUTPUT_FOLDER', 'outputs'), exist_ok=True)
        os.makedirs(os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'images'), exist_ok=True)
    except (OSError, IOError):
        pass

    # 初始化 LLM 服务
    init_llm_service(app.config)

    # 初始化图片生成服务
    app.config['IMAGE_OUTPUT_FOLDER'] = os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'images')
    init_image_service(app.config)

    # 初始化 OSS 服务
    init_oss_service(app.config)
    oss_service = get_oss_service()
    if oss_service and oss_service.is_available:
        logger.info("OSS 服务已初始化")
    else:
        logger.warning("OSS 服务不可用，封面动画功能将受限")

    # 初始化视频生成服务
    try:
        os.makedirs(os.path.join(app.config.get('OUTPUT_FOLDER', 'outputs'), 'videos'), exist_ok=True)
    except (OSError, IOError):
        pass
    init_video_service(app.config)
    video_service = get_video_service()
    if video_service and video_service.is_available():
        logger.info("统一视频生成服务已初始化 (Veo3 + Sora2)")
    else:
        logger.warning("视频生成服务不可用")

    # 初始化知识源相关服务
    init_db_service()
    init_knowledge_service(
        max_content_length=app.config.get('KNOWLEDGE_MAX_CONTENT_LENGTH', 8000)
    )

    # 初始化文件解析服务
    mineru_token = app.config.get('MINERU_TOKEN', '')
    if mineru_token:
        upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
        try:
            os.makedirs(upload_folder, exist_ok=True)
        except (OSError, IOError):
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

    # 初始化博客生成相关服务（搜索 + 博客）
    from routes.blog_routes import init_blog_services
    init_blog_services(app.config)

    # 注册所有 Blueprint
    from routes import register_all_blueprints
    register_all_blueprints(app)

    # 健康检查
    @app.route('/health')
    def health_check():
        return {'status': 'ok', 'service': 'banana-blog'}

    # ========== vibe-reviewer 初始化 ==========
    if os.environ.get('REVIEWER_ENABLED', 'false').lower() != 'true':
        logger.info("vibe-reviewer 功能未启用 (REVIEWER_ENABLED != true)")
    else:
      try:
        from vibe_reviewer import init_reviewer_service, get_reviewer_service
        from vibe_reviewer.api import register_reviewer_routes

        reviewer_search_service = None
        try:
            reviewer_search_service = get_search_service()
            if reviewer_search_service and reviewer_search_service.is_available():
                logger.info("vibe-reviewer 将使用智谱搜索服务进行增强评估")
            else:
                logger.warning("vibe-reviewer 搜索服务不可用，将仅使用 LLM 评估")
                reviewer_search_service = None
        except Exception as e:
            logger.warning(f"获取搜索服务失败: {e}")

        init_reviewer_service(
            llm_service=get_llm_service(),
            search_service=reviewer_search_service,
        )

        register_reviewer_routes(app)

        logger.info("vibe-reviewer 模块已初始化")
      except Exception as e:
        logger.warning(f"vibe-reviewer 模块初始化失败 (可选模块): {e}")

    logger.info("Vibe Blog 后端应用已启动")
    return app


# 开发服务器入口
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
