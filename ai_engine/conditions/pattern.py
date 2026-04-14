"""
고승률 패턴 계산기

1. 눌림목 패턴: 거래량 폭증 + 60봉 최고종가 + 이평선 지지 → 재상승
2. 단기 눌림목: 눌림목 + 조정기간 짧을수록 고점수 (세력 강도)
3. 스퀴즈 패턴: 이평선 밀집 + 거래량/변동폭 없음 → 폭발
"""
from .base import BaseCondition


def _inverse_proportional(value: float, good_max: float, bad_max: float = None) -> float:
    """
    역비례 점수: 값이 작을수록 고점수.
    - value ≤ 0 → 95점
    - value ≤ good_max → 95~60점 (비례)
    - value ≤ bad_max → 60~10점 (비례)
    - value > bad_max → 10점
    """
    if bad_max is None:
        bad_max = good_max * 2
    if value <= 0:
        return 95.0
    if value <= good_max:
        ratio = value / good_max
        return 95.0 - ratio * 35.0  # 95 → 60
    if value <= bad_max:
        ratio = (value - good_max) / (bad_max - good_max)
        return 60.0 - ratio * 50.0  # 60 → 10
    return 10.0


def _check_min60_required(data: dict) -> tuple:
    """
    60분봉 필수 4박자 + 15분봉 확인 (세 패턴 공통)
    1) 거래량(유동주식 대비) 3봉 평균 대비 100% 이상
    2) 60분봉 60봉 최고종가 근접/돌파
    3) 60분봉 전봉 대비 등락 상승
    4) 윗꼬리 아닌가 (고가 대비 현재가 위치 0.3 이상)
    +) 15분봉 타이밍 확인 (보너스)

    Returns: (met_count, details_list)
      met_count: 충족 개수 (4박자 기준), -1=데이터 부족
      details_list: 상세 문자열 리스트
    """
    min60 = data.get("min60", [])
    min15 = data.get("min15", [])
    price_data = data.get("price", {})

    if len(min60) < 4:
        return -1, ["60분봉 데이터 부족"]

    listing = 0
    try:
        listing = int(float(price_data.get("listing", 0)))
    except Exception:
        pass

    met = 0
    details = []

    cur = min60[0]
    cur_close = cur.get("close", 0)
    cur_high = cur.get("high", 0)
    cur_low = cur.get("low", 0)
    cur_vol = cur.get("volume", 0)
    prev_close = min60[1].get("close", 0) if len(min60) > 1 else 0

    # ── 1) 거래량(유동주식 대비) 3봉 평균 대비 100% 이상 ──
    recent_3_vols = [d.get("volume", 0) for d in min60[:3] if d.get("volume", 0) > 0]
    avg_3bar = sum(recent_3_vols) / len(recent_3_vols) if recent_3_vols else 0

    if avg_3bar > 0 and cur_vol >= avg_3bar * 1.0:
        vol_ratio = cur_vol / avg_3bar
        met += 1
        details.append(f"60분거래량{vol_ratio:.1f}배✓")
    else:
        vol_ratio = cur_vol / avg_3bar if avg_3bar > 0 else 0
        details.append(f"60분거래량{vol_ratio:.1f}배✗")

    # ── 2) 60분봉 60봉 최고종가 근접/돌파 ──
    closes_60m = [d.get("close", 0) for d in min60[:60] if d.get("close", 0) > 0]
    if closes_60m and cur_close > 0:
        max_close_60m = max(closes_60m)
        if cur_close >= max_close_60m * 0.97:  # 3% 이내
            met += 1
            details.append(f"60분신고가✓({cur_close:,})")
        else:
            gap = (cur_close - max_close_60m) / max_close_60m * 100
            details.append(f"60분신고가✗({gap:+.1f}%)")
    else:
        details.append("60분신고가데이터X")

    # ── 3) 60분봉 전봉 대비 등락 상승 ──
    if cur_close > 0 and prev_close > 0:
        change_60m = (cur_close - prev_close) / prev_close * 100
        if change_60m > 0:
            met += 1
            details.append(f"60분등락{change_60m:+.1f}%✓")
        else:
            details.append(f"60분등락{change_60m:+.1f}%✗")
    else:
        details.append("60분등락데이터X")

    # ── 4) 윗꼬리 감지 (고가 대비 현재가 위치) ──
    if cur_high > 0 and cur_low > 0 and cur_high > cur_low:
        candle_range = cur_high - cur_low
        position = (cur_close - cur_low) / candle_range  # 0=바닥, 1=고가
        if position >= 0.3:
            met += 1
            details.append(f"윗꼬리X({position:.1%})✓")
        else:
            details.append(f"윗꼬리({position:.1%})✗")
    else:
        details.append("캔들데이터X")

    # ── 15분봉 타이밍 확인 (보너스: met에 가산하지 않고 별도 표시) ──
    min15_ok = False
    if len(min15) >= 2:
        m15_close = min15[0].get("close", 0)
        m15_prev = min15[1].get("close", 0)
        m15_high = min15[0].get("high", 0)
        m15_low = min15[0].get("low", 0)

        # 15분봉도 양봉 + 윗꼬리 아님
        m15_up = m15_close > m15_prev if m15_close > 0 and m15_prev > 0 else False
        m15_pos = (m15_close - m15_low) / (m15_high - m15_low) if m15_high > m15_low else 0.5
        m15_no_tail = m15_pos >= 0.3

        if m15_up and m15_no_tail:
            min15_ok = True
            m15_change = (m15_close - m15_prev) / m15_prev * 100 if m15_prev > 0 else 0
            details.append(f"15분확인✓({m15_change:+.1f}%)")
        else:
            details.append("15분확인✗")
    else:
        details.append("15분데이터X")

    return met, details


class PullbackCondition(BaseCondition):
    """
    눌림목 패턴 — 3순위
    시그널봉(거래량폭발+60봉최고종가) → 조정 → 이평선(20/60일) 지지

    시그널 조건 (10봉 이내):
    1) 유동주식 대비 거래량 500%+ 폭증
    2) 60봉 최고종가 달성
    3) 전봉 대비 거래량 변동율 400%+

    현재 조건:
    4) 20일선 또는 60일선에서 지지

    조정기간별 점수 (이평선 지지 확인 시):
    - 1~2일 → 95점
    - 3~5일 → 85점
    - 6~8일 → 70점
    - 9~10일 → 60점
    """
    name = "눌림목"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        price_data = data.get("price", {})

        if len(daily) < 60:
            return 50.0, "일봉 데이터 부족 (60봉 필요)"

        listing = 0
        try:
            listing = int(float(price_data.get("listing", 0)))
        except Exception:
            pass

        if listing <= 0:
            return 50.0, "상장주식수 데이터 없음"

        # ── 시그널 봉 찾기 (거래량 폭증 + 60봉 신고가) ──
        signal_day_idx = -1
        signal_turnover = 0
        signal_vol_change = 0
        signal_checks = []

        for i in range(1, min(11, len(daily) - 1)):
            d = daily[i]
            vol = d.get("volume", 0)
            close = d.get("close", 0)
            prev_vol = daily[i + 1].get("volume", 0) if i + 1 < len(daily) else 0

            # 조건1: 유동주식 대비 거래량 500%+
            turnover_pct = (vol / listing) * 100 if vol > 0 and listing > 0 else 0
            turnover_ok = turnover_pct >= 5.0

            # 조건2: 60봉 최고종가
            closes_60 = [dd.get("close", 0) for dd in daily[i:i + 60] if dd.get("close", 0) > 0]
            high_ok = (close >= max(closes_60) * 0.99) if closes_60 else False

            # 조건3: 전봉 대비 거래량 변동율 400%+
            vol_change = (vol / prev_vol) * 100 if prev_vol > 0 and vol > 0 else 0
            surge_ok = vol_change >= 400

            if turnover_ok and high_ok:
                signal_day_idx = i
                signal_turnover = turnover_pct
                signal_vol_change = vol_change
                if turnover_ok:
                    signal_checks.append(f"턴오버{turnover_pct:.1f}%")
                if high_ok:
                    signal_checks.append("60봉신고가")
                if surge_ok:
                    signal_checks.append(f"거래변동{vol_change:.0f}%")
                break

        if signal_day_idx < 0:
            return 20.0, "눌림목: 시그널봉 미발견 (10봉 이내)"

        # ── 조건4: 20일선 또는 60일선 지지 (비례점수) ──
        cur_close = daily[0].get("close", 0)
        ma_support_score = 0.0
        ma_detail = ""

        if cur_close > 0:
            closes_20 = [d.get("close", 0) for d in daily[:20] if d.get("close", 0) > 0]
            ma20 = sum(closes_20) / len(closes_20) if len(closes_20) >= 15 else 0

            closes_60_vals = [d.get("close", 0) for d in daily[:60] if d.get("close", 0) > 0]
            ma60 = sum(closes_60_vals) / len(closes_60_vals) if len(closes_60_vals) >= 45 else 0

            # 비례: 이평선에 가까울수록 고점수 (0%=95, 5%=60, 10%+=10)
            if ma20 > 0:
                gap20 = abs(cur_close - ma20) / ma20 * 100
                s20 = _inverse_proportional(gap20, 5.0, 10.0)
                if s20 > ma_support_score:
                    ma_support_score = s20
                    ma_detail = f"20일선({gap20:.1f}%이격→{s20:.0f}점)"
            if ma60 > 0:
                gap60 = abs(cur_close - ma60) / ma60 * 100
                s60 = _inverse_proportional(gap60, 5.0, 10.0)
                if s60 > ma_support_score:
                    ma_support_score = s60
                    ma_detail = f"60일선({gap60:.1f}%이격→{s60:.0f}점)"
                elif ma_detail:
                    ma_detail += f"+60일선({gap60:.1f}%→{s60:.0f})"

        if ma_support_score < 30:
            signal_str = ", ".join(signal_checks)
            return 20.0, f"눌림목: 시그널{signal_day_idx}일전[{signal_str}], 이평선이격과대"

        # ── 조정 기간별 점수 ──
        correction_days = signal_day_idx - 1

        if correction_days <= 2:
            base_pts = 95.0
            grade = "최강"
        elif correction_days <= 5:
            base_pts = 85.0
            grade = "강함"
        elif correction_days <= 8:
            base_pts = 70.0
            grade = "보통"
        elif correction_days <= 10:
            base_pts = 60.0
            grade = "약화"
        else:
            base_pts = 45.0
            grade = "장기조정"

        # 조정기간 점수 × 이평선 지지 비례 반영
        pts = base_pts * (ma_support_score / 95.0)

        signal_str = ", ".join(signal_checks)
        detail = (f"눌림목 {grade}: 조정{correction_days}일 "
                  f"(시그널{signal_day_idx}일전[{signal_str}]) "
                  f"{ma_detail}")

        return max(0, min(100, pts)), detail


class ShortPullbackCondition(BaseCondition):
    """
    단기 눌림목 — 사용자 1순위 패턴
    시그널봉(거래량폭발+60봉최고종가) → 1~4일 조정 → 오늘 다시 터짐

    시그널 조건 (10봉 이내):
    1) 유동주식 대비 거래량 500%+ 폭증
    2) 60봉 최고종가 달성
    3) 전봉 대비 거래량 변동율 400%+

    오늘 조건 (재돌파 확인):
    - 60봉 최고종가 근접/돌파 (상위 3% 이내)
    - 거래량(유동주식 대비) 상승
    - 등락율 양봉 (전일대비 상승)

    점수:
    - 조정 0일(연속상승) → 95점
    - 조정 1~2일 → 95점 (최강)
    - 조정 3~4일 → 85점 (강함)
    - 조정 5일+ → 급감 (패턴 약화)
    """
    name = "단기눌림목"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        price_data = data.get("price", {})

        if len(daily) < 60:
            return 50.0, "일봉 데이터 부족 (60봉 필요)"

        listing = 0
        try:
            listing = int(float(price_data.get("listing", 0)))
        except Exception:
            pass

        if listing <= 0:
            return 50.0, "상장주식수 데이터 없음"

        # ── 시그널 봉 찾기 (거래량 폭증 + 60봉 신고가 + 거래량 변동) ──
        # daily[0]=오늘, daily[1]=어제, ... 이므로 1부터 탐색 (오늘은 제외)
        signal_day_idx = -1
        signal_turnover = 0
        signal_vol_change = 0

        for i in range(1, min(10, len(daily) - 1)):
            d = daily[i]
            vol = d.get("volume", 0)
            close = d.get("close", 0)
            prev_vol = daily[i + 1].get("volume", 0) if i + 1 < len(daily) else 0

            # 조건1: 유동주식 대비 거래량 500%+
            turnover_pct = (vol / listing) * 100 if vol > 0 and listing > 0 else 0
            turnover_ok = turnover_pct >= 5.0

            # 조건2: 60봉 최고종가
            closes_60 = [dd.get("close", 0) for dd in daily[i:i + 60] if dd.get("close", 0) > 0]
            high_ok = (close >= max(closes_60) * 0.99) if closes_60 else False  # 1% 허용

            # 조건3: 전봉 대비 거래량 변동율 400%+
            vol_change = (vol / prev_vol) * 100 if prev_vol > 0 and vol > 0 else 0
            surge_ok = vol_change >= 400

            # 3개 중 2개 이상 충족 시 시그널 (핵심은 거래량폭증 + 신고가)
            if turnover_ok and high_ok:
                signal_day_idx = i
                signal_turnover = turnover_pct
                signal_vol_change = vol_change
                break

        if signal_day_idx < 0:
            return 20.0, "단기눌림목: 시그널봉 미발견 (10봉 이내)"

        # ── 조정 기간 ──
        correction_days = signal_day_idx - 1  # 시그널봉 다음날~오늘 전날

        # ── 오늘 재돌파 확인 ──
        today = daily[0]
        today_close = today.get("close", 0)
        today_vol = today.get("volume", 0)
        yesterday_close = daily[1].get("close", 0) if len(daily) > 1 else 0

        today_checks = []
        today_fails = []

        # 오늘1: 60봉 최고종가 근접/돌파 (상위 3% 이내)
        closes_60_all = [d.get("close", 0) for d in daily[:60] if d.get("close", 0) > 0]
        max_close_60 = max(closes_60_all) if closes_60_all else 0
        if max_close_60 > 0 and today_close >= max_close_60 * 0.97:
            today_checks.append(f"신고가근접({today_close:,}≥{int(max_close_60 * 0.97):,})")
        else:
            today_fails.append("신고가X")

        # 오늘2: 거래량(유동주식 대비) 상승
        today_turnover = (today_vol / listing) * 100 if today_vol > 0 and listing > 0 else 0
        # 최근 5일 평균 대비 1.5배 이상이면 거래량 상승
        recent_vols = [d.get("volume", 0) for d in daily[1:6] if d.get("volume", 0) > 0]
        avg_vol_5d = sum(recent_vols) / len(recent_vols) if recent_vols else 0
        vol_ratio = today_vol / avg_vol_5d if avg_vol_5d > 0 else 0
        if vol_ratio >= 1.5:
            today_checks.append(f"거래량상승({vol_ratio:.1f}배)")
        elif vol_ratio >= 1.0:
            today_checks.append(f"거래량보통({vol_ratio:.1f}배)")
        else:
            today_fails.append(f"거래량부족({vol_ratio:.1f}배)")

        # 오늘3: 등락율 양봉 (전일대비 상승)
        if yesterday_close > 0 and today_close > 0:
            today_change = (today_close - yesterday_close) / yesterday_close * 100
            if today_change >= 2.0:
                today_checks.append(f"등락+{today_change:.1f}%")
            elif today_change >= 0:
                today_checks.append(f"등락+{today_change:.1f}%(소폭)")
            else:
                today_fails.append(f"등락{today_change:+.1f}%")
        else:
            today_fails.append("등락확인불가")

        # ── 오늘 조건 미충족 시 감점 ──
        today_met = len(today_checks)

        if today_met == 0:
            # 오늘 아무 조건도 안 됨 → 패턴 아님
            fails = ", ".join(today_fails)
            return 25.0, f"단기눌림목: 시그널{signal_day_idx}일전, 오늘 재돌파X [{fails}]"

        # ── 점수: 조정기간 + 오늘 상태 ──
        if correction_days <= 0:
            base_pts = 95.0  # 연속 상승 (조정 없이 바로)
            grade = "연속돌파"
        elif correction_days <= 2:
            base_pts = 95.0
            grade = "최강"
        elif correction_days <= 4:
            base_pts = 85.0
            grade = "강함"
        else:
            base_pts = 60.0
            grade = "약화"

        # 오늘 조건 충족도에 따른 보정
        if today_met == 3:
            pts = base_pts  # 완벽
        elif today_met == 2:
            pts = base_pts - 5  # 소폭 감점
        else:
            pts = base_pts - 15  # 1개만 충족

        pts = max(0, min(100, pts))

        today_str = ", ".join(today_checks + today_fails)
        detail = (f"단기눌림목 {grade}: 조정{correction_days}일 "
                  f"(시그널{signal_day_idx}일전 턴오버{signal_turnover:.1f}%) "
                  f"오늘[{today_str}]")

        return pts, detail


class SqueezeCondition(BaseCondition):
    """
    스퀴즈 패턴 (일봉 기준)
    이평선 밀집 + 거래량 변동 없음 + 주가 변동폭 없음 → 폭발
    스프링 압축 후 폭발, 상한가 확률 70% 이상
    """
    name = "스퀴즈"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])

        if len(daily) < 30:
            return 50.0, "일봉 데이터 부족 (30봉 필요)"

        # 최근 20봉 데이터
        recent = daily[:20]
        closes = [d.get("close", 0) for d in recent if d.get("close", 0) > 0]
        volumes = [d.get("volume", 0) for d in recent if d.get("volume", 0) > 0]
        highs = [d.get("high", 0) for d in recent if d.get("high", 0) > 0]
        lows = [d.get("low", 0) for d in recent if d.get("low", 0) > 0]

        if len(closes) < 15 or len(volumes) < 15:
            return 50.0, "데이터 부족"

        details = []

        # ── 조건1: 이평선 밀집 (비례: 좁을수록 고점수) ──
        all_closes = [d.get("close", 0) for d in daily[:20] if d.get("close", 0) > 0]
        ma5 = sum(all_closes[:5]) / min(5, len(all_closes[:5])) if len(all_closes) >= 5 else 0
        ma10 = sum(all_closes[:10]) / min(10, len(all_closes[:10])) if len(all_closes) >= 10 else 0
        ma20 = sum(all_closes[:20]) / min(20, len(all_closes[:20])) if len(all_closes) >= 15 else 0

        ma_score = 50.0
        if ma5 > 0 and ma10 > 0 and ma20 > 0:
            ma_mid = (ma5 + ma10 + ma20) / 3
            ma_spread = (max(ma5, ma10, ma20) - min(ma5, ma10, ma20)) / ma_mid * 100
            ma_score = _inverse_proportional(ma_spread, 5.0, 10.0)
            details.append(f"이평밀집({ma_spread:.1f}%→{ma_score:.0f})")
        else:
            details.append("이평데이터X")

        # ── 조건2: 거래량 안정 (비례: 변동계수 낮을수록 고점수) ──
        recent_vols = volumes[:10]
        vol_score = 50.0
        if len(recent_vols) >= 5:
            vol_avg = sum(recent_vols) / len(recent_vols)
            if vol_avg > 0:
                vol_std = (sum((v - vol_avg) ** 2 for v in recent_vols) / len(recent_vols)) ** 0.5
                vol_cv = vol_std / vol_avg
                vol_score = _inverse_proportional(vol_cv, 0.3, 0.6)
                details.append(f"거래량CV({vol_cv:.2f}→{vol_score:.0f})")
            else:
                details.append("거래량없음")
        else:
            details.append("거래량부족")

        # ── 조건3: 변동폭 안정 (비례: ATR 비율 낮을수록 고점수) ──
        recent_ranges = []
        for d in recent[:10]:
            h, l = d.get("high", 0), d.get("low", 0)
            if h > 0 and l > 0:
                recent_ranges.append(h - l)

        price_score = 50.0
        if len(recent_ranges) >= 5 and closes[0] > 0:
            atr = sum(recent_ranges) / len(recent_ranges)
            atr_ratio = (atr / closes[0]) * 100
            price_score = _inverse_proportional(atr_ratio, 3.0, 6.0)
            details.append(f"ATR({atr_ratio:.1f}%→{price_score:.0f})")
        else:
            details.append("가격범위부족")

        # ── 압축 평균 점수 ──
        squeeze_avg = (ma_score + vol_score + price_score) / 3

        # ── 조건4: 폭발 감지 (오늘 봉이 압축 구간에서 돌출) ──
        explosion = False
        today = daily[0]
        today_vol = today.get("volume", 0)
        today_range = today.get("high", 0) - today.get("low", 0)
        today_close = today.get("close", 0)
        prev_close = daily[1].get("close", 0) if len(daily) > 1 else 0

        vol_avg_10 = sum(recent_vols[:10]) / len(recent_vols[:10]) if recent_vols else 0
        avg_range_10 = sum(recent_ranges) / len(recent_ranges) if recent_ranges else 0

        vol_explosion = today_vol >= vol_avg_10 * 2.0 if vol_avg_10 > 0 else False
        range_explosion = today_range >= avg_range_10 * 2.0 if avg_range_10 > 0 else False
        price_up = ((today_close - prev_close) / prev_close * 100 >= 3.0) if prev_close > 0 else False

        if vol_explosion and (range_explosion or price_up):
            explosion = True
            change = (today_close - prev_close) / prev_close * 100 if prev_close > 0 else 0
            details.append(f"폭발({change:+.1f}%)")
        elif vol_explosion:
            details.append("거래량돌출")
        else:
            details.append("폭발미감지")

        # ── 점수: 압축 비례 + 폭발 가점 ──
        pts = squeeze_avg
        if explosion:
            pts = min(95, pts + 15)  # 폭발 시 +15 가점

        pts = max(0, min(100, pts))

        detail = f"스퀴즈 압축avg:{squeeze_avg:.0f} [{', '.join(details)}]"

        return pts, detail


class DailyHighBreakCondition(BaseCondition):
    """
    일봉 60봉 최고종가 돌파 복합 조건
    1) 일봉 60봉 최고종가 발생/근접
    2) 거래량(유동주식 대비) 증가
    3) 등락율 양봉 확인
    3개 충족 → 90점, 2개 → 65점, 1개 → 35점, 0개 → 10점
    """
    name = "일봉60봉최고종가"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        price_data = data.get("price", {})

        if len(daily) < 60:
            return 50.0, "일봉 데이터 부족 (60봉 필요)"

        listing = 0
        try:
            listing = int(float(price_data.get("listing", 0)))
        except Exception:
            pass

        today = daily[0]
        today_close = today.get("close", 0)
        today_vol = today.get("volume", 0)
        prev_close = daily[1].get("close", 0) if len(daily) > 1 else 0

        if today_close <= 0:
            return 50.0, "종가 데이터 없음"

        met = 0
        details = []

        # ── 1) 일봉 60봉 최고종가 달성 (-1% 이내 허용) ──
        closes_60 = [d.get("close", 0) for d in daily[:60] if d.get("close", 0) > 0]
        if closes_60:
            max_close = max(closes_60)
            if today_close >= max_close:
                met += 1
                details.append(f"60봉신고가✓({today_close:,})")
            elif today_close >= max_close * 0.99:
                met += 1
                gap = (today_close - max_close) / max_close * 100
                details.append(f"60봉고가근접✓({gap:+.1f}%)")
            else:
                gap = (today_close - max_close) / max_close * 100
                details.append(f"60봉고가✗({gap:+.1f}%)")
        else:
            details.append("종가데이터X")

        # ── 2) 유동주식 대비 오늘 거래량 (턴오버율) ──
        if listing > 0 and today_vol > 0:
            turnover = (today_vol / listing) * 100
            if turnover >= 5.0:
                met += 1
                details.append(f"턴오버✓({turnover:.1f}%)")
            elif turnover >= 2.0:
                details.append(f"턴오버보통({turnover:.1f}%)")
            else:
                details.append(f"턴오버부족✗({turnover:.1f}%)")
        else:
            details.append("유동주식데이터X")

        # ── 3) 등락율 양봉 확인 ──
        if prev_close > 0 and today_close > 0:
            change_rate = (today_close - prev_close) / prev_close * 100
            if change_rate >= 2.0:
                met += 1
                details.append(f"등락율✓({change_rate:+.1f}%)")
            elif change_rate >= 0:
                details.append(f"등락율소폭({change_rate:+.1f}%)")
            else:
                details.append(f"등락율음봉✗({change_rate:+.1f}%)")
        else:
            details.append("등락율데이터X")

        # ── 점수 ──
        if met >= 3:
            pts = 90.0
        elif met >= 2:
            pts = 65.0
        elif met >= 1:
            pts = 35.0
        else:
            pts = 10.0

        detail_str = ", ".join(details)
        return pts, f"60봉돌파 {met}/3 [{detail_str}]"


class MADisparityCondition(BaseCondition):
    """
    이동평균 이격도 — 3순위 패턴
    MA200, MA50, MA20 간 이격도 분석
    - 밀집할수록 가점 (수렴 = 큰 움직임 준비)
    - 벌어질수록 감점 (과열 or 추세 말기)

    점수 기준 (이격도 = 세 이평선 간 최대 스프레드):
    - 3% 이내: 95점 (극도 밀집 = 폭발 임박)
    - 5% 이내: 85점
    - 8% 이내: 70점
    - 12% 이내: 55점
    - 15% 이내: 40점
    - 15% 초과: 25점 (과도 이격)
    """
    name = "이격도"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])

        if len(daily) < 200:
            if len(daily) < 20:
                return 50.0, "일봉 데이터 부족 (20봉 필요)"

        closes = [d.get("close", 0) for d in daily if d.get("close", 0) > 0]

        # ── 이동평균 계산 (MA5/20/50/200) ──
        ma5 = sum(closes[:5]) / 5 if len(closes) >= 5 else 0
        ma20 = sum(closes[:20]) / 20 if len(closes) >= 20 else 0
        ma50 = sum(closes[:50]) / 50 if len(closes) >= 50 else 0
        ma200 = sum(closes[:200]) / 200 if len(closes) >= 200 else 0

        # 사용 가능한 이평선 목록
        mas = {}
        if ma5 > 0:
            mas["5일"] = ma5
        if ma20 > 0:
            mas["20일"] = ma20
        if ma50 > 0:
            mas["50일"] = ma50
        if ma200 > 0:
            mas["200일"] = ma200

        if len(mas) < 2:
            return 50.0, "이평선 데이터 부족"

        # ── 이격도 계산 (최대-최소 / 중간값 * 100) ──
        ma_values = list(mas.values())
        ma_mid = sum(ma_values) / len(ma_values)
        spread = (max(ma_values) - min(ma_values)) / ma_mid * 100

        # ── 점수 (이격 낮을수록 고점수) ──
        pts = max(10.0, 95.0 - spread * 5.5)

        ma_strs = [f"{k}:{int(v):,}" for k, v in mas.items()]
        detail = f"이격도 {spread:.1f}% 봉수:{len(closes)} [{', '.join(ma_strs)}]"

        # 디버그
        try:
            import os as _dos, sys as _dsys
            _dp = _dos.path.join(_dos.path.dirname(_dos.path.dirname(_dos.path.dirname(_dos.path.abspath(__file__)))), "debug_disparity.txt")
            if getattr(_dsys, 'frozen', False):
                _dp = _dos.path.join(_dos.path.dirname(_dos.path.dirname(_dsys.executable)), "debug_disparity.txt")
            with open(_dp, "a", encoding="utf-8") as _ff:
                _ff.write(f"[{code}] spread={spread:.2f}% pts={pts:.1f} ma={dict((k,int(v)) for k,v in mas.items())} closes={len(closes)}\n")
        except Exception:
            pass

        return pts, detail


class ShortDisparityCondition(BaseCondition):
    """
    단기 이격도 — MA5/20 전용
    - 밀집(1%이내)=95점, 보통(3%이내)=75점, 이격(5%이내)=55점, 과이격=30점
    """
    name = "단기이격도"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        closes = [d.get("close", 0) for d in daily if d.get("close", 0) > 0]

        if len(closes) < 20:
            return 50.0, "일봉 데이터 부족 (20봉 필요)"

        ma5 = sum(closes[:5]) / 5
        ma20 = sum(closes[:20]) / 20

        if ma5 <= 0 or ma20 <= 0:
            return 50.0, "이평선 계산 실패"

        mid = (ma5 + ma20) / 2
        spread = abs(ma5 - ma20) / mid * 100

        # 이격 낮을수록 고점수 (단기라 10%에서 바닥)
        pts = max(10.0, 95.0 - spread * 8.5)

        detail = f"단기이격 {spread:.1f}% [5일:{int(ma5):,} 20일:{int(ma20):,}]"
        return pts, detail


class Min60DisparityCondition(BaseCondition):
    """
    60분봉 이동평균 이격도
    MA5, MA20, MA50 간 이격도 분석
    - 밀집할수록 가점 (수렴 = 단기 폭발 준비)
    - 벌어질수록 감점

    점수 기준:
    - 2% 이내: 95점 (극밀집)
    - 4% 이내: 85점
    - 6% 이내: 70점
    - 9% 이내: 55점
    - 12% 이내: 40점
    - 12% 초과: 25점
    """
    name = "60분봉_이격도"

    def score(self, code: str, data: dict) -> tuple:
        min60 = data.get("min60", [])

        if len(min60) < 50:
            if len(min60) < 20:
                return 50.0, "60분봉 데이터 부족 (20봉 필요)"

        closes = [d.get("close", 0) for d in min60 if d.get("close", 0) > 0]

        # ── 이동평균 계산 ──
        ma5 = sum(closes[:5]) / 5 if len(closes) >= 5 else 0
        ma20 = sum(closes[:20]) / 20 if len(closes) >= 20 else 0
        ma50 = sum(closes[:50]) / 50 if len(closes) >= 50 else 0

        mas = {}
        if ma5 > 0:
            mas["5봉"] = ma5
        if ma20 > 0:
            mas["20봉"] = ma20
        if ma50 > 0:
            mas["50봉"] = ma50

        if len(mas) < 2:
            return 50.0, "60분봉 이평선 부족"

        # ── 이격도 계산 ──
        ma_values = list(mas.values())
        ma_mid = sum(ma_values) / len(ma_values)
        spread = (max(ma_values) - min(ma_values)) / ma_mid * 100

        # 이격 낮을수록 고점수 (60분봉은 12%에서 바닥)
        pts = max(10.0, 95.0 - spread * 7.0)

        ma_strs = [f"{k}:{int(v):,}" for k, v in mas.items()]
        detail = f"60분 이격도 {spread:.1f}% [{', '.join(ma_strs)}]"

        return pts, detail
