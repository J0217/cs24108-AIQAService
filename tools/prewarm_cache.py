# -*- coding: utf-8 -*-
"""
演示缓存预热脚本

做的事情：把「答辩时要问的问题」提前问一遍后端，让大模型的回答落进回复缓存。
之后现场演示同一个问题，会直接命中缓存（毫秒级、不消耗 token、不受服务商限流影响）。

用法（后端必须已启动）：
    py -3.14 tools/prewarm_cache.py
    py -3.14 tools/prewarm_cache.py --base http://127.0.0.1:5000/api
    py -3.14 tools/prewarm_cache.py --delay 6     # 服务商限流严时把间隔调大

缓存文件：instance/ai_reply_cache.json（默认 24 小时有效）
"""
import argparse
import json
import time
import urllib.error
import urllib.request

# 演示脚本里要问的问题，按场景分组；模板能答的会自动走模板，不必预热
DEMO_QUESTIONS = {
    'general': [
        '你们这套智能客服系统背后用的是什么大模型？',
        '用一句话介绍你自己',
        '如果系统答不上来，会怎么处理？',
    ],
    'ordering': [
        '我上周买的东西到现在还没收到，能帮我看看吗',
    ],
    'after_sales': [
        '商品拆封了还能退吗',
    ],
    'product': [
        '我们团队 20 人左右，选哪个套餐比较合适',
    ],
}


def http_json(url, method='GET', payload=None, token=None):
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:5000/api')
    parser.add_argument('--delay', type=float, default=4.0, help='两次模型调用之间的间隔秒数')
    args = parser.parse_args()
    base = args.base.rstrip('/')

    print(f'后端地址: {base}')
    try:
        login = http_json(base + '/auth/wx-login', 'POST', {'code': 'prewarm-cache'})
    except (urllib.error.URLError, OSError) as e:
        raise SystemExit(f'无法连接后端（{e}），请先启动: py -3.14 backend/app.py')
    if login.get('code') != 200:
        raise SystemExit(f'登录失败: {login}')
    token = login['data']['token']
    print('登录成功，开始预热\n')

    total = ok = cached_hits = 0
    for scene, questions in DEMO_QUESTIONS.items():
        conv = http_json(base + '/chat/conversations', 'POST', {'scene_type': scene}, token)
        if conv.get('code') != 200:
            print(f'[跳过] 场景 {scene} 建会话失败: {conv.get("message")}')
            continue
        conv_id = conv['data']['id']
        for question in questions:
            total += 1
            try:
                res = http_json(f'{base}/chat/conversations/{conv_id}/messages',
                                'POST', {'content': question}, token)
            except (urllib.error.URLError, OSError) as e:
                print(f'[失败] {question[:20]} -> {e}')
                continue
            if res.get('code') != 200:
                print(f'[失败] {question[:20]} -> {res.get("message")}')
                continue
            msg = res['data']['assistant_message']
            quick = msg.get('is_quick_reply')
            ms = msg.get('response_time') or 0
            if quick:
                tag = '模板'
            elif ms < 100:
                tag = '缓存'
                cached_hits += 1
            else:
                tag = '模型'
                ok += 1
            print(f'[{tag}] {scene:10s} {ms:7.0f}ms  {question[:26]}')
            time.sleep(args.delay)

    print(f'\n完成：共 {total} 问，模型生成 {ok} 条已写入缓存，命中已有缓存 {cached_hits} 条。')
    print('缓存文件: instance/ai_reply_cache.json')
    print('现场演示同样的问题即可毫秒级返回，且不再请求服务商。')


if __name__ == '__main__':
    main()
