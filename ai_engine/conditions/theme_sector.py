"""
테마/업종 조건 계산기
- 상승테마 소속 여부
- 업종지수 상승 여부
메인 캐시(창고)에서 데이터 읽기
"""
from .base import BaseCondition
from ..data.cache import get_cache


class ThemeCondition(BaseCondition):
    """상승테마 소속 여부 체크"""
    name = "상승테마"

    def score(self, code: str, data: dict) -> tuple:
        cache = get_cache()
        themes = cache.get("market_themes") or []
        stock_themes = cache.get("stock_themes") or {}

        if not themes:
            return 50.0, "테마 데이터 없음"

        # 이 종목이 소속된 상승테마 찾기
        my_themes = stock_themes.get(code, [])
        if not my_themes:
            return 30.0, "상승테마 미소속"

        # 상승테마만 필터
        up_themes = [t for t in my_themes if t.get("diff", 0) > 0]
        if up_themes:
            best = max(up_themes, key=lambda x: x["diff"])
            count = len(up_themes)
            pts = min(100, 70 + best["diff"] * 5)
            return pts, f"상승테마 {count}개 소속 (최고: {best['name']} +{best['diff']:.1f}%)"

        # 하락테마만 소속
        worst = min(my_themes, key=lambda x: x.get("diff", 0))
        return 25.0, f"하락테마 소속 ({worst['name']} {worst.get('diff', 0):+.1f}%)"


class SectorCondition(BaseCondition):
    """업종지수 상승 여부 체크"""
    name = "업종지수"

    def score(self, code: str, data: dict) -> tuple:
        cache = get_cache()
        sectors = cache.get("market_sectors") or []

        if not sectors:
            return 50.0, "업종 데이터 없음"

        # 상승 업종 비율 계산
        up_count = 0
        for s in sectors:
            try:
                diff = float(s.get("change", s.get("diff", 0)))
                if diff > 0:
                    up_count += 1
            except (ValueError, TypeError):
                pass
        total = len(sectors)
        up_ratio = up_count / total * 100 if total > 0 else 50

        # 상위 업종 평균 등락률
        diffs = []
        for s in sectors:
            try:
                diffs.append(float(s.get("change", s.get("diff", 0))))
            except (ValueError, TypeError):
                pass
        diffs.sort(reverse=True)
        avg_diff = sum(diffs[:5]) / min(5, len(diffs)) if diffs else 0

        if up_ratio >= 70 and avg_diff > 0.5:
            pts = min(100, 70 + avg_diff * 10)
            detail = f"업종 강세 (상승 {up_ratio:.0f}%, 상위평균 +{avg_diff:.1f}%)"
        elif up_ratio >= 50:
            pts = 55.0
            detail = f"업종 보통 (상승 {up_ratio:.0f}%)"
        else:
            pts = max(10, 40 - (50 - up_ratio))
            detail = f"업종 약세 (상승 {up_ratio:.0f}%)"

        return pts, detail
