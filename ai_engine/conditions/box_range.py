"""
박스권(지지·저항) 조건
- 최근 N일 고가/저가로 박스 범위 설정
- 현재가 위치에 따른 점수 반환
- 돌파/이탈 판단
"""
from .base import BaseCondition
from ._config_helper import load_defaults


class BoxRangeCondition(BaseCondition):
    """
    박스권 분석 조건
    - 최근 20일 고가·저가로 박스 범위 산출
    - 현재가가 박스 상단 돌파 → 매수 신호 (높은 점수)
    - 현재가가 박스 하단 이탈 → 매도 신호 (낮은 점수)
    - 박스 내 위치에 따라 점수 배분

    키워드: "박스권", "지지선", "저항선", "돌파", "이탈", "신고가", "신저가"
    """
    name = "박스권_분석"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])

        # 일봉 없으면 52주 고저로 박스 추정
        if len(daily) < 22:
            price_data = data.get("price", {})
            try:
                current = float(price_data.get("price", 0))
                high52  = float(price_data.get("high52w", 0))
                low52   = float(price_data.get("low52w", 0))
                if current > 0 and high52 > low52:
                    pos = (current - low52) / (high52 - low52) * 100
                    if current > high52:
                        return 90.0, f"52주 신고가 돌파"
                    elif pos >= 80:
                        return 75.0, f"52주 상단 근접({pos:.0f}%)"
                    elif pos >= 50:
                        return 55.0, f"52주 중간({pos:.0f}%)"
                    elif pos >= 20:
                        return 35.0, f"52주 하단({pos:.0f}%)"
                    else:
                        return 15.0, f"52주 저점 근접({pos:.0f}%)"
            except:
                pass
            return 50.0, "박스권 데이터 부족"

        closes = [d["close"] for d in daily]
        highs  = [d["high"]  for d in daily]
        lows   = [d["low"]   for d in daily]
        current = closes[0]

        # ── N일 박스 (단기) — defaults.box_period에서 기간 읽기 ──
        defaults = load_defaults()
        box_period = int(defaults.get("box_period", 20))
        box20_high = max(highs[:box_period])
        box20_low  = min(lows[:box_period])
        box20_range = box20_high - box20_low

        if box20_range <= 0:
            return 50.0, "박스 범위 계산 불가"

        # 현재가의 박스 내 위치 (0% = 하단, 100% = 상단)
        position = (current - box20_low) / box20_range * 100

        details = []
        pts = 0

        # ── 박스 돌파/이탈 판단 ──
        if current > box20_high:
            # 상단 돌파 (브레이크아웃) → 강한 매수 신호
            breakout_pct = (current - box20_high) / box20_high * 100
            pts = 90
            details.append(f"20일 상단 돌파({breakout_pct:+.1f}%)")

            # 거래량 동반 확인
            if daily[0].get("volume", 0) > 0 and len(daily) >= 5:
                avg_vol = sum(d.get("volume", 0) for d in daily[1:6]) / 5
                if avg_vol > 0 and daily[0]["volume"] > avg_vol * 1.5:
                    pts = min(100, pts + 10)
                    details.append("거래량 동반")

        elif current < box20_low:
            # 하단 이탈 → 매도 신호
            breakdown_pct = (current - box20_low) / box20_low * 100
            pts = 10
            details.append(f"20일 하단 이탈({breakdown_pct:+.1f}%)")

        else:
            # 박스 내부 — 위치에 따라 점수
            if position >= 80:
                pts = 75
                details.append(f"저항선 근접({position:.0f}%)")
            elif position >= 60:
                pts = 65
                details.append(f"박스 상단({position:.0f}%)")
            elif position >= 40:
                pts = 50
                details.append(f"박스 중간({position:.0f}%)")
            elif position >= 20:
                pts = 35
                details.append(f"박스 하단({position:.0f}%)")
            else:
                pts = 20
                details.append(f"지지선 근접({position:.0f}%)")

        # ── 60일 박스 (중기) — 추세 확인용 ──
        if len(daily) >= 62:
            box60_high = max(highs[:60])
            box60_low  = min(lows[:60])
            box60_range = box60_high - box60_low

            if box60_range > 0:
                pos60 = (current - box60_low) / box60_range * 100
                if current > box60_high:
                    details.append("60일 신고가")
                    pts = min(100, pts + 5)
                elif current < box60_low:
                    details.append("60일 신저가")
                    pts = max(0, pts - 5)
                elif pos60 >= 80:
                    details.append(f"60일 상단({pos60:.0f}%)")
                elif pos60 <= 20:
                    details.append(f"60일 하단({pos60:.0f}%)")

        # ── 박스 폭(변동성) 정보 ──
        volatility = box20_range / ((box20_high + box20_low) / 2) * 100
        details.append(f"변동폭 {volatility:.1f}%")

        detail = ", ".join(details)
        return float(pts), detail
