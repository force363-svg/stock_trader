"""
AI 자체 판단 모델 (순수 Python — 외부 라이브러리 불필요)

과거 매매 데이터를 분석하여 새로운 종목의 승률을 예측.
사용자가 설정한 조건과 별개로 AI가 스스로 패턴을 학습.

모델 구조:
1. 조건별 베이지안 확률 — P(WIN | 조건점수 구간)
2. 조건 조합 패턴 — 동시 고점수 조건 조합의 승률
3. 시장 상황별 승률 — 시장 지수/업종/테마에 따른 승률 변화
4. 종목 특성별 승률 — 업종/시가총액 등에 따른 승률

블렌딩:
  최종점수 = (1-α) × 사용자점수 + α × AI예측점수
  α = min(0.5, 거래수/200)  ← 데이터 적으면 0, 최대 0.5
"""
import json
import math
from datetime import datetime
from ..db.database import get_connection


# ─── 설정 ───
MIN_TRADES_FOR_PREDICT = 10    # 최소 거래 수 (이하면 예측 안 함)
MAX_BLEND_RATIO        = 0.5   # AI 최대 반영 비율
BLEND_RAMP_TRADES      = 200   # 이 거래 수에서 MAX_BLEND에 도달
SCORE_BINS = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]


class AIPredictor:
    """과거 매매 데이터 기반 AI 예측 모델"""

    def __init__(self):
        self._condition_probs = {}   # 조건별 구간별 승률
        self._combo_patterns = {}    # 조건 조합 패턴
        self._total_trades = 0
        self._base_win_rate = 0.5
        self._loaded = False

    def load_model(self):
        """DB에서 과거 거래 데이터 로드 → 모델 구축"""
        conn = get_connection()
        try:
            rows = conn.execute("""
                SELECT conditions, pnl, result, signal_score
                FROM trade_results
                WHERE sell_date IS NOT NULL AND conditions IS NOT NULL
                ORDER BY sell_date DESC LIMIT 1000
            """).fetchall()

            self._total_trades = len(rows)
            if self._total_trades < MIN_TRADES_FOR_PREDICT:
                self._loaded = False
                return

            wins = sum(1 for r in rows if r["result"] == "WIN")
            self._base_win_rate = wins / self._total_trades if self._total_trades > 0 else 0.5

            # ── 1. 조건별 베이지안 확률 계산 ──
            self._condition_probs = self._calc_condition_probs(rows)

            # ── 2. 조건 조합 패턴 ──
            self._combo_patterns = self._calc_combo_patterns(rows)

            self._loaded = True

        except Exception as e:
            print(f"[AI모델] 로드 실패: {e}")
            self._loaded = False
        finally:
            conn.close()

    def _calc_condition_probs(self, rows) -> dict:
        """
        각 조건의 점수 구간별 승률 계산
        결과: {조건명: {(0,20): {"win":3, "total":5}, (20,40): {...}, ...}}
        """
        cond_bins = {}

        for row in rows:
            try:
                conds = json.loads(row["conditions"])
                is_win = row["result"] == "WIN"
            except Exception:
                continue

            for cname, cdata in conds.items():
                score = cdata.get("score", 0) if isinstance(cdata, dict) else 0

                if cname not in cond_bins:
                    cond_bins[cname] = {}
                    for b in SCORE_BINS:
                        cond_bins[cname][b] = {"win": 0, "total": 0}

                for lo, hi in SCORE_BINS:
                    if lo <= score < hi:
                        cond_bins[cname][(lo, hi)]["total"] += 1
                        if is_win:
                            cond_bins[cname][(lo, hi)]["win"] += 1
                        break

        # 승률 계산 (라플라스 스무딩)
        result = {}
        for cname, bins in cond_bins.items():
            result[cname] = {}
            for b, stats in bins.items():
                total = stats["total"]
                win = stats["win"]
                # 라플라스 스무딩: (win + 1) / (total + 2)
                result[cname][b] = (win + 1) / (total + 2)

        return result

    def _calc_combo_patterns(self, rows) -> dict:
        """
        2개 조건 조합의 승률 계산
        "체결강도 HIGH + 수급 HIGH" → 승률 80%
        """
        combos = {}

        for row in rows:
            try:
                conds = json.loads(row["conditions"])
                is_win = row["result"] == "WIN"
            except Exception:
                continue

            # 고점수(60+) 조건 추출
            high_conds = sorted([
                cname for cname, cdata in conds.items()
                if isinstance(cdata, dict) and cdata.get("score", 0) >= 60
            ])

            # 2개 조합
            for i in range(len(high_conds)):
                for j in range(i + 1, len(high_conds)):
                    key = f"{high_conds[i]}+{high_conds[j]}"
                    if key not in combos:
                        combos[key] = {"win": 0, "total": 0}
                    combos[key]["total"] += 1
                    if is_win:
                        combos[key]["win"] += 1

        # 최소 3건 이상만 유지
        return {
            k: {"win_rate": v["win"] / v["total"], "count": v["total"]}
            for k, v in combos.items()
            if v["total"] >= 3
        }

    def predict(self, conditions: dict) -> dict:
        """
        새로운 종목의 조건 점수를 받아 AI 예측 수행

        conditions: {조건명: {"score": float, "detail": str}, ...}
        반환: {
            "ai_score": float,       AI 예측 점수 (0~100)
            "win_probability": float, 승률 예측 (0~1)
            "confidence": str,       신뢰도 (HIGH/MEDIUM/LOW)
            "blend_ratio": float,    블렌딩 비율 (0~0.5)
            "reasons": [str],        판단 근거
        }
        """
        if not self._loaded or self._total_trades < MIN_TRADES_FOR_PREDICT:
            return {
                "ai_score": 50.0,
                "win_probability": 0.5,
                "confidence": "NONE",
                "blend_ratio": 0.0,
                "reasons": [f"데이터 부족 ({self._total_trades}/{MIN_TRADES_FOR_PREDICT}건)"]
            }

        reasons = []

        # ── 1. 조건별 베이지안 승률 ──
        log_odds_sum = 0.0
        cond_count = 0
        base_odds = self._base_win_rate / (1 - self._base_win_rate + 1e-9)

        for cname, cdata in conditions.items():
            score = cdata.get("score", 0) if isinstance(cdata, dict) else 0
            if cname not in self._condition_probs:
                continue

            # 해당 구간의 승률 가져오기
            bin_prob = self._base_win_rate
            for (lo, hi), prob in self._condition_probs[cname].items():
                if lo <= score < hi:
                    bin_prob = prob
                    break

            # 로그 오즈 누적 (나이브 베이즈)
            bin_odds = bin_prob / (1 - bin_prob + 1e-9)
            log_odds_sum += math.log(bin_odds / (base_odds + 1e-9) + 1e-9)
            cond_count += 1

        # 최종 확률 계산
        if cond_count > 0:
            final_log_odds = math.log(base_odds + 1e-9) + log_odds_sum
            bayes_prob = 1.0 / (1.0 + math.exp(-final_log_odds))
            bayes_prob = max(0.05, min(0.95, bayes_prob))
        else:
            bayes_prob = self._base_win_rate

        reasons.append(f"베이지안 승률: {bayes_prob:.0%}")

        # ── 2. 조합 패턴 보너스 ──
        high_conds = sorted([
            cname for cname, cdata in conditions.items()
            if isinstance(cdata, dict) and cdata.get("score", 0) >= 60
        ])

        combo_bonus = 0.0
        combo_count = 0
        for i in range(len(high_conds)):
            for j in range(i + 1, len(high_conds)):
                key = f"{high_conds[i]}+{high_conds[j]}"
                if key in self._combo_patterns:
                    pattern = self._combo_patterns[key]
                    wr = pattern["win_rate"]
                    if wr > 0.6:
                        combo_bonus += (wr - 0.5) * 20
                        reasons.append(f"패턴: {key} 승률{wr:.0%}({pattern['count']}건)")
                    elif wr < 0.4:
                        combo_bonus -= (0.5 - wr) * 20
                        reasons.append(f"⚠ 패턴: {key} 승률{wr:.0%}({pattern['count']}건)")
                    combo_count += 1

        # ── 3. 최종 AI 점수 ──
        ai_score = bayes_prob * 100 + combo_bonus
        ai_score = max(0, min(100, ai_score))

        # 블렌딩 비율 (데이터 양에 비례, 최대 MAX_BLEND_RATIO)
        blend_ratio = min(MAX_BLEND_RATIO,
                          self._total_trades / BLEND_RAMP_TRADES * MAX_BLEND_RATIO)

        # 신뢰도
        if self._total_trades >= 100 and cond_count >= 5:
            confidence = "HIGH"
        elif self._total_trades >= 50:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return {
            "ai_score": round(ai_score, 1),
            "win_probability": round(bayes_prob, 3),
            "confidence": confidence,
            "blend_ratio": round(blend_ratio, 3),
            "reasons": reasons[:5]
        }

    def blend_score(self, user_score: float, conditions: dict) -> dict:
        """
        사용자 점수와 AI 예측을 블렌딩

        반환: {
            "final_score": float,    최종 블렌딩 점수
            "user_score": float,     사용자 조건 점수
            "ai_score": float,       AI 예측 점수
            "blend_ratio": float,    AI 반영 비율
            "prediction": dict,      AI 예측 상세
        }
        """
        pred = self.predict(conditions)
        alpha = pred["blend_ratio"]

        final_score = (1 - alpha) * user_score + alpha * pred["ai_score"]
        final_score = max(0, min(100, final_score))

        return {
            "final_score": round(final_score, 1),
            "user_score": round(user_score, 1),
            "ai_score": pred["ai_score"],
            "blend_ratio": alpha,
            "prediction": pred
        }

    def get_status(self) -> str:
        """현재 AI 모델 상태 문자열"""
        if not self._loaded:
            return f"학습대기({self._total_trades}건)"
        return (f"학습완료({self._total_trades}건, "
                f"기본승률:{self._base_win_rate:.0%}, "
                f"반영:{min(MAX_BLEND_RATIO, self._total_trades/BLEND_RAMP_TRADES*MAX_BLEND_RATIO):.0%})")


# 싱글톤 인스턴스
_predictor = AIPredictor()


def get_predictor() -> AIPredictor:
    """글로벌 AI 예측 인스턴스 반환"""
    if not _predictor._loaded:
        _predictor.load_model()
    return _predictor


def reload_model():
    """모델 재로드 (학습 후 호출)"""
    _predictor.load_model()
