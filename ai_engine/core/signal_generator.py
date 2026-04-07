"""
매수/매도/보유 신호 생성
점수 기준: 80점↑매수 / 50~79보유 / 50↓관망
"""
import json
import os
import sys
from .scorer import calculate_score


def _get_thresholds():
    try:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(base, "engine_config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("thresholds", {"buy": 80, "hold": 50})
    except:
        return {"buy": 80, "hold": 50}


def _confidence(score: float, buy_thresh: float) -> str:
    if score >= buy_thresh + 10:
        return "HIGH"
    elif score >= buy_thresh:
        return "MEDIUM"
    else:
        return "LOW"


def _stop_loss(current_price: int, supply_avg: int = 0) -> int:
    """손절가 = 수급평단가 - 3% (없으면 현재가 - 3%)"""
    base = supply_avg if supply_avg > 0 else current_price
    return int(base * 0.97)


def _target_price(current_price: int, daily: list) -> int:
    """목표가 = 최근 52주 고점 (없으면 현재가 + 8%)"""
    if len(daily) >= 50:
        recent_high = max(d["high"] for d in daily[:50])
        if recent_high > current_price:
            return recent_high
    return int(current_price * 1.08)


def generate_signal(code: str, name: str, data: dict) -> dict | None:
    """
    단일 종목 신호 생성
    반환: 신호 dict 또는 None (관망)
    """
    thresh = _get_thresholds()
    buy_t  = thresh.get("buy",  80)
    hold_t = thresh.get("hold", 50)

    result  = calculate_score(code, data)
    score   = result["total_score"]

    price_data = data.get("price", {})
    try:
        current_price = int(float(price_data.get("price", price_data.get("close", 0))))
    except:
        current_price = 0

    # 무조건 제외 조건 (설계서 §5)
    rs_cond = result["conditions"].get("지수_대비_강도(RS)", {})
    if rs_cond.get("score", 100) < 30:
        return None  # RS 마이너스 → 제외

    ma_cond = result["conditions"].get("이평선_배열상태", {})
    if ma_cond.get("score", 100) < 20:
        return None  # 역배열 → 제외

    # 신호 타입
    if score >= buy_t:
        signal_type = "BUY"
    elif score >= hold_t:
        signal_type = "HOLD"
    else:
        return None   # 관망 → 신호 없음

    daily = data.get("daily", [])

    return {
        "stock_code"  : code,
        "stock_name"  : name,
        "signal_type" : signal_type,
        "score"       : score,
        "current_price": current_price,
        "conditions"  : {
            k: {"score": v["score"], "detail": v["detail"]}
            for k, v in result["conditions"].items()
        },
        "stop_loss"   : _stop_loss(current_price),
        "target_price": _target_price(current_price, daily),
        "confidence"  : _confidence(score, buy_t),
        "supply_score"  : result["supply_score"],
        "chart_score"   : result["chart_score"],
        "material_score": result["material_score"],
    }
