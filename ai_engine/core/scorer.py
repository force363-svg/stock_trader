"""
다중 조건 점수 합산
수급 30% + 차트 30% + 재료 40%
engine_config.json의 scoring 섹션 기준으로 동적 계산
"""
import json
import os
import sys

from ..conditions.ma_alignment    import MAAlignmentCondition
from ..conditions.trade_strength  import TradeStrengthCondition
from ..conditions.supply_continuity import SupplyContinuityCondition
from ..conditions.macd            import MACDCondition
from ..conditions.rsi             import RSICondition
from ..conditions.bollinger       import BollingerCondition
from ..conditions.volume_surge    import VolumeSurgeCondition


# 조건명 → 계산기 매핑
CONDITION_MAP = {
    "수급_연속성"     : SupplyContinuityCondition(),
    "당일_체결강도"   : TradeStrengthCondition(),
    "이평선_배열상태" : MAAlignmentCondition(),
    "MACD_상승"       : MACDCondition(),
    "RSI"             : RSICondition(),
    "볼린저밴드"      : BollingerCondition(),
    "거래량_급증"     : VolumeSurgeCondition(),
    "거래대금"        : VolumeSurgeCondition(),   # 재사용
    "분봉배열"        : MAAlignmentCondition(),   # 60분봉 정배열
    "일봉배열"        : MAAlignmentCondition(),   # 일봉 정배열
    "체결강도_120"    : TradeStrengthCondition(),
}


def _get_config_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "engine_config.json")


def load_scoring_config() -> list:
    """engine_config.json에서 scoring 섹션 로드"""
    try:
        with open(_get_config_path(), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return [c for c in cfg.get("scoring", []) if c.get("enabled", True)]
    except Exception as e:
        print(f"[스코어러] config 로드 실패: {e}")
        return []


def calculate_score(code: str, data: dict) -> dict:
    """
    종목 점수 계산
    반환:
    {
        "total_score": float,
        "supply_score": float,
        "chart_score": float,
        "material_score": float,
        "conditions": {조건명: {"score": float, "detail": str, "weight": int}}
    }
    """
    scoring_cfg = load_scoring_config()
    if not scoring_cfg:
        return {"total_score": 0, "conditions": {}}

    total_weight = sum(c.get("weight", 10) for c in scoring_cfg)
    if total_weight == 0:
        return {"total_score": 0, "conditions": {}}

    cond_results = {}
    weighted_sum = 0.0

    for cfg in scoring_cfg:
        name   = cfg["name"]
        weight = cfg.get("weight", 10)
        calc   = CONDITION_MAP.get(name)

        if calc:
            try:
                s, detail = calc.score(code, data)
            except Exception as e:
                s, detail = 0.0, f"오류: {e}"
        else:
            # 계산기 없는 조건은 engine_config에만 정의된 텍스트 조건
            s, detail = 50.0, "수동 조건 (계산기 미구현)"

        cond_results[name] = {"score": s, "detail": detail, "weight": weight}
        weighted_sum += s * weight

    total_score = weighted_sum / total_weight

    # 그룹별 점수 (설계서 기준: 수급30+차트30+재료40)
    supply_names   = ["수급_연속성", "외인_기관_합산평단", "프로그램_순유입", "실시간수급", "프로그램_속도"]
    chart_names    = ["이평선_배열상태", "MACD_상승", "RSI", "볼린저밴드", "분봉배열", "일봉배열", "거래량_급증"]
    material_names = ["거래대금", "지수_대비_강도(RS)", "섹터_자금유입", "뉴스_신선도", "재료_확장성", "목표가_괴리율"]

    def group_avg(names):
        scores = [cond_results[n]["score"] for n in names if n in cond_results]
        return sum(scores) / len(scores) if scores else 0.0

    return {
        "total_score"    : round(total_score, 1),
        "supply_score"   : round(group_avg(supply_names), 1),
        "chart_score"    : round(group_avg(chart_names), 1),
        "material_score" : round(group_avg(material_names), 1),
        "conditions"     : cond_results,
    }
