"""
RSI 조건
- 기간: engine_config.json defaults.rsi_period 또는 설명에서 파싱
- 디폴트: 14
"""
from .base import BaseCondition
from ._config_helper import load_defaults


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


def _get_rsi_period() -> int:
    """defaults에서 RSI 기간 로드"""
    defaults = load_defaults()
    return int(defaults.get("rsi_period", 14))


def _rsi_score(rsi: float) -> float:
    """RSI 값 → 점수 변환 (30~70 건강, 50~65 최적)"""
    if 50 <= rsi <= 65:
        return 90.0
    elif 40 <= rsi < 50:
        return 70.0
    elif 65 < rsi <= 70:
        return 60.0
    elif 30 <= rsi < 40:
        return 50.0
    elif rsi > 70:
        return 30.0
    else:
        return 20.0


class RSICondition(BaseCondition):
    name = "RSI"

    def score(self, code: str, data: dict) -> tuple:
        period = _get_rsi_period()
        daily = data.get("daily", [])
        min60 = data.get("min60", [])
        details = []

        # 일봉 RSI
        d_pts = None
        if len(daily) >= period + 6:
            d_closes = [d["close"] for d in daily]
            d_rsi = _rsi(d_closes, period)
            d_pts = _rsi_score(d_rsi)
            details.append(f"일봉RSI {d_rsi:.1f}={d_pts:.0f}")

        # 60분봉 RSI
        m_pts = None
        if len(min60) >= period + 6:
            m_closes = [d["close"] for d in min60]
            m_rsi = _rsi(m_closes, period)
            m_pts = _rsi_score(m_rsi)
            details.append(f"60분RSI {m_rsi:.1f}={m_pts:.0f}")

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
                if diff > 7:
                    return 30.0, f"과매수 추정(등락 {diff:+}%)"
                elif diff > 3:
                    return 60.0, f"RSI 추정 양호(등락 {diff:+}%)"
                elif diff >= -2:
                    return 70.0, f"RSI 추정 중립(등락 {diff:+}%)"
                else:
                    return 50.0, f"RSI 추정 약세(등락 {diff:+}%)"
            except:
                return 50.0, "데이터 부족"

        return pts, ", ".join(details)


class Min60RSISellCondition(BaseCondition):
    """60분봉 RSI 매도 신호 (과매수=고점수)"""
    name = "60분봉_RSI_매도"

    def score(self, code: str, data: dict) -> tuple:
        min60 = data.get("min60", [])
        period = _get_rsi_period()

        if len(min60) < period + 6:
            return 10.0, "60분봉 데이터 부족"

        closes = [d["close"] for d in min60]
        rsi = _rsi(closes, period)

        # 매도 관점: RSI 높을수록 고점수 (과매수 = 매도 타이밍)
        if rsi >= 80:
            pts = 95.0
        elif rsi >= 70:
            pts = 60.0 + (rsi - 70) / 10.0 * 35.0
        elif rsi >= 60:
            pts = 30.0 + (rsi - 60) / 10.0 * 30.0
        elif rsi >= 50:
            pts = 15.0 + (rsi - 50) / 10.0 * 15.0
        else:
            pts = 10.0

        return pts, f"60분RSI {rsi:.1f}"
