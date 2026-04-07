"""
체결강도 조건
- 체결강도 120% 이상 = 강한 매수세
"""
from .base import BaseCondition


class TradeStrengthCondition(BaseCondition):
    name = "당일_체결강도"

    def score(self, code: str, data: dict) -> tuple:
        price_data = data.get("price", {})
        # t1102 응답 필드: cvolume(체결량), volume(거래량), sell_ccount(매도체결수), buy_ccount(매수체결수)
        # 체결강도 = 매수체결수 / 매도체결수 * 100
        try:
            buy_cnt  = float(price_data.get("buy_ccount",  price_data.get("svalue", 0)))
            sell_cnt = float(price_data.get("sell_ccount", price_data.get("bvalue", 0)))
            # 직접 체결강도 필드가 있으면 사용
            strength = float(price_data.get("cojd", price_data.get("cgubun", 0)))
            if strength == 0 and sell_cnt > 0:
                strength = (buy_cnt / sell_cnt) * 100

            if strength <= 0:
                return 0.0, "체결강도 데이터 없음"

            # 점수화: 120%=기본, 150%=만점
            if strength >= 150:
                pts = 100.0
            elif strength >= 120:
                pts = 60.0 + (strength - 120) / 30 * 40
            elif strength >= 100:
                pts = 30.0 + (strength - 100) / 20 * 30
            else:
                pts = max(0.0, strength / 100 * 30)

            return pts, f"체결강도 {strength:.1f}%"
        except Exception as e:
            return 0.0, f"계산 실패: {e}"
