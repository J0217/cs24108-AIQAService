# -*- coding: utf-8 -*-
"""
对话路由 - 小程序对话接口、消息收发、AI回复生成
"""
import logging
import time
import uuid

from flask import Blueprint, request, current_app
from peewee import fn

from ..models import Conversation, Message, QuickReply
from ..services.ai_service import AIService
from ..utils.auth import get_current_user, utcnow
from ..utils.response import success_response, error_response

bp = Blueprint('chat', __name__, url_prefix='/api/chat')
logger = logging.getLogger(__name__)


def _valid_scene(scene_type):
    """场景白名单校验，非法值回退 general"""
    scenes = current_app.config.get('SCENE_TYPES', ())
    return scene_type if scene_type in scenes else 'general'


@bp.route('/conversations', methods=['GET'])
def list_conversations():
    """获取当前用户的对话列表（消息数一次聚合查询，避免 N+1）"""
    user, err = get_current_user()
    if err:
        return err

    page = max(1, request.args.get('page', 1, type=int))
    page_size = min(request.args.get('page_size', current_app.config.get('PAGE_SIZE'), type=int) or 20, 100)
    scene_type = request.args.get('scene_type', '')

    query = Conversation.select().where(Conversation.user_id == user.id, Conversation.status == 1)
    if scene_type:
        query = query.where(Conversation.scene_type == scene_type)
    query = query.order_by(Conversation.updated_at.desc())

    total = query.count()
    conversations = list(query.limit(page_size).offset((page - 1) * page_size))

    # 一次性统计本页每个会话的用户消息数
    counts = {}
    ids = [c.id for c in conversations]
    if ids:
        rows = (Message.select(Message.conversation_id, fn.COUNT(Message.id).alias('cnt'))
                .where((Message.conversation_id.in_(ids)) & (Message.role == 'user'))
                .group_by(Message.conversation_id)
                .tuples())
        counts = {row[0]: row[1] for row in rows}

    return success_response({
        'list': [c.to_dict(message_count=counts.get(c.id, 0)) for c in conversations],
        'total': total,
        'page': page,
        'page_size': page_size,
        'pages': (total + page_size - 1) // page_size
    }, '获取成功')


@bp.route('/conversations', methods=['POST'])
def create_conversation():
    """创建新对话；同场景已存在空会话时直接复用，避免产生大量空会话"""
    user, err = get_current_user()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '新对话').strip()[:128]
    scene_type = _valid_scene(data.get('scene_type', 'general'))
    reuse_empty = data.get('reuse_empty', True)

    if reuse_empty:
        empty = (Conversation.select()
                 .where(Conversation.user_id == user.id,
                        Conversation.scene_type == scene_type,
                        Conversation.status == 1)
                 .order_by(Conversation.updated_at.desc())
                 .first())
        if empty and not Message.select().where(Message.conversation_id == empty.id).exists():
            return success_response(empty.to_dict(message_count=0), '已复用空会话')

    conversation = Conversation.create(
        user_id=user.id,
        session_id=f"session_{uuid.uuid4().hex[:12]}",
        title=title,
        scene_type=scene_type,
        status=1
    )
    return success_response(conversation.to_dict(message_count=0), '创建成功')


@bp.route('/conversations/<int:conversation_id>', methods=['PUT'])
def update_conversation(conversation_id):
    """更新对话信息（修改标题）"""
    user, err = get_current_user()
    if err:
        return err

    conversation = Conversation.get_or_none(
        (Conversation.id == conversation_id) & (Conversation.user_id == user.id))
    if not conversation:
        return error_response('对话不存在', 404)

    data = request.get_json(silent=True) or {}
    if data.get('title'):
        conversation.title = data['title'].strip()[:128]
    if data.get('scene_type'):
        conversation.scene_type = _valid_scene(data['scene_type'])
    conversation.updated_at = utcnow()
    conversation.save()
    return success_response(conversation.to_dict(), '更新成功')


@bp.route('/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """获取对话详情及消息列表"""
    user, err = get_current_user()
    if err:
        return err

    conversation = Conversation.get_or_none(
        (Conversation.id == conversation_id) & (Conversation.user_id == user.id))
    if not conversation:
        return error_response('对话不存在', 404)

    page = max(1, request.args.get('page', 1, type=int))
    page_size = min(request.args.get('page_size', 50, type=int) or 50, 200)

    total = Message.select().where(Message.conversation_id == conversation_id).count()
    messages = [m.to_dict() for m in
                Message.select().where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc(), Message.id.asc())
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
    """删除对话（软删除）"""
    user, err = get_current_user()
    if err:
        return err

    conversation = Conversation.get_or_none(
        (Conversation.id == conversation_id) & (Conversation.user_id == user.id))
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

    conversation = Conversation.get_or_none(
        (Conversation.id == conversation_id) & (Conversation.user_id == user.id))
    if not conversation:
        return error_response('对话不存在', 404)

    data = request.get_json(silent=True)
    if not data or not str(data.get('content') or '').strip():
        return error_response('消息内容不能为空', 400)

    content = str(data['content']).strip()
    if len(content) > 500:
        return error_response('单条消息不能超过500字', 400)
    message_type = data.get('message_type', 'text')

    # 记录用户消息
    user_message = Message.create(
        conversation_id=conversation_id,
        user_id=user.id,
        role='user',
        content=content,
        message_type=message_type
    )

    # 仅取最近 N 条上下文（数据库层截断）
    history_limit = current_app.config.get('AI_HISTORY_LIMIT', 10)
    recent = list(
        Message.select().where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(history_limit + 1)
    )
    history = [{'role': m.role, 'content': m.content} for m in reversed(recent)][:-1]

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

    # 首次提问时用问题作为会话标题
    if conversation.title in ('新对话', '', None):
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

    conversation = Conversation.get_or_none(
        (Conversation.id == conversation_id) & (Conversation.user_id == user.id))
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
    ).order_by(Message.created_at.desc(), Message.id.desc()).first())

    if not user_msg:
        return error_response('找不到对应的用户消息', 404)

    history_limit = current_app.config.get('AI_HISTORY_LIMIT', 10)
    recent = list(
        Message.select().where(
            Message.conversation_id == conversation_id,
            Message.created_at < user_msg.created_at
        ).order_by(Message.created_at.desc(), Message.id.desc()).limit(history_limit)
    )
    history = [{'role': m.role, 'content': m.content} for m in reversed(recent)]

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
