import json
import os
import sys

# 설정 파일은 항상 C:\StockTrader\ 에 저장
# → 빌드/업데이트해도 절대 삭제되지 않음
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.dirname(sys.executable))
    # 실전/모의 각각 별도 설정 파일
    exe_name = os.path.basename(sys.executable).lower()
    if "mock" in exe_name:
        CONFIG_FILE = os.path.join(BASE_DIR, "user_settings_mock.json")
    else:
        CONFIG_FILE = os.path.join(BASE_DIR, "user_settings_real.json")
else:
    # 개발 환경 (.py 직접 실행 시)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_FILE = os.path.join(BASE_DIR, "user_settings.json")

DEFAULT_CONFIG = {
    "account": {
        "initial_capital": 500000000,
        "buy_amount": 1000000,
        "max_stocks": 5,
        "start_time": "09:05",
        "end_time": "15:20",
        "risk_limit": 3.0
    },
    "profit": {
        "profit_stages": [3.0, 5.0, 8.0, 12.0, 20.0],
        "sell_ratios": [20.0, 20.0, 20.0, 20.0, 20.0],
        "loss_cut": 3.0
    },
    "api": {
        "ls_app_key": "",
        "ls_app_secret": "",
        "ls_mock_key": "",
        "ls_mock_secret": "",
        "krx_key": "",
        "trade_mode": "real"
    },
    "notify": {
        "kakao_token": "",
        "telegram_token": "",
        "telegram_chat_id": ""
    },
    "data": {
        "data_path": "C:/stock_trader/data",
        "period": "5년",
        "tolerance": 0.5
    },
    "xing": {
        "user_id": "",
        "acf_path": "",
        "auto_login": False,
        "warehouse_interval": 60
    },
    "condition": ""
}

_cached_config = None
_cached_mtime = 0

def load_config():
    global _cached_config, _cached_mtime

    # 파일 수정 시간 비교 → 변경 없으면 캐시 반환
    try:
        mtime = os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else 0
    except OSError:
        mtime = 0
    if _cached_config is not None and mtime == _cached_mtime:
        return json.loads(json.dumps(_cached_config))  # deep copy of cache

    config = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy

    # 읽을 파일 결정: 신규 파일 없으면 구버전 user_settings.json 에서 마이그레이션
    load_file = CONFIG_FILE
    if not os.path.exists(CONFIG_FILE):
        old_file = os.path.join(BASE_DIR, "user_settings.json")
        if os.path.exists(old_file):
            load_file = old_file

    if os.path.exists(load_file):
        try:
            with open(load_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 저장된 값을 DEFAULT에 덮어쓰기 (섹션별 병합)
            for section, values in saved.items():
                if section in config and isinstance(config[section], dict) and isinstance(values, dict):
                    config[section].update(values)
                else:
                    config[section] = values
            # 구버전 파일에서 읽었으면 새 파일로 저장 (마이그레이션)
            if load_file != CONFIG_FILE:
                save_config(config)
                print(f"[설정] 마이그레이션 완료 → {CONFIG_FILE}")
        except Exception as e:
            print(f"[설정] 로드 실패, 기본값 사용: {e}")

    _cached_config = config
    _cached_mtime = mtime
    return json.loads(json.dumps(config))  # deep copy

def save_config(config: dict):
    global _cached_config, _cached_mtime
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    _cached_config = config
    try:
        _cached_mtime = os.path.getmtime(CONFIG_FILE)
    except OSError:
        _cached_mtime = 0
    print(f"[설정] 저장 완료 → {CONFIG_FILE}")
