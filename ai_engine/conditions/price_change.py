"""
등락율 조건 계산기
- 전일대비 등락율
- 시가대비 등락율
data["price"]에서 직접 추출
"""
from .base import BaseCondition


class PriceChangeCondition(BaseCondition):
    """전일대비/시가대비 등락율 체크"""
    name = "등락율"

    def score(self, code: str, data: dict) -> tuple:
        price_data = data.get("price", {})
        if not price_data:
            return 50.0, "가격 데이터 없음"

        # 전일대비 등락율
        try:
            diff_rate = float(price_data.get("diff", price_data.get("rate", 0)))
        except Exception:
            diff_rate = 0.0

        # 시가대비 등락율
        try:
            cur_price = float(price_data.get("price", price_data.get("close", 0)))
            open_price = float(price_data.get("open", 0))
            if open_price > 0:
                open_rate = (cur_price - open_price) / open_price * 100
            else:
                open_rate = 0.0
        except Exception:
            open_rate = 0.0

        # 점수화: 적당한 상승(+2~+5%)이 최고점, 과도한 상승은 감점
        if 2.0 <= diff_rate <= 5.0:
            pts = 85.0
        elif 1.0 <= diff_rate < 2.0:
            pts = 65.0
        elif 5.0 < diff_rate <= 7.0:
            pts = 70.0
        elif diff_rate > 7.0:
            pts = 40.0  # 과도한 급등 → 추격매수 위험
        elif 0 <= diff_rate < 1.0:
            pts = 50.0
        else:
            pts = 30.0  # 하락 중

        detail = f"전일대비 {diff_rate:+.1f}%, 시가대비 {open_rate:+.1f}%"
        return pts, detail


class DayChangeCondition(BaseCondition):
    """전일대비 등락율 전용"""
    name = "전일대비"

    def score(self, code: str, data: dict) -> tuple:
        price_data = data.get("price", {})
        try:
            diff_rate = float(price_data.get("diff", price_data.get("rate", 0)))
        except Exception:
            return 50.0, "데이터 없음"

        # 역비례: 2~9% 범위, 낮을수록 고점수
        if diff_rate < 2.0 or diff_rate > 9.0:
            pts = 10.0  # 범위 밖 탈락
        else:
            # 2% → 95점, 9% → 60점 역비례
            ratio = (diff_rate - 2.0) / (9.0 - 2.0)
            pts = 95.0 - ratio * 35.0  # 95 → 60

        return pts, f"전일대비 {diff_rate:+.1f}%"


class OpenChangeCondition(BaseCondition):
    """시가대비 등락율 전용"""
    name = "시가대비"

    def score(self, code: str, data: dict) -> tuple:
        price_data = data.get("price", {})
        try:
            cur_price = float(price_data.get("price", price_data.get("close", 0)))
            open_price = float(price_data.get("open", 0))
            if open_price > 0:
                open_rate = (cur_price - open_price) / open_price * 100
            else:
                return 50.0, "시가 데이터 없음"
        except Exception:
            return 50.0, "계산 실패"

        # 역비례: 2~9% 범위, 낮을수록 고점수
        if open_rate < 2.0 or open_rate > 9.0:
            pts = 10.0  # 범위 밖 탈락
        else:
            ratio = (open_rate - 2.0) / (9.0 - 2.0)
            pts = 95.0 - ratio * 35.0  # 95 → 60

        return pts, f"시가대비 {open_rate:+.1f}%"


class MinuteChangeCondition(BaseCondition):
    """60분봉 1봉전 대비 등락율"""
    name = "60분봉_등락율"

    def score(self, code: str, data: dict) -> tuple:
        min60 = data.get("min60", [])

        if len(min60) < 2:
            return 50.0, "60분봉 데이터 부족"

        cur_close = min60[0].get("close", 0)
        prev_close = min60[1].get("close", 0)

        if not cur_close or not prev_close:
            return 50.0, "60분봉 종가 없음"

        change_rate = (cur_close - prev_close) / prev_close * 100

        # 비례 가점: 1.7% 이상 높을수록 가점, 미만은 탈락
        from .turnover import _proportional_score
        pts = _proportional_score(change_rate, 1.7, 7.0)

        return pts, f"60분 1봉전대비 {change_rate:+.2f}% (현재:{cur_close:,} 전봉:{prev_close:,})"


class Min15ChangeCondition(BaseCondition):
    """15분봉 1봉전 대비 등락율"""
    name = "15분봉_등락율"

    def score(self, code: str, data: dict) -> tuple:
        min15 = data.get("min15", [])

        if len(min15) < 2:
            return 50.0, "15분봉 데이터 부족"

        cur_close = min15[0].get("close", 0)
        prev_close = min15[1].get("close", 0)

        if not cur_close or not prev_close:
            return 50.0, "15분봉 종가 없음"

        change_rate = (cur_close - prev_close) / prev_close * 100

        # 비례 가점: 1% 이상 높을수록 가점
        from .turnover import _proportional_score
        pts = _proportional_score(change_rate, 1.0, 7.0)

        return pts, f"15분 1봉전대비 {change_rate:+.2f}% (현재:{cur_close:,} 전봉:{prev_close:,})"


class MarketIndexCondition(BaseCondition):
    """코스피/코스닥 지수 상태 체크 (메인 캐시 활용)"""
    name = "코스피코스닥"

    def score(self, code: str, data: dict) -> tuple:
        try:
            from ..data.cache import get_cache
            cache = get_cache()
            market = cache.get("market_index") or {}
        except Exception:
            return 50.0, "캐시 읽기 실패"

        kospi_diff = float(market.get("kospi_diff", 0))
        kosdaq_diff = float(market.get("kosdaq_diff", 0))

        if not kospi_diff and not kosdaq_diff:
            return 50.0, "지수 데이터 없음"

        # 둘 다 상승이면 좋음
        avg_diff = (kospi_diff + kosdaq_diff) / 2

        if avg_diff >= 1.0:
            pts = 90.0
        elif avg_diff >= 0.5:
            pts = 75.0
        elif avg_diff >= 0:
            pts = 55.0
        elif avg_diff >= -0.5:
            pts = 40.0
        elif avg_diff >= -1.0:
            pts = 25.0
        else:
            pts = 10.0

        detail = f"코스피 {kospi_diff:+.1f}%, 코스닥 {kosdaq_diff:+.1f}%"
        return pts, detail
