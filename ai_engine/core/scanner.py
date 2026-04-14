"""
스캐너 — 창고(캐시)만 읽고 고려사항 점수로 평가

AI는 API를 모른다. 창고에 데이터가 있으면 읽고, 없으면 대기.
스캔 리스트 전체 종목 → 고려사항 점수 → 신호 생성.
"""
import json
import os
import sys
from datetime import datetime

from ..data.cache import get_cache
from .signal_generator import generate_signal, generate_sell_signal


def _get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



def _load_holdings_cache() -> list:
    """보유종목 캐시 로드"""
    try:
        base = _get_base_path()
        if getattr(sys, 'frozen', False):
            exe_name = os.path.basename(sys.executable).lower()
            fname = "holdings_cache_mock.json" if "mock" in exe_name else "holdings_cache_real.json"
        else:
            fname = "holdings_cache.json"
        path = os.path.join(base, fname)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _clean_code(code: str) -> str:
    if code.startswith("A") and len(code) == 7:
        return code[1:]
    return code


class Scanner:
    """
    AI 스캐너 — 창고(캐시)만 읽는다. API 모른다.

    사용법:
        scanner = Scanner()
        scanner.set_filtered_stocks(stocks)  # 서버 종목 리스트 전달
        signals, count = scanner.run_scan()  # 창고에서 읽고 평가
    """
    def __init__(self):
        self._cache = get_cache()
        self._filtered_stocks = None

    def set_filtered_stocks(self, stocks: list):
        """서버 조건검색 결과 전달 (수집기가 넣어줌)"""
        self._filtered_stocks = stocks
        print(f"[스캐너] 종목 설정: {len(stocks)}종목")

    def _load_diff_filter(self):
        """등락율 사전 필터 범위 로드 → (min, max) 또는 None"""
        try:
            from ..conditions._config_helper import get_engine_config_path
            import json as _json
            path = get_engine_config_path()
            with open(path, "r", encoding="utf-8") as f:
                cfg = _json.load(f)
            df = cfg.get("scan_diff_filter", {})
            if df.get("enabled", False):
                return (float(df.get("min", 2.0)), float(df.get("max", 9.0)))
        except Exception:
            pass
        return None

    def run_scan(self) -> tuple:
        """
        스캔 실행 — 창고 데이터만 사용, 고려사항 점수로 평가.
        Returns: (signals: list, scanned_count: int)
        """
        # 1. 보유종목 SELL 체크
        held_stocks = _load_holdings_cache()
        held_codes = {h["code"] for h in held_stocks}
        sell_signals = self._scan_held_stocks(held_stocks)

        # 2. 서버 종목 없으면 보유종목만
        if not self._filtered_stocks:
            print("[스캐너] 종목 없음")
            return sell_signals, 0

        # 3. 전체 종목 → 고려사항 점수 평가
        stocks = list(self._filtered_stocks)
        total = len(stocks)
        buy_hold_signals = []
        no_data_count = 0
        dbg = [
            f"=== 스캔 {datetime.now().strftime('%H:%M:%S')} ({total}종목) ===",
        ]
        detail_dbg = [
            f"=== 상세 스캔 {datetime.now().strftime('%H:%M:%S')} ({total}종목) ===",
        ]

        # 등락율 필터 범위 로드
        diff_filter = self._load_diff_filter()

        for stock in stocks:
            code = _clean_code(stock["code"])
            name = stock["name"]

            # 창고에서 읽기
            cached = self._cache.get(f"data_{code}")
            if not cached:
                no_data_count += 1
                if len(dbg) < 30:
                    dbg.append(f"  {name}({code}): 데이터 대기중")
                continue

            # 등락율 사전 필터 (범위 밖이면 스킵)
            if diff_filter:
                try:
                    pd = cached.get("price", {})
                    dr = float(pd.get("diff", pd.get("rate", 0)))
                    dmin, dmax = diff_filter
                    if dr < dmin or dr > dmax:
                        if len(dbg) < 30:
                            dbg.append(f"  {name}({code}): 등락율 범위밖 ({dr:+.1f}%)")
                        continue
                except Exception:
                    pass  # 데이터 파싱 실패 시 통과

            # 고려사항 점수 계산 → 추천 여부 결정
            try:
                sig = generate_signal(code, name, cached, server_filtered=True)
                if sig:
                    buy_hold_signals.append(sig)
                    if len(dbg) < 30:
                        dbg.append(f"  {name}({code}): {sig['signal_type']} {sig['score']:.1f}")
                    # 고려사항 상세 로그
                    conds = sig.get("conditions", {})
                    for cname, cval in conds.items():
                        sc = cval.get("score", 0)
                        dt = cval.get("detail", "")
                        wt = cval.get("weight", 0)
                        detail_dbg.append(f"  [{name}({code})] 고려: {cname} = {sc:.0f}점 (w={wt}) {dt}")
            except Exception as e:
                if len(dbg) < 30:
                    dbg.append(f"  {name}({code}): ⚠ {e}")

        buy_hold_signals.sort(key=lambda x: x["score"], reverse=True)
        signals = sell_signals + buy_hold_signals

        evaluated = len(buy_hold_signals)
        dbg.append(f"=== 전체={total} 평가={evaluated} 데이터대기={no_data_count} ===")
        print(f"[스캐너] {total}종목 → 평가:{evaluated} 데이터대기:{no_data_count}")
        self._write_debug(dbg)
        self._write_detail_debug(detail_dbg)

        return signals, total

    def _scan_held_stocks(self, held_stocks: list) -> list:
        """보유종목 SELL 신호 체크"""
        signals = []
        for h in held_stocks:
            code = h.get("code", "")
            name = h.get("name", "")
            if not code:
                continue
            try:
                cached = self._cache.get(f"data_{_clean_code(code)}")
                if not cached:
                    continue
                sig = generate_sell_signal(code, name, cached, hold_info=h)
                signals.append(sig)
            except Exception as e:
                print(f"[스캐너] SELL오류 {code}: {e}")
        return signals

    def _write_debug(self, lines: list):
        try:
            path = os.path.join(_get_base_path(), "debug_scan.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception:
            pass

    def _write_detail_debug(self, lines: list):
        try:
            path = os.path.join(_get_base_path(), "debug_screening.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception:
            pass


def _empty_signal(code, name, price=0):
    return {
        "stock_code": code, "stock_name": name,
        "signal_type": "WATCH", "score": 0,
        "current_price": price,
        "conditions": {}, "confidence": "–",
        "supply_score": 0, "chart_score": 0, "material_score": 0,
    }
