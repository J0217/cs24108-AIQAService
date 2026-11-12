# -*- coding: utf-8 -*-
"""
改进项回归测试（与 test_e_module.py 的 7 条冒烟用例互补）

运行：
    python test/test_improvements.py -v

覆盖：
    1. AI 服务：真实 Key 判定、占位 Key 判定
    2. AI 服务：大模型回复不被弱匹配模板覆盖
    3. AI 服务：大模型调用失败时降级为模板/兜底
    4. 接口：未知路径返回 JSON 404 而非 HTML
    5. 接口：跨用户访问会话被拒绝（越权防护）
    6. 接口：切换场景新建会话，旧会话消息不被改写
    7. 接口：超长消息被拒绝（400）
    8. 接口：开放 API 触发限流返回 429
    9. 公告：标记已读后未读数下降
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend.models import db  # noqa: E402
from backend.app import create_app  # noqa: E402
from backend.services.ai_service import AIService  # noqa: E402
from backend.utils.ratelimit import limiter  # noqa: E402

API_KEY = 'demo-api-key'
REAL_AI_KEY = 'sk-test-0123456789abcdef'


class _BaseCase(unittest.TestCase):
    """测试基类：临时数据库 + 独立 app 上下文"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix='aiqa_improve_')
        db.close()
        db.init(os.path.join(cls.tmpdir, 'test.db'))
        cls.app = create_app('testing')
        cls.app.config['API_KEYS'] = API_KEY
        cls.app.config['RATE_LIMIT_ENABLED'] = False  # 默认关闭，个别用例单独打开
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()
        db.close()


class AIServiceTestCase(_BaseCase):
    """AI 服务逻辑测试（不访问真实网络）"""

    def test_real_key_is_configured(self):
        self.assertTrue(AIService(api_key=REAL_AI_KEY)._ai_configured())

    def test_placeholder_keys_are_not_configured(self):
        for key in ['', '   ', 'your-ai-api-key-here', 'demo-api-key', 'none', 'change-me']:
            self.assertFalse(AIService(api_key=key)._ai_configured(), f'{key!r} 不应被判定为已配置')

    def _fake_completion(self, content):
        response = mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {'choices': [{'message': {'content': content}}]}
        return response

    def setUp(self):
        AIService.clear_cache()  # 用例之间不共享回复缓存

    def test_ai_reply_is_cached_and_second_call_skips_model(self):
        """同一问题第二次提问命中缓存，不再请求模型（规避服务商限流、省 token）"""
        service = AIService(api_key=REAL_AI_KEY)
        with mock.patch('backend.services.ai_service.requests.post',
                        return_value=self._fake_completion('这是模型生成的回答，请提供订单号。')) as mocked:
            first = service.generate_reply('想咨询一个缓存相关问题', scene_type='general')
            second = service.generate_reply('想咨询一个缓存相关问题', scene_type='general')

        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(first[0], second[0])
        self.assertEqual(second[3], 0)          # 仍是模型答案，不是模板
        self.assertLessEqual(second[2], first[2])  # 缓存命中不快于首次

    def test_ai_cache_can_be_disabled(self):
        """AI_CACHE_ENABLED=False 时每次都请求模型"""
        service = AIService(api_key=REAL_AI_KEY)
        self.app.config['AI_CACHE_ENABLED'] = False
        try:
            with mock.patch('backend.services.ai_service.requests.post',
                            return_value=self._fake_completion('这是模型生成的回答。')) as mocked:
                service.generate_reply('关闭缓存后的提问', scene_type='general')
                service.generate_reply('关闭缓存后的提问', scene_type='general')
            self.assertEqual(mocked.call_count, 2)
        finally:
            self.app.config['AI_CACHE_ENABLED'] = True

    def test_ai_answer_not_overridden_by_weak_template(self):
        """弱匹配模板（<0.75）存在时，应以大模型结果为准"""
        service = AIService(api_key=REAL_AI_KEY)
        ai_text = '这是大模型生成的回答。'
        with mock.patch('backend.services.ai_service.requests.post',
                        return_value=self._fake_completion(ai_text)):
            reply, confidence, _, is_quick = service.generate_reply('服务时间', scene_type='general')

        self.assertEqual(reply, ai_text)
        self.assertEqual(is_quick, 0)
        self.assertGreater(confidence, 0.5)

    def test_high_confidence_template_skips_ai(self):
        """高置信模板命中时不应调用大模型"""
        service = AIService(api_key=REAL_AI_KEY)
        with mock.patch('backend.services.ai_service.requests.post') as mocked_post:
            reply, confidence, _, is_quick = service.generate_reply(
                '如何查询订单？', scene_type='ordering')
            mocked_post.assert_not_called()

        self.assertEqual(is_quick, 1)
        self.assertGreaterEqual(confidence, 0.75)
        self.assertIn('订单', reply)

    def test_ai_failure_falls_back_to_template(self):
        """大模型异常时降级到模板，服务不中断"""
        service = AIService(api_key=REAL_AI_KEY)
        with mock.patch('backend.services.ai_service.requests.post',
                        side_effect=requests.RequestException('timeout')):
            reply, confidence, _, is_quick = service.generate_reply('服务时间', scene_type='general')

        self.assertTrue(reply)
        self.assertEqual(is_quick, 1)

    def test_history_is_trimmed(self):
        """上下文只保留最近 N 条，避免 token 爆炸"""
        service = AIService(api_key=REAL_AI_KEY)
        service.history_limit = 3
        history = [{'role': 'user', 'content': f'历史{i}'} for i in range(20)]
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured['messages'] = json['messages']
            return self._fake_completion('好的')

        with mock.patch('backend.services.ai_service.requests.post', side_effect=fake_post):
            service.generate_reply('你好', history=history, scene_type='general')

        # system + 3 条历史 + 当前问题
        self.assertEqual(len(captured['messages']), 5)


class ApiImprovementTestCase(_BaseCase):
    """接口层改进项测试"""

    def _login(self):
        resp = self.client.post('/api/auth/wx-login', json={'code': 'test-code'})
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()['data']['token']

    def test_unknown_path_returns_json(self):
        resp = self.client.get('/api/not-exist')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()['code'], 404)

    def test_cross_user_conversation_is_forbidden(self):
        token_a = self._login()
        created = self.client.post('/api/chat/conversations', json={'scene_type': 'general'},
                                   headers={'Authorization': 'Bearer ' + token_a})
        conv_id = created.get_json()['data']['id']

        token_b = self._login()  # 另一个 mock openid = 另一个用户
        resp = self.client.get('/api/chat/conversations/%d' % conv_id,
                               headers={'Authorization': 'Bearer ' + token_b})
        self.assertEqual(resp.status_code, 404)

    def test_switching_scene_creates_new_conversation(self):
        token = self._login()
        headers = {'Authorization': 'Bearer ' + token}

        first = self.client.post('/api/chat/conversations', json={'scene_type': 'general'},
                                 headers=headers).get_json()['data']
        self.client.post('/api/chat/conversations/%d/messages' % first['id'],
                         json={'content': '如何查询订单？'}, headers=headers)

        # 切换场景 → 新建会话（后端不再改写历史会话的场景）
        second = self.client.post('/api/chat/conversations', json={'scene_type': 'technical'},
                                  headers=headers).get_json()['data']
        self.assertNotEqual(first['id'], second['id'])

        detail = self.client.get('/api/chat/conversations/%d' % first['id'], headers=headers)
        self.assertEqual(detail.get_json()['data']['conversation']['scene_type'], 'general')
        self.assertGreaterEqual(len(detail.get_json()['data']['messages']), 2)

    def test_too_long_message_is_rejected(self):
        token = self._login()
        headers = {'Authorization': 'Bearer ' + token}
        conv = self.client.post('/api/chat/conversations', json={}, headers=headers).get_json()['data']
        resp = self.client.post('/api/chat/conversations/%d/messages' % conv['id'],
                                json={'content': '啊' * 501}, headers=headers)
        self.assertEqual(resp.status_code, 400)

    def test_invalid_scene_type_falls_back(self):
        token = self._login()
        headers = {'Authorization': 'Bearer ' + token}
        conv = self.client.post('/api/chat/conversations',
                                json={'scene_type': 'not-a-scene'},
                                headers=headers).get_json()['data']
        self.assertEqual(conv['scene_type'], 'general')

    def test_open_api_rate_limit(self):
        limiter.reset()
        self.app.config['RATE_LIMIT_ENABLED'] = True
        self.app.config['RATE_LIMIT_PER_MINUTE'] = 2
        try:
            headers = {'X-API-Key': API_KEY}
            codes = [self.client.get('/api/v1/stats', headers=headers).status_code
                     for _ in range(3)]
            self.assertEqual(codes[:2], [200, 200])
            self.assertEqual(codes[2], 429)
        finally:
            self.app.config['RATE_LIMIT_ENABLED'] = False
            limiter.reset()

    def test_announcement_read_flow(self):
        token = self._login()
        headers = {'Authorization': 'Bearer ' + token}

        before = self.client.get('/api/announcement/unread-count', headers=headers).get_json()['data']
        self.assertGreaterEqual(before['unread_count'], 1)

        listing = self.client.get('/api/announcement/list', headers=headers).get_json()['data']
        ann_id = listing['list'][0]['id']
        self.client.post('/api/announcement/read/%d' % ann_id, headers=headers)

        after = self.client.get('/api/announcement/unread-count', headers=headers).get_json()['data']
        self.assertEqual(after['unread_count'], before['unread_count'] - 1)

    def test_announcement_invalid_time_returns_400(self):
        resp = self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
        admin_token = resp.get_json()['data']['token']
        bad = self.client.post('/api/announcement/', json={
            'title': '测试公告', 'content': '内容', 'start_time': '不是时间'
        }, headers={'Authorization': 'Bearer ' + admin_token})
        self.assertEqual(bad.status_code, 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)
