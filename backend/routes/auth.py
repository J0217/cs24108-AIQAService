# -*- coding: utf-8 -*-
"""
认证路由 - 用户登录、注册、Token管理
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
import jwt
import uuid
import re

from ..models import db, User
from ..utils.response import success_response, error_response

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def utcnow():
    return datetime.now(timezone.utc)


def generate_token(user_id, secret_key):
    """生成JWT Token"""
    payload = {
        'user_id': user_id,
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc).timestamp() + 86400
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


def decode_token(token, secret_key):
    """解码JWT Token"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@bp.route('/wx-login', methods=['POST'])
def wx_login():
    """微信小程序登录"""
    data = request.get_json()
    if not data or not data.get('code'):
        return error_response('缺少微信登录凭证code', 400)

    openid = f"mock_openid_{uuid.uuid4().hex[:16]}"

    user = User.get_or_none(User.openid == openid)
    if not user:
        user = User.create(
            openid=openid,
            nickname=f'用户{str(uuid.uuid4())[:6]}',
            role='user',
            status=1
        )

    if user.status != 1:
        return error_response('账号已被禁用', 403)

    user.last_login_time = utcnow()
    user.save()

    token = generate_token(user.id, current_app.config.get('JWT_SECRET_KEY'))

    return success_response({'token': token, 'user': user.to_dict()}, '登录成功')


@bp.route('/login', methods=['POST'])
def login():
    """账号密码登录"""
    data = request.get_json()
    if not data:
        return error_response('请求数据为空', 400)

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return error_response('用户名和密码不能为空', 400)

    user = User.get_or_none((User.username == username) & (User.status == 1))
    if not user:
        return error_response('用户名或密码错误', 401)

    # TODO: 实际应使用bcrypt验证密码
    user.last_login_time = utcnow()
    user.save()

    token = generate_token(user.id, current_app.config.get('JWT_SECRET_KEY'))
    return success_response({'token': token, 'user': user.to_dict()}, '登录成功')


@bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    if not data:
        return error_response('请求数据为空', 400)

    username = data.get('username', '').strip()
    password = data.get('password', '')
    phone = data.get('phone', '').strip()

    if not username or not password:
        return error_response('用户名和密码不能为空', 400)

    if len(username) < 3 or len(username) > 64:
        return error_response('用户名长度需在3-64个字符之间', 400)

    if len(password) < 6:
        return error_response('密码长度至少6位', 400)

    if User.get_or_none(User.username == username):
        return error_response('用户名已存在', 409)

    user = User.create(
        username=username,
        nickname=username,
        phone=phone,
        role='user',
        status=1
    )
    return success_response(user.to_dict(), '注册成功')


@bp.route('/refresh', methods=['POST'])
def refresh():
    """刷新Token"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return error_response('未提供认证Token', 401)

    try:
        payload = jwt.decode(token, current_app.config.get('JWT_SECRET_KEY'), algorithms=['HS256'])
        new_token = generate_token(payload['user_id'], current_app.config.get('JWT_SECRET_KEY'))
        return success_response({'token': new_token}, 'Token刷新成功')
    except Exception:
        return error_response('Token无效或已过期', 401)


@bp.route('/profile', methods=['GET'])
def get_profile():
    """获取当前用户信息"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return error_response('未提供认证Token', 401)

    try:
        payload = jwt.decode(token, current_app.config.get('JWT_SECRET_KEY'), algorithms=['HS256'])
        user = User.get_or_none(User.id == payload['user_id'])
        if not user or user.status != 1:
            return error_response('用户不存在或已被禁用', 401)
        return success_response(user.to_dict(), '获取成功')
    except Exception:
        return error_response('Token无效或已过期', 401)


@bp.route('/profile', methods=['PUT'])
def update_profile():
    """更新用户信息"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return error_response('未提供认证Token', 401)

    try:
        payload = jwt.decode(token, current_app.config.get('JWT_SECRET_KEY'), algorithms=['HS256'])
        user = User.get_or_none(User.id == payload['user_id'])
        if not user or user.status != 1:
            return error_response('用户不存在或已被禁用', 401)

        data = request.get_json() or {}
        if 'nickname' in data:
            user.nickname = data['nickname'].strip()
        if 'avatar' in data:
            user.avatar = data['avatar'].strip()
        if 'phone' in data:
            user.phone = data['phone'].strip()
        user.save()

        return success_response(user.to_dict(), '更新成功')
    except Exception:
        return error_response('Token无效或已过期', 401)


@bp.route('/logout', methods=['POST'])
def logout():
    """退出登录"""
    return success_response(None, '退出成功')
