"""
수급 연속성 조건
- 최근 N일 중 외인+기관 합산 순매수 발생 일수
- N: engine_config.json defaults.supply_days (디폴트 5)
"""
from .base import BaseCondition
from ._config_helper import load_defaults


class SupplyContinuityCondition(BaseCondition):
    name = "수급_연속성"

    def score(self, code: str, data: dict) -> tuple:
        supply = data.get("supply", [])

        # t1716 수급 데이터가 없으면 t1102 price에서 외인 매수/매도로 추정
        if not supply:
            price_data = data.get("price", {})
            fwd = float(price_data.get("fwdvl", 0))  # 외인매도
            fws = float(price_data.get("fwsvl", 0))  # 외인매수
            ftd_cha = float(price_data.get("ftradmdcha", 0))  # 외인매도 대금변화
            fts_cha = float(price_data.get("ftradmscha", 0))  # 외인매수 대금변화

            if fws > 0 or fwd > 0:
                net = fws - fwd
                total_vol = fws + fwd
                if total_vol > 0:
                    ratio = (net / total_vol + 1) / 2  # -1~1 → 0~1
                    pts = ratio * 100
                    status = "순매수" if net > 0 else "순매도"
                    return float(pts), f"외인 당일 {status} ({fws:,.0f}/{fwd:,.0f})"
            return 50.0, "수급 데이터 없음"

        defaults = load_defaults()
        n_days = int(defaults.get("supply_days", 5))
        days = supply[:n_days]
        buy_days = sum(1 for d in days if d.get("total_net", 0) > 0)
        total    = len(days)

        if total == 0:
            return 50.0, "수급 데이터 없음"

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
