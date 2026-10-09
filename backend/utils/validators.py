# -*- coding: utf-8 -*-
"""
工具模块 - 参数校验
"""
import re


def validate_phone(phone: str) -> bool:
    """验证中国手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> tuple:
    """
    验证密码强度
    :return: (是否通过, 强度等级 1-4)
    """
    if len(password) < 6:
        return False, 1
    if len(password) < 8:
        return False, 2

    level = 2
    if re.search(r'[A-Z]', password):
        level += 1
    if re.search(r'[a-z]', password):
        level += 1
    if re.search(r'\d', password):
        level += 1
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        level += 1

    return level >= 3, min(level, 4)


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """清理输入，防止XSS攻击"""
    if not text:
        return ''
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 截断超长文本
    return text[:max_length]
