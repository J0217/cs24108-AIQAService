# -*- coding: utf-8 -*-
"""
公告路由 - 公告发布、推送、阅读状态管理
"""
from flask import Blueprint, request, current_app
from datetime import datetime, timezone
import json

from ..models import db, User, Announcement, UserAnnouncement
from ..utils.response import success_response, error_response
import logging

bp = Blueprint('announcement', __name__, url_prefix='/api/announcement')
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


def admin_required(f):
    """管理员权限装饰器（内联实现）"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user, err = get_current_user()
        if err:
            return err
        if user.role != 'admin':
            return error_response('无权限操作', 403)
        return f(user, *args, **kwargs)
    return decorated


@bp.route('/list', methods=['GET'])
def list_announcements():
    """获取公告列表（公开）"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', current_app.config.get('PAGE_SIZE'), type=int)
    ann_type = request.args.get('type', '')

    now = utcnow()
    query = Announcement.select().where(
        Announcement.status == 1,
        (Announcement.start_time.is_null(True)) | (Announcement.start_time <= now),
        (Announcement.end_time.is_null(True)) | (Announcement.end_time >= now)
    )

    if ann_type:
        query = query.where(Announcement.type == ann_type)

    query = query.order_by(Announcement.priority.desc(), Announcement.created_at.desc())
    total = query.count()
    announcements = [a.to_dict() for a in query.limit(page_size).offset((page - 1) * page_size)]

    return success_response({
        'list': announcements,
        'total': total,
        'page': page,
        'page_size': page_size
    }, '获取成功')


@bp.route('/list/unread', methods=['GET'])
def list_unread_announcements():
    """获取未读公告列表（需登录）"""
    user, err = get_current_user()
    if err:
        return err

    now = utcnow()
    query = Announcement.select().where(
        Announcement.status == 1,
        (Announcement.start_time.is_null(True)) | (Announcement.start_time <= now),
        (Announcement.end_time.is_null(True)) | (Announcement.end_time >= now)
    ).order_by(Announcement.priority.desc(), Announcement.created_at.desc())

    read_ids = [r.announcement_id for r in UserAnnouncement.select().where(
        UserAnnouncement.user_id == user.id, UserAnnouncement.is_read == 1
    )]

    if read_ids:
        query = query.where(~Announcement.id.in_(read_ids))
    unread = [a.to_dict() for a in query]
    return success_response(unread, '获取成功')


@bp.route('/<int:announcement_id>', methods=['GET'])
def get_announcement(announcement_id):
    """获取公告详情"""
    announcement = Announcement.get_or_none((Announcement.id == announcement_id) & (Announcement.status == 1))
    if not announcement:
        return error_response('公告不存在', 404)

    announcement.view_count += 1
    announcement.save()
    return success_response(announcement.to_dict(), '获取成功')


@bp.route('/', methods=['POST'])
@admin_required
def create_announcement(user):
    """创建公告（管理员）"""
    data = request.get_json()
    if not data:
        return error_response('请求数据为空', 400)

    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    if not title or not content:
        return error_response('标题和内容不能为空', 400)

    announcement = Announcement.create(
        title=title,
        content=content,
        type=data.get('type', 'notice'),
        priority=data.get('priority', 0),
        cover_image=data.get('cover_image', ''),
        target_users=json.dumps(data.get('target_users', ['all'])),
        start_time=datetime.fromisoformat(data['start_time']) if data.get('start_time') else None,
        end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
        status=data.get('status', 1),
        created_by=user.id
    )
    return success_response(announcement.to_dict(), '创建成功')


@bp.route('/<int:announcement_id>', methods=['PUT'])
@admin_required
def update_announcement(user, announcement_id):
    """更新公告（管理员）"""
    announcement = Announcement.get_or_none(Announcement.id == announcement_id)
    if not announcement:
        return error_response('公告不存在', 404)

    data = request.get_json()
    if not data:
        return error_response('请求数据为空', 400)

    if 'title' in data:
        announcement.title = data['title'].strip()
    if 'content' in data:
        announcement.content = data['content'].strip()
    if 'type' in data:
        announcement.type = data['type']
    if 'priority' in data:
        announcement.priority = data['priority']
    if 'cover_image' in data:
        announcement.cover_image = data['cover_image'].strip()
    if 'target_users' in data:
        announcement.target_users = json.dumps(data['target_users'])
    if 'start_time' in data and data['start_time']:
        announcement.start_time = datetime.fromisoformat(data['start_time'])
    if 'end_time' in data and data['end_time']:
        announcement.end_time = datetime.fromisoformat(data['end_time'])
    if 'status' in data:
        announcement.status = data['status']

    announcement.updated_at = utcnow()
    announcement.save()
    return success_response(announcement.to_dict(), '更新成功')


@bp.route('/<int:announcement_id>', methods=['DELETE'])
@admin_required
def delete_announcement(user, announcement_id):
    """删除公告（管理员）"""
    announcement = Announcement.get_or_none(Announcement.id == announcement_id)
    if not announcement:
        return error_response('公告不存在', 404)

    announcement.status = 0
    announcement.save()
    return success_response(None, '删除成功')


@bp.route('/read/<int:announcement_id>', methods=['POST'])
def mark_as_read(announcement_id):
    """标记公告为已读（需登录）"""
    user, err = get_current_user()
    if err:
        return err

    record = UserAnnouncement.get_or_none(
        (UserAnnouncement.user_id == user.id) & (UserAnnouncement.announcement_id == announcement_id)
    )
    if record:
        record.is_read = 1
        record.read_at = utcnow()
        record.save()
    else:
        UserAnnouncement.create(
            user_id=user.id,
            announcement_id=announcement_id,
            is_read=1,
            read_at=utcnow()
        )
    return success_response(None, '标记成功')


@bp.route('/unread-count', methods=['GET'])
def get_unread_count():
    """获取未读公告数量（需登录）"""
    user, err = get_current_user()
    if err:
        return err

    now = utcnow()
    active = Announcement.select().where(
        Announcement.status == 1,
        (Announcement.start_time.is_null(True)) | (Announcement.start_time <= now),
        (Announcement.end_time.is_null(True)) | (Announcement.end_time >= now)
    )
    read_ids = [r.announcement_id for r in UserAnnouncement.select().where(
        UserAnnouncement.user_id == user.id, UserAnnouncement.is_read == 1
    )]
    if read_ids:
        active = active.where(~Announcement.id.in_(read_ids))

    unread_count = active.count()
    return success_response({'unread_count': unread_count}, '获取成功')
