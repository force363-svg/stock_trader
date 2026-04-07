"""
매도 조건 점수 차감 (페널티 시스템)
매수 이후 보유 중인 종목에 대해 매도 조건 해당 시 점수 차감
"""
from .base import BaseCondition


class ScorePenaltyCondition(BaseCondition):
    name = "매도_페널티"

    def score(self, code: str, data: dict) -> tuple:
        """
        현재 보유 종목의 페널티 점수 계산
        data에 추가 키:
          "hold_score"    : 매수 당시 점수 (기본 80)
          "market_status" : {"down_ratio": float, "index_new_low": bool}
          "price_data"    : 현재가 정보
        반환: (남은 점수, 페널티 상세)
        """
        hold_score    = data.get("hold_score", 80.0)
        market_status = data.get("market_status", {})
        price_data    = data.get("price", {})
        daily         = data.get("daily", [])

        penalty = 0.0
        details = []

        # 1. 하락종목 3배 초과 (시장 전체)
        down_ratio = market_status.get("down_ratio", 0)
        if down_ratio >= 3.0:
            penalty += 20
            details.append(f"하락종목 {down_ratio:.1f}배 초과")

        # 2. 지수 당일 저점 갱신
        if market_status.get("index_new_low", False):
            penalty += 15
            details.append("지수 저점 갱신")

        # 3. 지수 급락 (1분 0.5% 이상)
        if market_status.get("index_sudden_drop", False):
            penalty += 25
            details.append("지수 급락")

        # 4. 전저점/5일선 이탈
        if len(daily) >= 6:
            from .ma_alignment import _ema
            closes = [d["close"] for d in daily]
            ema5 = _ema(closes, 5)
            cur = closes[0]
            if ema5 and cur < ema5[0]:
                penalty += 15
                details.append("5일선 이탈")

        # 5. 20일선 이격도 15% 이상 (과열 익절)
        if len(daily) >= 22:
            from .ma_alignment import _sma
            closes = [d["close"] for d in daily]
            sma20 = _sma(closes, 20)
            if sma20 and sma20[0] > 0:
                gap = (closes[0] - sma20[0]) / sma20[0] * 100
                if gap >= 15:
                    penalty += 10
                    details.append(f"20일선 이격 {gap:.1f}%")

        remaining = max(0.0, hold_score - penalty)
        detail = f"페널티 -{penalty:.0f}점 ({', '.join(details)})" if details else "이상 없음"
        return remaining, detail
