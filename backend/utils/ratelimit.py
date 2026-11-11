# -*- coding: utf-8 -*-
"""
轻量限流 - 进程内滑动窗口计数

说明：适用于单进程开发/演示环境（Flask 内置服务器或单 worker）。
多进程/多实例部署时应替换为 Redis 等共享存储（见 README「生产部署」）。
"""
import threading
import time
from collections import deque


class SlidingWindowLimiter:
    """按 key（如 IP、IP+接口）统计窗口内请求次数"""

    def __init__(self, max_keys=5000):
        self._buckets = {}
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def allow(self, key, limit, window_seconds):
        """
        :return: (是否放行, 建议等待秒数)
        """
        if limit <= 0:
            return True, 0
        now = time.time()
        with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            while bucket and bucket[0] <= now - window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                return False, max(1, int(bucket[0] + window_seconds - now) + 1)
            bucket.append(now)
            if len(self._buckets) > self._max_keys:
                self._prune(now, window_seconds)
            return True, 0

    def reset(self, key=None):
        """清空计数（测试或手动解锁时使用）"""
        with self._lock:
            if key is None:
                self._buckets.clear()
            else:
                self._buckets.pop(key, None)

    def _prune(self, now, window_seconds):
        """清理过期的空桶，避免字典无限增长"""
        stale = [k for k, dq in self._buckets.items()
                 if not dq or dq[-1] <= now - window_seconds]
        for k in stale:
            self._buckets.pop(k, None)


limiter = SlidingWindowLimiter()
