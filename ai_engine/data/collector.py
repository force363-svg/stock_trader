"""
데이터 수집기 — API 호출 → 창고(캐시) 적재

AI와 분리된 독립 모듈.
API를 아는 건 이 파일뿐. AI(scanner)는 이 파일을 모른다.

흐름:
  1. 서버 조건검색(t1859) → 종목 리스트
  2. 종목별 상세 데이터(일봉, 분봉, 수급, 시세) → 창고에 저장
  3. 시장 공통 데이터(테마, 업종지수) → 창고에 저장
  4. AI는 나중에 창고에서 읽기만 함
"""
import time
import threading as _threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from .cache import get_cache


def collect_market_data(fetcher) -> int:
    """
    시장 공통 데이터 수집 → 창고 적재.
    종목별이 아닌 시장 전체 데이터 (테마, 업종지수).

    Returns: 수집 항목 수
    """
    cache = get_cache()
    collected = 0

    # ── 1. 상승테마 + 테마별 종목 ──
    try:
        themes = fetcher.get_themes()
        if themes:
            # 테마별 종목 매핑: {종목코드: [테마명, ...]}
            stock_themes = {}
            for theme in themes[:20]:  # 상위 20개 테마
                tmcode = theme.get("code", "")
                tmname = theme.get("name", "")
                diff = theme.get("diff", 0)
                if not tmcode:
                    continue
                try:
                    theme_stocks = fetcher.get_theme_stocks(tmcode)
                    for ts in theme_stocks:
                        scode = ts.get("code", "")
                        if scode:
                            if scode not in stock_themes:
                                stock_themes[scode] = []
                            stock_themes[scode].append({
                                "name": tmname,
                                "diff": diff,
                            })
                    time.sleep(0.2)
                except Exception:
                    pass

            cache.set("market_themes", themes, ttl_seconds=86400)
            cache.set("stock_themes", stock_themes, ttl_seconds=86400)
            collected += 1
            print(f"[수집기] 테마 {len(themes)}개, 종목매핑 {len(stock_themes)}건")
    except Exception as e:
        print(f"[수집기] 테마 수집 오류: {e}")

    # ── 2. 시장지수 (코스피/코스닥) ──
    try:
        kospi = fetcher.api.get_market_index("001") if hasattr(fetcher.api, 'get_market_index') else None
        kosdaq = fetcher.api.get_market_index("301") if hasattr(fetcher.api, 'get_market_index') else None
        try:
            import os, sys
            _base = os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            with open(os.path.join(_base, "debug_t1511.txt"), "w", encoding="utf-8") as _f:
                _f.write(f"kospi: {kospi}\n")
                _f.write(f"kosdaq: {kosdaq}\n")
        except Exception:
            pass
        market_idx = {}
        if kospi:
            try:
                rate = kospi.get("diffjisu", kospi.get("jnildiff", kospi.get("rate", 0)))
                market_idx["kospi_diff"] = round(float(rate), 2)
            except (ValueError, TypeError):
                market_idx["kospi_diff"] = 0
        if kosdaq:
            try:
                rate = kosdaq.get("diffjisu", kosdaq.get("jnildiff", kosdaq.get("rate", 0)))
                market_idx["kosdaq_diff"] = round(float(rate), 2)
            except (ValueError, TypeError):
                market_idx["kosdaq_diff"] = 0
        if market_idx:
            cache.set("market_index", market_idx, ttl_seconds=86400)
            collected += 1
            print(f"[수집기] 시장지수: KOSPI {market_idx.get('kospi_diff', 0):+.2f}% KOSDAQ {market_idx.get('kosdaq_diff', 0):+.2f}%")
    except Exception as e:
        print(f"[수집기] 시장지수 수집 오류: {e}")

    # ── 3. 업종지수 ──
    try:
        sectors = fetcher.get_sector_indices()
        if sectors:
            cache.set("market_sectors", sectors, ttl_seconds=86400)
            collected += 1
            print(f"[수집기] 업종지수 {len(sectors)}개")
    except Exception as e:
        print(f"[수집기] 업종지수 수집 오류: {e}")

    cache.save()
    return collected


# ═══════════════════════════════════════════════════════
#  병렬 수집 (스레드별 fetcher 재사용)
# ═══════════════════════════════════════════════════════

_thread_local = _threading.local()


def _get_thread_fetcher(mode: str):
    """스레드별 fetcher 1개 재사용 (토큰 1번만 발급)"""
    f = getattr(_thread_local, 'fetcher', None)
    if f is None:
        from .ls_data_fetcher import LSDataFetcher
        f = LSDataFetcher(mode=mode)
        f.connect()
        _thread_local.fetcher = f
    return f


def _fetch_one_stock(mode: str, code: str) -> dict:
    """단일 종목: 일봉100 + 60분봉20 + 15분봉20 + 수급 + 시세 (5회 호출)"""
    fetcher = _get_thread_fetcher(mode)
    try:
        daily = fetcher.get_daily_ohlcv(code, count=100)
        min60 = fetcher.get_minute_ohlcv(code, tick_range=60, count=20)
        min15 = fetcher.get_minute_ohlcv(code, tick_range=15, count=20)
        supply = fetcher.get_supply_demand(code, count=5)
        price = fetcher.get_price(code) or {}
        return {
            "daily": daily, "min60": min60, "min15": min15,
            "min03": [], "min01": [], "supply": supply,
            "price": price, "financial": {},
        }
    except Exception as e:
        print(f"[수집기] {code} 오류: {e}")
        return None


def _is_cache_fresh(cache, code: str) -> bool:
    """캐시에 데이터가 있고 30분 이내면 스킵"""
    cached = cache.get(f"data_{code}")
    if not cached:
        return False
    if "min60" not in cached or not cached["min60"]:
        return False
    # 캐시 타임스탬프 체크
    ts = cache.get_timestamp(f"data_{code}")
    if ts and (time.time() - ts) < 1800:  # 30분
        return True
    return False


def collect_stock_data(fetcher, stocks: list, status_callback=None) -> int:
    """
    종목 리스트의 상세 데이터를 창고(캐시)에 적재.
    병렬 수집 (4 workers, 스레드별 fetcher 재사용).
    요청량 최적화: 일봉100, 60분봉20, 15분봉20, 2단계 보강 제거.
    """
    cache = get_cache()
    count = 0
    fail = 0
    total = len(stocks)
    mode = getattr(fetcher.api, 'mode', 'mock')

    # 캐시 히트 분리 (30분 이내 데이터는 스킵)
    need_fetch = []
    for stock in stocks:
        code = stock.get("code", "")
        if not code:
            continue
        if code.startswith("A") and len(code) == 7:
            code = code[1:]
        if _is_cache_fresh(cache, code):
            count += 1
        else:
            need_fetch.append(code)

    if not need_fetch:
        print(f"[수집기] 완료: 전체 캐시 히트 ({count}/{total}종목)")
        return count

    # 병렬 수집 (4 workers, 토큰 4개만)
    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_one_stock, mode, code): code
                   for code in need_fetch}
        for future in as_completed(futures):
            code = futures[future]
            data = future.result()
            if data:
                cache.set(f"data_{code}", data, ttl_seconds=86400)
                count += 1
            else:
                fail += 1
            done += 1
            if status_callback and done % 10 == 0:
                status_callback(f"[수집기] {done}/{len(need_fetch)} 완료")

    cache.save()
    print(f"[수집기] 완료: 성공={count} 실패={fail} / {total}종목 (수집={len(need_fetch)})")
    return count


def collect_holdings_data(fetcher, holdings: list) -> int:
    """보유종목 데이터도 창고에 적재."""
    cache = get_cache()
    count = 0

    for h in holdings:
        code = h.get("code", "")
        if not code:
            continue
        if code.startswith("A") and len(code) == 7:
            code = code[1:]

        if _is_cache_fresh(cache, code):
            count += 1
            continue

        try:
            daily = fetcher.get_daily_ohlcv(code, count=100)
            min60 = fetcher.get_minute_ohlcv(code, tick_range=60, count=20)
            min15 = fetcher.get_minute_ohlcv(code, tick_range=15, count=20)
            supply = fetcher.get_supply_demand(code, count=5)
            price = fetcher.get_price(code) or {}

            data = {
                "daily": daily, "min60": min60, "min15": min15,
                "min03": [], "min01": [], "supply": supply,
                "price": price, "financial": {},
            }
            cache.set(f"data_{code}", data, ttl_seconds=86400)
            count += 1
        except Exception as e:
            print(f"[수집기] 보유종목 {code} 오류: {e}")

        time.sleep(0.2)

    cache.save()
    print(f"[수집기] 보유종목 수집 완료: {count}종목")
    return count
