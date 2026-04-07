"""
거래량 급증 조건
- 60분봉: 이전 2봉 평균 대비 현재 1봉 거래량 120%~9000%
- 당일 거래대금 500억 돌파
"""
from .base import BaseCondition


class VolumeSurgeCondition(BaseCondition):
    name = "거래량_급증"

    def score(self, code: str, data: dict) -> tuple:
        min60    = data.get("min60", [])
        price_data = data.get("price", {})
        pts    = 0.0
        details = []

        # 60분봉 거래량 급증
        if len(min60) >= 3:
            cur_vol  = min60[0]["volume"]
            prev_avg = (min60[1]["volume"] + min60[2]["volume"]) / 2
            if prev_avg > 0:
                ratio = (cur_vol / prev_avg) * 100
                if 120 <= ratio <= 9000:
                    if ratio >= 300:
                        pts += 50
                    elif ratio >= 200:
                        pts += 35
                    else:
                        pts += 20
                    details.append(f"60분봉 거래량 {ratio:.0f}%")

        # 당일 거래대금 500억 체크
        try:
            amount = int(float(price_data.get("value", price_data.get("tramt", 0))))
            if amount >= 50_000_000_000:  # 500억
                pts += 50
                details.append(f"거래대금 {amount//100_000_000}억")
            elif amount >= 20_000_000_000:  # 200억
                pts += 25
                details.append(f"거래대금 {amount//100_000_000}억")
        except:
            pass

        return min(100.0, pts), ", ".join(details) if details else "거래량 조건 미충족"
