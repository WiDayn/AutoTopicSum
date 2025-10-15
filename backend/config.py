"""配置文件"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """基础配置"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5001))
    
    # 硅基流动 API 配置
    SILICONFLOW_API_KEY = os.getenv('SILICONFLOW_API_KEY', '')
    SILICONFLOW_API_URL = 'https://api.siliconflow.cn/v1/chat/completions'
    SILICONFLOW_MODEL = 'deepseek-ai/DeepSeek-R1-0528-Qwen3-8B'
    
    # 媒体分析缓存配置
    MEDIA_CACHE_FILE = os.getenv('MEDIA_CACHE_FILE', 'data/media_cache.json')


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

