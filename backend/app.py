"""
vibe-blog 后端应用入口
技术科普绘本生成器
"""
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in stripped test envs
    def load_dotenv(*args, **kwargs):
        return False

from logging_config import setup_logging

# 加载 .env 文件
load_dotenv()

# 提前初始化基础日志，避免启动早期日志丢失
setup_logging(os.getenv('LOG_LEVEL', 'INFO'))

from api import create_app

# 创建应用实例
app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
