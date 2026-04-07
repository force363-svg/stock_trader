"""
API 캐시 - 분봉은 5분, 일봉은 1시간 유효
"""
import time


class Cache:
    def __init__(self):
        self._store = {}  # key → (value, expire_at)

    def get(self, key):
        if key in self._store:
            val, expire_at = self._store[key]
            if time.time() < expire_at:
                return val
            del self._store[key]
        return None

    def set(self, key, value, ttl_seconds: int):
        self._store[key] = (value, time.time() + ttl_seconds)

    def clear(self):
        self._store.clear()


# 싱글턴
_cache = Cache()


def get_cache() -> Cache:
    return _cache
