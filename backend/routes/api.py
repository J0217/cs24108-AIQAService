# -*- coding: utf-8 -*-
"""
统一API路由 - 对外部系统提供的API接口
"""
from flask import Blueprint, request, current_app
from datetime import datetime, timezone
import hashlib
import time
import uuid

from ..models import db, User, Conversation, Message, Announcement, QuickReply
from ..utils.response import success_response, error_response
from ..services.ai_service import AIService
import logging

bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc)


@bp.route('/v1/chat', methods=['POST'])
def api_chat():
    """
    统一聊天接口 - 供外部系统调用
    请求头: X-API-Key: xxx
    请求体: { "question": "用户问题", "session_id": "会话标识（可选）", "scene_type": "场景类型（可选）" }
    """
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return error_response('缺少API Key', 401)

    # TODO: 实际应验证API Key
    user = User.get_or_none(User.username == 'api_user')  # 简化处理
    if not user:
        user = User.create(username='api_user', nickname='API用户', role='user', status=1)

    data = request.get_json()
    if not data or not data.get('question'):
        return error_response('问题内容不能为空', 400)

    question = data['question'].strip()
    session_id = data.get('session_id', f"api_{uuid.uuid4().hex[:12]}")
    scene_type = data.get('scene_type', 'general')

    conversation = Conversation.get_or_none(Conversation.session_id == session_id)
    if not conversation:
        conversation = Conversation.create(
            user_id=user.id,
            session_id=session_id,
            title=question[:30],
            scene_type=scene_type,
            status=1
        )

    # 记录用户消息
    user_message = Message.create(
        conversation_id=conversation.id,
        user_id=user.id,
        role='user',
        content=question,
        message_type='text'
    )

    # 获取对话历史
    history = [
        {'role': m.role, 'content': m.content}
        for m in Message.select().where(Message.conversation_id == conversation.id).order_by(Message.created_at.asc())
    ][:-1]

    # 调用AI生成回复
    ai_service = AIService()
    ai_response, confidence, response_time = ai_service.generate_reply(
        content=question,
        history=history,
        scene_type=scene_type
    )

    # 记录AI回复
    assistant_message = Message.create(
        conversation_id=conversation.id,
        user_id=user.id,
        role='assistant',
        content=ai_response,
        confidence=confidence,
        response_time=response_time
    )

    return success_response({
        'session_id': session_id,
        'question': question,
        'answer': ai_response,
        'confidence': confidence,
        'response_time': response_time,
        'message_id': assistant_message.id
    }, '请求成功')


@bp.route('/v1/quick-reply', methods=['GET'])
def api_quick_reply():
    """获取快捷回复 - 供外部系统调用"""
    category = request.args.get('category', '')
    scene_type = request.args.get('scene_type', '')
    keyword = request.args.get('keyword', '')

    query = QuickReply.select().where(QuickReply.status == 1)
    if category:
        query = query.where(QuickReply.category == category)
    if scene_type:
        query = query.where(QuickReply.scene_type == scene_type)
    if keyword:
        query = query.where(QuickReply.keywords.contains(keyword))

    replies = [r.to_dict() for r in query.order_by(QuickReply.usage_count.desc())]
    return success_response(replies, '获取成功')


@bp.route('/v1/announcement', methods=['GET'])
def api_announcement():
    """获取最新公告 - 供外部系统调用"""
    announcement = (Announcement.select()
                    .where(Announcement.status == 1)
                    .order_by(Announcement.priority.desc(), Announcement.created_at.desc())
                    .first())

    if announcement:
        announcement.view_count += 1
        announcement.save()
        return success_response(announcement.to_dict(), '获取成功')
    else:
        return success_response(None, '暂无公告')


@bp.route('/v1/stats', methods=['GET'])
def api_stats():
    """获取统计数据 - 供外部系统调用"""
    now = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    stats = {
        'total_users': User.select().where(User.status == 1).count(),
        'total_conversations': Conversation.select().where(Conversation.status == 1).count(),
        'total_messages': Message.select().count(),
        'today_conversations': Conversation.select().where(Conversation.created_at >= now).count(),
        'today_messages': Message.select().where(Message.created_at >= now).count()
    }
    return success_response(stats, '获取成功')
