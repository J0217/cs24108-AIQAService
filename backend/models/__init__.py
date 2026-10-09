# -*- coding: utf-8 -*-
"""
数据库模型 - 使用 Peewee ORM（兼容 Python 3.14）
"""
import os
import peewee
from datetime import datetime, timezone

# 数据库实例
db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance')
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, 'ai_qa_service.db')

db = peewee.SqliteDatabase(db_path)


def utcnow():
    """返回UTC时间"""
    return datetime.now(timezone.utc)


class BaseMixin(peewee.Model):
    """基础模型混入，统一时间字段"""
    created_at = peewee.DateTimeField(default=utcnow)
    updated_at = peewee.DateTimeField(default=utcnow, index=True)

    class Meta:
        database = db


class User(BaseMixin):
    """用户表"""
    openid = peewee.CharField(max_length=64, null=True, unique=True, index=True)
    username = peewee.CharField(max_length=64, null=True, unique=True)
    nickname = peewee.CharField(max_length=64, default='')
    avatar = peewee.CharField(max_length=256, default='')
    phone = peewee.CharField(max_length=20, default='')
    role = peewee.CharField(max_length=20, default='user')  # user/admin
    status = peewee.IntegerField(default=1)  # 1正常 0禁用
    last_login_time = peewee.DateTimeField(default=utcnow)

    class Meta:
        table_name = 'users'
        database = db

    def to_dict(self):
        return {
            'id': self.id,
            'openid': self.openid,
            'username': self.username,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'phone': self.phone,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Conversation(BaseMixin):
    """对话记录表"""
    user_id = peewee.ForeignKeyField(User, backref='conversations', on_delete='CASCADE')
    session_id = peewee.CharField(max_length=64, index=True)
    title = peewee.CharField(max_length=128, default='新对话')
    scene_type = peewee.CharField(max_length=32, default='general')
    status = peewee.IntegerField(default=1)  # 1进行中 0已结束

    class Meta:
        table_name = 'conversations'
        database = db

    def to_dict(self):
        msg_count = Message.select().where(
            (Message.conversation_id == self.id) & (Message.role == 'user')
        ).count()
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'title': self.title,
            'scene_type': self.scene_type,
            'status': self.status,
            'message_count': msg_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Message(BaseMixin):
    """消息表"""
    conversation_id = peewee.ForeignKeyField(Conversation, backref='messages', on_delete='CASCADE')
    user_id = peewee.ForeignKeyField(User, on_delete='CASCADE')
    role = peewee.CharField(max_length=10)  # user/assistant
    content = peewee.TextField()
    message_type = peewee.CharField(max_length=20, default='text')
    confidence = peewee.FloatField(null=True)
    is_quick_reply = peewee.IntegerField(default=0)
    response_time = peewee.FloatField(null=True)

    class Meta:
        table_name = 'messages'
        database = db

    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'user_id': self.user_id,
            'role': self.role,
            'content': self.content,
            'message_type': self.message_type,
            'confidence': self.confidence,
            'is_quick_reply': self.is_quick_reply,
            'response_time': self.response_time,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Announcement(BaseMixin):
    """公告表"""
    title = peewee.CharField(max_length=128)
    content = peewee.TextField()
    type = peewee.CharField(max_length=32, default='notice')  # notice/promotion/system
    priority = peewee.IntegerField(default=0)
    cover_image = peewee.CharField(max_length=256, default='')
    target_users = peewee.TextField(default='["all"]')
    start_time = peewee.DateTimeField(null=True)
    end_time = peewee.DateTimeField(null=True)
    status = peewee.IntegerField(default=1)  # 1发布 0草稿
    view_count = peewee.IntegerField(default=0)
    created_by = peewee.ForeignKeyField(User, null=True, backref='announcements', on_delete='SET NULL')

    class Meta:
        table_name = 'announcements'
        database = db

    def to_dict(self):
        creator_name = None
        if self.created_by:
            try:
                creator_name = User.get(User.id == self.created_by).nickname
            except User.DoesNotExist:
                pass
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'type': self.type,
            'priority': self.priority,
            'cover_image': self.cover_image,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'view_count': self.view_count,
            'created_by': self.created_by,
            'creator_name': creator_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserAnnouncement(BaseMixin):
    """用户公告阅读记录"""
    user_id = peewee.ForeignKeyField(User, on_delete='CASCADE')
    announcement_id = peewee.ForeignKeyField(Announcement, on_delete='CASCADE')
    is_read = peewee.IntegerField(default=0)
    read_at = peewee.DateTimeField(null=True)

    class Meta:
        table_name = 'user_announcements'
        database = db
        indexes = (
            (('user_id', 'announcement_id'), True),  # 唯一约束
        )


class QuickReply(BaseMixin):
    """快捷回复/回答模板表"""
    question = peewee.CharField(max_length=256)
    answer = peewee.TextField()
    category = peewee.CharField(max_length=32, default='general')
    keywords = peewee.TextField(default='')
    scene_type = peewee.CharField(max_length=32, default='general')
    usage_count = peewee.IntegerField(default=0)
    status = peewee.IntegerField(default=1)

    class Meta:
        table_name = 'quick_replies'
        database = db

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'category': self.category,
            'keywords': self.keywords.split(',') if self.keywords else [],
            'scene_type': self.scene_type,
            'usage_count': self.usage_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 确保 db 对象可被其他模块导入
__all__ = ['db', 'User', 'Conversation', 'Message', 'Announcement', 'UserAnnouncement', 'QuickReply']
