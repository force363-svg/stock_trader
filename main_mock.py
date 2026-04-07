"""
모의투자 전용 실행 파일
- LS 모의투자 서버 (포트 29443)
- ls_mock_key / ls_mock_secret 사용
- main.py(실전용)와 완전히 독립 실행
"""
import sys
from main import MainWindow, QApplication, QDialog

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow(trade_mode="mock")
    window.show()
    sys.exit(app.exec_())
