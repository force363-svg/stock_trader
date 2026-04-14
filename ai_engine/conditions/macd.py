"""
MACD 조건
- 파라미터: engine_config.json defaults.macd 또는 설명의 [fast,slow,signal] 파싱
- 디폴트: [10, 20, 9]
"""
import re
from .base import BaseCondition
from .ma_alignment import _ema
from ._config_helper import load_defaults


def _macd(closes: list, fast=10, slow=20, signal=9):
    """MACD 계산. 최신순 리스트 입력."""
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    if not ema_fast or not ema_slow:
        return [], [], []
    n = min(len(ema_fast), len(ema_slow))
    macd_line = [ema_fast[i] - ema_slow[i] for i in range(n)]
    sig_line  = _ema(macd_line, signal)
    if not sig_line:
        return [], [], []
    m = min(len(macd_line), len(sig_line))
    hist = [macd_line[i] - sig_line[i] for i in range(m)]
    return macd_line[:m], sig_line[:m], hist


def _parse_macd_params(text: str) -> tuple:
    """텍스트에서 MACD 파라미터 파싱. '[10,20,9]' 또는 'MACD(12,26,9)' 등"""
    m = re.search(r'[\[\(](\d+)\s*[,/]\s*(\d+)\s*[,/]\s*(\d+)[\]\)]', text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    defaults = load_defaults()
    params = defaults.get("macd", [10, 20, 9])
    if isinstance(params, list) and len(params) >= 3:
        return int(params[0]), int(params[1]), int(params[2])
    return 10, 20, 9


def _macd_proportional(macd_line, sig_line, price, label):
    """
    MACD 비례가중치 점수.
    - MACD > Signal: 차이 비율로 점수 (골든크로스 직후=60, 강한 확산=90)
    - MACD < Signal: 차이 비율로 감점 (데드크로스=30 이하)
    - MACD 상승 기울기: 기울기 크기로 가점
    Returns: (score, detail_str)
    """
    if len(macd_line) < 2 or len(sig_line) < 1 or price <= 0:
        return None, ""

    diff = macd_line[0] - sig_line[0]
    diff_pct = (diff / price) * 100  # 가격 대비 % 정규화
    slope = macd_line[0] - macd_line[1]
    slope_pct = (slope / price) * 100

    # MACD > Signal 비례점수 (0~60점)
    if diff_pct > 0:
        # 0% → 55, 0.3% → 75, 0.7%+ → 90
        if diff_pct <= 0.3:
            cross_pts = 55.0 + (diff_pct / 0.3) * 20.0  # 55→75
        elif diff_pct <= 0.7:
            cross_pts = 75.0 + ((diff_pct - 0.3) / 0.4) * 15.0  # 75→90
        else:
            cross_pts = 90.0
    else:
        # 데드크로스: 0% → 45, -0.3% → 25, -0.7%+ → 10
        if diff_pct >= -0.3:
            cross_pts = 45.0 + (diff_pct / 0.3) * 20.0  # 45→25
        elif diff_pct >= -0.7:
            cross_pts = 25.0 + ((diff_pct + 0.3) / 0.4) * 15.0  # 25→10
        else:
            cross_pts = 10.0

    # MACD 상승 기울기 보너스 (±15점)
    if slope_pct > 0:
        slope_bonus = min(15.0, slope_pct / 0.2 * 15.0)  # 0.2%에서 만점
    else:
        slope_bonus = max(-15.0, slope_pct / 0.2 * 15.0)

    pts = max(0, min(100, cross_pts + slope_bonus))
    detail = f"{label}MACD({diff_pct:+.2f}%,기울기{slope_pct:+.2f}%)={pts:.0f}"
    return pts, detail


class MACDCondition(BaseCondition):
    name = "MACD_상승"

    def score(self, code: str, data: dict) -> tuple:
        daily = data.get("daily", [])
        min60 = data.get("min60", [])
        fast, slow, sig = _parse_macd_params("")
        details = []

        # 현재가 (정규화 기준)
        price_data = data.get("price", {})
        cur_price = float(price_data.get("price", 0))
        if cur_price <= 0 and daily:
            cur_price = float(daily[0].get("close", 0))
        if cur_price <= 0 and min60:
            cur_price = float(min60[0].get("close", 0))

        # 일봉 MACD
        d_pts = None
        if len(daily) >= 30:
            d_closes = [d["close"] for d in daily]
            d_macd, d_sig, _ = _macd(d_closes, fast, slow, sig)
            d_pts, d_detail = _macd_proportional(d_macd, d_sig, cur_price, "일봉")
            if d_detail:
                details.append(d_detail)

        # 60분봉 MACD
        m_pts = None
        if len(min60) >= 30:
            m_closes = [d["close"] for d in min60]
            m_macd, m_sig, _ = _macd(m_closes, fast, slow, sig)
            m_pts, m_detail = _macd_proportional(m_macd, m_sig, cur_price, "60분")
            if m_detail:
                details.append(m_detail)

        if d_pts is not None and m_pts is not None:
            pts = d_pts * 0.4 + m_pts * 0.6  # 60분봉 가중
        elif m_pts is not None:
            pts = m_pts
        elif d_pts is not None:
            pts = d_pts
        else:
            return 0.0, "데이터 부족"

        return pts, ", ".join(details)

    def check_screening(self, code: str, data: dict,
                        enabled_names: set = None,
                        scr_cfg: list = None) -> bool:
        """MACD 스크리닝 — 파라미터를 설명/defaults에서 자동 파싱"""
        daily = data.get("daily", [])
        min60 = data.get("min60", [])

        if not enabled_names:
            s, _ = self.score(code, data)
            return s >= 50

        # 설명에서 파라미터 파싱 시도
        desc_text = ""
        if scr_cfg:
            for cfg in scr_cfg:
                if "MACD" in cfg.get("name", "") or "macd" in cfg.get("name", ""):
                    desc_text = cfg.get("description", "")
                    break
        fast, slow, sig = _parse_macd_params(desc_text)

        # 일봉 MACD
        d_macd, d_sig = [], []
        if len(daily) >= 30:
            d_closes = [d["close"] for d in daily]
            d_macd, d_sig, _ = _macd(d_closes, fast, slow, sig)

        # 60분봉 MACD
        m_macd, m_sig = [], []
        if len(min60) >= 30:
            m_closes = [d["close"] for d in min60]
            m_macd, m_sig, _ = _macd(m_closes, fast, slow, sig)

        for name in enabled_names:
            if "MACD" not in name and "macd" not in name:
                continue
            if ">" in name and ("Signal" in name or "signal" in name or "시그널" in name):
                ok = False
                if len(d_macd) >= 1 and len(d_sig) >= 1 and d_macd[0] > d_sig[0]:
                    ok = True
                if len(m_macd) >= 1 and len(m_sig) >= 1 and m_macd[0] > m_sig[0]:
                    ok = True
                if not ok:
                    return False
            elif "상승" in name:
                ok = False
                if len(d_macd) >= 2 and d_macd[0] > d_macd[1]:
                    ok = True
                if len(m_macd) >= 2 and m_macd[0] > m_macd[1]:
                    ok = True
                if not ok:
                    return False
        return True


class Min60MACDSellCondition(BaseCondition):
    """60분봉 MACD 매도 신호 (데드크로스=고점수)"""
    name = "60분봉_MACD_매도"

    def score(self, code: str, data: dict) -> tuple:
        min60 = data.get("min60", [])
        if len(min60) < 30:
            return 10.0, "60분봉 데이터 부족"

        fast, slow, sig = _parse_macd_params("")
        closes = [d["close"] for d in min60]
        price = closes[0]
        if price <= 0:
            return 10.0, "가격 없음"

        macd_line, sig_line, hist = _macd(closes, fast, slow, sig)
        if len(macd_line) < 2 or len(sig_line) < 1:
            return 10.0, "MACD 계산 실패"

        diff = macd_line[0] - sig_line[0]
        diff_pct = (diff / price) * 100
        slope = macd_line[0] - macd_line[1]
        slope_pct = (slope / price) * 100

        # 매도 관점: 데드크로스(diff < 0)일수록 고점수
        if diff_pct < 0:
            # 데드크로스: 강할수록 고점수
            pts = min(95.0, 60.0 + abs(diff_pct) / 0.5 * 35.0)
        elif diff_pct < 0.1:
            # 거의 교차 직전
            pts = 50.0
        else:
            # 골든크로스 유지: 매도 신호 약함
            pts = max(10.0, 40.0 - diff_pct / 0.5 * 30.0)

        # 기울기 하락이면 가산
        if slope_pct < 0:
            pts = min(95.0, pts + abs(slope_pct) / 0.2 * 10.0)

        return pts, f"60분MACD({diff_pct:+.2f}%,기울기{slope_pct:+.2f}%)"
