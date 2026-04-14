"""
스코어러 — 핵심조건 합산 + 고려사항 가점 방식

1단계: scoring_core (핵심 조건) — 각 조건 계산 → 충족 시 해당 점수 합산 → 기본점수
2단계: scoring_bonus (고려사항) — 각 조건 계산 → 충족 시 해당 점수 가점
최종점수 = 기본점수 + 가점

매도 고려사항: 기존 가중평균 방식 유지 (0~100)
"""
import json
import os
import re
import sys
from datetime import datetime

from ..conditions.trade_strength    import TradeStrengthCondition
from ..conditions.supply_continuity import SupplyContinuityCondition
from ..conditions.big_player        import BigPlayerCondition, ProgramTradeCondition, AccumulationCondition
from ..conditions.turnover          import TurnoverCondition, MinuteTurnoverCondition, Min15TurnoverCondition, MinuteVolChangeCondition, DailyVolChangeCondition, VolumeRateDisparityCondition
from ..conditions.macd              import MACDCondition, Min60MACDSellCondition
from ..conditions.rsi               import RSICondition, Min60RSISellCondition
from ..conditions.bollinger         import BollingerCondition, Min60BollingerSellCondition
from ..conditions.ma_alignment      import MAAlignmentCondition, MASupportCondition
from ..conditions.box_range         import BoxRangeCondition
from ..conditions.volume_surge      import VolumeSurgeCondition
from ..conditions.weekly_volume     import WeeklyVolumeCondition
from ..conditions.theme_sector      import ThemeCondition, SectorCondition
from ..conditions.news              import NewsCondition
from ..conditions.price_change      import (PriceChangeCondition, DayChangeCondition,
                                            OpenChangeCondition, MarketIndexCondition,
                                            MinuteChangeCondition, Min15ChangeCondition)
from ..conditions.pattern           import PullbackCondition, ShortPullbackCondition, SqueezeCondition, MADisparityCondition, ShortDisparityCondition, Min60DisparityCondition, DailyHighBreakCondition
from ..learning.ai_predictor        import get_predictor


# ═══════════════════════════════════════════════════════
#  카테고리별 계산기 레지스트리
# ═══════════════════════════════════════════════════════

_CALCULATOR_REGISTRY = [
    {
        "keywords": ["60분봉 유동주식", "60분 유동주식", "60분봉 턴오버", "60분 턴오버", "60분봉 거래비중", "60분 거래비중"],
        "calc": MinuteTurnoverCondition(),
        "category": "supply",
    },
    {
        "keywords": ["60분봉 1봉전", "60분 1봉전", "60분봉 등락율", "60분 등락율"],
        "calc": MinuteChangeCondition(),
        "category": "chart",
    },
    {
        "keywords": ["15분봉 유동주식", "15분 유동주식", "15분봉 턴오버", "15분 턴오버", "15분봉 거래비중", "15분 거래비중"],
        "calc": Min15TurnoverCondition(),
        "category": "supply",
    },
    {
        "keywords": ["15분봉 1봉전", "15분 1봉전", "15분봉 등락율", "15분 등락율"],
        "calc": Min15ChangeCondition(),
        "category": "chart",
    },
    {
        "keywords": ["체결강도", "매수세", "매도세", "체결"],
        "calc": TradeStrengthCondition(),
        "category": "supply",
    },
    {
        "keywords": ["수급", "외국인", "외인", "기관", "순매수"],
        "calc": SupplyContinuityCondition(),
        "category": "supply",
    },
    {
        "keywords": ["큰손", "세력", "투자주체", "기금", "연기금"],
        "calc": BigPlayerCondition(),
        "category": "supply",
    },
    {
        "keywords": ["프로그램"],
        "calc": ProgramTradeCondition(),
        "category": "supply",
    },
    {
        "keywords": ["턴오버", "유동주식", "회전율"],
        "calc": TurnoverCondition(),
        "category": "supply",
    },
    {
        "keywords": ["60분봉 MACD 매도", "60분MACD매도", "60분 MACD 매도"],
        "calc": Min60MACDSellCondition(),
        "category": "chart",
    },
    {
        "keywords": ["60분봉 RSI 매도", "60분RSI매도", "60분 RSI 매도"],
        "calc": Min60RSISellCondition(),
        "category": "chart",
    },
    {
        "keywords": ["60분봉 볼린저 매도", "60분볼린저매도", "60분 볼린저 매도"],
        "calc": Min60BollingerSellCondition(),
        "category": "chart",
    },
    {
        "keywords": ["MACD", "macd"],
        "calc": MACDCondition(),
        "category": "chart",
    },
    {
        "keywords": ["RSI", "rsi"],
        "calc": RSICondition(),
        "category": "chart",
    },
    {
        "keywords": ["볼린저", "bollinger"],
        "calc": BollingerCondition(),
        "category": "chart",
    },
    {
        "keywords": ["이평선", "정배열", "역배열", "일봉", "분봉"],
        "calc": MAAlignmentCondition(),
        "category": "chart",
    },
    {
        "keywords": ["지지", "이탈", "5일선", "20일선", "60일선", "120일선"],
        "calc": MASupportCondition(),
        "category": "chart",
    },
    {
        "keywords": ["박스권", "박스", "지지선", "저항선", "돌파", "신고가", "신저가"],
        "calc": BoxRangeCondition(),
        "category": "chart",
    },
    {
        "keywords": ["거래량", "거래대금"],
        "calc": VolumeSurgeCondition(),
        "category": "material",
    },
    {
        "keywords": ["주봉거래량", "주봉거래", "주간거래량", "주간거래"],
        "calc": WeeklyVolumeCondition(),
        "category": "material",
    },
    {
        "keywords": ["테마", "상승테마"],
        "calc": ThemeCondition(),
        "category": "market",
    },
    {
        "keywords": ["업종", "섹터", "업종지수"],
        "calc": SectorCondition(),
        "category": "market",
    },
    {
        "keywords": ["뉴스", "기사", "재료"],
        "calc": NewsCondition(),
        "category": "market",
    },
    {
        "keywords": ["전일대비"],
        "calc": DayChangeCondition(),
        "category": "chart",
    },
    {
        "keywords": ["시가대비"],
        "calc": OpenChangeCondition(),
        "category": "chart",
    },
    {
        "keywords": ["등락"],
        "calc": PriceChangeCondition(),
        "category": "chart",
    },
    {
        "keywords": ["코스피", "코스닥", "시장 지수", "시장지수"],
        "calc": MarketIndexCondition(),
        "category": "market",
    },
    {
        "keywords": ["단기눌림목", "단기 눌림목"],
        "calc": ShortPullbackCondition(),
        "category": "chart",
    },
    {
        "keywords": ["눌림목"],
        "calc": PullbackCondition(),
        "category": "chart",
    },
    {
        "keywords": ["스퀴즈", "squeeze", "압축", "이평선밀집"],
        "calc": SqueezeCondition(),
        "category": "chart",
    },
    {
        "keywords": ["60분봉 이격도", "60분 이격도", "60분봉이격도"],
        "calc": Min60DisparityCondition(),
        "category": "chart",
    },
    {
        "keywords": ["단기이격도", "단기 이격도", "MA5/20 이격도", "5일20일이격"],
        "calc": ShortDisparityCondition(),
        "category": "chart",
    },
    {
        "keywords": ["이격도", "이격", "이평선간", "MA간격"],
        "calc": MADisparityCondition(),
        "category": "chart",
    },
    {
        "keywords": ["매집", "누적매수", "비중증가", "매집동향"],
        "calc": AccumulationCondition(),
        "category": "supply",
    },
    {
        "keywords": ["60분봉 거래량변동", "60분 거래량변동"],
        "calc": MinuteVolChangeCondition(),
        "category": "supply",
    },
    {
        "keywords": ["일봉 거래량변동", "일봉거래량변동", "거래량변동율", "2봉평균"],
        "calc": DailyVolChangeCondition(),
        "category": "supply",
    },
    {
        "keywords": ["60봉최고종가", "60봉돌파", "60봉 최고종가", "일봉60봉", "최고종가"],
        "calc": DailyHighBreakCondition(),
        "category": "chart",
    },
    {
        "keywords": ["등락대비", "괴리", "등락대비거래량", "등락대비 거래량"],
        "calc": VolumeRateDisparityCondition(),
        "category": "supply",
    },
]


def _get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_scoring_config(section: str = "scoring_core") -> list:
    """engine_config에서 지정 섹션 로드. scoring_core는 전부, 나머지는 enabled만"""
    try:
        from ..conditions._config_helper import get_engine_config_path
        path = get_engine_config_path()
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # 하위호환: 기존 "scoring" 섹션도 지원
        items = cfg.get(section, [])
        if not items and section == "scoring_core":
            items = cfg.get("scoring", [])
        # 핵심조건은 전부 로드 (번호 기반 전략식 사용), 나머지는 enabled만
        if section == "scoring_core":
            return items
        return [c for c in items if c.get("enabled")]
    except Exception:
        return []


def _load_scoring_formula() -> str:
    """engine_config에서 scoring_formula 로드"""
    try:
        from ..conditions._config_helper import get_engine_config_path
        path = get_engine_config_path()
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        formula = cfg.get("scoring_formula", "")
        # 하위호환: scoring_combos → 전략식 자동 변환
        if not formula and cfg.get("scoring_combos"):
            parts = []
            for combo in cfg["scoring_combos"]:
                if combo.get("enabled", True):
                    nums = " and ".join(str(c) for c in combo.get("conditions", []))
                    parts.append(f"({nums})")
            formula = " or ".join(parts)
        return formula
    except Exception:
        return ""


def _evaluate_formula(formula: str, fulfilled_set: set) -> bool:
    """
    전략식 평가: and/or/괄호 지원
    예: (3 and 4 and 5) or (4 and 5 and 8)
    예: 1and2and3 (스페이스 없어도 OK)
    숫자 → fulfilled_set에 있으면 True, 없으면 False
    """
    if not formula or not formula.strip():
        return True  # 전략식 없으면 무조건 통과

    import re as _re
    # 1. and/or 앞뒤에 스페이스 보장 (1and2 → 1 and 2)
    expr = _re.sub(r'(and|or)', r' \1 ', formula)
    # 2. 숫자를 True/False로 치환
    def _replace_num(m):
        num = int(m.group())
        return "True" if num in fulfilled_set else "False"
    expr = _re.sub(r'\b(\d+)\b', _replace_num, expr)
    # 3. 안전 검증: True/False/and/or/괄호/공백만 허용
    check = _re.sub(r'(True|False|and|or|[() ])', '', expr)
    if check.strip():
        return False  # 허용되지 않은 문자 포함

    try:
        return bool(eval(expr, {"__builtins__": {}}, {}))
    except Exception:
        return False


# ═══════════════════════════════════════════════════════
#  키워드 → 계산기 매칭
# ═══════════════════════════════════════════════════════

def _find_calculator(text: str):
    """텍스트에서 키워드 검색 → (calculator, category) 반환"""
    for entry in _CALCULATOR_REGISTRY:
        for kw in entry["keywords"]:
            if kw in text:
                return entry["calc"], entry["category"]
    return None, None


def _extract_threshold(text: str) -> tuple:
    """텍스트에서 임계값 + 연산자 추출."""
    for num_str, unit, op_str in reversed(re.findall(
            r'(\d+(?:\.\d+)?)\s*(%|일|봉|점)?\s*(이상|이하|초과|미만)', text)):
        threshold = float(num_str)
        op_map = {"이상": ">=", "이하": "<=", "초과": ">", "미만": "<"}
        return threshold, op_map.get(op_str, ">=")
    return None, ">="


def _extract_actual_value(detail: str) -> float:
    """계산기 detail 문자열에서 수치 추출"""
    if any(kw in detail for kw in ["없음", "부족", "실패"]):
        return 0.0
    numbers = re.findall(r'(\d+(?:\.\d+)?)', detail)
    if not numbers:
        return 0.0
    if len(numbers) >= 2 and ("중" in detail or "연속" in detail):
        return float(numbers[1])
    return float(numbers[-1])


def _run_calculator(calc, code: str, data: dict, name: str, desc: str,
                    invert: bool = False) -> tuple:
    """
    계산기 실행 → (score 0~100, detail)
    invert=True: 매도 관점
    """
    full_text = f"{name} {desc}"

    try:
        raw_score, detail = calc.score(code, data)
    except Exception as e:
        return 50.0, f"계산 오류: {e}"

    if any(kw in detail for kw in ["없음", "부족", "실패"]):
        return 50.0, detail

    # 매도 관점: 점수 반전
    if invert:
        if raw_score >= 60:
            score = max(0, 10.0 - (raw_score - 60) * 0.25)
        elif raw_score >= 30:
            score = 30.0 - (raw_score - 30) * (20.0 / 30)
        elif raw_score >= 10:
            score = 55.0 - (raw_score - 10) * (25.0 / 20)
        else:
            score = 80.0 - raw_score * 2.5
        return max(0, min(100, score)), f"{detail} (원:{raw_score:.0f}→매도:{score:.0f})"

    # 매수 관점: 임계값 비교 (이격도 등 비례 점수 계산기는 제외)
    skip_threshold = any(kw in name for kw in ["이격도", "단기이격", "이격"])
    threshold, operator = _extract_threshold(full_text)
    if threshold is not None and not skip_threshold:
        actual = _extract_actual_value(detail)
        ops = {">=": lambda a, b: a >= b, ">": lambda a, b: a > b,
               "<=": lambda a, b: a <= b, "<": lambda a, b: a < b}
        passed = ops.get(operator, ops[">="])(actual, threshold)
        score = max(raw_score, 70.0) if passed else min(raw_score, 30.0)
        op_str = {">=": "이상", ">": "초과", "<=": "이하", "<": "미만"}.get(operator, "")
        tag = "✓" if passed else "✗"
        return max(0, min(100, score)), f"{detail} → {actual:.1f} {tag}(기준:{threshold:.0f}{op_str})"

    return max(0, min(100, raw_score)), detail


# 충족 기준: 계산기 점수가 이 값 이상이면 "충족"
FULFILL_THRESHOLD = 60.0


# ═══════════════════════════════════════════════════════
#  매수 점수 계산 (핵심조건 합산 + 고려사항 가점)
# ═══════════════════════════════════════════════════════

def calculate_score(code: str, data: dict) -> dict:
    """
    매수 점수 계산 — 합산 방식.

    1단계: scoring_core (핵심 조건)
      - 각 조건의 계산기 실행 → 점수 60 이상이면 "충족"
      - 충족된 조건의 config weight 합산 → 기본점수

    2단계: scoring_bonus (고려사항)
      - 각 조건의 계산기 실행 → 점수 60 이상이면 "충족"
      - 충족된 조건의 config weight 합산 → 가점

    최종 = 기본점수 + 가점
    """
    core_cfg = load_scoring_config("scoring_core")
    bonus_cfg = load_scoring_config("scoring_bonus")

    if not core_cfg and not bonus_cfg:
        return {
            "total_score": 0, "user_score": 0,
            "core_score": 0, "bonus_score": 0,
            "conditions": {},
            "supply_score": 0, "chart_score": 0, "material_score": 0,
            "primary_passed": False
        }

    conditions = {}
    cat_scores = {"supply": [], "chart": [], "material": [], "market": []}

    # ── 1단계: 핵심 조건 (개별 평가 + 조합 매칭) ──
    core_fulfilled_set = set()  # 충족된 조건 번호 (1-based)

    for idx, cfg in enumerate(core_cfg, 1):
        name = cfg["name"]
        desc = cfg.get("description", "")
        config_score = cfg.get("weight", 10)

        calc, category = _find_calculator(name)
        if not calc:
            calc, category = _find_calculator(desc)

        if calc:
            # 핵심조건: 계산기 점수 직접 사용 (임계값 덮어쓰기 없음)
            try:
                raw, detail = calc.score(code, data)
                raw = max(0, min(100, raw))
            except Exception as e:
                raw, detail = 50.0, f"계산 오류: {e}"
        else:
            raw, detail = 50.0, f"키워드 미인식: {name}"
            category = None

        fulfilled = raw >= FULFILL_THRESHOLD

        if fulfilled:
            core_fulfilled_set.add(idx)
            tag = f"✓ 충족(#{idx})"
        else:
            tag = f"✗ 미충족({raw:.0f}점)"

        conditions[name] = {
            "score": raw, "detail": f"{detail} {tag}",
            "weight": config_score, "role": "core",
            "fulfilled": fulfilled, "earned": 0
        }

        if category and category in cat_scores:
            cat_scores[category].append(raw)

    # 전략식 평가: 통과 시 전략식에 포함된 충족 조건만 weight 합산
    formula = _load_scoring_formula()
    formula_passed = _evaluate_formula(formula, core_fulfilled_set)
    core_total = 0.0

    # 전략식에서 참조된 조건 번호 추출
    formula_nums = set()
    if formula.strip():
        import re as _re2
        # and/or 앞뒤 스페이스 보장 후 숫자 추출
        _spaced = _re2.sub(r'(and|or)', r' \1 ', formula)
        formula_nums = set(int(n) for n in _re2.findall(r'\b(\d+)\b', _spaced))

    # 디버그 로그
    try:
        import os as _os2
        _dbg = _os2.path.join(_os2.path.dirname(_os2.path.dirname(_os2.path.dirname(_os2.path.abspath(__file__)))), "debug_scorer.txt")
        if getattr(sys, 'frozen', False):
            _dbg = _os2.path.join(_os2.path.dirname(_os2.path.dirname(sys.executable)), "debug_scorer.txt")
        with open(_dbg, "a", encoding="utf-8") as _df:
            _df.write(f"[{code}] formula='{formula}' nums={formula_nums} fulfilled={core_fulfilled_set} passed={formula_passed}\n")
            for idx, cfg in enumerate(core_cfg, 1):
                _df.write(f"  #{idx} {cfg['name']} w={cfg.get('weight',10)} in_formula={idx in formula_nums} fulfilled={idx in core_fulfilled_set}\n")
    except Exception:
        pass

    if formula_passed and core_fulfilled_set:
        for idx, cfg in enumerate(core_cfg, 1):
            if idx in core_fulfilled_set and (idx in formula_nums or not formula_nums):
                w = cfg.get("weight", 10)
                raw = conditions[cfg["name"]]["score"]
                earned = round(w * (raw / 100.0), 1)
                core_total += earned
                conditions[cfg["name"]]["earned"] = earned
        formula_tag = f"전략식 통과 → {core_total:.0f}점"
    elif not formula.strip():
        # 전략식 미설정 → 전체 충족 조건 합산
        for idx, cfg in enumerate(core_cfg, 1):
            if idx in core_fulfilled_set:
                w = cfg.get("weight", 10)
                raw = conditions[cfg["name"]]["score"]
                earned = round(w * (raw / 100.0), 1)
                core_total += earned
                conditions[cfg["name"]]["earned"] = earned
        formula_tag = f"전략식 없음 → {core_total:.0f}점"
    else:
        formula_tag = "전략식 미통과 → 0점"

    # 전략식 결과 기록
    for name in conditions:
        if conditions[name]["role"] == "core" and conditions[name]["fulfilled"]:
            conditions[name]["detail"] += f" [{formula_tag}]"

    # ── 2단계: 고려사항 가점 (전략식 통과 시에만) ──
    bonus_total = 0.0

    # 전략식 미통과 → bonus 평가 스킵, 최종 0점
    if not formula_passed and formula.strip():
        for cfg in bonus_cfg:
            name = cfg["name"]
            conditions[name] = {
                "score": 0, "detail": "전략식 미통과 → 미평가",
                "weight": cfg.get("weight", 10), "role": "bonus",
                "fulfilled": False, "earned": 0
            }
        return {
            "total_score": 0, "user_score": 0,
            "core_score": 0, "bonus_score": 0,
            "supply_score": 0, "chart_score": 0, "material_score": 0,
            "primary_passed": False,
            "conditions": conditions,
        }

    for cfg in bonus_cfg:
        name = cfg["name"]
        desc = cfg.get("description", "")
        config_score = cfg.get("weight", 10)

        # 과거 유사패턴 → AI 예측기
        if any(kw in name for kw in ["과거", "유사패턴", "패턴", "AI예측", "학습"]):
            try:
                predictor = get_predictor()
                pred = predictor.predict(conditions)
                ai_score = pred["ai_score"]
                wp = pred["win_probability"]
                conf = pred["confidence"]
                reasons = pred.get("reasons", [])
                reason_str = ", ".join(reasons[:2]) if reasons else "데이터 부족"
                raw = ai_score
                detail = f"승률:{wp:.0%} 신뢰:{conf} ({reason_str})"
                category = "market"
            except Exception as e:
                raw, detail = 50.0, f"AI예측 미작동: {e}"
                category = None
        else:
            calc, category = _find_calculator(name)
            if not calc:
                calc, category = _find_calculator(desc)

            if calc:
                raw, detail = _run_calculator(calc, code, data, name, desc, invert=False)
            else:
                raw, detail = 50.0, f"키워드 미인식: {name}"
                category = None

        fulfilled = raw >= FULFILL_THRESHOLD
        earned = round(config_score * (raw / 100.0), 1)
        bonus_total += earned

        if fulfilled:
            tag = f"✓ +{earned}점"
        else:
            tag = f"△ {earned}점(raw:{raw:.0f})"

        conditions[name] = {
            "score": raw, "detail": f"{detail} {tag}",
            "weight": config_score, "role": "bonus",
            "fulfilled": fulfilled, "earned": earned
        }

        if category and category in cat_scores:
            cat_scores[category].append(raw)

    # 고려사항 디버그 로그
    try:
        import os as _os3
        _dbg2 = _os3.path.join(_os3.path.dirname(_os3.path.dirname(_os3.path.dirname(_os3.path.abspath(__file__)))), "debug_scorer.txt")
        if getattr(sys, 'frozen', False):
            _dbg2 = _os3.path.join(_os3.path.dirname(_os3.path.dirname(sys.executable)), "debug_scorer.txt")
        with open(_dbg2, "a", encoding="utf-8") as _df2:
            _df2.write(f"  [고려사항] core={core_total:.1f} bonus={bonus_total:.1f} total={core_total+bonus_total:.1f}\n")
            for cfg in bonus_cfg:
                n = cfg["name"]
                if n in conditions:
                    c = conditions[n]
                    _df2.write(f"    {n}: raw={c['score']:.0f} earned={c.get('earned',0)} fulfilled={c['fulfilled']} w={c['weight']}\n")
    except Exception:
        pass

    # ── 최종 점수 ──
    user_score = core_total + bonus_total
    total_score = user_score

    def _avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    return {
        "total_score":    round(total_score, 1),
        "user_score":     round(user_score, 1),
        "core_score":     round(core_total, 1),
        "bonus_score":    round(bonus_total, 1),
        "supply_score":   round(_avg(cat_scores["supply"]), 1),
        "chart_score":    round(_avg(cat_scores["chart"]), 1),
        "material_score": round(_avg(cat_scores["material"]), 1),
        "primary_passed": len(core_fulfilled_set) > 0,
        "conditions":     conditions,
    }


# ═══════════════════════════════════════════════════════
#  매도 고려사항 점수 계산 (기존 가중평균 유지)
# ═══════════════════════════════════════════════════════

def calculate_sell_score(code: str, data: dict, hold_info: dict = None,
                         market_status: dict = None) -> dict:
    """
    매도 점수 — 비례 합산 방식.
    각 조건: earned = weight × (raw / 100)
    겹칠수록 점수 높아짐 → 매도 확신 ↑
    """
    scoring_cfg = load_scoring_config("sell_scoring")
    if not scoring_cfg:
        return {"total_score": 0.0, "conditions": {}}

    hold_info = hold_info or {}
    market_status = market_status or {}
    cond_results = {}
    sell_total = 0.0

    for cfg in scoring_cfg:
        name = cfg["name"]
        desc = cfg.get("description", "")
        weight = cfg.get("weight", 10)

        # 특수 조건 우선 처리
        if any(kw in name for kw in ["윗꼬리", "상꼬리", "upper"]):
            raw, detail = _calc_upper_tail(code, data, hold_info)
        elif any(kw in name for kw in ["손익", "수익률", "수익"]):
            raw, detail = _calc_pnl(code, data, hold_info)
        elif any(kw in name for kw in ["시장", "코스피", "코스닥"]) and "업종" not in name:
            raw, detail = _calc_market(market_status)
        elif any(kw in name for kw in ["시간", "장마감", "오후", "마감"]):
            raw, detail = _calc_time()
        elif "거래량" in name and "유동" not in name:
            raw, detail = _calc_volume_decline(code, data)
        elif any(kw in name for kw in ["수급", "세력"]):
            raw, detail = _calc_supply_exit(code, data)
        elif any(kw in name for kw in ["뉴스", "기사"]):
            raw, detail = 15.0, "뉴스 조건 미사용 (등락율로 대체)"
        else:
            calc, _ = _find_calculator(name)
            if not calc:
                calc, _ = _find_calculator(desc)
            if calc:
                # 매도 전용 calculator는 이미 매도 관점이므로 invert 안 함
                is_sell_calc = any(kw in name for kw in ["매도", "MACD 매도", "RSI 매도", "볼린저 매도"])
                raw, detail = _run_calculator(calc, code, data, name, desc, invert=not is_sell_calc)
            else:
                raw, detail = 30.0, f"미인식: {name}"

        raw = max(0, min(100, raw))
        earned = round(weight * (raw / 100.0), 1)
        sell_total += earned

        fulfilled = raw >= FULFILL_THRESHOLD
        if fulfilled:
            tag = f"✓ +{earned}점"
        else:
            tag = f"△ {earned}점(raw:{raw:.0f})"

        cond_results[name] = {
            "score": raw, "detail": f"{detail} {tag}",
            "weight": weight, "earned": earned, "fulfilled": fulfilled
        }

    return {"total_score": round(sell_total, 1), "conditions": cond_results}


# ═══════════════════════════════════════════════════════
#  특수 매도 계산기
# ═══════════════════════════════════════════════════════

def _calc_volume_decline(code: str, data: dict) -> tuple:
    """거래량 감소 + 주가 하락 동반 시에만 매도 신호"""
    daily = data.get("daily", [])
    if len(daily) < 6:
        return 15.0, "일봉 데이터 부족"

    cur_vol = daily[0].get("volume", 0)
    avg_vol = sum(d.get("volume", 0) for d in daily[1:6]) / 5
    if avg_vol <= 0:
        return 15.0, "평균 거래량 없음"

    vol_ratio = cur_vol / avg_vol * 100

    cur_close = daily[0].get("close", 0)
    prev_close = daily[1].get("close", 0)
    price_chg = 0
    if prev_close > 0:
        price_chg = (cur_close - prev_close) / prev_close * 100

    if vol_ratio <= 50 and price_chg < -2:
        score = 80.0
    elif vol_ratio <= 70 and price_chg < -1:
        score = 60.0
    elif vol_ratio <= 70 and price_chg < 0:
        score = 40.0
    elif vol_ratio <= 70:
        score = 15.0
    else:
        score = 10.0

    return score, f"거래량 {vol_ratio:.0f}%(5일비) 등락:{price_chg:+.1f}%"


def _calc_supply_exit(code: str, data: dict) -> tuple:
    """수급/세력 이탈 + 등락율 하락 + 이평선 이탈 동반 시에만 매도 강화"""
    supply = data.get("supply", [])
    daily = data.get("daily", [])

    if not supply or len(daily) < 6:
        return 15.0, "데이터 부족"

    days = supply[:3]
    total_big = 0
    for d in days:
        total_big += d.get("foreign_net", 0) + d.get("inst_net", 0) + d.get("program", 0)

    cur_close = daily[0].get("close", 0)
    prev_close = daily[1].get("close", 0)
    price_chg = 0
    if prev_close > 0:
        price_chg = (cur_close - prev_close) / prev_close * 100

    closes = [d.get("close", 0) for d in daily[:6]]
    ema5_broken = False
    if len(closes) >= 5:
        ema5 = sum(closes[:5]) / 5
        if closes[0] < ema5:
            ema5_broken = True

    details = []
    score = 10.0

    if total_big < 0:
        details.append(f"세력매도({total_big:+,})")
        if price_chg < -1 and ema5_broken:
            score = 80.0
            details.append(f"등락:{price_chg:+.1f}%+5일선이탈")
        elif price_chg < -1:
            score = 55.0
            details.append(f"등락:{price_chg:+.1f}%")
        elif ema5_broken:
            score = 45.0
            details.append("5일선이탈")
        else:
            score = 20.0
            details.append(f"주가유지({price_chg:+.1f}%) 페이크?")
    else:
        details.append(f"세력매수({total_big:+,})")
        score = 10.0

    return score, " | ".join(details)


def _calc_upper_tail(code: str, data: dict, hold_info: dict) -> tuple:
    """60분봉 윗꼬리 감지"""
    min60 = data.get("min60", [])
    if len(min60) < 1:
        return 20.0, "60분봉 데이터 없음"

    cur = min60[0]
    high = cur.get("high", 0)
    low = cur.get("low", 0)
    close = cur.get("close", 0)

    if high <= low or close <= 0:
        return 20.0, "캔들 데이터 부족"

    candle_range = high - low
    position = (close - low) / candle_range

    buy_price = hold_info.get("buy_price", 0) if hold_info else 0
    pnl = 0
    if buy_price > 0:
        try:
            cur_price = float(data.get("price", {}).get("price", close))
            pnl = (cur_price - buy_price) / buy_price * 100
        except Exception:
            pass

    if position < 0.3:
        if pnl >= 10:
            score = 85.0
        elif pnl >= 5:
            score = 70.0
        elif pnl >= 0:
            score = 55.0
        else:
            score = 45.0
        return score, f"윗꼬리감지 위치:{position:.0%} 수익:{pnl:+.1f}%"
    elif position < 0.5:
        if pnl >= 10:
            score = 55.0
        else:
            score = 35.0
        return score, f"약윗꼬리 위치:{position:.0%} 수익:{pnl:+.1f}%"
    else:
        return 15.0, f"윗꼬리없음 위치:{position:.0%}"


def _calc_pnl(code: str, data: dict, hold_info: dict) -> tuple:
    """손익률 기반 매도 점수"""
    buy_price = hold_info.get("buy_price", 0)
    if not buy_price:
        return 30.0, "매수가 없음"

    price_data = data.get("price", {})
    try:
        cur = float(price_data.get("price", price_data.get("close", 0)))
    except Exception:
        return 30.0, "현재가 없음"

    pnl = (cur - buy_price) / buy_price * 100

    if pnl <= -5:
        return min(100, 80 + abs(pnl) * 2), f"손절 ({pnl:+.1f}%)"
    if pnl <= -3:
        return 70.0, f"손절 경계 ({pnl:+.1f}%)"
    if pnl >= 20:
        return 65.0, f"익절 구간 ({pnl:+.1f}%)"
    if pnl >= 10:
        return 50.0, f"부분익절 ({pnl:+.1f}%)"
    if pnl >= 3:
        return 20.0, f"수익 진행 ({pnl:+.1f}%)"
    if pnl >= 0:
        return 25.0, f"소폭 수익 ({pnl:+.1f}%)"
    return 40.0, f"소폭 손실 ({pnl:+.1f}%)"


def _calc_market(market_status: dict) -> tuple:
    """시장 악화도"""
    if not market_status:
        return 30.0, "시장 데이터 없음"

    score = 10.0
    details = []

    kospi = market_status.get("kospi_diff", 0)
    kosdaq = market_status.get("kosdaq_diff", 0)
    avg = (kospi + kosdaq) / 2 if kospi or kosdaq else 0

    if avg < -1.5:
        score += 40
        details.append(f"급락({avg:+.2f}%)")
    elif avg < -0.5:
        score += 25
        details.append(f"하락({avg:+.2f}%)")
    elif avg < 0:
        score += 10
        details.append(f"소폭하락({avg:+.2f}%)")
    else:
        details.append(f"상승({avg:+.2f}%)")

    down_ratio = market_status.get("down_ratio", 0)
    if down_ratio >= 3:
        score += 30
        details.append(f"하락종목 {down_ratio:.1f}배")
    elif down_ratio >= 2:
        score += 15
        details.append(f"하락종목 {down_ratio:.1f}배")

    return min(100, score), ", ".join(details)


def _calc_time() -> tuple:
    """시간 조건 — 중립"""
    return 30.0, "시간 조건 미사용"
