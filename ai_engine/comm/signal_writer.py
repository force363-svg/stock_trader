"""
AI → GUI 신호 파일 쓰기 (ai_signals.json)
"""
import json
import os
import sys
from datetime import datetime


def get_signals_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "ai_signals.json")


def write_signals(signals: list, scan_count: int = 0):
    """
    signals: [
        {
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "signal_type": "BUY",   # BUY / HOLD / WATCH
            "score": 82.5,
            "current_price": 73400,
            "conditions": {"조건명": {"score": 90, "detail": "..."}},
            "stop_loss": 71198,
            "target_price": 78000,
            "confidence": "HIGH"    # HIGH / MEDIUM / LOW
        }, ...
    ]
    """
    payload = {
        "timestamp": datetime.now().isoformat(),
        "scan_count": scan_count,
        "signals": signals
    }
    path = get_signals_path()
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        print(f"[신호] {len(signals)}개 신호 저장 → {path}")
    except Exception as e:
        print(f"[신호] 저장 실패: {e}")
