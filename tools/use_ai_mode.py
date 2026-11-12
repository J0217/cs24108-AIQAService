# -*- coding: utf-8 -*-
"""
一键切换 AI 后端：本地模拟服务 <-> 真实大模型服务商

演示场景建议：
    1. 先用 --mock 切到本地模拟服务，跑通全流程、录制视频；
    2. 需要展示"真实模型"时用 --real 切回服务商，问 1~2 个问题即可。

用法：
    py -3.14 tools/use_ai_mode.py --mock
    py -3.14 tools/use_ai_mode.py --real
    py -3.14 tools/use_ai_mode.py --real --base-url https://api.deepseek.com/v1 --model deepseek-chat
    py -3.14 tools/use_ai_mode.py --status

说明：只修改 .env 中的 AI_API_BASE_URL / AI_MODEL 两行，不动 AI_API_KEY，
      因此不需要重新粘贴 key。切换后必须重启后端才生效。
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT, '.env')
BACKUP_PATH = os.path.join(ROOT, 'instance', 'ai_mode_backup.json')

MOCK_BASE_URL = 'http://127.0.0.1:5001/v1'
MOCK_MODEL = 'mock-qa-1.0'
MOCK_HEALTH = 'http://127.0.0.1:5001/health'


def read_env():
    if not os.path.exists(ENV_PATH):
        sys.exit('未找到 .env，请先执行: Copy-Item .env.example .env')
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        return f.read().splitlines()


def env_value(lines, name):
    for line in lines:
        if line.startswith(name + '='):
            return line.split('=', 1)[1].strip()
    return ''


def write_env(lines):
    with open(ENV_PATH, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def set_value(lines, name, value):
    for i, line in enumerate(lines):
        if line.startswith(name + '='):
            lines[i] = f'{name}={value}'
            return lines
    lines.append(f'{name}={value}')
    return lines


def backup_real(base_url, model):
    os.makedirs(os.path.dirname(BACKUP_PATH), exist_ok=True)
    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        json.dump({'base_url': base_url, 'model': model}, f, ensure_ascii=False, indent=2)


def load_backup():
    try:
        with open(BACKUP_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('base_url'), data.get('model')
    except (OSError, ValueError):
        return None, None


def mock_alive():
    try:
        with urllib.request.urlopen(MOCK_HEALTH, timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--mock', action='store_true', help='切到本地模拟模型服务')
    group.add_argument('--real', action='store_true', help='切回真实大模型服务商')
    group.add_argument('--status', action='store_true', help='查看当前配置')
    parser.add_argument('--base-url', default=None, help='--real 时指定服务地址')
    parser.add_argument('--model', default=None, help='--real 时指定模型名')
    args = parser.parse_args()

    lines = read_env()
    cur_base = env_value(lines, 'AI_API_BASE_URL')
    cur_model = env_value(lines, 'AI_MODEL')

    if args.status:
        is_mock = '127.0.0.1' in cur_base or 'localhost' in cur_base
        print(f'当前模式   : {"本地模拟服务" if is_mock else "真实服务商"}')
        print(f'base_url   : {cur_base}')
        print(f'model      : {cur_model}')
        if is_mock:
            print(f'模拟服务状态: {"运行中" if mock_alive() else "未启动（先运行 tools/mock_llm_server.py）"}')
        else:
            print(f'已备份真实配置: {"是" if load_backup()[0] else "否"}')
        return

    if args.mock:
        if '127.0.0.1' not in cur_base and 'localhost' not in cur_base:
            backup_real(cur_base, cur_model)
            print(f'已备份真实配置: {cur_base} / {cur_model}')
        lines = set_value(lines, 'AI_API_BASE_URL', MOCK_BASE_URL)
        lines = set_value(lines, 'AI_MODEL', MOCK_MODEL)
        write_env(lines)
        print('已切换到【本地模拟模型】')
        print(f'  AI_API_BASE_URL={MOCK_BASE_URL}')
        print(f'  AI_MODEL={MOCK_MODEL}')
        if not mock_alive():
            print('\n[!] 本地模拟服务尚未启动，请在另一个窗口运行：')
            print('    py -3.14 tools/mock_llm_server.py')
        return

    # --real
    if '127.0.0.1' not in cur_base and 'localhost' not in cur_base and not args.base_url:
        print(f'当前已是真实服务商配置：{cur_base} / {cur_model}')
        return

    base, model = load_backup()
    base = args.base_url or base
    model = args.model or model
    if not base or not model:
        sys.exit('没有找到可恢复的真实配置，请用 --base-url 和 --model 显式指定')
    lines = set_value(lines, 'AI_API_BASE_URL', base)
    lines = set_value(lines, 'AI_MODEL', model)
    write_env(lines)
    print('已切换回【真实大模型服务商】')
    print(f'  AI_API_BASE_URL={base}')
    print(f'  AI_MODEL={model}')
    print('\n提示：服务商可能限流，演示前可用 tools/prewarm_cache.py 预热缓存。')


if __name__ == '__main__':
    main()
