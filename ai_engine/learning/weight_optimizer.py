"""
가중치 자동 조정 (장 마감 후 실행)
- 각 조건별 적중률 계산
- alpha=0.1로 천천히 가중치 조정
- 최소 20건 이후 조정 시작
"""
import json
import os
import sys
from datetime import datetime
from ..db.database import get_connection


ALPHA      = 0.1    # 학습률
MIN_TRADES = 20     # 최소 거래 수
MIN_WEIGHT = 1      # 최소 가중치
MAX_WEIGHT = 100    # 최대 가중치


def _get_config_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "engine_config.json")


def _load_config() -> dict:
    with open(_get_config_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def _save_config(cfg: dict):
    with open(_get_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def optimize_weights():
    """
    당일 매매 결과 기반 가중치 조정
    장 마감 후 1회 실행
    """
    conn = get_connection()
    try:
        # 매도 완료된 거래 결과 조회
        rows = conn.execute("""
            SELECT conditions, pnl, result FROM trade_results
            WHERE sell_date IS NOT NULL AND conditions IS NOT NULL
            ORDER BY sell_date DESC LIMIT 500
        """).fetchall()

        if len(rows) < MIN_TRADES:
            print(f"[학습] 거래 수 부족 ({len(rows)}/{MIN_TRADES}) - 조정 건너뜀")
            return

        # 조건별 WIN/LOSE 집계
        condition_stats = {}  # 조건명 → {"win": int, "total": int}
        for row in rows:
            try:
                conds = json.loads(row["conditions"])
                is_win = row["result"] == "WIN"
                for cname, cdata in conds.items():
                    score = cdata.get("score", 0)
                    if score < 50:   # 조건 점수 낮으면 이 조건은 작동 안 한 것
                        continue
                    if cname not in condition_stats:
                        condition_stats[cname] = {"win": 0, "total": 0}
                    condition_stats[cname]["total"] += 1
                    if is_win:
                        condition_stats[cname]["win"] += 1
            except:
                continue

        if not condition_stats:
            print("[학습] 조건 통계 없음")
            return

        # 가중치 조정
        cfg = _load_config()
        today = datetime.now().strftime("%Y%m%d")
        adjustments = []

        for item in cfg.get("scoring", []):
            name = item["name"]
            if name not in condition_stats:
                continue
            stats    = condition_stats[name]
            if stats["total"] < 5:
                continue
            accuracy = stats["win"] / stats["total"]
            old_w    = item.get("weight", 10)
            # accuracy 0.5 → 변화 없음, >0.5 → 상향, <0.5 → 하향
            delta    = (accuracy - 0.5) * 2 * old_w * ALPHA
            new_w    = max(MIN_WEIGHT, min(MAX_WEIGHT, int(old_w + delta)))
            item["weight"] = new_w

            adjustments.append({
                "condition": name, "old": old_w, "new": new_w,
                "accuracy": accuracy, "trades": stats["total"]
            })

            # DB 기록
            conn.execute("""
                INSERT INTO weight_history
                    (date, condition, old_weight, new_weight, accuracy, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (today, name, old_w, new_w, round(accuracy, 3),
                  f"적중률 {accuracy:.1%} ({stats['total']}건)",
                  datetime.now().isoformat()))

        _save_config(cfg)
        conn.commit()

        for a in adjustments:
            direction = "↑" if a["new"] > a["old"] else "↓" if a["new"] < a["old"] else "→"
            print(f"[학습] {a['condition']}: {a['old']}→{a['new']} {direction} "
                  f"(적중률 {a['accuracy']:.1%}, {a['trades']}건)")
        print(f"[학습] 가중치 조정 완료 - {len(adjustments)}개 조건")

    finally:
        conn.close()
