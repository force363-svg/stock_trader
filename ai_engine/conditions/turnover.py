"""
유동주식 턴오버율 분석

유동주식(상장주식수) 대비 거래량 비율로 매집/관심 집중도 판단
- 당일 턴오버율 vs 10일 평균 → 평소 대비 거래 활성도
- 당일 vs 최근 2~3일 평균 → 단기 추세 가속 여부

점수 기준:
- 당일 턴오버 > 10일 평균 2배 + 3일 추세 가속 → 고점수 (매집/관심 급증)
- 당일 턴오버 < 10일 평균 → 저점수 (관심 이탈)
- 과도하게 높은 턴오버 (5배 이상) → 과열 경고 (급등 후 급락 위험)
"""
from .base import BaseCondition


def _proportional_score(value: float, min_threshold: float, max_cap: float = None) -> float:
    """
    비례 가점 공통 함수.
    - value < min_threshold → 10점 (탈락)
    - value >= min_threshold → 비례 가점 (60~95점)
    - max_cap: 상한값 (없으면 min_threshold * 10 사용)
    """
    if value < min_threshold:
        return 10.0
    if max_cap is None:
        max_cap = min_threshold * 10
    if max_cap <= min_threshold:
        max_cap = min_threshold * 10
    ratio = min(1.0, (value - min_threshold) / (max_cap - min_threshold))
    return 60.0 + ratio * 35.0  # 60 ~ 95


class TurnoverCondition(BaseCondition):
    """유동주식 대비 거래량 비율 (턴오버율) 분석"""
    name = "유동주식_턴오버"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        price_data = data.get("price", {})

        # ── 유동주식수 (상장주식수) 가져오기 ──
        listing = 0
        try:
            listing = int(float(price_data.get("listing", 0)))
        except Exception:
            pass

        if listing <= 0:
            return 50.0, "상장주식수 데이터 없음"

        # ── 당일 거래량 ──
        today_vol = 0
        try:
            today_vol = int(float(price_data.get("volume", 0)))
        except Exception:
            pass

        if today_vol <= 0:
            return 50.0, "거래량 데이터 없음"

        # ── 턴오버율 계산 (%) ──
        today_turnover = (today_vol / listing) * 100

        # ── 과거 일봉에서 턴오버율 시계열 구성 ──
        turnover_history = []
        for d in daily:
            vol = d.get("volume", 0)
            if vol > 0 and listing > 0:
                turnover_history.append((vol / listing) * 100)
            else:
                turnover_history.append(0)

        # ── 10일 평균 턴오버율 ──
        if len(turnover_history) >= 10:
            avg_10d = sum(turnover_history[:10]) / 10
        elif len(turnover_history) >= 3:
            avg_10d = sum(turnover_history) / len(turnover_history)
        else:
            avg_10d = 0

        # ── 최근 2~3일 평균 턴오버율 ──
        if len(turnover_history) >= 3:
            avg_3d = sum(turnover_history[:3]) / 3
        elif len(turnover_history) >= 1:
            avg_3d = turnover_history[0]
        else:
            avg_3d = 0

        if avg_10d <= 0:
            return 50.0, f"턴오버 {today_turnover:.2f}% (비교 데이터 부족)"

        # ── 점수 계산 ──
        pts = 50.0  # 기본 중립
        details = []

        # 1) 당일 vs 10일 평균 비율
        ratio_10d = today_turnover / avg_10d if avg_10d > 0 else 1.0

        if ratio_10d >= 5.0:
            pts += 30
            details.append(f"10일대비 {ratio_10d:.1f}배(급증)")
        elif ratio_10d >= 3.0:
            pts += 25
            details.append(f"10일대비 {ratio_10d:.1f}배(급증)")
        elif ratio_10d >= 2.0:
            pts += 20
            details.append(f"10일대비 {ratio_10d:.1f}배(증가)")
        elif ratio_10d >= 1.5:
            pts += 10
            details.append(f"10일대비 {ratio_10d:.1f}배")
        elif ratio_10d >= 1.0:
            details.append(f"10일대비 {ratio_10d:.1f}배(보통)")
        elif ratio_10d >= 0.5:
            pts -= 10
            details.append(f"10일대비 {ratio_10d:.1f}배(감소)")
        else:
            pts -= 20
            details.append(f"10일대비 {ratio_10d:.1f}배(급감)")

        # 2) 최근 3일 추세 (가속/감속)
        if avg_3d > 0 and avg_10d > 0:
            trend_ratio = avg_3d / avg_10d
            if trend_ratio >= 2.0:
                pts += 15
                details.append(f"3일추세 가속({trend_ratio:.1f}배)")
            elif trend_ratio >= 1.3:
                pts += 10
                details.append(f"3일추세 증가({trend_ratio:.1f}배)")
            elif trend_ratio < 0.7:
                pts -= 10
                details.append(f"3일추세 감소({trend_ratio:.1f}배)")

        # 3) 당일 vs 3일 평균 (당일 돌출 여부)
        if avg_3d > 0:
            ratio_3d = today_turnover / avg_3d
            if ratio_3d >= 2.0:
                pts += 10
                details.append(f"3일대비 {ratio_3d:.1f}배 돌출")
            elif ratio_3d < 0.5:
                pts -= 5
                details.append(f"3일대비 {ratio_3d:.1f}배 위축")

        pts = max(0, min(100, pts))
        detail_str = ", ".join(details) if details else "보통"

        return float(pts), (
            f"턴오버 {today_turnover:.2f}% "
            f"(10일평균 {avg_10d:.2f}%, 3일평균 {avg_3d:.2f}%) | "
            f"{detail_str}"
        )


class MinuteTurnoverCondition(BaseCondition):
    """60분봉 유동주식 대비 거래비중"""
    name = "60분봉_턴오버"

    def score(self, code: str, data: dict) -> tuple:
        min60 = data.get("min60", [])
        price_data = data.get("price", {})

        # 유동주식수 (상장주식수)
        listing = 0
        try:
            listing = int(float(price_data.get("listing", 0)))
        except Exception:
            pass

        if listing <= 0:
            return 50.0, "상장주식수 데이터 없음"

        if len(min60) < 3:
            return 50.0, "60분봉 데이터 부족"

        # 현재봉 거래량
        cur_vol = min60[0].get("volume", 0)
        if cur_vol <= 0:
            return 50.0, "60분봉 거래량 없음"

        # 현재봉 턴오버율 (%)
        cur_turnover = (cur_vol / listing) * 100

        # 비례 가점: 0.3% 이상 높을수록 가점
        pts = _proportional_score(cur_turnover, 0.3, 5.0)

        return pts, f"60분 턴오버 {cur_turnover:.3f}%"


class MinuteVolChangeCondition(BaseCondition):
    """60분봉 2봉평균 대비 거래량 변동율"""
    name = "60분봉_거래량변동"

    def score(self, code: str, data: dict) -> tuple:
        min60 = data.get("min60", [])

        if len(min60) < 3:
            return 50.0, "60분봉 데이터 부족"

        cur_vol = min60[0].get("volume", 0)
        if cur_vol <= 0:
            return 50.0, "60분봉 거래량 없음"

        # 2봉 평균 거래량
        prev_vols = [d.get("volume", 0) for d in min60[1:3] if d.get("volume", 0) > 0]
        if not prev_vols:
            return 50.0, "이전봉 거래량 없음"

        avg_vol = sum(prev_vols) / len(prev_vols)
        if avg_vol <= 0:
            return 50.0, "이전봉 거래량 없음"

        change_pct = (cur_vol / avg_vol) * 100  # 100% = 동일

        # 비례 가점: 90% 이상 높을수록 가점
        pts = _proportional_score(change_pct, 90.0, 500.0)

        return pts, f"60분 거래량변동 {change_pct:.0f}% (2봉평균대비)"


class DailyVolChangeCondition(BaseCondition):
    """일봉 2봉평균 대비 거래량 변동율"""
    name = "일봉_거래량변동"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])

        if len(daily) < 3:
            return 50.0, "일봉 데이터 부족"

        cur_vol = daily[0].get("volume", 0)
        if cur_vol <= 0:
            return 50.0, "일봉 거래량 없음"

        prev_vols = [d.get("volume", 0) for d in daily[1:3] if d.get("volume", 0) > 0]
        if not prev_vols:
            return 50.0, "이전봉 거래량 없음"

        avg_vol = sum(prev_vols) / len(prev_vols)
        if avg_vol <= 0:
            return 50.0, "이전봉 거래량 없음"

        change_pct = (cur_vol / avg_vol) * 100

        pts = _proportional_score(change_pct, 90.0, 500.0)

        return pts, f"일봉 거래량변동 {change_pct:.0f}% (2봉평균대비)"


class VolumeRateDisparityCondition(BaseCondition):
    """등락대비 거래량 괴리: 등락율 낮은데 거래량 높으면 가점 (세력 매집 신호)"""
    name = "등락대비_거래량괴리"

    def score(self, code: str, data: dict) -> tuple:
        min60 = data.get("min60", [])
        price_data = data.get("price", {})

        # 유동주식수
        listing = 0
        try:
            listing = int(float(price_data.get("listing", 0)))
        except Exception:
            pass

        if listing <= 0:
            return 50.0, "상장주식수 데이터 없음"

        if len(min60) < 2:
            return 50.0, "60분봉 데이터 부족"

        cur = min60[0]
        cur_vol = cur.get("volume", 0)
        cur_close = cur.get("close", 0)
        cur_open = cur.get("open", 0)

        if cur_vol <= 0 or cur_close <= 0 or cur_open <= 0:
            return 50.0, "60분봉 데이터 부족"

        # 60분봉 등락율
        change_pct = abs((cur_close - cur_open) / cur_open * 100)

        # 유동주식 대비 거래량 비율
        vol_ratio = (cur_vol / listing) * 100

        # 판단: 등락율 낮은데(< 3%) 거래량 높으면(> 0.3%) = 세력 매집
        if change_pct < 3.0 and vol_ratio >= 0.3:
            # 등락율이 낮을수록 + 거래량이 높을수록 = 높은 점수
            low_change_bonus = max(0, (3.0 - change_pct) / 3.0) * 20  # 0~20점
            vol_bonus = min(30, (vol_ratio - 0.3) / 2.0 * 30)  # 0~30점
            pts = 55.0 + low_change_bonus + vol_bonus
            pts = min(95.0, pts)
            return pts, f"괴리감지 등락:{change_pct:.1f}% 거래비중:{vol_ratio:.2f}% (조용+거래↑)"
        elif change_pct >= 3.0 and vol_ratio >= 0.3:
            # 등락율도 높고 거래량도 높으면 → 정상적 상승, 중립
            return 50.0, f"정상상승 등락:{change_pct:.1f}% 거래비중:{vol_ratio:.2f}%"
        elif change_pct < 3.0 and vol_ratio < 0.3:
            # 등락율 낮고 거래량도 낮으면 → 관심 없음
            return 30.0, f"무관심 등락:{change_pct:.1f}% 거래비중:{vol_ratio:.2f}%"
        else:
            return 40.0, f"등락:{change_pct:.1f}% 거래비중:{vol_ratio:.2f}%"


class Min15TurnoverCondition(BaseCondition):
    """15분봉 유동주식 대비 거래비중"""
    name = "15분봉_턴오버"

    def score(self, code: str, data: dict) -> tuple:
        min15 = data.get("min15", [])
        price_data = data.get("price", {})

        listing = 0
        try:
            listing = int(float(price_data.get("listing", 0)))
        except Exception:
            pass

        if listing <= 0:
            return 50.0, "상장주식수 데이터 없음"

        if len(min15) < 3:
            return 50.0, "15분봉 데이터 부족"

        cur_vol = min15[0].get("volume", 0)
        if cur_vol <= 0:
            return 50.0, "15분봉 거래량 없음"

        cur_turnover = (cur_vol / listing) * 100

        # 비례 가점: 0.3% 이상 높을수록 가점
        pts = _proportional_score(cur_turnover, 0.3, 5.0)

        return pts, f"15분 턴오버 {cur_turnover:.3f}%"
