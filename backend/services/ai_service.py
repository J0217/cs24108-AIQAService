# -*- coding: utf-8 -*-
"""
AI服务 - 场景智能匹配快捷回复模板 + AI大模型生成回复
"""
import re
import time
import logging
from difflib import SequenceMatcher
from typing import List, Tuple
import requests

logger = logging.getLogger(__name__)

# 快捷回复命中阈值：达到该置信度直接使用模板，无需调用大模型
QUICK_REPLY_THRESHOLD = 0.75

# 占位 Key 前缀（注意：不能把空字符串放进来，否则任何 Key 都会被判定为占位）
_PLACEHOLDER_PREFIXES = ('your-', 'sk-your', 'sk-xxx', 'xxx', 'demo', 'none', 'change-me')

# 送入大模型的上下文消息条数上限
DEFAULT_HISTORY_LIMIT = 10


class AIService:
    """AI问答服务"""

    def __init__(self, api_key=None, base_url=None, model=None):
        from flask import current_app
        self.api_key = api_key or current_app.config.get('AI_API_KEY', '')
        self.base_url = base_url or current_app.config.get('AI_API_BASE_URL', 'https://api.openai.com/v1')
        self.model = model or current_app.config.get('AI_MODEL', 'gpt-3.5-turbo')
        self.timeout = current_app.config.get('AI_TIMEOUT', 30)
        self.history_limit = current_app.config.get('AI_HISTORY_LIMIT', DEFAULT_HISTORY_LIMIT)
        self.quick_replies = self._load_quick_replies()

    # ==================== 快捷回复模板 ====================
    def _load_quick_replies(self) -> List[dict]:
        """加载启用的快捷回复模板（含场景、关键词）"""
        try:
            from ..models import QuickReply
            replies = QuickReply.select().where(QuickReply.status == 1)
            return [{
                'id': r.id,
                'question': r.question,
                'answer': r.answer,
                'scene_type': r.scene_type,
                'keywords': [kw.strip() for kw in r.keywords.split(',') if kw.strip()]
            } for r in replies]
        except Exception as e:
            logger.warning(f'加载快捷回复失败: {e}')
            return []

    @staticmethod
    def _normalize(text: str) -> str:
        """去除标点与空白，统一小写，便于相似度计算"""
        return re.sub(r'[\s，。！？、,.!?;:；：""\'\'（）()【】\[\]]', '', (text or '').lower())

    def _match_quick_reply(self, content: str, scene_type: str) -> Tuple[str, float, int]:
        """按场景 + 关键词 + 问题相似度匹配模板，返回 (答案, 置信度, 模板ID)"""
        content_norm = self._normalize(content)
        if not content_norm:
            return '', 0.0, 0

        candidates = [r for r in self.quick_replies
                      if r.get('scene_type') in (scene_type, 'general', '', None)]

        best_answer, best_confidence, best_id = '', 0.0, 0
        for reply in candidates:
            question_norm = self._normalize(reply.get('question', ''))
            ratio = SequenceMatcher(None, content_norm, question_norm).ratio() if question_norm else 0.0
            matched_keywords = [kw for kw in reply.get('keywords', []) if kw and kw.lower() in content_norm]

            if ratio >= 0.9:
                confidence = 0.95
            elif ratio >= 0.7:
                confidence = 0.85
            elif len(matched_keywords) >= 2:
                confidence = min(0.9, 0.6 + len(matched_keywords) * 0.1)
            elif len(matched_keywords) == 1:
                confidence = 0.6 + ratio * 0.15
            elif ratio >= 0.5:
                confidence = 0.55
            else:
                confidence = 0.0

            # 同场景模板优先于通用模板（避免通用模板抢答）
            if confidence and reply.get('scene_type') == scene_type:
                confidence = min(confidence + 0.05, 0.95)

            if confidence > best_confidence:
                best_confidence = confidence
                best_answer = reply.get('answer', '')
                best_id = reply.get('id', 0)

        return best_answer, best_confidence, best_id

    @staticmethod
    def _increase_usage(template_id: int):
        """模板命中计数 +1"""
        if not template_id:
            return
        try:
            from ..models import QuickReply
            QuickReply.update(usage_count=QuickReply.usage_count + 1).where(
                QuickReply.id == template_id).execute()
        except Exception as e:
            logger.warning(f'更新模板使用次数失败: {e}')

    # ==================== 回复生成 ====================
    def generate_reply(self, content: str, history: List[dict] = None,
                       scene_type: str = 'general',
                       max_tokens: int = None,
                       temperature: float = None) -> Tuple[str, float, float, int]:
        """
        生成回复，策略优先级：
            1) 场景模板高置信命中（>=0.75）→ 直接返回模板，省 token、响应快
            2) 已配置大模型 → 调用 AI 生成（模板不再覆盖 AI 结果）
            3) AI 未配置或调用失败 → 低置信模板兜底
            4) 全无命中 → 场景默认话术
        :return: (回复内容, 置信度, 响应时间毫秒, 是否命中快捷模板 1/0)
        """
        from flask import current_app
        max_tokens = max_tokens or current_app.config.get('AI_MAX_TOKENS', 2000)
        temperature = current_app.config.get('AI_TEMPERATURE', 0.7) if temperature is None else temperature
        start_time = time.time()
        history = list(history or [])
        if len(history) > self.history_limit:
            history = history[-self.history_limit:]

        # 1. 场景模板匹配
        template_answer, template_confidence, template_id = self._match_quick_reply(content, scene_type)

        # 1) 高置信模板直接返回
        if template_answer and template_confidence >= QUICK_REPLY_THRESHOLD:
            self._increase_usage(template_id)
            response_time = (time.time() - start_time) * 1000
            logger.info('命中快捷模板(id=%s) 置信度=%.2f', template_id, template_confidence)
            return template_answer, template_confidence, response_time, 1

        # 2) 已配置大模型：调用 AI，成功则以其结果为准
        if self._ai_configured():
            try:
                reply, ai_confidence = self._call_ai_api(
                    content, history, scene_type, max_tokens, temperature)
                if reply:
                    response_time = (time.time() - start_time) * 1000
                    logger.info('大模型回复成功，置信度=%.2f，耗时=%.0fms', ai_confidence, response_time)
                    return reply, ai_confidence, response_time, 0
                logger.warning('大模型返回空内容，降级为模板/兜底')
            except Exception as e:
                logger.error('AI回复生成失败，降级为模板/兜底: %s', e)
        else:
            logger.info('未配置有效 AI_API_KEY，使用本地模板兜底')

        # 3) 低置信模板兜底
        response_time = (time.time() - start_time) * 1000
        if template_answer:
            self._increase_usage(template_id)
            return template_answer, max(template_confidence, 0.6), response_time, 1

        # 4) 场景默认话术
        return self._get_default_reply(scene_type), 0.3, response_time, 0

    def _ai_configured(self) -> bool:
        """判断是否配置了可用的大模型 Key（排除空值与占位值）"""
        key = (self.api_key or '').strip()
        if len(key) < 8:
            return False
        lowered = key.lower()
        return not any(lowered.startswith(prefix) for prefix in _PLACEHOLDER_PREFIXES)

    def _call_ai_api(self, content: str, history: List[dict], scene_type: str,
                     max_tokens: int, temperature: float) -> Tuple[str, float]:
        """调用 OpenAI Compatible API"""
        system_prompt = self._build_system_prompt(scene_type)
        messages = [{'role': 'system', 'content': system_prompt}]
        if history:
            messages.extend(history[-self.history_limit:])  # 控制上下文长度
        messages.append({'role': 'user', 'content': content})

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        payload = {'model': self.model, 'messages': messages,
                   'max_tokens': max_tokens, 'temperature': temperature}

        response = requests.post(f'{self.base_url}/chat/completions',
                                 headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()

        reply = response.json()['choices'][0]['message']['content'].strip()
        confidence = self._estimate_confidence(content, reply)
        return reply, confidence

    def _build_system_prompt(self, scene_type: str) -> str:
        """构建场景化系统提示词"""
        prompts = {
            'general': '你是一个友好、专业的智能客服助手，请用简洁的中文回答用户的问题。',
            'product': '你是一个产品咨询顾问，请详细、准确地介绍产品功能与套餐，并给出购买建议。',
            'after_sales': '你是一个售后服务专员，请耐心解决用户的退换货、退款等售后问题。',
            'technical': '你是一个技术支持工程师，请专业地解答技术问题，必要时引导用户提供报错信息。',
            'ordering': '你是一个订单客服，请帮助用户查询订单状态、发货与物流进度。'
        }
        return prompts.get(scene_type, prompts['general'])

    def _estimate_confidence(self, content: str, reply: str) -> float:
        """估算回复置信度"""
        confidence = 0.7
        if 20 < len(reply) < 500:
            confidence += 0.1
        if any(word in reply for word in ['您', '请', '可以', '需要', '建议']):
            confidence += 0.05
        if '不知道' not in reply and '无法' not in reply and '不清楚' not in reply:
            confidence += 0.05
        return min(confidence, 0.95)

    def _get_default_reply(self, scene_type: str) -> str:
        """获取场景默认兜底回复"""
        defaults = {
            'general': '抱歉，我暂时无法回答这个问题。您可以换个说法，或联系人工客服获取帮助。',
            'product': '关于产品咨询，建议您提供更详细的需求，或联系产品顾问获取专业建议。',
            'after_sales': '感谢您的反馈！请提供订单号，我们会尽快为您处理售后问题。',
            'technical': '技术问题需要进一步排查，请描述具体报错信息，技术团队会尽快与您联系。',
            'ordering': '关于订单问题，请提供订单号，我会尽快为您查询处理。'
        }
        return defaults.get(scene_type, defaults['general'])
