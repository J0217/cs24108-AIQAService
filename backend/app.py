# -*- coding: utf-8 -*-
"""
AI智能问答客服平台 - Flask应用主入口
功能：小程序对话接口、统一API接口、AI智能回复生成、公告推送
"""
import os
from flask import Flask, request, render_template
from flask_cors import CORS
from datetime import datetime
import logging

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name=None):
    """
    工厂模式创建Flask应用
    :param config_name: 配置名称 (development/production/testing)
    :return: Flask应用实例
    """
    app = Flask(__name__, template_folder='../templates', static_folder='../static')

    # 加载配置
    config_class = get_config_class(config_name)
    app.config.from_object(config_class)

    # 启用CORS，支持多端调用
    CORS(app, supports_credentials=True)

    # 注册蓝图
    from .routes import auth, chat, announcement, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(announcement.bp)
    app.register_blueprint(api.bp)

    # 初始化数据库（创建表）
    from .models import db, User, Conversation, Message, Announcement, UserAnnouncement, QuickReply
    db.connect()
    db.create_tables([
        User, Conversation, Message,
        Announcement, UserAnnouncement, QuickReply
    ], safe=True)

    logger.info('AI问答客服平台启动成功!')
    return app


def get_config_class(config_name):
    """根据配置名称返回对应的配置类"""
    import importlib.util
    config_mapping = {
        'development': 'DevelopmentConfig',
        'production': 'ProductionConfig',
        'testing': 'TestingConfig'
    }
    config_class_name = config_mapping.get(config_name, 'DevelopmentConfig')
    # 从backend目录下加载config模块
    spec = importlib.util.spec_from_file_location(
        "config",
        os.path.join(os.path.dirname(__file__), 'config.py')
    )
    cfg_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg_module)
    return getattr(cfg_module, config_class_name)


# 命令行启动入口
if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=5000, debug=True)
