"""
수급 연속성 조건
- 최근 5일 중 외인+기관 합산 순매수 발생 일수
"""
from .base import BaseCondition


class SupplyContinuityCondition(BaseCondition):
    name = "수급_연속성"

    def score(self, code: str, data: dict) -> tuple:
        supply = data.get("supply", [])
        if not supply:
            return 0.0, "수급 데이터 없음"

        days = supply[:5]
        buy_days = sum(1 for d in days if d.get("total_net", 0) > 0)
        total    = len(days)

        if total == 0:
            return 0.0, "수급 데이터 없음"

        # 5일 중 순매수 일수 비율로 점수화
        ratio = buy_days / total
        pts   = ratio * 100

        # 연속 순매수 보너스
        consecutive = 0
        for d in days:
            if d.get("total_net", 0) > 0:
                consecutive += 1
            else:
                break
        if consecutive >= 3:
            pts = min(100.0, pts + 10)

        detail = f"최근{total}일 중 {buy_days}일 순매수"
        if consecutive >= 2:
            detail += f" ({consecutive}일 연속)"
        return float(pts), detail
