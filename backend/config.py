# -*- coding: utf-8 -*-
"""
配置文件 - 支持多环境配置
"""
import os
from datetime import timedelta


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
    AI_MAX_TOKENS = 2000
    AI_TEMPERATURE = 0.7

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


# 配置映射
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
