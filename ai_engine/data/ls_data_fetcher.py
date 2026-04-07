"""
LS API 데이터 조회 래퍼
ai_engine에서 사용하는 데이터 조회 인터페이스
실제 API 호출은 기존 ls_api.py (LSApi)에 위임
"""
import sys
import os

# 상위 디렉토리(stock_trader/)를 import 경로에 추가
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from ls_api import LSApi


class LSDataFetcher:
    """LSApi 래퍼 - ai_engine 전용 데이터 조회"""

    def __init__(self, mode: str = "real"):
        self.api = LSApi(mode=mode)
        self._token_ok = False

    def connect(self) -> bool:
        self._token_ok = self.api.get_token()
        return self._token_ok

    def get_daily_ohlcv(self, code: str, count: int = 250) -> list:
        return self.api.get_daily_ohlcv(code, count=count)

    def get_minute_ohlcv(self, code: str, tick_range: int = 60,
                         count: int = 100) -> list:
        return self.api.get_minute_ohlcv(code, tick_range=tick_range, count=count)

    def get_supply_demand(self, code: str, count: int = 5) -> list:
        return self.api.get_supply_demand(code, count=count)

    def get_price(self, code: str) -> dict:
        return self.api.get_price(code) or {}

    def get_stock_list(self, market: str = "0") -> list:
        return self.api.get_stock_list(market=market)
