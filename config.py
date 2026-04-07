import json
import os
import sys

# 설정 파일은 항상 C:\StockTrader\ 에 저장
# → 빌드/업데이트해도 절대 삭제되지 않음
if getattr(sys, 'frozen', False):
    # exe 실행 시: C:\StockTrader\user_settings.json
    BASE_DIR = os.path.dirname(os.path.dirname(sys.executable))
else:
    # 개발 환경 (.py 직접 실행 시)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "account": {
        "buy_amount": 1000000,
        "max_stocks": 5,
        "start_time": "09:05",
        "end_time": "15:20",
        "risk_limit": 3.0
    },
    "profit": {
        "profit_stages": [3.0, 5.0, 8.0, 12.0, 20.0],
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
    "condition": ""
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"[설정] 저장 완료 → {CONFIG_FILE}")
