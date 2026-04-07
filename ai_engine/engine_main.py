"""
AI 매매 엔진 실행 진입점
사용법: python ai_engine/engine_main.py [real|mock]

동작:
1. 장 시작 전: 종목 유니버스 로드
2. 장중 (09:00~15:30): 5분마다 전 종목 스캔 → ai_signals.json 업데이트
3. 장 마감 후 (15:40): 가중치 학습 실행
4. GUI 명령(command.json) 수시 체크
"""
import sys
import os
import time
import json
from datetime import datetime

# stock_trader/ 루트를 경로에 추가
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from ai_engine.db.database          import init_db
from ai_engine.data.ls_data_fetcher import LSDataFetcher
from ai_engine.core.scanner         import Scanner
from ai_engine.comm.signal_writer   import write_signals
from ai_engine.comm.command_reader  import read_command
from ai_engine.learning.weight_optimizer import optimize_weights


SCAN_INTERVAL   = 300   # 5분마다 스캔
MARKET_OPEN     = "09:00"
MARKET_CLOSE    = "15:30"
LEARN_TIME      = "15:40"   # 가중치 학습 실행 시각


def _now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _current_hm() -> str:
    return datetime.now().strftime("%H:%M")


def _is_market_open() -> bool:
    hm = _current_hm()
    return MARKET_OPEN <= hm <= MARKET_CLOSE


def handle_command(cmd: dict, scanner: Scanner, mode_holder: list):
    """GUI 명령 처리"""
    command = cmd.get("command", "")
    params  = cmd.get("params", {})
    if command == "set_mode":
        new_mode = params.get("mode", "real")
        mode_holder[0] = new_mode
        print(f"[엔진] 모드 변경: {new_mode}")
    elif command == "pause":
        print("[엔진] 일시정지 명령 수신")
    elif command == "resume":
        print("[엔진] 재개 명령 수신")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "real"
    mode_holder = [mode]
    learned_today = False

    print(f"[엔진] AI 매매 엔진 시작 (모드: {mode})")

    # DB 초기화
    init_db()

    # API 연결
    fetcher = LSDataFetcher(mode=mode)
    if not fetcher.connect():
        print("[엔진] ❌ API 연결 실패 - 30초 후 재시도")
        time.sleep(30)
        if not fetcher.connect():
            print("[엔진] ❌ 재연결 실패 - 종료")
            sys.exit(1)

    scanner = Scanner(fetcher)
    print(f"[엔진] ✅ API 연결 완료 ({_now_str()})")

    last_scan  = 0
    last_learn = ""

    while True:
        now_hm = _current_hm()

        # GUI 명령 체크
        cmd = read_command()
        if cmd:
            handle_command(cmd, scanner, mode_holder)

        # 장 마감 후 학습 (1일 1회)
        today = datetime.now().strftime("%Y%m%d")
        if now_hm >= LEARN_TIME and last_learn != today:
            print(f"[엔진] 📚 가중치 학습 시작 ({_now_str()})")
            try:
                optimize_weights()
            except Exception as e:
                print(f"[엔진] 학습 오류: {e}")
            last_learn = today
            learned_today = True

        # 장중 스캔
        if _is_market_open():
            elapsed = time.time() - last_scan
            if elapsed >= SCAN_INTERVAL:
                print(f"\n[엔진] 🔍 스캔 시작 ({_now_str()})")
                try:
                    signals, count = scanner.run_scan()
                    write_signals(signals, scan_count=count)
                    print(f"[엔진] ✅ {count}종목 스캔 → {len(signals)}개 신호")
                except Exception as e:
                    print(f"[엔진] 스캔 오류: {e}")
                last_scan = time.time()
        else:
            if now_hm < MARKET_OPEN:
                wait_min = (int(MARKET_OPEN[:2]) * 60 + int(MARKET_OPEN[3:])) - \
                           (int(now_hm[:2]) * 60 + int(now_hm[3:]))
                if wait_min > 0 and wait_min % 30 == 0:
                    print(f"[엔진] 장 시작까지 {wait_min}분 대기 중...")

        time.sleep(10)


if __name__ == "__main__":
    main()
