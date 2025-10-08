"""Flask应用工厂"""
from flask import Flask
from flask_cors import CORS


def create_app(config_name='default'):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 加载配置
    from config import config
    app.config.from_object(config[config_name])
    
    # 启用CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # 注册蓝图
    from app.routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app

