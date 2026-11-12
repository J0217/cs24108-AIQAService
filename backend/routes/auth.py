# -*- coding: utf-8 -*-
"""
认证路由 - 用户登录、注册、Token管理
"""
import logging
import uuid
from datetime import datetime, timezone

import jwt
import requests
from flask import Blueprint, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from ..models import User
from ..utils.auth import decode_token, extract_token
from ..utils.ratelimit import limiter
from ..utils.response import success_response, error_response

bp = Blueprint('auth', __name__, url_prefix='/api/auth')
logger = logging.getLogger(__name__)

WX_CODE2SESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'


def utcnow():
    return datetime.now(timezone.utc)


def _client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _login_rate_limited(scope):
    """登录类接口限流，防止撞库与暴力破解"""
    if not current_app.config.get('RATE_LIMIT_ENABLED', True):
        return None
    limit = current_app.config.get('LOGIN_RATE_LIMIT_PER_MINUTE', 10)
    allowed, retry_after = limiter.allow(f'login:{scope}:{_client_ip()}', limit, 60)
    if allowed:
        return None
    logger.warning('登录接口触发限流: scope=%s ip=%s', scope, _client_ip())
    resp, code = error_response('尝试过于频繁，请稍后再试', 429)
    resp['retry_after'] = retry_after
    return resp, code


def generate_token(user_id, secret_key):
    """生成JWT Token"""
    payload = {
        'user_id': user_id,
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc).timestamp() + 86400
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


# .env.example 里的占位值（your-wx-appid 等）不能当成真实配置，
# 否则会去调微信接口并返回 invalid appid，导致开发者工具里登录直接 401
_WX_PLACEHOLDER_PREFIXES = ('your-', 'your_', 'wx-your', 'xxx', 'none', 'change-me', 'todo', 'test')


def _wx_configured(appid, secret):
    """只有 appid 与 secret 都是真实值时才走微信接口"""
    for value in (appid, secret):
        value = (value or '').strip().lower()
        if not value or value.startswith(_WX_PLACEHOLDER_PREFIXES):
            return False
    return True


def _request_openid(code):
    """调用微信 jscode2session 换取 openid；未配置或仍是占位值时使用开发态 mock"""
    appid = current_app.config.get('WX_APPID', '')
    secret = current_app.config.get('WX_SECRET', '')
    if not _wx_configured(appid, secret):
        return f"mock_openid_{uuid.uuid4().hex[:16]}"

    resp = requests.get(WX_CODE2SESSION_URL, params={
        'appid': appid, 'secret': secret,
        'js_code': code, 'grant_type': 'authorization_code'
    }, timeout=5)
    result = resp.json()
    if result.get('errcode'):
        raise ValueError(result.get('errmsg', '微信登录失败'))
    openid = result.get('openid')
    if not openid:
        raise ValueError('微信登录失败：未获取到 openid')
    return openid


@bp.route('/wx-login', methods=['POST'])
def wx_login():
    """微信小程序登录"""
    limited = _login_rate_limited('wx')
    if limited:
        return limited

    payload = request.get_json(silent=True) or {}
    if not payload.get('code'):
        return error_response('缺少微信登录凭证code', 400)

    try:
        openid = _request_openid(payload['code'])
    except ValueError as e:
        return error_response(str(e), 401)
    except requests.RequestException:
        return error_response('微信登录服务暂不可用，请稍后重试', 503)

    user = User.get_or_none(User.openid == openid)
    if not user:
        nickname = payload.get('nickname') or f'用户{str(uuid.uuid4())[:6]}'
        user = User.create(
            openid=openid,
            nickname=nickname,
            avatar=payload.get('avatar', ''),
            role='user',
            status=1
        )

    if user.status != 1:
        return error_response('账号已被禁用', 403)

    if payload.get('nickname'):
        user.nickname = payload['nickname'].strip()[:64]
    if payload.get('avatar'):
        user.avatar = payload['avatar'].strip()[:256]
    user.last_login_time = utcnow()
    user.save()

    token = generate_token(user.id, current_app.config.get('JWT_SECRET_KEY'))
    return success_response({'token': token, 'user': user.to_dict()}, '登录成功')


@bp.route('/login', methods=['POST'])
def login():
    """账号密码登录"""
    limited = _login_rate_limited('password')
    if limited:
        return limited

    data = request.get_json(silent=True)
    if not data:
        return error_response('请求数据为空', 400)

    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return error_response('用户名和密码不能为空', 400)

    user = User.get_or_none((User.username == username) & (User.status == 1))
    if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
        logger.info('登录失败: username=%s ip=%s', username, _client_ip())
        return error_response('用户名或密码错误', 401)

    user.last_login_time = utcnow()
    user.save()

    token = generate_token(user.id, current_app.config.get('JWT_SECRET_KEY'))
    return success_response({'token': token, 'user': user.to_dict()}, '登录成功')


@bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    limited = _login_rate_limited('register')
    if limited:
        return limited

    data = request.get_json(silent=True)
    if not data:
        return error_response('请求数据为空', 400)

    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    phone = (data.get('phone') or '').strip()

    if not username or not password:
        return error_response('用户名和密码不能为空', 400)

    if len(username) < 3 or len(username) > 64:
        return error_response('用户名长度需在3-64个字符之间', 400)

    if len(password) < 6:
        return error_response('密码长度至少6位', 400)

    if phone:
        from ..utils.validators import validate_phone
        if not validate_phone(phone):
            return error_response('手机号格式不正确', 400)

    if User.get_or_none(User.username == username):
        return error_response('用户名已存在', 409)

    user = User.create(
        username=username,
        nickname=username,
        phone=phone,
        password_hash=generate_password_hash(password),
        role='user',
        status=1
    )
    return success_response(user.to_dict(), '注册成功')


@bp.route('/refresh', methods=['POST'])
def refresh():
    """刷新Token（过期后不再可用，客户端应重新登录）"""
    token = extract_token()
    if not token:
        return error_response('未提供认证Token', 401)

    payload = decode_token(token)
    if not payload or not payload.get('user_id'):
        return error_response('Token无效或已过期', 401)

    user = User.get_or_none((User.id == payload['user_id']) & (User.status == 1))
    if not user:
        return error_response('用户不存在或已被禁用', 401)

    new_token = generate_token(user.id, current_app.config.get('JWT_SECRET_KEY'))
    return success_response({'token': new_token}, 'Token刷新成功')


@bp.route('/profile', methods=['GET'])
def get_profile():
    """获取当前用户信息"""
    token = extract_token()
    if not token:
        return error_response('未提供认证Token', 401)

    payload = decode_token(token)
    if not payload or not payload.get('user_id'):
        return error_response('Token无效或已过期', 401)

    user = User.get_or_none((User.id == payload['user_id']) & (User.status == 1))
    if not user:
        return error_response('用户不存在或已被禁用', 401)
    return success_response(user.to_dict(), '获取成功')


@bp.route('/profile', methods=['PUT'])
def update_profile():
    """更新用户信息"""
    token = extract_token()
    if not token:
        return error_response('未提供认证Token', 401)

    payload = decode_token(token)
    if not payload or not payload.get('user_id'):
        return error_response('Token无效或已过期', 401)

    user = User.get_or_none((User.id == payload['user_id']) & (User.status == 1))
    if not user:
        return error_response('用户不存在或已被禁用', 401)

    data = request.get_json(silent=True) or {}
    if 'nickname' in data:
        user.nickname = (data['nickname'] or '').strip()[:64]
    if 'avatar' in data:
        user.avatar = (data['avatar'] or '').strip()[:256]
    if 'phone' in data:
        user.phone = (data['phone'] or '').strip()[:20]
    user.save()

    return success_response(user.to_dict(), '更新成功')


@bp.route('/logout', methods=['POST'])
def logout():
    """退出登录"""
    return success_response(None, '退出成功')
