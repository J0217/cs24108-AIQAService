# -*- coding: utf-8 -*-
"""
公告路由 - 公告发布、推送、阅读状态管理
"""
import json
import logging
from datetime import datetime

from flask import Blueprint, request, current_app

from ..models import Announcement, UserAnnouncement
from ..utils.auth import admin_required, get_current_user, utcnow
from ..utils.response import success_response, error_response

bp = Blueprint('announcement', __name__, url_prefix='/api/announcement')
logger = logging.getLogger(__name__)


def _parse_dt(value, field):
    """安全解析 ISO 时间字符串，返回 (datetime|None, error)"""
    if value in (None, ''):
        return None, None
    try:
        return datetime.fromisoformat(str(value)), None
    except (TypeError, ValueError):
        return None, error_response(f'{field} 格式应为 ISO8601（如 2026-11-11T09:00:00）', 400)


def _active_query(user=None):
    """当前生效的公告查询（状态 + 时间窗 + 定向范围）"""
    now = utcnow()
    query = Announcement.select().where(
        Announcement.status == 1,
        (Announcement.start_time.is_null(True)) | (Announcement.start_time <= now),
        (Announcement.end_time.is_null(True)) | (Announcement.end_time >= now)
    )
    # 定向推送：只展示 all 或包含当前用户 ID/角色的公告
    target_cond = Announcement.target_users.contains('"all"')
    if user is not None:
        target_cond = (target_cond
                       | Announcement.target_users.contains(f'"{user.id}"')
                       | Announcement.target_users.contains(f'"{user.role}"'))
    return query.where(target_cond)


@bp.route('/list', methods=['GET'])
def list_announcements():
    """获取公告列表（公开，未登录只返回面向全体用户的公告）"""
    page = max(1, request.args.get('page', 1, type=int))
    page_size = min(request.args.get('page_size', current_app.config.get('PAGE_SIZE'), type=int) or 20, 100)
    ann_type = request.args.get('type', '')

    user = None
    if request.headers.get('Authorization'):
        user, _ = get_current_user()

    query = _active_query(user)
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

    query = _active_query(user).order_by(Announcement.priority.desc(), Announcement.created_at.desc())
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
    announcement = Announcement.get_or_none(
        (Announcement.id == announcement_id) & (Announcement.status == 1))
    if not announcement:
        return error_response('公告不存在', 404)

    # 原子自增，避免并发读改写丢失
    Announcement.update(view_count=Announcement.view_count + 1).where(
        Announcement.id == announcement_id).execute()
    announcement.view_count += 1
    return success_response(announcement.to_dict(), '获取成功')


@bp.route('/', methods=['POST'])
@bp.route('', methods=['POST'])
@admin_required
def create_announcement(user):
    """创建公告（管理员）"""
    data = request.get_json(silent=True)
    if not data:
        return error_response('请求数据为空', 400)

    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    if not title or not content:
        return error_response('标题和内容不能为空', 400)
    if len(title) > 128:
        return error_response('标题不能超过128字', 400)

    start_time, err = _parse_dt(data.get('start_time'), 'start_time')
    if err:
        return err
    end_time, err = _parse_dt(data.get('end_time'), 'end_time')
    if err:
        return err
    if start_time and end_time and end_time < start_time:
        return error_response('结束时间不能早于开始时间', 400)

    announcement = Announcement.create(
        title=title,
        content=content,
        type=data.get('type', 'notice'),
        priority=int(data.get('priority', 0) or 0),
        cover_image=data.get('cover_image', ''),
        target_users=json.dumps(data.get('target_users', ['all']), ensure_ascii=False),
        start_time=start_time,
        end_time=end_time,
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

    data = request.get_json(silent=True)
    if not data:
        return error_response('请求数据为空', 400)

    if 'title' in data:
        announcement.title = (data['title'] or '').strip()[:128]
    if 'content' in data:
        announcement.content = (data['content'] or '').strip()
    if 'type' in data:
        announcement.type = data['type']
    if 'priority' in data:
        announcement.priority = int(data['priority'] or 0)
    if 'cover_image' in data:
        announcement.cover_image = (data['cover_image'] or '').strip()
    if 'target_users' in data:
        announcement.target_users = json.dumps(data['target_users'], ensure_ascii=False)
    if 'start_time' in data:
        announcement.start_time, err = _parse_dt(data['start_time'], 'start_time')
        if err:
            return err
    if 'end_time' in data:
        announcement.end_time, err = _parse_dt(data['end_time'], 'end_time')
        if err:
            return err
    if 'status' in data:
        announcement.status = data['status']

    announcement.updated_at = utcnow()
    announcement.save()
    return success_response(announcement.to_dict(), '更新成功')


@bp.route('/<int:announcement_id>', methods=['DELETE'])
@admin_required
def delete_announcement(user, announcement_id):
    """删除公告（管理员，软删除）"""
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

    if not Announcement.get_or_none(Announcement.id == announcement_id):
        return error_response('公告不存在', 404)

    now = utcnow()
    updated = (UserAnnouncement.update(is_read=1, read_at=now)
               .where((UserAnnouncement.user_id == user.id)
                      & (UserAnnouncement.announcement_id == announcement_id))
               .execute())
    if not updated:
        UserAnnouncement.create(
            user_id=user.id,
            announcement_id=announcement_id,
            is_read=1,
            read_at=now
        )
    return success_response(None, '标记成功')


@bp.route('/unread-count', methods=['GET'])
def get_unread_count():
    """获取未读公告数量（需登录）"""
    user, err = get_current_user()
    if err:
        return err

    active = _active_query(user)
    read_ids = [r.announcement_id for r in UserAnnouncement.select().where(
        UserAnnouncement.user_id == user.id, UserAnnouncement.is_read == 1
    )]
    if read_ids:
        active = active.where(~Announcement.id.in_(read_ids))

    return success_response({'unread_count': active.count()}, '获取成功')
