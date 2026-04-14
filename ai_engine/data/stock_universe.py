"""
종목 유니버스 관리
- 코스피 + 코스닥 보통주
- 현재가 1,000원 ~ 500,000원
- 제외: 정리매매, 관리종목, ETF, ELW, ETN, SPAC 등
"""
import time
from .cache import get_cache


# 제외 키워드 (종목명에 포함 시 제외)
EXCLUDE_KEYWORDS = [
    "스팩", "SPAC", "ETF", "ETN", "리츠", "인프라",
    "선박", "우", "2우", "3우", "B",   # 우선주
]

# 제외 종목코드 패턴
EXCLUDE_SUFFIX = ["0", "5"]  # 우선주는 끝자리 0 또는 5 (단순 휴리스틱)


def is_valid_stock(code: str, name: str, price: int,
                   status: str = "", stock_type: str = "") -> bool:
    """
    종목 유니버스 필터
    code: 종목코드 (6자리)
    name: 종목명
    price: 현재가
    status: 거래 상태 (정리매매/관리/투자경고 등)
    stock_type: 주식 종류 (보통주/우선주 등)
    """
    # 가격 범위
    if not (1000 <= price <= 500000):
        return False

    # 거래 상태 이상
    bad_status = ["정리매매", "관리종목", "투자경고", "투자주의", "투자위험", "거래정지", "불성실"]
    for s in bad_status:
        if s in status:
            return False

    # 제외 종목명 키워드
    for kw in EXCLUDE_KEYWORDS:
        if kw in name:
            return False

    # 우선주 제외 (코드 끝이 0이 아닌 5 → 우선주 관행)
    if len(code) == 6 and code[-1] == "5":
        return False

    return True


class StockUniverse:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self._stocks = []          # [{"code": .., "name": .., "market": ..}]
        self._last_update = 0

    def get_stocks(self, force_refresh=False) -> list:
        """전체 종목 리스트 반환 (1시간 캐시, 실패 시 재시도)"""
        import time as _time
        cache = get_cache()
        cached = cache.get("universe")
        if cached and not force_refresh:
            return cached

        # 최대 3회 재시도
        for attempt in range(3):
            stocks = self.fetcher.get_stock_list()
            if stocks:
                cache.set("universe", stocks, ttl_seconds=3600)
                self._stocks = stocks
                print(f"[유니버스] {len(stocks)}종목 로드 (시도:{attempt+1})")
                return self._stocks
            print(f"[유니버스] ⚠ 종목 로드 실패 (시도:{attempt+1}/3)")
            if attempt < 2:
                _time.sleep(2)

        print("[유니버스] ❌ 종목 로드 3회 실패")
        return self._stocks

    def size(self) -> int:
        return len(self._stocks)
