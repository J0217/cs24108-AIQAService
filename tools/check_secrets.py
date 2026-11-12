# -*- coding: utf-8 -*-
"""
密钥泄漏自检：确认真实 AI Key 没有进入 git 跟踪文件或提交历史。

用法：
    py -3.14 tools/check_secrets.py            # 检查工作区跟踪文件 + 全部提交历史
    py -3.14 tools/check_secrets.py --quiet    # 只输出结果行

原理：从 .env 读取真实 AI_API_KEY，取其中段指纹在
  1) git ls-files 列出的所有跟踪文件
  2) git rev-list --all 覆盖的全部提交 blob
中搜索。任一命中即以退出码 1 结束（可用于 CI 或 pre-commit）。
"""
import os
import subprocess
import sys

QUIET = '--quiet' in sys.argv


def msg(text):
    if not QUIET:
        print(text)


def run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding='utf-8', errors='ignore', **kw).stdout


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    # 1. 读取真实 key
    key = None
    env_path = os.path.join(root, '.env')
    if os.path.exists(env_path):
        for ln in open(env_path, encoding='utf-8'):
            if ln.startswith('AI_API_KEY='):
                key = ln.split('=', 1)[1].strip()
                break

    if not key or len(key) < 16 or key.lower().startswith(
            ('your-', 'sk-your', 'demo', 'none', 'xxx')):
        msg('[i] .env 中没有真实 key（占位值或未创建），无需检查')
        print('[OK] 无泄漏')
        return 0

    fingerprint = key[6:-4]  # 取中段，避免误报
    problems = []

    # 2. 跟踪文件
    tracked = run(['git', 'ls-files']).splitlines()
    for p in tracked:
        if not os.path.isfile(p) or os.path.getsize(p) > 3_000_000:
            continue
        try:
            txt = open(p, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        if key in txt or fingerprint in txt:
            problems.append(f'跟踪文件: {p}')

    # 3. 全部提交历史
    revs = run(['git', 'rev-list', '--all']).split()
    for rev in revs:
        out = run(['git', 'grep', '-l', '-I', '-F', fingerprint, rev])
        for line in out.splitlines():
            path = line.split(':', 1)[-1]
            problems.append(f'提交历史: {path} (commit {rev[:8]})')

    if problems:
        print('[!!] 发现真实 key 泄漏：')
        for p in problems:
            print('   ', p)
        print('处理建议：从文件中移除 key 后重新提交；已进入历史的需改写历史或作废该 key')
        return 1

    print('[OK] 无泄漏：真实 key 只存在于 .env（未被 git 跟踪）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
