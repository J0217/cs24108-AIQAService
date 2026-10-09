# -*- coding: utf-8 -*-
"""
工具模块 - 响应封装、参数校验等
"""
from datetime import datetime


def success_response(data=None, message='success', code=200):
    return {
        'code': code,
        'message': message,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }


def error_response(message='error', code=400, data=None):
    return {
        'code': code,
        'message': message,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }, code


def validate_phone(phone: str) -> bool:
    import re
    return bool(re.match(r'^1[3-9]\d{9}$', phone))


def validate_email(email: str) -> bool:
    import re
    return bool(re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email))
