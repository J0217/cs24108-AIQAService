# -*- coding: utf-8 -*-
"""
AI Key 配置自检工具
用法：py -3.14 tools/check_ai_key.py

不启动 Flask，直接读 .env 并向服务商发一次最小请求，
用来说明「Key 到底有没有配对」。
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, '.env')


def mask(value):
    if not value:
        return '(空)'
    if len(value) <= 12:
        return value[:2] + '***'
    return value[:6] + '...' + value[-4:]


def main():
    if not os.path.exists(ENV_PATH):
        print('[×] 找不到 .env：' + ENV_PATH)
        print('    先在项目根目录执行：Copy-Item .env.example .env')
        return 2

    try:
        from dotenv import load_dotenv
    except ImportError:
        print('[×] 缺少 python-dotenv，执行：py -3.14 -m pip install python-dotenv')
        return 2

    load_dotenv(ENV_PATH, override=True)
    api_key = (os.getenv('AI_API_KEY') or '')
    base_url = (os.getenv('AI_API_BASE_URL') or '').rstrip('/')
    model = os.getenv('AI_MODEL') or ''

    print('配置文件 : ' + ENV_PATH)
    print('AI_API_KEY        = ' + mask(api_key))
    print('AI_API_BASE_URL   = ' + (base_url or '(空)'))
    print('AI_MODEL          = ' + (model or '(空)'))
    print('AI_TIMEOUT        = ' + (os.getenv('AI_TIMEOUT') or '(默认 30)'))
    print('-' * 56)

    problems = []
    if not api_key:
        problems.append('AI_API_KEY 为空')
    if api_key != api_key.strip():
        problems.append('key 首尾有空格，请删掉')
    if api_key[:1] in ('"', "'"):
        problems.append('key 带了引号，请删掉引号')
    if not base_url:
        problems.append('AI_API_BASE_URL 为空')
    if base_url.endswith('/chat/completions'):
        problems.append('AI_API_BASE_URL 不要带 /chat/completions')
    if not model:
        problems.append('AI_MODEL 为空')

    placeholders = ('your-', 'sk-your', 'sk-xxx', 'xxx', 'demo', 'none', 'change-me')
    if api_key and api_key.lower().startswith(placeholders):
        problems.append('key 仍是占位值，后端会判定为「未配置」，走本地模板')

    if problems:
        print('[!] 配置问题：')
        for p in problems:
            print('    - ' + p)
        print('-' * 56)

    if not api_key or api_key.lower().startswith(placeholders):
        print('结论：Key 未配置，系统会一直使用本地模板（这本身不算故障）。')
        return 1

    import requests
    url = base_url + '/chat/completions'
    print('请求地址 : ' + url)
    headers = {'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'}
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': '说一句你好'}],
        'max_tokens': 32,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        print('[×] 请求失败：' + str(exc))
        print('    检查网络、代理，或换服务商地址')
        return 3

    print('HTTP 状态 : ' + str(resp.status_code))
    if resp.status_code == 200:
        try:
            content = resp.json()['choices'][0]['message']['content'].strip()
        except Exception:
            content = resp.text[:200]
        print('模型回复 : ' + content)
        print('-' * 56)
        print('[√] 配置成功，后端重启后即可调用大模型')
        return 0

    print('响应内容 : ' + resp.text[:300])
    hints = {
        401: 'Key 无效或已删除，去控制台重新生成',
        402: '账户余额不足，去控制台充值',
        403: '该 Key 无权访问此模型',
        404: '地址或模型名不对：检查 AI_API_BASE_URL 是否多了路径，模型名是否已下线',
        429: '触发限流或超额，稍后重试',
    }
    print('-' * 56)
    print('[×] 失败提示：' + hints.get(resp.status_code, '查看服务商文档的错误码说明'))
    return 4


if __name__ == '__main__':
    sys.exit(main())
