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

        # 당일 거래량 vs 전일 거래량 (t1102 price 데이터)
        if not min60:
            try:
                vol_today = int(float(price_data.get("volume", 0)))
                vol_prev  = int(float(price_data.get("jnilvolume", 0)))
                if vol_prev > 0 and vol_today > 0:
                    vol_ratio = (vol_today / vol_prev) * 100
                    if vol_ratio >= 200:
                        pts += 40
                        details.append(f"당일거래량 전일대비 {vol_ratio:.0f}%")
                    elif vol_ratio >= 120:
                        pts += 20
                        details.append(f"당일거래량 전일대비 {vol_ratio:.0f}%")
                    elif vol_ratio >= 80:
                        pts += 10
                        details.append(f"당일거래량 전일대비 {vol_ratio:.0f}%")
                    else:
                        details.append(f"거래량 감소 {vol_ratio:.0f}%")
            except:
                pass

        # 당일 거래대금 체크
        try:
            amount = int(float(price_data.get("value", price_data.get("tramt", 0))))
            if amount >= 50_000_000_000:  # 500억
                pts += 50
                details.append(f"거래대금 {amount//100_000_000}억")
            elif amount >= 20_000_000_000:  # 200억
                pts += 25
                details.append(f"거래대금 {amount//100_000_000}억")
            elif amount >= 5_000_000_000:  # 50억
                pts += 10
                details.append(f"거래대금 {amount//100_000_000}억")
        except:
            pass

        return min(100.0, pts), ", ".join(details) if details else "거래량 조건 미충족"
