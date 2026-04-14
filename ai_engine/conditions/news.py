"""
뉴스 조건 계산기
- 네이버 금융 모바일 API로 종목 뉴스 조회
- 뉴스 건수 + 키워드 감성 분석
"""
import re
import time
import requests
from .base import BaseCondition


# ── 감성 키워드 사전 ──
_POSITIVE_KEYWORDS = [
    "수주", "계약", "흑자", "실적", "매출", "성장", "신고가", "상향",
    "호실적", "턴어라운드", "증가", "상승", "돌파", "최대", "사상최대",
    "인수", "합병", "투자", "확대", "개발", "승인", "특허", "수출",
    "배당", "자사주", "매입", "호재", "급등", "강세", "목표가",
]

_NEGATIVE_KEYWORDS = [
    "적자", "하락", "급락", "폭락", "하향", "감소", "손실", "부진",
    "횡령", "배임", "수사", "기소", "벌금", "제재", "리콜", "결함",
    "상폐", "상장폐지", "감자", "유상증자", "공매도", "반대매매",
    "파산", "부도", "워크아웃", "매물", "약세", "악재", "위험",
]

# 뉴스 캐시 (종목코드 → (시각, 결과))
_news_cache = {}
_CACHE_TTL = 300  # 5분


def _fetch_news(code: str, count: int = 20) -> list:
    """
    네이버 금융 모바일 API로 종목 뉴스 조회
    반환: [{"title": str, "datetime": str, "officeName": str}, ...]
    """
    # 캐시 확인
    cached = _news_cache.get(code)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return cached[1]

    try:
        url = f"https://m.stock.naver.com/api/news/stock/{code}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code != 200:
            print(f"[뉴스] HTTP {res.status_code} for {code}")
            return []

        data = res.json()

        # 디버그: 첫 호출 시 응답 구조 기록
        if not _news_cache:
            try:
                import os, sys, json as _json
                dbg_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                if getattr(sys, 'frozen', False):
                    dbg_base = os.path.dirname(os.path.dirname(sys.executable))
                with open(os.path.join(dbg_base, "debug_news.txt"), "w", encoding="utf-8") as f:
                    f.write(f"code: {code}\n")
                    f.write(f"type: {type(data).__name__}\n")
                    f.write(f"response: {_json.dumps(data, ensure_ascii=False)[:3000]}\n")
            except:
                pass

        result = []
        if isinstance(data, list):
            # 기존 형식: [{items: [...]}, ...]
            for group in data[:count]:
                items = group.get("items", []) if isinstance(group, dict) else []
                for item in items:
                    result.append({
                        "title": item.get("title", ""),
                        "datetime": item.get("datetime", ""),
                        "office": item.get("officeName", ""),
                    })
        elif isinstance(data, dict):
            # 새 형식 대비: {items: [...]} 또는 {news: [...]}
            items = data.get("items", data.get("news", data.get("result", [])))
            if isinstance(items, list):
                for item in items[:count]:
                    title = item.get("title", item.get("tit", ""))
                    result.append({
                        "title": title,
                        "datetime": item.get("datetime", item.get("dt", "")),
                        "office": item.get("officeName", item.get("office", "")),
                    })

        # 캐시 저장
        _news_cache[code] = (time.time(), result)
        return result

    except Exception as e:
        print(f"[뉴스] 조회 오류({code}): {e}")
        return []


def _analyze_sentiment(titles: list) -> dict:
    """
    뉴스 제목 감성 분석
    반환: {"positive": int, "negative": int, "neutral": int,
           "pos_keywords": list, "neg_keywords": list}
    """
    pos_count = 0
    neg_count = 0
    pos_keywords = []
    neg_keywords = []

    for title in titles:
        found_pos = [kw for kw in _POSITIVE_KEYWORDS if kw in title]
        found_neg = [kw for kw in _NEGATIVE_KEYWORDS if kw in title]

        if found_pos:
            pos_count += 1
            pos_keywords.extend(found_pos)
        if found_neg:
            neg_count += 1
            neg_keywords.extend(found_neg)

    neutral = len(titles) - pos_count - neg_count
    # 중복 제거
    pos_keywords = list(dict.fromkeys(pos_keywords))
    neg_keywords = list(dict.fromkeys(neg_keywords))

    return {
        "positive": pos_count,
        "negative": neg_count,
        "neutral": max(0, neutral),
        "pos_keywords": pos_keywords[:5],
        "neg_keywords": neg_keywords[:5],
    }


def prefetch_news(code: str):
    """수집기에서 호출 — 뉴스를 미리 캐시에 저장"""
    from ..data.cache import get_cache
    cache = get_cache()
    cached = cache.get(f"news_{code}")
    if cached:
        return  # 이미 캐시에 있음
    articles = _fetch_news(code)
    if articles:
        titles = [a["title"] for a in articles]
        sentiment = _analyze_sentiment(titles)
        cache.set(f"news_{code}", {
            "count": len(articles),
            "sentiment": sentiment,
        }, ttl_seconds=300)  # 5분 TTL


class NewsCondition(BaseCondition):
    """뉴스 건수 + 감성 분석 — 캐시에서만 읽기"""
    name = "뉴스"

    def score(self, code: str, data: dict) -> tuple:
        # 1차: 메인 캐시에서 읽기 (수집기가 미리 저장)
        from ..data.cache import get_cache
        cache = get_cache()
        cached_news = cache.get(f"news_{code}")
        if cached_news:
            return self._score_from_cache(cached_news)

        # 2차: 로컬 뉴스 캐시 (호환용)
        articles = _fetch_news(code)

        if not articles:
            return 50.0, "뉴스 없음"

        titles = [a["title"] for a in articles]
        count = len(titles)
        sentiment = _analyze_sentiment(titles)

        pos = sentiment["positive"]
        neg = sentiment["negative"]
        pos_kw = sentiment["pos_keywords"]
        neg_kw = sentiment["neg_keywords"]

        # 점수 계산
        # 기본: 뉴스 건수 (관심도)
        if count >= 10:
            base_pts = 70.0
        elif count >= 5:
            base_pts = 55.0
        else:
            base_pts = 40.0

        # 감성 가감
        if pos > neg:
            sentiment_adj = min(20, (pos - neg) * 5)
            detail_mood = "긍정"
        elif neg > pos:
            sentiment_adj = -min(20, (neg - pos) * 5)
            detail_mood = "부정"
        else:
            sentiment_adj = 0
            detail_mood = "중립"

        pts = max(0, min(100, base_pts + sentiment_adj))

        # 상세 정보
        detail = f"뉴스 {count}건 ({detail_mood}: +{pos}/-{neg})"
        if pos_kw:
            detail += f" [{','.join(pos_kw[:3])}]"
        if neg_kw:
            detail += f" [{','.join(neg_kw[:3])}]"

        return pts, detail

    def _score_from_cache(self, cached_news: dict) -> tuple:
        """캐시된 뉴스 데이터로 점수 계산"""
        count = cached_news.get("count", 0)
        sentiment = cached_news.get("sentiment", {})
        pos = sentiment.get("positive", 0)
        neg = sentiment.get("negative", 0)
        pos_kw = sentiment.get("pos_keywords", [])
        neg_kw = sentiment.get("neg_keywords", [])

        if count >= 10:
            base_pts = 70.0
        elif count >= 5:
            base_pts = 55.0
        else:
            base_pts = 40.0

        if pos > neg:
            sentiment_adj = min(20, (pos - neg) * 5)
            detail_mood = "긍정"
        elif neg > pos:
            sentiment_adj = -min(20, (neg - pos) * 5)
            detail_mood = "부정"
        else:
            sentiment_adj = 0
            detail_mood = "중립"

        pts = max(0, min(100, base_pts + sentiment_adj))
        detail = f"뉴스 {count}건 ({detail_mood}: +{pos}/-{neg})"
        if pos_kw:
            detail += f" [{','.join(pos_kw[:3])}]"
        if neg_kw:
            detail += f" [{','.join(neg_kw[:3])}]"
        return pts, detail
