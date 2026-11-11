# -*- coding: utf-8 -*-
"""
鉴权工具 - JWT 解析与登录态校验（供各蓝重复用，避免重复实现）
"""
from datetime import datetime, timezone
from functools import wraps

import jwt
from flask import request, current_app

from ..models import User
from .response import error_response


def utcnow():
    """统一 UTC 时间"""
    return datetime.now(timezone.utc)


def decode_token(token, secret_key=None):
    """解析 JWT，失败返回 None"""
    secret_key = secret_key or current_app.config.get('JWT_SECRET_KEY')
    try:
        return jwt.decode(token, secret_key, algorithms=['HS256'])
    except jwt.PyJWTError:
        return None


def extract_token():
    """从 Authorization 头提取 Bearer Token"""
    header = request.headers.get('Authorization', '') or ''
    if header.lower().startswith('bearer '):
        return header[7:].strip()
    return header.strip()


def get_current_user():
    """
    获取当前登录用户
    :return: (user, error_response) —— 成功时 error_response 为 None
    """
    token = extract_token()
    if not token:
        return None, error_response('未提供认证Token', 401)

    payload = decode_token(token)
    if not payload or not payload.get('user_id'):
        return None, error_response('Token无效或已过期', 401)

    user = User.get_or_none((User.id == payload['user_id']) & (User.status == 1))
    if not user:
        return None, error_response('用户不存在或已被禁用', 401)
    return user, None


def login_required(view):
    """登录态装饰器：把 user 作为第一个参数注入视图函数"""
    @wraps(view)
    def wrapper(*args, **kwargs):
        user, err = get_current_user()
        if err:
            return err
        return view(user, *args, **kwargs)
    return wrapper


def admin_required(view):
    """管理员装饰器：需登录且 role=admin"""
    @wraps(view)
    def wrapper(*args, **kwargs):
        user, err = get_current_user()
        if err:
            return err
        if user.role != 'admin':
            return error_response('无权限操作', 403)
        return view(user, *args, **kwargs)
    return wrapper
