"""
MACD 조건 [10, 20, 9]
- MACD > Signal
- MACD 상승 추세
"""
from .base import BaseCondition
from .ma_alignment import _ema


def _macd(closes: list, fast=10, slow=20, signal=9):
    """MACD 계산. 최신순 리스트 입력."""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    if not ema_fast or not ema_slow:
        return [], [], []
    # 공통 길이
    n = min(len(ema_fast), len(ema_slow))
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(n)]
    sig_line  = _ema(macd_line, signal)
    if not sig_line:
        return [], [], []
    m = min(len(macd_line), len(sig_line))
    hist = [macd_line[i] - sig_line[i] for i in range(m)]
    return macd_line[:m], sig_line[:m], hist


class MACDCondition(BaseCondition):
    name = "MACD_상승"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        min60 = data.get("min60", [])
        if len(daily) < 30:
            return 0.0, "데이터 부족"

        pts = 0.0
        details = []

        # 일봉 MACD
        d_closes = [d["close"] for d in daily]
        d_macd, d_sig, d_hist = _macd(d_closes, 10, 20, 9)
        if len(d_macd) >= 2:
            if d_macd[0] > d_sig[0]:
                pts += 30
                details.append("일봉MACD>Signal")
            if d_macd[0] > d_macd[1]:
                pts += 20
                details.append("일봉MACD↑")

        # 60분봉 MACD
        if len(min60) >= 30:
            m_closes = [d["close"] for d in min60]
            m_macd, m_sig, _ = _macd(m_closes, 10, 20, 9)
            if len(m_macd) >= 2:
                if m_macd[0] > m_sig[0]:
                    pts += 30
                    details.append("60분MACD>Signal")
                if m_macd[0] > m_macd[1]:
                    pts += 20
                    details.append("60분MACD↑")

        return min(100.0, pts), ", ".join(details) if details else "MACD 조건 미충족"

    def check_screening(self, code: str, data: dict) -> bool:
        s, _ = self.score(code, data)
        return s >= 50
