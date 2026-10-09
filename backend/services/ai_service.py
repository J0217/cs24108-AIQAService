# -*- coding: utf-8 -*-
"""
AI服务 - 调用AI生成智能回复
"""
import time
import json
import logging
from typing import List, Tuple
import requests

logger = logging.getLogger(__name__)


class AIService:
    """AI问答服务"""

    def __init__(self, api_key=None, base_url=None, model=None):
        from flask import current_app
        self.api_key = api_key or current_app.config.get('AI_API_KEY')
        self.base_url = base_url or current_app.config.get('AI_API_BASE_URL', 'https://api.openai.com/v1')
        self.model = model or current_app.config.get('AI_MODEL', 'gpt-3.5-turbo')
        self.quick_replies = self._load_quick_replies()

    def _load_quick_replies(self) -> List[dict]:
        """加载快捷回复模板"""
        try:
            from ..models import QuickReply
            replies = QuickReply.select().where(QuickReply.status == 1)
            return [{'question': r.question, 'answer': r.answer,
                     'keywords': r.keywords.split(',') if r.keywords else []}
                    for r in replies]
        except Exception as e:
            logger.warning(f'加载快捷回复失败: {e}')
            return []

    def generate_reply(self, content: str, history: List[dict] = None,
                       scene_type: str = 'general',
                       max_tokens: int = 2000,
                       temperature: float = 0.7) -> Tuple[str, float, float]:
        """生成AI回复，返回 (回复内容, 置信度, 响应时间毫秒)"""
        start_time = time.time()

        try:
            # 先尝试匹配快捷回复
            quick_reply, confidence = self._match_quick_reply(content, scene_type)
            if confidence > 0.8:
                response_time = (time.time() - start_time) * 1000
                return quick_reply, confidence, response_time

            # 调用AI API
            reply, ai_confidence = self._call_ai_api(content, history, scene_type, max_tokens, temperature)
            response_time = (time.time() - start_time) * 1000
            final_confidence = max(confidence, ai_confidence)
            return reply, final_confidence, response_time

        except Exception as e:
            logger.error(f'AI回复生成失败: {e}')
            default_reply = self._get_default_reply(scene_type)
            response_time = (time.time() - start_time) * 1000
            return default_reply, 0.3, response_time

    def _match_quick_reply(self, content: str, scene_type: str) -> Tuple[str, float]:
        """匹配快捷回复"""
        content_lower = content.lower()
        scene_replies = [r for r in self.quick_replies
                         if r.get('scene_type') == scene_type or not r.get('scene_type')]

        best_match, best_confidence = None, 0.0

        for reply in scene_replies:
            keywords = reply.get('keywords', [])
            keyword_score = sum(1 for kw in keywords if kw and kw in content_lower)
            if keyword_score > 0:
                question = reply.get('question', '').lower()
                if question in content_lower or content_lower in question:
                    match_confidence = 0.95
                else:
                    match_confidence = min(0.8, 0.5 + keyword_score * 0.1)
                if match_confidence > best_confidence:
                    best_confidence = match_confidence
                    best_match = reply.get('answer')

        return best_match or '', best_confidence

    def _call_ai_api(self, content: str, history: List[dict], scene_type: str,
                     max_tokens: int, temperature: float) -> Tuple[str, float]:
        """调用AI API"""
        system_prompt = self._build_system_prompt(scene_type)
        messages = [{'role': 'system', 'content': system_prompt}]
        if history:
            messages.extend(history)
        messages.append({'role': 'user', 'content': content})

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        payload = {'model': self.model, 'messages': messages,
                   'max_tokens': max_tokens, 'temperature': temperature}

        response = requests.post(f'{self.base_url}/chat/completions',
                                 headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        reply = response.json()['choices'][0]['message']['content'].strip()
        confidence = self._estimate_confidence(content, reply)
        return reply, confidence

    def _build_system_prompt(self, scene_type: str) -> str:
        """构建系统提示词"""
        prompts = {
            'general': '你是一个智能客服助手，请友好、专业地回答用户的问题。',
            'product': '你是一个产品咨询顾问，请详细、准确地介绍产品功能。',
            'after_sales': '你是一个售后服务专员，请耐心解决用户的问题。',
            'technical': '你是一个技术支持工程师，请专业地解答技术问题。',
            'ordering': '你是一个订单客服，请帮助用户查询订单状态。'
        }
        return prompts.get(scene_type, prompts['general'])

    def _estimate_confidence(self, content: str, reply: str) -> float:
        """估算回复置信度"""
        confidence = 0.7
        if 20 < len(reply) < 500:
            confidence += 0.1
        if any(word in reply.lower() for word in ['您', '请', '可以', '需要', '建议']):
            confidence += 0.05
        if '不知道' not in reply and '无法' not in reply and '不清楚' not in reply:
            confidence += 0.05
        return min(confidence, 0.95)

    def _get_default_reply(self, scene_type: str) -> str:
        """获取默认回复"""
        defaults = {
            'general': '抱歉，我暂时无法回答这个问题。请联系人工客服获取帮助。',
            'product': '关于产品咨询，建议您提供更多详细信息，或联系产品顾问。',
            'after_sales': '感谢您的反馈！我们会尽快为您处理售后服务问题。',
            'technical': '技术问题需要专业支持，请您留下联系方式，技术团队会尽快与您联系。',
            'ordering': '关于订单问题，请提供订单号，我们会尽快为您查询处理。'
        }
        return defaults.get(scene_type, defaults['general'])
