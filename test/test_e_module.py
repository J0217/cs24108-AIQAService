# -*- coding: utf-8 -*-
"""
E-多端接入（小程序 + 开放 API）接口冒烟测试

运行：
    python test/test_e_module.py -v

覆盖范围：
    1. 开放 API 的 X-API-Key 鉴权（缺失、错误、正确）
    2. 开放 API 四个接口（chat / quick-reply / announcement / stats）
    3. 小程序依赖的 JWT 登录、用户信息、场景列表
    4. 小程序“新建会话 -> 发送消息 -> 取历史”主链路
测试使用临时 SQLite 数据库，不读写 instance/ai_qa_service.db。
"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.models import db  # noqa: E402
from backend.app import create_app  # noqa: E402


class EModuleSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix='aiqa_test_')
        db.close()
        db.init(os.path.join(cls.tmpdir, 'test.db'))
        cls.app = create_app('testing')
        cls.app.config['API_KEYS'] = 'demo-api-key'
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        db.close()

    # ---------- 开放 API 鉴权 ----------
    def test_api_key_missing_returns_401(self):
        resp = self.client.post('/api/v1/chat', json={'question': '如何查询订单？'})
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['code'], 401)

    def test_api_key_invalid_returns_401(self):
        resp = self.client.get('/api/v1/stats', headers={'X-API-Key': 'wrong-key'})
        self.assertEqual(resp.status_code, 401)

    # ---------- 开放 API 业务 ----------
    def test_api_chat_hits_template(self):
        resp = self.client.post(
            '/api/v1/chat',
            json={'question': '如何查询订单？', 'session_id': 'test-001', 'scene_type': 'ordering'},
            headers={'X-API-Key': 'demo-api-key'},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body['code'], 200)
        data = body['data']
        self.assertTrue(data['answer'])
        self.assertEqual(data['is_quick_reply'], 1)
        self.assertGreaterEqual(data['confidence'], 0.75)

    def test_api_chat_rejects_empty_question(self):
        resp = self.client.post(
            '/api/v1/chat', json={'question': '  '}, headers={'X-API-Key': 'demo-api-key'}
        )
        self.assertEqual(resp.status_code, 400)

    def test_api_quick_reply_announcement_stats(self):
        headers = {'X-API-Key': 'demo-api-key'}
        quick = self.client.get('/api/v1/quick-reply?scene_type=ordering', headers=headers)
        self.assertEqual(quick.status_code, 200)
        self.assertGreaterEqual(len(quick.get_json()['data']), 1)

        announcement = self.client.get('/api/v1/announcement', headers=headers)
        self.assertEqual(announcement.status_code, 200)
        self.assertIsNotNone(announcement.get_json()['data'])

        stats = self.client.get('/api/v1/stats', headers=headers)
        self.assertEqual(stats.status_code, 200)
        self.assertIn('total_messages', stats.get_json()['data'])

    # ---------- 小程序依赖链路 ----------
    def _wx_login(self):
        resp = self.client.post('/api/auth/wx-login', json={'code': 'test-code'})
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()['data']['token']

    def test_wx_login_profile_and_scenes(self):
        token = self._wx_login()
        headers = {'Authorization': 'Bearer ' + token}
        profile = self.client.get('/api/auth/profile', headers=headers)
        self.assertEqual(profile.status_code, 200)
        scenes = self.client.get('/api/chat/scenes', headers=headers)
        self.assertEqual(scenes.status_code, 200)
        self.assertEqual(len(scenes.get_json()['data']), 5)

    def test_miniprogram_chat_flow(self):
        token = self._wx_login()
        headers = {'Authorization': 'Bearer ' + token}

        created = self.client.post(
            '/api/chat/conversations',
            json={'title': '新对话', 'scene_type': 'ordering'},
            headers=headers,
        )
        self.assertEqual(created.status_code, 200)
        conversation_id = created.get_json()['data']['id']

        sent = self.client.post(
            '/api/chat/conversations/%d/messages' % conversation_id,
            json={'content': '订单什么时候发货？'},
            headers=headers,
        )
        self.assertEqual(sent.status_code, 200)
        data = sent.get_json()['data']
        self.assertEqual(data['user_message']['role'], 'user')
        self.assertEqual(data['assistant_message']['role'], 'assistant')

        history = self.client.get(
            '/api/chat/conversations/%d' % conversation_id, headers=headers
        )
        self.assertEqual(history.status_code, 200)
        self.assertGreaterEqual(len(history.get_json()['data']['messages']), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
