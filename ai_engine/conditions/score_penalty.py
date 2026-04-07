"""
매도 조건 점수 차감 (페널티 시스템)
engine_config.json sell 섹션의 threshold를 실시간으로 읽어 동적 적용
"""
import json
import os
import sys
from .base import BaseCondition


def _load_sell_config() -> dict:
    """engine_config.json sell 섹션 로드 → {조건명: threshold} 반환"""
    try:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(base, "engine_config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return {
            c["name"]: c.get("threshold", 0)
            for c in cfg.get("sell", [])
            if c.get("enabled", True)
        }
    except Exception:
        # 기본값 (GUI 설정 불러오기 실패 시)
        return {
            "하락종목 3배 초과"   : 3,
            "지수 저점 갱신"      : 0,
            "지수 1분 0.5% 낙하"  : 0.5,
            "전저점/5일선 이탈"   : 0,
            "20일선 이격도 15%"   : 15,
            "거래량 음봉"         : 0,
        }


class ScorePenaltyCondition(BaseCondition):
    name = "매도_페널티"

    def score(self, code: str, data: dict) -> tuple:
        """
        보유 종목의 페널티 점수 계산 (engine_config sell 섹션 threshold 실시간 반영)
        data 추가 키:
          "hold_score"    : 매수 당시 점수 (기본 80)
          "market_status" : {"down_ratio": float, "index_new_low": bool,
                             "index_sudden_drop": bool}
        반환: (남은 점수, 페널티 상세)
        """
        sell_cfg      = _load_sell_config()
        hold_score    = data.get("hold_score", 80.0)
        market_status = data.get("market_status", {})
        daily         = data.get("daily", [])

        penalty  = 0.0
        details  = []

        # ── 시장 전체 조건 ──
        # 하락종목 N배 초과
        thr_down = sell_cfg.get("하락종목 3배 초과", 3)
        down_ratio = market_status.get("down_ratio", 0)
        if thr_down > 0 and down_ratio >= thr_down:
            penalty += 20
            details.append(f"하락종목 {down_ratio:.1f}배 초과(기준:{thr_down}배)")

        # 지수 당일 저점 갱신
        if "지수 저점 갱신" in sell_cfg and market_status.get("index_new_low", False):
            penalty += 15
            details.append("지수 저점 갱신")

        # 지수 급락 (N% 이상)
        thr_drop = sell_cfg.get("지수 1분 0.5% 낙하", 0.5)
        index_drop = market_status.get("index_drop_pct", 0)
        if thr_drop > 0 and index_drop >= thr_drop:
            penalty += 25
            details.append(f"지수 급락 {index_drop:.2f}%(기준:{thr_drop}%)")
        elif "지수 1분 0.5% 낙하" in sell_cfg and market_status.get("index_sudden_drop", False):
            penalty += 25
            details.append("지수 급락")

        # ── 종목 기술적 조건 ──
        if len(daily) >= 6:
            from .ma_alignment import _ema, _sma
            closes = [d["close"] for d in daily]

            # 전저점/5일선 이탈
            if "전저점/5일선 이탈" in sell_cfg:
                ema5 = _ema(closes, 5)
                if ema5 and closes[0] < ema5[0]:
                    penalty += 15
                    details.append("5일선 이탈")

            # 20일선 이격도 N% 이상 (과열 익절)
            thr_gap = sell_cfg.get("20일선 이격도 15%", 15)
            if len(daily) >= 22 and thr_gap > 0:
                sma20 = _sma(closes, 20)
                if sma20 and sma20[0] > 0:
                    gap = (closes[0] - sma20[0]) / sma20[0] * 100
                    if gap >= thr_gap:
                        penalty += 10
                        details.append(f"20일선 이격 {gap:.1f}%(기준:{thr_gap}%)")

        # 거래량 음봉 (당일 음봉 + 거래량 동반)
        if "거래량 음봉" in sell_cfg and daily:
            d = daily[0]
            if d.get("close", 0) < d.get("open", 0) and d.get("volume", 0) > 0:
                penalty += 10
                details.append("거래량 음봉")

        remaining = max(0.0, hold_score - penalty)
        detail = f"페널티 -{penalty:.0f}점 ({', '.join(details)})" if details else "이상 없음"
        return remaining, detail
