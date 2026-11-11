# -*- coding: utf-8 -*-
"""
AI智能问答客服平台 - Flask应用主入口
功能：小程序对话接口、统一API接口、AI智能回复生成、公告推送
"""
import os
import sys
import logging

from flask import Flask
from flask_cors import CORS

# 支持 `python backend/app.py` 直接启动（补齐包上下文）
if __package__ in (None, ''):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = 'backend'

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 初始快捷回复模板 ====================
# 首次启动时写入数据库，AI 会按场景 + 关键词 + 问题相似度自动匹配
DEFAULT_QUICK_REPLIES = [
    {
        'question': '如何联系人工客服？',
        'answer': '您可以直接在对话中留言，或拨打客服热线 400-800-1234（服务时间 9:00-21:00），我们会尽快为您服务。',
        'keywords': '人工,转人工,客服电话,联系客服,找客服',
        'scene_type': 'general', 'category': 'service'
    },
    {
        'question': '客服的服务时间是什么时候？',
        'answer': '在线客服服务时间为每天 9:00-21:00，智能助手 7×24 小时在线，随时为您解答常见问题。',
        'keywords': '服务时间,营业时间,工作时间,几点上班,几点下班',
        'scene_type': 'general', 'category': 'service'
    },
    {
        'question': '如何查询订单？',
        'answer': '您可以进入“我的订单”页面查看全部订单，或在对话中提供订单号，我帮您快速查询物流与状态。',
        'keywords': '查询订单,订单号,我的订单,订单状态,物流,快递',
        'scene_type': 'ordering', 'category': 'order'
    },
    {
        'question': '订单什么时候发货？',
        'answer': '一般在付款后 48 小时内发货，节假日顺延。发货后您会收到物流通知，也可随时向我提供订单号查询进度。',
        'keywords': '发货,几天发货,什么时候发货,多久发货,物流进度',
        'scene_type': 'ordering', 'category': 'order'
    },
    {
        'question': '退换货政策是什么？',
        'answer': '支持 7 天无理由退换货（商品需保持完好且配件齐全）。您可在订单详情页提交售后申请，或提供订单号由我协助处理。',
        'keywords': '退换货,退货,换货,7天无理由,售后政策',
        'scene_type': 'after_sales', 'category': 'after_sales'
    },
    {
        'question': '退款多久到账？',
        'answer': '退款审核通过后 1-3 个工作日原路退回，银行到账可能有 1-2 天延迟。如超时未到账，请提供订单号，我帮您核查。',
        'keywords': '退款,退款进度,退款到账,退钱,多久到账',
        'scene_type': 'after_sales', 'category': 'after_sales'
    },
    {
        'question': '产品支持哪些功能？',
        'answer': '我们的产品支持智能问答、多场景客服、公告推送与数据统计等能力。您可以告诉我具体使用场景，我为您详细介绍。',
        'keywords': '产品功能,有哪些功能,功能介绍,支持什么,产品介绍',
        'scene_type': 'product', 'category': 'product'
    },
    {
        'question': '价格与套餐如何选择？',
        'answer': '我们提供基础版、专业版和企业版三档套餐，分别面向个人、中小团队与大型企业。您可以说明团队规模，我为您推荐合适方案。',
        'keywords': '价格,多少钱,费用,套餐,收费,报价',
        'scene_type': 'product', 'category': 'product'
    },
    {
        'question': '登录不上怎么办？',
        'answer': '请先确认账号密码是否正确，并尝试重新打开小程序或清除缓存。若仍无法登录，请描述具体报错信息，我帮您排查。',
        'keywords': '登录不了,无法登录,登录失败,登不上,密码错误',
        'scene_type': 'technical', 'category': 'technical'
    },
    {
        'question': '使用过程中报错如何处理？',
        'answer': '请提供报错截图或错误提示文字、操作步骤和手机型号，我会据此定位问题；紧急情况可联系技术支持远程协助。',
        'keywords': '报错,错误,异常,闪退,无法使用,打不开',
        'scene_type': 'technical', 'category': 'technical'
    },
]


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

    # 统一 JSON 错误响应（避免前端拿到 HTML 错误页）
    register_error_handlers(app)

    # 初始化数据库（创建表 + 兼容旧库结构 + 初始化基础数据）
    init_database()

    logger.info('AI问答客服平台启动成功!')
    return app


def register_error_handlers(app):
    """所有异常统一返回 {code, message, data, timestamp} 结构，便于小程序解析"""
    from werkzeug.exceptions import HTTPException
    from .utils.response import error_response

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        messages = {
            400: '请求参数有误', 401: '未授权', 403: '无权限访问',
            404: '接口或资源不存在', 405: '请求方法不被允许',
            413: '请求体过大', 429: '请求过于频繁，请稍后再试',
        }
        message = messages.get(err.code, err.description or '请求失败')
        if err.code >= 500:
            logger.error('HTTP %s: %s', err.code, err.description)
        return error_response(message, err.code)

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        logger.exception('未捕获异常: %s', err)
        return error_response('服务器内部错误，请稍后重试', 500)


def init_database():
    """连接数据库、建表、兼容升级并写入基础数据"""
    from .models import db, User, Conversation, Message, Announcement, UserAnnouncement, QuickReply
    db.connect(reuse_if_open=True)
    db.create_tables([
        User, Conversation, Message,
        Announcement, UserAnnouncement, QuickReply
    ], safe=True)

    # 旧数据库可能没有 password_hash 字段，做一次兼容升级
    if 'password_hash' not in [c.name for c in db.get_columns('users')]:
        db.execute_sql('ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL')
        logger.info('数据库结构已升级: users.password_hash')

    _seed_data()


def _seed_data():
    """初始化管理员账号、快捷回复模板与欢迎公告（幂等）"""
    from werkzeug.security import generate_password_hash
    from .models import User, QuickReply, Announcement

    admin = User.get_or_none(User.username == 'admin')
    if not admin:
        User.create(
            username='admin', nickname='管理员', role='admin', status=1,
            password_hash=generate_password_hash('admin123')
        )
        logger.info('已创建管理员账号 admin / admin123')

    if QuickReply.select().count() == 0:
        for item in DEFAULT_QUICK_REPLIES:
            QuickReply.create(**item)
        logger.info('已初始化 %d 条快捷回复模板', len(DEFAULT_QUICK_REPLIES))

    if Announcement.select().count() == 0:
        Announcement.create(
            title='欢迎使用 AI 智能客服',
            content='您好！AI 智能客服已上线，支持通用问答、产品咨询、售后服务、技术支持与订单查询等场景，欢迎体验。',
            type='notice', priority=10, status=1
        )
        logger.info('已初始化欢迎公告')


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
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
