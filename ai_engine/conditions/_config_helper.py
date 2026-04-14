"""
engine_config 로딩 헬퍼
모든 계산기/엔진 모듈에서 공통 사용
모드별 분리: engine_config_mock.json / engine_config_real.json
"""
import json
import os
import sys

_cached_defaults = None


def _get_base_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _detect_mode() -> str:
    """exe 이름으로 모드 감지 (AI 엔진 내부용)"""
    exe_name = os.path.basename(sys.executable if getattr(sys, 'frozen', False) else "")
    if "Mock" in exe_name or "mock" in exe_name:
        return "mock"
    if "Real" in exe_name or "real" in exe_name:
        return "real"
    # 개발 환경: config에서 읽기
    try:
        base = _get_base_dir()
        with open(os.path.join(base, "config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("api", {}).get("trade_mode", "mock")
    except Exception:
        return "mock"


def get_engine_config_path() -> str:
    """현재 모드에 맞는 engine_config 파일 전체 경로 반환"""
    base = _get_base_dir()
    mode = _detect_mode()
    if mode == "mock":
        fname = "engine_config_mock.json"
    elif mode == "real":
        fname = "engine_config_real.json"
    else:
        fname = "engine_config.json"
    path = os.path.join(base, fname)
    # fallback: 모드별 파일 없으면 기존 engine_config.json
    if not os.path.exists(path):
        fallback = os.path.join(base, "engine_config.json")
        if os.path.exists(fallback):
            return fallback
    return path


def load_defaults() -> dict:
    """engine_config의 defaults 섹션 로드 (캐시)"""
    global _cached_defaults
    if _cached_defaults is not None:
        return _cached_defaults
    try:
        with open(get_engine_config_path(), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        _cached_defaults = cfg.get("defaults", {})
        return _cached_defaults
    except Exception:
        return {}


def reload_defaults():
    """캐시 무효화 (설정 변경 후 호출)"""
    global _cached_defaults
    _cached_defaults = None
