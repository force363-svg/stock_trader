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
        exe_name = os.path.basename(sys.executable).lower()
        fname = "ai_signals_mock.json" if "mock" in exe_name else "ai_signals_real.json"
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fname = "ai_signals.json"
    return os.path.join(base, fname)


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
