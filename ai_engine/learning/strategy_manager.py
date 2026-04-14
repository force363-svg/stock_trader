"""
시장 상황별 전략 자동 전환

시장 상황을 분류하고, 각 상황에서의 과거 성과를 분석하여
매매 전략을 자동 전환.

시장 상황 분류:
  - BULL (강세장): 지수 상승 + 상승종목 우위
  - BEAR (약세장): 지수 하락 + 하락종목 우위
  - SIDEWAYS (횡보장): 변동 작음
  - VOLATILE (변동장): 급등락 반복

전략 전환:
  - BULL: 공격적 (매수 임계값 ↓, 매도 임계값 ↑)
  - BEAR: 방어적 (매수 임계값 ↑, 매도 임계값 ↓)
  - SIDEWAYS: 기본값 유지
  - VOLATILE: 보수적 + 빠른 손절
"""
import json
import os
import sys
from datetime import datetime
from ..db.database import get_connection


def _get_config_path():
    from ..conditions._config_helper import get_engine_config_path
    return get_engine_config_path()


def _load_market_cache() -> dict:
    """market_cache.json에서 시장 상태 로드"""
    try:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "market_cache.json")
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def classify_market() -> dict:
    """
    현재 시장 상황 분류
    반환: {
        "regime": str,        BULL / BEAR / SIDEWAYS / VOLATILE
        "kospi_diff": float,
        "kosdaq_diff": float,
        "confidence": float,  0~1
    }
    """
    cache = _load_market_cache()
    indices = cache.get("indices", {})
    kospi = float(indices.get("kospi_diff", 0))
    kosdaq = float(indices.get("kosdaq_diff", 0))
    avg = (kospi + kosdaq) / 2

    # 업종 상승/하락 비율
    sectors = cache.get("sectors", [])
    up_sectors = sum(1 for s in sectors if s.get("diff", 0) > 0)
    total_sectors = max(1, len(sectors))
    up_ratio = up_sectors / total_sectors

    # 분류
    if avg > 1.0 and up_ratio > 0.7:
        regime = "BULL"
        confidence = min(1.0, avg / 3.0)
    elif avg < -1.0 and up_ratio < 0.3:
        regime = "BEAR"
        confidence = min(1.0, abs(avg) / 3.0)
    elif abs(avg) > 2.0:
        regime = "VOLATILE"
        confidence = min(1.0, abs(avg) / 5.0)
    else:
        regime = "SIDEWAYS"
        confidence = 1.0 - abs(avg) / 2.0

    return {
        "regime": regime,
        "kospi_diff": kospi,
        "kosdaq_diff": kosdaq,
        "up_ratio": round(up_ratio, 2),
        "confidence": round(max(0, min(1, confidence)), 2)
    }


def get_strategy_adjustments(regime: str) -> dict:
    """
    시장 상황에 따른 전략 조정값
    반환: {"buy_adjust": int, "sell_adjust": int, "description": str}
    """
    strategies = {
        "BULL": {
            "buy_adjust": -3,     # 매수 임계값 3점 ↓ (공격적)
            "sell_adjust": +5,    # 매도 임계값 5점 ↑ (보유 연장)
            "description": "강세장: 적극 매수, 보유 연장"
        },
        "BEAR": {
            "buy_adjust": +5,     # 매수 임계값 5점 ↑ (보수적)
            "sell_adjust": -3,    # 매도 임계값 3점 ↓ (빠른 매도)
            "description": "약세장: 보수적 매수, 빠른 손절"
        },
        "VOLATILE": {
            "buy_adjust": +3,     # 매수 임계값 3점 ↑
            "sell_adjust": -2,    # 매도 임계값 2점 ↓
            "description": "변동장: 신중한 진입, 리스크 관리"
        },
        "SIDEWAYS": {
            "buy_adjust": 0,
            "sell_adjust": 0,
            "description": "횡보장: 기본 전략 유지"
        }
    }
    return strategies.get(regime, strategies["SIDEWAYS"])


def analyze_regime_performance() -> dict:
    """
    시장 상황별 과거 성과 분석
    반환: {"BULL": {"trades":N, "win_rate":0.7, "avg_pnl":2.1}, ...}
    """
    conn = get_connection()
    try:
        # market_regime 컬럼이 있으면 사용, 없으면 빈 결과
        try:
            rows = conn.execute("""
                SELECT market_regime, pnl, result FROM trade_results
                WHERE sell_date IS NOT NULL AND market_regime IS NOT NULL
            """).fetchall()
        except Exception:
            return {}

        stats = {}
        for row in rows:
            regime = row["market_regime"]
            if regime not in stats:
                stats[regime] = {"trades": 0, "wins": 0, "pnls": []}
            stats[regime]["trades"] += 1
            if row["result"] == "WIN":
                stats[regime]["wins"] += 1
            if row["pnl"] is not None:
                stats[regime]["pnls"].append(row["pnl"])

        result = {}
        for regime, s in stats.items():
            result[regime] = {
                "trades": s["trades"],
                "win_rate": round(s["wins"] / s["trades"], 2) if s["trades"] > 0 else 0,
                "avg_pnl": round(sum(s["pnls"]) / len(s["pnls"]), 2) if s["pnls"] else 0
            }
        return result
    finally:
        conn.close()


def apply_strategy():
    """
    현재 시장 상황 판단 → 전략 조정 적용
    장 시작 시 1회 호출
    """
    market = classify_market()
    regime = market["regime"]
    adj = get_strategy_adjustments(regime)

    print(f"[전략] 시장: {regime} (신뢰도:{market['confidence']:.0%}) → {adj['description']}")

    # 과거 성과 참조
    perf = analyze_regime_performance()
    if regime in perf:
        p = perf[regime]
        print(f"[전략] {regime} 과거 성과: {p['trades']}건, "
              f"승률:{p['win_rate']:.0%}, 평균:{p['avg_pnl']:+.2f}%")

    return {
        "regime": regime,
        "adjustments": adj,
        "market": market,
        "performance": perf.get(regime, {})
    }
