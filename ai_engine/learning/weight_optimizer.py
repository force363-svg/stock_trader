"""
가중치 자동 조정 + 수익률 분석 (장 마감 후 실행)
- 각 조건별 적중률 계산 → 가중치 조정
- 전일/주간/월간 수익률 분석 → 매수 임계값 조정
- 종목별 포지션 분석 → 조건 패턴 학습
- alpha=0.1로 천천히 가중치 조정
- 최소 20건 이후 조정 시작
"""
import json
import os
import sys
from datetime import datetime, timedelta
from ..db.database import get_connection


ALPHA      = 0.1    # 학습률
MIN_TRADES = 20     # 최소 거래 수
MIN_WEIGHT = 1      # 최소 가중치
MAX_WEIGHT = 100    # 최대 가중치


def _get_config_path():
    from ..conditions._config_helper import get_engine_config_path
    return get_engine_config_path()


def _load_config() -> dict:
    with open(_get_config_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def _save_config(cfg: dict):
    with open(_get_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _get_log_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "learning_log.txt")


def _log(msg: str):
    """학습 로그 기록"""
    try:
        with open(_get_log_path(), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass
    print(f"[학습] {msg}")


# ═══════════════════════════════════════════════════════
#  수익률 분석
# ═══════════════════════════════════════════════════════

def analyze_performance() -> dict:
    """
    전일/주간/월간 수익률 분석
    반환: {
        "daily_pnl": float,      전일 평균 수익률
        "weekly_pnl": float,     주간 평균 수익률
        "monthly_pnl": float,    월간 평균 수익률
        "daily_count": int,      전일 거래 수
        "weekly_count": int,     주간 거래 수
        "monthly_count": int,    월간 거래 수
        "weekly_win_rate": float, 주간 승률
        "monthly_win_rate": float,월간 승률
        "trend": str,            "UP" / "DOWN" / "FLAT"
    }
    """
    conn = get_connection()
    try:
        today = datetime.now()
        d1  = (today - timedelta(days=1)).strftime("%Y%m%d")
        d7  = (today - timedelta(days=7)).strftime("%Y%m%d")
        d30 = (today - timedelta(days=30)).strftime("%Y%m%d")

        def _calc(from_date):
            rows = conn.execute("""
                SELECT pnl, result FROM trade_results
                WHERE sell_date IS NOT NULL AND sell_date >= ?
            """, (from_date,)).fetchall()
            if not rows:
                return 0.0, 0, 0.0
            pnls = [r["pnl"] for r in rows if r["pnl"] is not None]
            wins = sum(1 for r in rows if r["result"] == "WIN")
            avg = sum(pnls) / len(pnls) if pnls else 0.0
            win_rate = wins / len(rows) if rows else 0.0
            return avg, len(rows), win_rate

        daily_pnl, daily_cnt, daily_wr = _calc(d1)
        weekly_pnl, weekly_cnt, weekly_wr = _calc(d7)
        monthly_pnl, monthly_cnt, monthly_wr = _calc(d30)

        # 추세 판단: 주간 vs 월간
        if weekly_cnt >= 3 and monthly_cnt >= 5:
            if weekly_pnl > monthly_pnl + 0.5:
                trend = "UP"
            elif weekly_pnl < monthly_pnl - 0.5:
                trend = "DOWN"
            else:
                trend = "FLAT"
        else:
            trend = "FLAT"

        return {
            "daily_pnl": round(daily_pnl, 2),
            "weekly_pnl": round(weekly_pnl, 2),
            "monthly_pnl": round(monthly_pnl, 2),
            "daily_count": daily_cnt,
            "weekly_count": weekly_cnt,
            "monthly_count": monthly_cnt,
            "weekly_win_rate": round(weekly_wr, 3),
            "monthly_win_rate": round(monthly_wr, 3),
            "trend": trend
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
#  종목별 포지션 분석
# ═══════════════════════════════════════════════════════

def analyze_positions() -> list:
    """
    종목별 매매 결과 분석 — 어떤 조건에서 수익/손실이 났는지
    반환: [{"code", "name", "trades", "win_rate", "avg_pnl",
            "best_conditions", "worst_conditions"}, ...]
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT code, name, pnl, result, conditions, signal_score
            FROM trade_results
            WHERE sell_date IS NOT NULL AND conditions IS NOT NULL
            ORDER BY sell_date DESC LIMIT 500
        """).fetchall()

        # 종목별 집계
        stock_stats = {}
        for row in rows:
            code = row["code"]
            if code not in stock_stats:
                stock_stats[code] = {
                    "code": code, "name": row["name"],
                    "trades": [], "wins": 0, "total": 0
                }
            stock_stats[code]["total"] += 1
            if row["result"] == "WIN":
                stock_stats[code]["wins"] += 1
            stock_stats[code]["trades"].append({
                "pnl": row["pnl"],
                "result": row["result"],
                "score": row["signal_score"],
                "conditions": row["conditions"]
            })

        results = []
        for code, stats in stock_stats.items():
            pnls = [t["pnl"] for t in stats["trades"] if t["pnl"] is not None]
            avg_pnl = sum(pnls) / len(pnls) if pnls else 0

            # 수익 거래에서 높은 점수였던 조건 vs 손실 거래에서 높은 점수였던 조건
            best_conds = {}
            worst_conds = {}
            for t in stats["trades"]:
                try:
                    conds = json.loads(t["conditions"]) if t["conditions"] else {}
                except Exception:
                    continue
                target = best_conds if t["result"] == "WIN" else worst_conds
                for cname, cdata in conds.items():
                    score = cdata.get("score", 0) if isinstance(cdata, dict) else 0
                    if score >= 50:
                        target[cname] = target.get(cname, 0) + 1

            results.append({
                "code": code,
                "name": stats["name"],
                "trades": stats["total"],
                "win_rate": round(stats["wins"] / stats["total"], 2) if stats["total"] > 0 else 0,
                "avg_pnl": round(avg_pnl, 2),
                "best_conditions": sorted(best_conds.items(), key=lambda x: -x[1])[:5],
                "worst_conditions": sorted(worst_conds.items(), key=lambda x: -x[1])[:5]
            })

        return sorted(results, key=lambda x: -x["trades"])
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════
#  매수 임계값 자동 조정
# ═══════════════════════════════════════════════════════

def adjust_threshold(perf: dict, cfg: dict) -> dict:
    """
    수익률 추세에 따라 매수 임계값 조정
    - 수익률 하락 추세 → 보수적 (임계값 ↑)
    - 수익률 상승 추세 → 공격적 (임계값 ↓, 최소 70)
    - 변화폭: ±2점/회
    """
    thresholds = cfg.get("thresholds", {})
    buy_t = thresholds.get("buy", 75)
    old_buy = buy_t

    trend = perf.get("trend", "FLAT")
    monthly_wr = perf.get("monthly_win_rate", 0.5)

    if trend == "DOWN" or monthly_wr < 0.4:
        # 손실 추세 → 보수적
        buy_t = min(90, buy_t + 2)
        reason = f"하락추세(승률:{monthly_wr:.0%}) → 매수기준 상향"
    elif trend == "UP" and monthly_wr > 0.6:
        # 수익 추세 → 공격적
        buy_t = max(70, buy_t - 2)
        reason = f"상승추세(승률:{monthly_wr:.0%}) → 매수기준 하향"
    else:
        reason = "추세 유지"

    if buy_t != old_buy:
        thresholds["buy"] = buy_t
        cfg["thresholds"] = thresholds
        _log(f"매수 임계값 조정: {old_buy} → {buy_t} ({reason})")

    return cfg


# ═══════════════════════════════════════════════════════
#  메인: 가중치 최적화 (장 마감 후 1회 실행)
# ═══════════════════════════════════════════════════════

def optimize_weights():
    """
    당일 매매 결과 기반 종합 학습
    1. 수익률 분석 (전일/주간/월간)
    2. 종목별 포지션 분석
    3. 조건별 적중률 → 가중치 조정
    4. 수익률 추세 → 매수 임계값 조정
    """
    _log("=" * 50)
    _log("장 마감 학습 시작")

    # 1. 수익률 분석
    perf = analyze_performance()
    _log(f"전일 수익률: {perf['daily_pnl']:+.2f}% ({perf['daily_count']}건)")
    _log(f"주간 수익률: {perf['weekly_pnl']:+.2f}% ({perf['weekly_count']}건, 승률:{perf['weekly_win_rate']:.0%})")
    _log(f"월간 수익률: {perf['monthly_pnl']:+.2f}% ({perf['monthly_count']}건, 승률:{perf['monthly_win_rate']:.0%})")
    _log(f"추세: {perf['trend']}")

    # 2. 종목별 분석 (로그)
    positions = analyze_positions()
    if positions:
        _log(f"--- 종목별 실적 (최근 {len(positions)}종목) ---")
        for p in positions[:10]:
            _log(f"  {p['name']}({p['code']}): {p['trades']}건 "
                 f"승률:{p['win_rate']:.0%} 평균:{p['avg_pnl']:+.2f}%")

    # 3. 조건별 가중치 조정
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT conditions, pnl, result FROM trade_results
            WHERE sell_date IS NOT NULL AND conditions IS NOT NULL
            ORDER BY sell_date DESC LIMIT 500
        """).fetchall()

        cfg = _load_config()

        if len(rows) >= MIN_TRADES:
            # 조건별 WIN/LOSE 집계
            condition_stats = {}
            for row in rows:
                try:
                    conds = json.loads(row["conditions"])
                    is_win = row["result"] == "WIN"
                    for cname, cdata in conds.items():
                        score = cdata.get("score", 0) if isinstance(cdata, dict) else 0
                        if score < 50:
                            continue
                        if cname not in condition_stats:
                            condition_stats[cname] = {"win": 0, "total": 0}
                        condition_stats[cname]["total"] += 1
                        if is_win:
                            condition_stats[cname]["win"] += 1
                except Exception:
                    continue

            if condition_stats:
                today = datetime.now().strftime("%Y%m%d")
                adjustments = []

                for item in cfg.get("scoring", []):
                    name = item["name"]
                    if name not in condition_stats:
                        continue
                    stats = condition_stats[name]
                    if stats["total"] < 5:
                        continue
                    accuracy = stats["win"] / stats["total"]
                    old_w = item.get("weight", 10)
                    delta = (accuracy - 0.5) * 2 * old_w * ALPHA
                    new_w = max(MIN_WEIGHT, min(MAX_WEIGHT, int(old_w + delta)))
                    item["weight"] = new_w

                    adjustments.append({
                        "condition": name, "old": old_w, "new": new_w,
                        "accuracy": accuracy, "trades": stats["total"]
                    })

                    conn.execute("""
                        INSERT INTO weight_history
                            (date, condition, old_weight, new_weight, accuracy, reason, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (today, name, old_w, new_w, round(accuracy, 3),
                          f"적중률 {accuracy:.1%} ({stats['total']}건)",
                          datetime.now().isoformat()))

                for a in adjustments:
                    direction = "↑" if a["new"] > a["old"] else "↓" if a["new"] < a["old"] else "→"
                    _log(f"가중치: {a['condition']}: {a['old']}→{a['new']} {direction} "
                         f"(적중률 {a['accuracy']:.1%}, {a['trades']}건)")
                _log(f"가중치 조정: {len(adjustments)}개 조건")
        else:
            _log(f"거래 수 부족 ({len(rows)}/{MIN_TRADES}) - 가중치 조정 건너뜀")

        # 4. 수익률 추세 → 매수 임계값 조정
        cfg = adjust_threshold(perf, cfg)

        _save_config(cfg)
        conn.commit()
        _log("장 마감 학습 완료")

    finally:
        conn.close()
