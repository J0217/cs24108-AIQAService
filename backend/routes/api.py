# -*- coding: utf-8 -*-
"""
统一API路由 - 对外部系统提供的API接口
"""
import hmac
import logging
import uuid
from datetime import datetime, timezone

from flask import Blueprint, request, current_app

from ..models import User, Conversation, Message, Announcement, QuickReply
from ..utils.ratelimit import limiter
from ..utils.response import success_response, error_response
from ..services.ai_service import AIService

bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


def utcnow():
    return datetime.now(timezone.utc)


def _client_ip():
    """取真实客户端 IP（兼容反向代理）"""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def validate_api_key() -> bool:
    """校验外部调用方传入的 X-API-Key（常量时间比较，避免时序攻击）"""
    api_key = (request.headers.get('X-API-Key') or '').strip()
    if not api_key:
        return False
    allowed = [k.strip() for k in str(current_app.config.get('API_KEYS', '')).split(',') if k.strip()]
    # 逐个比较且不使用短路，避免通过响应时间推测 Key
    matched = False
    for candidate in allowed:
        if hmac.compare_digest(api_key, candidate):
            matched = True
    return matched


@bp.before_request
def require_api_key():
    """统一API下的所有 /v1 接口都必须携带有效的 X-API-Key，并限制调用频率"""
    if not request.path.startswith('/api/v1/'):
        return None
    if not request.headers.get('X-API-Key'):
        return error_response('缺少API Key', 401)
    if not validate_api_key():
        return error_response('API Key 无效', 401)

    if current_app.config.get('RATE_LIMIT_ENABLED', True):
        limit = current_app.config.get('RATE_LIMIT_PER_MINUTE', 60)
        allowed, retry_after = limiter.allow(f'api:{_client_ip()}', limit, 60)
        if not allowed:
            logger.warning('开放API触发限流: ip=%s', _client_ip())
            resp, code = error_response('请求过于频繁，请稍后再试', 429)
            resp['retry_after'] = retry_after
            return resp, code
    return None


@bp.route('/v1/chat', methods=['POST'])
def api_chat():
    """
    统一聊天接口 - 供外部系统调用
    请求头: X-API-Key: xxx
    请求体: { "question": "用户问题", "session_id": "会话标识（可选）", "scene_type": "场景类型（可选）" }
    """
    user = User.get_or_none(User.username == 'api_user')  # 统一API接入账号
    if not user:
        user = User.create(username='api_user', nickname='API用户', role='user', status=1)

    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question:
        return error_response('问题内容不能为空', 400)
    if len(question) > 500:
        return error_response('问题内容不能超过500字', 400)

    session_id = (data.get('session_id') or f"api_{uuid.uuid4().hex[:12]}").strip()[:64]
    scene_type = data.get('scene_type', 'general')
    if scene_type not in current_app.config.get('SCENE_TYPES', ()):
        scene_type = 'general'

    conversation = Conversation.get_or_none(
        (Conversation.session_id == session_id) & (Conversation.user_id == user.id)
    )
    if not conversation:
        conversation = Conversation.create(
            user_id=user.id,
            session_id=session_id,
            title=question[:30],
            scene_type=scene_type,
            status=1
        )
    elif conversation.scene_type != scene_type:
        conversation.scene_type = scene_type
        conversation.save()

    # 记录用户消息
    Message.create(
        conversation_id=conversation.id,
        user_id=user.id,
        role='user',
        content=question,
        message_type='text'
    )

    # 仅取最近 N 条作为上下文（数据库层截断，长会话不再全表扫描）
    history_limit = current_app.config.get('AI_HISTORY_LIMIT', 10)
    recent = list(
        Message.select().where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(history_limit + 1)
    )
    history = [{'role': m.role, 'content': m.content} for m in reversed(recent)][:-1]

    # 调用AI生成回复
    ai_service = AIService()
    ai_response, confidence, response_time, is_quick_reply = ai_service.generate_reply(
        content=question,
        history=history,
        scene_type=scene_type,
        max_tokens=current_app.config.get('AI_MAX_TOKENS'),
        temperature=current_app.config.get('AI_TEMPERATURE')
    )

    # 记录AI回复
    assistant_message = Message.create(
        conversation_id=conversation.id,
        user_id=user.id,
        role='assistant',
        content=ai_response,
        confidence=confidence,
        is_quick_reply=is_quick_reply,
        response_time=response_time
    )
    conversation.updated_at = utcnow()
    conversation.save()

    return success_response({
        'session_id': session_id,
        'question': question,
        'answer': ai_response,
        'confidence': confidence,
        'is_quick_reply': is_quick_reply,
        'response_time': round(response_time, 2),
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
    """获取最新公告 - 供外部系统调用；默认不累加浏览量（加 ?count_view=1 才计数）"""
    announcement = (Announcement.select()
                    .where(Announcement.status == 1)
                    .order_by(Announcement.priority.desc(), Announcement.created_at.desc())
                    .first())

    if not announcement:
        return success_response(None, '暂无公告')

    if request.args.get('count_view') in ('1', 'true', 'yes'):
        Announcement.update(view_count=Announcement.view_count + 1).where(
            Announcement.id == announcement.id).execute()
        announcement.view_count += 1
    return success_response(announcement.to_dict(), '获取成功')


@bp.route('/v1/stats', methods=['GET'])
def api_stats():
    """获取统计数据 - 供外部系统调用"""
    now = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    stats = {
        'total_users': User.select().where(User.status == 1).count(),
        'total_conversations': Conversation.select().where(Conversation.status == 1).count(),
        'total_messages': Message.select().count(),
        'today_conversations': Conversation.select().where(Conversation.created_at >= now).count(),
        'today_messages': Message.select().where(Message.created_at >= now).count(),
        'template_hit_messages': Message.select().where(Message.is_quick_reply == 1).count()
    }
    return success_response(stats, '获取成功')
