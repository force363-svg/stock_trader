"""
큰손(세력) 수급 분석 조건

투자주체별 세부 분석:
- 프로그램 매매: 기관 알고리즘 매매 동향
- 기금(연기금): 국민연금 등 장기 투자자 동향
- 외국인+기관 동시 매수: 세력 합류 신호
- 개인 vs 기관 역방향: 세력 이탈/진입 판단

점수 기준:
- 큰손(외인+기관+프로그램+기금) 동시 매수 → 고점수
- 개인만 매수, 기관/외인 매도 → 저점수 (개미물량)
- 프로그램 대량 매수 → 기관 매집 신호
"""
from .base import BaseCondition


class BigPlayerCondition(BaseCondition):
    name = "큰손_수급"

    def score(self, code: str, data: dict) -> tuple:
        supply = data.get("supply", [])

        if not supply:
            return 50.0, "수급 데이터 없음"

        days = supply[:5]
        if not days:
            return 50.0, "수급 데이터 부족"

        # ── 최근 5일 투자주체별 누적 ──
        total_foreign = 0
        total_inst = 0
        total_program = 0
        total_fund = 0
        total_personal = 0
        valid_days = 0

        for d in days:
            total_foreign  += d.get("foreign_net", 0)
            total_inst     += d.get("inst_net", 0)
            total_program  += d.get("program", 0)
            total_fund     += d.get("fund", 0)
            total_personal += d.get("personal", 0)
            valid_days += 1

        if valid_days == 0:
            return 50.0, "수급 데이터 부족"

        # ── 세력 점수 계산 ──
        pts = 50.0  # 기본 중립
        details = []

        # 1) 외국인+기관 동시 매수 (가장 강한 신호)
        if total_foreign > 0 and total_inst > 0:
            pts += 20
            details.append("외인+기관 동시매수")
        elif total_foreign > 0 and total_inst < 0:
            pts += 5
            details.append("외인매수/기관매도")
        elif total_foreign < 0 and total_inst > 0:
            pts += 5
            details.append("외인매도/기관매수")
        elif total_foreign < 0 and total_inst < 0:
            pts -= 15
            details.append("외인+기관 동시매도")

        # 2) 프로그램 매매 방향 (기관 알고리즘)
        if total_program > 0:
            pts += 10
            details.append(f"프로그램매수({total_program:+,})")
        elif total_program < 0:
            pts -= 5
            details.append(f"프로그램매도({total_program:+,})")

        # 3) 기금(연기금) — 장기 투자자
        if total_fund > 0:
            pts += 10
            details.append(f"기금매수({total_fund:+,})")

        # 4) 개인 vs 기관 역방향 (세력 이탈 판단)
        big_player_net = total_foreign + total_inst + total_program
        if big_player_net > 0 and total_personal < 0:
            # 큰손 매수 + 개인 매도 → 세력 매집 (긍정적)
            pts += 10
            details.append("세력매집(개인매도)")
        elif big_player_net < 0 and total_personal > 0:
            # 큰손 매도 + 개인 매수 → 개미물량 (위험)
            pts -= 15
            details.append("⚠개미물량(세력이탈)")

        pts = max(0, min(100, pts))
        detail_str = ", ".join(details) if details else "중립"

        return float(pts), f"5일누적 외인:{total_foreign:+,} 기관:{total_inst:+,} 프:{total_program:+,} 기금:{total_fund:+,} | {detail_str}"


class AccumulationCondition(BaseCondition):
    """
    매집 동향 — 10~15일간 큰손 매수비중 증가 추세 감지
    개인과 반대로 움직이면서 전체 매수비중을 높여가는 패턴
    - 큰손(외인+기관+프로그램+기금) 누적이 증가 추세
    - 개인은 반대 (매도) 추세
    - 기간이 길수록 + 비중 높아질수록 고점수
    """
    name = "매집_동향"

    def score(self, code: str, data: dict) -> tuple:
        supply = data.get("supply", [])

        if len(supply) < 10:
            return 50.0, "수급 데이터 부족 (10일 필요)"

        days = supply[:15]  # 최근 15일
        n = len(days)

        # ── 일별 큰손 순매수 / 개인 순매수 계산 ──
        big_daily = []  # 큰손 일별 순매수
        personal_daily = []  # 개인 일별 순매수

        for d in days:
            foreign = d.get("foreign_net", 0)
            inst = d.get("inst_net", 0)
            program = d.get("program", 0)
            fund = d.get("fund", 0)
            personal = d.get("personal", 0)

            big = foreign + inst + program + fund
            big_daily.append(big)
            personal_daily.append(personal)

        # ── 1) 큰손 매수일 비율 ──
        big_buy_days = sum(1 for b in big_daily if b > 0)
        buy_ratio = big_buy_days / n

        # ── 2) 큰손 vs 개인 역방향 일수 ──
        opposite_days = 0
        for i in range(n):
            if big_daily[i] > 0 and personal_daily[i] < 0:
                opposite_days += 1
            elif big_daily[i] < 0 and personal_daily[i] > 0:
                opposite_days += 1
        opposite_ratio = opposite_days / n

        # ── 3) 누적 추세 (전반 5일 vs 후반 5일 비교) ──
        # supply는 최신순이므로 앞=최근, 뒤=과거
        half = n // 2
        recent_sum = sum(big_daily[:half])  # 최근
        older_sum = sum(big_daily[half:])   # 과거
        trend_up = recent_sum > older_sum   # 최근이 더 많으면 비중 증가 추세

        # ── 4) 큰손 총 누적 ──
        total_big = sum(big_daily)
        total_personal = sum(personal_daily)

        # ── 점수 계산 ──
        pts = 30.0  # 기본

        # 매수일 비율 (60% 이상이면 가점)
        if buy_ratio >= 0.7:
            pts += 25
        elif buy_ratio >= 0.5:
            pts += 15
        elif buy_ratio >= 0.3:
            pts += 5

        # 큰손-개인 역방향 (의도적 매집 신호)
        if opposite_ratio >= 0.6:
            pts += 20
        elif opposite_ratio >= 0.4:
            pts += 10

        # 누적 추세 상승
        if trend_up and total_big > 0:
            pts += 15
        elif total_big > 0:
            pts += 5
        elif total_big < 0:
            pts -= 10

        # 개인 매도 확인 (세력 매집 + 개미 털기)
        if total_big > 0 and total_personal < 0:
            pts += 10

        pts = max(0, min(100, pts))

        details = []
        details.append(f"{n}일간 매수{big_buy_days}일({buy_ratio:.0%})")
        details.append(f"역방향{opposite_days}일({opposite_ratio:.0%})")
        if trend_up:
            details.append("비중증가↑")
        else:
            details.append("비중감소↓")
        details.append(f"큰손{total_big:+,}/개인{total_personal:+,}")

        return float(pts), f"매집동향 | {', '.join(details)}"


class ProgramTradeCondition(BaseCondition):
    """프로그램 매매 동향 (기관 알고리즘 매매)"""
    name = "프로그램_매매"

    def score(self, code: str, data: dict) -> tuple:
        supply = data.get("supply", [])
        if not supply:
            return 50.0, "수급 데이터 없음"

        days = supply[:5]
        pgm_buy_days = 0
        total_pgm = 0

        for d in days:
            pgm = d.get("program", 0)
            total_pgm += pgm
            if pgm > 0:
                pgm_buy_days += 1

        total = len(days)
        if total == 0:
            return 50.0, "데이터 부족"

        # 프로그램 매수 일수 비율 + 방향
        ratio = pgm_buy_days / total
        pts = ratio * 60 + 20  # 20~80 범위

        # 연속 대량 매수 보너스
        if pgm_buy_days >= 3:
            pts = min(100, pts + 10)

        # 대량 매도 페널티
        if pgm_buy_days == 0:
            pts = max(0, pts - 10)

        status = "순매수" if total_pgm > 0 else "순매도"
        return float(pts), f"프로그램 {total}일 중 {pgm_buy_days}일 매수 ({status} {total_pgm:+,})"
