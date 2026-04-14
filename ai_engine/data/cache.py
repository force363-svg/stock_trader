"""
API 캐시 - 파일 기반 영구 저장
프로그램 재시작해도 데이터 유지
"""
import json
import os
import sys
import time
import threading


def _get_cache_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    exe_name = os.path.basename(sys.executable).lower() if getattr(sys, 'frozen', False) else ""
    fname = "stock_cache_mock.json" if "mock" in exe_name else "stock_cache.json"
    return os.path.join(base, fname)


class Cache:
    def __init__(self):
        self._store = {}  # key → (value, expire_at)
        self._lock = threading.Lock()
        self._dirty = False
        self._load_from_file()

    def get(self, key):
        with self._lock:
            if key in self._store:
                val, expire_at = self._store[key]
                if time.time() < expire_at:
                    return val
                del self._store[key]
            return None

    def set(self, key, value, ttl_seconds: int):
        with self._lock:
            self._store[key] = (value, time.time() + ttl_seconds)
            self._dirty = True

    def get_timestamp(self, key):
        """키의 저장 시각 반환 (expire_at - ttl 추정, 없으면 None)"""
        with self._lock:
            if key in self._store:
                val, expire_at = self._store[key]
                if time.time() < expire_at:
                    # ttl=86400으로 설정했으므로 저장시각 = expire_at - 86400
                    return expire_at - 86400
            return None

    def clear(self):
        with self._lock:
            self._store.clear()
            self._dirty = True
            self._save_to_file()

    def save(self):
        """명시적 저장"""
        with self._lock:
            if self._dirty:
                self._save_to_file()
                self._dirty = False

    def _load_from_file(self):
        """파일에서 캐시 로드"""
        try:
            path = _get_cache_path()
            if not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            now = time.time()
            loaded = 0
            for key, (val, expire_at) in raw.items():
                if expire_at > now:
                    self._store[key] = (val, expire_at)
                    loaded += 1
            print(f"[캐시] 파일에서 {loaded}건 로드 ({os.path.basename(path)})")
        except Exception as e:
            print(f"[캐시] 파일 로드 실패: {e}")

    def _save_to_file(self):
        """캐시를 파일에 저장"""
        try:
            path = _get_cache_path()
            now = time.time()
            # 만료 안 된 것만 저장
            data = {}
            for key, (val, expire_at) in self._store.items():
                if expire_at > now:
                    data[key] = [val, expire_at]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, default=str)
            print(f"[캐시] {len(data)}건 저장 → {path}")
        except Exception as e:
            import traceback
            print(f"[캐시] 파일 저장 실패: {e}")
            # 에러를 파일로 기록
            try:
                err_path = os.path.join(os.path.dirname(path), "debug_cache_error.txt")
                with open(err_path, "w", encoding="utf-8") as f:
                    f.write(f"path: {path}\n")
                    f.write(f"data keys: {len(data)}\n")
                    f.write(traceback.format_exc())
            except:
                pass


# 싱글턴
_cache = Cache()


def get_cache() -> Cache:
    return _cache
