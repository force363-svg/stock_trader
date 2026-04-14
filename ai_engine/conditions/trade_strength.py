"""
체결강도 조건
- 체결강도 120% 이상 = 강한 매수세
"""
from .base import BaseCondition


class TradeStrengthCondition(BaseCondition):
    name = "당일_체결강도"

    def score(self, code: str, data: dict) -> tuple:
        price_data = data.get("price", {})
        # t1102 응답 필드에서 체결강도 계산
        # 방법1: 직접 체결강도 필드
        # 방법2: 매수/매도 호가 거래량 비율 (dvol=매도, svol=매수)
        # 방법3: 외인 매수/매도 비율
        try:
            buy_cnt  = float(price_data.get("buy_ccount",  price_data.get("svalue", 0)))
            sell_cnt = float(price_data.get("sell_ccount", price_data.get("bvalue", 0)))
            strength = float(price_data.get("cojd", price_data.get("cgubun", 0)))
            if strength == 0 and sell_cnt > 0:
                strength = (buy_cnt / sell_cnt) * 100

            # t1102 호가 데이터에서 체결강도 추정 (dvol=매도잔량, svol=매수잔량)
            if strength <= 0:
                total_dvol = sum(float(price_data.get(f"dvol{i}", 0)) for i in range(1, 6))
                total_svol = sum(float(price_data.get(f"svol{i}", 0)) for i in range(1, 6))
                if total_dvol > 0:
                    strength = (total_svol / total_dvol) * 100

            # 외인 매수/매도 비율로 보조
            if strength <= 0:
                fwd = float(price_data.get("fwdvl", 0))  # 외인매도
                fws = float(price_data.get("fwsvl", 0))  # 외인매수
                if fwd > 0:
                    strength = (fws / fwd) * 100
                elif fws > 0:
                    strength = 150  # 매도 없이 매수만

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
