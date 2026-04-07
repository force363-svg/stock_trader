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
from ls_api import LSApi
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QTabWidget, QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QGroupBox, QGridLayout, QFrame,
    QScrollArea, QSizePolicy, QProgressBar, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

# ─────────────────────────────────────────────
#  다크 테마 스타일시트
# ─────────────────────────────────────────────
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: '맑은 고딕', Arial;
    font-size: 13px;
}
QLabel {
    color: #e0e0e0;
}
QPushButton {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #0f3460;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #533483;
}
QPushButton#btn_start {
    background-color: #00b894;
    color: #ffffff;
    border: none;
    font-weight: bold;
}
QPushButton#btn_start:hover {
    background-color: #00cec9;
}
QPushButton#btn_stop {
    background-color: #d63031;
    color: #ffffff;
    border: none;
    font-weight: bold;
}
QPushButton#btn_stop:hover {
    background-color: #e17055;
}
QPushButton#btn_settings {
    background-color: #533483;
    color: #ffffff;
    border: none;
    font-weight: bold;
    padding: 6px 16px;
}
QPushButton#btn_settings:hover {
    background-color: #6c5ce7;
}
QTableWidget {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    gridline-color: #0f3460;
    selection-background-color: #533483;
}
QTableWidget::item {
    padding: 4px;
}
QHeaderView::section {
    background-color: #0f3460;
    color: #a0c4ff;
    padding: 6px;
    border: none;
    font-weight: bold;
    font-size: 12px;
}
QTabWidget::pane {
    border: 1px solid #0f3460;
    background-color: #16213e;
}
QTabBar::tab {
    background-color: #1a1a2e;
    color: #a0a0a0;
    padding: 8px 16px;
    border: 1px solid #0f3460;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: #533483;
    color: #ffffff;
}
QTabBar::tab:hover {
    background-color: #0f3460;
    color: #ffffff;
}
QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #0f3460;
    color: #e0e0e0;
    border: 1px solid #533483;
    border-radius: 4px;
    padding: 4px 8px;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #6c5ce7;
}
QGroupBox {
    border: 1px solid #0f3460;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    color: #a0c4ff;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #a0c4ff;
}
QScrollBar:vertical {
    background-color: #16213e;
    width: 8px;
}
QScrollBar::handle:vertical {
    background-color: #0f3460;
    border-radius: 4px;
}
QCheckBox {
    color: #e0e0e0;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #533483;
    border-radius: 3px;
    background-color: #0f3460;
}
QCheckBox::indicator:checked {
    background-color: #533483;
}
QProgressBar {
    background-color: #0f3460;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #00b894;
    border-radius: 4px;
}
QDialog {
    background-color: #1a1a2e;
    color: #e0e0e0;
}
"""

# ─────────────────────────────────────────────
#  설정 다이얼로그
# ─────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 설정")
        self.setMinimumSize(700, 550)
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
        btn_save.clicked.connect(self._save_and_close)
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        layout.setContentsMargins(10, 10, 10, 10)

    def _load_values(self):
        c = self.config
        self.edit_buy_amount.setText(str(c["account"]["buy_amount"]))
        self.spin_max_stocks.setValue(c["account"]["max_stocks"])
        self.edit_start_time.setText(c["account"]["start_time"])
        self.edit_end_time.setText(c["account"]["end_time"])
        self.spin_risk.setValue(c["account"]["risk_limit"])
        for i, val in enumerate(c["profit"]["profit_stages"]):
            self.profit_edits[i].setValue(val)
        self.spin_loss.setValue(c["profit"]["loss_cut"])
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

    def _save_and_close(self):
        self.config["account"]["buy_amount"]   = int(self.edit_buy_amount.text() or 0)
        self.config["account"]["max_stocks"]   = self.spin_max_stocks.value()
        self.config["account"]["start_time"]   = self.edit_start_time.text()
        self.config["account"]["end_time"]     = self.edit_end_time.text()
        self.config["account"]["risk_limit"]   = self.spin_risk.value()
        self.config["profit"]["profit_stages"] = [e.value() for e in self.profit_edits]
        self.config["profit"]["loss_cut"]      = self.spin_loss.value()
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
        save_config(self.config)
        self.accept()

    # ── 탭 1: 계좌·매수 설정 ──
    def _tab_account(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        grp = QGroupBox("매수 설정")
        grid = QGridLayout(grp)

        grid.addWidget(QLabel("종목당 매수금액 (원):"), 0, 0)
        self.edit_buy_amount = QLineEdit("1000000")
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
        self.spin_risk.setRange(0.1, 20.0)
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

        grp_profit = QGroupBox("수익 정산 (단계별 분할 매도)")
        grid_p = QGridLayout(grp_profit)
        stages = [("1차", "3.0"), ("2차", "5.0"), ("3차", "8.0"), ("4차", "12.0"), ("5차", "20.0")]
        self.profit_edits = []
        for i, (label, val) in enumerate(stages):
            grid_p.addWidget(QLabel(f"수익 {label} 목표 (%):"), i, 0)
            edit = QDoubleSpinBox()
            edit.setRange(0.1, 100.0)
            edit.setValue(float(val))
            edit.setSuffix(" %")
            grid_p.addWidget(edit, i, 1)
            self.profit_edits.append(edit)

        grp_loss = QGroupBox("손실 정산 (손절)")
        grid_l = QGridLayout(grp_loss)
        grid_l.addWidget(QLabel("손절 기준 (%):"), 0, 0)
        self.spin_loss = QDoubleSpinBox()
        self.spin_loss.setRange(0.1, 30.0)
        self.spin_loss.setValue(3.0)
        self.spin_loss.setSuffix(" %")
        grid_l.addWidget(self.spin_loss, 0, 1)

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

        # 점수 임계값 + 스캔 설정 행
        thresh_row = QHBoxLayout()
        thresh_row.addWidget(QLabel("매수 임계값:"))
        self.spin_buy_thresh = QSpinBox()
        self.spin_buy_thresh.setRange(0, 100)
        self.spin_buy_thresh.setSuffix("점 이상")
        self.spin_buy_thresh.setFixedWidth(100)
        thresh_row.addWidget(self.spin_buy_thresh)
        thresh_row.addSpacing(20)
        thresh_row.addWidget(QLabel("보유 임계값:"))
        self.spin_hold_thresh = QSpinBox()
        self.spin_hold_thresh.setRange(0, 100)
        self.spin_hold_thresh.setSuffix("점 이상")
        self.spin_hold_thresh.setFixedWidth(100)
        thresh_row.addWidget(self.spin_hold_thresh)
        thresh_row.addSpacing(20)
        thresh_row.addWidget(QLabel("스캔 간격:"))
        self.spin_scan_interval = QSpinBox()
        self.spin_scan_interval.setRange(30, 3600)
        self.spin_scan_interval.setSuffix("초")
        self.spin_scan_interval.setFixedWidth(90)
        self.spin_scan_interval.setToolTip("AI 전 종목 스캔 주기 (최소 30초)")
        thresh_row.addWidget(self.spin_scan_interval)
        thresh_row.addSpacing(20)
        thresh_row.addWidget(QLabel("최대 종목 수:"))
        self.spin_max_scan = QSpinBox()
        self.spin_max_scan.setRange(100, 5000)
        self.spin_max_scan.setSingleStep(100)
        self.spin_max_scan.setSuffix("개")
        self.spin_max_scan.setFixedWidth(90)
        self.spin_max_scan.setToolTip("한 번에 스캔할 최대 종목 수")
        thresh_row.addWidget(self.spin_max_scan)
        thresh_row.addStretch()
        layout.addLayout(thresh_row)

        # 서브 탭
        sub_tabs = QTabWidget()
        sub_tabs.addTab(self._ai_cond_subtab("screening"), "📋 매수 스크리닝")
        sub_tabs.addTab(self._ai_cond_subtab("scoring"),   "⭐ 고려사항 점수")
        sub_tabs.addTab(self._ai_cond_subtab("sell"),      "🔴 매도 조건")
        layout.addWidget(sub_tabs)

        # 저장 버튼
        btn_save = QPushButton("💾 AI 조건 저장")
        btn_save.setObjectName("btn_settings")
        btn_save.clicked.connect(self._save_ai_conditions)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        # 초기값 로드
        self._load_ai_conditions()
        return w

    def _ai_cond_subtab(self, group):
        """조건 그룹별 서브탭 위젯 생성"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(4, 4, 4, 4)

        # 안내
        hint = QLabel("☑ 체크 = 활성 | 조건명 직접 입력 가능 | " +
                      ("가중치: 점수 비중" if group == "scoring" else "임계값: 판단 기준값 (없으면 0)"))
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint)

        # 테이블
        tbl = QTableWidget(0, 4 if group == "scoring" else 3)
        if group == "scoring":
            tbl.setHorizontalHeaderLabels(["활성", "조건명", "설명", "가중치"])
            tbl.setColumnWidth(0, 40); tbl.setColumnWidth(1, 160)
            tbl.setColumnWidth(2, 260); tbl.setColumnWidth(3, 60)
        else:
            tbl.setHorizontalHeaderLabels(["활성", "조건명", "설명/임계값"])
            tbl.setColumnWidth(0, 40); tbl.setColumnWidth(1, 180)
            tbl.setColumnWidth(2, 310)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.verticalHeader().setVisible(False)
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(
            "QTableWidget { background:#16213e; alternate-background-color:#1a1a2e; }"
            "QTableWidget::item { padding:3px; }"
        )
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
        return w

    # ── AI 조건 행 추가/삭제/이동 ──
    def _ai_add_row(self, group):
        tbl = getattr(self, f"_ai_tbl_{group}")
        row = tbl.rowCount()
        tbl.insertRow(row)
        chk = QTableWidgetItem()
        chk.setCheckState(Qt.Checked)
        chk.setTextAlignment(Qt.AlignCenter)
        tbl.setItem(row, 0, chk)
        tbl.setItem(row, 1, QTableWidgetItem("새 조건"))
        tbl.setItem(row, 2, QTableWidgetItem(""))
        if tbl.columnCount() == 4:
            tbl.setItem(row, 3, QTableWidgetItem("10"))
        tbl.scrollToBottom()
        tbl.editItem(tbl.item(row, 1))

    def _ai_del_row(self, group):
        tbl = getattr(self, f"_ai_tbl_{group}")
        rows = sorted(set(i.row() for i in tbl.selectedItems()), reverse=True)
        for r in rows:
            tbl.removeRow(r)

    def _ai_move_row(self, group, direction):
        tbl = getattr(self, f"_ai_tbl_{group}")
        row = tbl.currentRow()
        if row < 0:
            return
        target = row + direction
        if target < 0 or target >= tbl.rowCount():
            return
        for col in range(tbl.columnCount()):
            a = tbl.item(row, col)
            b = tbl.item(target, col)
            a_text  = a.text()  if a else ""
            b_text  = b.text()  if b else ""
            a_check = a.checkState() if a and a.flags() & Qt.ItemIsUserCheckable else None
            b_check = b.checkState() if b and b.flags() & Qt.ItemIsUserCheckable else None
            if col == 0:
                tbl.item(row, 0).setCheckState(b_check if b_check is not None else Qt.Unchecked)
                tbl.item(target, 0).setCheckState(a_check if a_check is not None else Qt.Unchecked)
            else:
                if a: a.setText(b_text)
                if b: b.setText(a_text)
        tbl.setCurrentCell(target, tbl.currentColumn())

    # ── engine_config.json 로드/저장 ──
    def _get_config_path(self):
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "engine_config.json")

    def _load_ai_conditions(self):
        path = self._get_config_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.spin_buy_thresh.setValue(cfg.get("thresholds", {}).get("buy", 80))
            self.spin_hold_thresh.setValue(cfg.get("thresholds", {}).get("hold", 50))
            self.spin_scan_interval.setValue(cfg.get("scan_interval_seconds", 60))
            self.spin_max_scan.setValue(cfg.get("max_scan_stocks", 2000))
            for group in ("screening", "scoring", "sell"):
                tbl = getattr(self, f"_ai_tbl_{group}")
                tbl.setRowCount(0)
                for item in cfg.get(group, []):
                    r = tbl.rowCount()
                    tbl.insertRow(r)
                    chk = QTableWidgetItem()
                    chk.setCheckState(Qt.Checked if item.get("enabled", True) else Qt.Unchecked)
                    chk.setTextAlignment(Qt.AlignCenter)
                    tbl.setItem(r, 0, chk)
                    tbl.setItem(r, 1, QTableWidgetItem(item.get("name", "")))
                    desc = item.get("description", item.get("threshold", ""))
                    tbl.setItem(r, 2, QTableWidgetItem(str(desc)))
                    if tbl.columnCount() == 4:
                        tbl.setItem(r, 3, QTableWidgetItem(str(item.get("weight", 10))))
        except Exception as e:
            print(f"[AI조건] 로드 실패: {e}")

    def _save_ai_conditions(self):
        path = self._get_config_path()
        try:
            cfg = {
                "version": "1.0",
                "thresholds": {
                    "buy":  self.spin_buy_thresh.value(),
                    "hold": self.spin_hold_thresh.value()
                },
                "scan_interval_seconds": self.spin_scan_interval.value(),
                "max_scan_stocks": self.spin_max_scan.value(),
                "screening": [],
                "scoring": [],
                "sell": []
            }
            for group in ("screening", "scoring", "sell"):
                tbl = getattr(self, f"_ai_tbl_{group}")
                for r in range(tbl.rowCount()):
                    chk  = tbl.item(r, 0)
                    name = tbl.item(r, 1)
                    desc = tbl.item(r, 2)
                    enabled = (chk.checkState() == Qt.Checked) if chk else True
                    entry = {
                        "enabled": enabled,
                        "name": name.text() if name else "",
                        "description": desc.text() if desc else ""
                    }
                    if tbl.columnCount() == 4:
                        w_item = tbl.item(r, 3)
                        try:
                            entry["weight"] = int(w_item.text()) if w_item else 10
                        except:
                            entry["weight"] = 10
                    cfg[group].append(entry)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            print(f"[AI조건] 저장 완료 → {path}")
        except Exception as e:
            print(f"[AI조건] 저장 실패: {e}")

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
        note_real.setStyleSheet("color: #888; font-size: 10px;")
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
        note_mock.setStyleSheet("color: #888; font-size: 10px;")
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

        grp = QGroupBox("역사 데이터")
        grid = QGridLayout(grp)
        grid.addWidget(QLabel("데이터 저장 경로:"), 0, 0)
        self.edit_data_path = QLineEdit("C:/stock_trader/data")
        grid.addWidget(self.edit_data_path, 0, 1)
        grid.addWidget(QLabel("다운로드 기간:"), 1, 0)
        self.combo_period = QComboBox()
        self.combo_period.addItems(["1년", "3년", "5년", "10년"])
        self.combo_period.setCurrentText("5년")
        grid.addWidget(self.combo_period, 1, 1)

        btn_download = QPushButton("📥 역사 데이터 다운로드")
        btn_download.setObjectName("btn_settings")
        grid.addWidget(btn_download, 2, 0, 1, 2)

        grp2 = QGroupBox("교차검증 설정")
        grid2 = QGridLayout(grp2)
        grid2.addWidget(QLabel("LS vs KRX 허용 오차 (%):"), 0, 0)
        self.spin_tolerance = QDoubleSpinBox()
        self.spin_tolerance.setValue(0.5)
        self.spin_tolerance.setSuffix(" %")
        grid2.addWidget(self.spin_tolerance, 0, 1)

        layout.addWidget(grp)
        layout.addWidget(grp2)
        layout.addStretch()
        return w


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
        self.setFixedSize(130, 32)
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

        font = QFont("맑은 고딕", 9, QFont.Bold)
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
#  API 초기 연결 스레드 (토큰 취득 → 첫 데이터 로드)
#  창을 먼저 띄우고, 연결은 백그라운드에서 처리
# ─────────────────────────────────────────────
class ApiInitThread(QThread):
    connected    = pyqtSignal(bool, str)   # (성공여부, 오류메시지)
    data_ready   = pyqtSignal(dict)        # 첫 데이터 로드 완료

    def __init__(self, api):
        super().__init__()
        self.api = api

    def run(self):
        # 1단계: 토큰 취득
        try:
            ok = self.api.get_token()
        except Exception as e:
            self.connected.emit(False, str(e))
            return

        if not ok:
            self.connected.emit(False, getattr(self.api, 'last_error', '연결 실패'))
            return

        self.connected.emit(True, "")

        # 2단계: 첫 데이터 로드 (연결 성공 직후)
        result = {}
        try:
            result["holdings"], result["summary"] = self.api.get_holdings_for_ui()
        except Exception:
            result["holdings"], result["summary"] = [], {}
        try:
            result["kospi"]  = self.api.get_market_index("001")
            result["kosdaq"] = self.api.get_market_index("301")
        except Exception:
            pass
        try:
            result["sectors"] = self.api.get_sector_indices()
        except Exception:
            result["sectors"] = []
        try:
            result["themes"] = self.api.get_themes()
        except Exception:
            result["themes"] = []
        self.data_ready.emit(result)


# ─────────────────────────────────────────────
#  데이터 조회 백그라운드 스레드 (주기적 갱신)
# ─────────────────────────────────────────────
class DataFetchThread(QThread):
    done = pyqtSignal(dict)   # 완료 시 결과 dict 전달

    def __init__(self, api):
        super().__init__()
        self.api = api

    def run(self):
        result = {}
        try:
            result["holdings"], result["summary"] = self.api.get_holdings_for_ui()
        except Exception as e:
            result["holdings"], result["summary"] = [], {}
            result["error_holdings"] = str(e)

        try:
            result["kospi"]  = self.api.get_market_index("001")
            result["kosdaq"] = self.api.get_market_index("301")
        except Exception as e:
            result["error_index"] = str(e)

        try:
            result["sectors"] = self.api.get_sector_indices()
        except Exception as e:
            result["sectors"] = []
            result["error_sectors"] = str(e)

        try:
            result["themes"] = self.api.get_themes()
        except Exception as e:
            result["themes"] = []

        self.done.emit(result)


# ─────────────────────────────────────────────
#  AI 엔진 백그라운드 스레드
# ─────────────────────────────────────────────
class AIEngineThread(QThread):
    """AI 엔진을 GUI 내부 백그라운드 스레드로 실행"""
    status_signal = pyqtSignal(str)   # 상태 메시지 → GUI 로그

    def __init__(self, mode="real"):
        super().__init__()
        self.mode     = mode
        self._running = False

    def run(self):
        self._running = True
        self.status_signal.emit("[AI엔진] 시작 중...")
        try:
            import sys, os
            # frozen exe / 개발 환경 모두 대응
            if getattr(sys, 'frozen', False):
                _root = os.path.dirname(sys.executable)
                # PyInstaller onedir: sys._MEIPASS에 패키지 있음
                _pkg  = getattr(sys, '_MEIPASS', _root)
            else:
                _root = os.path.dirname(os.path.abspath(__file__))
                _pkg  = _root
            for p in (_root, _pkg):
                if p not in sys.path:
                    sys.path.insert(0, p)

            from ai_engine.db.database          import init_db
            from ai_engine.data.ls_data_fetcher import LSDataFetcher
            from ai_engine.core.scanner         import Scanner
            from ai_engine.comm.signal_writer   import write_signals
            from ai_engine.comm.command_reader  import read_command
            from ai_engine.learning.weight_optimizer import optimize_weights

            init_db()
            fetcher = LSDataFetcher(mode=self.mode)
            if not fetcher.connect():
                self.status_signal.emit("[AI엔진] ❌ API 연결 실패")
                return

            scanner    = Scanner(fetcher)
            last_scan  = 0
            last_held  = 0
            last_learn = ""
            last_closing = ""
            last_buy_signals = []   # 마지막 BUY 신호 보존 (장외 보유종목 판단 시 활용)
            import json as _json
            import time
            from datetime import datetime
            _cfg_path = os.path.join(_root, "engine_config.json")

            self.status_signal.emit("[AI엔진] ✅ 준비 완료")

            while self._running:
                now_hm = datetime.now().strftime("%H:%M")
                today  = datetime.now().strftime("%Y%m%d")

                # GUI 명령 체크
                cmd = read_command()
                if cmd.get("command") == "stop":
                    break

                # engine_config.json에서 스캔간격 실시간 반영
                try:
                    with open(_cfg_path, "r", encoding="utf-8") as _f:
                        _cfg = _json.load(_f)
                    scan_interval = max(10, int(_cfg.get("scan_interval_seconds", 60)))
                    max_scan      = int(_cfg.get("max_scan_stocks", 2000))
                except Exception:
                    scan_interval = 60
                    max_scan      = 2000

                # 장 마감 후 학습 (1일 1회)
                if now_hm >= "15:40" and last_learn != today:
                    self.status_signal.emit("[AI엔진] 📚 가중치 학습 중...")
                    try:
                        optimize_weights()
                        self.status_signal.emit("[AI엔진] ✅ 가중치 학습 완료")
                    except Exception as e:
                        self.status_signal.emit(f"[AI엔진] 학습 오류: {e}")
                    last_learn = today

                # 보유종목 판단 (시간 무관, 주기적)
                if time.time() - last_held >= scan_interval:
                    try:
                        from ai_engine.core.scanner import _load_holdings_cache
                        from ai_engine.core.signal_generator import generate_sell_signal
                        held = _load_holdings_cache()
                        if held:
                            self.status_signal.emit(f"[AI엔진] 🔍 보유종목 판단 중... ({len(held)}종목)")
                            held_signals = []
                            for h in held:
                                code = h.get("code", "")
                                name = h.get("name", "")
                                if not code:
                                    continue
                                try:
                                    data = scanner._fetch_data(code)
                                    sig  = generate_sell_signal(code, name, data, h)
                                    held_signals.append(sig)
                                except Exception:
                                    pass
                            if held_signals:
                                combined = held_signals + last_buy_signals
                                write_signals(combined, scan_count=len(held))
                                sell_c = sum(1 for s in held_signals if s["signal_type"] == "SELL")
                                hold_c = sum(1 for s in held_signals if s["signal_type"] == "HOLD")
                                self.status_signal.emit(
                                    f"[AI엔진] ✅ 보유종목 판단 → 보유:{hold_c} 매도:{sell_c}"
                                )
                    except Exception as e:
                        self.status_signal.emit(f"[AI엔진] 보유종목 판단 오류: {e}")
                    last_held = time.time()

                # 장중 전체 스캔 (BUY 신호 포함)
                if "09:00" <= now_hm <= "15:30":
                    if time.time() - last_scan >= scan_interval:
                        self.status_signal.emit(
                            f"[AI엔진] 🔍 전 종목 스캔 중... (간격:{scan_interval}초)"
                        )
                        try:
                            signals, count = scanner.run_scan(max_stocks=max_scan)
                            write_signals(signals, scan_count=count)
                            last_buy_signals = [s for s in signals if s.get("signal_type") == "BUY"]
                            buy_cnt  = sum(1 for s in signals if s.get("signal_type") == "BUY")
                            sell_cnt = sum(1 for s in signals if s.get("signal_type") == "SELL")
                            hold_cnt = sum(1 for s in signals if s.get("signal_type") == "HOLD")
                            self.status_signal.emit(
                                f"[AI엔진] ✅ {count}종목 스캔 → 매수:{buy_cnt} 보유:{hold_cnt} 매도:{sell_cnt}"
                            )
                        except Exception as e:
                            self.status_signal.emit(f"[AI엔진] 스캔 오류: {e}")
                        last_scan = time.time()

                time.sleep(5)   # 5초마다 체크 (명령/간격 변경 빠른 반영)

        except Exception as e:
            import traceback
            self.status_signal.emit(f"[AI엔진] ❌ 오류: {type(e).__name__}: {e}")
            self.status_signal.emit(f"[AI엔진] 상세: {traceback.format_exc().splitlines()[-1]}")
        finally:
            if self._running:   # 정상 정지가 아닌 오류 종료
                self.status_signal.emit("[AI엔진] 비정상 종료")

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(DARK_STYLE)

        # API 초기화 (exe 이름으로 모드 우선 감지)
        config = load_config()
        detected = _detect_trade_mode()
        self.trade_mode = detected if detected else config["api"].get("trade_mode", "real")

        # exe 감지 모드이면 config에도 저장 (일치 유지)
        if detected and config["api"].get("trade_mode") != detected:
            config["api"]["trade_mode"] = detected
            save_config(config)

        mode_label = "모의투자" if self.trade_mode == "mock" else "실전투자"
        self.setWindowTitle(f"주식 자동매매 시스템 v1.1  [{mode_label}]")

        self.api = LSApi(mode=self.trade_mode)
        self.api_connected = False
        self.is_trading = False
        self.holdings_data  = []   # 보유종목 원본 데이터
        self.ai_signals     = []   # AI 신호 캐시
        self.ai_thread      = None # AI 엔진 스레드
        self._fetch_thread  = None # 데이터 조회 스레드 (API 블로킹 방지)

        self._api_init_thread = None   # API 초기 연결 스레드

        self._build_ui()

        # 타이머들 (창 표시 후 즉시 시작)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(30000)

        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self._auto_reconnect)
        self.reconnect_timer.start(60000)

        self.ai_timer = QTimer()
        self.ai_timer.timeout.connect(self._update_ai_signals)
        self.ai_timer.start(10000)

        # 창이 완전히 뜬 뒤 API 연결 시작 (100ms 후)
        QTimer.singleShot(100, self._init_api)

    def _auto_reconnect(self):
        """60초마다 미연결 상태면 자동 재연결 시도"""
        if not self.api_connected:
            now = datetime.now().strftime("%H:%M:%S")
            self.log_area.append(f"[{now}] 🔄 API 재연결 시도...")
            self._init_api()
    def _init_api(self):
        """API 연결을 백그라운드 스레드로 시작 (UI 블로킹 없음)"""
        now = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{now}] API 연결 중...")
        self.ls_badge.setText("LS ⏳")

        self._api_init_thread = ApiInitThread(self.api)
        self._api_init_thread.connected.connect(self._on_api_connected)
        self._api_init_thread.data_ready.connect(self._on_fetch_done)
        self._api_init_thread.start()

    def _on_api_connected(self, ok: bool, error: str):
        """API 연결 결과 수신 (메인 스레드)"""
        now = datetime.now().strftime("%H:%M:%S")
        if ok:
            self.api_connected = True
            self.ls_badge.setText("LS ✅")
            self.ls_badge.setStyleSheet(
                "background-color: #00b89422; color: #00b894; "
                "border: 1px solid #00b894; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
            )
            self.log_area.append(f"[{now}] LS API 연결 완료")
        else:
            self.api_connected = False
            self.ls_badge.setText("LS ❌")
            self.ls_badge.setStyleSheet(
                "background-color: #d6303122; color: #d63031; "
                "border: 1px solid #d63031; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
            )
            self.log_area.append(f"[{now}] ❌ LS API 연결 실패 - {error}")

    def refresh_data(self):
        """백그라운드 스레드로 API 데이터 조회 시작 (UI 블로킹 없음)"""
        if not self.api_connected:
            return
        # 이미 조회 중이면 중복 실행 방지
        if self._fetch_thread and self._fetch_thread.isRunning():
            return
        self._fetch_thread = DataFetchThread(self.api)
        self._fetch_thread.done.connect(self._on_fetch_done)
        self._fetch_thread.start()

    def _on_fetch_done(self, result: dict):
        """백그라운드 조회 완료 → UI 업데이트 (메인 스레드에서 안전하게 실행)"""
        now = datetime.now().strftime("%H:%M:%S")

        # 보유종목 + 계좌요약
        holdings = result.get("holdings", [])
        summary  = result.get("summary", {})
        if holdings is not None:
            self.holdings_data = holdings
            self._update_holdings_table(holdings)
            self._write_holdings_cache(holdings)   # AI 엔진에 보유종목 전달
        if summary:
            self._update_summary(summary)

        # 오류 로그
        if "error_holdings" in result:
            self.log_area.append(f"[{now}] ❌ 잔고 조회 실패: {result['error_holdings']}")

        # 시장지수 (KOSPI/KOSDAQ)
        self._apply_market_index("KOSPI",  result.get("kospi"))
        self._apply_market_index("KOSDAQ", result.get("kosdaq"))

        # 업종지수 차트
        sectors = result.get("sectors", [])
        if sectors:
            self._apply_sector_table(sectors)

        # 상승테마
        themes = result.get("themes", [])
        if themes:
            self._update_theme_section(themes)

        self.time_label.setText(f"⏱ {now} 업데이트")

# ── AI 신호 파일 읽기 (10초마다) ──
    def _update_ai_signals(self):
        """ai_signals.json 읽어서 스캔종목/추천종목 테이블 갱신"""
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "ai_signals.json")

        if not os.path.exists(path):
            return
        try:
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
        all_scanned  = sorted(signals, key=lambda x: x.get("score", 0), reverse=True)

        # 상태 레이블 갱신
        if hasattr(self, "ai_status_label"):
            self.ai_status_label.setText(
                f"🤖 AI엔진: {timestamp} | {scan_count}종목 스캔 | 매수신호 {len(buy_signals)}개"
            )
            self.ai_status_label.setStyleSheet(
                "color: #00b894; font-size: 11px; padding: 2px 4px;"
                if buy_signals else "color: #888; font-size: 11px; padding: 2px 4px;"
            )

        def _item(text, color=None, align=Qt.AlignCenter):
            it = QTableWidgetItem(str(text))
            it.setTextAlignment(align)
            if color:
                it.setForeground(QColor(color))
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            return it

        # ── 왼쪽: AI 스캔종목 (전체, 점수순) ──
        if hasattr(self, "scan_list"):
            self.scan_list.setRowCount(0)
            self._scan_codes = {}
            for row_idx, sig in enumerate(all_scanned[:50]):   # 최대 50개
                self.scan_list.insertRow(row_idx)
                sig_type  = sig.get("signal_type", "")
                score     = sig.get("score", 0)
                cur_price = sig.get("current_price", 0)

                # 상태 색상: BUY=초록, HOLD=노랑, WATCH=회색
                state_color = {"BUY": "#00b894", "HOLD": "#fdcb6e"}.get(sig_type, "#888")
                score_color = "#00b894" if sig_type == "BUY" else "#fdcb6e" if sig_type == "HOLD" else "#aaa"

                self.scan_list.setItem(row_idx, 0, _item(sig.get("stock_name", ""), align=Qt.AlignLeft | Qt.AlignVCenter))
                self.scan_list.setItem(row_idx, 1, _item(f"{score:.1f}", score_color))
                self.scan_list.setItem(row_idx, 2, _item(sig_type, state_color))
                self.scan_list.setItem(row_idx, 3, _item(f"{cur_price:,}" if cur_price else "-"))
                self._scan_codes[row_idx] = sig.get("stock_code", "")

        # ── 오른쪽: AI 추천종목 (BUY만, 점수순) ──
        if hasattr(self, "rec_list"):
            self.rec_list.setRowCount(0)
            for rank, sig in enumerate(buy_signals[:20], 1):
                row = self.rec_list.rowCount()
                self.rec_list.insertRow(row)

                score      = sig.get("score", 0)
                confidence = sig.get("confidence", "")
                cur_price  = sig.get("current_price", 0)
                stop_loss  = sig.get("stop_loss", 0)
                target     = sig.get("target_price", 0)
                conf_color = {"HIGH": "#00b894", "MEDIUM": "#fdcb6e", "LOW": "#888"}.get(confidence, "#888")

                self.rec_list.setItem(row, 0, _item(f"{rank}"))
                self.rec_list.setItem(row, 1, _item(sig.get("stock_name", ""), align=Qt.AlignLeft | Qt.AlignVCenter))
                self.rec_list.setItem(row, 2, _item(f"{score:.1f}점", "#ff6b6b"))
                self.rec_list.setItem(row, 3, _item(confidence, conf_color))
                self.rec_list.setItem(row, 4, _item(f"{cur_price:,}" if cur_price else "-"))
                self.rec_list.setItem(row, 5, _item(f"{stop_loss:,}" if stop_loss else "-", "#ff6b6b"))
                self.rec_list.setItem(row, 6, _item(f"{target:,}" if target else "-", "#74b9ff"))

        self.ai_signals = signals

        # 보유종목 AI판단 컬럼 즉시 갱신 (신호 업데이트 시 항상 반영)
        self._refresh_holdings_ai_column()

    def _refresh_holdings_ai_column(self):
        """보유종목 테이블의 AI판단 컬럼만 갱신 (신호 변경 시 호출)"""
        if not hasattr(self, 'holdings_table'):
            return
        # 종목코드 → 신호 매핑 (날짜 무관, 가장 최근 데이터 기준)
        sig_map = {s.get("stock_code"): s for s in self.ai_signals
                   if s.get("signal_type") in ("SELL", "HOLD")}

        for row in range(self.holdings_table.rowCount()):
            if row >= len(self.holdings_data):
                break
            code = self.holdings_data[row].get("raw_code", "")
            sig  = sig_map.get(code)
            if sig:
                score = sig.get("score", 0)
                if sig["signal_type"] == "SELL":
                    ai_text  = f"매도 {score:.0f}점"
                    ai_color = "#ff6b6b"
                else:
                    ai_text  = f"보유 {score:.0f}점"
                    ai_color = "#fdcb6e"
            else:
                ai_text, ai_color = "-", "#636e72"
            item = self.holdings_table.item(row, 8)
            if item is None:
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignCenter)
                self.holdings_table.setItem(row, 8, item)
            item.setText(ai_text)
            item.setForeground(QColor(ai_color))

    def _apply_market_index(self, name: str, data):
        """KOSPI/KOSDAQ 지수 UI 적용 (메인 스레드)"""
        if not data or name not in self.market_labels:
            return
        try:
            row = data[0] if isinstance(data, list) else data
            price = float(str(row.get("pricejisu", 0)).replace(",", ""))
            try:
                chg_val = float(str(row.get("change", 0)).replace(",", ""))
            except:
                chg_val = 0.0
            sign_cd = str(row.get("sign", "3"))
            prev = price - chg_val
            if prev > 0:
                rt = chg_val / prev * 100
                rt = -abs(rt) if sign_cd == "2" else abs(rt)
            else:
                rt = 0.0
            val_lbl, chg_lbl = self.market_labels[name]
            val_lbl.setText(f"{price:,.2f}")
            sign_str = "+" if rt >= 0 else ""
            color = "#ff6b6b" if rt >= 0 else "#74b9ff"
            chg_lbl.setText(f"{sign_str}{rt:.2f}%")
            chg_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
        except Exception as e:
            print(f"[시장지수] {name} 파싱 실패: {e}")

    def _apply_sector_table(self, sectors: list):
        """업종지수 차트형 카드 UI 적용 (메인 스레드)"""
        if not hasattr(self, 'sector_chart_layout') or not sectors:
            return

        # 기존 카드 제거 (stretch 남김)
        while self.sector_chart_layout.count() > 1:
            item = self.sector_chart_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 등락률 파싱 후 내림차순 정렬 (상승 높은 것부터)
        def parse_rate(s):
            try:
                return float(s["change"].replace("%", "").replace("+", ""))
            except:
                return 0.0

        sectors = sorted(sectors, key=parse_rate, reverse=True)

        rates = [abs(parse_rate(s)) for s in sectors]
        max_rate = max(rates) if rates else 1.0

        for s, rate_abs in zip(sectors, rates):
            chg = s["change"]
            idx = s["index"]
            name = s["name"]
            is_up = chg.startswith("+")
            bar_color  = "#ff6b6b" if is_up else "#74b9ff"
            text_color = "#ff6b6b" if is_up else "#74b9ff"

            card = QFrame()
            card.setStyleSheet("background-color: #16213e; border-radius: 3px;")
            card.setFixedHeight(36)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(6, 2, 6, 2)
            cl.setSpacing(4)

            # 업종명
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("color: #c0c0c0; font-size: 11px;")
            name_lbl.setFixedWidth(58)

            # 지수값
            idx_lbl = QLabel(idx)
            idx_lbl.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: bold;")
            idx_lbl.setFixedWidth(58)
            idx_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # 등락률 바 (미니 차트)
            bar_widget = QWidget()
            bar_widget.setFixedHeight(18)
            bar_layout = QHBoxLayout(bar_widget)
            bar_layout.setContentsMargins(0, 0, 0, 0)
            bar_layout.setSpacing(0)

            bar_fill = QFrame()
            fill_w = max(4, int(80 * rate_abs / max(max_rate, 0.01)))
            bar_fill.setFixedWidth(fill_w)
            bar_fill.setFixedHeight(14)
            bar_fill.setStyleSheet(f"background-color: {bar_color}; border-radius: 2px;")
            bar_layout.addWidget(bar_fill)
            bar_layout.addStretch()

            # 등락률 텍스트
            chg_lbl = QLabel(chg)
            chg_lbl.setStyleSheet(f"color: {text_color}; font-size: 11px; font-weight: bold;")
            chg_lbl.setFixedWidth(52)
            chg_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            cl.addWidget(name_lbl)
            cl.addWidget(idx_lbl)
            cl.addWidget(bar_widget, stretch=1)
            cl.addWidget(chg_lbl)

            self.sector_chart_layout.insertWidget(
                self.sector_chart_layout.count() - 1, card)
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

        # ── 메인 2단 레이아웃 ──
        content = QHBoxLayout()
        content.setSpacing(8)
        content.addLayout(self._build_center_column(), stretch=1)
        content.addWidget(self._build_right_column(), stretch=0)
        main_layout.addLayout(content)

    # ── 타이틀바 (계좌요약 포함) ──
    def _build_titlebar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #0f3460; border-radius: 6px;")
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

        # 계좌 요약 인라인 (실시간 업데이트용 참조 저장)
        self.summary_labels = {}
        summaries = [
            ("추정자산", "연결중...", "#ffffff"),
            ("실현손익", "-",         "#00b894"),
            ("손익률",   "-",         "#00b894"),
            ("보유종목", "-",         "#a0c4ff"),
            ("매매상태", "대기중",     "#fdcb6e"),
        ]
        for label, value, color in summaries:
            col = QVBoxLayout()
            col.setSpacing(1)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #888; font-size: 9px;")
            val = QLabel(value)
            val.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            self.summary_labels[label] = val
            col.addWidget(lbl)
            col.addWidget(val)
            layout.addLayout(col)

            sep = QFrame(); sep.setFrameShape(QFrame.VLine)
            sep.setStyleSheet("color: #1e4a7a;")
            layout.addWidget(sep)

        layout.addStretch()

        # API 배지 (연결 상태에 따라 업데이트)
        self.ls_badge = QLabel("LS ⏳")
        self.ls_badge.setStyleSheet(
            "background-color: #fdcb6e22; color: #fdcb6e; "
            "border: 1px solid #fdcb6e; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
        )
        layout.addWidget(self.ls_badge)

        # 버튼들
        self.btn_settings = QPushButton("⚙️ 설정")
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(self.btn_settings)

        # 모드 버튼: exe 이름으로 감지된 경우 해당 버튼만 표시
        detected_mode = _detect_trade_mode()
        btn_style_mock = (
            "QPushButton { padding: 2px 8px; font-size: 11px; "
            "background-color: #0984e3; color: #fff; border: 1px solid #0984e3; border-radius: 3px; }"
        )
        btn_style_real = (
            "QPushButton { padding: 2px 8px; font-size: 11px; "
            "background-color: #d63031; color: #fff; border: 1px solid #d63031; border-radius: 3px; }"
        )
        btn_style_inactive = "padding: 2px 8px; font-size: 11px;"

        self.btn_mock = QPushButton("모의")
        self.btn_mock.setCheckable(True)
        self.btn_mock.setChecked(self.trade_mode == "mock")
        self.btn_mock.setStyleSheet(btn_style_mock if self.trade_mode == "mock" else btn_style_inactive)
        self.btn_mock.clicked.connect(lambda: self.switch_trade_mode("mock"))

        self.btn_real = QPushButton("실전")
        self.btn_real.setCheckable(True)
        self.btn_real.setChecked(self.trade_mode == "real")
        self.btn_real.setStyleSheet(btn_style_real if self.trade_mode == "real" else btn_style_inactive)
        self.btn_real.clicked.connect(lambda: self.switch_trade_mode("real"))

        if detected_mode == "mock":
            # 모의 exe: 모의 버튼만 표시 (라벨 역할)
            layout.addWidget(self.btn_mock)
        elif detected_mode == "real":
            # 실전 exe: 실전 버튼만 표시 (라벨 역할)
            layout.addWidget(self.btn_real)
        else:
            # 개발 환경: 둘 다 표시 (전환 가능)
            layout.addWidget(self.btn_mock)
            layout.addWidget(self.btn_real)

        self.btn_ai_engine = AIToggleSwitch()
        self.btn_ai_engine.toggled.connect(self._on_ai_toggle)
        layout.addWidget(self.btn_ai_engine)

        self.btn_start = QPushButton("🚀 자동매매 시작")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self.toggle_trading)
        layout.addWidget(self.btn_start)

        return bar

    # ── 시장현황 바 ──
    def _build_market_bar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #0d1b2a; border-radius: 6px; border: 1px solid #0f3460;")
        bar.setFixedHeight(36)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(0)

        market_data = [
            ("KOSPI",    "2,634.82", "+0.43%",  "#ff6b6b"),
            ("KOSDAQ",   "856.14",   "+0.87%",  "#ff6b6b"),
            ("환율(USD)", "1,328.50", "-0.12%",  "#74b9ff"),
            ("외국인",    "+2,847억", "순매수",   "#ff6b6b"),
            ("기관",      "+1,203억", "순매수",   "#ff6b6b"),
            ("거래대금",  "12.4조",   "KOSPI",   "#a0c4ff"),
        ]

        for i, (label, value, change, color) in enumerate(market_data):
            item_layout = QHBoxLayout()
            item_layout.setSpacing(4)

            lbl = QLabel(label)
            lbl.setStyleSheet("color: #888; font-size: 11px;")

            val = QLabel(value)
            val.setStyleSheet(f"color: #ffffff; font-size: 12px; font-weight: bold;")

            chg = QLabel(change)
            chg.setStyleSheet(f"color: {color}; font-size: 11px;")

            item_layout.addWidget(lbl)
            item_layout.addWidget(val)
            item_layout.addWidget(chg)
            layout.addLayout(item_layout)

            # 구분선
            if i < len(market_data) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.VLine)
                sep.setStyleSheet("color: #1e3a5f; margin: 4px 12px;")
                layout.addWidget(sep)

        layout.addStretch()

        # 업데이트 시간
        self.time_label = QLabel("⏱ 연결중...")
        self.time_label.setStyleSheet("color: #555; font-size: 10px;")
        layout.addWidget(self.time_label)

        return bar

    # ── 계좌 요약 바 ──
    def _build_summary_bar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #16213e; border-radius: 6px;")
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(20)

        summaries = [
            ("추정자산", "52,384,500 원", "#ffffff"),
            ("실현손익", "+384,500 원", "#00b894"),
            ("손익률", "+0.74%", "#00b894"),
            ("검색결과", "23 종목", "#a0c4ff"),
            ("자동매매", "대기중", "#fdcb6e"),
        ]
        for label, value, color in summaries:
            box = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #888; font-size: 11px;")
            val = QLabel(value)
            val.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
            box.addWidget(lbl)
            box.addWidget(val)
            layout.addLayout(box)
            # 구분선
            if label != "자동매매":
                sep = QFrame()
                sep.setFrameShape(QFrame.VLine)
                sep.setStyleSheet("color: #0f3460;")
                layout.addWidget(sep)

        layout.addStretch()
        return bar

    # ── 중앙 컬럼 ──
    def _build_center_column(self):
        # 상단: 보유종목 + 업종/외국인/기관
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.addWidget(self._build_holdings_table())
        top_splitter.addWidget(self._build_market_panel())
        top_splitter.setSizes([620, 320])
        top_splitter.setStyleSheet("QSplitter::handle { background-color: #0f3460; width: 4px; }")

        # 전체: 상단 + 하단 2분할
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.addWidget(top_splitter)
        v_splitter.addWidget(self._build_bottom_panels())
        v_splitter.setSizes([300, 380])
        v_splitter.setStyleSheet("QSplitter::handle { background-color: #0f3460; height: 4px; }")

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(v_splitter)
        return layout

    # ── 업종지수 / 외국인·기관 패널 ──
    def _build_market_panel(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # 업종지수
        grp_sector = QGroupBox("📊 업종지수")
        sector_layout = QVBoxLayout(grp_sector)
        sector_table = QTableWidget()
        sector_table.setColumnCount(5)
        sector_table.setHorizontalHeaderLabels(["업종명", "지수", "등락률", "외국인", "기관"])
        sector_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sector_table.setEditTriggers(QTableWidget.NoEditTriggers)
        sector_table.setAlternatingRowColors(True)
        sector_table.setStyleSheet("QTableWidget { alternate-background-color: #1a2744; }")
        # 업종명 / 지수 / 등락률 / 외국인동향 / 기관동향
        sectors = [
            ("반도체",  "3,842.15", "+1.23%", "매수", "매수"),
            ("2차전지", "2,156.88", "+2.41%", "매수", "매수"),
            ("바이오",  "8,934.20", "-0.87%", "매도", "중립"),
            ("자동차",  "1,623.44", "+0.54%", "매수", "매도"),
            ("금융",    "982.33",   "+0.12%", "중립", "매수"),
            ("IT",      "4,211.67", "+0.98%", "매수", "중립"),
        ]
        sector_table.setRowCount(len(sectors))
        for r, (name, idx, chg, foreign, inst) in enumerate(sectors):
            for c, val in enumerate([name, idx, chg, foreign, inst]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if c == 2:  # 등락률
                    item.setForeground(QColor("#ff6b6b") if val.startswith("+") else QColor("#74b9ff"))
                if c in [3, 4]:  # 외국인/기관
                    if val == "매수":
                        item.setForeground(QColor("#ff6b6b"))
                    elif val == "매도":
                        item.setForeground(QColor("#74b9ff"))
                    else:
                        item.setForeground(QColor("#888888"))
                sector_table.setItem(r, c, item)
        sector_layout.addWidget(sector_table)

        layout.addWidget(grp_sector)
        return widget

    # ── 보유종목 테이블 ──
    def _build_holdings_table(self):
        grp = QGroupBox("💼 보유종목")
        layout = QVBoxLayout(grp)

        self.holdings_table = QTableWidget()
        self.holdings_table.setColumnCount(9)
        self.holdings_table.setHorizontalHeaderLabels([
            "종목명", "매수가", "현재가", "등락률", "수익률", "보유수량", "평가금액", "손익금액", "AI판단"
        ])
        self.holdings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.holdings_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Fixed)
        self.holdings_table.setColumnWidth(8, 90)
        self.holdings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.holdings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.holdings_table.setAlternatingRowColors(True)
        self.holdings_table.setStyleSheet(
            "QTableWidget { alternate-background-color: #1a2744; }"
        )
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
                f"background-color: #16213e; border: 1px solid {color}44; "
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

    # ── 하단 2분할 패널 ──
    def _build_bottom_panels(self):
        splitter = QSplitter(Qt.Horizontal)

        # AI 스캔종목 리스트 (스크리닝 통과한 전체 종목)
        left = QGroupBox("🔍 AI 스캔종목")
        left_layout = QVBoxLayout(left)
        self.scan_list = QTableWidget()
        self.scan_list.setColumnCount(4)
        self.scan_list.setHorizontalHeaderLabels(["종목명", "AI점수", "상태", "현재가"])
        self.scan_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.scan_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.scan_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.scan_list.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.scan_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.scan_list.setRowCount(0)

        # 더블클릭 시 HTS 종목 연동
        self.scan_list.cellDoubleClicked.connect(self._on_scan_click)

        btn_row = QHBoxLayout()
        btn_chart = QPushButton("📊 차트▶")
        btn_chart.clicked.connect(self._open_chart_from_scan)
        btn_buy   = QPushButton("💸 수동매수")
        btn_buy.setObjectName("btn_start")
        btn_buy.clicked.connect(self._manual_buy_from_scan)
        btn_row.addWidget(btn_chart)
        btn_row.addWidget(btn_buy)
        left_layout.addWidget(self.scan_list)
        left_layout.addLayout(btn_row)

        # AI 추천종목 리스트
        right = QGroupBox("🤖 AI 추천종목")
        right_layout = QVBoxLayout(right)
        self.rec_list = QTableWidget()
        self.rec_list.setColumnCount(7)
        self.rec_list.setHorizontalHeaderLabels(["순위", "종목명", "AI점수", "신뢰도", "현재가", "손절가", "목표가"])
        self.rec_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.rec_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.rec_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.rec_list.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.rec_list.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.rec_list.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.rec_list.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.rec_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rec_list.setRowCount(0)
        # AI 상태 레이블
        self.ai_status_label = QLabel("🤖 AI엔진: 신호 없음")
        self.ai_status_label.setStyleSheet("color: #888; font-size: 11px; padding: 2px 4px;")
        right_layout.addWidget(self.ai_status_label)

        # 하단 자동 / 수동 버튼
        btn_row2 = QHBoxLayout()

        self.btn_auto_mode = QPushButton("🤖 자동")
        self.btn_auto_mode.setCheckable(True)
        self.btn_auto_mode.setStyleSheet(
            "QPushButton { background-color: #2d3436; color: #aaa; border: 2px solid #636e72; "
            "border-radius: 5px; font-size: 13px; font-weight: bold; padding: 6px; }"
            "QPushButton:checked { background-color: #00b894; color: #fff; border: 2px solid #00b894; }"
        )
        self.btn_auto_mode.clicked.connect(self.toggle_auto_mode)

        self.btn_manual_mode = QPushButton("✋ 수동")
        self.btn_manual_mode.setCheckable(True)
        self.btn_manual_mode.setChecked(True)
        self.btn_manual_mode.setStyleSheet(
            "QPushButton { background-color: #2d3436; color: #aaa; border: 2px solid #636e72; "
            "border-radius: 5px; font-size: 13px; font-weight: bold; padding: 6px; }"
            "QPushButton:checked { background-color: #0984e3; color: #fff; border: 2px solid #0984e3; }"
        )
        self.btn_manual_mode.clicked.connect(self.toggle_manual_mode)

        btn_row2.addWidget(self.btn_auto_mode)
        btn_row2.addWidget(self.btn_manual_mode)
        right_layout.addWidget(self.rec_list)
        right_layout.addLayout(btn_row2)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([400, 400])
        return splitter

    # ── 우측 컬럼 ──
    def _build_right_column(self):
        widget = QWidget()
        widget.setFixedWidth(300)
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # 상승테마
        theme_grp = QGroupBox("🔥 상승테마")
        self.theme_layout = QVBoxLayout(theme_grp)
        self.theme_layout.setSpacing(4)
        theme_layout = self.theme_layout

        self.theme_stocks = {
            "2차전지": [("LG에너지솔루션","385,500","+4.21%"),("삼성SDI","420,000","+3.87%"),("SK이노베이션","125,500","+2.94%"),("에코프로","182,000","+5.12%"),("포스코퓨처엠","320,000","+3.45%")],
            "반도체":  [("삼성전자","73,400","+2.34%"),("SK하이닉스","128,500","+1.87%"),("DB하이텍","52,300","+3.21%"),("한미반도체","68,900","+4.56%"),("리노공업","215,000","+2.78%")],
            "AI·로봇": [("레인보우로보틱스","82,400","+5.34%"),("두산로보틱스","42,150","+3.12%"),("NAVER","168,000","+0.96%"),("카카오","42,150","+1.23%"),("솔트룩스","28,500","+4.87%")],
            "바이오":  [("삼성바이오로직스","812,000","+1.54%"),("셀트리온","168,500","+2.43%"),("유한양행","58,200","+1.87%"),("한미약품","320,000","+0.98%"),("녹십자","132,000","+1.23%")],
            "방산":    [("한화에어로스페이스","185,000","+3.21%"),("LIG넥스원","142,000","+2.87%"),("현대로템","52,400","+4.12%"),("한국항공우주","62,300","+1.98%")],
            "자동차":  [("현대차","185,000","+0.87%"),("기아","98,500","+1.23%"),("현대모비스","245,000","+0.54%"),("HL만도","42,300","+0.98%")],
            "게임":    [("엔씨소프트","185,000","-1.23%"),("넥슨게임즈","12,450","-0.87%"),("크래프톤","215,000","-0.34%"),("넷마블","42,150","-0.56%")],
        }

        themes = [
            ("2차전지",   "+4.21%", "관련 23종목", "#ff6b6b"),
            ("반도체",    "+2.87%", "관련 18종목", "#ff6b6b"),
            ("AI·로봇",   "+2.34%", "관련 15종목", "#ff6b6b"),
            ("바이오",    "+1.92%", "관련 31종목", "#ff6b6b"),
            ("방산",      "+1.54%", "관련 9종목",  "#fdcb6e"),
            ("자동차",    "+0.87%", "관련 12종목", "#fdcb6e"),
            ("게임",      "-0.43%", "관련 14종목", "#74b9ff"),
        ]
        for theme, chg, stocks, color in themes:
            card = QFrame()
            card.setStyleSheet(
                f"background-color: #16213e; border-left: 3px solid {color}; "
                f"border-radius: 4px;"
            )
            card.setCursor(Qt.PointingHandCursor)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(8, 5, 8, 5)

            name_lbl = QLabel(theme)
            name_lbl.setStyleSheet("color: #fff; font-size: 12px; font-weight: bold;")

            chg_lbl = QLabel(chg)
            chg_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

            stocks_btn = QPushButton(stocks)
            stocks_btn.setStyleSheet(
                "background-color: #0f3460; color: #a0c4ff; border: none; "
                "border-radius: 3px; font-size: 10px; padding: 2px 6px;"
                "text-decoration: underline; cursor: pointer;"
            )
            stocks_btn.clicked.connect(lambda _, t=theme: self.show_theme_stocks(t))

            cl.addWidget(name_lbl)
            cl.addStretch()
            cl.addWidget(chg_lbl)
            cl.addWidget(stocks_btn)
            theme_layout.addWidget(card)

        layout.addWidget(theme_grp)

        # 관련종목 패널 (테마 클릭 시 표시)
        self.related_grp = QGroupBox("📋 관련종목")
        related_layout = QVBoxLayout(self.related_grp)
        self.related_table = QTableWidget()
        self.related_table.setColumnCount(3)
        self.related_table.setHorizontalHeaderLabels(["종목명", "현재가", "등락률"])
        self.related_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.related_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.related_table.setAlternatingRowColors(True)
        self.related_table.setStyleSheet("QTableWidget { alternate-background-color: #1a2744; }")
        self.related_table.setFixedHeight(160)
        # 더블클릭 시 HTS 종목 연동
        self.related_table.cellDoubleClicked.connect(self._on_related_click)

        hint = QLabel("← 테마를 클릭하면 관련종목이 표시됩니다")
        hint.setStyleSheet("color: #555; font-size: 10px;")
        hint.setAlignment(Qt.AlignCenter)
        related_layout.addWidget(hint)
        related_layout.addWidget(self.related_table)
        self.related_table.hide()
        layout.addWidget(self.related_grp)

        # 매매 로그
        log_grp = QGroupBox("📝 매매 로그")
        log_layout = QVBoxLayout(log_grp)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(
            "background-color: #0a0a1a; color: #00ff88; font-family: Consolas; font-size: 11px;"
        )
        # 로그는 API 연결 후 자동으로 기록됨
        log_layout.addWidget(self.log_area)
        layout.addWidget(log_grp)

        return widget

    # ── 보유종목 테이블 업데이트 ──
    def _update_holdings_table(self, holdings):
        """API에서 받은 보유종목 데이터로 테이블 갱신"""
        self.holdings_table.setRowCount(len(holdings))
        for row, h in enumerate(holdings):
            cols = [
                h["name"], h["buy_price"], h["cur_price"],
                h["day_change"], h["pnl_rate"], h["qty"],
                h["eval_amt"], h["pnl_amt"]
            ]
            for col, val in enumerate(cols):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                # 등락률/수익률/손익금액 색상
                if col in [3, 4, 7]:
                    if val.startswith("+"):
                        item.setForeground(QColor("#ff6b6b"))
                    elif val.startswith("-"):
                        item.setForeground(QColor("#74b9ff"))
                self.holdings_table.setItem(row, col, item)

            # AI 판단 (SELL/HOLD + 점수, 날짜 무관 최근 데이터 기준)
            code    = h.get("raw_code", "")
            sig_map = {s.get("stock_code"): s for s in self.ai_signals
                       if s.get("signal_type") in ("SELL", "HOLD")}
            sig     = sig_map.get(code)
            if sig:
                score = sig.get("score", 0)
                if sig["signal_type"] == "SELL":
                    ai_text, ai_color = f"매도 {score:.0f}점", "#ff6b6b"
                else:
                    ai_text, ai_color = f"보유 {score:.0f}점", "#fdcb6e"
            else:
                ai_text, ai_color = "-", "#636e72"
            ai_item = QTableWidgetItem(ai_text)
            ai_item.setTextAlignment(Qt.AlignCenter)
            ai_item.setForeground(QColor(ai_color))
            ai_item.setFlags(ai_item.flags() & ~Qt.ItemIsEditable)
            self.holdings_table.setItem(row, 8, ai_item)

    def _write_holdings_cache(self, holdings):
        """AI 엔진이 보유종목 SELL 판단에 쓸 holdings_cache.json 저장"""
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(os.path.dirname(sys.executable))
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "holdings_cache.json")
        tmp  = path + ".tmp"
        try:
            payload = [
                {
                    "code"     : h.get("raw_code", ""),
                    "name"     : h.get("name", ""),
                    "buy_price": h.get("raw_buy_price", 0),
                    "qty"      : h.get("raw_qty", 0),
                }
                for h in holdings if h.get("raw_code")
            ]
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            os.replace(tmp, path)
        except Exception:
            pass

    # ── 계좌 요약 업데이트 ──
    def _update_summary(self, summary):
        """타이틀바 계좌요약 라벨 갱신"""
        if "추정자산" in self.summary_labels:
            self.summary_labels["추정자산"].setText(summary.get("total_eval", "-"))
        if "실현손익" in self.summary_labels:
            val = summary.get("total_pnl", "-")
            color = "#ff6b6b" if val.startswith("+") else "#74b9ff" if val.startswith("-") else "#e0e0e0"
            self.summary_labels["실현손익"].setText(val)
            self.summary_labels["실현손익"].setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        if "손익률" in self.summary_labels:
            val = summary.get("total_pnl_rate", "-")
            color = "#ff6b6b" if val.startswith("+") else "#74b9ff" if val.startswith("-") else "#e0e0e0"
            self.summary_labels["손익률"].setText(val)
            self.summary_labels["손익률"].setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        if "보유종목" in self.summary_labels:
            self.summary_labels["보유종목"].setText(summary.get("stock_count", "-"))
        if "매매상태" in self.summary_labels:
            status = "자동매매중" if self.is_trading else "대기중"
            color = "#00b894" if self.is_trading else "#fdcb6e"
            self.summary_labels["매매상태"].setText(status)
            self.summary_labels["매매상태"].setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

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
            self.log_area.append(f"[{now}] ⏸ 모드 전환으로 자동매매 정지")
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
        # API 재연결
        mode_name = "모의투자" if mode == "mock" else "실전투자"
        self.log_area.append(f"[{now}] 투자모드: {mode_name}")
        self.api = LSApi(mode=mode)
        self.api_connected = False
        self._init_api()

    # ── 설정 창 열기 ──
    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            # 설정 저장 후 API 키가 변경됐을 수 있으므로 재연결
            self.api = LSApi(mode=self.trade_mode)
            self.api_connected = False
            self._init_api()

    # ── 자동/수동 모드 전환 ──
    def toggle_auto_mode(self):
        self.btn_auto_mode.setChecked(True)
        self.btn_manual_mode.setChecked(False)
        # 1위 종목 이름 가져오기
        top_stock = self.rec_list.item(0, 1).text() if self.rec_list.rowCount() > 0 else "없음"
        self.log_area.append(f"[모드] 🤖 자동 모드 활성 → 1위 종목 [{top_stock}] 자동매수 대기중")

    def toggle_manual_mode(self):
        self.btn_manual_mode.setChecked(True)
        self.btn_auto_mode.setChecked(False)
        self.log_area.append("[모드] ✋ 수동 모드 활성 → 직접 종목을 선택하세요")

    def set_auto_trade(self, name, action):
        self.log_area.append(f"[자동{action}] {name} → {action} 신호 등록됨")

    def set_manual_trade(self, name):
        self.log_area.append(f"[수동] {name} → 수동매매 모드")

    def sell_stock(self, name, code=None, qty=None):
        now = datetime.now().strftime("%H:%M:%S")
        if not self.api_connected:
            self.log_area.append(f"[{now}] ❌ API 미연결 - 매도 불가")
            return
        if not code or not qty:
            self.log_area.append(f"[{now}] ❌ {name} 종목코드/수량 정보 없음")
            return
        self.log_area.append(f"[{now}] 🔴 매도 주문 요청: {name} ({code}) {qty}주 시장가")
        result = self.api.sell_order(code, qty, price=0)
        if result:
            self.log_area.append(f"[{now}] 🔴 매도 체결: {name} {qty}주")
            self.refresh_data()  # 잔고 갱신
        else:
            self.log_area.append(f"[{now}] ❌ 매도 실패: {name}")

    def _update_theme_section(self, themes: list):
        """API에서 받은 테마 데이터로 카드 갱신 (메인 스레드)"""
        if not hasattr(self, 'theme_layout') or not themes:
            return
        # 기존 카드 제거
        while self.theme_layout.count():
            item = self.theme_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for t in themes[:10]:
            name  = t.get("name", "")
            diff  = t.get("diff", 0.0)
            diff_str = t.get("diff_str", f"{diff:+.2f}%")
            color = "#ff6b6b" if diff >= 0 else "#74b9ff"

            card = QFrame()
            card.setStyleSheet(
                f"background-color: #16213e; border-left: 3px solid {color}; border-radius: 4px;"
            )
            card.setCursor(Qt.PointingHandCursor)
            cl = QHBoxLayout(card)
            cl.setContentsMargins(8, 5, 8, 5)

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("color: #fff; font-size: 12px; font-weight: bold;")
            chg_lbl = QLabel(diff_str)
            chg_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")

            cl.addWidget(name_lbl)
            cl.addStretch()
            cl.addWidget(chg_lbl)
            self.theme_layout.addWidget(card)

    def show_theme_stocks(self, theme):
        stocks = self.theme_stocks.get(theme, [])
        self.related_grp.setTitle(f"📋 {theme} 관련종목")
        self.related_table.show()
        self.related_table.setRowCount(len(stocks))
        for r, (name, price, chg) in enumerate(stocks):
            for c, val in enumerate([name, price, chg]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if c == 2:
                    item.setForeground(QColor("#ff6b6b") if val.startswith("+") else QColor("#74b9ff"))
                self.related_table.setItem(r, c, item)

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
                time.sleep(0.05)

            # 창 활성화
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            time.sleep(0.1)
            user32.BringWindowToTop(hwnd)
            time.sleep(0.1)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.1)

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
            self.log_area.append(f"[{now}] ⚠️ {stock_name} → 종목코드 없음")
            return

        # 클립보드에도 복사 (백업)
        clipboard = QApplication.clipboard()
        clipboard.setText(code)

        hts_hwnd = self._find_hts_window()
        if not hts_hwnd:
            self.log_area.append(f"[{now}] ⚠️ HTS(LS증권 투혼) 미실행 → {stock_name}({code}) 클립보드 복사됨")
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

            self.log_area.append(f"[{now}] ✅ HTS 연동: {stock_name} ({code})")
        except Exception as e:
            self.log_area.append(f"[{now}] ⚠️ HTS 연동 오류: {e} → 코드 클립보드 복사됨")

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
            self.log_area.append(f"[{now}] 📊 {name} → 종목명 클립보드 복사 (HTS에서 검색)")

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
        if not self.api_connected:
            self.log_area.append(f"[{now}] ❌ API 미연결 - 매수 불가")
            return
        if not code:
            self.log_area.append(f"[{now}] ❌ 종목코드 없음: {name}")
            return
        config = load_config()
        buy_amount = config["account"].get("buy_amount", 1000000)
        # 현재가 컬럼(3번)에서 가격 읽기
        price_item = self.scan_list.item(row, 3)
        try:
            price = int(price_item.text().replace(",", "")) if price_item else 0
        except Exception:
            price = 0
        qty = max(1, buy_amount // price) if price > 0 else 1
        self.log_area.append(f"[{now}] 💸 수동매수: {name}({code}) {qty}주 시장가")
        result = self.api.buy_order(code, qty, price=0)
        if result:
            self.log_area.append(f"[{now}] ✅ 매수 체결: {name} {qty}주")
            self.refresh_data()
        else:
            self.log_area.append(f"[{now}] ❌ 매수 실패: {name}")

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
        self.ai_thread = AIEngineThread(mode=self.trade_mode)
        self.ai_thread.status_signal.connect(self._on_ai_status)
        self.ai_thread.finished.connect(self._on_ai_engine_stopped)
        self.ai_thread.start()
        self.btn_ai_engine.setChecked(True)
        self.log_area.append(f"[{now}] ▶ AI 엔진 시작")

    def _ai_engine_stop(self):
        now = datetime.now().strftime("%H:%M:%S")
        if not self.ai_thread or not self.ai_thread.isRunning():
            self.btn_ai_engine.setChecked(False)
            return
        self.btn_ai_engine.setStopping()
        self.ai_thread.stop()
        self.log_area.append(f"[{now}] ⏸ AI 엔진 정지 요청")

    # 하위 호환용 (다른 곳에서 호출 시)
    def toggle_ai_engine(self):
        self._on_ai_toggle(not (self.ai_thread and self.ai_thread.isRunning()))

    def _on_ai_status(self, msg: str):
        """AI 엔진 상태 메시지 수신"""
        now = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{now}] {msg}")
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
            if not self.api_connected:
                self.log_area.append(f"[{now}] ❌ API 미연결 - 자동매매 불가")
                return
            self.is_trading = True
            self.btn_start.setText("⏸ 자동매매 중지")
            self.btn_start.setStyleSheet("background-color: #d63031; color: #fff; border: none; font-weight: bold;")
            self.log_area.append(f"[{now}] ▶ 자동매매 시작!")
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
            self.log_area.append(f"[{now}] ⏸ 자동매매 정지")
        self._update_summary({"stock_count": f"{len(self.holdings_data)}종목"})

    # ── 자동매매 사이클 ──
    def auto_trade_cycle(self):
        """10초마다 실행 - AI 신호 체크 → 매수/매도 판단"""
        if not self.api_connected:
            return
        now = datetime.now().strftime("%H:%M:%S")
        config = load_config()

        # 매매 시간 체크
        start_time = config["account"]["start_time"]
        end_time   = config["account"]["end_time"]
        current_time = datetime.now().strftime("%H:%M")
        if current_time < start_time or current_time > end_time:
            return

        # ── AI 신호 기반 매수 ──
        buy_amount  = config["account"]["buy_amount"]
        max_stocks  = config["account"]["max_stocks"]
        held_codes  = {h["raw_code"] for h in self.holdings_data}

        if len(held_codes) < max_stocks:
            for sig in self.ai_signals:
                if sig.get("signal_type") != "BUY":
                    continue
                code = sig.get("stock_code", "")
                name = sig.get("stock_name", "")
                price = sig.get("current_price", 0)
                if not code or not price or code in held_codes:
                    continue
                qty = max(1, buy_amount // price)
                self.log_area.append(
                    f"[{now}] 🤖 AI매수신호: {name}({code}) "
                    f"점수:{sig['score']:.1f} 신뢰:{sig.get('confidence','')} "
                    f"→ {qty}주 시장가"
                )
                result = self.api.buy_order(code, qty, price=0)
                if result:
                    self.log_area.append(f"[{now}] ✅ AI매수 체결: {name} {qty}주")
                    held_codes.add(code)
                else:
                    self.log_area.append(f"[{now}] ❌ AI매수 실패: {name}")
                if len(held_codes) >= max_stocks:
                    break

        # ── 손절 체크 ──
        loss_cut = config["profit"]["loss_cut"]
        for h in self.holdings_data:
            try:
                pnl = float(h["pnl_rate"].replace("%", "").replace("+", ""))
                if pnl <= -loss_cut:
                    self.log_area.append(f"[{now}] ⚠️ 손절 발동: {h['name']} ({h['pnl_rate']})")
                    self.sell_stock(h["name"], h["raw_code"], h["raw_qty"])
            except:
                pass

        # ── AI 매도 신호 체크 (보유종목 중 SELL 신호) ──
        sell_codes = {s["stock_code"] for s in self.ai_signals
                      if s.get("signal_type") == "SELL"}
        for h in self.holdings_data:
            if h["raw_code"] in sell_codes:
                self.log_area.append(f"[{now}] 🤖 AI매도신호: {h['name']} → 전량매도")
                self.sell_stock(h["name"], h["raw_code"], h["raw_qty"])

        # ── 수익 정산 체크 (단계별 분할 매도) ──
        profit_stages = config["profit"]["profit_stages"]
        for h in self.holdings_data:
            try:
                pnl = float(h["pnl_rate"].replace("%", "").replace("+", ""))
                for stage in reversed(profit_stages):
                    if pnl >= stage:
                        sell_qty = max(1, h["raw_qty"] // 3)
                        self.log_area.append(
                            f"[{now}] 📈 수익정산: {h['name']} ({h['pnl_rate']}) → {sell_qty}주 매도"
                        )
                        self.sell_stock(h["name"], h["raw_code"], sell_qty)
                        break
            except:
                pass

        # 잔고 갱신
        self.refresh_data()


    def closeEvent(self, event):
        """창 닫을 때 백그라운드 스레드 정리"""
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.stop()
            self.ai_thread.wait(2000)
        if self._fetch_thread and self._fetch_thread.isRunning():
            self._fetch_thread.wait(1000)
        if self._api_init_thread and self._api_init_thread.isRunning():
            self._api_init_thread.wait(1000)
        event.accept()


# ─────────────────────────────────────────────
#  실행 진입점
# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as _e:
        import traceback
        _log_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)), "crash.log")
        with open(_log_path, "w", encoding="utf-8") as _f:
            traceback.print_exc(file=_f)
        raise
