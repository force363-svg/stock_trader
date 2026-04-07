"""
볼린저밴드 조건
- 중심선 위 + 상단밴드 돌파 직전
"""
from .base import BaseCondition
from .ma_alignment import _sma


def _bollinger(closes: list, period: int = 20, k: float = 2.0):
    """볼린저밴드 계산. closes는 최신순."""
    sma = _sma(closes, period)
    if not sma:
        return None, None, None
    # 표준편차 계산
    arr = list(reversed(closes))
    std_devs = []
    for i in range(len(arr) - period + 1):
        window = arr[i:i+period]
        mean   = sum(window) / period
        std    = (sum((x - mean) ** 2 for x in window) / period) ** 0.5
        std_devs.append(std)
    std_devs = list(reversed(std_devs))
    n = min(len(sma), len(std_devs))
    upper = [sma[i] + k * std_devs[i] for i in range(n)]
    lower = [sma[i] - k * std_devs[i] for i in range(n)]
    return sma[:n], upper, lower


class BollingerCondition(BaseCondition):
    name = "볼린저밴드"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        if len(daily) < 25:
            return 0.0, "데이터 부족"

        closes = [d["close"] for d in daily]
        mid, upper, lower = _bollinger(closes)
        if mid is None:
            return 0.0, "계산 실패"

        cur = closes[0]
        band_width = upper[0] - lower[0]
        if band_width == 0:
            return 50.0, "밴드폭 0"

        position = (cur - lower[0]) / band_width  # 0=하단, 1=상단

        if 0.5 <= position <= 0.85:
            pts = 80.0
            detail = f"밴드 중상단 ({position:.0%})"
        elif 0.85 < position <= 1.0:
            pts = 60.0
            detail = f"밴드 상단 근접 ({position:.0%})"
        elif position > 1.0:
            pts = 30.0
            detail = f"밴드 상단 돌파 ({position:.0%}) - 과열"
        elif 0.3 <= position < 0.5:
            pts = 50.0
            detail = f"밴드 중하단 ({position:.0%})"
        else:
            pts = 20.0
            detail = f"밴드 하단 ({position:.0%})"

        return pts, detail
