"""
매도 조건 점수 차감 (페널티 시스템)
engine_config.json sell 섹션의 조건명에서 키워드 자동 파싱
조건명/설명을 수정하면 즉시 반영
"""
import json
import os
import re
import sys
from .base import BaseCondition
from ._config_helper import load_defaults


def _load_sell_config() -> list:
    """engine_config sell 섹션 로드 → [{name, description, threshold, enabled}, ...] 반환"""
    try:
        from ._config_helper import get_engine_config_path
        with open(get_engine_config_path(), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return [c for c in cfg.get("sell", []) if c.get("enabled", True)]
    except Exception:
        return []


def _match_keywords(text, *keywords):
    """텍스트에 모든 키워드가 포함되어 있으면 True"""
    return all(kw in text for kw in keywords)


class ScorePenaltyCondition(BaseCondition):
    name = "매도_페널티"

    def score(self, code: str, data: dict) -> tuple:
        """
        보유 종목의 페널티 점수 계산 (키워드 기반 자동 매칭)
        조건명에서 키워드를 인식하여 해당 로직 실행, threshold는 config에서 동적으로 읽음

        data 추가 키:
          "hold_score"    : 매수 당시 점수 (기본 80)
          "market_status" : {"down_ratio": float, "index_new_low": bool, ...}
        반환: (남은 점수, 페널티 상세)
        """
        sell_items     = _load_sell_config()
        hold_score     = data.get("hold_score", 80.0)
        market_status  = data.get("market_status", {})
        daily          = data.get("daily", [])
        supply         = data.get("supply", [])
        price_data     = data.get("price", {})

        penalty = 0.0
        details = []

        # 페널티 점수를 defaults에서 읽기 (사용자가 수정 가능)
        defaults = load_defaults()
        pp = defaults.get("penalty_points", {})
        def _pp(key, fallback):
            return float(pp.get(key, fallback))

        closes = []
        if daily:
            closes = [d["close"] for d in daily]

        for item in sell_items:
            cname = item["name"]
            cdesc = item.get("description", "")
            threshold = item.get("threshold", 0)
            full_text = f"{cname} {cdesc}"

            # ── 하락종목 N배 ──
            if _match_keywords(cname, "하락종목"):
                down_ratio = market_status.get("down_ratio", 0)
                thr = threshold if threshold > 0 else 3
                if down_ratio >= thr:
                    penalty += _pp("하락종목", 20)
                    details.append(f"하락종목 {down_ratio:.1f}배(기준:{thr}배)")

            # ── 지수 저점 갱신 ──
            elif _match_keywords(cname, "지수") and "저점" in cname:
                if market_status.get("index_new_low", False):
                    penalty += _pp("지수저점", 15)
                    details.append("지수 저점 갱신")

            # ── 지수 급락 ──
            elif _match_keywords(cname, "지수") and ("낙하" in cname or "급락" in cname):
                thr = threshold if threshold > 0 else 0.5
                index_drop = market_status.get("index_drop_pct", 0)
                if index_drop >= thr:
                    penalty += _pp("지수급락", 25)
                    details.append(f"지수 급락 {index_drop:.2f}%(기준:{thr}%)")
                elif market_status.get("index_sudden_drop", False):
                    penalty += _pp("지수급락", 25)
                    details.append("지수 급락")

            # ── 전저점/이평선 이탈 ──
            elif "이탈" in cname and ("전저점" in cname or "일선" in cname or "5일" in cname):
                if closes and len(closes) >= 6:
                    from .ma_alignment import _ema
                    ema5 = _ema(closes, 5)
                    if ema5 and closes[0] < ema5[0]:
                        penalty += _pp("이평선이탈", 15)
                        details.append("5일선 이탈")

            # ── 이격도 N% ──
            elif "이격" in cname or "이격도" in full_text:
                thr = threshold if threshold > 0 else 15
                # 이평선 기간 파싱: "20일선 이격도" → 20
                period_m = re.search(r'(\d+)\s*일선?', full_text)
                period = int(period_m.group(1)) if period_m else 20
                if closes and len(closes) >= period + 2:
                    from .ma_alignment import _sma
                    sma_vals = _sma(closes, period)
                    if sma_vals and sma_vals[0] > 0:
                        gap = (closes[0] - sma_vals[0]) / sma_vals[0] * 100
                        if gap >= thr:
                            penalty += _pp("이격도", 10)
                            details.append(f"{period}일선 이격 {gap:.1f}%(기준:{thr}%)")

            # ── 거래량 음봉 ──
            elif "음봉" in cname and "거래량" in full_text:
                if daily:
                    d = daily[0]
                    if d.get("close", 0) < d.get("open", 0) and d.get("volume", 0) > 0:
                        penalty += _pp("거래량음봉", 10)
                        details.append("거래량 음봉")

            # ── 거래량 급감 ──
            elif "거래량" in cname and ("급감" in cname or "이하" in cname):
                thr = threshold if threshold > 0 else 70
                if daily and len(daily) >= 6:
                    avg_vol = sum(d.get("volume", 0) for d in daily[1:6]) / 5
                    cur_vol = daily[0].get("volume", 0)
                    if avg_vol > 0:
                        ratio = cur_vol / avg_vol * 100
                        if ratio <= thr:
                            penalty += _pp("거래량급감", 10)
                            details.append(f"거래량 {ratio:.0f}%(기준:{thr}%이하)")

            # ── 외인/기관 매도 전환 ──
            elif ("외인" in cname or "외국인" in cname) and ("기관" in cname) and ("매도" in cname or "전환" in cname):
                if supply and len(supply) >= 1:
                    today = supply[0]
                    foreign_net = today.get("foreign_net", 0)
                    inst_net = today.get("inst_net", 0)
                    total_net = today.get("total_net", foreign_net + inst_net)
                    if total_net < 0:
                        penalty += _pp("외인기관매도", 15)
                        details.append(f"외인+기관 매도 전환(순매도:{total_net:,})")

            # ── 프로그램 매수 피크 대비 하락 ──
            elif "프로그램" in cname and ("피크" in cname or "하락" in cname):
                thr = threshold if threshold > 0 else 30
                if supply and len(supply) >= 3:
                    pgm_values = [d.get("program", 0) for d in supply[:5]]
                    peak = max(pgm_values) if pgm_values else 0
                    current = pgm_values[0] if pgm_values else 0
                    if peak > 0:
                        drop_pct = (peak - current) / peak * 100
                        if drop_pct >= thr:
                            penalty += _pp("프로그램피크", 15)
                            details.append(f"프로그램매수 피크 대비 -{drop_pct:.0f}%(기준:{thr}%)")

            # ── 테마 대장주 급락 ──
            elif "테마" in cname and ("대장" in cname or "급락" in cname):
                thr = threshold if threshold > 0 else 5
                try:
                    from .theme_sector import _load_cache
                    cache = _load_cache()
                    themes = cache.get("themes", [])
                    # 상위 테마 중 급락한 테마가 있는지 체크
                    for t in themes[:5]:
                        if t.get("diff", 0) <= -thr:
                            penalty += _pp("테마급락", 15)
                            details.append(f"테마 급락: {t['name']} {t['diff']:+.1f}%")
                            break
                except Exception:
                    pass

            # ── 오후 시간 강화 ──
            elif "시" in cname and ("오후" in cname or "이후" in cname or "마감" in cname):
                from datetime import datetime
                now = datetime.now()
                t = now.hour * 60 + now.minute
                # 시간 파싱: "오후 3시" → 15시
                hour_m = re.search(r'(\d+)\s*시', cname)
                target_hour = int(hour_m.group(1)) if hour_m else 15
                if "오후" in cname and target_hour < 12:
                    target_hour += 12
                target_min = target_hour * 60
                thr_pct = threshold if threshold > 0 else _pp("시간강화", 15)
                if t >= target_min:
                    penalty += thr_pct
                    details.append(f"{target_hour}시 이후 매도 강화(+{thr_pct:.0f}%)")

        remaining = max(0.0, hold_score - penalty)
        detail = f"페널티 -{penalty:.0f}점 ({', '.join(details)})" if details else "이상 없음"
        return remaining, detail
