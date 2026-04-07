"""
이평선 배열 조건
- EMA5 > EMA20 > EMA50 > EMA200 정배열
- 200일선 상승 여부
- 50일선 > 200일선 여부
"""
from .base import BaseCondition


def _ema(closes: list, period: int) -> list:
    """지수이동평균 계산 (최신이 index 0인 리스트 → 역순으로 계산 후 반전)"""
    if len(closes) < period:
        return []
    arr = list(reversed(closes))  # 오래된 것부터
    k = 2.0 / (period + 1)
    ema = [arr[0]]
    for price in arr[1:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return list(reversed(ema))   # 다시 최신순


def _sma(closes: list, period: int) -> list:
    """단순이동평균"""
    if len(closes) < period:
        return []
    result = []
    arr = list(reversed(closes))
    for i in range(len(arr) - period + 1):
        result.append(sum(arr[i:i+period]) / period)
    return list(reversed(result))


class MAAlignmentCondition(BaseCondition):
    name = "이평선_배열상태"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        if len(daily) < 210:
            return 0.0, "데이터 부족"

        closes = [d["close"] for d in daily]

        ema5   = _ema(closes, 5)
        ema20  = _ema(closes, 20)
        ema50  = _ema(closes, 50)
        ema200 = _ema(closes, 200)
        sma50  = _sma(closes, 50)
        sma200 = _sma(closes, 200)

        if not (ema5 and ema20 and ema50 and ema200 and sma50 and sma200):
            return 0.0, "계산 실패"

        pts = 0
        details = []

        # 1. 200일선 상승 (최근 2봉 비교)
        if len(sma200) >= 2 and sma200[0] > sma200[1]:
            pts += 20
            details.append("200일선↑")

        # 2. 50일선 > 200일선
        if sma50[0] > sma200[0]:
            pts += 15
            details.append("50>200")

        # 3. EMA20 > EMA50
        if ema20[0] > ema50[0]:
            pts += 15
            details.append("EMA20>50")

        # 4. EMA5 > EMA20
        if ema5[0] > ema20[0]:
            pts += 20
            details.append("EMA5>20")

        # 5. 현재가 > EMA5
        if closes[0] > ema5[0]:
            pts += 15
            details.append("종가>EMA5")

        # 6. EMA5 상승 (최근 2봉)
        if len(ema5) >= 2 and ema5[0] > ema5[1]:
            pts += 10
            details.append("EMA5↑")

        # 7. 50일선 상승
        if len(sma50) >= 2 and sma50[0] > sma50[1]:
            pts += 5
            details.append("50일선↑")

        detail = ", ".join(details) if details else "정배열 조건 미충족"
        return float(pts), detail

    def check_screening(self, code: str, data: dict) -> bool:
        """스크리닝: 핵심 조건(200일선 상승 + EMA5>EMA20)만 체크"""
        daily = data.get("daily", [])
        if len(daily) < 210:
            return False
        closes = [d["close"] for d in daily]
        sma200 = _sma(closes, 200)
        ema5   = _ema(closes, 5)
        ema20  = _ema(closes, 20)
        if not (sma200 and ema5 and ema20):
            return False
        return (len(sma200) >= 2 and sma200[0] > sma200[1] and
                ema5[0] > ema20[0])
