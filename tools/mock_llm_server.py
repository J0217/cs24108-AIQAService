# -*- coding: utf-8 -*-
"""
本地模拟大模型服务（OpenAI 兼容）

用途：演示/答辩时不依赖外网服务商，避免 429 限流、超时、欠费导致演示翻车。
它实现了与 OpenAI 完全一致的 /v1/chat/completions 协议，因此后端的调用代码
一行都不用改，只把 AI_API_BASE_URL 指向本地即可。

启动：
    py -3.14 tools/mock_llm_server.py            # 默认 5001 端口
    py -3.14 tools/mock_llm_server.py --port 5002

配合 .env：
    AI_API_KEY=mock-local-key
    AI_API_BASE_URL=http://127.0.0.1:5001/v1
    AI_MODEL=mock-qa-1.0

注意：这是"协议级模拟"，不是真模型。演示时如需展示真实模型能力，
把 .env 切回真实服务商即可（见 docs/演示模式说明.md）。
"""
import argparse
import hashlib
import json
import random
import re
import time

from flask import Flask, jsonify, request

app = Flask(__name__)

# 模拟首 token 延迟区间（毫秒），让演示看起来像真的在"思考"
LATENCY_RANGE = (350, 900)

SCENE_HINTS = {
    'ordering': '订单',
    'after_sales': '售后',
    'product': '产品',
    'technical': '技术',
    'general': '咨询',
}


def _pick(seed_text, options):
    """按输入文本稳定地选一个，保证同一问题重复问答案一致（便于演示复现）"""
    digest = hashlib.md5(seed_text.encode('utf-8')).hexdigest()
    return options[int(digest[:8], 16) % len(options)]


def _compose(user_text, scene):
    """根据用户问题拼一段像人话的回复。

    真模型做不到本地复现，这里的目标是：语义相关、结构完整、可被追问，
    足以支撑"发消息 -> 收到回复 -> 落库"的演示链路。
    """
    topic = SCENE_HINTS.get(scene, '咨询')
    text = user_text.strip()
    short = text[:24]

    if re.search(r'什么模型|哪个模型|大模型|底层', text):
        body = (
            '我这边接入的是 OpenAI 兼容的对话服务，通过 HTTP 调用 chat/completions 接口，'
            '模型名由配置项 AI_MODEL 指定，换成别家服务商只需要改 base_url 和模型名两行配置。'
        )
    elif re.search(r'你好|hi|hello|在吗', text, re.I):
        body = '您好，我在的。请直接说您的问题，我会尽量给出可操作的答复。'
    elif re.search(r'订单|物流|发货|快递|收货|没收到|还没到|签收', text):
        body = (
            '查询订单需要订单号。您可以在「我的-全部订单」里找到订单号，'
            '发给我之后我帮您查看当前状态；如果已发货，物流信息通常在下单后 24 小时内更新。'
        )
    elif re.search(r'退|换|退款|售后', text):
        body = (
            '退换货请在签收后 7 天内发起，商品需保持不影响二次销售的状态。'
            '您把订单号和退货原因发我，我先帮您登记，再按流程安排上门取件。'
        )
    elif re.search(r'价格|多少钱|套餐|优惠', text):
        body = (
            '我们的套餐分基础版、专业版和企业版，差异主要在并发数和是否支持私有化部署。'
            '如果方便，说一下您的使用人数和场景，我给您推荐更合适的一档。'
        )
    elif re.search(r'报错|错误|异常|失败|bug', text, re.I):
        body = (
            '这类问题通常需要看具体报错。请把报错信息、操作步骤和发生时间发给我，'
            '我先做初步定位；如果涉及服务端日志，我会同步给技术同学跟进。'
        )
    else:
        body = _pick(text, [
            f'关于「{short}」，我理解您想确认的是具体处理方式。',
            f'您提到「{short}」，这属于{topic}范围内的问题，我可以帮您梳理一下。',
        ]) + '为了给出准确答复，麻烦补充一下具体场景或单号，我再逐条说明。'

    return body


@app.route('/v1/models', methods=['GET'])
def models():
    return jsonify({'object': 'list', 'data': [
        {'id': 'mock-qa-1.0', 'object': 'model', 'owned_by': 'local'}
    ]})


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    payload = request.get_json(silent=True) or {}
    messages = payload.get('messages') or []
    model = payload.get('model', 'mock-qa-1.0')

    system_text = next((m.get('content', '') for m in messages if m.get('role') == 'system'), '')
    user_text = next((m.get('content', '') for m in reversed(messages) if m.get('role') == 'user'), '')

    scene = 'general'
    if '订单客服' in system_text:
        scene = 'ordering'
    elif '售后' in system_text:
        scene = 'after_sales'
    elif '产品' in system_text:
        scene = 'product'
    elif '技术支持' in system_text:
        scene = 'technical'

    time.sleep(random.randint(*LATENCY_RANGE) / 1000.0)

    answer = _compose(user_text, scene)
    prompt_tokens = sum(len(m.get('content', '')) for m in messages) // 2
    completion_tokens = len(answer) // 2

    return jsonify({
        'id': 'chatcmpl-mock-' + hashlib.md5(user_text.encode('utf-8')).hexdigest()[:12],
        'object': 'chat.completion',
        'created': int(time.time()),
        'model': model,
        'choices': [{
            'index': 0,
            'message': {'role': 'assistant', 'content': answer},
            'finish_reason': 'stop'
        }],
        'usage': {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens
        }
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'mock-llm', 'latency_ms': LATENCY_RANGE})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5001)
    args = parser.parse_args()
    print(f'[mock-llm] OpenAI 兼容模拟服务已启动: http://127.0.0.1:{args.port}/v1')
    print(f'[mock-llm] 接口: POST /v1/chat/completions  GET /v1/models  GET /health')
    app.run(host='127.0.0.1', port=args.port, debug=False, use_reloader=False)
