import sys
import traceback
import ctypes
import ctypes.wintypes
import threading
import time
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
        tabs.addTab(self._tab_condition(),  "📋 조건식 편집")
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
        self.condition_editor.setPlainText(c.get("condition", ""))

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
        self.config["condition"]               = self.condition_editor.toPlainText()
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
    def _tab_condition(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        info = QLabel("📝 아래에 조건식을 직접 입력하세요. 엑셀 수식처럼 자유롭게 작성 가능합니다.")
        info.setStyleSheet("color: #a0c4ff; font-size: 12px; padding: 4px;")
        layout.addWidget(info)

        # 빠른 입력 버튼들
        btn_row = QHBoxLayout()
        quick_btns = ["코스피", "코스닥", "보통주", "거래량>평균*3", "RSI<30", "이평정배열", "등락률>2%"]
        for text in quick_btns:
            btn = QPushButton(text)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda _, t=text: self._insert_condition(t))
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 조건식 편집기
        self.condition_editor = QTextEdit()
        self.condition_editor.setPlaceholderText(
            "# 조건식 예시\n"
            "시장 = '코스피' OR 시장 = '코스닥'\n"
            "주식구분 = '보통주'\n"
            "시가총액 >= 500억\n"
            "현재가 >= 3000\n"
            "거래량 >= 전일거래량 * 3\n"
            "등락률 >= 2.0\n"
            "RSI(14) <= 70\n"
            "이동평균배열 = '정배열'  # 5일 > 20일 > 60일"
        )
        self.condition_editor.setFont(QFont("Consolas", 12))
        self.condition_editor.setStyleSheet(
            "background-color: #0a0a1a; color: #00ff88; "
            "border: 1px solid #533483; font-family: Consolas;"
        )
        layout.addWidget(self.condition_editor)

        # 지표 참고
        ref = QLabel("📌 사용 가능 지표: 시가총액, 현재가, 거래량, 등락률, RSI(n), MACD, 볼린저밴드, 이동평균(n), 시가, 고가, 저가")
        ref.setStyleSheet("color: #666; font-size: 11px;")
        ref.setWordWrap(True)
        layout.addWidget(ref)
        return w

    def _insert_condition(self, text):
        self.condition_editor.insertPlainText(text + "\n")

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

        # 실투자 API
        grp_real = QGroupBox("실투자 API (포트 8080)")
        grid_real = QGridLayout(grp_real)
        grid_real.addWidget(QLabel("App Key:"), 0, 0)
        self.edit_ls_key = QLineEdit()
        grid_real.addWidget(self.edit_ls_key, 0, 1)
        grid_real.addWidget(QLabel("App Secret:"), 1, 0)
        self.edit_ls_secret = QLineEdit()
        self.edit_ls_secret.setEchoMode(QLineEdit.Password)
        grid_real.addWidget(self.edit_ls_secret, 1, 1)
        note_real = QLabel("* LS투자증권 OpenAPI 실전투자용 키")
        note_real.setStyleSheet("color: #888; font-size: 10px;")
        grid_real.addWidget(note_real, 2, 0, 1, 2)

        # 모의투자 API
        grp_mock = QGroupBox("모의투자 API (포트 29443)")
        grid_mock = QGridLayout(grp_mock)
        grid_mock.addWidget(QLabel("App Key:"), 0, 0)
        self.edit_mock_key = QLineEdit()
        grid_mock.addWidget(self.edit_mock_key, 0, 1)
        grid_mock.addWidget(QLabel("App Secret:"), 1, 0)
        self.edit_mock_secret = QLineEdit()
        self.edit_mock_secret.setEchoMode(QLineEdit.Password)
        grid_mock.addWidget(self.edit_mock_secret, 1, 1)
        note_mock = QLabel("* LS투자증권 OpenAPI 모의투자용 키 (별도 발급)")
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
#  로그인 다이얼로그 (실전/모의 선택)
# ─────────────────────────────────────────────
class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("주식 자동매매 시스템")
        self.setFixedSize(460, 340)
        self.setStyleSheet(DARK_STYLE)
        self.selected_mode = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(14)

        # 타이틀
        title = QLabel("📈 주식 자동매매 시스템")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold; padding: 8px;")
        layout.addWidget(title)

        # API 키 상태 표시
        config = load_config()
        has_keys = bool(config["api"].get("ls_app_key") and config["api"].get("ls_app_secret"))
        if not has_keys:
            warn = QLabel("⚠️ API 키 미설정 - 아래 [API 키 설정] 버튼을 눌러 실전 키를 먼저 입력하세요")
            warn.setAlignment(Qt.AlignCenter)
            warn.setWordWrap(True)
            warn.setStyleSheet(
                "color: #fdcb6e; font-size: 12px; padding: 8px; "
                "background-color: #2d2400; border: 1px solid #fdcb6e; border-radius: 4px;"
            )
            layout.addWidget(warn)
        else:
            ok = QLabel("✅ API 키 설정 완료 - 투자 모드를 선택하세요")
            ok.setAlignment(Qt.AlignCenter)
            ok.setStyleSheet(
                "color: #00b894; font-size: 12px; padding: 6px; "
                "background-color: #00241a; border: 1px solid #00b894; border-radius: 4px;"
            )
            layout.addWidget(ok)

        # 모드 선택 버튼
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_real = QPushButton("📊 실전투자 시작")
        btn_real.setMinimumHeight(56)
        btn_real.setStyleSheet(
            "background-color: #c0392b; color: #fff; font-size: 14px; "
            "font-weight: bold; border: none; border-radius: 6px;"
        )
        btn_real.clicked.connect(lambda: self._select("real"))

        btn_mock = QPushButton("🎮 모의투자 시작")
        btn_mock.setMinimumHeight(56)
        btn_mock.setStyleSheet(
            "background-color: #0984e3; color: #fff; font-size: 14px; "
            "font-weight: bold; border: none; border-radius: 6px;"
        )
        btn_mock.clicked.connect(lambda: self._select("mock"))

        btn_row.addWidget(btn_real)
        btn_row.addWidget(btn_mock)
        layout.addLayout(btn_row)

        # 설명
        note = QLabel(
            "• 실전투자: 포트 8080 접속 → 실계좌 실제 매수/매도\n"
            "• 모의투자: 포트 29443 접속 → 모의계좌 실제 매수/매도 (가상머니)"
        )
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("color: #888; font-size: 11px; padding: 4px;")
        layout.addWidget(note)

        # 설정 버튼
        btn_settings = QPushButton("⚙️ API 키 설정")
        btn_settings.setStyleSheet("background-color: #533483; color: #fff; border: none; padding: 6px;")
        btn_settings.clicked.connect(self._open_settings)
        layout.addWidget(btn_settings)

    def _select(self, mode):
        from PyQt5.QtWidgets import QMessageBox
        config = load_config()
        has_keys = bool(config["api"].get("ls_app_key") and config["api"].get("ls_app_secret"))
        if not has_keys:
            QMessageBox.warning(self, "API 키 미설정",
                                "실전 App Key/Secret을 먼저 설정에서 입력하세요.")
            return
        self.selected_mode = mode
        self.accept()

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec_()
        # 설정 저장 후 화면 다시 그리기
        self._rebuild_ui()

    def _rebuild_ui(self):
        # 레이아웃 초기화 후 재구성
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._build_ui()


# ─────────────────────────────────────────────
#  메인 윈도우
# ─────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, trade_mode="real"):
        super().__init__()
        mode_title = "🎮 모의투자" if trade_mode == "mock" else "📊 실전투자"
        self.setWindowTitle(f"주식 자동매매 시스템 v1.1 [{mode_title}]")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(DARK_STYLE)

        # API 초기화 (로그인 화면에서 선택한 모드 사용)
        self.trade_mode = trade_mode
        self.api = LSApi(mode=self.trade_mode)
        self.api_connected = False
        self.is_trading = False
        self.holdings_data = []  # 보유종목 원본 데이터

        self._build_ui()
        # 버튼 초기 상태를 config의 trade_mode에 맞게 설정
        self.btn_mock.setChecked(self.trade_mode == "mock")
        self.btn_real.setChecked(self.trade_mode == "real")
        self._init_api()

        # 30초마다 자동 업데이트 타이머
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(30000)  # 30초

        # 60초마다 자동 재연결 타이머 (미연결 상태일 때만 재시도)
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self._auto_reconnect)
        self.reconnect_timer.start(60000)  # 60초

    def _auto_reconnect(self):
        """60초마다 미연결 상태면 자동 재연결 시도"""
        if not self.api_connected:
            now = datetime.now().strftime("%H:%M:%S")
            self.log_area.append(f"[{now}] 🔄 API 재연결 시도...")
            self._init_api()

    def _init_api(self):
        """프로그램 시작 시 API 연결 및 초기 데이터 로드"""
        now = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{now}] 시스템 시작")
        try:
            if self.api.get_token():
                self.api_connected = True
                self.ls_badge.setText("LS ✅")
                self.ls_badge.setStyleSheet(
                    "background-color: #00b89422; color: #00b894; "
                    "border: 1px solid #00b894; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
                )
                self.log_area.append(f"[{now}] LS API 연결 완료")
                self.refresh_data()
            else:
                self.ls_badge.setText("LS ❌")
                self.ls_badge.setStyleSheet(
                    "background-color: #d6303122; color: #d63031; "
                    "border: 1px solid #d63031; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
                )
                self.log_area.append(f"[{now}] ❌ LS API 연결 실패 - {self.api.last_error}")
        except Exception as e:
            self.log_area.append(f"[{now}] ❌ API 오류: {e}")

    def refresh_data(self):
        """보유종목 + 계좌요약 업데이트"""
        if not self.api_connected:
            return
        try:
            holdings, summary = self.api.get_holdings_for_ui()
            self.holdings_data = holdings
            self._update_holdings_table(holdings)
            self._update_summary(summary)
            now = datetime.now().strftime("%H:%M:%S")
            self.time_label.setText(f"⏱ {now} 업데이트")
        except Exception as e:
            now = datetime.now().strftime("%H:%M:%S")
            self.log_area.append(f"[{now}] ❌ 데이터 갱신 실패: {e}")

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

        self.btn_mock = QPushButton("모의")
        self.btn_mock.setCheckable(True)
        self.btn_mock.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_mock.clicked.connect(lambda: self.switch_trade_mode("mock"))
        layout.addWidget(self.btn_mock)

        self.btn_real = QPushButton("실전")
        self.btn_real.setCheckable(True)
        self.btn_real.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_real.clicked.connect(lambda: self.switch_trade_mode("real"))
        layout.addWidget(self.btn_real)

        self.btn_stop = QPushButton("⏹ 정지")
        self.btn_stop.setObjectName("btn_stop")
        layout.addWidget(self.btn_stop)

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
            "종목명", "매수가", "현재가", "등락률", "수익률", "보유수량", "평가금액", "손익금액", "매도"
        ])
        self.holdings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.holdings_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.Fixed)
        self.holdings_table.setColumnWidth(8, 70)
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

        # 검색종목 리스트
        left = QGroupBox("🔍 검색종목")
        left_layout = QVBoxLayout(left)
        self.search_list = QTableWidget()
        self.search_list.setColumnCount(3)
        self.search_list.setHorizontalHeaderLabels(["종목명", "현재가", "등락률"])
        self.search_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.search_list.setEditTriggers(QTableWidget.NoEditTriggers)
        # 샘플
        stocks = [("삼성전자","73,400","+2.34%"),("SK하이닉스","128,500","+1.87%"),
                  ("카카오","42,150","+3.12%"),("NAVER","168,000","+0.96%"),
                  ("LG에너지솔루션","385,500","+4.21%")]
        self.search_list.setRowCount(len(stocks))
        for r, (n, p, c) in enumerate(stocks):
            for col, val in enumerate([n, p, c]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if col == 2:
                    item.setForeground(QColor("#ff6b6b") if val.startswith("+") else QColor("#74b9ff"))
                self.search_list.setItem(r, col, item)

        # 더블클릭 시 HTS 종목 연동
        self.search_list.cellDoubleClicked.connect(self._on_search_click)

        btn_row = QHBoxLayout()
        btn_chart = QPushButton("📊 차트▶")
        btn_chart.clicked.connect(self._open_chart_from_search)
        btn_buy   = QPushButton("💸 매수")
        btn_buy.setObjectName("btn_start")
        btn_row.addWidget(btn_chart)
        btn_row.addWidget(btn_buy)
        left_layout.addWidget(self.search_list)
        left_layout.addLayout(btn_row)

        # 추천종목 리스트
        right = QGroupBox("⭐ 추천종목 상세")
        right_layout = QVBoxLayout(right)
        self.rec_list = QTableWidget()
        self.rec_list.setColumnCount(4)
        self.rec_list.setHorizontalHeaderLabels(["순위", "종목명", "상승확률", "현재가"])
        self.rec_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rec_list.setEditTriggers(QTableWidget.NoEditTriggers)
        rec_data = [("1","LG에너지솔루션","81.3%","385,500"),
                    ("2","삼성전자","73.2%","73,400"),
                    ("3","SK하이닉스","68.5%","128,500"),
                    ("4","카카오","65.1%","42,150")]
        self.rec_list.setRowCount(len(rec_data))
        for r, row in enumerate(rec_data):
            for c, val in enumerate(row):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                if c == 2:
                    item.setForeground(QColor("#00b894"))
                self.rec_list.setItem(r, c, item)

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
        theme_layout = QVBoxLayout(theme_grp)
        theme_layout.setSpacing(4)

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

            # 매도 버튼
            btn_sell = QPushButton("💸 매도")
            btn_sell.setStyleSheet(
                "background-color: #d63031; color: #fff; border: none; "
                "border-radius: 3px; font-size: 11px; padding: 2px;"
            )
            code = h["raw_code"]
            qty = h["raw_qty"]
            name = h["name"]
            btn_sell.clicked.connect(lambda _, c=code, q=qty, n=name: self.sell_stock(n, c, q))
            self.holdings_table.setCellWidget(row, 8, btn_sell)

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
        self.trade_mode = mode
        # 버튼 상태 업데이트
        self.btn_mock.setChecked(mode == "mock")
        self.btn_real.setChecked(mode == "real")
        # 자동매매 중이면 정지
        if self.is_trading:
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

    def _on_search_click(self, row, col):
        """검색종목 클릭 → HTS 차트 연동"""
        name_item = self.search_list.item(row, 0)
        if name_item:
            name = name_item.text()
            code = getattr(self, '_search_codes', {}).get(row, "")
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

    def _open_chart_from_search(self):
        """검색종목 차트▶ 버튼 클릭"""
        row = self.search_list.currentRow()
        if row >= 0:
            name_item = self.search_list.item(row, 0)
            if name_item:
                name = name_item.text()
                code = getattr(self, '_search_codes', {}).get(row, "")
                self._send_to_hts(code, name)

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
        """10초마다 실행 - 조건식 체크 → 매수/매도 판단"""
        if not self.api_connected:
            return
        now = datetime.now().strftime("%H:%M:%S")
        config = load_config()

        # 매매 시간 체크
        start_time = config["account"]["start_time"]
        end_time = config["account"]["end_time"]
        current_time = datetime.now().strftime("%H:%M")
        if current_time < start_time or current_time > end_time:
            return

        # 손절 체크 (보유종목 중 손절 기준 이하인 종목 매도)
        loss_cut = config["profit"]["loss_cut"]
        for h in self.holdings_data:
            try:
                pnl = float(h["pnl_rate"].replace("%", "").replace("+", ""))
                if pnl <= -loss_cut:
                    self.log_area.append(f"[{now}] ⚠️ 손절 발동: {h['name']} ({h['pnl_rate']})")
                    self.sell_stock(h["name"], h["raw_code"], h["raw_qty"])
            except:
                pass

        # 수익 정산 체크 (단계별 분할 매도)
        profit_stages = config["profit"]["profit_stages"]
        for h in self.holdings_data:
            try:
                pnl = float(h["pnl_rate"].replace("%", "").replace("+", ""))
                for stage in reversed(profit_stages):
                    if pnl >= stage:
                        sell_qty = max(1, h["raw_qty"] // 3)  # 1/3 분할매도
                        self.log_area.append(f"[{now}] 📈 수익정산: {h['name']} ({h['pnl_rate']}) → {sell_qty}주 매도")
                        self.sell_stock(h["name"], h["raw_code"], sell_qty)
                        break
            except:
                pass

        # 잔고 갱신
        self.refresh_data()


# ─────────────────────────────────────────────
#  실행 진입점
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 로그인 다이얼로그: 실전/모의 선택
    login = LoginDialog()
    if login.exec_() != QDialog.Accepted:
        sys.exit(0)

    window = MainWindow(trade_mode=login.selected_mode)
    window.show()
    sys.exit(app.exec_())
