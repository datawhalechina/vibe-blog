"""
Blueprint 路由注册。

避免在包导入时急切加载所有 route 模块；测试里经常只 monkeypatch 其中一个模块，
这里保持懒加载以减少副作用。
"""


def register_all_blueprints(app):
    """注册所有 Blueprint 到 Flask 应用"""
    from api.routes.static_routes import static_bp
    from api.routes.transform_routes import transform_bp
    from api.routes.task_routes import task_bp
    from api.routes.blog_routes import blog_bp
    from api.routes.history_routes import history_bp
    from api.routes.book_routes import book_bp
    from api.routes.xhs_routes import xhs_bp
    from api.routes.publish_routes import publish_bp
    from api.routes.queue_routes import queue_bp
    from api.routes.scheduler_routes import scheduler_bp
    from api.routes.chat_routes import chat_bp
    from api.routes.feishu_routes import feishu_bp
    from api.routes.settings_routes import settings_bp

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
