"""
매수/매도/보유 신호 생성
점수 기준: engine_config.json thresholds 실시간 반영
  - BUY  : 매수 임계값 이상
  - HOLD : 보유 임계값 이상
  - SELL : 보유 종목 점수 하락 또는 페널티 조건 충족
"""
import json
import os
import sys
from .scorer import calculate_score
from ..conditions.score_penalty import ScorePenaltyCondition

_penalty_calc = ScorePenaltyCondition()


def _get_thresholds():
    try:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(base, "engine_config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("thresholds", {"buy": 80, "hold": 50})
    except Exception:
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
    신규 진입 후보 신호 생성 (BUY / HOLD)
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
    except Exception:
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
        "stock_code"    : code,
        "stock_name"    : name,
        "signal_type"   : signal_type,
        "score"         : score,
        "current_price" : current_price,
        "conditions"    : {
            k: {"score": v["score"], "detail": v["detail"]}
            for k, v in result["conditions"].items()
        },
        "stop_loss"     : _stop_loss(current_price),
        "target_price"  : _target_price(current_price, daily),
        "confidence"    : _confidence(score, buy_t),
        "supply_score"  : result["supply_score"],
        "chart_score"   : result["chart_score"],
        "material_score": result["material_score"],
    }


def generate_sell_signal(code: str, name: str, data: dict,
                         hold_info: dict,
                         market_status: dict | None = None) -> dict | None:
    """
    보유 종목에 대한 매도 신호 생성
    hold_info: {"code", "name", "buy_price", "qty"}
    market_status: {"down_ratio", "index_new_low", "index_sudden_drop", "index_drop_pct"}
    반환: SELL 신호 dict 또는 None (매도 불필요)
    """
    thresh = _get_thresholds()
    hold_t = thresh.get("hold", 50)

    # 현재 점수 계산
    result = calculate_score(code, data)
    score  = result["total_score"]

    price_data = data.get("price", {})
    try:
        current_price = int(float(price_data.get("price", price_data.get("close", 0))))
    except Exception:
        current_price = 0

    sell_reasons = []

    # ── 1. 점수 자체가 보유 임계값 미만 → 매도 ──
    if score < hold_t:
        sell_reasons.append(f"점수 하락({score:.1f} < 보유임계값 {hold_t})")

    # ── 2. 페널티 조건 체크 (engine_config sell 섹션) ──
    penalty_data = {
        **data,
        "hold_score"    : score,
        "market_status" : market_status or {},
    }
    remaining, penalty_detail = _penalty_calc.score(code, penalty_data)
    if remaining < hold_t and penalty_detail != "이상 없음":
        sell_reasons.append(f"페널티: {penalty_detail}")

    # ── 3. 역배열 전환 → 즉시 매도 ──
    ma_cond = result["conditions"].get("이평선_배열상태", {})
    if ma_cond.get("score", 100) < 15:
        sell_reasons.append("이평선 역배열 전환")

    if not sell_reasons:
        return None

    daily = data.get("daily", [])
    return {
        "stock_code"    : code,
        "stock_name"    : name,
        "signal_type"   : "SELL",
        "score"         : score,
        "current_price" : current_price,
        "sell_reason"   : " / ".join(sell_reasons),
        "conditions"    : {
            k: {"score": v["score"], "detail": v["detail"]}
            for k, v in result["conditions"].items()
        },
        "stop_loss"     : 0,
        "target_price"  : 0,
        "confidence"    : "HIGH",
        "supply_score"  : result["supply_score"],
        "chart_score"   : result["chart_score"],
        "material_score": result["material_score"],
    }
