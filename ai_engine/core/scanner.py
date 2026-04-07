"""
전 종목 스캔 + 보유종목 SELL 신호 생성
1. 종목 유니버스 로드
2. 사전 스크리닝 (기술적 조건)
3. 점수 계산 → BUY/HOLD 신호 생성
4. 보유종목(holdings_cache.json) → SELL 신호 생성
"""
import time
import json
import os
import sys
from datetime import datetime

from ..data.stock_universe import StockUniverse, is_valid_stock
from ..data.cache import get_cache
from ..conditions.ma_alignment   import MAAlignmentCondition
from ..conditions.macd           import MACDCondition
from ..core.signal_generator     import generate_signal, generate_sell_signal


# 스크리닝 조건 계산기 목록
SCREENING_CONDITIONS = [
    MAAlignmentCondition(),
    MACDCondition(),
]


def _load_screening_cfg() -> list:
    """engine_config.json screening 섹션 로드"""
    try:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(base, "engine_config.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return [c for c in cfg.get("screening", []) if c.get("enabled", True)]
    except Exception:
        return []


def _load_holdings_cache() -> list:
    """
    GUI가 저장한 holdings_cache.json 읽기
    반환: [{"code", "name", "buy_price", "qty"}, ...]
    """
    try:
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "holdings_cache.json")
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


class Scanner:
    def __init__(self, fetcher):
        self.fetcher   = fetcher
        self.universe  = StockUniverse(fetcher)
        self._cache    = get_cache()

    def _fetch_data(self, code: str) -> dict:
        """종목 데이터 조회 (캐시 활용)"""
        cache_key = f"data_{code}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        daily  = self.fetcher.get_daily_ohlcv(code, count=250)
        min60  = self.fetcher.get_minute_ohlcv(code, tick_range=60, count=100)
        min15  = self.fetcher.get_minute_ohlcv(code, tick_range=15, count=100)
        supply = self.fetcher.get_supply_demand(code, count=5)
        price  = self.fetcher.get_price(code) or {}

        data = {
            "daily" : daily,
            "min60" : min60,
            "min15" : min15,
            "supply": supply,
            "price" : price,
        }
        self._cache.set(cache_key, data, ttl_seconds=300)  # 5분 캐시
        return data

    def _passes_screening(self, code: str, data: dict) -> bool:
        """사전 스크리닝 통과 여부"""
        if not data.get("daily"):
            return False

        # 가격 범위 체크
        price_data = data.get("price", {})
        try:
            price = int(float(price_data.get("price", price_data.get("close", 0))))
        except Exception:
            price = 0
        if not is_valid_stock(code, "", price):
            return False

        # 등락률 체크 (+2% ~ +7%)
        try:
            rate = float(price_data.get("diff", price_data.get("rate", 0)))
            if not (2.0 <= rate <= 7.0):
                return False
        except Exception:
            pass

        # 기술적 조건 (활성화된 것만)
        for cond in SCREENING_CONDITIONS:
            try:
                if not cond.check_screening(code, data):
                    return False
            except Exception:
                pass

        return True

    def _scan_held_stocks(self, held_stocks: list) -> list:
        """
        보유종목 SELL 신호 체크 (스크리닝 없이 무조건 점수 계산)
        매수 조건이 약해지거나 매도 조건 충족 시 SELL 반환
        """
        sell_signals = []
        for h in held_stocks:
            code = h.get("code", "")
            name = h.get("name", "")
            if not code:
                continue
            try:
                data = self._fetch_data(code)
                sig  = generate_sell_signal(
                    code, name, data,
                    hold_info=h,
                    market_status=None   # TODO: 시장 상태 주입 (향후 확장)
                )
                sell_signals.append(sig)
                if sig["signal_type"] == "SELL":
                    print(f"[스캐너] 🔴 SELL: {name}({code}) 사유: {sig.get('sell_reason')}")
                else:
                    print(f"[스캐너] 🟡 HOLD: {name}({code}) {sig['score']:.1f}점")
                time.sleep(0.05)
            except Exception as e:
                print(f"[스캐너] SELL체크 오류 {code}: {e}")
        return sell_signals

    def run_scan(self, max_stocks: int = 2000) -> tuple[list, int]:
        """
        전 종목 스캔 실행
        반환: (signals 리스트, 스캔한 종목 수)
        """
        # ── 1. 보유종목 SELL 체크 (최우선) ──
        held_stocks  = _load_holdings_cache()
        held_codes   = {h["code"] for h in held_stocks}
        sell_signals = self._scan_held_stocks(held_stocks)

        # ── 2. 전 종목 BUY/HOLD 스캔 ──
        stocks     = self.universe.get_stocks()
        if not stocks:
            print("[스캐너] 종목 리스트 없음")
            # 보유종목 SELL 신호만이라도 반환
            return sell_signals, 0

        buy_hold_signals = []
        scan_count = 0

        for stock in stocks[:max_stocks]:
            code = stock["code"]
            name = stock["name"]

            # 보유종목은 위에서 이미 SELL 처리 → BUY/HOLD 스캔 제외
            if code in held_codes:
                continue

            scan_count += 1
            try:
                data = self._fetch_data(code)
                if not self._passes_screening(code, data):
                    continue
                sig = generate_signal(code, name, data)
                if sig:
                    buy_hold_signals.append(sig)
                    print(f"[스캐너] ✅ {name}({code}) {sig['signal_type']} {sig['score']}점")
            except Exception as e:
                print(f"[스캐너] {code} 오류: {e}")

            time.sleep(0.1)

        # ── 3. 합산 (SELL 먼저, 나머지 점수 내림차순) ──
        buy_hold_signals.sort(key=lambda x: x["score"], reverse=True)
        signals = sell_signals + buy_hold_signals

        print(f"[스캐너] 완료 - {scan_count}종목 스캔 → "
              f"매수/보유:{len(buy_hold_signals)} 매도:{len(sell_signals)}")
        return signals, scan_count
