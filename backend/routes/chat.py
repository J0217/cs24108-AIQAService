# -*- coding: utf-8 -*-
"""
对话路由 - 小程序对话接口、消息收发、AI回复生成
"""
from flask import Blueprint, request, current_app
from datetime import datetime, timezone
import time
import uuid

from ..models import db, User, Conversation, Message, QuickReply
from ..services.ai_service import AIService
from ..utils.response import success_response, error_response
import logging

bp = Blueprint('chat', __name__, url_prefix='/api/chat')
logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc)


def get_current_user():
    """获取当前登录用户"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return None, error_response('未提供认证Token', 401)

    import jwt
    try:
        payload = jwt.decode(token, current_app.config.get('JWT_SECRET_KEY'), algorithms=['HS256'])
        user = User.get_or_none((User.id == payload['user_id']) & (User.status == 1))
        if not user:
            return None, error_response('用户不存在或已被禁用', 401)
        return user, None
    except Exception:
        return None, error_response('Token无效或已过期', 401)


@bp.route('/conversations', methods=['GET'])
def list_conversations():
    """获取当前用户的对话列表"""
    user, err = get_current_user()
    if err:
        return err

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', current_app.config.get('PAGE_SIZE'), type=int)
    scene_type = request.args.get('scene_type', '')

    query = Conversation.select().where(Conversation.user_id == user.id, Conversation.status == 1)
    if scene_type:
        query = query.where(Conversation.scene_type == scene_type)
    query = query.order_by(Conversation.updated_at.desc())

    total = query.count()
    conversations = [c.to_dict() for c in query.limit(page_size).offset((page - 1) * page_size)]

    return success_response({
        'list': conversations,
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size
    }, '获取成功')


@bp.route('/conversations', methods=['POST'])
def create_conversation():
    """创建新对话"""
    user, err = get_current_user()
    if err:
        return err

    data = request.get_json() or {}
    title = data.get('title', '新对话')
    scene_type = data.get('scene_type', 'general')
    session_id = f"session_{uuid.uuid4().hex[:12]}"

    conversation = Conversation.create(
        user_id=user.id,
        session_id=session_id,
        title=title,
        scene_type=scene_type,
        status=1
    )
    return success_response(conversation.to_dict(), '创建成功')


@bp.route('/conversations/<int:conversation_id>', methods=['PUT'])
def update_conversation(conversation_id):
    """更新对话信息（切换场景/修改标题）"""
    user, err = get_current_user()
    if err:
        return err

    conversation = Conversation.get_or_none((Conversation.id == conversation_id) & (Conversation.user_id == user.id))
    if not conversation:
        return error_response('对话不存在', 404)

    data = request.get_json() or {}
    if data.get('title'):
        conversation.title = data['title'].strip()[:128]
    scene_type = data.get('scene_type')
    if scene_type:
        conversation.scene_type = scene_type
    conversation.updated_at = utcnow()
    conversation.save()
    return success_response(conversation.to_dict(), '更新成功')


@bp.route('/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """获取对话详情及消息列表"""
    user, err = get_current_user()
    if err:
        return err

    conversation = Conversation.get_or_none((Conversation.id == conversation_id) & (Conversation.user_id == user.id))
    if not conversation:
        return error_response('对话不存在', 404)

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)

    total = Message.select().where(Message.conversation_id == conversation_id).count()
    messages = [m.to_dict() for m in
                Message.select().where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
                .limit(page_size)
                .offset((page - 1) * page_size)]

    return success_response({
        'conversation': conversation.to_dict(),
        'messages': messages,
        'total': total,
        'page': page,
        'page_size': page_size
    }, '获取成功')


@bp.route('/conversations/<int:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """删除对话"""
    user, err = get_current_user()
    if err:
        return err

    conversation = Conversation.get_or_none((Conversation.id == conversation_id) & (Conversation.user_id == user.id))
    if not conversation:
        return error_response('对话不存在', 404)

    conversation.status = 0
    conversation.save()
    return success_response(None, '删除成功')


@bp.route('/conversations/<int:conversation_id>/messages', methods=['POST'])
def send_message(conversation_id):
    """发送消息并获取AI回复"""
    user, err = get_current_user()
    if err:
        return err

    conversation = Conversation.get_or_none((Conversation.id == conversation_id) & (Conversation.user_id == user.id))
    if not conversation:
        return error_response('对话不存在', 404)

    data = request.get_json()
    if not data or not data.get('content'):
        return error_response('消息内容不能为空', 400)

    content = data['content'].strip()
    message_type = data.get('message_type', 'text')

    start_time = time.time()

    # 记录用户消息
    user_message = Message.create(
        conversation_id=conversation_id,
        user_id=user.id,
        role='user',
        content=content,
        message_type=message_type
    )

    # 获取对话历史
    history = [
        {'role': m.role, 'content': m.content}
        for m in Message.select().where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    ]
    history = history[:-1]  # 排除刚添加的用户消息

    # 调用AI生成回复
    ai_service = AIService()
    ai_response, confidence, response_time, is_quick_reply = ai_service.generate_reply(
        content=content,
        history=history,
        scene_type=conversation.scene_type,
        max_tokens=current_app.config.get('AI_MAX_TOKENS'),
        temperature=current_app.config.get('AI_TEMPERATURE')
    )

    # 记录AI回复
    assistant_message = Message.create(
        conversation_id=conversation_id,
        user_id=user.id,
        role='assistant',
        content=ai_response,
        confidence=confidence,
        is_quick_reply=is_quick_reply,
        response_time=response_time
    )

    # 更新对话标题（如果是对话第一条）
    if conversation.messages.count() <= 2:
        conversation.title = content[:30] + ('...' if len(content) > 30 else '')
    conversation.updated_at = utcnow()
    conversation.save()

    return success_response({
        'user_message': user_message.to_dict(),
        'assistant_message': assistant_message.to_dict()
    }, '发送成功')


@bp.route('/conversations/<int:conversation_id>/messages/<int:message_id>/regenerate', methods=['POST'])
def regenerate_message(conversation_id, message_id):
    """重新生成AI回复"""
    user, err = get_current_user()
    if err:
        return err

    conversation = Conversation.get_or_none((Conversation.id == conversation_id) & (Conversation.user_id == user.id))
    if not conversation:
        return error_response('对话不存在', 404)

    message = Message.get_or_none(
        (Message.id == message_id) & (Message.conversation_id == conversation_id) & (Message.role == 'assistant')
    )
    if not message:
        return error_response('消息不存在', 404)

    # 找到该回复之前最近的一条用户消息
    user_msg = (Message.select().where(
        Message.conversation_id == conversation_id,
        Message.role == 'user',
        Message.created_at <= message.created_at
    ).order_by(Message.created_at.desc()).first())

    if not user_msg:
        return error_response('找不到对应的用户消息', 404)

    history = [
        {'role': m.role, 'content': m.content}
        for m in Message.select().where(
            Message.conversation_id == conversation_id,
            Message.created_at < user_msg.created_at
        ).order_by(Message.created_at.asc())
    ]

    ai_service = AIService()
    ai_response, confidence, response_time, is_quick_reply = ai_service.generate_reply(
        content=user_msg.content,
        history=history,
        scene_type=conversation.scene_type,
        max_tokens=current_app.config.get('AI_MAX_TOKENS'),
        temperature=current_app.config.get('AI_TEMPERATURE')
    )

    message.content = ai_response
    message.confidence = confidence
    message.is_quick_reply = is_quick_reply
    message.response_time = response_time
    message.created_at = utcnow()
    message.save()

    return success_response(message.to_dict(), '重新生成成功')


@bp.route('/quick-replies', methods=['GET'])
def list_quick_replies():
    """获取快捷回复列表"""
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


@bp.route('/scenes', methods=['GET'])
def list_scenes():
    """获取场景列表"""
    scenes = [
        {'type': 'general', 'name': '通用问答', 'icon': 'chat'},
        {'type': 'product', 'name': '产品咨询', 'icon': 'goods'},
        {'type': 'after_sales', 'name': '售后服务', 'icon': 'service'},
        {'type': 'technical', 'name': '技术支持', 'icon': 'tool'},
        {'type': 'ordering', 'name': '订单查询', 'icon': 'order'},
    ]
    return success_response(scenes, '获取成功')
