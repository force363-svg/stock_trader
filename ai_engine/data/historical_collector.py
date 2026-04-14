"""
과거 데이터 수집기
- 네이버 금융 → 5년 일봉 OHLCV (API 키 불필요)
- SQLite DB에 저장 (historical_ohlcv 테이블)
"""
import requests
import time
import json
import os
import sys
from datetime import datetime, timedelta

from ..db.database import get_connection


# ──────────────────────────────────────────
#  네이버 금융 API
# ──────────────────────────────────────────
NAVER_CHART_URL = "https://fchart.stock.naver.com/siseJson.nhn"
NAVER_STOCK_LIST_URL = "https://m.stock.naver.com/api/stocks/marketValue"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


class HistoricalCollector:
    """과거 OHLCV 데이터 수집 → DB 저장"""

    def __init__(self, ls_api=None):
        self.ls_api = ls_api
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    # ──────────────────────────────────────
    #  종목 리스트 (네이버 금융)
    # ──────────────────────────────────────
    def _get_stock_list(self, callback=None) -> list:
        """KOSPI + KOSDAQ 전 종목 리스트 조회"""
        stocks = []
        for market in ("KOSPI", "KOSDAQ"):
            page = 1
            while True:
                try:
                    url = f"{NAVER_STOCK_LIST_URL}/{market}?page={page}&pageSize=100"
                    res = requests.get(url, headers=HEADERS, timeout=15)
                    if res.status_code != 200:
                        break
                    data = res.json()
                    items = data.get("stocks", [])
                    if not items:
                        break
                    for item in items:
                        code = item.get("itemCode", "")
                        name = item.get("stockName", "")
                        # 주식만 (ETF/ETN/우선주 제외)
                        end_type = item.get("stockEndType", "")
                        if end_type != "stock":
                            continue
                        if code and len(code) == 6:
                            stocks.append({
                                "code": code,
                                "name": name,
                                "market": market,
                            })
                    total = data.get("totalCount", 0)
                    if page * 100 >= total:
                        break
                    page += 1
                    time.sleep(0.1)
                except Exception as e:
                    print(f"[수집기] {market} 종목리스트 p{page} 오류: {e}")
                    break

            if callback:
                callback(f"[수집기] {market} {len([s for s in stocks if s['market']==market])}종목 로드")

        print(f"[수집기] 전체 종목: {len(stocks)}개 (KOSPI+KOSDAQ)")
        return stocks

    # ──────────────────────────────────────
    #  메인: 전 종목 과거 데이터 수집
    # ──────────────────────────────────────
    def collect_all(self, years: int = 5, callback=None):
        """
        전 종목 과거 데이터 수집 (네이버 금융)
        years: 수집 기간 (년)
        callback: 진행상황 콜백 (message: str)
        """
        self._stop_flag = False

        if callback:
            callback(f"[수집기] {years}년 과거 데이터 수집 시작...")

        # 1) 종목 리스트
        stocks = self._get_stock_list(callback)
        if not stocks:
            if callback:
                callback("[수집기] ❌ 종목 리스트 조회 실패")
            return

        # 2) 종목별 수집
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")

        total = len(stocks)
        success = 0
        skip = 0
        fail = 0

        for i, stock in enumerate(stocks):
            if self._stop_flag:
                if callback:
                    callback("[수집기] ⏹ 중지됨")
                break

            code = stock["code"]
            name = stock["name"]

            # 이미 충분한 데이터가 있으면 스킵
            existing = self._get_stock_data_count(code, start_date, end_date)
            if existing >= years * 200:  # 연 ~250영업일, 200이면 충분
                skip += 1
                continue

            try:
                count = self._fetch_stock_from_naver(code, start_date, end_date)
                if count > 0:
                    success += 1
                else:
                    fail += 1
            except Exception as e:
                fail += 1
                print(f"[수집기] {name}({code}) 오류: {e}")

            # 진행률 표시
            if callback and (i + 1) % 20 == 0:
                pct = (i + 1) * 100 // total
                callback(f"[수집기] {i+1}/{total} ({pct}%) | 성공={success} 스킵={skip} 실패={fail}")

            time.sleep(0.2)  # 네이버 서버 부하 방지

        if callback:
            status = self.get_collect_status()
            callback(f"[수집기] ✅ 완료 | {status['count']:,}건 | "
                     f"성공={success} 스킵={skip} 실패={fail} | "
                     f"{status.get('min_date', '')[:4]}.{status.get('min_date', '')[4:6]}~"
                     f"{status.get('max_date', '')[:4]}.{status.get('max_date', '')[4:6]}")

    # ──────────────────────────────────────
    #  네이버 금융 수집
    # ──────────────────────────────────────
    def _fetch_stock_from_naver(self, code: str, start_date: str, end_date: str) -> int:
        """네이버 금융에서 종목별 일봉 수집 → DB 저장. 반환: 저장 건수"""
        params = {
            "symbol": code,
            "requestType": 1,
            "startTime": start_date,
            "endTime": end_date,
            "timeframe": "day",
        }
        res = requests.get(NAVER_CHART_URL, params=params, headers=HEADERS, timeout=30)
        if res.status_code != 200:
            return 0

        # JS 배열 파싱: ["20260410", 198200, 203000, ...]
        rows = []
        for line in res.text.split("\n"):
            line = line.strip().rstrip(",")
            if not line.startswith('["'):
                continue
            try:
                # ["날짜", 시가, 고가, 저가, 종가, 거래량, 외국인소진율]
                parts = line.strip("[]").split(",")
                date_str = parts[0].strip().strip('"')
                open_p = int(float(parts[1].strip()))
                high_p = int(float(parts[2].strip()))
                low_p = int(float(parts[3].strip()))
                close_p = int(float(parts[4].strip()))
                volume = int(float(parts[5].strip()))
                rows.append((code, date_str, open_p, high_p, low_p, close_p, volume))
            except Exception:
                continue

        if not rows:
            return 0

        # DB 저장
        conn = get_connection()
        try:
            saved = 0
            for row in rows:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO historical_ohlcv
                        (code, date, open, high, low, close, volume,
                         amount, market_cap, shares, source, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, 'NAVER', ?)
                    """, (*row, datetime.now().isoformat()))
                    saved += 1
                except Exception:
                    continue
            conn.commit()
            return saved
        finally:
            conn.close()

    # ──────────────────────────────────────
    #  유틸
    # ──────────────────────────────────────
    def get_collect_status(self) -> dict:
        """현재 수집 상태 조회 (기간, 건수)"""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT MIN(date) as min_d, MAX(date) as max_d, COUNT(*) as cnt "
                "FROM historical_ohlcv"
            ).fetchone()
            if row and row["cnt"] > 0:
                return {
                    "min_date": row["min_d"],
                    "max_date": row["max_d"],
                    "count": row["cnt"],
                }
            return {"min_date": None, "max_date": None, "count": 0}
        finally:
            conn.close()

    def _get_stock_data_count(self, code: str, start_date: str, end_date: str) -> int:
        """특정 종목의 기존 데이터 건수 조회"""
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM historical_ohlcv "
                "WHERE code=? AND date>=? AND date<=?",
                (code, start_date, end_date)
            ).fetchone()
            return row["cnt"] if row else 0
        finally:
            conn.close()

    def get_stats(self) -> dict:
        """수집 현황 통계"""
        conn = get_connection()
        try:
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM historical_ohlcv"
            ).fetchone()["cnt"]
            stocks = conn.execute(
                "SELECT COUNT(DISTINCT code) as cnt FROM historical_ohlcv"
            ).fetchone()["cnt"]
            min_date = conn.execute(
                "SELECT MIN(date) as d FROM historical_ohlcv"
            ).fetchone()["d"]
            max_date = conn.execute(
                "SELECT MAX(date) as d FROM historical_ohlcv"
            ).fetchone()["d"]
            by_source = {}
            for row in conn.execute(
                "SELECT source, COUNT(*) as cnt FROM historical_ohlcv GROUP BY source"
            ).fetchall():
                by_source[row["source"]] = row["cnt"]
            return {
                "total_records": total,
                "total_stocks": stocks,
                "date_range": f"{min_date or '없음'} ~ {max_date or '없음'}",
                "by_source": by_source,
            }
        finally:
            conn.close()

    def get_stock_history(self, code: str, start_date: str = "", end_date: str = "") -> list:
        """특정 종목의 과거 데이터 조회"""
        conn = get_connection()
        try:
            sql = "SELECT * FROM historical_ohlcv WHERE code=?"
            params = [code]
            if start_date:
                sql += " AND date>=?"
                params.append(start_date)
            if end_date:
                sql += " AND date<=?"
                params.append(end_date)
            sql += " ORDER BY date ASC"
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
