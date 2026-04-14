import sys
import traceback
import ctypes
import ctypes.wintypes
import threading
import time
import json
import os
from datetime import datetime
from config import load_config, save_config
# ls_api는 과거데이터 수집(historical_collector)에서만 사용
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QTabWidget, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout, QFrame,
    QScrollArea, QSizePolicy, QProgressBar, QSplitter, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QPen, QFontMetrics

# ─────────────────────────────────────────────
#  다크 테마 스타일시트
# ─────────────────────────────────────────────
# 모드별 색상 팔레트
_THEME = {
    "mock": {
        "bg":      "#1c1c2e", "panel":  "#2a2a3e", "accent": "#3d3d60",
        "border":  "#5a5a8a", "btn":    "#4a4a80", "btn_hv": "#4e4e7a",
        "pressed": "#2a2a50", "scroll": "#1c1c2e", "chk":    "#4a4a80",
        "tab_sel": "#4a4a80", "arrow":  "#a0a0d0", "focus":  "#8080c0",
        "alt_row": "#33334f", "text":   "#e8e8ff",
    },
    "real": {
        "bg":      "#181e28", "panel":  "#222c3a", "accent": "#2e3d50",
        "border":  "#4a6080", "btn":    "#2a4060", "btn_hv": "#3a5070",
        "pressed": "#121828", "scroll": "#181e28", "chk":    "#2a4060",
        "tab_sel": "#2a4060", "arrow":  "#8aaac0", "focus":  "#6090b0",
        "alt_row": "#1e2a38", "text":   "#e0eeff",
    },
}

def build_style(mode="mock"):
    c = _THEME.get(mode, _THEME["mock"])
    return f"""
QMainWindow, QWidget {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: '맑은 고딕', Arial;
    font-size: 13px;
}}
QLabel {{ color: {c['text']}; }}
QPushButton {{
    background-color: {c['accent']};
    color: {c['text']};
    border: 1px solid {c['border']};
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 12px;
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
    background-color: {c['panel']};
    color: {c['text']};
    border: 1px solid {c['border']};
    gridline-color: {c['border']};
    selection-background-color: {c['accent']};
}}
QTableWidget::item {{ padding: 4px; }}
QHeaderView::section {{
    background-color: {c['accent']};
    color: {c['text']};
    padding: 6px;
    border: 1px solid {c['border']};
    font-weight: bold;
    font-size: 12px;
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
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {c['accent']};
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

# 하위 호환 (기본값 mock)
DARK_STYLE = build_style("mock")

# ─────────────────────────────────────────────
#  설정 다이얼로그
# ─────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # 메인 윈도우 참조
        self.setWindowTitle("⚙️ 설정")
        self.setMinimumSize(650, 450)
        self.resize(700, 500)
        self.setStyleSheet(DARK_STYLE)
        self.config = load_config()
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.addTab(self._tab_account(),    "💰 계좌·매수 설정")
        tabs.addTab(self._tab_profit(),     "📈 수익·손실 설정")
        tabs.addTab(self._tab_ai_condition(), "🤖 AI 조건 편집기")
        tabs.addTab(self._tab_api(),        "🔑 API·계정 설정")
        tabs.addTab(self._tab_notify(),     "🔔 알림 설정")
        tabs.addTab(self._tab_data(),       "🗄️ 데이터 소스")
        layout.addWidget(tabs)

        # 하단 저장/닫기 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_save = QPushButton("💾 저장")
        btn_save.setObjectName("btn_settings")
        btn_save.clicked.connect(self._save_all_and_close)
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        layout.setContentsMargins(10, 10, 10, 10)

    def _format_comma_field(self):
        """숫자 입력 필드에 콤마 자동 추가"""
        sender = self.sender()
        if not sender:
            return
        text = sender.text().replace(",", "")
        if not text:
            return
        try:
            val = int(text)
            formatted = f"{val:,}"
            if formatted != sender.text():
                sender.blockSignals(True)
                cursor_pos = sender.cursorPosition()
                old_len = len(sender.text())
                sender.setText(formatted)
                new_len = len(formatted)
                sender.setCursorPosition(cursor_pos + (new_len - old_len))
                sender.blockSignals(False)
        except ValueError:
            pass

    @staticmethod
    def _parse_comma_int(text: str, default: int = 0) -> int:
        """콤마 포함 텍스트를 정수로 변환"""
        try:
            return int(text.replace(",", ""))
        except (ValueError, AttributeError):
            return default

    def _load_values(self):
        c = self.config
        buy_amt = c["account"]["buy_amount"]
        self.edit_buy_amount.setText(f"{buy_amt:,}")
        self.spin_max_stocks.setValue(c["account"]["max_stocks"])
        self.edit_start_time.setText(c["account"]["start_time"])
        self.edit_end_time.setText(c["account"]["end_time"])
        self.spin_risk.setValue(c["account"]["risk_limit"])
        for i, val in enumerate(c["profit"]["profit_stages"]):
            self.profit_edits[i].setValue(val)
        sell_ratios = c["profit"].get("sell_ratios", [20.0] * 5)
        for i, val in enumerate(sell_ratios[:len(self.sell_ratio_edits)]):
            self.sell_ratio_edits[i].setValue(val)
        self.spin_loss.setValue(c["profit"]["loss_cut"])
        loss_stages = c["profit"].get("loss_stages", [(-3.0, 33.0), (-5.0, 33.0), (-7.0, 100.0)])
        for i, (thresh, ratio) in enumerate(loss_stages[:len(self.loss_threshold_edits)]):
            self.loss_threshold_edits[i].setValue(thresh)
            self.loss_ratio_edits[i].setValue(ratio)
        self.edit_ls_key.setText(c["api"].get("ls_app_key", ""))
        self.edit_ls_secret.setText(c["api"].get("ls_app_secret", ""))
        self.edit_mock_key.setText(c["api"].get("ls_mock_key", ""))
        self.edit_mock_secret.setText(c["api"].get("ls_mock_secret", ""))
        self.edit_krx_key.setText(c["api"].get("krx_key", ""))
        self.edit_kakao.setText(c["notify"]["kakao_token"])
        self.edit_telegram.setText(c["notify"]["telegram_token"])
        self.edit_chat_id.setText(c["notify"]["telegram_chat_id"])
        self.edit_data_path.setText(c["data"]["data_path"])
        self.combo_period.setCurrentText(c["data"]["period"])

    def _save_all_and_close(self):
        """config.json + engine_config.json 한 번에 저장 (창 닫지 않음)"""
        print("[설정저장] _save_all_and_close 시작")
        self.config["account"]["buy_amount"]   = self._parse_comma_int(self.edit_buy_amount.text(), 1000000)
        self.config["account"]["max_stocks"]   = self.spin_max_stocks.value()
        self.config["account"]["start_time"]   = self.edit_start_time.text()
        self.config["account"]["end_time"]     = self.edit_end_time.text()
        self.config["account"]["risk_limit"]   = self.spin_risk.value()
        self.config["profit"]["profit_stages"] = [e.value() for e in self.profit_edits]
        self.config["profit"]["sell_ratios"]   = [e.value() for e in self.sell_ratio_edits]
        self.config["profit"]["loss_cut"]      = self.spin_loss.value()
        self.config["profit"]["loss_stages"]   = [
            (self.loss_threshold_edits[i].value(), self.loss_ratio_edits[i].value())
            for i in range(len(self.loss_threshold_edits))
        ]
        self.config["api"]["ls_app_key"]       = self.edit_ls_key.text()
        self.config["api"]["ls_app_secret"]    = self.edit_ls_secret.text()
        self.config["api"]["ls_mock_key"]      = self.edit_mock_key.text()
        self.config["api"]["ls_mock_secret"]   = self.edit_mock_secret.text()
        self.config["api"]["krx_key"]          = self.edit_krx_key.text()
        self.config["notify"]["kakao_token"]   = self.edit_kakao.text()
        self.config["notify"]["telegram_token"]= self.edit_telegram.text()
        self.config["notify"]["telegram_chat_id"] = self.edit_chat_id.text()
        self.config["data"]["data_path"]       = self.edit_data_path.text()
        self.config["data"]["period"]          = self.combo_period.currentText()
        print("[설정저장] config.json 저장 중...")
        save_config(self.config)
        print("[설정저장] config.json 저장 완료, AI 조건 저장 시작...")
        self._save_ai_conditions()
        print("[설정저장] 전체 저장 완료")
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "저장", "설정이 저장되었습니다.")

    # ── 탭 1: 계좌·매수 설정 ──
    def _tab_account(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        grp = QGroupBox("매수 설정")
        grid = QGridLayout(grp)

        grid.addWidget(QLabel("종목당 매수금액 (원):"), 0, 0)
        self.edit_buy_amount = QLineEdit("1,000,000")
        self.edit_buy_amount.textChanged.connect(self._format_comma_field)
        grid.addWidget(self.edit_buy_amount, 0, 1)

        grid.addWidget(QLabel("최대 보유 종목 수:"), 1, 0)
        self.spin_max_stocks = QSpinBox()
        self.spin_max_stocks.setRange(1, 20)
        self.spin_max_stocks.setValue(5)
        grid.addWidget(self.spin_max_stocks, 1, 1)

        grid.addWidget(QLabel("매매 시작 시간:"), 2, 0)
        self.edit_start_time = QLineEdit("09:05")
        grid.addWidget(self.edit_start_time, 2, 1)

        grid.addWidget(QLabel("매매 종료 시간:"), 3, 0)
        self.edit_end_time = QLineEdit("15:20")
        grid.addWidget(self.edit_end_time, 3, 1)

        grid.addWidget(QLabel("일일 최대 손실 한도 (%):"), 4, 0)
        self.spin_risk = QDoubleSpinBox()
        self.spin_risk.setRange(0.0, 20.0)
        self.spin_risk.setValue(3.0)
        self.spin_risk.setSuffix(" %")
        grid.addWidget(self.spin_risk, 4, 1)

        layout.addWidget(grp)
        layout.addStretch()
        return w

    # ── 탭 2: 수익·손실 설정 ──
    def _tab_profit(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # 안내
        hint = QLabel("0 = AI 능동 대응 (고려사항 기반) | 값 입력 = 해당 기준 적용")
        hint.setStyleSheet("color: #444444; font-size: 11px; margin-bottom: 4px;")
        layout.addWidget(hint)

        grp_profit = QGroupBox("수익 정산 (단계별 분할 매도)")
        grid_p = QGridLayout(grp_profit)
        grid_p.addWidget(QLabel(""), 0, 0)
        grid_p.addWidget(QLabel("수익률 (%)"), 0, 1)
        grid_p.addWidget(QLabel("매도 비율 (%)"), 0, 2)
        for col in range(3):
            grid_p.setColumnStretch(col, 1)

        stages = [("1차", 3.0, 20.0), ("2차", 5.0, 20.0), ("3차", 8.0, 20.0),
                  ("4차", 12.0, 20.0), ("5차", 20.0, 20.0)]
        self.profit_edits = []
        self.sell_ratio_edits = []
        for i, (label, pct_val, ratio_val) in enumerate(stages):
            grid_p.addWidget(QLabel(f"{label}:"), i + 1, 0)
            # 수익률
            edit_pct = QDoubleSpinBox()
            edit_pct.setRange(0.0, 100.0)
            edit_pct.setValue(pct_val)
            edit_pct.setSuffix(" %")
            edit_pct.setToolTip("0 = AI 능동 대응")
            grid_p.addWidget(edit_pct, i + 1, 1)
            self.profit_edits.append(edit_pct)
            # 매도 비율
            edit_ratio = QDoubleSpinBox()
            edit_ratio.setRange(0.0, 100.0)
            edit_ratio.setValue(ratio_val)
            edit_ratio.setSuffix(" %")
            edit_ratio.setToolTip("해당 수익률 도달 시 보유량의 몇 % 매도")
            grid_p.addWidget(edit_ratio, i + 1, 2)
            self.sell_ratio_edits.append(edit_ratio)

        # 기존 손절 기준 (숨김, 호환용)
        self.spin_loss = QDoubleSpinBox()
        self.spin_loss.setRange(0.0, 30.0)
        self.spin_loss.setValue(0.0)
        self.spin_loss.hide()

        grp_loss = QGroupBox("손실 정산 (단계별 분할 손절)")
        grid_l = QGridLayout(grp_loss)
        grid_l.addWidget(QLabel(""), 0, 0)
        lbl_lt = QLabel("손실률 (%)")
        lbl_lt.setAlignment(Qt.AlignCenter)
        grid_l.addWidget(lbl_lt, 0, 1)
        eq2 = QLabel("=")
        eq2.setAlignment(Qt.AlignCenter)
        grid_l.addWidget(eq2, 0, 2)
        lbl_lr = QLabel("매도 비율 (%)")
        lbl_lr.setAlignment(Qt.AlignCenter)
        grid_l.addWidget(lbl_lr, 0, 3)

        loss_defaults = [(-3.0, 33.0), (-5.0, 33.0), (-7.0, 100.0)]
        self.loss_threshold_edits = []
        self.loss_ratio_edits = []
        for i, (thresh, ratio) in enumerate(loss_defaults):
            grid_l.addWidget(QLabel(f"{i+1}차:"), i + 1, 0)
            edit_thresh = QDoubleSpinBox()
            edit_thresh.setRange(-50.0, 0.0)
            edit_thresh.setValue(thresh)
            edit_thresh.setSuffix(" %")
            edit_thresh.setToolTip("해당 손실률 도달 시 분할 매도")
            grid_l.addWidget(edit_thresh, i + 1, 1)
            self.loss_threshold_edits.append(edit_thresh)

            eq = QLabel("=")
            eq.setAlignment(Qt.AlignCenter)
            grid_l.addWidget(eq, i + 1, 2)

            edit_ratio = QDoubleSpinBox()
            edit_ratio.setRange(0.0, 100.0)
            edit_ratio.setValue(ratio)
            edit_ratio.setSuffix(" %")
            edit_ratio.setToolTip("보유량의 몇 % 매도 (100% = 전량)")
            grid_l.addWidget(edit_ratio, i + 1, 3)
            self.loss_ratio_edits.append(edit_ratio)

        grid_l.setColumnStretch(0, 0)
        grid_l.setColumnStretch(1, 1)
        grid_l.setColumnStretch(2, 0)
        grid_l.setColumnStretch(3, 1)

        layout.addWidget(grp_profit)
        layout.addWidget(grp_loss)
        layout.addStretch()
        return w

    # ── 탭 3: 조건식 편집 ──
    def _tab_ai_condition(self):
        """AI 조건 편집기 탭 - 매수스크리닝 / 고려사항점수 / 매도조건"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        # 점수 임계값 행 (1줄) — 소형 스타일
        bar_style = "font-size:11px;"
        spin_style = "QSpinBox { font-size:11px; padding:1px 2px; }"
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        row1.setContentsMargins(0, 0, 0, 0)

        def _make_spin(rng, suffix, width=55, step=1, tip=""):
            s = QSpinBox()
            s.setRange(*rng)
            s.setSuffix(suffix)
            s.setFixedWidth(width)
            s.setSingleStep(step)
            s.setStyleSheet(spin_style)
            s.setButtonSymbols(QSpinBox.NoButtons)
            if tip:
                s.setToolTip(tip)
            return s

        def _lbl(text):
            lb = QLabel(text)
            lb.setStyleSheet(bar_style)
            return lb

        row1.addWidget(_lbl("매수"))
        self.spin_buy_thresh = _make_spin((0, 500), "점")
        row1.addWidget(self.spin_buy_thresh)
        row1.addSpacing(6)
        row1.addWidget(_lbl("보유"))
        self.spin_hold_thresh = _make_spin((0, 100), "점")
        row1.addWidget(self.spin_hold_thresh)
        row1.addSpacing(6)
        row1.addWidget(_lbl("매도"))
        self.spin_sell_thresh = _make_spin((0, 100), "점")
        row1.addWidget(self.spin_sell_thresh)
        row1.addSpacing(6)
        row1.addWidget(_lbl("관망"))
        self.spin_sell_watch = _make_spin((0, 100), "점")
        row1.addWidget(self.spin_sell_watch)
        row1.addSpacing(12)
        row1.addWidget(_lbl("스캔"))
        self.spin_scan_interval = _make_spin((5, 3600), "초", tip="AI 전 종목 스캔 주기")
        row1.addWidget(self.spin_scan_interval)
        row1.addSpacing(6)
        row1.addWidget(_lbl("최대"))
        self.spin_max_scan = _make_spin((100, 5000), "개", width=65, step=100, tip="한 번에 스캔할 최대 종목 수")
        row1.addWidget(self.spin_max_scan)
        row1.addSpacing(6)
        row1.addWidget(_lbl("재매수"))
        self.spin_rebuy_cooldown = _make_spin((0, 1440), "분", tip="당일 매도 후 재매수 금지 시간 (0=즉시)")
        row1.addWidget(self.spin_rebuy_cooldown)
        row1.addStretch()
        layout.addLayout(row1)

        # 서브 탭
        sub_tabs = QTabWidget()
        sub_tabs.addTab(self._ai_cond_subtab("scoring_core"),  "⭐ 핵심 조건")
        sub_tabs.addTab(self._ai_cond_subtab("scoring_bonus"),"✨ 고려사항 (가점)")
        sub_tabs.addTab(self._ai_cond_subtab("sell"),        "🔴 매도 스크리닝")
        sub_tabs.addTab(self._ai_cond_subtab("sell_scoring"),"🟠 매도 고려사항")
        layout.addWidget(sub_tabs)

        # 기본값 복원 버튼만 (저장은 하단 "💾 저장" 버튼 하나로 통합)
        btn_defaults = QPushButton("🔄 기본값 복원")
        btn_defaults.setObjectName("btn_settings")
        btn_defaults.setToolTip("engine_config.json의 defaults 섹션 값으로 복원")
        btn_defaults.clicked.connect(self._restore_ai_defaults)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_defaults)
        layout.addLayout(btn_row)

        # 초기값 로드
        self._load_ai_conditions()
        return w

    def _primary_filter_subtab(self):
        """1차 필터 설정 서브탭"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.setSpacing(4)

        # ── 서버 조건검색 (t1866/t1859) ──
        grp_sv = QGroupBox("서버 조건검색")
        from PyQt5.QtWidgets import QGridLayout as _GL
        sv_grid = QGridLayout(grp_sv)

        # 체크박스
        self._pf_use_server = QCheckBox("  서버 조건검색 사용")
        self._pf_use_server.setToolTip("HTS에서 저장한 조건검색을 1차 필터로 사용 (훨씬 빠름)")
        self._pf_use_server.setStyleSheet(
            "QCheckBox { color: #dfe6e9; font-weight: bold; font-size: 12px; spacing: 8px; }"
            "QCheckBox::indicator { width: 22px; height: 22px; border: 2px solid #888; border-radius: 3px; background: #2d3436; }"
        )
        def _update_sv_text(checked):
            if checked:
                self._pf_use_server.setText("  ✔ 서버 조건검색 사용")
                self._pf_use_server.setStyleSheet(
                    "QCheckBox { color: #00b894; font-weight: bold; font-size: 12px; spacing: 8px; }"
                    "QCheckBox::indicator { width: 22px; height: 22px; border: 2px solid #00b894; border-radius: 3px; background: #00b894; }"
                )
            else:
                self._pf_use_server.setText("  서버 조건검색 사용")
                self._pf_use_server.setStyleSheet(
                    "QCheckBox { color: #dfe6e9; font-weight: bold; font-size: 12px; spacing: 8px; }"
                    "QCheckBox::indicator { width: 22px; height: 22px; border: 2px solid #888; border-radius: 3px; background: #2d3436; }"
                )
        self._pf_use_server.toggled.connect(_update_sv_text)
        sv_grid.addWidget(self._pf_use_server, 0, 0)

        # ── 매수 조건 ──
        lbl_buy = QLabel("매수 조건:")
        lbl_buy.setStyleSheet("color: #00b894; font-weight: bold;")
        sv_grid.addWidget(lbl_buy, 1, 0)
        self._pf_condition_combo = QComboBox()
        self._pf_condition_combo.setFixedWidth(280)
        self._pf_condition_combo.setPlaceholderText("조건검색 목록을 불러오세요")
        sv_grid.addWidget(self._pf_condition_combo, 1, 1)

        # ── 목록 불러오기 버튼 + 상태 ──
        btn_load_cond = QPushButton("📋 목록 불러오기")
        btn_load_cond.setStyleSheet("font-size: 11px; padding: 3px 8px;")
        btn_load_cond.clicked.connect(self._load_condition_list)
        sv_grid.addWidget(btn_load_cond, 1, 2)

        self._pf_sv_status = QLabel("")
        self._pf_sv_status.setStyleSheet("color: #444444; font-size: 11px;")
        sv_grid.addWidget(self._pf_sv_status, 1, 3)

        layout.addWidget(grp_sv)
        layout.addStretch()

        # 더미 참조 (저장/로드 호환용)
        self._pf_market = QComboBox()
        self._pf_price_min = QSpinBox()
        self._pf_price_max = QSpinBox()
        self._pf_min_vol = QSpinBox()
        self._pf_min_amount = QSpinBox()
        self._pf_enabled = QCheckBox()
        self._pf_enabled.setChecked(True)
        self._ai_tbl_primary_filter = QTableWidget(0, 3)
        self._pf_status = QLabel("")

        return w

    def _load_condition_list(self):
        """서버 조건검색 목록 불러오기 (xingAPI t1866)"""
        try:
            # MainWindow에서 xing_api 가져오기
            main_win = None
            for w in QApplication.topLevelWidgets():
                if hasattr(w, 'xing_api'):
                    main_win = w
                    break

            if not main_win or not main_win.xing_api or not main_win.xing_api.is_connected():
                self._pf_sv_status.setText("❌ xingAPI 미연결")
                return

            conditions = main_win.xing_api.get_server_conditions()
            self._pf_condition_combo.clear()
            if not conditions:
                self._pf_sv_status.setText("❌ 저장된 조건검색 없음")
                return

            for c in conditions:
                self._pf_condition_combo.addItem(c['name'], c['index'])
            self._pf_sv_status.setText(f"✅ {len(conditions)}개 조건 로드")

            # 저장된 선택값 복원
            try:
                base = os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                cfg_path = os.path.join(base, get_engine_config_filename())
                with open(cfg_path, "r", encoding="utf-8") as f:
                    eng_cfg = json.load(f)
                saved_index = eng_cfg.get("primary_filter", {}).get("server_condition_index", "")
                if saved_index:
                    for i in range(self._pf_condition_combo.count()):
                        if self._pf_condition_combo.itemData(i) == saved_index:
                            self._pf_condition_combo.setCurrentIndex(i)
                            break
            except Exception:
                pass

        except Exception as e:
            self._pf_sv_status.setText(f"❌ 오류: {e}")
            # 디버그 파일
            try:
                import traceback
                _bd = os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                with open(os.path.join(_bd, "debug_t1866.txt"), "w", encoding="utf-8") as _df:
                    _df.write(f"error: {e}\n")
                    _df.write(traceback.format_exc())
            except Exception:
                pass

    def _update_pf_status(self):
        """1차 필터 결과 상태 표시"""
        try:
            from ai_engine.core.primary_filter import _get_filtered_path
            path = _get_filtered_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ts = data.get("timestamp", "")[:16].replace("T", " ")
                cnt = data.get("filtered_count", 0)
                total = data.get("total_universe", 0)
                self._pf_status.setText(f"마지막: {ts} | {total} → {cnt}종목")
            else:
                self._pf_status.setText("필터 미실행")
        except Exception:
            self._pf_status.setText("필터 미실행")

    def _run_primary_filter(self):
        """1차 필터 수동 실행 (AI엔진에 명령 전송)"""
        try:
            from ai_engine.comm.command_reader import write_command
            write_command("run_filter")
            self._pf_status.setText("필터 실행 요청됨...")
        except Exception as e:
            self._pf_status.setText(f"오류: {e}")

    def _ai_cond_subtab(self, group):
        """조건 그룹별 서브탭 위젯 생성"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(4, 4, 4, 4)

        is_scoring = group in ("scoring", "scoring_core", "scoring_bonus", "sell_scoring")
        has_value = group in ("scoring", "scoring_core", "scoring_bonus", "sell_scoring", "sell")

        # 안내
        if group == "scoring_core":
            hint = QLabel("번호: 전략식 참조용 | 조건명 자유 입력 | 설명: 메모 | 점수: 충족 시 획득 점수")
        elif group == "scoring_bonus":
            hint = QLabel("☑ 활성/비활성 | 조건명 자유 입력 | 설명: 메모 | 점수: 충족 시 가점")
        elif is_scoring:
            hint = QLabel("☑ 활성/비활성 | 조건명 자유 입력 | 설명: 메모 | W: 가중치")
        elif group == "sell":
            hint = QLabel("☑ 활성/비활성 | 조건명 직접 입력 | 설명: 메모 | 임계값: 판단 기준값")
        else:
            hint = QLabel("☑ 활성/비활성 | 조건명 직접 입력 가능")
        hint.setStyleSheet("color: #444444; font-size: 10px;")
        layout.addWidget(hint)

        # 테이블: scoring_core는 [번호][조건명][설명][점수], 나머지는 [☑][조건명][설명][값]
        is_core = group == "scoring_core"
        if has_value:
            tbl = QTableWidget(0, 4)
            val_label = "점수" if group in ("scoring_core", "scoring_bonus") else ("W" if is_scoring else "임계")
            col0_label = "No" if is_core else ""
            tbl.setHorizontalHeaderLabels([col0_label, "조건명", "설명", val_label])
            tbl.setColumnWidth(0, 30)
            tbl.setColumnWidth(1, 160)
            tbl.setColumnWidth(3, 45)
        else:
            tbl = QTableWidget(0, 3)
            tbl.setHorizontalHeaderLabels(["", "조건명", "설명"])
            tbl.setColumnWidth(0, 30)
            tbl.setColumnWidth(1, 160)
        tbl.horizontalHeader().setStretchLastSection(not has_value)
        if has_value:
            tbl.horizontalHeader().setSectionResizeMode(2, tbl.horizontalHeader().Stretch)
        else:
            tbl.horizontalHeader().setSectionResizeMode(2, tbl.horizontalHeader().Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(
            "QTableWidget { background:#243e64; alternate-background-color:#0f1e30; "
            "font-size:11px; }"
            "QTableWidget::item { padding:2px 4px; }"
            "QHeaderView::section { font-size:11px; padding:3px; }"
        )
        tbl.verticalHeader().setDefaultSectionSize(26)
        layout.addWidget(tbl)
        setattr(self, f"_ai_tbl_{group}", tbl)

        # 버튼 행
        btn_row = QHBoxLayout()
        btn_add = QPushButton("＋ 추가")
        btn_add.setFixedWidth(70)
        btn_add.clicked.connect(lambda: self._ai_add_row(group))
        btn_del = QPushButton("－ 삭제")
        btn_del.setFixedWidth(70)
        btn_del.clicked.connect(lambda: self._ai_del_row(group))
        btn_up = QPushButton("▲")
        btn_up.setFixedWidth(40)
        btn_up.clicked.connect(lambda: self._ai_move_row(group, -1))
        btn_dn = QPushButton("▼")
        btn_dn.setFixedWidth(40)
        btn_dn.clicked.connect(lambda: self._ai_move_row(group, 1))
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addWidget(btn_up)
        btn_row.addWidget(btn_dn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── 핵심 조건 전용: 전략식 입력 ──
        if group == "scoring_core":
            formula_label = QLabel("📋 전략식 (조건번호 and/or 조합, 예: (3 and 4 and 5) or (4 and 5 and 8))")
            formula_label.setStyleSheet("color: #444444; font-size: 10px; margin-top: 8px;")
            layout.addWidget(formula_label)

            from PyQt5.QtWidgets import QLineEdit
            self._formula_edit = QLineEdit()
            self._formula_edit.setPlaceholderText("예: (3 and 4 and 5 and 6 and 7) or (4 and 5 and 8)")
            self._formula_edit.setStyleSheet(
                "QLineEdit { background:#1a2a44; color:#ffffff; border:1px solid #3a5a8a;"
                "            padding:6px 8px; font-size:12px; font-family:Consolas; }"
                "QLineEdit:focus { border:1px solid #5a9aff; }"
            )
            self._formula_edit.setMinimumHeight(32)
            layout.addWidget(self._formula_edit)

        return w

    # ── AI 조건 행 추가/삭제/이동 ──
    def _ai_add_row(self, group):
        is_scoring = group in ("scoring", "scoring_core", "scoring_bonus", "sell_scoring")
        has_value = group in ("scoring", "scoring_core", "scoring_bonus", "sell_scoring", "sell")
        is_core = group == "scoring_core"
        tbl = getattr(self, f"_ai_tbl_{group}")
        row = tbl.rowCount()
        tbl.insertRow(row)
        if is_core:
            # 핵심조건: 번호 자동부여 (읽기전용)
            num_item = QTableWidgetItem(str(row + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(row, 0, num_item)
        else:
            # 나머지: 체크박스
            chk = QTableWidgetItem()
            chk.setCheckState(Qt.Checked)
            chk.setTextAlignment(Qt.AlignCenter)
            tbl.setItem(row, 0, chk)
        tbl.setItem(row, 1, QTableWidgetItem("새 조건"))
        tbl.setItem(row, 2, QTableWidgetItem(""))
        if has_value:
            tbl.setItem(row, 3, QTableWidgetItem("10" if is_scoring else "0"))
        tbl.scrollToBottom()
        tbl.editItem(tbl.item(row, 1))

    def _ai_del_row(self, group):
        tbl = getattr(self, f"_ai_tbl_{group}")
        rows = sorted(set(i.row() for i in tbl.selectedItems()), reverse=True)
        for r in rows:
            tbl.removeRow(r)
        # 핵심조건 번호 재정렬
        if group == "scoring_core":
            for r in range(tbl.rowCount()):
                num_item = tbl.item(r, 0)
                if num_item:
                    num_item.setText(str(r + 1))

    def _ai_move_row(self, group, direction):
        tbl = getattr(self, f"_ai_tbl_{group}")
        row = tbl.currentRow()
        if row < 0:
            return
        target = row + direction
        if target < 0 or target >= tbl.rowCount():
            return
        is_core = group == "scoring_core"
        # col 0(번호/체크)는 건드리지 않고, 나머지 열만 교환
        for col in range(1, tbl.columnCount()):
            a = tbl.item(row, col)
            b = tbl.item(target, col)
            a_text = a.text() if a else ""
            b_text = b.text() if b else ""
            if a: a.setText(b_text)
            if b: b.setText(a_text)
        if not is_core:
            # 체크박스 상태 교환
            a = tbl.item(row, 0)
            b = tbl.item(target, 0)
            a_check = a.checkState() if a and a.flags() & Qt.ItemIsUserCheckable else Qt.Unchecked
            b_check = b.checkState() if b and b.flags() & Qt.ItemIsUserCheckable else Qt.Unchecked
            if a: a.setCheckState(b_check)
            if b: b.setCheckState(a_check)
        # 핵심조건 번호는 행 순서 고정이므로 교환 불필요
        tbl.setCurrentCell(target, tbl.currentColumn())

    # ── engine_config.json 로드/저장 ──
    def _get_config_path(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, get_engine_config_filename())

    def _load_ai_conditions(self):
        path = self._get_config_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.spin_buy_thresh.setValue(cfg.get("thresholds", {}).get("buy", 80))
            self.spin_hold_thresh.setValue(cfg.get("thresholds", {}).get("hold", 50))
            self.spin_sell_thresh.setValue(cfg.get("thresholds", {}).get("sell_confirm", 75))
            self.spin_sell_watch.setValue(cfg.get("thresholds", {}).get("sell_watch", 50))
            self.spin_scan_interval.setValue(cfg.get("scan_interval_seconds", 60))
            self.spin_max_scan.setValue(cfg.get("max_scan_stocks", 2000))
            self.spin_rebuy_cooldown.setValue(cfg.get("defaults", {}).get("rebuy_cooldown_min", 30))

            # 1차 필터 로드 (탭이 존재할 때만)
            if hasattr(self, '_pf_enabled'):
                pf = cfg.get("primary_filter", {})
                self._pf_enabled.setChecked(pf.get("enabled", True))
                self._pf_use_server.setChecked(pf.get("use_server_condition", False))
                saved_sv_name = pf.get("server_condition_name", "")
                saved_sv_index = pf.get("server_condition_index", "")
                if saved_sv_name and saved_sv_index:
                    self._pf_condition_combo.clear()
                    self._pf_condition_combo.addItem(saved_sv_name, saved_sv_index)
                    self._pf_condition_combo.setCurrentIndex(0)
                market_map = {"0": 0, "1": 1, "2": 2}
                self._pf_market.setCurrentIndex(market_map.get(str(pf.get("market", "0")), 0))
                self._pf_price_min.setValue(pf.get("price_min", 1000))
                self._pf_price_max.setValue(pf.get("price_max", 500000))
                self._pf_min_vol.setValue(pf.get("min_volume_5d", 10000))
                self._pf_min_amount.setValue(pf.get("min_amount_1d", 10))
                tbl_pf = self._ai_tbl_primary_filter
                tbl_pf.setRowCount(0)
                for item in pf.get("conditions", []):
                    r = tbl_pf.rowCount()
                    tbl_pf.insertRow(r)
                    chk = QTableWidgetItem()
                    chk.setCheckState(Qt.Checked if item.get("enabled", True) else Qt.Unchecked)
                    chk.setTextAlignment(Qt.AlignCenter)
                    tbl_pf.setItem(r, 0, chk)
                    tbl_pf.setItem(r, 1, QTableWidgetItem(item.get("name", "")))
                    tbl_pf.setItem(r, 2, QTableWidgetItem(str(item.get("description", ""))))

            for group in ("scoring_core", "scoring_bonus", "sell", "sell_scoring"):
                is_scoring = group in ("scoring_core", "scoring_bonus", "sell_scoring")
                has_value = group in ("scoring_core", "scoring_bonus", "sell_scoring", "sell")
                tbl = getattr(self, f"_ai_tbl_{group}", None)
                if tbl is None:
                    continue
                tbl.setRowCount(0)
                items = cfg.get(group, [])
                if not items and group == "scoring_core":
                    items = cfg.get("scoring", [])
                is_core = group == "scoring_core"
                for item in items:
                    r = tbl.rowCount()
                    tbl.insertRow(r)
                    if is_core:
                        # 핵심조건: 번호 (읽기전용)
                        num_item = QTableWidgetItem(str(r + 1))
                        num_item.setTextAlignment(Qt.AlignCenter)
                        num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
                        tbl.setItem(r, 0, num_item)
                    else:
                        # 나머지: 체크박스
                        chk = QTableWidgetItem()
                        chk.setCheckState(Qt.Checked if item.get("enabled", True) else Qt.Unchecked)
                        chk.setTextAlignment(Qt.AlignCenter)
                        tbl.setItem(r, 0, chk)
                    tbl.setItem(r, 1, QTableWidgetItem(item.get("name", "")))
                    tbl.setItem(r, 2, QTableWidgetItem(str(item.get("description", ""))))
                    if has_value:
                        val_key = "weight" if is_scoring else "threshold"
                        tbl.setItem(r, 3, QTableWidgetItem(str(item.get(val_key, 10 if is_scoring else 0))))

            # 전략식 로드
            if hasattr(self, '_formula_edit'):
                formula = cfg.get("scoring_formula", "")
                # 하위호환: scoring_combos → 전략식 자동 변환
                if not formula and cfg.get("scoring_combos"):
                    parts = []
                    for combo in cfg["scoring_combos"]:
                        if combo.get("enabled", True):
                            nums = " and ".join(str(c) for c in combo.get("conditions", []))
                            parts.append(f"({nums})")
                    formula = " or ".join(parts)
                self._formula_edit.setText(formula)
        except Exception as e:
            print(f"[AI조건] 로드 실패: {e}")

    def _restore_ai_defaults(self):
        """engine_config.json의 defaults 섹션에서 기본값 복원"""
        path = self._get_config_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            defaults = cfg.get("defaults", {})
            if not defaults:
                QMessageBox.information(self, "기본값", "defaults 섹션이 없습니다.\n먼저 AI 조건을 저장하세요.")
                return
            reply = QMessageBox.question(
                self, "기본값 복원",
                "모든 계산기 파라미터(MACD, RSI, 볼린저, 수급, 박스권, 페널티 점수)를\n"
                "기본값으로 복원하시겠습니까?\n\n"
                "※ 조건 목록(스크리닝/고려사항/매도)은 변경되지 않습니다.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            # defaults를 초기값으로 리셋
            cfg["defaults"] = {
                "macd": [10, 20, 9],
                "rsi_period": 14,
                "bollinger_period": 20,
                "bollinger_k": 2.0,
                "supply_days": 5,
                "box_period": 20,
                "rebuy_cooldown_min": 30,
                "penalty_points": {
                    "하락종목": 20, "지수저점": 15, "지수급락": 25,
                    "이평선이탈": 15, "이격도": 10, "거래량음봉": 10,
                    "거래량급감": 10, "외인기관매도": 15, "프로그램피크": 15,
                    "테마급락": 15, "시간강화": 15
                }
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            # 캐시 무효화
            try:
                from ai_engine.conditions._config_helper import reload_defaults
                reload_defaults()
            except Exception:
                pass
            QMessageBox.information(self, "기본값 복원", "기본값으로 복원되었습니다.")
            print("[AI조건] 기본값 복원 완료")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"기본값 복원 실패: {e}")

    def _save_ai_conditions(self):
        path = self._get_config_path()
        print(f"[설정저장] 시작 → {path}")
        try:
            # 기존 defaults 보존
            existing_defaults = {}
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                    existing_defaults = existing.get("defaults", {})
                except Exception:
                    pass
            existing_defaults["rebuy_cooldown_min"] = self.spin_rebuy_cooldown.value()
            print(f"[설정저장] defaults 로드 완료, rebuy_cooldown={existing_defaults['rebuy_cooldown_min']}")
            # 1차 필터 조건 수집 (탭이 존재할 때만)
            pf_section = {}
            if hasattr(self, '_pf_enabled'):
                pf_conditions = []
                tbl_pf = self._ai_tbl_primary_filter
                for r in range(tbl_pf.rowCount()):
                    chk = tbl_pf.item(r, 0)
                    name_item = tbl_pf.item(r, 1)
                    desc_item = tbl_pf.item(r, 2)
                    pf_conditions.append({
                        "enabled": (chk.checkState() == Qt.Checked) if chk else True,
                        "name": name_item.text() if name_item else "",
                        "description": desc_item.text() if desc_item else ""
                    })
                market_map = {0: "0", 1: "1", 2: "2"}
                sv_condition_index = ""
                sv_condition_name = ""
                if self._pf_condition_combo.currentIndex() >= 0:
                    sv_condition_index = self._pf_condition_combo.currentData() or ""
                    sv_condition_name = self._pf_condition_combo.currentText() or ""
                pf_section = {
                    "enabled": self._pf_enabled.isChecked(),
                    "use_server_condition": self._pf_use_server.isChecked(),
                    "server_condition_index": sv_condition_index,
                    "server_condition_name": sv_condition_name,
                    "market": market_map.get(self._pf_market.currentIndex(), "0"),
                    "price_min": self._pf_price_min.value(),
                    "price_max": self._pf_price_max.value(),
                    "min_volume_5d": self._pf_min_vol.value(),
                    "min_amount_1d": self._pf_min_amount.value(),
                    "conditions": pf_conditions
                }
            else:
                # 기존 config에서 primary_filter 보존
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            pf_section = json.load(f).get("primary_filter", {})
                    except Exception:
                        pass

            cfg = {
                "version": "1.0",
                "primary_filter": pf_section,
                "defaults": existing_defaults,
                "thresholds": {
                    "buy":  self.spin_buy_thresh.value(),
                    "hold": self.spin_hold_thresh.value(),
                    "sell_confirm": self.spin_sell_thresh.value(),
                    "sell_watch":   self.spin_sell_watch.value()
                },
                "scan_interval_seconds": self.spin_scan_interval.value(),
                "max_scan_stocks": self.spin_max_scan.value(),
                "scoring_core": [],
                "scoring_bonus": [],
                "scoring_formula": "",
                "sell": [],
                "sell_scoring": []
            }
            # 전략식 저장
            if hasattr(self, '_formula_edit'):
                cfg["scoring_formula"] = self._formula_edit.text().strip()
            for group in ("scoring_core", "scoring_bonus", "sell", "sell_scoring"):
                is_scoring = group in ("scoring_core", "scoring_bonus", "sell_scoring")
                has_value = group in ("scoring_core", "scoring_bonus", "sell_scoring", "sell")
                tbl = getattr(self, f"_ai_tbl_{group}", None)
                if tbl is None:
                    print(f"[설정저장] ⚠ 테이블 없음: _ai_tbl_{group}")
                    continue
                print(f"[설정저장] {group} 테이블 행수: {tbl.rowCount()}")
                is_core = group == "scoring_core"
                for r in range(tbl.rowCount()):
                    # scoring_core: [번호](0), 나머지: [☑](0), 조건명(1), 설명(2), (값)(3)
                    chk  = tbl.item(r, 0)
                    name_item = tbl.item(r, 1)
                    desc_item = tbl.item(r, 2)
                    if is_core:
                        enabled = True  # 핵심조건은 항상 활성
                    else:
                        enabled = (chk.checkState() == Qt.Checked) if chk else True
                    entry = {
                        "enabled": enabled,
                        "name": name_item.text() if name_item else "",
                        "description": desc_item.text() if desc_item else ""
                    }
                    if has_value:
                        val_item = tbl.item(r, 3)
                        val_key = "weight" if is_scoring else "threshold"
                        try:
                            val = val_item.text() if val_item else ("10" if is_scoring else "0")
                            entry[val_key] = int(val) if "." not in val else float(val)
                        except Exception:
                            entry[val_key] = 10 if is_scoring else 0
                    cfg[group].append(entry)
                print(f"[설정저장] {group}: {len(cfg[group])}개 조건 수집")
            print(f"[설정저장] JSON 파일 쓰기 → {path}")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            print(f"[설정저장] JSON 저장 완료")
            # 디버그: 저장 내용 상세 기록
            _dbg_path = os.path.join(os.path.dirname(path), "debug_save.txt")
            with open(_dbg_path, "w", encoding="utf-8") as _df:
                _df.write(f"=== 설정 저장 {datetime.now().strftime('%H:%M:%S')} ===\n")
                _df.write(f"save_path: {path}\n\n")
                _core = cfg.get('scoring_core', [])
                _bonus = cfg.get('scoring_bonus', [])
                _df.write(f"[핵심 조건] ({sum(1 for c in _core if c['enabled'])}/{len(_core)} 활성)\n")
                for c in _core:
                    tag = "✓" if c["enabled"] else "✗"
                    _df.write(f"  {tag} {c['name']} | {c.get('description','')} (점수={c.get('weight',0)})\n")
                _df.write(f"\n[고려사항 가점] ({sum(1 for c in _bonus if c['enabled'])}/{len(_bonus)} 활성)\n")
                for c in _bonus:
                    tag = "✓" if c["enabled"] else "✗"
                    _df.write(f"  {tag} {c['name']} | {c.get('description','')} (가점={c.get('weight',0)})\n")
                _df.write(f"\n[매도 스크리닝] ({sum(1 for c in cfg['sell'] if c['enabled'])}/{len(cfg['sell'])} 활성)\n")
                for i, c in enumerate(cfg["sell"]):
                    tag = "✓" if c["enabled"] else "✗"
                    _df.write(f"  {tag} {c['name']} | {c.get('description','')} (t={c.get('threshold',0)})\n")
                _df.write(f"\n[매도 고려사항] ({sum(1 for c in cfg['sell_scoring'] if c['enabled'])}/{len(cfg['sell_scoring'])} 활성)\n")
                for i, c in enumerate(cfg["sell_scoring"]):
                    tag = "✓" if c["enabled"] else "✗"
                    _df.write(f"  {tag} {c['name']} | {c.get('description','')} (w={c.get('weight',0)})\n")
            print(f"[AI조건] 저장 완료 → {path}")

            # ── AI 엔진에 재스캔 명령 전송 ──
            try:
                from ai_engine.comm.command_reader import write_command
                write_command("rescan")
                print("[AI조건] 재스캔 명령 전송")
            except Exception:
                pass

        except Exception as e:
            import traceback
            print(f"[AI조건] 저장 실패: {e}")
            print(traceback.format_exc())
            QMessageBox.warning(self, "저장 실패", f"AI 조건 저장 오류:\n{e}\n\n{traceback.format_exc()}")

    def _clear_scan_data(self):
        """이전 스캔 신호 파일 및 캐시 클리어"""
        try:
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(os.path.dirname(sys.executable))
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            # ai_signals 파일 비우기
            for fname in ("ai_signals_mock.json", "ai_signals_real.json", "ai_signals.json"):
                fpath = os.path.join(base, fname)
                if os.path.exists(fpath):
                    with open(fpath, "w", encoding="utf-8") as f:
                        json.dump({"signals": [], "scan_count": 0,
                                   "timestamp": datetime.now().isoformat()}, f)
                    print(f"[AI조건] 클리어: {fname}")
        except Exception as e:
            print(f"[AI조건] 클리어 실패: {e}")

    # ── 탭 4: API·계정 설정 ──
    def _tab_api(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # LS투자증권 로그인
        grp_login = QGroupBox("LS투자증권 로그인")
        grid_login = QGridLayout(grp_login)
        login_fields = [
            ("아이디:", "edit_ls_id"),
            ("비밀번호:", "edit_ls_pw"),
        ]
        for i, (label, attr) in enumerate(login_fields):
            grid_login.addWidget(QLabel(label), i, 0)
            edit = QLineEdit()
            if "비밀번호" in label:
                edit.setEchoMode(QLineEdit.Password)
            setattr(self, attr, edit)
            grid_login.addWidget(edit, i, 1)
        # 인증서 경로
        grid_login.addWidget(QLabel("인증서 경로:"), 2, 0)
        self.edit_cert_path = QLineEdit()
        self.edit_cert_path.setPlaceholderText("실투자 시 공인인증서 폴더 경로 (선택)")
        grid_login.addWidget(self.edit_cert_path, 2, 1)

        # 실투자 API (실계좌)
        grp_real = QGroupBox("실투자 API (실계좌)")
        grid_real = QGridLayout(grp_real)
        grid_real.addWidget(QLabel("App Key:"), 0, 0)
        self.edit_ls_key = QLineEdit()
        grid_real.addWidget(self.edit_ls_key, 0, 1)
        grid_real.addWidget(QLabel("App Secret:"), 1, 0)
        self.edit_ls_secret = QLineEdit()
        self.edit_ls_secret.setEchoMode(QLineEdit.Password)
        grid_real.addWidget(self.edit_ls_secret, 1, 1)
        note_real = QLabel("* LS투자증권 OpenAPI에서 실투자용 키 발급")
        note_real.setStyleSheet("color: #444444; font-size: 10px;")
        grid_real.addWidget(note_real, 2, 0, 1, 2)

        # 모의투자 API (모의계좌)
        grp_mock = QGroupBox("모의투자 API (모의계좌)")
        grid_mock = QGridLayout(grp_mock)
        grid_mock.addWidget(QLabel("App Key:"), 0, 0)
        self.edit_mock_key = QLineEdit()
        grid_mock.addWidget(self.edit_mock_key, 0, 1)
        grid_mock.addWidget(QLabel("App Secret:"), 1, 0)
        self.edit_mock_secret = QLineEdit()
        self.edit_mock_secret.setEchoMode(QLineEdit.Password)
        grid_mock.addWidget(self.edit_mock_secret, 1, 1)
        note_mock = QLabel("* LS투자증권 OpenAPI에서 모의투자용 키 발급 (포트 29443)")
        note_mock.setStyleSheet("color: #444444; font-size: 10px;")
        grid_mock.addWidget(note_mock, 2, 0, 1, 2)

        # 한국거래소(KRX) API
        grp_krx = QGroupBox("한국거래소(KRX) API")
        grid2 = QGridLayout(grp_krx)
        grid2.addWidget(QLabel("KRX API Key:"), 0, 0)
        self.edit_krx_key = QLineEdit()
        grid2.addWidget(self.edit_krx_key, 0, 1)

        layout.addWidget(grp_login)
        layout.addWidget(grp_real)
        layout.addWidget(grp_mock)
        layout.addWidget(grp_krx)
        layout.addStretch()
        return w

    # ── 탭 5: 알림 설정 ──
    def _tab_notify(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        grp = QGroupBox("메신저 알림")
        grid = QGridLayout(grp)
        grid.addWidget(QLabel("카카오톡 Token:"), 0, 0)
        self.edit_kakao = QLineEdit()
        grid.addWidget(self.edit_kakao, 0, 1)
        grid.addWidget(QLabel("텔레그램 Bot Token:"), 1, 0)
        self.edit_telegram = QLineEdit()
        grid.addWidget(self.edit_telegram, 1, 1)
        grid.addWidget(QLabel("텔레그램 Chat ID:"), 2, 0)
        self.edit_chat_id = QLineEdit()
        grid.addWidget(self.edit_chat_id, 2, 1)

        grp2 = QGroupBox("알림 항목")
        v = QVBoxLayout(grp2)
        self.chk_notify = {}
        items = ["매수 체결", "매도 체결", "손절 발동", "목표가 달성", "조건식 검색결과", "시스템 오류"]
        for item in items:
            chk = QCheckBox(item)
            chk.setChecked(True)
            v.addWidget(chk)
            self.chk_notify[item] = chk

        layout.addWidget(grp)
        layout.addWidget(grp2)
        layout.addStretch()
        return w

    # ── 탭 6: 데이터 소스 ──
    def _tab_data(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        # ── 과거 데이터 수집 ──
        grp = QGroupBox("📥 과거 데이터 수집 (AI 학습용)")
        grid = QGridLayout(grp)

        grid.addWidget(QLabel("수집 기간:"), 0, 0)
        self.combo_period = QComboBox()
        self.combo_period.addItems(["1년", "3년", "5년"])
        self.combo_period.setCurrentText("5년")
        grid.addWidget(self.combo_period, 0, 1)

        grid.addWidget(QLabel("데이터 소스:"), 1, 0)
        src_label = QLabel("네이버 금융 (API 키 불필요)")
        src_label.setStyleSheet("color: #000000;")
        grid.addWidget(src_label, 1, 1)

        # 수집 현황
        self.lbl_collect_status = QLabel("수집 현황: 확인 중...")
        self.lbl_collect_status.setStyleSheet("color: #555555; font-size: 11px;")
        grid.addWidget(self.lbl_collect_status, 2, 0, 1, 2)

        # 진행 상태
        self.lbl_collect_progress = QLabel("")
        self.lbl_collect_progress.setStyleSheet("color: #00b894; font-size: 11px;")
        grid.addWidget(self.lbl_collect_progress, 3, 0, 1, 2)

        # 버튼
        btn_layout_h = QHBoxLayout()
        self.btn_collect_start = QPushButton("📥 수집 시작")
        self.btn_collect_start.setObjectName("btn_settings")
        self.btn_collect_start.clicked.connect(self._start_data_collect)
        btn_layout_h.addWidget(self.btn_collect_start)

        btn_check = QPushButton("📊 현황 확인")
        btn_check.setObjectName("btn_settings")
        btn_check.clicked.connect(self._check_collect_stats)
        btn_layout_h.addWidget(btn_check)

        grid.addLayout(btn_layout_h, 4, 0, 1, 2)

        # ── 데이터 경로 ──
        grp2 = QGroupBox("저장 경로")
        grid2 = QGridLayout(grp2)
        grid2.addWidget(QLabel("데이터 저장 경로:"), 0, 0)
        self.edit_data_path = QLineEdit("C:/stock_trader/data")
        grid2.addWidget(self.edit_data_path, 0, 1)

        hint = QLabel("※ DB 파일: ai_engine.db (프로그램 폴더)")
        hint.setStyleSheet("color: #444444; font-size: 10px;")
        grid2.addWidget(hint, 1, 0, 1, 2)

        layout.addWidget(grp)
        layout.addWidget(grp2)
        layout.addStretch()

        # 초기 현황 로드
        QTimer.singleShot(500, self._check_collect_stats)

        # 수집 중이면 상태 복원
        if self.main_window and self.main_window._hist_collecting:
            self.btn_collect_start.setEnabled(False)
            self.btn_collect_start.setText("⏳ 수집 중...")
            self.lbl_collect_progress.setText(self.main_window._hist_collect_msg)
            # 주기적으로 메시지 업데이트
            self._collect_timer = QTimer()
            self._collect_timer.timeout.connect(self._sync_collect_status)
            self._collect_timer.start(2000)

        return w

    def _start_data_collect(self):
        """과거 데이터 수집 시작 (메인 윈도우에서 관리 — 설정창 닫아도 계속 수집)"""
        mw = self.main_window
        if not mw:
            self.lbl_collect_progress.setText("오류: 메인 윈도우 연결 실패")
            return

        # 이미 수집 중이면 중복 방지
        if mw._hist_collecting:
            self.lbl_collect_progress.setText("⏳ 이미 수집 진행 중...")
            return

        period_map = {"1년": 1, "3년": 3, "5년": 5}
        years = period_map.get(self.combo_period.currentText(), 5)

        self.btn_collect_start.setEnabled(False)
        self.btn_collect_start.setText("⏳ 수집 중...")
        self.lbl_collect_progress.setText("수집 준비 중...")
        mw._hist_collecting = True
        mw._hist_collect_msg = "수집 준비 중..."

        from threading import Thread

        def _run():
            try:
                from ai_engine.data.historical_collector import HistoricalCollector
                from ai_engine.db.database import init_db
                init_db()

                def _callback(msg):
                    mw._hist_collect_msg = msg
                    # 설정창이 열려있으면 UI도 업데이트
                    try:
                        if hasattr(self, 'lbl_collect_progress') and self.lbl_collect_progress.isVisible():
                            self.lbl_collect_progress.setText(msg)
                    except (RuntimeError, AttributeError):
                        pass  # 설정창 닫힌 경우 무시

                collector = HistoricalCollector()
                collector.collect_all(years=years, callback=_callback)
                mw._hist_collect_msg = "✅ 수집 완료!"
            except Exception as e:
                mw._hist_collect_msg = f"오류: {e}"
            finally:
                mw._hist_collecting = False
                try:
                    if hasattr(self, 'btn_collect_start') and self.btn_collect_start.isVisible():
                        self.btn_collect_start.setEnabled(True)
                        self.btn_collect_start.setText("📥 수집 시작")
                        self._check_collect_stats()
                except (RuntimeError, AttributeError):
                    pass

        t = Thread(target=_run, daemon=True)
        mw._hist_collect_thread = t
        t.start()

    def _sync_collect_status(self):
        """수집 진행 메시지 동기화 (설정창 재오픈 시)"""
        try:
            mw = self.main_window
            if mw and mw._hist_collecting:
                self.lbl_collect_progress.setText(mw._hist_collect_msg)
            else:
                # 수집 완료됨
                self.lbl_collect_progress.setText(mw._hist_collect_msg if mw else "")
                self.btn_collect_start.setEnabled(True)
                self.btn_collect_start.setText("📥 수집 시작")
                self._check_collect_stats()
                if hasattr(self, '_collect_timer'):
                    self._collect_timer.stop()
        except (RuntimeError, AttributeError):
            if hasattr(self, '_collect_timer'):
                self._collect_timer.stop()

    def _check_collect_stats(self):
        """수집 현황 통계 표시 + 완료 여부 판단"""
        try:
            from ai_engine.data.historical_collector import HistoricalCollector
            from ai_engine.db.database import init_db
            init_db()
            collector = HistoricalCollector()
            status = collector.get_collect_status()
            total = status["count"]

            if total == 0:
                self.lbl_collect_status.setText("수집 현황: 데이터 없음")
                self.lbl_collect_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
                return

            min_d = status["min_date"]
            max_d = status["max_date"]
            display_range = f"{min_d[:4]}.{min_d[4:6]}.{min_d[6:]} ~ {max_d[:4]}.{max_d[4:6]}.{max_d[6:]}"

            # 선택된 기간 대비 수집 완료 여부 판단
            period_map = {"1년": 1, "3년": 3, "5년": 5}
            years = period_map.get(self.combo_period.currentText(), 5)
            from datetime import datetime, timedelta
            target_start = datetime.now() - timedelta(days=years * 365)
            first_date = datetime.strptime(min_d, "%Y%m%d")

            if first_date <= target_start + timedelta(days=7):  # 7일 이내면 완료로 간주
                self.lbl_collect_status.setText(
                    f"✅ 수집 완료 | {total:,}건 | {display_range}"
                )
                self.lbl_collect_status.setStyleSheet("color: #00b894; font-size: 11px;")
            else:
                self.lbl_collect_status.setText(
                    f"⚠ 수집 중 | {total:,}건 | {display_range} (추가 수집 필요)"
                )
                self.lbl_collect_status.setStyleSheet("color: #fdcb6e; font-size: 11px;")
        except Exception as e:
            self.lbl_collect_status.setText(f"수집 현황: 확인 실패 ({e})")


# ─────────────────────────────────────────────
#  AI 엔진 토글 스위치 위젯
# ─────────────────────────────────────────────
class AIToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)   # True=ON, False=OFF

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked  = False
        self._enabled  = True
        self._stopping = False
        self.setFixedSize(68, 20)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, val: bool):
        self._checked  = val
        self._stopping = False
        self.setEnabled(True)
        self.update()

    def setStopping(self):
        """정지 중 상태 (비활성)"""
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
        from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QFont
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        r = h // 2   # 반지름

        # 배경 트랙
        if self._stopping:
            track_color = QColor("#636e72")
        elif self._checked:
            track_color = QColor("#00b894")
        else:
            track_color = QColor("#2d3436")

        p.setBrush(QBrush(track_color))
        p.setPen(QPen(QColor("#4a545a"), 1))
        p.drawRoundedRect(0, 0, w, h, r, r)

        # 슬라이더 원
        circle_d = h - 6
        if self._stopping:
            cx = w // 2 - circle_d // 2   # 가운데
            circle_color = QColor("#b2bec3")
        elif self._checked:
            cx = w - circle_d - 3          # 오른쪽
            circle_color = QColor("#ffffff")
        else:
            cx = 3                          # 왼쪽
            circle_color = QColor("#636e72")

        p.setBrush(QBrush(circle_color))
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx, 3, circle_d, circle_d)

        # 텍스트
        if self._stopping:
            text = "정지 중..."
            text_color = QColor("#dfe6e9")
        elif self._checked:
            text = "동작중"
            text_color = QColor("#ffffff")
        else:
            text = "AI엔진"
            text_color = QColor("#888888")

        font = QFont("맑은 고딕", 7, QFont.Bold)
        p.setFont(font)
        p.setPen(QPen(text_color))
        # 텍스트 위치: ON이면 왼쪽, OFF이면 오른쪽
        if self._checked:
            text_rect = self.rect().adjusted(8, 0, -(circle_d + 8), 0)
        else:
            text_rect = self.rect().adjusted(circle_d + 6, 0, -4, 0)
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignCenter, text)
        p.end()


# ─────────────────────────────────────────────
#  (ApiInitThread, DataFetchThread 삭제됨 — REST API 제거)
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
#  AI 스캐너 스레드 — 창고(캐시)만 읽고 조건 평가 (REST API 없음)
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

            try:
                predictor = get_predictor()
            except Exception:
                pass
            try:
                apply_strategy()
            except Exception:
                pass

            scanner = Scanner()

            # 창고에서 종목 로드 → Scanner에 전달
            from xing_api import XingAPI
            _mode = "mock"
            if getattr(sys, 'frozen', False):
                _exe = os.path.basename(sys.executable).lower()
                _mode = "mock" if "mock" in _exe else "real"
            warehouse = XingAPI.load_warehouse(mode=_mode)
            if warehouse:
                scanner.set_filtered_stocks(warehouse)
                self.status_signal.emit(f"[스캐너] 창고 {len(warehouse)}종목 로드")
            else:
                self.status_signal.emit("[스캐너] 창고 비어있음")

            # 데이터 수집 (시작 시 전체 수집 → 캐시 적재)
            from ai_engine.data.ls_data_fetcher import LSDataFetcher
            from ai_engine.data.collector import collect_stock_data, collect_market_data, collect_holdings_data
            fetcher = LSDataFetcher(mode=_mode)
            _fetcher_ok = False
            if fetcher.connect():
                _fetcher_ok = True
                self.status_signal.emit("[수집기] API 연결 완료, 데이터 수집 시작...")
                if warehouse:
                    collect_stock_data(fetcher, warehouse, status_callback=lambda msg: self.status_signal.emit(msg))
                # 보유종목 데이터도 수집 (스캔필드에 없는 보유종목 커버)
                from ai_engine.core.scanner import _load_holdings_cache
                held = _load_holdings_cache()
                if held:
                    collect_holdings_data(fetcher, held)
                    self.status_signal.emit(f"[수집기] 보유종목 {len(held)}개 데이터 수집 완료")
                collect_market_data(fetcher)
                self.status_signal.emit("[수집기] 데이터 수집 완료")
            else:
                self.status_signal.emit("[수집기] ⚠ API 연결 실패 - 캐시 데이터로 스캔")

            # 이미 수집된 종목코드 기록 (새 종목 감지용)
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
                    if cmd:
                        print(f"[스캐너스레드] 명령 수신: {cmd}")
                    if cmd.get("command") == "stop":
                        break
                    if cmd.get("command") in ("rescan", "run_filter"):
                        print("[스캐너스레드] rescan 명령 → 재스캔 시작")
                        self.status_signal.emit("🔄 조건 변경 → 재스캔 중...")
                        try:
                            signals, count = scanner.run_scan()
                            write_signals(signals, scan_count=count)
                            self.status_signal.emit(f"✅ 재스캔 완료: {count}종목")
                        except Exception as e:
                            self.status_signal.emit(f"⚠ 재스캔 오류: {e}")

                    try:
                        _mt = os.path.getmtime(_cfg_path) if os.path.exists(_cfg_path) else 0
                        if _mt != _cfg_mtime:
                            _cfg_mtime = _mt
                            with open(_cfg_path, "r", encoding="utf-8") as _f:
                                _cfg = _json.load(_f)
                            scan_interval = max(1, int(_cfg.get("scan_interval_seconds", 2)))
                    except Exception:
                        pass

                    if now_hm >= "15:40" and last_learn != today:
                        try:
                            optimize_weights()
                            reload_model()
                            predictor = get_predictor()
                        except Exception:
                            pass
                        last_learn = today

                    # 창고 변경 감지 → 새 종목만 추가 수집
                    try:
                        new_warehouse = XingAPI.load_warehouse(mode=_mode)
                        if new_warehouse:
                            new_codes = {s["code"] for s in new_warehouse}
                            if new_codes != _known_codes:
                                scanner.set_filtered_stocks(new_warehouse)
                                added = new_codes - _known_codes
                                if added and _fetcher_ok:
                                    new_stocks = [s for s in new_warehouse if s["code"] in added]
                                    print(f"[수집기] 새 종목 {len(new_stocks)}개 감지 → 수집 시작")
                                    collect_stock_data(fetcher, new_stocks, status_callback=lambda msg: self.status_signal.emit(msg))
                                _known_codes = new_codes
                        else:
                            # 창고 비어있으면 스캔필드도 비움
                            if _known_codes:
                                scanner.set_filtered_stocks([])
                                write_signals([], scan_count=0)
                                _known_codes = set()
                    except Exception:
                        pass

                    try:
                        signals, count = scanner.run_scan()
                        # 디버그 로그
                        try:
                            _slog = os.path.join(_root, "debug_scanner.txt")
                            scored = [s for s in signals if s.get("score", 0) > 0]
                            with open(_slog, "a", encoding="utf-8") as _sf:
                                _sf.write(f"[{datetime.now().strftime('%H:%M:%S')}] scan: {count}종목, scored={len(scored)}, signals={len(signals)}\n")
                        except: pass
                        write_signals(signals, scan_count=count)
                        buy_sigs = sorted(
                            [s for s in signals if s.get("signal_type") == "BUY"],
                            key=lambda x: x.get("score", 0), reverse=True
                        )
                        top10 = buy_sigs[:10]
                        if top10:
                            names = ", ".join(f'{s["stock_name"]}({s["score"]:.0f})' for s in top10)
                            self.status_signal.emit(f"[추천] {names}")
                    except Exception as e:
                        self.status_signal.emit(f"[스캐너] 오류: {e}")
                        try:
                            import traceback as _tb2
                            _slog = os.path.join(_root, "debug_scanner.txt")
                            with open(_slog, "a", encoding="utf-8") as _sf:
                                _sf.write(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {e}\n{_tb2.format_exc()}\n")
                        except: pass

                except Exception as e:
                    self.status_signal.emit(f"[스캐너] ⚠ 루프 오류: {e}")

                time.sleep(scan_interval)

        except Exception as e:
            import traceback
            self.status_signal.emit(f"[스캐너] ❌ 초기화 오류: {e}")
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
#  메인 윈도우
# ─────────────────────────────────────────────
def _detect_trade_mode() -> str:
    """exe 이름으로 실전/모의 모드 자동 감지"""
    exe_name = os.path.basename(sys.executable if getattr(sys, 'frozen', False) else "")
    if "Mock" in exe_name or "mock" in exe_name:
        return "mock"
    if "Real" in exe_name or "real" in exe_name:
        return "real"
    # 개발 환경: config 우선
    return None


# ── 모드별 engine_config 파일 경로 ──
_current_trade_mode = None  # MainWindow.__init__에서 설정됨

def get_engine_config_filename() -> str:
    """현재 모드에 맞는 engine_config 파일명 반환"""
    if _current_trade_mode == "mock":
        return "engine_config_mock.json"
    elif _current_trade_mode == "real":
        return "engine_config_real.json"
    return "engine_config.json"  # fallback


# ── 업종지수 바차트 위젯 ──
class SectorBarChart(QWidget):
    """업종별 등락률을 세로 바차트로 시각화"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sectors = []  # [{"name": str, "rate": float}, ...]
        self.setFixedHeight(170)

    def set_data(self, sectors: list):
        """sectors: [{"name": "섬유의복", "change": "+2.50%", ...}, ...]"""
        parsed = []
        for s in sectors:
            try:
                rate = float(s.get("change", "0").replace("%", "").replace("+", ""))
            except (ValueError, TypeError):
                rate = 0.0
            name = s.get("name", "")
            # 등락률 부호 복원
            chg_str = s.get("change", "0%")
            if chg_str.startswith("-"):
                rate = -abs(rate)
            parsed.append({"name": name, "rate": rate})
        # 내림차순 정렬
        parsed.sort(key=lambda x: x["rate"], reverse=True)
        self._sectors = parsed
        self.update()

    def paintEvent(self, event):
        if not self._sectors:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        n = len(self._sectors)

        # 여백
        margin_left = 4
        margin_right = 28   # Y축 눈금용
        margin_top = 6
        margin_bottom = 75   # 업종명 텍스트용 (수직 배열)

        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom
        if chart_w <= 0 or chart_h <= 0 or n == 0:
            p.end()
            return

        # Y축 범위 — 실제 데이터 기반으로 동적 계산
        import math
        rates = [s["rate"] for s in self._sectors]
        actual_min = min(rates) if rates else 0.0
        actual_max = max(rates) if rates else 1.0

        padding = (actual_max - actual_min) * 0.1 if actual_max != actual_min else 0.5
        d_min = actual_min - padding
        d_max = actual_max + padding
        # 양수 데이터면 0선 포함
        if actual_min >= 0:
            d_min = 0.0
        # 음수 데이터면 0선 포함
        if actual_max <= 0:
            d_max = 0.0

        d_range = d_max - d_min if d_max != d_min else 1.0

        def rate_to_y(r):
            return margin_top + chart_h * (d_max - r) / d_range

        zero_y = rate_to_y(0)

        # 바 너비
        bar_total_w = chart_w / n
        bar_w = max(3, int(bar_total_w * 0.75))
        gap = (bar_total_w - bar_w) / 2

        # 배경 그리드선 + Y축 눈금
        p.setPen(QPen(QColor("#5a5a8a"), 1, Qt.DashLine))
        font_small = QFont("맑은 고딕", 8)
        p.setFont(font_small)
        tick_count = 4
        for ti in range(tick_count + 1):
            tick_val = d_min + (d_max - d_min) * ti / tick_count
            py_pos = rate_to_y(tick_val)
            p.drawLine(int(margin_left), int(py_pos), int(margin_left + chart_w), int(py_pos))
            p.setPen(QPen(QColor("#e8e8ff")))
            p.drawText(int(margin_left + chart_w + 4), int(py_pos + 4), f"{tick_val:.1f}")
            p.setPen(QPen(QColor("#5a5a8a"), 1, Qt.DashLine))

        # 바 그리기
        for i, s in enumerate(self._sectors):
            rate = s["rate"]
            x = margin_left + i * bar_total_w + gap

            top_y   = rate_to_y(max(rate, 0))
            bot_y   = rate_to_y(min(rate, 0))
            bar_h   = max(1, int(bot_y - top_y))
            bar_y   = int(top_y)
            color   = QColor("#e74c3c") if rate >= 0 else QColor("#3498db")

            p.fillRect(int(x), bar_y, int(bar_w), bar_h, color)

            # 업종명 (수직 배열: 아래→위로 읽기)
            p.save()
            name_font = QFont("맑은 고딕", 7)
            p.setFont(name_font)
            p.setPen(QPen(QColor("#e8e8ff")))
            label = f"{s['name']}({rate:+.2f})"
            text_x = int(x + bar_w / 2 + 5)
            text_y = int(h - 2)
            p.translate(text_x, text_y)
            p.rotate(-90)               # 반시계 90° → 글자가 아래→위 방향
            p.drawText(0, 0, label)
            p.restore()

        p.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(1100, 700)
        self.resize(1360, 880)

        # API 초기화 (exe 이름으로 모드 우선 감지)
        config = load_config()
        detected = _detect_trade_mode()
        self.trade_mode = detected if detected else config["api"].get("trade_mode", "real")
        global _current_trade_mode
        _current_trade_mode = self.trade_mode
        self.setStyleSheet(build_style(self.trade_mode))
        self._theme = _THEME.get(self.trade_mode, _THEME["mock"])

        # exe 감지 모드이면 config에도 저장 (일치 유지)
        if detected and config["api"].get("trade_mode") != detected:
            config["api"]["trade_mode"] = detected
            save_config(config)

        mode_label = "모의투자" if self.trade_mode == "mock" else "실전투자"
        self.setWindowTitle(f"StockTrader [{mode_label}]")

        # 아이콘 설정
        icon_name = "icon_mock.ico" if self.trade_mode == "mock" else "icon_real.ico"
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), icon_name)
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), icon_name)
        if os.path.exists(icon_path):
            from PyQt5.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))

        self.is_trading = False
        self.holdings_data  = []
        self.ai_signals     = []
        self.xing_api = None      # xingAPI COM 객체 (조건검색 전용)
        self.acf_path = ""        # ACF 파일 경로
        self.api = None           # LS Open API (잔고/지수/주문)

        # ── 성능 최적화: 캐시 & 디바운스 ──
        self._config_cache = None
        self._config_cache_mtime = 0
        self._last_holdings_hash = None
        self._last_sig_hash = None
        self._qcolors = {}  # QColor 객체 캐시

        # 과거 데이터 수집 상태 (설정창 닫아도 유지)
        self._hist_collect_thread = None
        self._hist_collect_msg = ""
        self._hist_collecting = False

        # 초기 스캔필드는 창고 캐시 로드 시 채워짐 (비우지 않음)
        self._profit_sold_stages = self._load_profit_stages()  # 종목별 익절 완료 단계
        self._pending_buy_orders = {}   # {order_no: {"code", "name", "time", "qty"}}
        self._pending_sell_orders = {}  # {order_no: {"code", "name", "time", "qty", "retry"}}
        self._loss_cut_stages = {}      # {code: 완료 단계 (-3%=0, -5%=1, -7%=2)}
        self.ai_thread = None

        self._build_ui()

        self.ai_timer = QTimer()
        self.ai_timer.timeout.connect(self._update_ai_signals)
        self.ai_timer.start(3000)  # 3초마다 ai_signals.json 변경 체크

        # xingAPI 조건검색 주기적 재실행 타이머 (30초 — COM은 메인스레드 필수)
        self._warehouse_timer = QTimer()
        self._warehouse_timer.timeout.connect(self._refresh_warehouse)
        self._warehouse_timer.start(30000)
        self._last_warehouse_hash = None

        # Open API 데이터 갱신 타이머 (지수, 보유종목)
        self._init_open_api()
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self._refresh_data)
        self.data_timer.start(3000)  # 3초 타이머 (간격은 틱 카운터로 조절)

    # ── 성능 최적화 헬퍼 ──
    def _get_config(self):
        """캐시된 config 반환, 파일 변경 시에만 다시 읽기 (deep copy 없음)"""
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
        """QColor 객체 캐시 — 동일 색상 재생성 방지"""
        c = self._qcolors.get(hex_str)
        if c is None:
            c = QColor(hex_str)
            self._qcolors[hex_str] = c
        return c

    def _init_open_api(self):
        """LS Open API 초기화 (토큰 발급)"""
        try:
            from ls_api import LSApi
            self.api = LSApi(mode=self.trade_mode)
            if self.api.get_token():
                print(f"[Open API] 토큰 발급 성공 ({self.trade_mode})")
            else:
                print(f"[Open API] 토큰 발급 실패: {self.api.last_error}")
        except Exception as e:
            print(f"[Open API] 초기화 실패: {e}")
            self.api = None

    _sector_theme_tick = 359  # 업종/테마 갱신 카운터 (첫 틱에서 바로 조회)
    _index_tick = 599         # 지수 갱신 카운터 (첫 틱에서 바로 조회, 600틱=30분)
    _holdings_refresh = True  # 잔고 갱신 플래그 (시작 시 1회 + 매매 후)

    def _request_holdings_refresh(self):
        """매수/매도 후 잔고 갱신 요청"""
        self._holdings_refresh = True

    def _refresh_data(self):
        """Open API로 지수/업종/테마 갱신 (5초마다), 잔고는 매매 시에만"""
        if not self.api:
            return
        if not self.api.ensure_token():
            return
        try:
            # 지수 (KOSPI/KOSDAQ) - 30분마다 = 600틱 (3초×600=1800초)
            self._index_tick += 1
            if self._index_tick >= 600:
                self._index_tick = 0
                kospi = self.api.get_market_index("001")
                kosdaq = self.api.get_market_index("301")
                self._apply_market_index("KOSPI", kospi)
                self._apply_market_index("KOSDAQ", kosdaq)

            # 보유종목 - 매 틱(3초)마다 갱신
            self._holdings_tick = getattr(self, '_holdings_tick', 0) + 1
            if self._holdings_refresh or self._holdings_tick >= 1:  # 매 틱 = 3초
                self._holdings_refresh = False
                self._holdings_tick = 0
                ui_holdings, account_summary = self.api.get_holdings_for_ui()
                if ui_holdings is not None:
                    # 빈 응답이면 기존 데이터 유지 (API 일시 오류 방지)
                    if ui_holdings or not self.holdings_data:
                        # 디바운스: 데이터 변경 시에만 테이블 갱신 & 캐시 저장
                        h_key = tuple((h.get("raw_code"), h.get("raw_cur_price"), h.get("raw_pnl_rate"), h.get("raw_qty")) for h in ui_holdings)
                        data_changed = h_key != self._last_holdings_hash
                        self.holdings_data = ui_holdings
                        if data_changed:
                            self._last_holdings_hash = h_key
                            self._update_holdings_table(ui_holdings)
                            self._write_holdings_cache(ui_holdings)
                    if account_summary:
                        self._update_summary(account_summary)

            # 업종지수 + 상승테마 (5분마다 = 100틱, 3초×100=300초)
            self._sector_theme_tick += 1
            if self._sector_theme_tick >= 100:
                self._sector_theme_tick = 0
                try:
                    sectors = self.api.get_sector_indices()
                    if sectors:
                        self._apply_sector_table(sectors)
                    themes = self.api.get_themes()
                    if themes:
                        self._update_theme_section(themes)
                        self._save_theme_cache(themes)
                except Exception as e:
                    print(f"[업종/테마] 조회 실패: {e}")

            now = datetime.now().strftime("%H:%M:%S")
            self.time_label.setText(f"⏱ {now} 업데이트")
        except Exception as e:
            pass  # 갱신 실패 시 무시

    def _fetch_sector_theme_bg(self):
        """업종지수 + 상승테마를 백그라운드 스레드에서 조회"""
        if getattr(self, '_st_fetching', False):
            return  # 이미 조회 중
        self._st_fetching = True
        def _worker():
            try:
                sectors = self.api.get_sector_indices()
                themes = self.api.get_themes()
                self._st_result = (sectors, themes)
            except Exception as e:
                print(f"[업종/테마] 조회 실패: {e}")
                self._st_result = None
            finally:
                self._st_fetching = False
        threading.Thread(target=_worker, daemon=True).start()

    def _apply_sector_theme_result(self):
        """백그라운드 결과를 메인 스레드에서 UI 반영"""
        result = getattr(self, '_st_result', None)
        if not result:
            return
        self._st_result = None
        sectors, themes = result
        if sectors:
            self._apply_sector_table(sectors)
        if themes:
            self._update_theme_section(themes)
            self._save_theme_cache(themes)

# ── xingAPI 조건검색 주기적 재실행 (10초마다) ──
    _warehouse_busy = False

    def _refresh_warehouse(self):
        """xingAPI t1857 조건검색 재실행 → 창고 갱신 (30초마다)"""
        if self._warehouse_busy:
            return  # 재진입 방지
        if not self.xing_api or not self.acf_path:
            return
        self._warehouse_busy = True
        # 장 시간만 (09:00~15:30 평일)
        now = datetime.now()
        now_hm = now.strftime("%H:%M")
        if now.weekday() >= 5 or not ("09:00" <= now_hm <= "15:30"):
            return
        try:
            stocks = self.xing_api.run_full_scan(self.acf_path)
            # t1857 결과의 실시간 가격을 캐시에 반영
            if stocks:
                try:
                    from ai_engine.data.cache import get_cache
                    _cache = get_cache()
                    for s in stocks:
                        _code = s["code"]
                        if _code.startswith("A") and len(_code) == 7:
                            _code = _code[1:]
                        _cached = _cache.get(f"data_{_code}")
                        if _cached and "price" in _cached:
                            _cached["price"]["price"] = s.get("price", _cached["price"].get("price", 0))
                            _cached["price"]["change"] = s.get("change", _cached["price"].get("change", 0))
                            _cached["price"]["diff"] = s.get("diff", _cached["price"].get("diff", 0))
                            _cached["price"]["volume"] = s.get("volume", _cached["price"].get("volume", 0))
                            _cache.set(f"data_{_code}", _cached, ttl_seconds=86400)
                    _cache.save()
                except Exception as _e:
                    print(f"[창고갱신] 가격 캐시 갱신 오류: {_e}")
            # 스캔필드 갱신: AI ON이면 스캐너에게 맡김, OFF면 WATCH로 표시
            ai_running = self.ai_thread and self.ai_thread.isRunning()
            if not ai_running:
                from ai_engine.comm.signal_writer import write_signals
                if stocks:
                    _signals = [
                        {"stock_code": s["code"], "stock_name": s.get("name", ""),
                         "signal_type": "WATCH", "score": 0,
                         "current_price": s.get("price", 0),
                         "diff_rate": s.get("diff", 0.0),
                         "conditions": {}, "confidence": "LOW"}
                        for s in stocks
                    ]
                    write_signals(_signals, scan_count=len(stocks))
                else:
                    write_signals([], scan_count=0)
                # 즉시 UI 반영
                self._update_ai_signals()
            print(f"[창고갱신] t1857: {len(stocks) if stocks else 0}종목 (AI={'ON' if ai_running else 'OFF'})")
        except Exception as e:
            print(f"[창고갱신] 오류: {e}")
        finally:
            self._warehouse_busy = False

# ── AI 신호 파일 읽기 (10초마다, 변경 시에만) ──
    _ai_signals_mtime = 0

    def _update_ai_signals(self):
        """ai_signals.json 읽어서 스캔종목/추천종목 테이블 갱신 (변경 감지)"""
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
                return  # 변경 없음 → 스킵
            self._ai_signals_mtime = mtime
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        signals    = data.get("signals", [])
        scan_count = data.get("scan_count", 0)
        timestamp  = data.get("timestamp", "")[:16].replace("T", " ")
        # 스캔 날짜 저장 (오늘 스캔 여부 판단용)
        self._ai_signal_date = data.get("timestamp", "")[:10]

        buy_signals  = [s for s in signals if s.get("signal_type") == "BUY"]
        # AI 스캔종목: AI가 점수를 매긴 종목이 있으면 필터, 없으면 전체 표시
        has_ai_scores = any(s.get("score", 0) > 0 for s in signals)
        if has_ai_scores:
            # AI 필터 활성: 점수 있는 종목만
            scan_signals = [s for s in signals if s.get("signal_type") in ("BUY", "HOLD", "WATCH")
                            and s.get("score", 0) > 0
                            and "sell_reason" not in s]
        else:
            # AI 미동작: 전체 표시
            scan_signals = [s for s in signals if s.get("signal_type") in ("BUY", "HOLD", "WATCH")
                            and "sell_reason" not in s]
        all_scanned  = sorted(scan_signals, key=lambda x: x.get("score", 0), reverse=True)

        # 상태 레이블 갱신
        if hasattr(self, "ai_status_label"):
            self.ai_status_label.setText(
                f"🤖 AI엔진: {timestamp} | {scan_count}종목 스캔 | 매수신호 {len(buy_signals)}개"
            )
            self.ai_status_label.setStyleSheet(
                "color: #00b894; font-size: 11px; padding: 2px 4px;"
                if buy_signals else "color: #444444; font-size: 11px; padding: 2px 4px;"
            )

        _qc = self._qcolor  # 로컬 바인딩으로 빠른 접근
        def _item(text, color=None, align=Qt.AlignCenter):
            it = QTableWidgetItem(str(text))
            it.setTextAlignment(align)
            if color:
                it.setForeground(_qc(color))
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            return it

        # ── 왼쪽: AI 스캔종목 (전체, 점수순) ── 기존 셀 재사용으로 성능 최적화
        if hasattr(self, "scan_list"):
            self.scan_list.setUpdatesEnabled(False)
            new_count = len(all_scanned)
            old_count = self.scan_list.rowCount()
            if new_count != old_count:
                self.scan_list.setRowCount(new_count)
            self._scan_codes = {}
            for row_idx, sig in enumerate(all_scanned):
                sig_type  = sig.get("signal_type", "")
                score     = sig.get("score", 0)
                cur_price = sig.get("current_price", 0)
                state_color = {"BUY": "#00b894", "HOLD": "#fdcb6e"}.get(sig_type, "#888")
                score_color = "#00b894" if sig_type == "BUY" else "#fdcb6e" if sig_type == "HOLD" else "#aaa"
                diff_rate  = sig.get("diff_rate", 0.0)
                diff_color = "#ff6b6b" if diff_rate >= 0 else "#74b9ff"
                diff_str   = f"{diff_rate:+.2f}%" if diff_rate != 0 else "-"

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
                        if color:
                            item.setForeground(_qc(color))
                        item.setTextAlignment(align)
                self._scan_codes[row_idx] = sig.get("stock_code", "")
            self.scan_list.setUpdatesEnabled(True)

        # ── 오른쪽: AI 추천종목 (BUY 중 상위 10개, 복합 랭킹) ── 기존 셀 재사용
        if hasattr(self, "rec_list"):
            self.rec_list.setUpdatesEnabled(False)

            def _rank_score(s):
                return (s.get("score", 0) * 0.50
                        + s.get("supply_score", 0) * 0.25
                        + s.get("chart_score", 0) * 0.15
                        + s.get("material_score", 0) * 0.10)

            ranked = sorted(buy_signals, key=_rank_score, reverse=True)[:10]
            new_count = len(ranked)
            old_count = self.rec_list.rowCount()
            if new_count != old_count:
                self.rec_list.setRowCount(new_count)

            for rank, sig in enumerate(ranked, 1):
                row = rank - 1
                score      = sig.get("score", 0)
                confidence = sig.get("confidence", "")
                cur_price  = sig.get("current_price", 0)
                conf_color = {"HIGH": "#00b894", "MEDIUM": "#fdcb6e", "LOW": "#888"}.get(confidence, "#888")
                diff_rate  = sig.get("diff_rate", 0.0)
                diff_color = "#ff6b6b" if diff_rate >= 0 else "#74b9ff"
                diff_str   = f"{diff_rate:+.2f}%" if diff_rate != 0 else "-"

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
                        if color:
                            item.setForeground(_qc(color))
                        item.setTextAlignment(align)
            self.rec_list.setUpdatesEnabled(True)

        self.ai_signals = signals

        # 보유종목 AI판단 컬럼 즉시 갱신 (신호 업데이트 시 항상 반영)
        self._refresh_holdings_ai_column()

    def _refresh_holdings_ai_column(self):
        """보유종목 테이블의 AI판단 컬럼만 갱신 (신호 변경 시 호출)"""
        if not hasattr(self, 'holdings_table'):
            return
        # 종목코드 → 신호 매핑 (A접두사 포함/미포함 모두 매칭)
        sig_map = {}
        for s in self.ai_signals:
            if s.get("signal_type") in ("SELL", "HOLD"):
                sc = s.get("stock_code", "")
                sig_map[sc] = s
                # A접두사 변환 매핑도 추가
                if sc.startswith("A") and len(sc) == 7:
                    sig_map[sc[1:]] = s
                else:
                    sig_map["A" + sc] = s

        for row in range(self.holdings_table.rowCount()):
            if row >= len(self.holdings_data):
                break
            code = self.holdings_data[row].get("raw_code", "")
            sig  = sig_map.get(code)
            if sig:
                if sig["signal_type"] == "SELL":
                    score = sig.get("score", 0)
                    ai_text  = f"매도 {score:.0f}점"
                    ai_color = "#ff6b6b"
                else:
                    sell_score = sig.get("score", 50)
                    hold_score = 100.0 - sell_score
                    ai_text  = f"보유 {hold_score:.0f}점"
                    ai_color = "#fdcb6e"
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

    def _apply_market_index(self, name: str, data):
        """KOSPI/KOSDAQ 지수 UI 적용 (메인 스레드)"""
        if not data or name not in self.market_labels:
            return
        try:
            row = data[0] if isinstance(data, list) else data
            price = float(str(row.get("pricejisu", 0)).replace(",", ""))
            try:
                rt = float(str(row.get("diffjisu", 0)).replace(",", ""))
            except:
                rt = 0.0
            sign_cd = str(row.get("sign", "3"))
            # sign: 2=상승, 5=하락, 3=보합
            if sign_cd == "5":
                rt = -abs(rt)
            elif sign_cd == "2":
                rt = abs(rt)
            val_lbl, chg_lbl = self.market_labels[name]
            val_lbl.setText(f"{price:,.2f}")
            sign_str = "+" if rt >= 0 else ""
            color = "#ff6b6b" if rt >= 0 else "#74b9ff"
            chg_lbl.setText(f"{sign_str}{rt:.2f}%")
            chg_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        except Exception as e:
            print(f"[시장지수] {name} 파싱 실패: {e}")

    def _apply_sector_table(self, sectors: list):
        """업종지수 바차트 적용 (메인 스레드)"""
        if not hasattr(self, 'sector_chart') or not sectors:
            return

        # placeholder 제거
        if hasattr(self, '_sector_placeholder') and self._sector_placeholder:
            self._sector_placeholder.hide()
            self._sector_placeholder.deleteLater()
            self._sector_placeholder = None

        self.sector_chart.show()
        self.sector_chart.set_data(sectors)
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # ── 타이틀바 (계좌요약 포함) ──
        main_layout.addWidget(self._build_titlebar())

        # ── 시장현황 바 ──
        main_layout.addWidget(self._build_market_bar())

        # ── 메인 3컬럼 레이아웃 ──
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; width: 4px; }")
        self.main_splitter.addWidget(self._build_left_column())    # 보유종목 + 업종지수
        self.main_splitter.addWidget(self._build_center_column())  # AI추천 + AI스캔
        self.main_splitter.addWidget(self._build_right_column())   # 테마 + 관련종목 + 로그
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 1)
        main_layout.addWidget(self.main_splitter)
        self._load_splitter_sizes()

    # ── 타이틀바 (계좌요약 포함) ──
    def _build_titlebar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #1e3a5f; border-radius: 6px;")
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # 타이틀
        title = QLabel("📈 자동매매")
        title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        # 구분선
        sep0 = QFrame(); sep0.setFrameShape(QFrame.VLine)
        sep0.setStyleSheet("color: #1e4a7a;")
        layout.addWidget(sep0)

        # 계좌 요약 카드 — HTS와 동일 필드 (실시간 업데이트용 참조 저장)
        self.summary_labels = {}
        summaries = [
            ("추정자산", "연결중...", self._theme['text'], self._theme['accent']),
            ("실현손익", "-",         self._theme['text'], self._theme['accent']),
            ("매입금액", "-",         self._theme['text'], self._theme['accent']),
            ("평가금액", "-",         self._theme['text'], self._theme['accent']),
            ("평가손익", "-",         self._theme['text'], self._theme['accent']),
            ("손익률",   "-",         self._theme['text'], self._theme['accent']),
            ("보유종목", "-",         self._theme['text'], self._theme['accent']),
        ]
        for label, value, color, bg in summaries:
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background-color: {bg}; border: 1px solid {self._theme['border']}; "
                f"border-radius: 6px; padding: 1px 4px; }}"
            )
            col = QVBoxLayout(card)
            col.setContentsMargins(4, 2, 4, 2)
            col.setSpacing(0)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #c0c0e0; font-size: 9px; border: none;")
            lbl.setAlignment(Qt.AlignCenter)
            val = QLabel(value)
            val.setStyleSheet(
                f"color: {color}; font-size: 11px; font-weight: bold; border: none;"
            )
            val.setAlignment(Qt.AlignCenter)
            self.summary_labels[label] = val
            col.addWidget(lbl)
            col.addWidget(val)
            layout.addWidget(card)

        layout.addStretch()

        # 공통 박스 높이
        BOX_H = 28
        _box = (
            "QPushButton {{ background-color: {bg}; color: {fg}; "
            "border: 1px solid {bd}; border-radius: 4px; "
            "padding: 0px 12px; font-size: 12px; font-weight: bold; }}"
            "QPushButton:hover {{ background-color: {hv}; }}"
        )

        # API 배지
        self.ls_badge = QLabel("XING")
        self.ls_badge.setFixedHeight(BOX_H)
        self.ls_badge.setStyleSheet(
            "background-color: #00b89422; color: #00b894; "
            "border: 1px solid #00b894; border-radius: 4px; "
            "padding: 0px 10px; font-size: 12px; font-weight: bold;"
        )
        self.ls_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.ls_badge)

        # 설정 버튼
        self.btn_settings = QPushButton("설정")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setFixedHeight(BOX_H)
        self.btn_settings.setStyleSheet(
            _box.format(bg="#4a4a80", fg="#ffffff", bd="#5a5a9a", hv="#5a5a9a")
        )
        self.btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(self.btn_settings)

        # 모드 버튼
        detected_mode = _detect_trade_mode()
        self.btn_mock = QPushButton("모의투자")
        self.btn_mock.setCheckable(True)
        self.btn_mock.setChecked(self.trade_mode == "mock")
        self.btn_mock.setFixedHeight(BOX_H)
        self.btn_mock.setStyleSheet(
            _box.format(bg="#0984e3", fg="#ffffff", bd="#0984e3", hv="#1e90ff")
            if self.trade_mode == "mock" else
            _box.format(bg="#3d3d60", fg="#e8e8ff", bd="#5a5a8a", hv="#4a4a80")
        )
        self.btn_mock.clicked.connect(lambda: self.switch_trade_mode("mock"))

        self.btn_real = QPushButton("실투자")
        self.btn_real.setCheckable(True)
        self.btn_real.setChecked(self.trade_mode == "real")
        self.btn_real.setFixedHeight(BOX_H)
        self.btn_real.setStyleSheet(
            _box.format(bg="#d63031", fg="#ffffff", bd="#d63031", hv="#e17055")
            if self.trade_mode == "real" else
            _box.format(bg="#3d3d60", fg="#e8e8ff", bd="#5a5a8a", hv="#4a4a80")
        )
        self.btn_real.clicked.connect(lambda: self.switch_trade_mode("real"))

        if detected_mode == "mock":
            layout.addWidget(self.btn_mock)
        elif detected_mode == "real":
            layout.addWidget(self.btn_real)
        else:
            layout.addWidget(self.btn_mock)
            layout.addWidget(self.btn_real)

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

    # ── 시장현황 바 ──
    def _build_market_bar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #2a2a3e; border-radius: 6px; border: 1px solid #5a5a8a;")
        bar.setFixedHeight(36)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(0)

        self.market_labels = {}

        market_data = [
            ("KOSPI",    "-",  "-",  "#888"),
            ("KOSDAQ",   "-",  "-",  "#888"),
        ]

        for i, (label, value, change, color) in enumerate(market_data):
            item_layout = QHBoxLayout()
            item_layout.setSpacing(4)

            lbl = QLabel(label)
            lbl.setStyleSheet("color: #a0a0c0; font-size: 11px;")

            val = QLabel(value)
            val.setStyleSheet("color: #e8e8ff; font-size: 12px; font-weight: bold;")

            chg = QLabel(change)
            chg.setStyleSheet(f"color: {color}; font-size: 11px;")

            self.market_labels[label] = (val, chg)

            item_layout.addWidget(lbl)
            item_layout.addWidget(val)
            item_layout.addWidget(chg)
            layout.addLayout(item_layout)

            sep = QFrame()
            sep.setFrameShape(QFrame.VLine)
            sep.setStyleSheet("color: #5a5a8a; margin: 4px 12px;")
            layout.addWidget(sep)

        layout.addStretch()

        # 매매 로그 — 한줄 인라인 (최신 메시지만 덮어쓰기)
        log_icon = QLabel("📋")
        log_icon.setStyleSheet("font-size: 12px;")
        log_title = QLabel("매매 로그")
        log_title.setStyleSheet("color: #a0a0c0; font-size: 11px; font-weight: bold;")
        self.log_label = QLabel("")
        self.log_label.setStyleSheet(
            "color: #00ff88; font-family: Consolas; font-size: 11px;"
        )
        self.log_label.setWordWrap(False)
        layout.addWidget(log_icon)
        layout.addWidget(log_title)
        layout.addWidget(self.log_label, stretch=1)

        sep_log = QFrame()
        sep_log.setFrameShape(QFrame.VLine)
        sep_log.setStyleSheet("color: #5a5a8a; margin: 4px 8px;")
        layout.addWidget(sep_log)

        # 업데이트 시간
        self.time_label = QLabel("⏱ 연결중...")
        self.time_label.setStyleSheet("color: #a0a0c0; font-size: 10px;")
        layout.addWidget(self.time_label)

        return bar

    # ── 계좌 요약 바 ──
    def _build_summary_bar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #ffffff; border-radius: 6px;")
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(20)

        summaries = [
            ("추정자산", "52,384,500", "#ffffff"),
            ("실현손익", "+12,500", "#00b894"),
            ("매입금액", "5,000,000", "#7dd3fc"),
            ("평가금액", "5,384,500", "#7dd3fc"),
            ("평가손익", "+384,500", "#00b894"),
            ("손익률", "+0.74%", "#00b894"),
        ]
        for label, value, color in summaries:
            box = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #444444; font-size: 11px;")
            val = QLabel(value)
            val.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
            box.addWidget(lbl)
            box.addWidget(val)
            layout.addLayout(box)
            # 구분선
            if label != "자동매매":
                sep = QFrame()
                sep.setFrameShape(QFrame.VLine)
                sep.setStyleSheet("color: #000000;")
                layout.addWidget(sep)

        layout.addStretch()
        return bar

    # ── 좌측 컬럼: 보유종목 + 업종지수 ──
    def _build_left_column(self):
        widget = QWidget()
        self.left_v_splitter = QSplitter(Qt.Vertical)
        self.left_v_splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; height: 4px; }")
        self.left_v_splitter.addWidget(self._build_holdings_table())
        self.left_v_splitter.addWidget(self._build_market_panel())
        self.left_v_splitter.setSizes([520, 220])
        v_splitter = self.left_v_splitter
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(v_splitter)
        return widget

    # ── 중앙 컬럼: AI 추천종목 + AI 스캔종목 ──
    def _build_center_column(self):
        widget = QWidget()
        self.center_v_splitter = QSplitter(Qt.Vertical)
        self.center_v_splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; height: 4px; }")
        self.center_v_splitter.addWidget(self._build_rec_panel())
        self.center_v_splitter.addWidget(self._build_scan_panel())
        self.center_v_splitter.setSizes([350, 350])
        v_splitter = self.center_v_splitter
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(v_splitter)
        return widget

    # ── 업종지수 패널 (바차트) ──
    def _build_market_panel(self):
        grp_sector = QGroupBox("업종지수")
        grp_sector.setStyleSheet("""
            QGroupBox {
                color: #000000; font-size: 13px; font-weight: bold;
                border: 1px solid #5a9fd4; border-radius: 4px;
                margin-top: 8px; padding-top: 14px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        """)

        self.sector_chart = SectorBarChart()
        self._sector_placeholder = QLabel("")
        self._sector_placeholder.setStyleSheet("color: #444444; font-size: 11px; padding: 10px;")
        self._sector_placeholder.setAlignment(Qt.AlignCenter)

        outer = QVBoxLayout(grp_sector)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.addWidget(self._sector_placeholder)
        outer.addWidget(self.sector_chart)
        self.sector_chart.hide()
        return grp_sector

    # ── 보유종목 테이블 ──
    def _build_holdings_table(self):
        grp = QGroupBox("💼 보유종목")
        layout = QVBoxLayout(grp)

        self.holdings_table = QTableWidget()
        self.holdings_table.setColumnCount(10)
        self.holdings_table.setHorizontalHeaderLabels([
            "", "종목명", "매수가", "현재가", "등락률", "수익률", "수량", "평가금액", "손익금액", "AI"
        ])
        self._ai_exclude_codes = self._load_ai_exclude()
        hdr = self.holdings_table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        # 체크박스 좁게, 나머지 컴팩트
        col_widths = [28, 85, 65, 65, 58, 58, 50, 82, 82, 55]
        for i, w in enumerate(col_widths):
            self.holdings_table.setColumnWidth(i, w)
        hdr.setStretchLastSection(True)
        c = self._theme
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

        # 빈 테이블 (API 연결 후 자동 채워짐)
        self.holdings_table.setRowCount(0)
        # 더블클릭 시 HTS 종목 연동
        self.holdings_table.cellDoubleClicked.connect(self._on_holdings_click)

        layout.addWidget(self.holdings_table)
        return grp

    # ── 추천종목 섹션 ──
    def _build_recommend_section(self):
        grp = QGroupBox("⭐ 추천종목")
        layout = QHBoxLayout(grp)
        grp.setFixedHeight(140)

        recommend_data = [
            ("1순위", "LG에너지솔루션", "81.3%", "#ff6b6b"),
            ("2순위", "삼성전자",       "73.2%", "#fdcb6e"),
            ("3순위", "SK하이닉스",     "68.5%", "#00b894"),
            ("4순위", "카카오",         "65.1%", "#74b9ff"),
        ]
        for rank, name, prob, color in recommend_data:
            card = QFrame()
            card.setStyleSheet(
                f"background-color: #ffffff; border: 1px solid {color}44; "
                f"border-radius: 6px; padding: 4px;"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(4)

            rank_lbl = QLabel(rank)
            rank_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
            prob_lbl = QLabel(f"상승확률 {prob}")
            prob_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")

            bar = QProgressBar()
            bar.setValue(int(float(prob.replace("%", ""))))
            bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
            bar.setTextVisible(False)

            card_layout.addWidget(rank_lbl)
            card_layout.addWidget(name_lbl)
            card_layout.addWidget(prob_lbl)
            card_layout.addWidget(bar)
            layout.addWidget(card)

        return grp

    # ── AI 추천종목 패널 ──
    def _build_rec_panel(self):
        c = self._theme
        table_style = (
            f"QTableWidget {{ font-size: 11px; background-color: {c['panel']}; color: {c['text']}; alternate-background-color: {c['alt_row']}; gridline-color: {c['border']}; }}"
            f"QHeaderView::section {{ font-size: 10px; padding: 2px; background-color: {c['accent']}; color: {c['text']}; border: 1px solid {c['border']}; }}"
        )
        grp = QGroupBox("AI 추천종목")
        grp.setStyleSheet("""
            QGroupBox { color: #000000; font-size: 12px; font-weight: bold;
                border: 1px solid #5a9fd4; border-radius: 4px;
                margin-top: 8px; padding-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        """)
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(2)

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
        self.rec_list.setStyleSheet(table_style)
        self.rec_list.setRowCount(0)
        layout.addWidget(self.rec_list)
        return grp

    # ── AI 스캔종목 패널 ──
    def _build_scan_panel(self):
        c = self._theme
        table_style = (
            f"QTableWidget {{ font-size: 11px; background-color: {c['panel']}; color: {c['text']}; alternate-background-color: {c['alt_row']}; gridline-color: {c['border']}; }}"
            f"QHeaderView::section {{ font-size: 10px; padding: 2px; background-color: {c['accent']}; color: {c['text']}; border: 1px solid {c['border']}; }}"
        )
        grp = QGroupBox("AI 스캔종목")
        grp.setStyleSheet("""
            QGroupBox { color: #000000; font-size: 12px; font-weight: bold;
                border: 1px solid #5a9fd4; border-radius: 4px;
                margin-top: 8px; padding-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        """)
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(2)

        self.scan_list = QTableWidget()
        self.scan_list.setColumnCount(5)
        self.scan_list.setHorizontalHeaderLabels(["종목명", "등락률", "AI점수", "상태", "현재가"])
        self.scan_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            self.scan_list.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.scan_list.verticalHeader().setDefaultSectionSize(20)
        self.scan_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.scan_list.setAlternatingRowColors(True)
        self.scan_list.setStyleSheet(table_style)
        self.scan_list.setRowCount(0)
        self.scan_list.cellDoubleClicked.connect(self._on_scan_click)
        layout.addWidget(self.scan_list)
        return grp

    # ── 우측 컬럼 ──
    def _build_right_column(self):
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        self.right_v_splitter = QSplitter(Qt.Vertical)
        self.right_v_splitter.setStyleSheet("QSplitter::handle { background-color: #cbd5e1; height: 4px; }")
        v_splitter = self.right_v_splitter

        # 상승테마 (스크롤 영역)
        theme_grp = QGroupBox("🔥 상승테마")
        theme_grp_layout = QVBoxLayout(theme_grp)
        theme_grp_layout.setContentsMargins(4, 4, 4, 4)
        theme_grp_layout.setSpacing(0)

        theme_scroll = QScrollArea()
        theme_scroll.setWidgetResizable(True)
        theme_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        theme_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        theme_container = QWidget()
        self.theme_layout = QVBoxLayout(theme_container)
        self.theme_layout.setSpacing(2)
        self.theme_layout.setContentsMargins(0, 0, 0, 0)
        theme_scroll.setWidget(theme_container)

        self._theme_data = []

        self._theme_placeholder = QLabel("")
        self._theme_placeholder.setStyleSheet("color: #444444; font-size: 11px; padding: 10px;")
        self._theme_placeholder.setAlignment(Qt.AlignCenter)
        self.theme_layout.addWidget(self._theme_placeholder)

        theme_grp_layout.addWidget(theme_scroll)
        v_splitter.addWidget(theme_grp)

        # 관련종목 패널 (테마 클릭 시 표시)
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
            f"QTableWidget {{ background-color: {c['panel']}; color: {c['text']}; alternate-background-color: {c['alt_row']}; gridline-color: {c['border']}; }}"
            f"QHeaderView::section {{ background-color: {c['accent']}; color: {c['text']}; border: 1px solid {c['border']}; }}"
        )
        self.related_table.cellDoubleClicked.connect(self._on_related_click)

        hint = QLabel("테마를 클릭하면 관련종목이 표시됩니다")
        hint.setStyleSheet("color: #444444; font-size: 10px;")
        hint.setAlignment(Qt.AlignCenter)
        related_layout.addWidget(hint)
        related_layout.addWidget(self.related_table)
        self.related_table.hide()
        v_splitter.addWidget(self.related_grp)

        v_splitter.setSizes([400, 400])  # 상승테마:관련종목 = 50:50
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 1)
        outer.addWidget(v_splitter)

        return widget

    def _log(self, msg):
        """로그 메시지 — 최신 한줄만 덮어쓰기"""
        if hasattr(self, 'log_label'):
            self.log_label.setText(msg)

    # ── 보유종목 테이블 업데이트 ──
    def _update_holdings_table(self, holdings):
        """API에서 받은 보유종목 데이터로 테이블 갱신 (셀 재사용 최적화)"""
        self.holdings_table.blockSignals(True)
        self.holdings_table.setUpdatesEnabled(False)
        new_count = len(holdings)
        old_count = self.holdings_table.rowCount()
        if new_count != old_count:
            self.holdings_table.setRowCount(new_count)

        # sig_map 한번만 생성
        sig_map = {}
        for s in self.ai_signals:
            if s.get("signal_type") in ("SELL", "HOLD"):
                sc = s.get("stock_code", "")
                sig_map[sc] = s
                if sc.startswith("A") and len(sc) == 7:
                    sig_map[sc[1:]] = s
                else:
                    sig_map["A" + sc] = s

        for row, h in enumerate(holdings):
            code = h.get("raw_code", "")

            # col 0: 감시제외 체크박스
            chk_item = self.holdings_table.item(row, 0)
            if chk_item is None:
                chk_item = QTableWidgetItem()
                chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                chk_item.setCheckState(Qt.Checked if code in self._ai_exclude_codes else Qt.Unchecked)
                self.holdings_table.setItem(row, 0, chk_item)
            else:
                # 체크 상태는 사용자가 변경하므로 덮어쓰지 않음
                pass

            # col 1~8: 데이터
            cols = [
                h["name"], h["buy_price"], h["cur_price"],
                h["day_change"], h["pnl_rate"], h["qty"],
                h["eval_amt"], h["pnl_amt"]
            ]
            for col, val in enumerate(cols):
                actual_col = col + 1  # 체크박스가 0번이므로 +1
                item = self.holdings_table.item(row, actual_col)
                if item is None:
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.holdings_table.setItem(row, actual_col, item)
                else:
                    item.setText(val)
                # 등락률/수익률/손익금액 색상
                if col in [3, 4, 7]:
                    if val.startswith("+"):
                        item.setForeground(self._qcolor("#ff6b6b"))
                    elif val.startswith("-"):
                        item.setForeground(self._qcolor("#74b9ff"))

            # col 9: AI 판단
            sig = sig_map.get(code)
            if sig:
                if sig["signal_type"] == "SELL":
                    score = sig.get("score", 0)
                    ai_text, ai_color = f"매도{score:.0f}", "#ff6b6b"
                else:
                    sell_score = sig.get("score", 50)
                    hold_score = 100.0 - sell_score
                    ai_text, ai_color = f"보유{hold_score:.0f}", "#fdcb6e"
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
        """AI 엔진이 보유종목 SELL 판단에 쓸 holdings_cache 저장 (백그라운드 I/O)"""
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
            exe_name = os.path.basename(sys.executable).lower()
            fname = "holdings_cache_mock.json" if "mock" in exe_name else "holdings_cache_real.json"
        else:
            base = os.path.dirname(os.path.abspath(__file__))
            fname = "holdings_cache.json"
        path = os.path.join(base, fname)
        # 메인 스레드에서 payload 생성 (빠름), 파일 I/O는 백그라운드
        payload = []
        for h in holdings:
            rc = h.get("raw_code", "")
            if not rc:
                continue
            clean_code = rc[1:] if rc.startswith("A") and len(rc) == 7 else rc
            payload.append({
                "code"      : clean_code,
                "name"      : h.get("name", ""),
                "buy_price" : h.get("raw_buy_price", 0),
                "qty"       : h.get("raw_qty", 0),
                "cur_price" : h.get("raw_cur_price", 0),
                "pnl_rate"  : h.get("raw_pnl_rate", 0),
            })
        threading.Thread(target=self._write_holdings_cache_io, args=(payload, path), daemon=True).start()

    @staticmethod
    def _write_holdings_cache_io(payload, path):
        """백그라운드 파일 쓰기"""
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            os.replace(tmp, path)
        except Exception:
            pass

    # ── 계좌 요약 업데이트 ──
    def _update_summary(self, summary):
        """타이틀바 계좌요약 라벨 갱신 — HTS 동일 필드"""
        def _set(key, val_key, use_color=False):
            if key not in self.summary_labels:
                return
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
        _set("손익률",   "total_pnl_rate", use_color=True)
        if "보유종목" in self.summary_labels:
            self.summary_labels["보유종목"].setText(summary.get("stock_count", "-"))

    # ── 모의/실전 전환 ──
    def switch_trade_mode(self, mode):
        now = datetime.now().strftime("%H:%M:%S")
        # 자동매매 중이면 먼저 정지
        if getattr(self, 'is_trading', False):
            self.is_trading = False
            if hasattr(self, 'trade_timer'):
                self.trade_timer.stop()
            self.btn_start.setText("🚀 자동매매 시작")
            self.btn_start.setStyleSheet(
                "background-color: #00b894; color: #fff; border: none; font-weight: bold;"
            )
            self._log(f"[{now}] ⏸ 모드 전환으로 자동매매 정지")
        # 보유종목 초기화 (이전 모드 데이터 제거)
        self.holdings_data = []
        self._update_holdings_table([])
        self.trade_mode = mode
        # 버튼 상태 업데이트
        self.btn_mock.setChecked(mode == "mock")
        self.btn_real.setChecked(mode == "real")
        # config에 모드 저장
        config = load_config()
        config["api"]["trade_mode"] = mode
        save_config(config)
        mode_name = "모의투자" if mode == "mock" else "실전투자"
        self._log(f"[{now}] 투자모드: {mode_name}")

    # ── 설정 창 열기 ──
    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            pass  # 설정 저장 완료

            now = datetime.now().strftime("%H:%M:%S")
            self._log(f"[{now}] 🔄 설정 변경 → 새 조건으로 재스캔 시작")

    # ── 자동/수동 모드 전환 ──
    def toggle_auto_mode(self):
        self.btn_auto_mode.setChecked(True)
        self.btn_manual_mode.setChecked(False)
        # 1위 종목 이름 가져오기
        top_stock = self.rec_list.item(0, 1).text() if self.rec_list.rowCount() > 0 else "없음"
        self._log(f"[모드] 🤖 자동 모드 활성 → 1위 종목 [{top_stock}] 자동매수 대기중")

    def toggle_manual_mode(self):
        self.btn_manual_mode.setChecked(True)
        self.btn_auto_mode.setChecked(False)
        self._log("[모드] ✋ 수동 모드 활성 → 직접 종목을 선택하세요")

    def set_auto_trade(self, name, action):
        self._log(f"[자동{action}] {name} → {action} 신호 등록됨")

    def set_manual_trade(self, name):
        self._log(f"[수동] {name} → 수동매매 모드")

    def sell_stock(self, name, code=None, qty=None):
        now = datetime.now().strftime("%H:%M:%S")
        if not code or not qty:
            self._log(f"[{now}] ❌ {name} 종목코드/수량 정보 없음")
            return
        if not self.api:
            self._log(f"[{now}] ❌ Open API 미연결 - 매도 불가")
            return
        self._log(f"[{now}] 🔴 매도 주문 요청: {name} ({code}) {qty}주 시장가")
        result = self.api.sell_order(code, qty, price=0)
        if result:
            self._log(f"[{now}] 🔴 매도 체결: {name} {qty}주")
            self._request_holdings_refresh()
            # 당일 매도 시간 기록 (재매수 쿨다운용)
            self._record_sell_time(code)
            # 매매 기록 (학습용)
            try:
                from ai_engine.learning.trade_recorder import TradeRecorder
                # 현재가 가져오기 (보유목록에서)
                sell_price = 0
                for h in self.holdings_data:
                    if h.get("raw_code") == code:
                        sell_price = h.get("raw_cur_price", 0)
                        break
                if sell_price > 0:
                    TradeRecorder().record_sell(code, sell_price, qty)
            except Exception:
                pass
            pass  # 잔고 갱신은 xingAPI에서 처리
        else:
            self._log(f"[{now}] ❌ 매도 실패: {name}")

    def _update_theme_section(self, themes: list):
        """API에서 받은 테마 데이터로 카드 갱신 (메인 스레드)"""
        if not hasattr(self, 'theme_layout') or not themes:
            return

        # placeholder 제거
        if hasattr(self, '_theme_placeholder') and self._theme_placeholder:
            self._theme_placeholder.deleteLater()
            self._theme_placeholder = None

        # 기존 카드 제거
        while self.theme_layout.count():
            item = self.theme_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 테마 데이터 저장 (관련종목 조회용)
        self._theme_data = themes[:10]

        for t in themes[:10]:
            name  = t.get("name", "")
            code  = t.get("code", "")
            diff  = t.get("diff", 0.0)
            diff_str = t.get("diff_str", f"{diff:+.2f}%")
            color = "#ff6b6b" if diff >= 0 else "#74b9ff"

            card = QFrame()
            card.setStyleSheet(
                f"background-color: {self._theme['panel']}; border-left: 3px solid {color}; border-radius: 2px;"
            )
            card.setFixedHeight(26)
            card.setCursor(Qt.PointingHandCursor)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(6, 0, 4, 0)
            cl.setSpacing(3)

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("color: #fff; font-size: 11px;")
            chg_lbl = QLabel(diff_str)
            chg_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
            chg_lbl.setFixedWidth(55)
            chg_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            stocks_btn = QPushButton("관련종목")
            stocks_btn.setFixedWidth(48)
            stocks_btn.setFixedHeight(18)
            stocks_btn.setStyleSheet(
                "background-color: #3d3d60; color: #e8e8ff; border: none; "
                "border-radius: 2px; font-size: 9px; padding: 0px 2px;"
            )
            stocks_btn.setCursor(Qt.PointingHandCursor)
            stocks_btn.clicked.connect(lambda _, n=name, c=code: self.show_theme_stocks(n, c))

            cl.addWidget(name_lbl, stretch=1)
            cl.addWidget(chg_lbl)
            cl.addWidget(stocks_btn)
            self.theme_layout.addWidget(card)

    def show_theme_stocks(self, theme_name, tmcode=""):
        """테마 관련종목을 API에서 조회하여 표시 (토글)"""
        # 같은 테마 재클릭 → 닫기
        if (self.related_table.isVisible()
                and getattr(self, '_current_theme', '') == theme_name):
            self.related_table.hide()
            self.related_grp.setTitle("📋 관련종목")
            self._current_theme = ''
            return
        self._current_theme = theme_name
        self.related_grp.setTitle(f"  {theme_name} 관련종목")
        if not tmcode:
            self.related_table.setRowCount(1)
            item = QTableWidgetItem("테마코드 없음")
            item.setTextAlignment(Qt.AlignCenter)
            self.related_table.setItem(0, 0, item)
            self.related_table.show()
            return
        stocks = []
        if self.api:
            try:
                stocks = self.api.get_theme_stocks(tmcode)
            except Exception as e:
                print(f"[테마종목] 조회 오류: {e}")
        self.related_table.show()
        if not stocks:
            self.related_table.setRowCount(1)
            item = QTableWidgetItem("종목 데이터 없음")
            item.setTextAlignment(Qt.AlignCenter)
            self.related_table.setItem(0, 0, item)
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

    # ── AI 캐시 저장 (테마/업종 → scorer 연결) ──
    def _parse_index_diff(self, idx_data) -> float:
        """지수 데이터에서 등락률(%) 추출"""
        if not idx_data:
            return 0.0
        try:
            # list이면 첫 번째 요소 사용
            row = idx_data[0] if isinstance(idx_data, list) else idx_data
            rt = float(str(row.get("diffjisu", 0)).replace(",", ""))
            sign_cd = str(row.get("sign", "3"))
            if sign_cd == "5":
                rt = -abs(rt)
            elif sign_cd == "2":
                rt = abs(rt)
            # jisu 또는 pricejisu 필드 사용
            jisu = float(str(row.get("pricejisu", row.get("jisu", 0))).replace(",", ""))
            if jisu > 0:
                return rt / jisu * 100
        except Exception:
            pass
        return 0.0

    def _save_index_cache(self, kospi_data, kosdaq_data):
        """코스피/코스닥 지수를 AI 캐시에 저장 (백그라운드)"""
        kospi_diff = self._parse_index_diff(kospi_data)
        kosdaq_diff = self._parse_index_diff(kosdaq_data)
        def _worker():
            try:
                from ai_engine.conditions.theme_sector import _get_cache_path
                import json as _json
                path = _get_cache_path()
                cache = {}
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        cache = _json.load(f)
                cache["indices"] = {
                    "kospi_diff": round(kospi_diff, 2),
                    "kosdaq_diff": round(kosdaq_diff, 2)
                }
                with open(path, "w", encoding="utf-8") as f:
                    _json.dump(cache, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _save_market_cache(self, sectors=None):
        """업종 데이터를 AI 캐시에 저장 (백그라운드)"""
        sector_data = []
        if sectors:
            for s in sectors:
                sector_data.append({
                    "name": s.get("name", ""),
                    "diff": s.get("diff", 0.0)
                })
        def _worker():
            try:
                from ai_engine.conditions.theme_sector import save_market_cache
                save_market_cache(sectors=sector_data)
            except Exception:
                pass
        threading.Thread(target=_worker, daemon=True).start()

    def _save_theme_cache(self, themes):
        """테마 데이터 + 상위 테마 소속 종목을 AI 캐시에 저장 (백그라운드)"""
        def _worker():
            try:
                from ai_engine.conditions.theme_sector import save_market_cache
                import time as _time

                theme_list = []
                for t in themes[:20]:
                    theme_list.append({
                        "name": t.get("name", ""),
                        "code": t.get("code", ""),
                        "diff": t.get("diff", 0.0)
                    })

                theme_stocks = {}
                # TODO: xingAPI 테마종목 조회 구현

                save_market_cache(themes=theme_list, theme_stocks=theme_stocks)
            except Exception:
                pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    # ── HTS 종목 연동 ──
    def _find_hts_window(self):
        """LS증권 투혼 창 핸들 찾기 (안전한 메모리 관리)"""
        user32 = ctypes.windll.user32
        hts_hwnd = [None]  # Use list to avoid closure issues

        def enum_cb(hwnd, _):
            try:
                if hts_hwnd[0]:
                    return True
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        title = buf.value
                        if "투혼" in title:
                            hts_hwnd[0] = hwnd
                            return False  # Stop enumeration after finding
            except Exception:
                pass
            return True

        try:
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        except Exception:
            pass

        return hts_hwnd[0]

    def _activate_window(self, hwnd):
        """
        윈도우를 확실하게 앞으로 가져오기 (스레드 안전)
        - SW_RESTORE: 최소화된 창 복원
        - BringWindowToTop: Z-order 최상단으로
        - SetForegroundWindow: 입력 포커스 설정
        """
        if not hwnd:
            return

        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            # 현재 포그라운드 스레드 정보 취득
            current_thread = kernel32.GetCurrentThreadId()
            fg_hwnd = user32.GetForegroundWindow()
            fg_thread = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(fg_thread))
            fg_thread_id = fg_thread.value

            # 다른 스레드의 입력 허용
            if current_thread != fg_thread_id:
                user32.AttachThreadInput(current_thread, fg_thread_id, True)
                time.sleep(0.01)

            # 창 활성화
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.02)

            # 스레드 입력 분리
            if current_thread != fg_thread_id:
                user32.AttachThreadInput(current_thread, fg_thread_id, False)

        except Exception as e:
            print(f"Error activating window: {e}")

    def _send_to_hts(self, stock_code, stock_name=""):
        """
        HTS 창에 종목코드 직접 전달 (PostMessage 방식 - 포커스 불필요)
        """
        now = datetime.now().strftime("%H:%M:%S")
        code = stock_code.replace("A", "").replace("a", "").strip()
        if not code:
            self._log(f"[{now}] ⚠️ {stock_name} → 종목코드 없음")
            return

        # 클립보드에도 복사 (백업)
        clipboard = QApplication.clipboard()
        clipboard.setText(code)

        hts_hwnd = self._find_hts_window()
        if not hts_hwnd:
            self._log(f"[{now}] ⚠️ HTS(LS증권 투혼) 미실행 → {stock_name}({code}) 클립보드 복사됨")
            return

        try:
            user32 = ctypes.windll.user32
            WM_CHAR = 0x0102
            WM_KEYDOWN = 0x0100
            WM_KEYUP = 0x0101
            VK_RETURN = 0x0D

            # HTS 창에 직접 종목코드 문자 전송 (포커스 상관없이 동작)
            for ch in code:
                user32.PostMessageW(hts_hwnd, WM_CHAR, ord(ch), 0)

            # Enter 키 전송
            time.sleep(0.1)
            user32.PostMessageW(hts_hwnd, WM_KEYDOWN, VK_RETURN, 0)
            time.sleep(0.01)
            user32.PostMessageW(hts_hwnd, WM_KEYUP, VK_RETURN, 0)

            self._log(f"[{now}] ✅ HTS 연동: {stock_name} ({code})")
        except Exception as e:
            self._log(f"[{now}] ⚠️ HTS 연동 오류: {e} → 코드 클립보드 복사됨")

    def _on_exclude_changed(self, row, col):
        """감시제외 체크박스 변경 → 저장"""
        if col != 0:
            return
        if row >= len(self.holdings_data):
            return
        code = self.holdings_data[row].get("raw_code", "")
        item = self.holdings_table.item(row, 0)
        if item and item.checkState() == Qt.Checked:
            self._ai_exclude_codes.add(code)
        else:
            self._ai_exclude_codes.discard(code)
        self._save_ai_exclude()

    def _load_ai_exclude(self) -> set:
        """감시제외 종목 로드"""
        try:
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(os.path.dirname(sys.executable))
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, "ai_exclude.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return set(json.load(f))
        except Exception:
            pass
        return set()

    def _save_ai_exclude(self):
        """감시제외 종목 저장"""
        try:
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(os.path.dirname(sys.executable))
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, "ai_exclude.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(list(self._ai_exclude_codes), f)
        except Exception:
            pass

    def _on_holdings_click(self, row, col):
        """보유종목 클릭 → HTS 차트 연동"""
        if row < len(self.holdings_data):
            h = self.holdings_data[row]
            self._send_to_hts(h["raw_code"], h["name"])

    def _on_scan_click(self, row, col):
        """AI 스캔종목 클릭 → HTS 차트 연동"""
        name_item = self.scan_list.item(row, 0)
        if name_item:
            name = name_item.text()
            code = getattr(self, '_scan_codes', {}).get(row, "")
            self._send_to_hts(code, name)

    def _on_related_click(self, row, col):
        """관련종목 클릭 → HTS 차트 연동"""
        name_item = self.related_table.item(row, 0)
        if name_item:
            name = name_item.text()
            now = datetime.now().strftime("%H:%M:%S")
            clipboard = QApplication.clipboard()
            clipboard.setText(name)
            self._log(f"[{now}] 📊 {name} → 종목명 클립보드 복사 (HTS에서 검색)")

    def _open_chart_from_scan(self):
        """AI 스캔종목 차트▶ 버튼 클릭"""
        row = self.scan_list.currentRow()
        if row >= 0:
            name_item = self.scan_list.item(row, 0)
            if name_item:
                name = name_item.text()
                code = getattr(self, '_scan_codes', {}).get(row, "")
                self._send_to_hts(code, name)

    def _manual_buy_from_scan(self):
        """AI 스캔종목에서 수동매수 버튼 클릭"""
        row = self.scan_list.currentRow()
        if row < 0:
            return
        name_item = self.scan_list.item(row, 0)
        if not name_item:
            return
        name = name_item.text()
        code = getattr(self, '_scan_codes', {}).get(row, "")
        now = datetime.now().strftime("%H:%M:%S")
        if not self.api:
            self._log(f"[{now}] ❌ Open API 미연결 - 매수 불가")
            return
        if not code:
            self._log(f"[{now}] ❌ 종목코드 없음: {name}")
            return
        config = self._get_config()
        buy_amount = config["account"].get("buy_amount", 1000000)
        price_item = self.scan_list.item(row, 4)
        try:
            price = int(price_item.text().replace(",", "")) if price_item else 0
        except Exception:
            price = 0
        qty = max(1, buy_amount // price) if price > 0 else 1
        self._log(f"[{now}] 💸 수동매수: {name}({code}) {qty}주 시장가")
        result = self.api.buy_order(code, qty, price=0)
        if result:
            self._log(f"[{now}] ✅ 매수 체결: {name} {qty}주")
            self._request_holdings_refresh()
            try:
                from ai_engine.learning.trade_recorder import TradeRecorder
                TradeRecorder().record_buy(code, name, price, qty, 0, {})
            except Exception:
                pass
        else:
            self._log(f"[{now}] ❌ 매수 실패: {name}")

    def _set_ai_btn_state(self, running: bool):
        """토글 스위치 상태 반영"""
        self.btn_ai_engine.setChecked(running)

    def _on_ai_toggle(self, checked: bool):
        """토글 스위치 조작 → 시작/정지"""
        if checked:
            self._ai_engine_start()
        else:
            self._ai_engine_stop()

    def _ai_engine_start(self):
        now = datetime.now().strftime("%H:%M:%S")
        if self.ai_thread and self.ai_thread.isRunning():
            return
        self.ai_thread = ScannerThread()
        self.ai_thread.status_signal.connect(self._on_ai_status)
        self.ai_thread.finished.connect(self._on_ai_engine_stopped)
        self.ai_thread.start()
        self.btn_ai_engine.setChecked(True)
        self._log(f"[{now}] ▶ AI 스캐너 시작")

    def _ai_engine_stop(self):
        now = datetime.now().strftime("%H:%M:%S")
        if not self.ai_thread or not self.ai_thread.isRunning():
            self.btn_ai_engine.setChecked(False)
            return
        self.btn_ai_engine.setStopping()
        self.ai_thread.stop()
        self._log(f"[{now}] ⏸ AI 엔진 정지 요청")

    # 하위 호환용 (다른 곳에서 호출 시)
    def toggle_ai_engine(self):
        self._on_ai_toggle(not (self.ai_thread and self.ai_thread.isRunning()))

    def _on_ai_status(self, msg: str):
        """AI 엔진 상태 메시지 수신"""
        now = datetime.now().strftime("%H:%M:%S")
        self._log(f"[{now}] {msg}")
        if "오류" in msg or "❌" in msg:
            self.btn_ai_engine.setChecked(False)

    def _on_ai_engine_stopped(self):
        """AI 스레드 종료 → 스위치 OFF"""
        if self.ai_thread:
            try:
                self.ai_thread.finished.disconnect(self._on_ai_engine_stopped)
                self.ai_thread.status_signal.disconnect(self._on_ai_status)
            except Exception:
                pass
        self.ai_thread = None
        self.btn_ai_engine.setChecked(False)

    # ── 자동매매 시작/정지 ──
    def toggle_trading(self):
        now = datetime.now().strftime("%H:%M:%S")
        if not self.is_trading:
            if not self.api:
                self._log(f"[{now}] ❌ Open API 미연결 - 자동매매 불가")
                return
            self.is_trading = True
            self.btn_start.setText("⏸ 자동매매 중지")
            self.btn_start.setStyleSheet("background-color: #d63031; color: #fff; border: none; font-weight: bold;")
            self._log(f"[{now}] ▶ 자동매매 시작!")
            # 자동매매 타이머 (10초마다 조건 체크)
            self.trade_timer = QTimer()
            self.trade_timer.timeout.connect(self.auto_trade_cycle)
            self.trade_timer.start(10000)
        else:
            self.is_trading = False
            self.btn_start.setText("🚀 자동매매 시작")
            self.btn_start.setStyleSheet(
                "background-color: #00b894; color: #fff; border: none; font-weight: bold;"
            )
            if hasattr(self, 'trade_timer'):
                self.trade_timer.stop()
            self._log(f"[{now}] ⏸ 자동매매 정지")
        self._update_summary({"stock_count": f"{len(self.holdings_data)}종목"})

    # ── 자동매매 사이클 ──
    def auto_trade_cycle(self):
        """10초마다 실행 - AI 신호 체크 → 매수/매도 판단"""
        if not self.api:
            return
        now = datetime.now().strftime("%H:%M:%S")
        config = self._get_config()

        # 매매 시간 체크
        start_time = config["account"]["start_time"]
        end_time   = config["account"]["end_time"]
        current_time = datetime.now().strftime("%H:%M")
        if current_time < start_time or current_time > end_time:
            # 장 마감 후 일일 리포트 자동 생성 (1회만)
            if current_time > end_time and not getattr(self, '_daily_report_done', False):
                self._daily_report_done = True
                try:
                    from ai_engine.learning.report_generator import generate_report
                    path = generate_report(days=30)
                    if path:
                        self._log(f"[{now}] 📊 일일 리포트 생성: {os.path.basename(path)}")
                except Exception as e:
                    self._log(f"[{now}] ⚠️ 리포트 생성 실패: {e}")
            return
        # 매매 시간 중이면 리포트 플래그 리셋
        self._daily_report_done = False

        # ── AI 신호 기반 매수 ──
        buy_amount  = config["account"]["buy_amount"]
        max_stocks  = config["account"]["max_stocks"]
        held_codes  = {h["raw_code"] for h in self.holdings_data}

        if len(held_codes) < max_stocks:
            # BUY 신호가 있을 때만 가용금액 체크
            buy_candidates = [s for s in self.ai_signals if s.get("signal_type") == "BUY"]
            if not buy_candidates:
                pass  # BUY 없으면 조용히 스킵
            else:
                available_cash = self.api.get_available_cash() if self.api else 0
                if available_cash <= 0:
                    self._log(f"[{now}] ⚠ 주문가능금액 없음 — 매수 스킵")
                elif available_cash > 0:
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
                        # 당일 매도 후 재매수 쿨다운 체크
                        if self._is_rebuy_blocked(code):
                            continue
                        # 실제 투입금액: 설정금액 vs 가용잔고 중 작은 값
                        actual_amount = min(buy_amount, available_cash)
                        qty = actual_amount // price
                        if qty <= 0:
                            self._log(
                                f"[{now}] ⚠️ 잔고부족: {name}({code}) "
                                f"가용:{available_cash:,}원 < 1주({price:,}원)"
                            )
                            continue
                        # 매수 근거 상세 로그
                        buy_conds = sig.get("conditions", {})
                        buy_details = [f"{k}: {v['detail']}"
                                       for k, v in buy_conds.items()
                                       if v.get("score", 0) >= 70]
                        buy_detail_str = " | ".join(buy_details[:3]) if buy_details else ""
                        self._log(
                            f"[{now}] 🤖 AI매수: {name}({code}) "
                            f"점수:{sig['score']:.1f} 신뢰:{sig.get('confidence','')} "
                            f"투입:{actual_amount:,}원 → {qty}주"
                        )
                        if buy_detail_str:
                            self._log(f"  근거: {buy_detail_str}")
                        result = self.api.buy_order(code, qty, price=0) if self.api else None
                        if result:
                            self._log(f"[{now}] ✅ AI매수 체결: {name} {qty}주")
                            self._request_holdings_refresh()
                            # 체결 금액만큼 가용잔고 차감
                            available_cash -= qty * price
                            try:
                                from ai_engine.learning.trade_recorder import TradeRecorder
                                TradeRecorder().record_buy(
                                    code, name, price, qty,
                                    sig.get("score", 0),
                                    sig.get("conditions", {})
                                )
                            except Exception:
                                pass
                            held_codes.add(code)
                        else:
                            self._log(f"[{now}] ❌ AI매수 실패: {name}")
                        if len(held_codes) >= max_stocks:
                            break
                        if available_cash <= 0:
                            self._log(f"[{now}] ⚠️ 가용잔고 소진 — 매수 중단")
                            break

        # ── AI 매도 신호 체크 (보유종목 중 SELL 신호, A접두사 변환 매칭) ──
        sell_signals = {}
        for s in self.ai_signals:
            if s.get("signal_type") == "SELL":
                sc = s["stock_code"]
                sell_signals[sc] = s
                if sc.startswith("A") and len(sc) == 7:
                    sell_signals[sc[1:]] = s
                else:
                    sell_signals["A" + sc] = s
        for h in self.holdings_data:
            if h["raw_code"] in self._ai_exclude_codes:
                continue  # 감시제외 종목 → 자동매도 스킵
            if h["raw_code"] in sell_signals:
                sig = sell_signals[h["raw_code"]]
                # 상세 매도 근거 로그
                reasons = sig.get("sell_reason", "")
                score = sig.get("score", 0)
                conds = sig.get("conditions", {})
                sell_details = [f"{k.replace('[매도]','')}: {v['detail']}"
                                for k, v in conds.items()
                                if "[매도]" in k and v.get("score", 50) >= 60]
                detail_str = " | ".join(sell_details[:3]) if sell_details else reasons
                self._log(f"[{now}] 🤖 AI매도: {h['name']} 점수:{score:.1f} [{detail_str}]")
                self.sell_stock(h["name"], h["raw_code"], h["raw_qty"])

        # ── 미체결 주문 관리 ──
        self._manage_unfilled_orders(now)

        # ── 분할 손절 체크 (설정값 기반) ──
        loss_stages_raw = config["profit"].get("loss_stages", [(-3.0, 33.0), (-5.0, 33.0), (-7.0, 100.0)])
        loss_stages = [(t, r / 100.0) for t, r in loss_stages_raw]  # 비율을 0~1로 변환

        # ── 손절 + 수익 정산 체크 (단계별 분할 매도) ──
        profit_stages = config["profit"]["profit_stages"]
        sell_ratios   = config["profit"].get("sell_ratios", [20.0] * 5)
        loss_cut      = config["profit"].get("loss_cut", 0.0)

        # 보유 종목에서 사라진 코드 → 기록 정리
        held_code_set = {h["raw_code"] for h in self.holdings_data}
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

        for h in self.holdings_data:
            try:
                pnl = float(h["pnl_rate"].replace("%", "").replace("+", ""))
                code = h["raw_code"]

                # 분할 손절 체크
                done_loss = self._loss_cut_stages.get(code, -1)
                loss_handled = False
                for i, (threshold, ratio) in enumerate(loss_stages):
                    if i <= done_loss:
                        continue
                    if pnl <= threshold:
                        if ratio >= 1.0:
                            sell_qty = h["raw_qty"]
                            tag = "전량"
                        else:
                            sell_qty = max(1, int(h["raw_qty"] * ratio))
                            tag = f"{ratio:.0%}"
                        self._log(
                            f"[{now}] 🔴 분할손절 {i+1}차({threshold}%): {h['name']} ({h['pnl_rate']}) → {sell_qty}주({tag}) 매도"
                        )
                        self.sell_stock(h["name"], code, sell_qty)
                        self._loss_cut_stages[code] = i
                        loss_handled = True
                        break
                if loss_handled:
                    continue

                # 기존 손절 (사용자 설정값, 0이면 AI 능동 대응)
                # 분할 손절이 진행 중인 종목은 기존 손절 스킵 (중복 방지)
                if loss_cut > 0 and pnl <= -loss_cut and code not in self._loss_cut_stages:
                    self._log(
                        f"[{now}] 🔴 손절: {h['name']} ({h['pnl_rate']}) → 전량매도"
                    )
                    self.sell_stock(h["name"], code, h["raw_qty"])
                    continue

                # 수익 정산 (0이면 AI 능동 대응 → 해당 단계 스킵)
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
                        self._log(
                            f"[{now}] 📈 수익정산 {i+1}차: {h['name']} ({h['pnl_rate']}) → {sell_qty}주({ratio:.0f}%) 매도"
                        )
                        self.sell_stock(h["name"], code, sell_qty)
                        self._profit_sold_stages[code] = i
                        self._save_profit_stages()
                        break
            except:
                pass

        pass  # 잔고 갱신은 xingAPI에서 처리

    # ── 미체결 주문 관리 ──
    def _manage_unfilled_orders(self, now):
        """미체결 주문 추적: 매도 → 하향 추적, 매수 → 10~15분 후 취소"""
        if not self.api:
            return
        try:
            unfilled = self.api.get_unfilled_orders()
        except Exception:
            return

        if not unfilled:
            # 미체결이 일정 시간 없으면 추적 목록 초기화
            # (취소-재주문 직후 조회 지연 대비, 연속 2회 빈 목록일 때만)
            if not hasattr(self, '_unfilled_empty_count'):
                self._unfilled_empty_count = 0
            self._unfilled_empty_count += 1
            if self._unfilled_empty_count >= 3:
                self._pending_buy_orders.clear()
                self._pending_sell_orders.clear()
                self._unfilled_empty_count = 0
            return
        self._unfilled_empty_count = 0

        current_ts = datetime.now()

        for order in unfilled:
            ono = order["order_no"]
            code = order["stock_code"]
            name = order.get("stock_name", code)
            unf_qty = order["unfilled_qty"]

            if order["bns_type"] == "SELL":
                # ── 매도 미체결 → 하향 추적 (시장가 재주문) ──
                if ono not in self._pending_sell_orders:
                    self._pending_sell_orders[ono] = {
                        "code": code, "name": name,
                        "time": current_ts, "qty": unf_qty, "retry": 0
                    }

                info = self._pending_sell_orders[ono]
                elapsed = (current_ts - info["time"]).total_seconds()

                # 2~4초 경과 → 원주문 취소 후 시장가 재주문
                if elapsed >= 3 and info["retry"] < 3:
                    self._log(f"[{now}] 🔄 매도 하향추적: {name} 미체결 {unf_qty}주 → 시장가 재주문")
                    cancel_result = self.api.cancel_order(ono, code, unf_qty)
                    if cancel_result:
                        self.api.sell_order(code, unf_qty, price=0)
                    else:
                        self._log(f"[{now}] ⚠️ 원주문 취소 실패 (이미 체결?) — 재주문 보류")
                    info["retry"] += 1
                    info["time"] = current_ts

            elif order["bns_type"] == "BUY":
                # ── 매수 미체결 → 10~15분 후 취소 ──
                if ono not in self._pending_buy_orders:
                    self._pending_buy_orders[ono] = {
                        "code": code, "name": name,
                        "time": current_ts, "qty": unf_qty
                    }

                info = self._pending_buy_orders[ono]
                elapsed = (current_ts - info["time"]).total_seconds()

                # 15분(900초) 경과 → 취소
                if elapsed >= 900:
                    self._log(f"[{now}] ⏰ 매수 미체결 취소: {name} {unf_qty}주 (15분 경과)")
                    self.api.cancel_order(ono, code, unf_qty)
                    if ono in self._pending_buy_orders:
                        del self._pending_buy_orders[ono]

        # 체결 완료된 주문 정리
        active_onos = {o["order_no"] for o in unfilled}
        for ono in list(self._pending_sell_orders.keys()):
            if ono not in active_onos:
                del self._pending_sell_orders[ono]
        for ono in list(self._pending_buy_orders.keys()):
            if ono not in active_onos:
                del self._pending_buy_orders[ono]

    # ── 익절 단계 기록 (파일 기반, 당일만 유효) ──
    def _profit_stages_path(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "profit_stages.json")

    def _load_profit_stages(self) -> dict:
        """파일에서 익절 완료 단계 로드 (날짜 다르면 초기화)"""
        try:
            path = self._profit_stages_path()
            if not os.path.exists(path):
                return {}
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 날짜가 오늘이 아니면 초기화
            if data.get("date") != datetime.now().strftime("%Y-%m-%d"):
                return {}
            return data.get("stages", {})
        except Exception:
            return {}

    def _save_profit_stages(self):
        """익절 완료 단계를 파일에 저장"""
        try:
            data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "stages": self._profit_sold_stages
            }
            with open(self._profit_stages_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ── 당일 매도 시간 기록 (재매수 쿨다운용, 파일 기반) ──
    def _sell_times_path(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "sell_times.json")

    def _load_sell_times(self) -> dict:
        """당일 매도 시간 기록 로드 {code: "HH:MM:SS"}"""
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
        """매도 시간 기록 (가장 최근 매도 시간만 유지)"""
        try:
            sells = self._load_sell_times()
            sells[code] = datetime.now().strftime("%H:%M:%S")
            data = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sells": sells
            }
            with open(self._sell_times_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _is_rebuy_blocked(self, code: str) -> bool:
        """재매수 쿨다운 중인지 확인"""
        try:
            from ai_engine.conditions._config_helper import load_defaults
            cooldown_min = int(load_defaults().get("rebuy_cooldown_min", 30))
            if cooldown_min <= 0:
                return False
            sells = self._load_sell_times()
            sell_time_str = sells.get(code)
            if not sell_time_str:
                return False
            sell_time = datetime.strptime(
                f"{datetime.now().strftime('%Y-%m-%d')} {sell_time_str}",
                "%Y-%m-%d %H:%M:%S"
            )
            elapsed = (datetime.now() - sell_time).total_seconds() / 60
            return elapsed < cooldown_min
        except Exception:
            return False

    def _get_splitter_path(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "splitter_sizes.json")

    def _save_splitter_sizes(self):
        try:
            geo = self.geometry()
            data = {
                "main": self.main_splitter.sizes(),
                "left": self.left_v_splitter.sizes(),
                "center": self.center_v_splitter.sizes(),
                "right": self.right_v_splitter.sizes(),
                "window": {
                    "x": geo.x(),
                    "y": geo.y(),
                    "width": geo.width(),
                    "height": geo.height(),
                    "maximized": self.isMaximized()
                }
            }
            with open(self._get_splitter_path(), "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[splitter] 저장 실패: {e}")

    def _load_splitter_sizes(self):
        try:
            path = self._get_splitter_path()
            if not os.path.exists(path):
                self.main_splitter.setSizes([650, 473, 384])
                self.left_v_splitter.setSizes([385, 385])
                self.center_v_splitter.setSizes([385, 385])
                self.right_v_splitter.setSizes([385, 385])
                return
            with open(path) as f:
                data = json.load(f)
            self.main_splitter.setSizes(data.get("main", [540, 400, 400]))
            self.left_v_splitter.setSizes(data.get("left", [520, 220]))
            self.center_v_splitter.setSizes(data.get("center", [350, 350]))
            self.right_v_splitter.setSizes(data.get("right", [400, 400]))
            # 창 크기/위치 복원
            win = data.get("window")
            if win:
                if win.get("maximized"):
                    self.showMaximized()
                else:
                    self.setGeometry(win["x"], win["y"], win["width"], win["height"])
        except Exception as e:
            print(f"[splitter] 불러오기 실패: {e}")

    def closeEvent(self, event):
        """창 닫을 때 스플리터 크기 저장 + 백그라운드 스레드 정리"""
        self._save_splitter_sizes()
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.stop()
            self.ai_thread.wait(500)
        event.accept()


# ─────────────────────────────────────────────
#  xingAPI 로그인 다이얼로그
# ─────────────────────────────────────────────
class XingLoginDialog(QDialog):
    """xingAPI COM 로그인 + ACF 파일 선택 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("StockTrader 로그인")
        self.setFixedSize(420, 390)
        self.setStyleSheet(build_style("mock"))
        self.xing = None          # 로그인 성공 시 XingAPI 객체
        self.login_mode = "mock"  # 로그인된 모드
        self.acf_path = ""        # ACF 파일 경로

        config = load_config()
        xing_cfg = config.get("xing", {})

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 20, 30, 20)

        # 타이틀
        title = QLabel("StockTrader")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("맑은 고딕", 18, QFont.Bold))
        title.setStyleSheet("color: #00b894; margin-bottom: 5px;")
        layout.addWidget(title)

        # ID
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.addWidget(QLabel("ID:"), 0, 0)
        self.edit_id = QLineEdit()
        self.edit_id.setText(xing_cfg.get("user_id", ""))
        self.edit_id.setPlaceholderText("xingAPI 사용자 ID")
        grid.addWidget(self.edit_id, 0, 1)

        # PW
        grid.addWidget(QLabel("PW:"), 1, 0)
        self.edit_pw = QLineEdit()
        self.edit_pw.setEchoMode(QLineEdit.Password)
        self.edit_pw.setPlaceholderText("비밀번호")
        grid.addWidget(self.edit_pw, 1, 1)

        # 인증서 PW (실전용)
        grid.addWidget(QLabel("인증서:"), 2, 0)
        self.edit_cert = QLineEdit()
        self.edit_cert.setEchoMode(QLineEdit.Password)
        self.edit_cert.setPlaceholderText("인증서 비밀번호 (실전만)")
        self.edit_cert.setEnabled(False)
        grid.addWidget(self.edit_cert, 2, 1)

        # 인증서 경로 (실전용)
        grid.addWidget(QLabel("인증서경로:"), 3, 0)
        cert_path_layout = QHBoxLayout()
        self.edit_cert_dir = QLineEdit()
        self.edit_cert_dir.setText(xing_cfg.get("cert_path", ""))
        self.edit_cert_dir.setPlaceholderText("공동인증서 폴더 (미입력시 기본경로)")
        self.edit_cert_dir.setEnabled(False)
        cert_path_layout.addWidget(self.edit_cert_dir)
        btn_cert_browse = QPushButton("찾기")
        btn_cert_browse.setFixedWidth(50)
        btn_cert_browse.setAutoDefault(False)
        btn_cert_browse.clicked.connect(self._browse_cert_dir)
        btn_cert_browse.setEnabled(False)
        self._btn_cert_browse = btn_cert_browse
        cert_path_layout.addWidget(btn_cert_browse)
        grid.addLayout(cert_path_layout, 3, 1)

        # 접속서버
        grid.addWidget(QLabel("서버:"), 4, 0)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["모의투자", "실전투자"])
        detected = _detect_trade_mode()
        if detected == "real":
            self.combo_mode.setCurrentIndex(1)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_change)
        grid.addWidget(self.combo_mode, 4, 1)
        if detected == "real":
            self._on_mode_change(1)

        layout.addLayout(grid)

        # ACF 파일 경로
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

        # 상태 메시지
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #fdcb6e; font-size: 11px;")
        layout.addWidget(self.lbl_status)

        # 버튼
        btn_layout = QHBoxLayout()
        self.btn_login = QPushButton("로그인")
        self.btn_login.setObjectName("btn_start")
        self.btn_login.setFixedHeight(36)
        self.btn_login.setDefault(True)
        self.btn_login.setAutoDefault(True)
        self.btn_login.clicked.connect(self._do_login)
        btn_layout.addWidget(self.btn_login)

        btn_skip = QPushButton("REST만 사용")
        btn_skip.setFixedHeight(36)
        btn_skip.setAutoDefault(False)
        btn_skip.setToolTip("xingAPI 없이 기존 REST API만 사용")
        btn_skip.clicked.connect(self._skip_login)
        btn_layout.addWidget(btn_skip)
        layout.addLayout(btn_layout)

    def _on_mode_change(self, idx):
        is_real = (idx == 1)
        self.edit_cert.setEnabled(is_real)
        self.edit_cert_dir.setEnabled(is_real)
        self._btn_cert_browse.setEnabled(is_real)
        self.setStyleSheet(build_style("real" if is_real else "mock"))

    def _browse_cert_dir(self):
        from PyQt5.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(
            self, "인증서 폴더 선택", "",
            QFileDialog.ShowDirsOnly
        )
        if path:
            self.edit_cert_dir.setText(path)

    def _browse_acf(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "ACF 파일 선택", "",
            "ACF 파일 (*.acf *.ACF);;모든 파일 (*)"
        )
        if path:
            self.edit_acf.setText(path)

    def _do_login(self):
        user_id = self.edit_id.text().strip()
        password = self.edit_pw.text()
        cert_pw = self.edit_cert.text()
        cert_dir = self.edit_cert_dir.text().strip()
        mode = "real" if self.combo_mode.currentIndex() == 1 else "mock"

        if mode == "mock" and (not user_id or not password):
            self.lbl_status.setText("ID와 비밀번호를 입력하세요")
            self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
            return

        self.lbl_status.setText("로그인 중...")
        self.lbl_status.setStyleSheet("color: #fdcb6e; font-size: 11px;")
        self.btn_login.setEnabled(False)
        QApplication.processEvents()

        try:
            from xing_api import XingAPI
            self.xing = XingAPI()
            ok, msg = self.xing.login(user_id, password, mode=mode,
                                       cert_password=cert_pw,
                                       cert_path=cert_dir)

            if ok:
                self.login_mode = mode
                self.acf_path = self.edit_acf.text().strip()

                # 설정 저장
                config = load_config()
                config["xing"]["user_id"] = user_id
                config["xing"]["acf_path"] = self.acf_path
                if cert_dir:
                    config["xing"]["cert_path"] = cert_dir
                config["api"]["trade_mode"] = mode
                save_config(config)

                self.lbl_status.setText(f"로그인 성공! ({msg})")
                self.lbl_status.setStyleSheet("color: #00b894; font-size: 11px;")
                QApplication.processEvents()
                time.sleep(0.5)
                self.accept()  # 다이얼로그 닫기 → 메인 윈도우로
            else:
                self.lbl_status.setText(f"로그인 실패: {msg}")
                self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
                self.xing = None
        except Exception as e:
            self.lbl_status.setText(f"오류: {e}")
            self.lbl_status.setStyleSheet("color: #e74c3c; font-size: 11px;")
            self.xing = None

        self.btn_login.setEnabled(True)

    def _skip_login(self):
        """xingAPI 로그인 건너뛰기"""
        self.xing = None
        self.login_mode = "mock" if self.combo_mode.currentIndex() == 0 else "real"
        self.acf_path = self.edit_acf.text().strip()

        config = load_config()
        config["api"]["trade_mode"] = self.login_mode
        if self.acf_path:
            config["xing"]["acf_path"] = self.acf_path
        save_config(config)

        self.accept()


# ─────────────────────────────────────────────
#  실행 진입점
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 1. xingAPI 로그인 다이얼로그
    login_dlg = XingLoginDialog()
    if login_dlg.exec_() != QDialog.Accepted:
        sys.exit(0)

    # 2. 메인 윈도우 생성
    window = MainWindow()

    # 디버그 로그 (원인 추적용)
    _dbg_base = os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    _dbg_path = os.path.join(_dbg_base, "debug_init.txt")
    def _dlog(msg):
        try:
            with open(_dbg_path, "a", encoding="utf-8") as _f:
                _f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        except: pass
    _dlog(f"xing={login_dlg.xing}, connected={login_dlg.xing.is_connected() if login_dlg.xing else 'N/A'}, acf={login_dlg.acf_path}")

    # 3. xingAPI 객체 전달 (로그인 성공 시)
    if login_dlg.xing and login_dlg.xing.is_connected():
        window.xing_api = login_dlg.xing
        window.acf_path = login_dlg.acf_path
        window.ls_badge.setText("XING")
        window.ls_badge.setStyleSheet(
            "background-color: #00b89422; color: #00b894; "
            "border: 1px solid #00b894; border-radius: 4px; padding: 4px 10px; font-size: 12px; font-weight: bold;"
        )
        print(f"[Main] xingAPI 연결됨 (모드: {login_dlg.login_mode})")

        # ACF 파일 읽어서 스캔 리스트 표시 (실투자 방식 동일)
        if login_dlg.acf_path:
            import traceback as _tb
            _dbg = os.path.join(os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__)), "debug_init.txt")
            def _log(msg):
                try:
                    with open(_dbg, "a", encoding="utf-8") as _f:
                        _f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
                except: pass
            try:
                _log(f"ACF 초기 스캔 시작: {login_dlg.acf_path}")
                stocks = window.xing_api.run_full_scan(login_dlg.acf_path)
                _log(f"ACF 초기 스캔 결과: {len(stocks) if stocks else 0}종목")
                from ai_engine.comm.signal_writer import write_signals
                if not stocks:
                    from xing_api import XingAPI as _XA
                    _m = login_dlg.login_mode or "mock"
                    stocks = _XA.load_warehouse(mode=_m)
                    if stocks:
                        _log(f"조건검색 0 → 기존 창고 {len(stocks)}종목 사용")
                if stocks:
                    _log(f"초기 스캔: {len(stocks)}종목 → 시그널 기록 시작")
                    _signals = [
                        {"stock_code": s["code"], "stock_name": s.get("name", ""),
                         "signal_type": "WATCH", "score": 0,
                         "current_price": s.get("price", 0),
                         "diff_rate": s.get("diff", 0.0),
                         "conditions": {}, "confidence": "LOW"}
                        for s in stocks
                    ]
                    write_signals(_signals, scan_count=len(stocks))
                    _log(f"시그널 기록 완료: {len(_signals)}개")
                else:
                    write_signals([], scan_count=0)
                    _log("창고도 비어있음")
            except Exception as e:
                _log(f"초기 스캔 오류: {e}\n{_tb.format_exc()}")
    else:
        window.xing_api = None
        window.acf_path = ""
        print("[Main] xingAPI 미연결")

    window.show()
    sys.exit(app.exec_())
