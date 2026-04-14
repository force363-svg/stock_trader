"""
모의투자 전용 Worker 스레드
- XingWorker: COM 전용 (로그인, t1857 ACF, t0424 보유종목, t1511 지수)
- MarketWorker: LS REST (테마, 업종)
- TradeWorker: LS REST (매수/매도 주문, 미체결 관리)
"""
import sys
import os
import json
import time
import threading
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal, QMutex

from config import load_config, save_config


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _get_mode():
    if getattr(sys, 'frozen', False):
        exe = os.path.basename(sys.executable).lower()
        return "mock" if "mock" in exe else "real"
    return "mock"


# ─────────────────────────────────────────────
#  XingWorker — COM 전용 스레드
# ─────────────────────────────────────────────
class XingWorker(QThread):
    """xingAPI COM 객체를 소유하는 전용 스레드"""

    # Signals → UI
    login_result    = pyqtSignal(bool, str, object)   # ok, msg, xing_obj
    acf_updated     = pyqtSignal(list)                 # [{code, name, price, ...}]
    holdings_updated = pyqtSignal(list, dict)          # [ui_holdings], account_summary
    index_updated   = pyqtSignal(str, object)          # name, data
    status          = pyqtSignal(str)                  # 상태 메시지

    def __init__(self, user_id="", password="", cert_pw="", cert_dir="",
                 login_mode="mock", acf_path=""):
        super().__init__()
        self._running = False
        self._user_id = user_id
        self._password = password
        self._cert_pw = cert_pw
        self._cert_dir = cert_dir
        self._login_mode = login_mode
        self._acf_path = acf_path
        self._xing = None

    def run(self):
        """COM 초기화 → 로그인 → 주기적 데이터 갱신"""
        import pythoncom
        pythoncom.CoInitialize()
        self._running = True

        try:
            # 로그인
            from xing_api import XingAPI
            self._xing = XingAPI()
            ok, msg = self._xing.login(
                self._user_id, self._password,
                mode=self._login_mode,
                cert_password=self._cert_pw,
                cert_path=self._cert_dir
            )
            self.login_result.emit(ok, msg, self._xing if ok else None)
            if not ok:
                self.status.emit(f"[XING] 로그인 실패: {msg}")
                return

            self.status.emit(f"[XING] 로그인 성공 ({self._login_mode})")

            # 초기 ACF 스캔
            if self._acf_path:
                self._do_acf_scan()

            # 초기 지수 조회
            self._do_index()

            # 메인 루프
            acf_tick = 0
            holdings_tick = 0
            index_tick = 0
            acf_first = True  # 시작 시 1회 무조건 실행

            while self._running:
                try:
                    now = datetime.now()
                    now_hm = now.strftime("%H:%M")
                    is_market_hours = (now.weekday() < 5 and "09:00" <= now_hm <= "15:30")

                    # ACF 조건검색 (10초, 시작 시 1회는 장외에도 실행)
                    acf_tick += 1
                    if (acf_tick >= 10 or acf_first) and self._acf_path and (is_market_hours or acf_first):
                        acf_tick = 0
                        acf_first = False
                        self._do_acf_scan()

                    # 보유종목 (3초) - LS REST API 사용
                    holdings_tick += 1
                    if holdings_tick >= 3:
                        holdings_tick = 0
                        self._do_holdings()

                    # 업종지수 (60초)
                    index_tick += 1
                    if index_tick >= 60:
                        index_tick = 0
                        self._do_index()

                except Exception as e:
                    self.status.emit(f"[XING] 루프 오류: {e}")

                time.sleep(1)

        except Exception as e:
            self.status.emit(f"[XING] 치명적 오류: {e}")
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    def _do_acf_scan(self):
        """t1857 ACF 조건검색"""
        try:
            stocks = self._xing.run_full_scan(self._acf_path)
            if stocks is not None:
                self.acf_updated.emit(stocks)
                # 가격 캐시 갱신
                self._update_price_cache(stocks)
                self.status.emit(f"[XING] ACF: {len(stocks)}종목")
        except Exception as e:
            self.status.emit(f"[XING] ACF 오류: {e}")

    def _update_price_cache(self, stocks):
        """t1857 결과의 실시간 가격을 AI 캐시에 반영"""
        try:
            from ai_engine.data.cache import get_cache
            cache = get_cache()
            for s in stocks:
                code = s["code"]
                if code.startswith("A") and len(code) == 7:
                    code = code[1:]
                cached = cache.get(f"data_{code}")
                if cached and "price" in cached:
                    cached["price"]["price"] = s.get("price", cached["price"].get("price", 0))
                    cached["price"]["change"] = s.get("change", cached["price"].get("change", 0))
                    cached["price"]["diff"] = s.get("diff", cached["price"].get("diff", 0))
                    cached["price"]["volume"] = s.get("volume", cached["price"].get("volume", 0))
                    cache.set(f"data_{code}", cached, ttl_seconds=86400)
            cache.save()
        except Exception:
            pass

    def _do_holdings(self):
        """LS REST API로 보유종목 조회"""
        try:
            from ls_api import LSApi
            api = LSApi(mode=self._login_mode)
            if not api.get_token():
                return
            ui_holdings, summary = api.get_holdings_for_ui()
            if ui_holdings is not None:
                self.holdings_updated.emit(ui_holdings, summary or {})
        except Exception as e:
            self.status.emit(f"[보유종목] 오류: {e}")

    def _do_index(self):
        """LS REST API로 KOSPI/KOSDAQ 지수"""
        try:
            from ls_api import LSApi
            api = LSApi(mode=self._login_mode)
            if not api.get_token():
                return
            kospi = api.get_market_index("001")
            if kospi:
                self.index_updated.emit("KOSPI", kospi)
            kosdaq = api.get_market_index("301")
            if kosdaq:
                self.index_updated.emit("KOSDAQ", kosdaq)
        except Exception:
            pass

    def get_xing(self):
        return self._xing

    def get_server_conditions(self):
        """서버 조건검색 목록 (UI에서 호출)"""
        if self._xing:
            return self._xing.get_server_conditions()
        return []

    def stop(self):
        self._running = False


# ─────────────────────────────────────────────
#  MarketWorker — LS REST (테마, 업종)
# ─────────────────────────────────────────────
class MarketWorker(QThread):
    """테마/업종 데이터를 LS REST API로 주기적 수집"""

    theme_updated  = pyqtSignal(list)    # [{name, code, diff, diff_str, ...}]
    sector_updated = pyqtSignal(list)    # [{name, change, ...}]
    status         = pyqtSignal(str)

    def __init__(self, mode="mock"):
        super().__init__()
        self._running = False
        self._mode = mode

    def run(self):
        self._running = True
        self.status.emit("[마켓] 시작")

        while self._running:
            try:
                from ls_api import LSApi
                api = LSApi(mode=self._mode)
                if api.get_token():
                    # 업종지수
                    sectors = api.get_sector_indices()
                    if sectors:
                        self.sector_updated.emit(sectors)

                    # 상승테마
                    themes = api.get_themes()
                    if themes:
                        self.theme_updated.emit(themes)
                        self._save_theme_cache(themes)

            except Exception as e:
                self.status.emit(f"[마켓] 오류: {e}")

            # 5분 간격 (1초씩 체크하여 stop 반응성 유지)
            for _ in range(300):
                if not self._running:
                    break
                time.sleep(1)

        self.status.emit("[마켓] 종료")

    def _save_theme_cache(self, themes):
        """테마 데이터를 AI 캐시에 저장"""
        try:
            from ai_engine.conditions.theme_sector import save_market_cache
            theme_list = [
                {"name": t.get("name", ""), "code": t.get("code", ""), "diff": t.get("diff", 0.0)}
                for t in themes[:20]
            ]
            save_market_cache(themes=theme_list, theme_stocks={})
        except Exception:
            pass

    def stop(self):
        self._running = False


# ─────────────────────────────────────────────
#  TradeWorker — LS REST (주문 처리)
# ─────────────────────────────────────────────
class TradeWorker(QThread):
    """자동매매 사이클: AI 신호 기반 매수/매도"""

    order_result = pyqtSignal(str, dict)     # action, result_info
    log_message  = pyqtSignal(str)           # 매매 로그
    holdings_changed = pyqtSignal()          # 잔고 갱신 요청

    def __init__(self, mode="mock"):
        super().__init__()
        self._running = False
        self._trading = False
        self._mode = mode
        self._api = None

        # 매매 상태
        self._profit_sold_stages = {}
        self._pending_buy_orders = {}
        self._pending_sell_orders = {}
        self._loss_cut_stages = {}
        self._ai_exclude_codes = set()
        self._holdings_data = []
        self._ai_signals = []

    def run(self):
        self._running = True
        self._load_state()
        self.log_message.emit("[매매] Worker 시작")

        while self._running:
            if self._trading and self._api:
                try:
                    self._trade_cycle()
                except Exception as e:
                    self.log_message.emit(f"[매매] 오류: {e}")
            time.sleep(10)

        self.log_message.emit("[매매] Worker 종료")

    def set_trading(self, active: bool):
        """자동매매 ON/OFF"""
        self._trading = active
        if active:
            self._init_api()

    def set_holdings(self, holdings: list):
        self._holdings_data = holdings

    def set_signals(self, signals: list):
        self._ai_signals = signals

    def set_exclude_codes(self, codes: set):
        self._ai_exclude_codes = codes

    def _init_api(self):
        try:
            from ls_api import LSApi
            self._api = LSApi(mode=self._mode)
            if not self._api.get_token():
                self.log_message.emit("[매매] API 토큰 발급 실패")
                self._api = None
        except Exception as e:
            self.log_message.emit(f"[매매] API 초기화 실패: {e}")
            self._api = None

    def _trade_cycle(self):
        """10초마다 실행 — AI 신호 체크 → 매수/매도"""
        now = datetime.now().strftime("%H:%M:%S")
        config = load_config()

        # 매매 시간 체크
        start_time = config["account"]["start_time"]
        end_time = config["account"]["end_time"]
        current_time = datetime.now().strftime("%H:%M")
        if current_time < start_time or current_time > end_time:
            # 장 마감 후 리포트
            if current_time > end_time and not getattr(self, '_daily_report_done', False):
                self._daily_report_done = True
                try:
                    from ai_engine.learning.report_generator import generate_report
                    path = generate_report(days=30)
                    if path:
                        self.log_message.emit(f"[{now}] 일일 리포트: {os.path.basename(path)}")
                except Exception:
                    pass
            return
        self._daily_report_done = False

        if not self._api or not self._api.ensure_token():
            return

        # ── 매수 ──
        buy_amount = config["account"]["buy_amount"]
        max_stocks = config["account"]["max_stocks"]
        held_codes = {h["raw_code"] for h in self._holdings_data}

        if len(held_codes) < max_stocks:
            buy_candidates = [s for s in self._ai_signals if s.get("signal_type") == "BUY"]
            if buy_candidates:
                available_cash = self._api.get_available_cash()
                if available_cash <= 0:
                    self.log_message.emit(f"[{now}] 주문가능금액 없음")
                else:
                    def _rank_score(s):
                        return (s.get("score", 0) * 0.50
                                + s.get("supply_score", 0) * 0.25
                                + s.get("chart_score", 0) * 0.15
                                + s.get("material_score", 0) * 0.10)

                    recommended = sorted(buy_candidates, key=_rank_score, reverse=True)[:10]

                    for sig in recommended:
                        code = sig.get("stock_code", "")
                        name = sig.get("stock_name", "")
                        price = sig.get("current_price", 0)
                        if not code or not price or code in held_codes:
                            continue
                        if self._is_rebuy_blocked(code):
                            continue
                        actual_amount = min(buy_amount, available_cash)
                        qty = actual_amount // price
                        if qty <= 0:
                            continue

                        self.log_message.emit(
                            f"[{now}] AI매수: {name}({code}) "
                            f"점수:{sig['score']:.1f} → {qty}주"
                        )
                        result = self._api.buy_order(code, qty, price=0)
                        if result:
                            self.log_message.emit(f"[{now}] 매수 체결: {name} {qty}주")
                            self.holdings_changed.emit()
                            available_cash -= qty * price
                            try:
                                from ai_engine.learning.trade_recorder import TradeRecorder
                                TradeRecorder().record_buy(code, name, price, qty, sig.get("score", 0), sig.get("conditions", {}))
                            except Exception:
                                pass
                            held_codes.add(code)
                        else:
                            self.log_message.emit(f"[{now}] 매수 실패: {name}")
                        if len(held_codes) >= max_stocks or available_cash <= 0:
                            break

        # ── AI 매도 ──
        sell_signals = {}
        for s in self._ai_signals:
            if s.get("signal_type") == "SELL":
                sc = s["stock_code"]
                sell_signals[sc] = s
                if sc.startswith("A") and len(sc) == 7:
                    sell_signals[sc[1:]] = s
                else:
                    sell_signals["A" + sc] = s

        for h in self._holdings_data:
            if h["raw_code"] in self._ai_exclude_codes:
                continue
            if h["raw_code"] in sell_signals:
                sig = sell_signals[h["raw_code"]]
                reasons = sig.get("sell_reason", "")
                self.log_message.emit(f"[{now}] AI매도: {h['name']} [{reasons}]")
                self._do_sell(h["name"], h["raw_code"], h["raw_qty"])

        # ── 미체결 관리 ──
        self._manage_unfilled(now)

        # ── 분할 손절/익절 ──
        self._check_profit_loss(now, config)

    def _do_sell(self, name, code, qty):
        """매도 주문"""
        now = datetime.now().strftime("%H:%M:%S")
        if not self._api:
            return
        result = self._api.sell_order(code, qty, price=0)
        if result:
            self.log_message.emit(f"[{now}] 매도 체결: {name} {qty}주")
            self.holdings_changed.emit()
            self._record_sell_time(code)
            try:
                from ai_engine.learning.trade_recorder import TradeRecorder
                sell_price = 0
                for h in self._holdings_data:
                    if h.get("raw_code") == code:
                        sell_price = h.get("raw_cur_price", 0)
                        break
                if sell_price > 0:
                    TradeRecorder().record_sell(code, sell_price, qty)
            except Exception:
                pass
        else:
            self.log_message.emit(f"[{now}] 매도 실패: {name}")

    def _manage_unfilled(self, now):
        """미체결 주문 관리"""
        if not self._api:
            return
        try:
            unfilled = self._api.get_unfilled_orders()
        except Exception:
            return
        if not unfilled:
            cnt = getattr(self, '_uf_empty', 0) + 1
            self._uf_empty = cnt
            if cnt >= 3:
                self._pending_buy_orders.clear()
                self._pending_sell_orders.clear()
                self._uf_empty = 0
            return
        self._uf_empty = 0
        current_ts = datetime.now()

        for order in unfilled:
            ono = order["order_no"]
            code = order["stock_code"]
            name = order.get("stock_name", code)
            unf_qty = order["unfilled_qty"]

            if order["bns_type"] == "SELL":
                if ono not in self._pending_sell_orders:
                    self._pending_sell_orders[ono] = {
                        "code": code, "name": name, "time": current_ts, "qty": unf_qty, "retry": 0
                    }
                info = self._pending_sell_orders[ono]
                elapsed = (current_ts - info["time"]).total_seconds()
                if elapsed >= 3 and info["retry"] < 3:
                    self.log_message.emit(f"[{now}] 매도 하향추적: {name} {unf_qty}주")
                    cancel_result = self._api.cancel_order(ono, code, unf_qty)
                    if cancel_result:
                        self._api.sell_order(code, unf_qty, price=0)
                    info["retry"] += 1
                    info["time"] = current_ts

            elif order["bns_type"] == "BUY":
                if ono not in self._pending_buy_orders:
                    self._pending_buy_orders[ono] = {
                        "code": code, "name": name, "time": current_ts, "qty": unf_qty
                    }
                info = self._pending_buy_orders[ono]
                elapsed = (current_ts - info["time"]).total_seconds()
                if elapsed >= 900:
                    self.log_message.emit(f"[{now}] 매수 미체결 취소: {name} {unf_qty}주")
                    self._api.cancel_order(ono, code, unf_qty)
                    self._pending_buy_orders.pop(ono, None)

        active = {o["order_no"] for o in unfilled}
        for ono in list(self._pending_sell_orders):
            if ono not in active:
                del self._pending_sell_orders[ono]
        for ono in list(self._pending_buy_orders):
            if ono not in active:
                del self._pending_buy_orders[ono]

    def _check_profit_loss(self, now, config):
        """분할 손절 + 수익 정산"""
        loss_stages_raw = config["profit"].get("loss_stages", [(-3.0, 33.0), (-5.0, 33.0), (-7.0, 100.0)])
        loss_stages = [(t, r / 100.0) for t, r in loss_stages_raw]
        profit_stages = config["profit"]["profit_stages"]
        sell_ratios = config["profit"].get("sell_ratios", [20.0] * 5)
        loss_cut = config["profit"].get("loss_cut", 0.0)

        held_code_set = {h["raw_code"] for h in self._holdings_data}
        changed = False
        for code in list(self._profit_sold_stages.keys()):
            if code not in held_code_set:
                del self._profit_sold_stages[code]
                changed = True
        for code in list(self._loss_cut_stages.keys()):
            if code not in held_code_set:
                del self._loss_cut_stages[code]
        if changed:
            self._save_profit_stages()

        for h in self._holdings_data:
            try:
                pnl = float(h["pnl_rate"].replace("%", "").replace("+", ""))
                code = h["raw_code"]

                # 분할 손절
                done_loss = self._loss_cut_stages.get(code, -1)
                loss_handled = False
                for i, (threshold, ratio) in enumerate(loss_stages):
                    if i <= done_loss:
                        continue
                    if pnl <= threshold:
                        sell_qty = h["raw_qty"] if ratio >= 1.0 else max(1, int(h["raw_qty"] * ratio))
                        tag = "전량" if ratio >= 1.0 else f"{ratio:.0%}"
                        self.log_message.emit(
                            f"[{now}] 분할손절 {i+1}차({threshold}%): {h['name']} → {sell_qty}주({tag})"
                        )
                        self._do_sell(h["name"], code, sell_qty)
                        self._loss_cut_stages[code] = i
                        loss_handled = True
                        break
                if loss_handled:
                    continue

                if loss_cut > 0 and pnl <= -loss_cut and code not in self._loss_cut_stages:
                    self.log_message.emit(f"[{now}] 손절: {h['name']} ({h['pnl_rate']}) → 전량매도")
                    self._do_sell(h["name"], code, h["raw_qty"])
                    continue

                # 수익 정산
                done_stage = self._profit_sold_stages.get(code, -1)
                for i, stage in reversed(list(enumerate(profit_stages))):
                    if i <= done_stage:
                        break
                    if stage <= 0:
                        continue
                    if pnl >= stage:
                        ratio = sell_ratios[i] if i < len(sell_ratios) else 20.0
                        if ratio <= 0:
                            continue
                        sell_qty = max(1, int(h["raw_qty"] * ratio / 100))
                        self.log_message.emit(
                            f"[{now}] 수익정산 {i+1}차: {h['name']} ({h['pnl_rate']}) → {sell_qty}주({ratio:.0f}%)"
                        )
                        self._do_sell(h["name"], code, sell_qty)
                        self._profit_sold_stages[code] = i
                        self._save_profit_stages()
                        break
            except Exception:
                pass

    # ── 상태 파일 I/O ──
    def _load_state(self):
        base = _get_base_dir()
        self._profit_sold_stages = self._load_profit_stages()
        self._ai_exclude_codes = self._load_ai_exclude()

    def _profit_stages_path(self):
        return os.path.join(_get_base_dir(), "profit_stages.json")

    def _load_profit_stages(self) -> dict:
        try:
            path = self._profit_stages_path()
            if not os.path.exists(path):
                return {}
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") != datetime.now().strftime("%Y-%m-%d"):
                return {}
            return data.get("stages", {})
        except Exception:
            return {}

    def _save_profit_stages(self):
        try:
            data = {"date": datetime.now().strftime("%Y-%m-%d"), "stages": self._profit_sold_stages}
            with open(self._profit_stages_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _sell_times_path(self):
        return os.path.join(_get_base_dir(), "sell_times.json")

    def _load_sell_times(self) -> dict:
        try:
            path = self._sell_times_path()
            if not os.path.exists(path):
                return {}
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") != datetime.now().strftime("%Y-%m-%d"):
                return {}
            return data.get("sells", {})
        except Exception:
            return {}

    def _record_sell_time(self, code: str):
        try:
            sells = self._load_sell_times()
            sells[code] = datetime.now().strftime("%H:%M:%S")
            data = {"date": datetime.now().strftime("%Y-%m-%d"), "sells": sells}
            with open(self._sell_times_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _is_rebuy_blocked(self, code: str) -> bool:
        try:
            from ai_engine.conditions._config_helper import load_defaults
            cooldown = int(load_defaults().get("rebuy_cooldown_min", 30))
            if cooldown <= 0:
                return False
            sells = self._load_sell_times()
            st = sells.get(code)
            if not st:
                return False
            sell_time = datetime.strptime(
                f"{datetime.now().strftime('%Y-%m-%d')} {st}", "%Y-%m-%d %H:%M:%S"
            )
            return (datetime.now() - sell_time).total_seconds() / 60 < cooldown
        except Exception:
            return False

    def _load_ai_exclude(self) -> set:
        try:
            path = os.path.join(_get_base_dir(), "ai_exclude.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return set(json.load(f))
        except Exception:
            pass
        return set()

    def stop(self):
        self._running = False
