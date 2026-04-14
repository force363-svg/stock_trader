"""
볼린저밴드 조건
- 기간: engine_config.json defaults.bollinger_period (디폴트 20)
- k값: engine_config.json defaults.bollinger_k (디폴트 2.0)
"""
from .base import BaseCondition
from .ma_alignment import _sma
from ._config_helper import load_defaults


def _get_bollinger_params() -> tuple:
    """defaults에서 볼린저 파라미터 로드"""
    defaults = load_defaults()
    period = int(defaults.get("bollinger_period", 20))
    k = float(defaults.get("bollinger_k", 2.0))
    return period, k


def _bollinger(closes: list, period: int = 20, k: float = 2.0):
    """볼린저밴드 계산. closes는 최신순."""
    sma = _sma(closes, period)
    if not sma:
        return None, None, None
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


def _bb_score(closes: list, period: int, k: float, label: str) -> tuple:
    """볼린저밴드 점수 계산 (일봉/60분봉 공용)"""
    mid, upper, lower = _bollinger(closes, period, k)
    if mid is None:
        return None, ""
    cur = closes[0]
    band_width = upper[0] - lower[0]
    if band_width == 0:
        return 50.0, f"{label} 밴드폭0"
    position = (cur - lower[0]) / band_width

    if 0.5 <= position <= 0.85:
        pts = 80.0
    elif 0.85 < position <= 1.0:
        pts = 60.0
    elif position > 1.0:
        pts = 30.0
    elif 0.3 <= position < 0.5:
        pts = 50.0
    else:
        pts = 20.0

    return pts, f"{label}BB {position:.0%}={pts:.0f}"


class BollingerCondition(BaseCondition):
    name = "볼린저밴드"

    def score(self, code: str, data: dict) -> tuple:
        period, k = _get_bollinger_params()
        daily = data.get("daily", [])
        min60 = data.get("min60", [])
        details = []

        # 일봉 볼린저
        d_pts = None
        if len(daily) >= period + 5:
            d_closes = [d["close"] for d in daily]
            d_pts, d_detail = _bb_score(d_closes, period, k, "일봉")
            if d_detail:
                details.append(d_detail)

        # 60분봉 볼린저
        m_pts = None
        if len(min60) >= period + 5:
            m_closes = [d["close"] for d in min60]
            m_pts, m_detail = _bb_score(m_closes, period, k, "60분")
            if m_detail:
                details.append(m_detail)

        # 둘 다 있으면 평균, 하나만 있으면 그 값
        if d_pts is not None and m_pts is not None:
            pts = d_pts * 0.4 + m_pts * 0.6  # 60분봉 가중
        elif m_pts is not None:
            pts = m_pts
        elif d_pts is not None:
            pts = d_pts
        else:
            # 데이터 없으면 등락률 추정
            price_data = data.get("price", {})
            try:
                diff = float(price_data.get("diff", 0))
                if diff > 10:
                    return 25.0, f"과열 추정(등락 {diff:+}%)"
                elif diff > 5:
                    return 55.0, f"밴드 상단 추정(등락 {diff:+}%)"
                elif diff >= -2:
                    return 70.0, f"밴드 중간 추정(등락 {diff:+}%)"
                else:
                    return 40.0, f"밴드 하단 추정(등락 {diff:+}%)"
            except:
                return 50.0, "데이터 부족"

        return pts, ", ".join(details)


class Min60BollingerSellCondition(BaseCondition):
    """60분봉 볼린저밴드 매도 신호 (상단 이탈=고점수)"""
    name = "60분봉_볼린저_매도"

    def score(self, code: str, data: dict) -> tuple:
        min60 = data.get("min60", [])
        period, k = _get_bollinger_params()

        if len(min60) < period + 5:
            return 10.0, "60분봉 데이터 부족"

        closes = [d["close"] for d in min60]
        mid, upper, lower = _bollinger(closes, period, k)
        if mid is None:
            return 10.0, "볼린저 계산 실패"

        cur = closes[0]
        band_width = upper[0] - lower[0]
        if band_width == 0:
            return 10.0, "밴드폭 0"

        position = (cur - lower[0]) / band_width

        # 매도 관점: 상단에 가까울수록 고점수
        if position > 1.0:
            pts = 95.0  # 상단 이탈
        elif position > 0.85:
            pts = 70.0 + (position - 0.85) / 0.15 * 25.0
        elif position > 0.7:
            pts = 45.0 + (position - 0.7) / 0.15 * 25.0
        elif position > 0.5:
            pts = 20.0 + (position - 0.5) / 0.2 * 25.0
        else:
            pts = 10.0

        return pts, f"60분BB {position:.0%}"
