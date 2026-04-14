"""
이평선 배열 조건
- EMA5 > EMA20 > EMA50 > EMA200 정배열
- 200일선 상승 여부
- 50일선 > 200일선 여부
"""
from .base import BaseCondition


def _ema(closes: list, period: int) -> list:
    """지수이동평균 계산 (최신이 index 0인 리스트 → 역순으로 계산 후 반전)"""
    if len(closes) < period:
        return []
    arr = list(reversed(closes))  # 오래된 것부터
    k = 2.0 / (period + 1)
    ema = [arr[0]]
    for price in arr[1:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return list(reversed(ema))   # 다시 최신순


def _sma(closes: list, period: int) -> list:
    """단순이동평균"""
    if len(closes) < period:
        return []
    result = []
    arr = list(reversed(closes))
    for i in range(len(arr) - period + 1):
        result.append(sum(arr[i:i+period]) / period)
    return list(reversed(result))


class MAAlignmentCondition(BaseCondition):
    name = "이평선_배열상태"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        if len(daily) < 210:
            # 일봉 부족 시 price 등락률 기반 추정
            price_data = data.get("price", {})
            try:
                diff = float(price_data.get("diff", 0))
                if diff > 3:
                    return 70.0, f"상승세({diff:+}%) - 일봉 데이터 부족"
                elif diff > 0:
                    return 55.0, f"소폭 상승({diff:+}%) - 일봉 데이터 부족"
                elif diff > -2:
                    return 40.0, f"보합/소폭하락({diff:+}%) - 일봉 데이터 부족"
                else:
                    return 20.0, f"하락세({diff:+}%) - 일봉 데이터 부족"
            except:
                return 50.0, "데이터 부족"

        closes = [d["close"] for d in daily]

        ema5   = _ema(closes, 5)
        ema20  = _ema(closes, 20)
        ema50  = _ema(closes, 50)
        ema200 = _ema(closes, 200)
        sma50  = _sma(closes, 50)
        sma200 = _sma(closes, 200)

        if not (ema5 and ema20 and ema50 and ema200 and sma50 and sma200):
            return 0.0, "계산 실패"

        pts = 0
        details = []

        # 1. 200일선 상승 (최근 2봉 비교)
        if len(sma200) >= 2 and sma200[0] > sma200[1]:
            pts += 20
            details.append("200일선↑")

        # 2. 50일선 > 200일선
        if sma50[0] > sma200[0]:
            pts += 15
            details.append("50>200")

        # 3. EMA20 > EMA50
        if ema20[0] > ema50[0]:
            pts += 15
            details.append("EMA20>50")

        # 4. EMA5 > EMA20
        if ema5[0] > ema20[0]:
            pts += 20
            details.append("EMA5>20")

        # 5. 현재가 > EMA5
        if closes[0] > ema5[0]:
            pts += 15
            details.append("종가>EMA5")

        # 6. EMA5 상승 (최근 2봉)
        if len(ema5) >= 2 and ema5[0] > ema5[1]:
            pts += 10
            details.append("EMA5↑")

        # 7. 50일선 상승
        if len(sma50) >= 2 and sma50[0] > sma50[1]:
            pts += 5
            details.append("50일선↑")

        detail = ", ".join(details) if details else "정배열 조건 미충족"
        return float(pts), detail

    def check_screening(self, code: str, data: dict, enabled_names: set = None) -> bool:
        """
        범용 이평선 스크리닝 — 조건명을 자동 파싱
        지원 패턴:
          비교: "50일선 > 200일선", "EMA20 > EMA50", "종가 > EMA5", "5 > 20"
          상승: "200일선 상승", "EMA5 상승"
        """
        import re
        daily = data.get("daily", [])
        if not daily:
            return False
        closes = [d["close"] for d in daily]

        if not enabled_names:
            return True

        # MA 캐시 (같은 기간 중복 계산 방지)
        _ema_c, _sma_c = {}, {}
        def get_ema(p):
            if p not in _ema_c:
                _ema_c[p] = _ema(closes, p)
            return _ema_c[p]
        def get_sma(p):
            if p not in _sma_c:
                _sma_c[p] = _sma(closes, p)
            return _sma_c[p]

        def parse_token(token):
            """토큰 → (타입, 기간). 종가=(close,0), EMA5=(ema,5), 200일선=(sma,200)"""
            token = token.strip()
            if token == "종가":
                return ("close", 0)
            m = re.match(r'[Ee][Mm][Aa]\s*(\d+)', token)
            if m:
                return ("ema", int(m.group(1)))
            m = re.match(r'(\d+)\s*일?선?$', token)
            if m:
                return ("sma", int(m.group(1)))
            return None

        def current_val(vtype, period):
            if vtype == "close":
                return closes[0] if closes else None
            vals = get_ema(period) if vtype == "ema" else get_sma(period)
            return vals[0] if vals else None

        def prev_val(vtype, period):
            vals = get_ema(period) if vtype == "ema" else get_sma(period)
            return vals[1] if vals and len(vals) >= 2 else None

        # 필요한 최대 기간 계산 → 데이터 길이 체크
        max_period = 0
        for name in enabled_names:
            for p in re.findall(r'(\d+)', name):
                pi = int(p)
                if pi <= 500:  # 비정상 큰 수 무시
                    max_period = max(max_period, pi)
        if len(closes) < max_period + 10:
            return False

        for name in enabled_names:
            # 비교 조건: "A > B"
            cmp_m = re.search(r'(.+?)\s*>\s*(.+?)$', name)
            if cmp_m:
                left = parse_token(cmp_m.group(1))
                right = parse_token(cmp_m.group(2))
                if left and right:
                    lv = current_val(*left)
                    rv = current_val(*right)
                    if lv is None or rv is None:
                        return False
                    if not (lv > rv):
                        return False
                continue

            # 상승 조건: "X 상승"
            rise_m = re.search(r'(.+?)\s*상승', name)
            if rise_m:
                target = parse_token(rise_m.group(1))
                if target:
                    cv = current_val(*target)
                    pv = prev_val(*target)
                    if cv is None or pv is None:
                        return False
                    if not (cv > pv):
                        return False
                continue

        return True


class MASupportCondition(BaseCondition):
    """
    이동평균선 지지/이탈 판단
    - 현재가가 특정 이평선(5/20/60/120일) 위에 있으면 → 지지 중 (매수 관점 높은 점수)
    - 아래에 있으면 → 이탈 (매도 관점 높은 점수)
    - 이평선과의 거리(이격도)도 함께 반환
    """
    name = "이평선_지지"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])

        # 일봉 데이터 없으면 price에서 52주 고저/등락 기반 추정
        if len(daily) < 20:
            price_data = data.get("price", {})
            try:
                current = float(price_data.get("price", 0))
                high52  = float(price_data.get("high52w", 0))
                low52   = float(price_data.get("low52w", 0))
                diff    = float(price_data.get("diff", 0))
                if current > 0 and high52 > 0 and low52 > 0:
                    # 52주 범위에서 현재가 위치
                    pos = (current - low52) / (high52 - low52) * 100 if high52 > low52 else 50
                    pts = 0
                    details = []
                    if pos >= 70:
                        pts = 80
                        details.append(f"52주 상단({pos:.0f}%)")
                    elif pos >= 40:
                        pts = 60
                        details.append(f"52주 중간({pos:.0f}%)")
                    else:
                        pts = 30
                        details.append(f"52주 하단({pos:.0f}%)")
                    if diff > 0:
                        pts = min(100, pts + 10)
                        details.append(f"상승 중({diff:+}%)")
                    return float(pts), ", ".join(details)
            except:
                pass
            return 50.0, "이평선 데이터 부족"

        closes = [d["close"] for d in daily]
        current = closes[0]

        # 주요 이평선 계산
        sma20  = _sma(closes, 20)
        sma60  = _sma(closes, 60)
        ema5   = _ema(closes, 5)
        ema20  = _ema(closes, 20)

        if not sma20:
            return 50.0, "이평선 계산 실패"

        pts = 0
        max_pts = 0   # 가용 이평선에 따른 만점 (정규화용)
        details = []

        # EMA5 지지 (단기)
        if ema5:
            max_pts += 20
            gap5 = (current - ema5[0]) / ema5[0] * 100
            if current >= ema5[0]:
                pts += 20
                details.append(f"EMA5 지지({gap5:+.1f}%)")
            else:
                details.append(f"EMA5 이탈({gap5:+.1f}%)")

        # 20일선 지지 (중단기)
        max_pts += 30
        gap20 = (current - sma20[0]) / sma20[0] * 100
        if current >= sma20[0]:
            pts += 30
            details.append(f"20일선 지지({gap20:+.1f}%)")
        else:
            details.append(f"20일선 이탈({gap20:+.1f}%)")

        # EMA20 지지
        if ema20:
            max_pts += 15
            gap_ema20 = (current - ema20[0]) / ema20[0] * 100
            if current >= ema20[0]:
                pts += 15
            # detail은 20일선과 중복 방지 — 생략

        # 60일선 지지 (중기) — 데이터 부족 시 자동 건너뜀
        if sma60:
            max_pts += 25
            gap60 = (current - sma60[0]) / sma60[0] * 100
            if current >= sma60[0]:
                pts += 25
                details.append(f"60일선 지지({gap60:+.1f}%)")
            else:
                details.append(f"60일선 이탈({gap60:+.1f}%)")
        elif len(daily) < 65:
            details.append("60일선 데이터 부족")

        # 120일선 — 데이터 부족 시 자동 건너뜀
        if len(daily) >= 125:
            sma120 = _sma(closes, 120)
            if sma120:
                max_pts += 10
                gap120 = (current - sma120[0]) / sma120[0] * 100
                if current >= sma120[0]:
                    pts += 10
                    details.append(f"120일선 지지")
                else:
                    details.append(f"120일선 이탈")
        else:
            details.append("120일선 데이터 부족")

        # 정규화: 가용 이평선 만점 기준으로 100점 스케일 변환
        if max_pts > 0:
            normalized = (pts / max_pts) * 100.0
        else:
            normalized = 50.0

        detail = ", ".join(details) if details else "지지 없음"
        return min(100.0, normalized), detail
