"""
매수/매도/보유 신호 생성
점수 기준: engine_config.json thresholds 실시간 반영
"""
import json
import os
import sys
from .scorer import calculate_score, calculate_sell_score
from ..conditions.score_penalty import ScorePenaltyCondition

_penalty_calc = ScorePenaltyCondition()


def _get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_thresholds() -> dict:
    """매수/매도 임계값 로드"""
    try:
        from ..conditions._config_helper import get_engine_config_path
        path = get_engine_config_path()
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("thresholds", {"buy": 80, "hold": 50, "sell_confirm": 75, "sell_watch": 50})
    except Exception:
        return {"buy": 80, "hold": 50, "sell_confirm": 75, "sell_watch": 50}


def _load_market_status() -> dict:
    """메인 캐시에서 시장 상태 로드"""
    try:
        from ..data.cache import get_cache
        cache = get_cache()
        market = cache.get("market_index") or {}
        kospi = float(market.get("kospi_diff", 0))
        kosdaq = float(market.get("kosdaq_diff", 0))
        avg = (kospi + kosdaq) / 2 if kospi or kosdaq else 0
        return {
            "kospi_diff": kospi,
            "kosdaq_diff": kosdaq,
            "down_ratio": float(market.get("down_ratio", 0)),
            "index_new_low": avg < -1.5,
            "index_sudden_drop": avg < -0.5,
            "index_drop_pct": abs(min(0, avg)),
        }
    except Exception:
        return {}


def _confidence(score: float, threshold: float) -> str:
    if score >= threshold + 10:
        return "HIGH"
    if score >= threshold:
        return "MEDIUM"
    return "LOW"


def generate_signal(code: str, name: str, data: dict, server_filtered: bool = False) -> dict:
    """
    신규 진입 후보 신호 생성 (BUY / HOLD / WATCH).
    server_filtered=True: 서버 조건검색 통과 종목 → 전부 표시.
    """
    thresh = _load_thresholds()
    buy_t = thresh.get("buy", 80)
    hold_t = thresh.get("hold", 50)

    result = calculate_score(code, data)
    score = result["total_score"]

    price_data = data.get("price", {})
    try:
        current_price = int(float(price_data.get("price", price_data.get("close", 0))))
    except Exception:
        current_price = 0
    try:
        diff_rate = float(price_data.get("diff", price_data.get("rate", 0)))
    except Exception:
        diff_rate = 0.0

    # 신호 타입 결정
    if score >= buy_t:
        signal_type = "BUY"
    elif score >= hold_t:
        signal_type = "HOLD"
    else:
        signal_type = "WATCH"

    return {
        "stock_code":     code,
        "stock_name":     name,
        "signal_type":    signal_type,
        "score":          score,
        "current_price":  current_price,
        "diff_rate":      diff_rate,
        "conditions":     {k: {"score": v["score"], "detail": v["detail"], "weight": v.get("weight", 0)}
                          for k, v in result["conditions"].items()},
        "confidence":     _confidence(score, buy_t),
        "supply_score":   result["supply_score"],
        "chart_score":    result["chart_score"],
        "material_score": result["material_score"],
    }


def generate_sell_signal(code: str, name: str, data: dict,
                         hold_info: dict,
                         market_status: dict = None) -> dict:
    """
    보유 종목 매도 신호.
    흐름: 매도조건(sell) → 매도고려사항(sell_scoring) → 최종판단
    """
    thresh = _load_thresholds()
    hold_t = thresh.get("hold", 50)
    sell_confirm_t = thresh.get("sell_confirm", 75)
    sell_watch_t = thresh.get("sell_watch", 50)

    if market_status is None:
        market_status = _load_market_status()

    price_data = data.get("price", {})
    try:
        current_price = int(float(price_data.get("price", price_data.get("close", 0))))
    except Exception:
        current_price = 0

    # 1단계: 매도조건 스크리닝 (페널티 체크)
    sell_reasons = []

    penalty_data = {**data, "hold_score": 80.0, "market_status": market_status or {}}
    remaining, penalty_detail = _penalty_calc.score(code, penalty_data)
    if penalty_detail != "이상 없음":
        sell_reasons.append(penalty_detail)

    # 매수 점수 하락 체크
    buy_result = calculate_score(code, data)
    buy_score = buy_result["total_score"]
    if buy_score < hold_t:
        sell_reasons.append(f"매수점수 하락({buy_score:.1f} < {hold_t})")

    # 2단계: 매도 고려사항
    sell_result = calculate_sell_score(code, data, hold_info=hold_info, market_status=market_status)
    sell_score = sell_result["total_score"]

    # 3단계: 최종판단
    # 매수 점수가 보유 기준 미만 → 매수 근거 소멸, 무조건 매도
    if buy_score < hold_t:
        signal_type = "SELL"
        sell_reasons.append(f"매수근거 소멸({buy_score:.1f} < {hold_t})")
    elif sell_reasons:
        if sell_score >= sell_confirm_t:
            signal_type = "SELL"
        elif sell_score >= sell_watch_t:
            signal_type = "HOLD"
            sell_reasons.append(f"매도 관망({sell_score:.1f}점)")
        else:
            signal_type = "HOLD"
            sell_reasons.append(f"고려사항 양호({sell_score:.1f}점)")
    elif sell_score >= sell_confirm_t + 10:
        signal_type = "SELL"
        sell_reasons.append(f"고려사항 매도({sell_score:.1f})")
    else:
        signal_type = "HOLD"

    # 조건 결과 합산
    all_conditions = {}
    for k, v in buy_result["conditions"].items():
        all_conditions[f"[매수]{k}"] = {"score": v["score"], "detail": v["detail"]}
    for k, v in sell_result["conditions"].items():
        all_conditions[f"[매도]{k}"] = {"score": v["score"], "detail": v["detail"]}

    return {
        "stock_code":     code,
        "stock_name":     name,
        "signal_type":    signal_type,
        "score":          sell_score,
        "buy_score":      buy_score,
        "current_price":  current_price,
        "sell_reason":    " / ".join(sell_reasons) if sell_reasons else "",
        "conditions":     all_conditions,
        "confidence":     _confidence(sell_score, sell_confirm_t),
        "supply_score":   buy_result["supply_score"],
        "chart_score":    buy_result["chart_score"],
        "material_score": buy_result["material_score"],
    }
