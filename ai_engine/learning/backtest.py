"""
백테스트 - 과거 데이터로 전략 검증
"""
from datetime import datetime
from ..core.scorer import calculate_score
from ..core.signal_generator import generate_signal


class Backtest:
    def __init__(self, fetcher):
        self.fetcher = fetcher

    def run(self, codes: list, start_date: str = "", end_date: str = "") -> dict:
        """
        백테스트 실행
        codes: 테스트할 종목코드 리스트
        반환: {
            "total": int, "win": int, "loss": int,
            "win_rate": float, "avg_pnl": float,
            "results": [{"code","name","buy_date","sell_date","pnl"}, ...]
        }
        """
        results  = []
        win, loss = 0, 0
        pnl_list  = []

        for code in codes:
            try:
                daily = self.fetcher.get_daily_ohlcv(code, count=250)
                if len(daily) < 50:
                    continue

                # 슬라이딩 윈도우: 200봉씩 잘라서 신호 확인
                for i in range(len(daily) - 60, 0, -5):
                    window_data = {
                        "daily" : daily[i:],
                        "min60" : [],
                        "min15" : [],
                        "supply": [],
                        "price" : {"price": daily[i]["close"],
                                   "diff" : 3.0}  # 가정
                    }
                    sig = generate_signal(code, code, window_data)
                    if not sig or sig["signal_type"] != "BUY":
                        continue

                    # 5일 후 수익률 계산 (단순 검증)
                    if i < 5:
                        break
                    buy_price  = daily[i]["close"]
                    sell_price = daily[i - 5]["close"]
                    pnl = (sell_price - buy_price) / buy_price * 100

                    pnl_list.append(pnl)
                    if pnl > 0:
                        win += 1
                    else:
                        loss += 1

                    results.append({
                        "code"      : code,
                        "buy_date"  : daily[i]["date"],
                        "sell_date" : daily[i-5]["date"],
                        "buy_price" : buy_price,
                        "sell_price": sell_price,
                        "pnl"       : round(pnl, 2),
                        "score"     : sig["score"]
                    })

            except Exception as e:
                print(f"[백테스트] {code} 오류: {e}")

        total    = win + loss
        win_rate = win / total * 100 if total > 0 else 0
        avg_pnl  = sum(pnl_list) / len(pnl_list) if pnl_list else 0

        return {
            "total"   : total,
            "win"     : win,
            "loss"    : loss,
            "win_rate": round(win_rate, 1),
            "avg_pnl" : round(avg_pnl, 2),
            "results" : results[:100]  # 최대 100건
        }
