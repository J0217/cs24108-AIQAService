# -*- coding: utf-8 -*-
"""
配置文件 - 支持多环境配置
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

# 加载项目根目录下的 .env（不存在时忽略）
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


class BaseConfig:
    """基础配置"""
    # 数据库配置（SQLite，无需额外安装）
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'ai_qa_service.db')

    # JWT配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # 跨域配置
    CORS_HEADERS = 'Content-Type'

    # AI配置
    AI_API_KEY = os.getenv('AI_API_KEY', 'your-ai-api-key-here')
    AI_API_BASE_URL = os.getenv('AI_API_BASE_URL', 'https://api.openai.com/v1')
    AI_MODEL = os.getenv('AI_MODEL', 'gpt-3.5-turbo')
    AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', 2000))
    AI_TEMPERATURE = float(os.getenv('AI_TEMPERATURE', 0.7))
    AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', 30))
    # 送入大模型的上下文消息条数上限
    AI_HISTORY_LIMIT = int(os.getenv('AI_HISTORY_LIMIT', 10))

    # 对外开放 API 的 Key 列表（逗号分隔）
    API_KEYS = os.getenv('API_KEYS', 'demo-api-key')

    # 限流配置（进程内滑动窗口，单位：次/分钟）
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() != 'false'
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))
    LOGIN_RATE_LIMIT_PER_MINUTE = int(os.getenv('LOGIN_RATE_LIMIT_PER_MINUTE', 10))

    # 支持的问答场景（用于入参白名单校验）
    SCENE_TYPES = ('general', 'product', 'after_sales', 'technical', 'ordering')

    # 文件上传配置
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # 分页配置
    PAGE_SIZE = 20

    # 微信小程序配置
    WX_APPID = os.getenv('WX_APPID', '')
    WX_SECRET = os.getenv('WX_SECRET', '')


class DevelopmentConfig(BaseConfig):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(BaseConfig):
    """生产环境配置"""
    DEBUG = False


class TestingConfig(BaseConfig):
    """测试环境配置"""
    TESTING = True
    # 单测不得依赖 .env 里的真实 Key，也不打外部网络：
    # 清空后 AI 服务统一走本地模板路径，用例结果与是否有 Key 无关
    AI_API_KEY = ''


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
