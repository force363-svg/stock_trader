"""
매매 결과 기록 (학습용)
"""
import json
from datetime import datetime
from ..db.database import get_connection


class TradeRecorder:
    def record_buy(self, code: str, name: str, buy_price: int,
                   qty: int, signal_score: float, conditions: dict):
        """매수 체결 기록 (시장 상황 포함)"""
        conn = get_connection()
        try:
            # 시장 상황 기록
            market_regime = ""
            try:
                from .strategy_manager import classify_market
                market_regime = classify_market().get("regime", "")
            except Exception:
                pass

            # market_regime 컬럼 없으면 추가
            try:
                conn.execute("ALTER TABLE trade_results ADD COLUMN market_regime TEXT")
            except Exception:
                pass

            conn.execute("""
                INSERT INTO trade_results
                    (code, name, buy_date, buy_price, qty, signal_score, conditions,
                     market_regime, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, name,
                  datetime.now().strftime("%Y%m%d"),
                  buy_price, qty, signal_score,
                  json.dumps(conditions, ensure_ascii=False),
                  market_regime,
                  datetime.now().isoformat()))
            conn.commit()
            print(f"[기록] 매수 기록: {name}({code}) {buy_price:,}원 x{qty}주 [{market_regime}]")
        finally:
            conn.close()

    def record_sell(self, code: str, sell_price: int, qty: int):
        """매도 체결 기록 - 가장 최근 미완료 매수 기록에 업데이트"""
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT id, buy_price FROM trade_results
                WHERE code=? AND sell_date IS NULL
                ORDER BY buy_date DESC LIMIT 1
            """, (code,)).fetchone()

            if not row:
                print(f"[기록] {code} 매수 기록 없음 - 매도만 기록")
                return

            buy_price = row["buy_price"]
            pnl = ((sell_price - buy_price) / buy_price * 100) if buy_price > 0 else 0
            result = "WIN" if pnl > 0 else "LOSS"

            conn.execute("""
                UPDATE trade_results
                SET sell_date=?, sell_price=?, pnl=?, result=?
                WHERE id=?
            """, (datetime.now().strftime("%Y%m%d"),
                  sell_price, round(pnl, 2), result, row["id"]))
            conn.commit()
            print(f"[기록] 매도 기록: {code} {sell_price:,}원 → {pnl:+.2f}% ({result})")
        finally:
            conn.close()

    def get_recent_results(self, days: int = 30) -> list:
        """최근 N일 매매 결과 조회"""
        conn = get_connection()
        try:
            rows = conn.execute("""
                SELECT * FROM trade_results
                WHERE sell_date IS NOT NULL
                ORDER BY sell_date DESC
                LIMIT 200
            """).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
