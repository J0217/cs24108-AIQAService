# -*- coding: utf-8 -*-
"""
AI服务 - 场景智能匹配快捷回复模板 + AI大模型生成回复
"""
import json
import os
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

# 可重试的 HTTP 状态：多为服务商并发/配额抖动，退避后再试通常成功
_RETRYABLE_STATUS = (429, 500, 502, 503, 504)

# ==================== 大模型回复缓存 ====================
# 作用：同一问题第二次提问不再请求模型接口，从而
#   1) 规避演示现场的服务商限流（429）与网络抖动；
#   2) 省 token 费用（模板 -> 缓存 -> 模型 三级成本递减）；
#   3) 重复问题响应时间从「秒级」降到「毫秒级」。
# 键为「场景 + 归一化问题文本」，默认 24 小时过期，可落盘到 instance/ 下重启复用。
_CACHE = {}
_CACHE_MAX_ENTRIES = 500
_CACHE_LOADED = False
_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'instance', 'ai_reply_cache.json')


def _load_cache_from_disk():
    """启动时把未过期的缓存读回内存（文件不存在或损坏时静默跳过）"""
    global _CACHE_LOADED
    if _CACHE_LOADED:
        return
    _CACHE_LOADED = True
    try:
        with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        now = time.time()
        for key, item in data.items():
            if isinstance(item, dict) and item.get('expires_at', 0) > now:
                _CACHE[key] = item
        if _CACHE:
            logger.info('已加载大模型回复缓存 %d 条: %s', len(_CACHE), _CACHE_FILE)
    except (OSError, ValueError):
        pass


def _save_cache_to_disk():
    """缓存落盘，保证重启后预热结果仍然有效"""
    try:
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        tmp = _CACHE_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(_CACHE, f, ensure_ascii=False)
        os.replace(tmp, _CACHE_FILE)
    except OSError as e:
        logger.warning('回复缓存落盘失败: %s', e)


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

    # ==================== 回复缓存 ====================
    @staticmethod
    def clear_cache():
        """清空内存缓存（单元测试与「重置演示数据」时使用）"""
        global _CACHE_LOADED
        _CACHE.clear()
        _CACHE_LOADED = True  # 标记已加载，避免清空后又被磁盘旧数据回填

    def _cache_key(self, scene_type: str, content: str) -> str:
        return f'{scene_type}|{self._normalize(content)}'

    def _cache_get(self, key: str):
        """读取未过期的缓存项，命中时自增计数；未命中返回 None"""
        from flask import current_app
        if not current_app.config.get('AI_CACHE_ENABLED', True):
            return None
        _load_cache_from_disk()
        item = _CACHE.get(key)
        if not item:
            return None
        if item.get('expires_at', 0) <= time.time():
            _CACHE.pop(key, None)
            return None
        item['hits'] = item.get('hits', 0) + 1
        return item

    def _cache_set(self, key: str, answer: str, confidence: float):
        """写入缓存；测试环境不落盘，避免污染 instance/ 目录"""
        from flask import current_app
        if not current_app.config.get('AI_CACHE_ENABLED', True):
            return
        if len(_CACHE) >= _CACHE_MAX_ENTRIES:
            now = time.time()
            for stale in [k for k, v in _CACHE.items() if v.get('expires_at', 0) <= now]:
                _CACHE.pop(stale, None)
            if len(_CACHE) >= _CACHE_MAX_ENTRIES:
                _CACHE.pop(next(iter(_CACHE)), None)  # 仍然超限则淘汰最早的一条
        ttl = current_app.config.get('AI_CACHE_TTL', 86400)
        now = time.time()
        _CACHE[key] = {'answer': answer, 'confidence': confidence,
                       'created_at': now, 'expires_at': now + ttl, 'hits': 0}
        if not current_app.config.get('TESTING'):
            _save_cache_to_disk()

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

        # 2) 已配置大模型：先查缓存，未命中再调接口（缓存命中不消耗 token）
        if self._ai_configured():
            cache_key = self._cache_key(scene_type, content)
            cached = self._cache_get(cache_key)
            if cached:
                response_time = (time.time() - start_time) * 1000
                logger.info('命中回复缓存（累计 %d 次），跳过模型调用，耗时=%.0fms',
                            cached.get('hits', 1), response_time)
                return cached.get('answer', ''), cached.get('confidence', 0.85), response_time, 0
            try:
                reply, ai_confidence = self._call_ai_api(
                    content, history, scene_type, max_tokens, temperature)
                if reply:
                    self._cache_set(cache_key, reply, ai_confidence)
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

        endpoint = f'{str(self.base_url).rstrip("/")}/chat/completions'
        # 429/5xx 多为服务商并发或配额抖动，退避重试两次，避免演示时直接掉到兜底话术
        response = None
        for attempt in range(3):
            response = requests.post(endpoint, headers=headers, json=payload, timeout=self.timeout)
            if response.status_code not in _RETRYABLE_STATUS or attempt == 2:
                break
            wait = 1.5 * (attempt + 1)
            # 服务商通常会在 Retry-After 里给出建议等待秒数，优先采用（上限 8s，避免拖住演示）
            retry_after = response.headers.get('Retry-After') if response.headers else None
            if retry_after:
                try:
                    wait = min(float(retry_after), 8.0)
                except (TypeError, ValueError):
                    pass
            logger.warning('大模型接口返回 %s，%.1fs 后重试（第 %d 次）',
                           response.status_code, wait, attempt + 1)
            time.sleep(wait)
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
