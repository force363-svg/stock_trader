"""
조건 파서 — HTS 스타일 자유 텍스트를 AI가 정확히 이해하는 핵심 모듈

스크리닝/고려사항이 하는 말을 AI가 알아듣게 하는 번역기.
"시세 | 0봉전시가 대비 0봉전등락율 2~9%" → type=open_rate, range=(2,9)

파싱 흐름:
  1. 조건 텍스트 (이름 + 설명) 수신
  2. 패턴 매칭으로 조건 타입 식별
  3. 정규식으로 파라미터 추출
  4. 창고(캐시) 데이터에 대해 평가

지원 조건 타입:
  - open_rate     : 시가대비 등락률 범위
  - day_change    : 전일대비 등락률 범위
  - ma_compare    : 이평선 비교 (A > B)
  - ma_rising     : 이평선 상승추세
  - price_vs_ma   : 종가 > 이평선
  - macd_cross    : MACD > Signal
  - macd_rising   : MACD 상승추세
  - volume_surge  : 거래량 급증
  - new_high      : 신고가
"""
import re
from typing import Optional


# ═══════════════════════════════════════════════════════
#  기술 지표 계산 헬퍼 (자체 구현, 외부 의존성 없음)
# ═══════════════════════════════════════════════════════

def _ema(closes: list, period: int) -> list:
    """지수이동평균 (입력: newest-first, 출력: newest-first)"""
    if len(closes) < period:
        return []
    rev = list(reversed(closes))
    mult = 2.0 / (period + 1)
    result = [sum(rev[:period]) / period]
    for price in rev[period:]:
        result.append(price * mult + result[-1] * (1 - mult))
    return list(reversed(result))


def _sma(closes: list, period: int) -> list:
    """단순이동평균 (입력: newest-first, 출력: newest-first)"""
    if len(closes) < period:
        return []
    rev = list(reversed(closes))
    result = []
    for i in range(len(rev) - period + 1):
        result.append(sum(rev[i:i + period]) / period)
    return list(reversed(result))


def _macd(closes: list, fast=10, slow=20, signal_period=9):
    """MACD 계산 → (macd_line, signal_line, histogram) 또는 (None, None, None)"""
    if len(closes) < slow + signal_period:
        return None, None, None
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    n = min(len(ema_fast), len(ema_slow))
    if n == 0:
        return None, None, None
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(n)]
    if len(macd_line) < signal_period:
        return macd_line, None, None
    signal_line = _ema(macd_line, signal_period)
    n2 = min(len(macd_line), len(signal_line))
    histogram = [macd_line[i] - signal_line[i] for i in range(n2)]
    return macd_line, signal_line, histogram


def _rsi(closes: list, period: int = 14) -> float:
    """RSI 계산 → float (실패 시 -1)"""
    if len(closes) < period + 1:
        return -1
    rev = list(reversed(closes))
    gains, losses = [], []
    for i in range(1, len(rev)):
        diff = rev[i] - rev[i - 1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    if len(gains) < period:
        return -1
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ═══════════════════════════════════════════════════════
#  텍스트 파싱 → 구조화된 조건
# ═══════════════════════════════════════════════════════

def parse_condition(name: str, description: str) -> dict:
    """
    조건 텍스트를 파싱하여 구조화된 조건 반환.

    Returns: {"type": str, "params": dict, "raw": str}
    """
    full = f"{name} {description}"

    # ── 시가대비 등락률 ──
    if _is_open_rate(full):
        rmin, rmax = _extract_range(full, default=(2.0, 9.0))
        return {"type": "open_rate", "params": {"min": rmin, "max": rmax}, "raw": full}

    # ── 전일대비 등락률 ──
    if _is_day_change(full):
        rmin, rmax = _extract_range(full, default=(2.0, 7.0))
        return {"type": "day_change", "params": {"min": rmin, "max": rmax}, "raw": full}

    # ── MACD (이평선보다 먼저 체크 — "MACD"가 명시적 키워드) ──
    if re.search(r'MACD|macd', full):
        fast, slow, sig = _extract_macd_params(full)
        tfs = _extract_timeframes(full)
        if re.search(r'[>＞]|signal|Signal|시그널', full):
            return {"type": "macd_cross", "params": {"fast": fast, "slow": slow, "signal": sig, "timeframes": tfs}, "raw": full}
        return {"type": "macd_rising", "params": {"fast": fast, "slow": slow, "signal": sig, "timeframes": tfs}, "raw": full}

    # ── 이평선 비교 (A > B) ──
    ma_cmp = _parse_ma_compare(full)
    if ma_cmp:
        return {"type": "ma_compare", "params": ma_cmp, "raw": full}

    # ── 종가 > 이평선 ──
    pv = _parse_price_vs_ma(full)
    if pv:
        return {"type": "price_vs_ma", "params": pv, "raw": full}

    # ── 이평선 상승 ──
    mr = _parse_ma_rising(full)
    if mr:
        return {"type": "ma_rising", "params": mr, "raw": full}

    # ── 거래량 급증 (분봉 기반) ──
    if re.search(r'거래량', full) and re.search(r'(\d+분|급증|평균|%)', full):
        return {"type": "volume_surge", "params": _extract_volume_params(full), "raw": full}

    # ── 유동주식 대비 거래량 비율 ──
    if "유동주식" in full:
        return {"type": "turnover", "params": _extract_turnover_params(full), "raw": full}

    # ── 주가비교 (봉 간 종가/시가 비교) ──
    if "주가비교" in full or ("종가" in full and (">" in full or "＞" in full) and ("봉전" in full or "봉" in full)):
        return {"type": "price_compare", "params": _extract_price_compare_params(full), "raw": full}

    # ── 분봉 등락율 범위 ──
    if re.search(r'(60분|15분|3분|1분).*등락', full) and re.search(r'[+\-]?\d+\.?\d*%?\s*~', full):
        return {"type": "minute_change", "params": _extract_minute_change_params(full), "raw": full}

    # ── 재무 (영업이익, ROE, ROA, 유보율) ──
    if "재무" in full or any(kw in full for kw in ["영업이익", "ROE", "ROA", "유보율", "roe", "roa"]):
        return {"type": "financial", "params": {"raw": full}, "raw": full}

    # ── 최고종가 / 신고가 ──
    if "최고종가" in full:
        return {"type": "new_high", "params": _extract_new_high_params(full), "raw": full}
    if "신고가" in full:
        return {"type": "new_high", "params": _extract_new_high_params(full), "raw": full}

    # ── 인식 실패 → 통과 처리 ──
    return {"type": "unknown", "params": {}, "raw": full}


# ═══════════════════════════════════════════════════════
#  스크리닝 평가 (통과/탈락)
# ═══════════════════════════════════════════════════════

def evaluate_screening(condition: dict, data: dict) -> tuple:
    """
    파싱된 조건을 창고 데이터에 적용.
    Returns: (passed: bool, reason: str)
    """
    ctype = condition["type"]
    params = condition["params"]

    _EVALUATORS = {
        "open_rate":    _eval_open_rate,
        "day_change":   _eval_day_change,
        "ma_compare":   _eval_ma_compare,
        "ma_rising":    _eval_ma_rising,
        "price_vs_ma":  _eval_price_vs_ma,
        "macd_cross":   _eval_macd_cross,
        "macd_rising":  _eval_macd_rising,
        "volume_surge": _eval_volume_surge,
        "new_high":     _eval_new_high,
        "financial":    _eval_financial,
        "turnover":     _eval_turnover,
        "price_compare": _eval_price_compare,
        "minute_change": _eval_minute_change,
    }

    evaluator = _EVALUATORS.get(ctype)
    if not evaluator:
        return True, f"미인식 조건 → 통과 ({condition['raw'][:30]})"

    try:
        return evaluator(params, data)
    except Exception as e:
        return False, f"평가 오류: {e}"


# ═══════════════════════════════════════════════════════
#  패턴 매칭 함수 — 조건 타입 식별
# ═══════════════════════════════════════════════════════

def _is_open_rate(text: str) -> bool:
    """시가대비 등락률인지 판별"""
    patterns = [
        r'시가.*대비.*등락',
        r'시가.*등락.*%',
        r'시가대비',
        r'0봉전시가.*등락',
        r'시가.*대비.*%',
    ]
    return any(re.search(p, text) for p in patterns)


def _is_day_change(text: str) -> bool:
    """전일대비 등락률인지 판별"""
    patterns = [
        r'전일.*대비.*등락',
        r'전일종가.*대비',
        r'전일대비.*%',
        r'전일.*대비.*당일',
    ]
    return any(re.search(p, text) for p in patterns)


def _parse_ma_compare(text: str) -> Optional[dict]:
    """
    이평선 비교 (A > B) 파싱.
    "일봉 단순 50이평 > 200이평"  → daily SMA(50) > SMA(200)
    "60분봉 지수 5이평 > 지수 20이평" → min60 EMA(5) > EMA(20)
    "EMA20 > EMA50"              → daily EMA(20) > EMA(50)
    "60분 50선>200선"            → min60 SMA(50) > SMA(200)
    """
    patterns = [
        # 풀 형식: "일봉 단순 50이평 > 200이평"
        r'(60분봉?|15분봉?|일봉)?\s*(단순|지수|EMA|SMA)?\s*(\d+)\s*이?평?\s*선?\s*[>＞]\s*(단순|지수|EMA|SMA)?\s*(\d+)',
        # 축약: "EMA5>EMA20", "50선>200선"
        r'(EMA|ema|SMA|sma)?(\d+)\s*선?\s*[>＞]\s*(EMA|ema|SMA|sma)?(\d+)\s*선?',
    ]
    for i, p in enumerate(patterns):
        m = re.search(p, text)
        if not m:
            continue
        groups = m.groups()
        if i == 0:  # 5-group pattern
            tf_raw, type1, p1, type2, p2 = groups
            tf = _resolve_timeframe(tf_raw, text)
            mt = _resolve_ma_type(type1 or type2, text)
            return {"timeframe": tf, "ma_type": mt, "period1": int(p1), "period2": int(p2)}
        else:  # 4-group pattern
            type1, p1, type2, p2 = groups
            tf = _resolve_timeframe(None, text)
            mt = _resolve_ma_type(type1 or type2, text)
            return {"timeframe": tf, "ma_type": mt, "period1": int(p1), "period2": int(p2)}
    return None


def _parse_price_vs_ma(text: str) -> Optional[dict]:
    """종가 > 이평선 파싱: "종가 > 지수 5이평", "종가 > EMA5" """
    m = re.search(r'종가\s*[>＞]\s*(단순|지수|EMA|SMA)?\s*(\d+)\s*이?평?선?', text)
    if m:
        return {
            "timeframe": _resolve_timeframe(None, text),
            "ma_type": _resolve_ma_type(m.group(1), text),
            "period": int(m.group(2)),
        }
    return None


def _parse_ma_rising(text: str) -> Optional[dict]:
    """
    이평선 상승 파싱:
    "일봉 단순 200이평 상승추세" → daily SMA(200) rising
    "EMA5 상승"                → daily EMA(5) rising
    "50일선 상승"              → daily SMA(50) rising
    """
    patterns = [
        # "단순/지수 N이평 상승"
        r'(60분봉?|15분봉?|일봉)?\s*(단순|지수|EMA|SMA)?\s*(\d+)\s*이?평?\s*선?\s*상승',
        # "EMA5 상승", "50일선 상승"
        r'(EMA|ema|SMA|sma)?(\d+)\s*(일선|이평|이평선|선)?\s*상승',
    ]
    for i, p in enumerate(patterns):
        m = re.search(p, text)
        if not m:
            continue
        groups = m.groups()
        if i == 0:
            tf_raw, type_raw, period_str = groups[:3]
            return {
                "timeframe": _resolve_timeframe(tf_raw, text),
                "ma_type": _resolve_ma_type(type_raw, text),
                "period": int(period_str),
            }
        else:
            type_raw, period_str = groups[0], groups[1]
            return {
                "timeframe": _resolve_timeframe(None, text),
                "ma_type": _resolve_ma_type(type_raw, text),
                "period": int(period_str),
            }
    return None


# ═══════════════════════════════════════════════════════
#  파라미터 추출 헬퍼
# ═══════════════════════════════════════════════════════

def _extract_range(text: str, default: tuple = (0.0, 100.0)) -> tuple:
    """범위 추출: "2~9%", "+2.00% ~ +7.00%" """
    m = re.search(r'([+-]?\d+\.?\d*)\s*%?\s*~\s*\+?(\d+\.?\d*)\s*%?', text)
    if m:
        return float(m.group(1)), float(m.group(2))
    return default


def _extract_macd_params(text: str) -> tuple:
    """MACD 파라미터: "[10,20,9]", "MACD(12,26,9)" → (fast, slow, signal)"""
    m = re.search(r'[\[\(]?\s*(\d+)\s*[,/]\s*(\d+)\s*[,/]\s*(\d+)\s*[\]\)]?', text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return 10, 20, 9


def _extract_timeframes(text: str) -> list:
    """텍스트에서 타임프레임 목록 추출"""
    tfs = []
    if "60분" in text:
        tfs.append("min60")
    if "15분" in text:
        tfs.append("min15")
    if "3분" in text:
        tfs.append("min03")
    if "1분" in text:
        tfs.append("min01")
    if "일봉" in text or not tfs:
        tfs.append("daily")
    return tfs


def _resolve_timeframe(raw: Optional[str], text: str) -> str:
    """타임프레임 해석"""
    if raw:
        if "60" in raw:
            return "min60"
        if "15" in raw:
            return "min15"
        if "3" in raw and "분" in text:
            return "min03"
        if "1" in raw and "분" in text:
            return "min01"
    if "60분" in text:
        return "min60"
    if "15분" in text:
        return "min15"
    if "3분" in text:
        return "min03"
    if "1분" in text:
        return "min01"
    return "daily"


def _resolve_ma_type(raw: Optional[str], text: str) -> str:
    """이평선 타입 해석 → 'ema' 또는 'sma'"""
    if raw:
        up = raw.upper()
        if up in ("EMA", "지수"):
            return "ema"
        if up in ("SMA", "단순"):
            return "sma"
    if "지수" in text or "EMA" in text or "ema" in text:
        return "ema"
    return "sma"


def _extract_volume_params(text: str) -> dict:
    """거래량 급증 파라미터"""
    range_m = re.search(r'(\d+)\s*%?\s*~\s*(\d+)\s*%?', text)
    avg_m = re.search(r'(\d+)\s*봉\s*평균', text)
    return {
        "min_pct": float(range_m.group(1)) if range_m else 120,
        "max_pct": float(range_m.group(2)) if range_m else 9000,
        "avg_bars": int(avg_m.group(1)) if avg_m else 2,
        "timeframe": _resolve_timeframe(None, text),
    }


def _extract_turnover_params(text: str) -> dict:
    """유동주식 대비 거래량 비율 파라미터"""
    # "3% 이상" → threshold=3.0, op=">="
    m = re.search(r'(\d+(?:\.\d+)?)\s*%?\s*(이상|이하|초과|미만)', text)
    threshold = float(m.group(1)) if m else 3.0
    op_map = {"이상": ">=", "이하": "<=", "초과": ">", "미만": "<"}
    op = op_map.get(m.group(2), ">=") if m else ">="
    return {
        "threshold": threshold,
        "operator": op,
        "timeframe": _resolve_timeframe(None, text),
    }


def _extract_price_compare_params(text: str) -> dict:
    """주가비교 파라미터 (0봉전 종가 > 1봉전 종가, 0봉전 종가 > 0봉전 시가)"""
    # "0봉전 종가 > 1봉전 종가" or "0봉전 종가 > 0봉전 시가"
    is_open_compare = "시가" in text  # 종가 vs 시가 (양봉 판단)
    return {
        "compare_type": "close_vs_open" if is_open_compare else "close_vs_prev_close",
        "timeframe": _resolve_timeframe(None, text),
    }


def _extract_minute_change_params(text: str) -> dict:
    """분봉 등락율 범위 파라미터"""
    # "+2.00% ~ +6.00%" 또는 "2~6%"
    m = re.search(r'[+\-]?(\d+(?:\.\d+)?)\s*%?\s*~\s*[+\-]?(\d+(?:\.\d+)?)\s*%?', text)
    return {
        "min_rate": float(m.group(1)) if m else 2.0,
        "max_rate": float(m.group(2)) if m else 6.0,
        "timeframe": _resolve_timeframe(None, text),
    }


def _extract_new_high_params(text: str) -> dict:
    """신고가 파라미터"""
    bars = re.findall(r'(\d+)\s*봉', text)
    return {
        "lookback": int(bars[0]) if len(bars) >= 1 else 3,
        "within": int(bars[1]) if len(bars) >= 2 else 1,
        "timeframe": _resolve_timeframe(None, text),
    }


# ═══════════════════════════════════════════════════════
#  평가 함수 — 각 조건 타입별 실행
# ═══════════════════════════════════════════════════════

def _get_candles(data: dict, timeframe: str) -> list:
    """타임프레임에 맞는 캔들 반환"""
    tf_map = {"min60": "min60", "min15": "min15", "min03": "min03", "min01": "min01", "daily": "daily"}
    return data.get(tf_map.get(timeframe, "daily"), [])


def _eval_open_rate(params: dict, data: dict) -> tuple:
    """시가대비 등락률"""
    price = data.get("price", {})
    cur = float(price.get("price", price.get("close", 0)))
    opn = float(price.get("open", 0))
    if opn <= 0:
        return False, "시가 없음"
    rate = (cur - opn) / opn * 100
    rmin, rmax = params["min"], params["max"]
    if rmin <= rate <= rmax:
        return True, f"시가대비 {rate:+.1f}% ✓ ({rmin}~{rmax}%)"
    return False, f"시가대비 {rate:+.1f}% ({rmin}~{rmax}% 밖)"


def _eval_day_change(params: dict, data: dict) -> tuple:
    """전일대비 등락률"""
    price = data.get("price", {})
    rate = float(price.get("diff", price.get("rate", 0)))
    rmin, rmax = params["min"], params["max"]
    if rmin <= rate <= rmax:
        return True, f"전일대비 {rate:+.1f}% ✓ ({rmin}~{rmax}%)"
    return False, f"전일대비 {rate:+.1f}% ({rmin}~{rmax}% 밖)"


def _eval_ma_compare(params: dict, data: dict) -> tuple:
    """이평선 비교 (A > B)"""
    candles = _get_candles(data, params["timeframe"])
    if not candles:
        return False, f"캔들 없음 ({params['timeframe']})"

    closes = [float(c["close"]) for c in candles]
    p1, p2 = params["period1"], params["period2"]
    need = max(p1, p2)

    if len(closes) < need:
        return False, f"데이터 부족 ({len(closes)}/{need}봉)"

    calc = _ema if params["ma_type"] == "ema" else _sma
    ma1 = calc(closes, p1)
    ma2 = calc(closes, p2)

    if not ma1 or not ma2:
        return False, "이평 계산 실패"

    label = "EMA" if params["ma_type"] == "ema" else ""
    if ma1[0] > ma2[0]:
        return True, f"{label}{p1}({ma1[0]:.0f}) > {label}{p2}({ma2[0]:.0f}) ✓"
    return False, f"{label}{p1}({ma1[0]:.0f}) ≤ {label}{p2}({ma2[0]:.0f})"


def _eval_ma_rising(params: dict, data: dict) -> tuple:
    """이평선 상승추세"""
    candles = _get_candles(data, params["timeframe"])
    if not candles:
        return False, "캔들 없음"

    closes = [float(c["close"]) for c in candles]
    period = params["period"]

    if len(closes) < period + 2:
        return False, f"데이터 부족 ({len(closes)}/{period + 2}봉)"

    calc = _ema if params["ma_type"] == "ema" else _sma
    ma = calc(closes, period)

    if not ma or len(ma) < 2:
        return False, "이평 계산 실패"

    label = "EMA" if params["ma_type"] == "ema" else ""
    if ma[0] > ma[1]:
        return True, f"{label}{period}선 상승 ({ma[1]:.0f}→{ma[0]:.0f}) ✓"
    return False, f"{label}{period}선 하락 ({ma[1]:.0f}→{ma[0]:.0f})"


def _eval_price_vs_ma(params: dict, data: dict) -> tuple:
    """종가 > 이평선"""
    candles = _get_candles(data, params["timeframe"])
    if not candles:
        return False, "캔들 없음"

    closes = [float(c["close"]) for c in candles]
    period = params["period"]

    if len(closes) < period:
        return False, f"데이터 부족"

    calc = _ema if params["ma_type"] == "ema" else _sma
    ma = calc(closes, period)

    if not ma:
        return False, "이평 계산 실패"

    label = "EMA" if params["ma_type"] == "ema" else ""
    cur = closes[0]
    if cur > ma[0]:
        return True, f"종가({cur:.0f}) > {label}{period}({ma[0]:.0f}) ✓"
    return False, f"종가({cur:.0f}) ≤ {label}{period}({ma[0]:.0f})"


def _eval_macd_cross(params: dict, data: dict) -> tuple:
    """MACD > Signal"""
    for tf in params.get("timeframes", ["daily"]):
        candles = _get_candles(data, tf)
        if not candles or len(candles) < params["slow"] + params["signal"]:
            continue
        closes = [float(c["close"]) for c in candles]
        ml, sl, _ = _macd(closes, params["fast"], params["slow"], params["signal"])
        if ml and sl and ml[0] > sl[0]:
            return True, f"MACD({ml[0]:.2f}) > Signal({sl[0]:.2f}) ✓ [{tf}]"
    return False, "MACD ≤ Signal"


def _eval_macd_rising(params: dict, data: dict) -> tuple:
    """MACD 상승추세"""
    for tf in params.get("timeframes", ["daily"]):
        candles = _get_candles(data, tf)
        if not candles or len(candles) < params["slow"] + params["signal"]:
            continue
        closes = [float(c["close"]) for c in candles]
        ml, _, _ = _macd(closes, params["fast"], params["slow"], params["signal"])
        if ml and len(ml) >= 2 and ml[0] > ml[1]:
            return True, f"MACD 상승 ({ml[1]:.2f}→{ml[0]:.2f}) ✓ [{tf}]"
    return False, "MACD 하락/횡보"


def _eval_volume_surge(params: dict, data: dict) -> tuple:
    """거래량 급증"""
    candles = _get_candles(data, params["timeframe"])
    avg_bars = params["avg_bars"]
    if not candles or len(candles) < avg_bars + 1:
        return False, "거래량 데이터 부족"

    avg_vol = sum(candles[i]["volume"] for i in range(1, avg_bars + 1)) / avg_bars
    if avg_vol <= 0:
        return False, "평균거래량 0"

    ratio = candles[0]["volume"] / avg_vol * 100
    rmin, rmax = params["min_pct"], params["max_pct"]

    if rmin <= ratio <= rmax:
        return True, f"거래량 {ratio:.0f}% ✓ ({rmin}~{rmax}%)"
    return False, f"거래량 {ratio:.0f}% ({rmin}~{rmax}% 밖)"


def _eval_new_high(params: dict, data: dict) -> tuple:
    """신고가"""
    candles = _get_candles(data, params["timeframe"])
    lookback = params["lookback"]
    within = params["within"]

    if not candles or len(candles) < lookback:
        return False, "데이터 부족"

    closes = [float(c["close"]) for c in candles[:lookback]]
    max_close = max(closes)
    recent_max = max(closes[:within])

    if recent_max >= max_close:
        return True, f"신고가 ✓ ({params['timeframe']} {lookback}봉 내)"
    return False, f"신고가 아님 (최고:{max_close:.0f} vs 최근:{recent_max:.0f})"


def _eval_financial(params: dict, data: dict) -> tuple:
    """재무 조건 (영업이익, ROE, ROA, 유보율)"""
    fin = data.get("financial", {})
    if not fin:
        return True, "재무 데이터 없음 → 통과"

    raw = params.get("raw", "")

    # 임계값 파싱: "10% 이상", "+5% 이상", "500% 이상"
    m = re.search(r'[+\-]?(\d+(?:\.\d+)?)\s*%?\s*(이상|이하|초과|미만)', raw)
    if not m:
        return True, "기준값 없음 → 통과"
    threshold = float(m.group(1))
    op_map = {"이상": ">=", "이하": "<=", "초과": ">", "미만": "<"}
    op = op_map.get(m.group(2), ">=")
    ops = {">=": lambda a, b: a >= b, ">": lambda a, b: a > b,
           "<=": lambda a, b: a <= b, "<": lambda a, b: a < b}

    # 조건별 값 추출
    if "ROE" in raw or "roe" in raw:
        val = fin.get("roe", 0)
        label = f"ROE {val:.1f}%"
    elif "ROA" in raw or "roa" in raw:
        val = fin.get("roa", 0)
        label = f"ROA {val:.1f}%"
    elif "유보율" in raw:
        val = fin.get("reserve_ratio", 0)
        label = f"유보율 {val:.0f}%"
    elif "영업이익" in raw and "분기" in raw:
        val = fin.get("op_profit_quarter_rate", 0)
        label = f"영업이익 분기 {val:+.1f}%"
    elif "영업이익" in raw and "년" in raw:
        val = fin.get("op_profit_year_rate", 0)
        label = f"영업이익 년 {val:+.1f}%"
    else:
        return True, "재무 조건 미인식 → 통과"

    passed = ops.get(op, ops[">="])(val, threshold)
    op_str = {">=": "이상", ">": "초과", "<=": "이하", "<": "미만"}.get(op, "")
    tag = "✓" if passed else "✗"
    return passed, f"{label} {tag} (기준:{threshold}%{op_str})"


def _eval_turnover(params: dict, data: dict) -> tuple:
    """유동주식 대비 거래량 비율"""
    tf = params["timeframe"]
    threshold = params["threshold"]
    op = params["operator"]
    price_data = data.get("price", {})

    listing = 0
    try:
        listing = int(float(price_data.get("listing", 0)))
    except Exception:
        pass
    if listing <= 0:
        return False, "상장주식수 데이터 없음"

    if tf == "daily":
        # 일봉: 당일 거래량
        try:
            vol = int(float(price_data.get("volume", 0)))
        except Exception:
            return False, "거래량 없음"
        turnover = (vol / listing) * 100
    else:
        # 분봉: 현재봉 거래량
        candles = _get_candles(data, tf)
        if not candles:
            return False, f"{tf} 데이터 없음"
        vol = candles[0].get("volume", 0)
        turnover = (vol / listing) * 100

    ops = {">=": lambda a, b: a >= b, ">": lambda a, b: a > b,
           "<=": lambda a, b: a <= b, "<": lambda a, b: a < b}
    passed = ops.get(op, ops[">="])(turnover, threshold)

    op_str = {">=": "이상", ">": "초과", "<=": "이하", "<": "미만"}.get(op, "")
    tag = "✓" if passed else "✗"
    return passed, f"턴오버 {turnover:.3f}% {tag} (기준:{threshold}%{op_str}) [{tf}]"


def _eval_price_compare(params: dict, data: dict) -> tuple:
    """주가비교 (봉 간 비교)"""
    tf = params["timeframe"]
    ctype = params["compare_type"]
    candles = _get_candles(data, tf)

    if not candles or len(candles) < 2:
        return False, f"{tf} 데이터 부족"

    cur = candles[0]
    cur_close = float(cur.get("close", 0))

    if ctype == "close_vs_open":
        # 0봉전 종가 > 0봉전 시가 (양봉)
        cur_open = float(cur.get("open", 0))
        if cur_open <= 0:
            return False, "시가 없음"
        if cur_close > cur_open:
            rate = (cur_close - cur_open) / cur_open * 100
            return True, f"양봉 ✓ 종가({cur_close:,.0f}) > 시가({cur_open:,.0f}) {rate:+.2f}% [{tf}]"
        return False, f"음봉 종가({cur_close:,.0f}) ≤ 시가({cur_open:,.0f}) [{tf}]"
    else:
        # 0봉전 종가 > 1봉전 종가
        prev_close = float(candles[1].get("close", 0))
        if prev_close <= 0:
            return False, "전봉 종가 없음"
        if cur_close > prev_close:
            rate = (cur_close - prev_close) / prev_close * 100
            return True, f"상승 ✓ 현재({cur_close:,.0f}) > 전봉({prev_close:,.0f}) {rate:+.2f}% [{tf}]"
        return False, f"하락 현재({cur_close:,.0f}) ≤ 전봉({prev_close:,.0f}) [{tf}]"


def _eval_minute_change(params: dict, data: dict) -> tuple:
    """분봉 등락율 범위"""
    tf = params["timeframe"]
    candles = _get_candles(data, tf)

    if not candles or len(candles) < 2:
        return False, f"{tf} 데이터 부족"

    cur_close = float(candles[0].get("close", 0))
    prev_close = float(candles[1].get("close", 0))

    if prev_close <= 0:
        return False, "전봉 종가 없음"

    rate = (cur_close - prev_close) / prev_close * 100
    rmin, rmax = params["min_rate"], params["max_rate"]

    if rmin <= rate <= rmax:
        return True, f"등락율 {rate:+.2f}% ✓ ({rmin}~{rmax}%) [{tf}]"
    return False, f"등락율 {rate:+.2f}% ({rmin}~{rmax}% 밖) [{tf}]"
