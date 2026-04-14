"""
모의투자 전용 프로그램 — Worker Thread 분리 설계
- UI: 표시 전용 (API 호출 없음)
- XingWorker: COM (로그인, ACF, 보유종목, 지수)
- MarketWorker: REST (테마, 업종)
- AI Scanner: 기존 ScannerThread (ai_signals.json 독점)
- TradeWorker: REST (매수/매도)
"""
import sys
import os
import json
import time
import ctypes
import ctypes.wintypes
import threading
from datetime import datetime
from config import load_config, save_config
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QTabWidget, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout, QFrame,
    QScrollArea, QSizePolicy, QProgressBar, QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QPen, QFontMetrics

from mock_workers import XingWorker, MarketWorker, TradeWorker, _get_base_dir, _get_mode


# ─────────────────────────────────────────────
#  테마 & 스타일
# ─────────────────────────────────────────────
_THEME = {
    "mock": {
        "bg":      "#1c1c2e", "panel":  "#2a2a3e", "accent": "#3d3d60",
        "border":  "#5a5a8a", "btn":    "#4a4a80", "btn_hv": "#4e4e7a",
        "pressed": "#2a2a50", "scroll": "#1c1c2e", "chk":    "#4a4a80",
        "tab_sel": "#4a4a80", "arrow":  "#a0a0d0", "focus":  "#8080c0",
        "alt_row": "#33334f", "text":   "#e8e8ff",
    },
}

def build_style():
    c = _THEME["mock"]
    return f"""
QMainWindow, QWidget {{
    background-color: {c['bg']}; color: {c['text']};
    font-family: '맑은 고딕', Arial; font-size: 13px;
}}
QLabel {{ color: {c['text']}; }}
QPushButton {{
    background-color: {c['accent']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 4px; padding: 6px 12px; font-size: 12px;
}}
QPushButton:hover {{ background-color: {c['btn_hv']}; color: #ffffff; }}
QPushButton:pressed {{ background-color: {c['pressed']}; }}
QPushButton#btn_start {{
    background-color: #00b894; color: #ffffff; border: none; font-weight: bold;
}}
QPushButton#btn_start:hover {{ background-color: #00cec9; }}
QPushButton#btn_stop {{
    background-color: #d63031; color: #ffffff; border: none; font-weight: bold;
}}
QPushButton#btn_stop:hover {{ background-color: #e17055; }}
QPushButton#btn_settings {{
    background-color: {c['btn']}; color: #ffffff; border: none;
    font-weight: bold; padding: 6px 16px;
}}
QPushButton#btn_settings:hover {{ background-color: {c['btn_hv']}; }}
QTableWidget {{
    background-color: {c['panel']}; color: {c['text']};
    border: 1px solid {c['border']}; gridline-color: {c['border']};
    selection-background-color: {c['accent']};
}}
QTableWidget::item {{ padding: 4px; }}
QHeaderView::section {{
    background-color: {c['accent']}; color: {c['text']};
    padding: 6px; border: 1px solid {c['border']}; font-weight: bold; font-size: 12px;
}}
QTabWidget::pane {{ border: 1px solid {c['border']}; background-color: {c['panel']}; }}
QTabBar::tab {{
    background-color: {c['bg']}; color: {c['text']};
    padding: 8px 16px; border: 1px solid {c['border']}; border-bottom: none;
}}
QTabBar::tab:selected {{ background-color: {c['tab_sel']}; color: #ffffff; }}
QTabBar::tab:hover {{ background-color: {c['accent']}; color: #ffffff; }}
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {c['accent']}; color: {c['text']};
    border: 1px solid {c['border']}; border-radius: 4px; padding: 4px 8px;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border; subcontrol-position: top right;
    width: 20px; border-left: 1px solid {c['border']}; background-color: {c['panel']};
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 20px; border-left: 1px solid {c['border']}; background-color: {c['panel']};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    width: 0; height: 0;
    border-left: 5px solid transparent; border-right: 5px solid transparent;
    border-bottom: 6px solid {c['arrow']};
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    width: 0; height: 0;
    border-left: 5px solid transparent; border-right: 5px solid transparent;
    border-top: 6px solid {c['arrow']};
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {c['focus']};
}}
QGroupBox {{
    border: 1px solid {c['border']}; border-radius: 6px;
    margin-top: 10px; padding-top: 10px;
    color: {c['text']}; font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 10px; padding: 0 5px; color: {c['text']};
}}
QScrollBar:vertical {{ background-color: {c['scroll']}; width: 8px; }}
QScrollBar::handle:vertical {{ background-color: {c['border']}; border-radius: 4px; }}
QCheckBox {{ color: {c['text']}; spacing: 6px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {c['border']}; border-radius: 3px;
    background-color: {c['panel']};
}}
QCheckBox::indicator:checked {{ background-color: {c['chk']}; }}
QProgressBar {{
    background-color: {c['panel']}; border: none;
    border-radius: 4px; height: 8px; text-align: center;
}}
QProgressBar::chunk {{ background-color: #00b894; border-radius: 4px; }}
QDialog {{ background-color: {c['bg']}; color: {c['text']}; }}
"""

DARK_STYLE = build_style()


# ─────────────────────────────────────────────
#  engine_config 파일명
# ─────────────────────────────────────────────
def get_engine_config_filename():
    return "engine_config_mock.json"


# ─────────────────────────────────────────────
#  SettingsDialog — main.py에서 그대로 import
# ─────────────────────────────────────────────
# main.py의 SettingsDialog를 직접 가져오지 않고 동일 코드를 사용
# (main.py를 import하면 실전투자 코드도 로드되므로 피함)
# → main.py의 SettingsDialog 클래스를 별도 파일로 분리하면 이상적이나,
#   main.py 수정 금지 원칙에 따라 여기에 필요한 부분만 복사

# SettingsDialog는 main.py에서 그대로 사용 (import 경로 우회)
# 아래에서 _import_settings_dialog() 함수로 동적 import
_cached_settings_cls = None

def _get_settings_dialog_class():
    """main.py에서 SettingsDialog만 가져오기 (실행 방지)"""
    global _cached_settings_cls
    if _cached_settings_cls is not None:
        return _cached_settings_cls

    import importlib.util
    # frozen 환경: _internal/ 안에 main.py 존재
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
        main_path = os.path.join(base, "_internal", "main.py")
    else:
        main_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")

    if not os.path.exists(main_path):
        raise FileNotFoundError(f"main.py not found: {main_path}")

    spec = importlib.util.spec_from_file_location(
        "main_settings", main_path, submodule_search_locations=[]
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = "main_settings"
    mod.__file__ = spec.origin
    spec.loader.exec_module(mod)

    # Mock용 설정 파일 경로로 오버라이드
    mod.get_engine_config_filename = get_engine_config_filename

    # 설정창 스타일을 흰색/검정으로 교체
    mod.DARK_STYLE = MockMainWindow._SETTINGS_STYLE

    _cached_settings_cls = mod.SettingsDialog
    return _cached_settings_cls


# ─────────────────────────────────────────────
#  AI 토글 스위치
# ─────────────────────────────────────────────
class AIToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._enabled = True
        self._stopping = False
        self.setFixedSize(68, 20)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, val: bool):
        self._checked = val
        self._stopping = False
        self.setEnabled(True)
        self.update()

    def setStopping(self):
        self._stopping = True
        self.setEnabled(False)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._enabled:
            self._checked = not self._checked
            self.update()
            self.toggled.emit(self._checked)

    def setEnabled(self, val: bool):
        self._enabled = val
        super().setEnabled(val)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h // 2
        if self._stopping:
            track_color = QColor("#636e72")
        elif self._checked:
            track_color = QColor("#00b894")
        else:
            track_color = QColor("#2d3436")
        from PyQt5.QtGui import QBrush
        p.setBrush(QBrush(track_color))
        p.setPen(QPen(QColor("#4a545a"), 1))
        p.drawRoundedRect(0, 0, w, h, r, r)
        circle_d = h - 6
        if self._stopping:
            cx = w // 2 - circle_d // 2
            circle_color = QColor("#b2bec3")
        elif self._checked:
            cx = w - circle_d - 3
            circle_color = QColor("#ffffff")
        else:
            cx = 3
            circle_color = QColor("#636e72")
        p.setBrush(QBrush(circle_color))
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx, 3, circle_d, circle_d)
        if self._stopping:
            text, text_color = "정지 중...", QColor("#dfe6e9")
        elif self._checked:
            text, text_color = "동작중", QColor("#ffffff")
        else:
            text, text_color = "AI엔진", QColor("#888888")
        font = QFont("맑은 고딕", 8, QFont.Bold)
        p.setFont(font)
        p.setPen(QPen(text_color))
        if self._checked:
            text_rect = self.rect().adjusted(8, 0, -(circle_d + 8), 0)
        else:
            text_rect = self.rect().adjusted(circle_d + 6, 0, -4, 0)
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignCenter, text)
        p.end()


# ─────────────────────────────────────────────
#  업종지수 바차트
# ─────────────────────────────────────────────
class SectorBarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sectors = []
        self.setFixedHeight(280)

    def set_data(self, sectors: list):
        parsed = []
        for s in sectors:
            try:
                rate = float(s.get("change", "0").replace("%", "").replace("+", ""))
            except (ValueError, TypeError):
                rate = 0.0
            name = s.get("name", "")
            chg_str = s.get("change", "0%")
            if chg_str.startswith("-"):
                rate = -abs(rate)
            parsed.append({"name": name, "rate": rate})
        parsed.sort(key=lambda x: x["rate"], reverse=True)
        self._sectors = parsed
        self.update()

    def paintEvent(self, event):
        if not self._sectors:
            return
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        n = len(self._sectors)
        ml, mr, mt, mb = 4, 32, 6, 80
        cw, ch = w - ml - mr, h - mt - mb
        if cw <= 0 or ch <= 0 or n == 0:
            p.end(); return
        rates = [s["rate"] for s in self._sectors]
        amin, amax = min(rates), max(rates)
        pad = (amax - amin) * 0.1 if amax != amin else 0.5
        d_min = amin - pad
        d_max = amax + pad
        if amin >= 0: d_min = 0.0
        if amax <= 0: d_max = 0.0
        d_range = d_max - d_min if d_max != d_min else 1.0
        def r2y(r): return mt + ch * (d_max - r) / d_range
        btw = cw / n
        bw = max(3, int(btw * 0.75))
        gap = (btw - bw) / 2
        p.setPen(QPen(QColor("#5a5a8a"), 1, Qt.DashLine))
        fs = QFont("맑은 고딕", 8); p.setFont(fs)
        for ti in range(5):
            tv = d_min + (d_max - d_min) * ti / 4
            py = r2y(tv)
            p.drawLine(int(ml), int(py), int(ml + cw), int(py))
            p.setPen(QPen(QColor("#e8e8ff")))
            p.drawText(int(ml + cw + 4), int(py + 4), f"{tv:.1f}")
            p.setPen(QPen(QColor("#5a5a8a"), 1, Qt.DashLine))
        for i, s in enumerate(self._sectors):
            rate = s["rate"]
            x = ml + i * btw + gap
            ty = r2y(max(rate, 0)); by = r2y(min(rate, 0))
            bh = max(1, int(by - ty))
            color = QColor("#e74c3c") if rate >= 0 else QColor("#3498db")
            p.fillRect(int(x), int(ty), int(bw), bh, color)
            p.save()
            nf = QFont("맑은 고딕", 8); p.setFont(nf)
            p.setPen(QPen(QColor("#e8e8ff")))
            label = f"{s['name']}({rate:+.2f})"
            tx = int(x + bw / 2 + 5); tyy = int(h - 2)
            p.translate(tx, tyy); p.rotate(-90)
            p.drawText(0, 0, label)
            p.restore()
        p.end()


# ─────────────────────────────────────────────
#  AI Scanner Thread (main.py에서 이식)
# ─────────────────────────────────────────────
class ScannerThread(QThread):
    status_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._running = False

    def run(self):
        self._running = True
        self.status_signal.emit("[스캐너] 시작...")
        try:
            import sys, os, time, json as _json
            from datetime import datetime

            if getattr(sys, 'frozen', False):
                _root = os.path.dirname(os.path.dirname(sys.executable))
                _pkg = getattr(sys, '_MEIPASS', _root)
            else:
                _root = os.path.dirname(os.path.abspath(__file__))
                _pkg = _root
            for p in (_root, _pkg):
                if p not in sys.path:
                    sys.path.insert(0, p)

            from ai_engine.db.database import init_db
            from ai_engine.core.scanner import Scanner
            from ai_engine.comm.signal_writer import write_signals
            from ai_engine.comm.command_reader import read_command
            from ai_engine.learning.weight_optimizer import optimize_weights
            from ai_engine.learning.ai_predictor import get_predictor, reload_model
            from ai_engine.learning.strategy_manager import apply_strategy

            init_db()
            try: get_predictor()
            except Exception: pass
            try: apply_strategy()
            except Exception: pass

            scanner = Scanner()

            from xing_api import XingAPI
            _mode = _get_mode()
            warehouse = XingAPI.load_warehouse(mode=_mode)
            if warehouse:
                scanner.set_filtered_stocks(warehouse)
                self.status_signal.emit(f"[스캐너] 창고 {len(warehouse)}종목 로드")
            else:
                self.status_signal.emit("[스캐너] 창고 비어있음")

            from ai_engine.data.ls_data_fetcher import LSDataFetcher
            from ai_engine.data.collector import collect_stock_data, collect_market_data, collect_holdings_data
            import threading

            fetcher = LSDataFetcher(mode=_mode)
            _fetcher_ok = False
            _collecting = threading.Event()  # 수집 진행 중 플래그

            def _bg_collect(stocks_to_collect, held_list=None, do_market=True):
                """백그라운드 수집 — 점수 매기기를 블로킹하지 않음"""
                _collecting.set()
                try:
                    if stocks_to_collect:
                        collect_stock_data(fetcher, stocks_to_collect,
                                           status_callback=lambda msg: self.status_signal.emit(msg))
                    if held_list:
                        collect_holdings_data(fetcher, held_list)
                    if do_market:
                        collect_market_data(fetcher)
                    self.status_signal.emit("[수집기] 데이터 수집 완료")
                except Exception as e:
                    self.status_signal.emit(f"[수집기] 오류: {e}")
                finally:
                    _collecting.clear()

            if fetcher.connect():
                _fetcher_ok = True
                self.status_signal.emit("[수집기] API 연결 완료, 백그라운드 수집 시작...")
                from ai_engine.core.scanner import _load_holdings_cache
                held = _load_holdings_cache()
                # 수집을 별도 스레드로 — 점수 매기기는 바로 시작
                threading.Thread(target=_bg_collect,
                                 args=(warehouse, held, True), daemon=True).start()
            else:
                self.status_signal.emit("[수집기] API 연결 실패 - 캐시로 스캔")

            _known_codes = {s["code"] for s in warehouse} if warehouse else set()
            _cfg_path = os.path.join(_root, get_engine_config_filename())
            _cfg_mtime = 0
            scan_interval = 2
            last_learn = ""

            self.status_signal.emit("[스캐너] 준비 완료")

            while self._running:
                try:
                    now_hm = datetime.now().strftime("%H:%M")
                    today = datetime.now().strftime("%Y%m%d")

                    cmd = read_command()
                    if cmd.get("command") == "stop":
                        break
                    if cmd.get("command") in ("rescan", "run_filter"):
                        self.status_signal.emit("조건 변경 → 재스캔 중...")
                        try:
                            signals, count = scanner.run_scan()
                            write_signals(signals, scan_count=count)
                            self.status_signal.emit(f"재스캔 완료: {count}종목")
                        except Exception as e:
                            self.status_signal.emit(f"재스캔 오류: {e}")

                    try:
                        _mt = os.path.getmtime(_cfg_path) if os.path.exists(_cfg_path) else 0
                        if _mt != _cfg_mtime:
                            _cfg_mtime = _mt
                            with open(_cfg_path, "r", encoding="utf-8") as _f:
                                _cfg = _json.load(_f)
                            scan_interval = max(1, int(_cfg.get("scan_interval_seconds", 2)))
                    except Exception: pass

                    if now_hm >= "15:40" and last_learn != today:
                        try:
                            optimize_weights()
                            reload_model()
                            get_predictor()
                        except Exception: pass
                        last_learn = today

                    # 창고 변경 감지
                    try:
                        new_wh = XingAPI.load_warehouse(mode=_mode)
                        if new_wh:
                            new_codes = {s["code"] for s in new_wh}
                            if new_codes != _known_codes:
                                scanner.set_filtered_stocks(new_wh)
                                added = new_codes - _known_codes
                                if added and _fetcher_ok:
                                    new_stocks = [s for s in new_wh if s["code"] in added]
                                    collect_stock_data(fetcher, new_stocks, status_callback=lambda msg: self.status_signal.emit(msg))
                                _known_codes = new_codes
                        else:
                            if _known_codes:
                                scanner.set_filtered_stocks([])
                                write_signals([], scan_count=0)
                                _known_codes = set()
                    except Exception: pass

                    try:
                        signals, count = scanner.run_scan()
                        try:
                            _slog = os.path.join(_root, "debug_scanner.txt")
                            scored = [s for s in signals if s.get("score", 0) > 0]
                            with open(_slog, "a", encoding="utf-8") as _sf:
                                _sf.write(f"[{datetime.now().strftime('%H:%M:%S')}] scan: {count}종목, scored={len(scored)}\n")
                        except: pass
                        write_signals(signals, scan_count=count)
                        buy_sigs = sorted([s for s in signals if s.get("signal_type") == "BUY"],
                                          key=lambda x: x.get("score", 0), reverse=True)
                        top10 = buy_sigs[:10]
                        if top10:
                            names = ", ".join(f'{s["stock_name"]}({s["score"]:.0f})' for s in top10)
                            self.status_signal.emit(f"[추천] {names}")
                    except Exception as e:
                        self.status_signal.emit(f"[스캐너] 오류: {e}")

                except Exception as e:
                    self.status_signal.emit(f"[스캐너] 루프 오류: {e}")

                time.sleep(scan_interval)

        except Exception as e:
            import traceback
            self.status_signal.emit(f"[스캐너] 초기화 오류: {e}")
            try:
                _slog = os.path.join(_root if '_root' in dir() else '.', "debug_scanner.txt")
                with open(_slog, "a", encoding="utf-8") as _sf:
                    _sf.write(f"[INIT ERROR] {e}\n{traceback.format_exc()}\n")
            except: pass
        finally:
            if self._running:
                self.status_signal.emit("[스캐너] 비정상 종료")

    def stop(self):
        self._running = False


# ─────────────────────────────────────────────
#  MockMainWindow — UI 전용
# ─────────────────────────────────────────────
class MockMainWindow(QMainWindow):
    def __init__(self, xing_worker=None, acf_path=""):
        super().__init__()
        self.setMinimumSize(1100, 700)
        self.resize(1360, 880)
        self.trade_mode = "mock"
        self.setStyleSheet(DARK_STYLE)
        self._theme = _THEME["mock"]
        self.setWindowTitle("StockTrader [모의투자]")

        # 아이콘
        icon_path = os.path.join(_get_base_dir(), "icon_mock.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 상태
        self.is_trading = False
        self.holdings_data = []
        self.ai_signals = []
        self.ai_thread = None

        # 성능 캐시
        self._config_cache = None
        self._config_cache_mtime = 0
        self._last_holdings_hash = None
        self._qcolors = {}

        # 과거 데이터 수집
        self._hist_collect_thread = None
        self._hist_collect_msg = ""
        self._hist_collecting = False

        # Workers
        self._xing_worker = xing_worker
        self._market_worker = None
        self._trade_worker = None
        self._acf_path = acf_path

        # UI 구성
        self._build_ui()

        # 유일한 타이머: ai_signals.json 감시 (3초)
        self._ai_signals_mtime = 0
        self._acf_stocks = []  # ACF 스캔 결과 보관
        self.ai_timer = QTimer()
        self.ai_timer.timeout.connect(self._update_ai_signals)
        self.ai_timer.start(3000)

        # Worker 시작
        self._start_workers()

    # ── 성능 헬퍼 ──
    def _get_config(self):
        try:
            from config import CONFIG_FILE
            mtime = os.path.getmtime(CONFIG_FILE)
        except OSError:
            mtime = 0
        if self._config_cache is not None and mtime == self._config_cache_mtime:
            return self._config_cache
        self._config_cache = load_config()
        self._config_cache_mtime = mtime
        return self._config_cache

    def _qcolor(self, hex_str):
        c = self._qcolors.get(hex_str)
        if c is None:
            c = QColor(hex_str)
            self._qcolors[hex_str] = c
        return c

    # ── Worker 시작 ──
    def _start_workers(self):
        # XingWorker signal 연결
        if self._xing_worker:
            self._xing_worker.acf_updated.connect(self._on_acf_updated)
            self._xing_worker.holdings_updated.connect(self._on_holdings_updated)
            self._xing_worker.index_updated.connect(self._on_index_updated)
            self._xing_worker.status.connect(self._on_worker_status)

        # MarketWorker
        self._market_worker = MarketWorker(mode="mock")
        self._market_worker.theme_updated.connect(self._on_theme_updated)
        self._market_worker.sector_updated.connect(self._on_sector_updated)
        self._market_worker.status.connect(self._on_worker_status)
        self._market_worker.start()

        # TradeWorker
        self._trade_worker = TradeWorker(mode="mock")
        self._trade_worker.log_message.connect(self._on_trade_log)
        self._trade_worker.holdings_changed.connect(self._on_holdings_refresh)
        self._trade_worker.start()

    # ── Worker Signal Handlers (UI 스레드) ──
    def _on_acf_updated(self, stocks):
        """ACF 종목 수신 → 항상 보관, AI OFF면 스캔리스트에 직접 표시"""
        # ACF 결과 항상 보관
        if stocks:
            self._acf_stocks = stocks
        # AI OFF면 보관된 ACF 리스트를 스캔리스트에 표시
        ai_running = self.ai_thread and self.ai_thread.isRunning()
        if not ai_running:
            self._show_acf_in_scanlist()

    def _show_acf_in_scanlist(self):
        """보관된 ACF 종목을 스캔리스트에 직접 표시 (AI OFF 상태)"""
        stocks = getattr(self, '_acf_stocks', None)
        if not stocks or not hasattr(self, 'scan_list'):
            return
        _qc = self._qcolor
        self.scan_list.setUpdatesEnabled(False)
        self.scan_list.setRowCount(len(stocks))
        self._scan_codes = {}
        for row, s in enumerate(stocks):
            diff = s.get("diff", 0.0)
            diff_color = "#ff6b6b" if diff >= 0 else "#74b9ff"
            diff_str = f"{diff:+.2f}%" if diff != 0 else "-"
            price = s.get("price", 0)
            cells = [
                (s.get("name", ""), None, Qt.AlignLeft | Qt.AlignVCenter),
                (diff_str, diff_color, Qt.AlignCenter),
                ("-", "#888", Qt.AlignCenter),
                ("ACF", "#b2bec3", Qt.AlignCenter),
                (f"{price:,}" if price else "-", None, Qt.AlignCenter),
            ]
            for col, (text, color, align) in enumerate(cells):
                it = QTableWidgetItem(str(text))
                it.setTextAlignment(align)
                if color:
                    it.setForeground(_qc(color))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.scan_list.setItem(row, col, it)
            self._scan_codes[row] = s.get("code", "")
        self.scan_list.setUpdatesEnabled(True)

    def _on_holdings_updated(self, ui_holdings, summary):
        """보유종목 수신 → 테이블 업데이트"""
        if ui_holdings is not None:
            if ui_holdings or not self.holdings_data:
                h_key = tuple((h.get("raw_code"), h.get("raw_cur_price"), h.get("raw_pnl_rate"), h.get("raw_qty")) for h in ui_holdings)
                if h_key != self._last_holdings_hash:
                    self._last_holdings_hash = h_key
                    self.holdings_data = ui_holdings
                    self._update_holdings_table(ui_holdings)
                    self._write_holdings_cache(ui_holdings)
                    # TradeWorker에 보유종목 전달
                    if self._trade_worker:
                        self._trade_worker.set_holdings(ui_holdings)
        if summary:
            self._update_summary(summary)

    def _on_index_updated(self, name, data):
        """지수 수신 → UI 반영"""
        self._apply_market_index(name, data)

    def _on_theme_updated(self, themes):
        """테마 수신 → UI 반영"""
        self._update_theme_section(themes)

    def _on_sector_updated(self, sectors):
        """업종 수신 → 바차트 반영"""
        self._apply_sector_table(sectors)

    def _on_worker_status(self, msg):
        """Worker 상태 → 로그"""
        self._log(msg)

    def _on_trade_log(self, msg):
        """매매 로그"""
        self._log(msg)

    def _on_holdings_refresh(self):
        """매매 후 잔고 갱신 요청"""
        pass  # XingWorker가 3초마다 갱신하므로 별도 처리 불필요

    # ── UI 구성 ──
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        main_layout.addWidget(self._build_titlebar())
        main_layout.addWidget(self._build_market_bar())

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; width: 4px; }")
        self.main_splitter.addWidget(self._build_left_column())
        self.main_splitter.addWidget(self._build_center_column())
        self.main_splitter.addWidget(self._build_right_column())
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 1)
        main_layout.addWidget(self.main_splitter)
        self._load_splitter_sizes()

    def _build_titlebar(self):
        c = self._theme
        bar = QFrame()
        bar.setStyleSheet("background-color: #1e3a5f; border-radius: 6px;")
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        title = QLabel("📈 자동매매")
        title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        sep0 = QFrame(); sep0.setFrameShape(QFrame.VLine)
        sep0.setStyleSheet("color: #1e4a7a;")
        layout.addWidget(sep0)

        # 계좌 요약
        self.summary_labels = {}
        summaries = [
            ("추정자산", "연결중...", c['text'], c['accent']),
            ("실현손익", "-", c['text'], c['accent']),
            ("매입금액", "-", c['text'], c['accent']),
            ("평가금액", "-", c['text'], c['accent']),
            ("평가손익", "-", c['text'], c['accent']),
            ("손익률", "-", c['text'], c['accent']),
            ("보유종목", "-", c['text'], c['accent']),
        ]
        for label, value, color, bg in summaries:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background-color: {bg}; border: 1px solid {c['border']}; "
                f"border-radius: 6px; padding: 1px 4px; }}"
            )
            col = QVBoxLayout(card)
            col.setContentsMargins(4, 2, 4, 2); col.setSpacing(0)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #c0c0e0; font-size: 9px; border: none;")
            lbl.setAlignment(Qt.AlignCenter)
            val = QLabel(value)
            val.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; border: none;")
            val.setAlignment(Qt.AlignCenter)
            self.summary_labels[label] = val
            col.addWidget(lbl); col.addWidget(val)
            layout.addWidget(card)

        layout.addStretch()

        BOX_H = 28
        _box = (
            "QPushButton {{ background-color: {bg}; color: {fg}; "
            "border: 1px solid {bd}; border-radius: 4px; "
            "padding: 0px 12px; font-size: 12px; font-weight: bold; }}"
            "QPushButton:hover {{ background-color: {hv}; }}"
        )

        self.ls_badge = QLabel("XING")
        self.ls_badge.setFixedHeight(BOX_H)
        self.ls_badge.setStyleSheet(
            "background-color: #00b89422; color: #00b894; "
            "border: 1px solid #00b894; border-radius: 4px; "
            "padding: 0px 10px; font-size: 12px; font-weight: bold;"
        )
        self.ls_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.ls_badge)

        self.btn_settings = QPushButton("설정")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setFixedHeight(BOX_H)
        self.btn_settings.setStyleSheet(_box.format(bg="#4a4a80", fg="#ffffff", bd="#5a5a9a", hv="#5a5a9a"))
        self.btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(self.btn_settings)

        self.btn_mock = QPushButton("모의투자")
        self.btn_mock.setCheckable(True)
        self.btn_mock.setChecked(True)
        self.btn_mock.setFixedHeight(BOX_H)
        self.btn_mock.setStyleSheet(_box.format(bg="#0984e3", fg="#ffffff", bd="#0984e3", hv="#1e90ff"))
        layout.addWidget(self.btn_mock)

        self.btn_ai_engine = AIToggleSwitch()
        self.btn_ai_engine.setFixedHeight(BOX_H)
        self.btn_ai_engine.toggled.connect(self._on_ai_toggle)
        layout.addWidget(self.btn_ai_engine)

        self.btn_start = QPushButton("🚀 자동매매 시작")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFixedHeight(BOX_H)
        self.btn_start.clicked.connect(self.toggle_trading)
        layout.addWidget(self.btn_start)

        return bar

    def _build_market_bar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #2a2a3e; border-radius: 6px; border: 1px solid #5a5a8a;")
        bar.setFixedHeight(36)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 2, 12, 2); layout.setSpacing(0)

        self.market_labels = {}
        for label in ["KOSPI", "KOSDAQ"]:
            item_layout = QHBoxLayout(); item_layout.setSpacing(4)
            lbl = QLabel(label); lbl.setStyleSheet("color: #a0a0c0; font-size: 11px;")
            val = QLabel("-"); val.setStyleSheet("color: #e8e8ff; font-size: 12px; font-weight: bold;")
            chg = QLabel("-"); chg.setStyleSheet("color: #888; font-size: 11px;")
            self.market_labels[label] = (val, chg)
            item_layout.addWidget(lbl); item_layout.addWidget(val); item_layout.addWidget(chg)
            layout.addLayout(item_layout)
            sep = QFrame(); sep.setFrameShape(QFrame.VLine)
            sep.setStyleSheet("color: #5a5a8a; margin: 4px 12px;")
            layout.addWidget(sep)

        layout.addStretch()

        log_icon = QLabel("📋"); log_icon.setStyleSheet("font-size: 12px;")
        log_title = QLabel("매매 로그"); log_title.setStyleSheet("color: #a0a0c0; font-size: 11px; font-weight: bold;")
        self.log_label = QLabel("")
        self.log_label.setStyleSheet("color: #00ff88; font-family: Consolas; font-size: 11px;")
        self.log_label.setWordWrap(False)
        layout.addWidget(log_icon); layout.addWidget(log_title)
        layout.addWidget(self.log_label, stretch=1)

        sep_log = QFrame(); sep_log.setFrameShape(QFrame.VLine)
        sep_log.setStyleSheet("color: #5a5a8a; margin: 4px 8px;")
        layout.addWidget(sep_log)

        self.time_label = QLabel("⏱ 연결중...")
        self.time_label.setStyleSheet("color: #a0a0c0; font-size: 10px;")
        layout.addWidget(self.time_label)

        return bar

    def _build_left_column(self):
        widget = QWidget()
        self.left_v_splitter = QSplitter(Qt.Vertical)
        self.left_v_splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; height: 4px; }")
        self.left_v_splitter.addWidget(self._build_holdings_table())
        self.left_v_splitter.addWidget(self._build_market_panel())
        self.left_v_splitter.setSizes([520, 220])
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        layout.addWidget(self.left_v_splitter)
        return widget

    def _build_center_column(self):
        widget = QWidget()
        self.center_v_splitter = QSplitter(Qt.Vertical)
        self.center_v_splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; height: 4px; }")
        self.center_v_splitter.addWidget(self._build_rec_panel())
        self.center_v_splitter.addWidget(self._build_scan_panel())
        self.center_v_splitter.setSizes([350, 350])
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        layout.addWidget(self.center_v_splitter)
        return widget

    def _build_market_panel(self):
        grp = QGroupBox("업종지수")
        grp.setStyleSheet("""
            QGroupBox { color: #000000; font-size: 13px; font-weight: bold;
                border: 1px solid #5a9fd4; border-radius: 4px; margin-top: 8px; padding-top: 14px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        """)
        self.sector_chart = SectorBarChart()
        self._sector_placeholder = QLabel("")
        self._sector_placeholder.setStyleSheet("color: #444444; font-size: 11px; padding: 10px;")
        self._sector_placeholder.setAlignment(Qt.AlignCenter)
        outer = QVBoxLayout(grp); outer.setContentsMargins(4, 4, 4, 4)
        outer.addWidget(self._sector_placeholder)
        outer.addWidget(self.sector_chart)
        self.sector_chart.hide()
        return grp

    def _build_holdings_table(self):
        grp = QGroupBox("💼 보유종목")
        layout = QVBoxLayout(grp)
        c = self._theme
        self.holdings_table = QTableWidget()
        self.holdings_table.setColumnCount(10)
        self.holdings_table.setHorizontalHeaderLabels(["", "종목명", "매수가", "현재가", "등락률", "수익률", "수량", "평가금액", "손익금액", "AI"])
        self._ai_exclude_codes = self._load_ai_exclude()
        hdr = self.holdings_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        for i, w in enumerate([28, 85, 65, 65, 58, 58, 50, 82, 82, 55]):
            self.holdings_table.setColumnWidth(i, w)
        hdr.setStretchLastSection(True)
        self.holdings_table.setStyleSheet(
            f"QTableWidget {{ font-size: 11px; background-color: {c['panel']}; color: {c['text']}; alternate-background-color: {c['alt_row']}; gridline-color: {c['border']}; }}"
            f"QHeaderView::section {{ font-size: 10px; padding: 2px; background-color: {c['accent']}; color: {c['text']}; border: 1px solid {c['border']}; }}"
        )
        self.holdings_table.verticalHeader().setDefaultSectionSize(22)
        self.holdings_table.verticalHeader().setMinimumSectionSize(20)
        self.holdings_table.verticalHeader().setVisible(False)
        self.holdings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.holdings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.holdings_table.cellChanged.connect(self._on_exclude_changed)
        self.holdings_table.setAlternatingRowColors(True)
        self.holdings_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.holdings_table.setRowCount(0)
        self.holdings_table.cellDoubleClicked.connect(self._on_holdings_click)
        layout.addWidget(self.holdings_table)
        return grp

    def _build_rec_panel(self):
        c = self._theme
        ts = (
            f"QTableWidget {{ font-size: 11px; background-color: {c['panel']}; color: {c['text']}; alternate-background-color: {c['alt_row']}; gridline-color: {c['border']}; }}"
            f"QHeaderView::section {{ font-size: 10px; padding: 2px; background-color: {c['accent']}; color: {c['text']}; border: 1px solid {c['border']}; }}"
        )
        grp = QGroupBox("AI 추천종목")
        grp.setStyleSheet("""
            QGroupBox { color: #000000; font-size: 12px; font-weight: bold;
                border: 1px solid #5a9fd4; border-radius: 4px; margin-top: 8px; padding-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        """)
        layout = QVBoxLayout(grp); layout.setContentsMargins(4, 8, 4, 4); layout.setSpacing(2)
        self.rec_list = QTableWidget()
        self.rec_list.setColumnCount(6)
        self.rec_list.setHorizontalHeaderLabels(["순위", "종목명", "등락률", "AI점수", "신뢰도", "현재가"])
        self.rec_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.rec_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 6):
            self.rec_list.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.rec_list.verticalHeader().setDefaultSectionSize(20)
        self.rec_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rec_list.setAlternatingRowColors(True)
        self.rec_list.setStyleSheet(ts)
        self.rec_list.setRowCount(0)
        layout.addWidget(self.rec_list)
        return grp

    def _build_scan_panel(self):
        c = self._theme
        ts = (
            f"QTableWidget {{ font-size: 11px; background-color: {c['panel']}; color: {c['text']}; alternate-background-color: {c['alt_row']}; gridline-color: {c['border']}; }}"
            f"QHeaderView::section {{ font-size: 10px; padding: 2px; background-color: {c['accent']}; color: {c['text']}; border: 1px solid {c['border']}; }}"
        )
        grp = QGroupBox("AI 스캔종목")
        grp.setStyleSheet("""
            QGroupBox { color: #000000; font-size: 12px; font-weight: bold;
                border: 1px solid #5a9fd4; border-radius: 4px; margin-top: 8px; padding-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        """)
        layout = QVBoxLayout(grp); layout.setContentsMargins(4, 8, 4, 4); layout.setSpacing(2)
        self.scan_list = QTableWidget()
        self.scan_list.setColumnCount(5)
        self.scan_list.setHorizontalHeaderLabels(["종목명", "등락률", "AI점수", "상태", "현재가"])
        self.scan_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            self.scan_list.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.scan_list.verticalHeader().setDefaultSectionSize(20)
        self.scan_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.scan_list.setAlternatingRowColors(True)
        self.scan_list.setStyleSheet(ts)
        self.scan_list.setRowCount(0)
        self.scan_list.cellDoubleClicked.connect(self._on_scan_click)
        layout.addWidget(self.scan_list)
        return grp

    def _build_right_column(self):
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setSpacing(0); outer.setContentsMargins(0, 0, 0, 0)
        self.right_v_splitter = QSplitter(Qt.Vertical)
        self.right_v_splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; height: 4px; }")

        theme_grp = QGroupBox("🔥 상승테마")
        theme_grp.setStyleSheet("""
            QGroupBox { color: #000000; font-size: 12px; font-weight: bold;
                border: 1px solid #5a9fd4; border-radius: 4px; margin-top: 8px; padding-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        """)
        theme_grp_layout = QVBoxLayout(theme_grp)
        theme_grp_layout.setContentsMargins(4, 8, 4, 4); theme_grp_layout.setSpacing(2)
        self.theme_table = QTableWidget()
        self.theme_table.setColumnCount(3)
        self.theme_table.setHorizontalHeaderLabels(["테마명", "등락률", "관련종목"])
        self.theme_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.theme_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.theme_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.theme_table.verticalHeader().setDefaultSectionSize(20)
        self.theme_table.verticalHeader().setVisible(False)
        self.theme_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.theme_table.setAlternatingRowColors(True)
        self.theme_table.setSelectionBehavior(QTableWidget.SelectRows)
        c = self._theme
        self.theme_table.setStyleSheet(
            f"QTableWidget {{ font-size: 11px; background-color: {c['panel']}; color: {c['text']}; alternate-background-color: {c['alt_row']}; gridline-color: {c['border']}; }}"
            f"QHeaderView::section {{ font-size: 10px; padding: 2px; background-color: {c['accent']}; color: {c['text']}; border: 1px solid {c['border']}; }}"
        )
        self.theme_table.setRowCount(0)
        self.theme_table.cellClicked.connect(self._on_theme_click)
        self._theme_data = []
        theme_grp_layout.addWidget(self.theme_table)
        self.right_v_splitter.addWidget(theme_grp)

        self.related_grp = QGroupBox("관련종목")
        related_layout = QVBoxLayout(self.related_grp)
        self.related_table = QTableWidget()
        self.related_table.setColumnCount(3)
        self.related_table.setHorizontalHeaderLabels(["종목명", "현재가", "등락률"])
        self.related_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.related_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.related_table.setAlternatingRowColors(True)
        c = self._theme
        self.related_table.setStyleSheet(
            f"QTableWidget {{ font-size: 11px; background-color: {c['panel']}; color: {c['text']}; alternate-background-color: {c['alt_row']}; gridline-color: {c['border']}; }}"
            f"QHeaderView::section {{ font-size: 10px; padding: 2px; background-color: {c['accent']}; color: {c['text']}; border: 1px solid {c['border']}; }}"
        )
        self.related_table.verticalHeader().setDefaultSectionSize(22)
        self.related_table.verticalHeader().setVisible(False)
        self.related_table.cellDoubleClicked.connect(self._on_related_click)
        hint = QLabel("테마를 클릭하면 관련종목이 표시됩니다")
        hint.setStyleSheet("color: #444444; font-size: 10px;")
        hint.setAlignment(Qt.AlignCenter)
        related_layout.addWidget(hint)
        related_layout.addWidget(self.related_table)
        self.related_table.hide()
        self.right_v_splitter.addWidget(self.related_grp)
        self.right_v_splitter.setSizes([400, 400])
        outer.addWidget(self.right_v_splitter)
        return widget

    # ── 로그 ──
    def _log(self, msg):
        if hasattr(self, 'log_label'):
            self.log_label.setText(msg)
        now = datetime.now().strftime("%H:%M:%S")
        if hasattr(self, 'time_label'):
            self.time_label.setText(f"⏱ {now} 업데이트")

    # ── AI 신호 파일 읽기 ──
    def _update_ai_signals(self):
        # AI 꺼져있으면 이전 데이터 표시 안 함
        if not self.ai_thread or not self.ai_thread.isRunning():
            return
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
            exe_name = os.path.basename(sys.executable).lower()
            fname = "ai_signals_mock.json" if "mock" in exe_name else "ai_signals_real.json"
        else:
            base = os.path.dirname(os.path.abspath(__file__))
            fname = "ai_signals.json"
        path = os.path.join(base, fname)
        if not os.path.exists(path):
            return
        try:
            mtime = os.path.getmtime(path)
            if mtime == self._ai_signals_mtime:
                return
            self._ai_signals_mtime = mtime
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        signals = data.get("signals", [])
        scan_count = data.get("scan_count", 0)
        timestamp = data.get("timestamp", "")[:16].replace("T", " ")

        buy_signals = [s for s in signals if s.get("signal_type") == "BUY"]
        has_ai_scores = any(s.get("score", 0) > 0 for s in signals)
        if has_ai_scores:
            scan_signals = [s for s in signals if s.get("signal_type") in ("BUY", "HOLD", "WATCH")
                            and s.get("score", 0) > 0 and "sell_reason" not in s]
        else:
            scan_signals = [s for s in signals if s.get("signal_type") in ("BUY", "HOLD", "WATCH")
                            and "sell_reason" not in s]
        all_scanned = sorted(scan_signals, key=lambda x: x.get("score", 0), reverse=True)

        if hasattr(self, "ai_status_label"):
            self.ai_status_label.setText(
                f"🤖 AI엔진: {timestamp} | {scan_count}종목 스캔 | 매수신호 {len(buy_signals)}개"
            )

        _qc = self._qcolor
        def _item(text, color=None, align=Qt.AlignCenter):
            it = QTableWidgetItem(str(text))
            it.setTextAlignment(align)
            if color: it.setForeground(_qc(color))
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            return it

        # 스캔종목
        if hasattr(self, "scan_list"):
            self.scan_list.setUpdatesEnabled(False)
            self.scan_list.setRowCount(len(all_scanned))
            self._scan_codes = {}
            for row_idx, sig in enumerate(all_scanned):
                sig_type = sig.get("signal_type", "")
                score = sig.get("score", 0)
                cur_price = sig.get("current_price", 0)
                state_color = {"BUY": "#00b894", "HOLD": "#fdcb6e"}.get(sig_type, "#888")
                score_color = "#00b894" if sig_type == "BUY" else "#fdcb6e" if sig_type == "HOLD" else "#aaa"
                diff_rate = sig.get("diff_rate", 0.0)
                diff_color = "#ff6b6b" if diff_rate >= 0 else "#74b9ff"
                diff_str = f"{diff_rate:+.2f}%" if diff_rate != 0 else "-"
                cells = [
                    (sig.get("stock_name", ""), None, Qt.AlignLeft | Qt.AlignVCenter),
                    (diff_str, diff_color, Qt.AlignCenter),
                    (f"{score:.1f}", score_color, Qt.AlignCenter),
                    (sig_type, state_color, Qt.AlignCenter),
                    (f"{cur_price:,}" if cur_price else "-", None, Qt.AlignCenter),
                ]
                for col, (text, color, align) in enumerate(cells):
                    item = self.scan_list.item(row_idx, col)
                    if item is None:
                        item = _item(text, color, align)
                        self.scan_list.setItem(row_idx, col, item)
                    else:
                        item.setText(str(text))
                        if color: item.setForeground(_qc(color))
                        item.setTextAlignment(align)
                self._scan_codes[row_idx] = sig.get("stock_code", "")
            self.scan_list.setUpdatesEnabled(True)

        # 추천종목
        if hasattr(self, "rec_list"):
            self.rec_list.setUpdatesEnabled(False)
            def _rank_score(s):
                return (s.get("score", 0) * 0.50 + s.get("supply_score", 0) * 0.25
                        + s.get("chart_score", 0) * 0.15 + s.get("material_score", 0) * 0.10)
            ranked = sorted(buy_signals, key=_rank_score, reverse=True)[:10]
            self.rec_list.setRowCount(len(ranked))
            for rank, sig in enumerate(ranked, 1):
                row = rank - 1
                score = sig.get("score", 0)
                confidence = sig.get("confidence", "")
                cur_price = sig.get("current_price", 0)
                conf_color = {"HIGH": "#00b894", "MEDIUM": "#fdcb6e", "LOW": "#888"}.get(confidence, "#888")
                diff_rate = sig.get("diff_rate", 0.0)
                diff_color = "#ff6b6b" if diff_rate >= 0 else "#74b9ff"
                diff_str = f"{diff_rate:+.2f}%" if diff_rate != 0 else "-"
                cells = [
                    (f"{rank}", None, Qt.AlignCenter),
                    (sig.get("stock_name", ""), None, Qt.AlignLeft | Qt.AlignVCenter),
                    (diff_str, diff_color, Qt.AlignCenter),
                    (f"{score:.1f}점", "#ff6b6b", Qt.AlignCenter),
                    (confidence, conf_color, Qt.AlignCenter),
                    (f"{cur_price:,}" if cur_price else "-", None, Qt.AlignCenter),
                ]
                for col, (text, color, align) in enumerate(cells):
                    item = self.rec_list.item(row, col)
                    if item is None:
                        item = _item(text, color, align)
                        self.rec_list.setItem(row, col, item)
                    else:
                        item.setText(str(text))
                        if color: item.setForeground(_qc(color))
                        item.setTextAlignment(align)
            self.rec_list.setUpdatesEnabled(True)

        self.ai_signals = signals
        # TradeWorker에 신호 전달
        if self._trade_worker:
            self._trade_worker.set_signals(signals)

        self._refresh_holdings_ai_column()

    def _refresh_holdings_ai_column(self):
        if not hasattr(self, 'holdings_table'): return
        sig_map = {}
        for s in self.ai_signals:
            if s.get("signal_type") in ("SELL", "HOLD"):
                sc = s.get("stock_code", "")
                sig_map[sc] = s
                if sc.startswith("A") and len(sc) == 7: sig_map[sc[1:]] = s
                else: sig_map["A" + sc] = s
        for row in range(self.holdings_table.rowCount()):
            if row >= len(self.holdings_data): break
            code = self.holdings_data[row].get("raw_code", "")
            sig = sig_map.get(code)
            if sig:
                if sig["signal_type"] == "SELL":
                    ai_text, ai_color = f"매도 {sig.get('score', 0):.0f}점", "#ff6b6b"
                else:
                    ai_text, ai_color = f"보유 {100 - sig.get('score', 50):.0f}점", "#fdcb6e"
            else:
                ai_text, ai_color = "-", "#636e72"
            item = self.holdings_table.item(row, 9)
            if item is None:
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignCenter)
                self.holdings_table.setItem(row, 9, item)
            item.setText(ai_text)
            item.setForeground(self._qcolor(ai_color))

    # ── 지수/업종/테마 UI ──
    def _apply_market_index(self, name, data):
        if not data or name not in self.market_labels: return
        try:
            row = data[0] if isinstance(data, list) else data
            price = float(str(row.get("pricejisu", 0)).replace(",", ""))
            try: rt = float(str(row.get("diffjisu", 0)).replace(",", ""))
            except: rt = 0.0
            sign_cd = str(row.get("sign", "3"))
            if sign_cd == "5": rt = -abs(rt)
            elif sign_cd == "2": rt = abs(rt)
            val_lbl, chg_lbl = self.market_labels[name]
            val_lbl.setText(f"{price:,.2f}")
            color = "#ff6b6b" if rt >= 0 else "#74b9ff"
            chg_lbl.setText(f"{'+' if rt >= 0 else ''}{rt:.2f}%")
            chg_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        except Exception: pass

    def _apply_sector_table(self, sectors):
        if not hasattr(self, 'sector_chart') or not sectors: return
        if hasattr(self, '_sector_placeholder') and self._sector_placeholder:
            self._sector_placeholder.hide()
            self._sector_placeholder.deleteLater()
            self._sector_placeholder = None
        self.sector_chart.show()
        self.sector_chart.set_data(sectors)

    def _update_theme_section(self, themes):
        if not hasattr(self, 'theme_table') or not themes: return
        self._theme_data = themes[:10]
        self.theme_table.setRowCount(len(self._theme_data))
        for r, t in enumerate(self._theme_data):
            name = t.get("name", "")
            diff = t.get("diff", 0.0)
            diff_str = t.get("diff_str", f"{diff:+.2f}%")
            color = QColor("#ff6b6b") if diff >= 0 else QColor("#74b9ff")
            name_item = QTableWidgetItem(name)
            chg_item = QTableWidgetItem(diff_str)
            chg_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            chg_item.setForeground(color)
            btn_item = QTableWidgetItem("관련종목")
            btn_item.setTextAlignment(Qt.AlignCenter)
            btn_item.setForeground(QColor("#a0a0c0"))
            self.theme_table.setItem(r, 0, name_item)
            self.theme_table.setItem(r, 1, chg_item)
            self.theme_table.setItem(r, 2, btn_item)

    def _on_theme_click(self, row, col):
        if row < 0 or row >= len(self._theme_data): return
        t = self._theme_data[row]
        self.show_theme_stocks(t.get("name", ""), t.get("code", ""))

    def show_theme_stocks(self, theme_name, tmcode=""):
        if self.related_table.isVisible() and getattr(self, '_current_theme', '') == theme_name:
            self.related_table.hide()
            self.related_grp.setTitle("관련종목")
            self._current_theme = ''
            return
        self._current_theme = theme_name
        self.related_grp.setTitle(f"  {theme_name} 관련종목")
        if not tmcode:
            self.related_table.setRowCount(1)
            self.related_table.setItem(0, 0, QTableWidgetItem("테마코드 없음"))
            self.related_table.show()
            return
        stocks = []
        try:
            from ls_api import LSApi
            api = LSApi(mode="mock")
            if api.get_token():
                stocks = api.get_theme_stocks(tmcode)
        except Exception: pass
        self.related_table.show()
        if not stocks:
            self.related_table.setRowCount(1)
            self.related_table.setItem(0, 0, QTableWidgetItem("종목 데이터 없음"))
            return
        self.related_table.setRowCount(len(stocks))
        for r, row_data in enumerate(stocks):
            name = row_data[0] if len(row_data) > 0 else ""
            price = row_data[1] if len(row_data) > 1 else "-"
            chg = row_data[2] if len(row_data) > 2 else "-"
            for c, val in enumerate([name, price, chg]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if c == 2:
                    item.setForeground(QColor("#ff6b6b") if val.startswith("+") else QColor("#74b9ff"))
                self.related_table.setItem(r, c, item)

    # ── 보유종목 테이블 ──
    def _update_holdings_table(self, holdings):
        self.holdings_table.blockSignals(True)
        self.holdings_table.setUpdatesEnabled(False)
        self.holdings_table.setRowCount(len(holdings))
        sig_map = {}
        for s in self.ai_signals:
            if s.get("signal_type") in ("SELL", "HOLD"):
                sc = s.get("stock_code", "")
                sig_map[sc] = s
                if sc.startswith("A") and len(sc) == 7: sig_map[sc[1:]] = s
                else: sig_map["A" + sc] = s
        for row, h in enumerate(holdings):
            code = h.get("raw_code", "")
            chk_item = self.holdings_table.item(row, 0)
            if chk_item is None:
                chk_item = QTableWidgetItem()
                chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk_item.setCheckState(Qt.Checked if code in self._ai_exclude_codes else Qt.Unchecked)
                self.holdings_table.setItem(row, 0, chk_item)
            cols = [h["name"], h["buy_price"], h["cur_price"], h["day_change"], h["pnl_rate"], h["qty"], h["eval_amt"], h["pnl_amt"]]
            for col, val in enumerate(cols):
                actual_col = col + 1
                item = self.holdings_table.item(row, actual_col)
                if item is None:
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.holdings_table.setItem(row, actual_col, item)
                else:
                    item.setText(val)
                if col in [3, 4, 7]:
                    if val.startswith("+"): item.setForeground(self._qcolor("#ff6b6b"))
                    elif val.startswith("-"): item.setForeground(self._qcolor("#74b9ff"))
            sig = sig_map.get(code)
            if sig:
                if sig["signal_type"] == "SELL":
                    ai_text, ai_color = f"매도{sig.get('score', 0):.0f}", "#ff6b6b"
                else:
                    ai_text, ai_color = f"보유{100 - sig.get('score', 50):.0f}", "#fdcb6e"
            else:
                ai_text, ai_color = "-", "#636e72"
            ai_item = self.holdings_table.item(row, 9)
            if ai_item is None:
                ai_item = QTableWidgetItem(ai_text)
                ai_item.setTextAlignment(Qt.AlignCenter)
                ai_item.setFlags(ai_item.flags() & ~Qt.ItemIsEditable)
                self.holdings_table.setItem(row, 9, ai_item)
            else:
                ai_item.setText(ai_text)
            ai_item.setForeground(self._qcolor(ai_color))
        self.holdings_table.setUpdatesEnabled(True)
        self.holdings_table.blockSignals(False)

    def _write_holdings_cache(self, holdings):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
            fname = "holdings_cache_mock.json"
        else:
            base = os.path.dirname(os.path.abspath(__file__))
            fname = "holdings_cache.json"
        path = os.path.join(base, fname)
        payload = []
        for h in holdings:
            rc = h.get("raw_code", "")
            if not rc: continue
            clean_code = rc[1:] if rc.startswith("A") and len(rc) == 7 else rc
            payload.append({"code": clean_code, "name": h.get("name", ""),
                            "buy_price": h.get("raw_buy_price", 0), "qty": h.get("raw_qty", 0),
                            "cur_price": h.get("raw_cur_price", 0), "pnl_rate": h.get("raw_pnl_rate", 0)})
        def _io():
            tmp = path + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False)
                os.replace(tmp, path)
            except Exception: pass
        threading.Thread(target=_io, daemon=True).start()

    def _update_summary(self, summary):
        def _set(key, val_key, use_color=False):
            if key not in self.summary_labels: return
            val = summary.get(val_key, "-")
            self.summary_labels[key].setText(val)
            if use_color and val != "-":
                color = "#ff6b6b" if val.startswith("+") else "#74b9ff" if val.startswith("-") else "#e0e0e0"
                self.summary_labels[key].setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        _set("추정자산", "total_eval")
        _set("실현손익", "realized_pnl", use_color=True)
        _set("매입금액", "total_buy")
        _set("평가금액", "total_appamt")
        _set("평가손익", "total_pnl", use_color=True)
        _set("손익률", "total_pnl_rate", use_color=True)
        if "보유종목" in self.summary_labels:
            self.summary_labels["보유종목"].setText(summary.get("stock_count", "-"))

    # ── 설정 ──
    _SETTINGS_STYLE = """
        QDialog { background-color: #ffffff; color: #000000; font-family: '맑은 고딕'; font-size: 13px; }
        QDialog QWidget { background-color: #ffffff; color: #000000; }
        QDialog QGroupBox { border: 1px solid #000000; border-radius: 4px; margin-top: 8px; padding-top: 8px; }
        QDialog QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        QDialog QTabWidget::pane { border: 1px solid #000000; background: #ffffff; }
        QDialog QTabBar::tab { background: #ffffff; color: #000000; border: 1px solid #000000; padding: 6px 12px; }
        QDialog QTabBar::tab:selected { background: #ffffff; border-bottom: 2px solid #000000; font-weight: bold; }
        QDialog QTableWidget { background-color: #ffffff; color: #000000; gridline-color: #000000; border: 1px solid #000000; }
        QDialog QHeaderView::section { background-color: #ffffff; color: #000000; border: 1px solid #000000; padding: 4px; font-weight: bold; }
        QDialog QLineEdit, QDialog QSpinBox, QDialog QDoubleSpinBox, QDialog QComboBox, QDialog QTextEdit {
            background: #ffffff; color: #000000; border: 2px solid #000000; padding: 3px; }
        QDialog QCheckBox { color: #000000; }
        QDialog QCheckBox::indicator { border: 2px solid #000000; background: #ffffff; width: 14px; height: 14px; }
        QDialog QCheckBox::indicator:checked { background: #000000; }
        QDialog QPushButton { background: #ffffff; color: #000000; border: 2px solid #000000; padding: 5px 15px; }
        QDialog QPushButton:hover { border-width: 3px; }
        QDialog QLabel { color: #000000; background: transparent; }
        QDialog QScrollBar:vertical { background: #ffffff; width: 12px; border: 1px solid #000000; }
        QDialog QScrollBar::handle:vertical { background: #000000; }
    """

    def open_settings(self):
        try:
            SettingsDialogCls = _get_settings_dialog_class()
            dlg = SettingsDialogCls(self)
            # 크기: 크게 + 위아래 리사이즈 가능
            dlg.resize(900, 750)
            dlg.setMinimumSize(700, 400)
            dlg.setSizeGripEnabled(True)
            # 개별 위젯 인라인 스타일 전부 제거 → 다이얼로그 스타일만 적용
            for child in dlg.findChildren(QWidget):
                child.setStyleSheet("")
            dlg.setStyleSheet(self._SETTINGS_STYLE)
            dlg.exec_()
        except Exception as e:
            self._log(f"설정 열기 실패: {e}")

    # ── AI 엔진 ──
    def _on_ai_toggle(self, checked):
        if checked:
            self._ai_engine_start()
        else:
            self._ai_engine_stop()

    def _ai_engine_start(self):
        if self.ai_thread and self.ai_thread.isRunning(): return
        # 이전 signals 파일 삭제 (새 스캔 데이터만 표시)
        try:
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(os.path.dirname(sys.executable))
                exe_name = os.path.basename(sys.executable).lower()
                fname = "ai_signals_mock.json" if "mock" in exe_name else "ai_signals_real.json"
            else:
                base = os.path.dirname(os.path.abspath(__file__))
                fname = "ai_signals.json"
            sig_path = os.path.join(base, fname)
            if os.path.exists(sig_path):
                os.remove(sig_path)
        except Exception:
            pass
        self._ai_signals_mtime = 0
        self.ai_thread = ScannerThread()
        self.ai_thread.status_signal.connect(self._on_ai_status)
        self.ai_thread.finished.connect(self._on_ai_engine_stopped)
        self.ai_thread.start()
        self.btn_ai_engine.setChecked(True)
        self._log("▶ AI 스캐너 시작")

    def _ai_engine_stop(self):
        if not self.ai_thread or not self.ai_thread.isRunning():
            self.btn_ai_engine.setChecked(False)
            return
        self.btn_ai_engine.setStopping()
        self.ai_thread.stop()
        self._log("AI 엔진 정지 요청")

    def _on_ai_status(self, msg):
        self._log(msg)

    def _on_ai_engine_stopped(self):
        if self.ai_thread:
            try:
                self.ai_thread.finished.disconnect(self._on_ai_engine_stopped)
                self.ai_thread.status_signal.disconnect(self._on_ai_status)
            except Exception: pass
        self.ai_thread = None
        self.btn_ai_engine.setChecked(False)
        # AI 꺼지면 보관된 ACF 리스트 복원
        self._show_acf_in_scanlist()

    # ── 자동매매 ──
    def toggle_trading(self):
        now = datetime.now().strftime("%H:%M:%S")
        if not self.is_trading:
            self.is_trading = True
            self.btn_start.setText("⏸ 자동매매 중지")
            self.btn_start.setStyleSheet("background-color: #d63031; color: #fff; border: none; font-weight: bold;")
            self._log(f"[{now}] ▶ 자동매매 시작!")
            if self._trade_worker:
                self._trade_worker.set_trading(True)
        else:
            self.is_trading = False
            self.btn_start.setText("🚀 자동매매 시작")
            self.btn_start.setStyleSheet("background-color: #00b894; color: #fff; border: none; font-weight: bold;")
            self._log(f"[{now}] ⏸ 자동매매 정지")
            if self._trade_worker:
                self._trade_worker.set_trading(False)

    # ── HTS 연동 ──
    def _find_hts_window(self):
        user32 = ctypes.windll.user32
        hts_hwnd = [None]
        def enum_cb(hwnd, _):
            try:
                if hts_hwnd[0]: return True
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        if "투혼" in buf.value:
                            hts_hwnd[0] = hwnd
                            return False
            except Exception: pass
            return True
        try:
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        except Exception: pass
        return hts_hwnd[0]

    def _send_to_hts(self, stock_code, stock_name=""):
        now = datetime.now().strftime("%H:%M:%S")
        code = stock_code.replace("A", "").replace("a", "").strip()
        if not code:
            self._log(f"[{now}] {stock_name} → 종목코드 없음")
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(code)
        hts_hwnd = self._find_hts_window()
        if not hts_hwnd:
            self._log(f"[{now}] HTS 미실행 → {stock_name}({code}) 클립보드 복사됨")
            return
        try:
            user32 = ctypes.windll.user32
            for ch in code:
                user32.PostMessageW(hts_hwnd, 0x0102, ord(ch), 0)
            time.sleep(0.1)
            user32.PostMessageW(hts_hwnd, 0x0100, 0x0D, 0)
            time.sleep(0.01)
            user32.PostMessageW(hts_hwnd, 0x0101, 0x0D, 0)
            self._log(f"[{now}] HTS 연동: {stock_name} ({code})")
        except Exception as e:
            self._log(f"[{now}] HTS 오류: {e}")

    def _on_holdings_click(self, row, col):
        if row < len(self.holdings_data):
            h = self.holdings_data[row]
            self._send_to_hts(h["raw_code"], h["name"])

    def _on_scan_click(self, row, col):
        name_item = self.scan_list.item(row, 0)
        if name_item:
            code = getattr(self, '_scan_codes', {}).get(row, "")
            self._send_to_hts(code, name_item.text())

    def _on_related_click(self, row, col):
        name_item = self.related_table.item(row, 0)
        if name_item:
            clipboard = QApplication.clipboard()
            clipboard.setText(name_item.text())
            self._log(f"{name_item.text()} → 클립보드 복사")

    # ── 감시제외 ──
    def _on_exclude_changed(self, row, col):
        if col != 0 or row >= len(self.holdings_data): return
        code = self.holdings_data[row].get("raw_code", "")
        item = self.holdings_table.item(row, 0)
        if item and item.checkState() == Qt.Checked:
            self._ai_exclude_codes.add(code)
        else:
            self._ai_exclude_codes.discard(code)
        self._save_ai_exclude()
        if self._trade_worker:
            self._trade_worker.set_exclude_codes(self._ai_exclude_codes)

    def _load_ai_exclude(self) -> set:
        try:
            path = os.path.join(_get_base_dir(), "ai_exclude.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return set(json.load(f))
        except Exception: pass
        return set()

    def _save_ai_exclude(self):
        try:
            path = os.path.join(_get_base_dir(), "ai_exclude.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(list(self._ai_exclude_codes), f)
        except Exception: pass

    # ── 스플리터 저장/로드 ──
    def _get_splitter_path(self):
        return os.path.join(_get_base_dir(), "splitter_sizes.json")

    def _save_splitter_sizes(self):
        try:
            geo = self.geometry()
            data = {
                "main": self.main_splitter.sizes(),
                "left": self.left_v_splitter.sizes(),
                "center": self.center_v_splitter.sizes(),
                "right": self.right_v_splitter.sizes(),
                "window": {"x": geo.x(), "y": geo.y(), "width": geo.width(), "height": geo.height(), "maximized": self.isMaximized()}
            }
            with open(self._get_splitter_path(), "w") as f:
                json.dump(data, f, indent=2)
        except Exception: pass

    def _load_splitter_sizes(self):
        try:
            path = self._get_splitter_path()
            if not os.path.exists(path):
                self.main_splitter.setSizes([650, 473, 384])
                return
            with open(path) as f:
                data = json.load(f)
            self.main_splitter.setSizes(data.get("main", [540, 400, 400]))
            self.left_v_splitter.setSizes(data.get("left", [520, 220]))
            self.center_v_splitter.setSizes(data.get("center", [350, 350]))
            self.right_v_splitter.setSizes(data.get("right", [400, 400]))
            win = data.get("window")
            if win:
                if win.get("maximized"): self.showMaximized()
                else: self.setGeometry(win["x"], win["y"], win["width"], win["height"])
        except Exception: pass

    def closeEvent(self, event):
        self._save_splitter_sizes()
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.stop()
            self.ai_thread.wait(500)
        if self._xing_worker:
            self._xing_worker.stop()
            self._xing_worker.wait(2000)
        if self._market_worker:
            self._market_worker.stop()
            self._market_worker.wait(2000)
        if self._trade_worker:
            self._trade_worker.stop()
            self._trade_worker.wait(2000)
        event.accept()


# ─────────────────────────────────────────────
#  로그인 다이얼로그
# ─────────────────────────────────────────────
class MockLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("StockTrader 모의투자 로그인")
        self.setFixedSize(420, 320)
        self.setStyleSheet(DARK_STYLE)
        self.xing_worker = None
        self.acf_path = ""

        config = load_config()
        xing_cfg = config.get("xing", {})

        layout = QVBoxLayout(self)
        layout.setSpacing(12); layout.setContentsMargins(30, 20, 30, 20)

        title = QLabel("StockTrader [모의투자]")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("맑은 고딕", 18, QFont.Bold))
        title.setStyleSheet("color: #00b894; margin-bottom: 5px;")
        layout.addWidget(title)

        grid = QGridLayout(); grid.setSpacing(8)
        grid.addWidget(QLabel("ID:"), 0, 0)
        self.edit_id = QLineEdit()
        self.edit_id.setText(xing_cfg.get("user_id", ""))
        self.edit_id.setPlaceholderText("xingAPI 사용자 ID")
        grid.addWidget(self.edit_id, 0, 1)

        grid.addWidget(QLabel("PW:"), 1, 0)
        self.edit_pw = QLineEdit()
        self.edit_pw.setEchoMode(QLineEdit.Password)
        self.edit_pw.setPlaceholderText("비밀번호")
        grid.addWidget(self.edit_pw, 1, 1)

        layout.addLayout(grid)

        acf_layout = QHBoxLayout()
        acf_layout.addWidget(QLabel("ACF:"))
        self.edit_acf = QLineEdit()
        self.edit_acf.setText(xing_cfg.get("acf_path", ""))
        self.edit_acf.setPlaceholderText("HTS 조건검색 ACF 파일")
        acf_layout.addWidget(self.edit_acf)
        btn_browse = QPushButton("찾기")
        btn_browse.setFixedWidth(50)
        btn_browse.setAutoDefault(False)
        btn_browse.clicked.connect(self._browse_acf)
        acf_layout.addWidget(btn_browse)
        layout.addLayout(acf_layout)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #fdcb6e; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        btn_layout = QHBoxLayout()
        self.btn_login = QPushButton("로그인")
        self.btn_login.setObjectName("btn_start")
        self.btn_login.setFixedHeight(36)
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self._do_login)
        btn_layout.addWidget(self.btn_login)

        btn_skip = QPushButton("REST만 사용")
        btn_skip.setFixedHeight(36)
        btn_skip.setAutoDefault(False)
        btn_skip.clicked.connect(self._skip_login)
        btn_layout.addWidget(btn_skip)
        layout.addLayout(btn_layout)

    def _browse_acf(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "ACF 파일 선택", "", "ACF 파일 (*.acf *.ACF);;모든 파일 (*)")
        if path:
            self.edit_acf.setText(path)

    def _do_login(self):
        user_id = self.edit_id.text().strip()
        password = self.edit_pw.text()
        if not user_id or not password:
            self.lbl_status.setText("ID와 비밀번호를 입력하세요")
            self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
            return

        self.lbl_status.setText("로그인 중...")
        self.lbl_status.setStyleSheet("color: #fdcb6e; font-size: 11px;")
        self.btn_login.setEnabled(False)
        QApplication.processEvents()

        self.acf_path = self.edit_acf.text().strip()

        # XingWorker 생성 및 시작
        self.xing_worker = XingWorker(
            user_id=user_id, password=password,
            login_mode="mock", acf_path=self.acf_path
        )
        self.xing_worker.login_result.connect(self._on_login_result)
        self.xing_worker.start()

    def _on_login_result(self, ok, msg, xing_obj):
        if ok:
            # 설정 저장
            config = load_config()
            config["xing"]["user_id"] = self.edit_id.text().strip()
            config["xing"]["acf_path"] = self.acf_path
            config["api"]["trade_mode"] = "mock"
            save_config(config)

            self.lbl_status.setText(f"로그인 성공! ({msg})")
            self.lbl_status.setStyleSheet("color: #00b894; font-size: 11px;")
            QApplication.processEvents()
            QTimer.singleShot(500, self.accept)
        else:
            self.lbl_status.setText(f"로그인 실패: {msg}")
            self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
            self.xing_worker.stop()
            self.xing_worker = None
            self.btn_login.setEnabled(True)

    def _skip_login(self):
        self.xing_worker = None
        self.acf_path = self.edit_acf.text().strip()
        config = load_config()
        config["api"]["trade_mode"] = "mock"
        if self.acf_path:
            config["xing"]["acf_path"] = self.acf_path
        save_config(config)
        self.accept()


# ─────────────────────────────────────────────
#  진입점
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    login_dlg = MockLoginDialog()
    if login_dlg.exec_() != QDialog.Accepted:
        sys.exit(0)

    window = MockMainWindow(
        xing_worker=login_dlg.xing_worker,
        acf_path=login_dlg.acf_path
    )

    if login_dlg.xing_worker:
        window.ls_badge.setText("XING")
        window.ls_badge.setStyleSheet(
            "background-color: #00b89422; color: #00b894; "
            "border: 1px solid #00b894; border-radius: 4px; padding: 4px 10px; font-size: 12px; font-weight: bold;"
        )
    else:
        window.ls_badge.setText("REST")
        window.ls_badge.setStyleSheet(
            "background-color: #fdcb6e22; color: #fdcb6e; "
            "border: 1px solid #fdcb6e; border-radius: 4px; padding: 4px 10px; font-size: 12px; font-weight: bold;"
        )

    window.show()
    sys.exit(app.exec_())
