"""
1차 필터: 일봉 데이터만으로 종목 유니버스 축소
- 시장/가격/제외종목/거래량 등 기본 필터
- 일봉 이평선 조건 (MA 정배열, 상승추세 등)
- 결과를 filtered_universe.json에 저장
- Scanner는 이 파일에서만 2차 스캔 실행
"""
import json
import os
import sys
import re
import time
from datetime import datetime

from ..data.stock_universe import StockUniverse, is_valid_stock
from ..conditions.ma_alignment import MAAlignmentCondition, _ema, _sma


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_filtered_path():
    base = _get_base_dir()
    if getattr(sys, 'frozen', False):
        exe_name = os.path.basename(sys.executable).lower()
        fname = "filtered_universe_mock.json" if "mock" in exe_name else "filtered_universe_real.json"
    else:
        fname = "filtered_universe.json"
    return os.path.join(base, fname)


def _load_filter_config() -> dict:
    """engine_config에서 primary_filter 섹션 로드"""
    try:
        from ..conditions._config_helper import get_engine_config_path
        path = get_engine_config_path()
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("primary_filter", {})
    except Exception:
        return {}


class PrimaryFilter:
    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.universe = StockUniverse(fetcher)
        self._ma_cond = MAAlignmentCondition()

    def run_filter(self, status_callback=None) -> list:
        """
        1차 필터 실행 (우선순위)
        1. xingAPI 창고 파일 (warehouse_*.json) — ACF 조건검색 결과
        2. 서버 조건검색 (t1859) — REST API
        3. 미설정 시 빈 리스트
        """
        config = _load_filter_config()
        if not config.get("enabled", True):
            if status_callback:
                status_callback("[1차필터] 비활성 — 전체 유니버스 사용")
            return self.universe.get_stocks()

        # ── xingAPI 창고 파일 (t1857 조건검색 결과) ──
        warehouse = self._load_warehouse()
        if warehouse:
            if status_callback:
                status_callback(f"[1차필터] 창고에서 {len(warehouse)}종목 로드")
            return warehouse

        # 창고 없으면 빈 리스트
        if status_callback:
            status_callback("[1차필터] 창고 없음 — xingAPI 조건검색 대기 중")
        return []

    def _load_warehouse(self) -> list:
        """xingAPI 창고 파일에서 종목 로드"""
        try:
            base = _get_base_dir()
            # 모의/실전 자동 감지
            if getattr(sys, 'frozen', False):
                exe_name = os.path.basename(sys.executable).lower()
                mode = "mock" if "mock" in exe_name else "real"
            else:
                mode = "mock"

            path = os.path.join(base, f"warehouse_{mode}.json")
            if not os.path.exists(path):
                return []

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            stocks = data.get("stocks", [])
            if not stocks:
                return []

            # 우리 포맷으로 변환
            result = []
            for s in stocks:
                result.append({
                    "code": s.get("code", ""),
                    "name": s.get("name", ""),
                    "market": "",
                    "price": s.get("price", 0),
                })

            updated = data.get("updated", "?")
            print(f"[1차필터] 창고 로드: {len(result)}종목 (갱신: {updated})")
            return result
        except Exception as e:
            print(f"[1차필터] 창고 로드 실패: {e}")
            return []

    def _run_server_condition(self, query_index, cond_name, status_callback=None) -> list:
        """서버 조건검색(t1859)으로 1차 필터 실행 — 몇 초면 완료"""
        if status_callback:
            status_callback(f"[1차필터] 서버 조건검색 실행 중... [{cond_name}]")

        try:
            results = self.fetcher.api.run_condition_search(query_index)
        except Exception as e:
            if status_callback:
                status_callback(f"[1차필터] ❌ 서버 조건검색 실패: {e} → 기존 필터로 전환")
            return self.run_filter_legacy(status_callback)

        if not results:
            if status_callback:
                status_callback("[1차필터] ⚠ 서버 조건검색 결과 0종목 → 기존 필터로 전환")
            return self.run_filter_legacy(status_callback)

        # 결과를 우리 포맷으로 변환
        filtered = []
        for item in results:
            filtered.append({
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "market": "",
                "price": 0,
            })

        # 결과 저장
        self._save_filtered(filtered, total=0, phase1=0, fail_counts={"server_condition": cond_name})

        if status_callback:
            status_callback(
                f"[1차필터] ✅ 서버 조건검색 완료: [{cond_name}] → {len(filtered)}종목 선별"
            )

        return filtered

    def run_filter_legacy(self, status_callback=None) -> list:
        """기존 1차 필터 (서버 조건검색 실패 시 폴백)"""
        config = _load_filter_config()
        # use_server_condition 무시하고 기존 로직 실행
        config["use_server_condition"] = False
        return self._run_local_filter(config, status_callback)

    def _run_local_filter(self, config, status_callback=None) -> list:
        """기존 일봉 기반 로컬 필터 실행"""
        # 설정값 로드
        market = str(config.get("market", "0"))
        price_min = int(config.get("price_min", 1000))
        price_max = int(config.get("price_max", 500000))
        min_vol_5d = int(config.get("min_volume_5d", 10000))
        min_amount = int(config.get("min_amount_1d", 10))
        min_amount_won = min_amount * 100_000_000
        conditions = [c for c in config.get("conditions", []) if c.get("enabled", True)]

        ma_names = set()
        for c in conditions:
            n = c["name"]
            if re.search(r'(\d+일선|EMA\d+|ema\d+|종가\s*>|\d+선?\s*>|\d+\s*상승)', n):
                ma_names.add(n)

        if status_callback:
            status_callback("[1차필터] 종목 유니버스 로드 중...")

        all_stocks = self.universe.get_stocks()
        if not all_stocks:
            if status_callback:
                status_callback("[1차필터] ❌ 종목 로드 실패")
            return []

        total = len(all_stocks)
        if status_callback:
            status_callback(f"[1차필터] {total}종목 로드 → 기본 필터 적용 중...")

        phase1 = []
        for s in all_stocks:
            code = s.get("code", "")
            name = s.get("name", "")
            price = int(s.get("price", 0))
            s_market = s.get("market", "")
            if market == "1" and s_market != "KOSPI":
                continue
            if market == "2" and s_market != "KOSDAQ":
                continue
            if not (price_min <= price <= price_max):
                continue
            if not is_valid_stock(code, name, price):
                continue
            phase1.append(s)

        if status_callback:
            status_callback(f"[1차필터] 기본 필터: {total} → {len(phase1)}종목 | 일봉 분석 시작...")

        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        filtered = []
        fail_counts = {}
        _lock = threading.Lock()
        _processed = [0]

        def _check_stock(s):
            code = s.get("code", "")
            try:
                daily = self.fetcher.get_daily_ohlcv(code, count=220)
            except Exception:
                return None, None
            if not daily or len(daily) < 5:
                return None, None
            avg_vol = sum(d.get("volume", 0) for d in daily[:5]) / 5
            if avg_vol < min_vol_5d:
                return None, "low_volume"
            try:
                today_amt = daily[0].get("close", 0) * daily[0].get("volume", 0)
                yest_amt = daily[1].get("close", 0) * daily[1].get("volume", 0) if len(daily) >= 2 else 0
                if today_amt < min_amount_won and yest_amt < min_amount_won:
                    return None, "low_amount"
            except Exception:
                pass
            if self._check_abnormal(daily):
                return None, "abnormal"
            if ma_names:
                data = {"daily": daily}
                try:
                    if not self._ma_cond.check_screening(code, data, enabled_names=ma_names):
                        return None, "ma_fail"
                except Exception:
                    pass
            return s, None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_check_stock, s): s for s in phase1}
            for future in as_completed(futures):
                with _lock:
                    _processed[0] += 1
                    cnt = _processed[0]
                if status_callback and cnt % 200 == 0:
                    status_callback(
                        f"[1차필터] 일봉 분석 중... {cnt}/{len(phase1)} "
                        f"(통과: {len(filtered)}종목)"
                    )
                try:
                    result, reason = future.result()
                    if result is not None:
                        filtered.append(result)
                    elif reason:
                        with _lock:
                            fail_counts[reason] = fail_counts.get(reason, 0) + 1
                except Exception:
                    pass

        self._save_filtered(filtered, total, len(phase1), fail_counts)
        if status_callback:
            status_callback(
                f"[1차필터] ✅ 완료: {total} → {len(phase1)} → {len(filtered)}종목 선별"
            )
        return filtered

    def _check_abnormal(self, daily: list) -> bool:
        """비정상 급등 감지 (scanner와 동일 로직)"""
        try:
            current = daily[0].get("close", 0)
            if current <= 0:
                return True

            # 200일 평균 대비 3배
            if len(daily) >= 200:
                avg = sum(d["close"] for d in daily[:200]) / 200
                if avg > 0 and current > avg * 3:
                    return True

            # 60일 평균 대비 2.5배
            if len(daily) >= 60:
                avg = sum(d["close"] for d in daily[:60]) / 60
                if avg > 0 and current > avg * 2.5:
                    return True

            # 20일 평균 대비 2배
            if len(daily) >= 20:
                avg = sum(d["close"] for d in daily[:20]) / 20
                if avg > 0 and current > avg * 2:
                    return True
        except Exception:
            pass
        return False

    def _save_filtered(self, stocks: list, total: int, phase1: int, fail_counts: dict):
        """필터 결과를 JSON 파일에 저장"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "total_universe": total,
                "phase1_count": phase1,
                "filtered_count": len(stocks),
                "fail_summary": fail_counts,
                "stocks": [
                    {
                        "code": s.get("code", ""),
                        "name": s.get("name", ""),
                        "market": s.get("market", ""),
                        "price": s.get("price", 0)
                    }
                    for s in stocks
                ]
            }
            path = _get_filtered_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def load_filtered() -> list | None:
        """
        filtered_universe.json에서 필터된 종목 로드
        반환: [{"code", "name", "market", "price"}, ...] 또는 None (파일 없음/만료)
        """
        try:
            path = _get_filtered_path()
            if not os.path.exists(path):
                return None
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 24시간 이상 지나면 만료
            ts = data.get("timestamp", "")
            if ts:
                dt = datetime.fromisoformat(ts)
                if (datetime.now() - dt).total_seconds() > 86400:
                    return None
            stocks = data.get("stocks", [])
            return stocks if stocks else None
        except Exception:
            return None
