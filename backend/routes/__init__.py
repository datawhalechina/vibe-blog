"""
Blueprint 路由注册
"""
from routes.static_routes import static_bp
from routes.transform_routes import transform_bp
from routes.task_routes import task_bp
from routes.blog_routes import blog_bp
from routes.history_routes import history_bp
from routes.book_routes import book_bp
from routes.xhs_routes import xhs_bp
from routes.publish_routes import publish_bp
from routes.queue_routes import queue_bp
from routes.scheduler_routes import scheduler_bp
from routes.chat_routes import chat_bp
from routes.feishu_routes import feishu_bp
from routes.settings_routes import settings_bp
from routes.memory_routes import memory_bp
from routes.podcast_routes import podcast_bp
from routes.prose_routes import prose_bp
from routes.ppt_routes import ppt_bp
from routes.skills_api import skills_bp


def register_all_blueprints(app):
    """注册所有 Blueprint 到 Flask 应用"""
    app.register_blueprint(static_bp)
    app.register_blueprint(transform_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(book_bp)
    app.register_blueprint(xhs_bp)
    app.register_blueprint(publish_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(feishu_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(memory_bp)
    app.register_blueprint(podcast_bp)
    app.register_blueprint(prose_bp)
    app.register_blueprint(ppt_bp)
    app.register_blueprint(skills_bp)
