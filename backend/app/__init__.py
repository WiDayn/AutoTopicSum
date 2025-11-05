"""Flask应用工厂"""
import logging
from flask import Flask
from flask_cors import CORS


def create_app(config_name='default'):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 配置日志系统（确保在 Flask reloader 中也能生效）
    if not logging.root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # 加载配置
    from config import config
    app.config.from_object(config[config_name])
    
    # 启用CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # 注册蓝图
    from app.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    logger = logging.getLogger(__name__)
    logger.info(f"Flask 应用初始化完成 (环境: {config_name})")
    
    return app

