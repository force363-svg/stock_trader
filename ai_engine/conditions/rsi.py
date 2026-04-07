"""
RSI 조건
- RSI(14) 과매도 탈출 (30~70 구간)
"""
from .base import BaseCondition


def _rsi(closes: list, period: int = 14) -> float:
    """RSI 계산. closes는 최신순."""
    if len(closes) < period + 1:
        return 50.0
    arr = list(reversed(closes[:period + 10]))
    gains, losses = [], []
    for i in range(1, len(arr)):
        diff = arr[i] - arr[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if not gains:
        return 50.0
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


class RSICondition(BaseCondition):
    name = "RSI"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        if len(daily) < 20:
            return 50.0, "데이터 부족"

        closes = [d["close"] for d in daily]
        rsi = _rsi(closes, 14)

        # 30~70이 건강한 구간, 50~65가 매수 최적
        if 50 <= rsi <= 65:
            pts = 90.0
        elif 40 <= rsi < 50:
            pts = 70.0
        elif 65 < rsi <= 70:
            pts = 60.0
        elif 30 <= rsi < 40:
            pts = 50.0   # 과매도 탈출 가능성
        elif rsi > 70:
            pts = 30.0   # 과매수
        else:
            pts = 20.0   # 과매도

        return pts, f"RSI {rsi:.1f}"
