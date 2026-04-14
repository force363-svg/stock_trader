"""
주봉 기준 거래량 변동율 분석

일봉 데이터를 주 단위로 묶어서 주간 거래량 비교
- 이번 주 vs 지난 주 거래량 변동율
- 이번 주 vs 4주 평균 거래량 비교
- 주간 거래량 추세 (증가/감소/횡보)

점수 기준:
- 이번 주 거래량이 4주 평균 2배 이상 + 증가 추세 → 고점수 (관심 급증)
- 이번 주 거래량이 4주 평균 이하 + 감소 추세 → 저점수 (관심 이탈)
"""
from .base import BaseCondition


def _group_by_week(daily: list) -> list:
    """
    일봉 데이터를 주 단위로 묶기 (최신순 입력)
    반환: [{"week_vol": 합계, "days": 일수, "avg_close": 평균종가}, ...] 최신 주부터
    """
    if not daily:
        return []

    weeks = []
    current_week = {"vol": 0, "days": 0, "closes": []}
    prev_weekday = None

    for d in daily:
        date_str = d.get("date", "")
        volume = d.get("volume", 0)
        close = d.get("close", 0)

        # 요일 판단 (날짜 파싱)
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str, "%Y%m%d")
            weekday = dt.weekday()  # 0=월 ~ 4=금
        except Exception:
            weekday = 0

        # 새로운 주 시작 감지: 현재 요일이 이전보다 크면 같은 주
        # (최신순이므로 금→목→수... 순서, 갑자기 커지면 새 주)
        if prev_weekday is not None and weekday < prev_weekday:
            # 같은 주 계속
            pass
        elif prev_weekday is not None and current_week["days"] > 0:
            # 새 주 시작 → 이전 주 저장
            weeks.append({
                "week_vol": current_week["vol"],
                "days": current_week["days"],
                "avg_close": sum(current_week["closes"]) / len(current_week["closes"]) if current_week["closes"] else 0,
            })
            current_week = {"vol": 0, "days": 0, "closes": []}

        current_week["vol"] += volume
        current_week["days"] += 1
        current_week["closes"].append(close)
        prev_weekday = weekday

    # 마지막 주
    if current_week["days"] > 0:
        weeks.append({
            "week_vol": current_week["vol"],
            "days": current_week["days"],
            "avg_close": sum(current_week["closes"]) / len(current_week["closes"]) if current_week["closes"] else 0,
        })

    return weeks


class WeeklyVolumeCondition(BaseCondition):
    """주봉 기준 거래량 변동율 분석"""
    name = "주봉_거래량변동"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])

        if len(daily) < 10:
            return 50.0, "주봉 데이터 부족"

        weeks = _group_by_week(daily)

        if len(weeks) < 2:
            return 50.0, "주간 데이터 부족 (최소 2주 필요)"

        # ── 이번 주 / 지난 주 거래량 ──
        this_week = weeks[0]
        last_week = weeks[1]

        # 일수 보정 (이번 주가 아직 안 끝났으면 일평균으로 비교)
        this_daily_avg = this_week["week_vol"] / this_week["days"] if this_week["days"] > 0 else 0
        last_daily_avg = last_week["week_vol"] / last_week["days"] if last_week["days"] > 0 else 0

        # ── 4주 평균 (일평균 기준) ──
        avg_4w_daily = 0
        if len(weeks) >= 5:
            # 이번 주 제외, 지난 4주
            total_vol = sum(w["week_vol"] for w in weeks[1:5])
            total_days = sum(w["days"] for w in weeks[1:5])
            avg_4w_daily = total_vol / total_days if total_days > 0 else 0
        elif len(weeks) >= 2:
            total_vol = sum(w["week_vol"] for w in weeks[1:])
            total_days = sum(w["days"] for w in weeks[1:])
            avg_4w_daily = total_vol / total_days if total_days > 0 else 0

        if avg_4w_daily <= 0:
            return 50.0, "비교 거래량 데이터 부족"

        # ── 점수 계산 ──
        pts = 50.0
        details = []

        # 1) 이번 주 vs 지난 주 변동율
        if last_daily_avg > 0:
            week_change = ((this_daily_avg - last_daily_avg) / last_daily_avg) * 100
            if week_change >= 100:
                pts += 20
                details.append(f"전주대비 +{week_change:.0f}%")
            elif week_change >= 50:
                pts += 15
                details.append(f"전주대비 +{week_change:.0f}%")
            elif week_change >= 20:
                pts += 10
                details.append(f"전주대비 +{week_change:.0f}%")
            elif week_change >= 0:
                details.append(f"전주대비 +{week_change:.0f}%")
            elif week_change >= -30:
                pts -= 5
                details.append(f"전주대비 {week_change:.0f}%")
            else:
                pts -= 15
                details.append(f"전주대비 {week_change:.0f}%(급감)")
        else:
            week_change = 0

        # 2) 이번 주 vs 4주 평균
        ratio_4w = this_daily_avg / avg_4w_daily if avg_4w_daily > 0 else 1.0
        if ratio_4w >= 3.0:
            pts += 20
            details.append(f"4주평균 {ratio_4w:.1f}배(급증)")
        elif ratio_4w >= 2.0:
            pts += 15
            details.append(f"4주평균 {ratio_4w:.1f}배(증가)")
        elif ratio_4w >= 1.3:
            pts += 10
            details.append(f"4주평균 {ratio_4w:.1f}배")
        elif ratio_4w >= 1.0:
            details.append(f"4주평균 {ratio_4w:.1f}배(보통)")
        elif ratio_4w >= 0.5:
            pts -= 10
            details.append(f"4주평균 {ratio_4w:.1f}배(감소)")
        else:
            pts -= 15
            details.append(f"4주평균 {ratio_4w:.1f}배(급감)")

        # 3) 주간 추세 (최근 3주 연속 증가/감소)
        if len(weeks) >= 4:
            w1_avg = weeks[0]["week_vol"] / max(1, weeks[0]["days"])
            w2_avg = weeks[1]["week_vol"] / max(1, weeks[1]["days"])
            w3_avg = weeks[2]["week_vol"] / max(1, weeks[2]["days"])

            if w1_avg > w2_avg > w3_avg:
                pts += 10
                details.append("3주 연속 증가")
            elif w1_avg < w2_avg < w3_avg:
                pts -= 10
                details.append("3주 연속 감소")

        pts = max(0, min(100, pts))
        detail_str = ", ".join(details) if details else "보통"

        return float(pts), (
            f"주간거래량 일평균 {this_daily_avg:,.0f}주 "
            f"(전주 {last_daily_avg:,.0f}, 4주평균 {avg_4w_daily:,.0f}) | "
            f"{detail_str}"
        )
