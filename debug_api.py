"""
LS API 진단 스크립트 - t8425 업종지수 원시 응답 확인
실행: python debug_api.py
결과: debug_output.txt 로 저장
"""
import json
import requests
from config import load_config

config = load_config()

# 실전/모의 둘 다 시도
for mode in ["real", "mock"]:
    print(f"\n{'='*50}")
    print(f"  모드: {mode}")
    print(f"{'='*50}")

    if mode == "mock":
        app_key    = config["api"].get("ls_mock_key", "")
        app_secret = config["api"].get("ls_mock_secret", "")
    else:
        app_key    = config["api"].get("ls_app_key", "")
        app_secret = config["api"].get("ls_app_secret", "")

    if not app_key or not app_secret:
        print(f"[{mode}] 키 없음 - 건너뜀")
        continue

    base = "https://openapi.ls-sec.co.kr:8080"

    # 1. 토큰 발급
    res = requests.post(f"{base}/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type":"client_credentials","appkey":app_key,"appsecretkey":app_secret,"scope":"oob"},
        timeout=10)
    token_data = res.json()
    token = token_data.get("access_token", "")
    if not token:
        print(f"[{mode}] 토큰 발급 실패: {token_data}")
        continue
    print(f"[{mode}] 토큰 OK")

    headers = {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cont"      : "N",
    }

    # 2. t8425 - 전업종지수
    print(f"\n--- t8425 (전업종지수) ---")
    headers["tr_cd"] = "t8425"
    res = requests.post(f"{base}/stock/sector",
        headers=headers,
        json={"t8425InBlock": {"gubun": "0"}},
        timeout=10)
    print(f"HTTP: {res.status_code}")
    try:
        raw = res.json()
        print(f"응답 키: {list(raw.keys())}")
        # 각 키별 타입과 미리보기
        for k, v in raw.items():
            if isinstance(v, list):
                print(f"  [{k}] 리스트 {len(v)}행")
                if v:
                    print(f"    첫행 키: {list(v[0].keys())}")
                    print(f"    첫행 값: {v[0]}")
            elif isinstance(v, dict):
                print(f"  [{k}] dict: {v}")
            else:
                print(f"  [{k}] = {v}")
        # 전체 응답 파일 저장
        with open(f"debug_t8425_{mode}.json", "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        print(f"→ 전체 응답 저장: debug_t8425_{mode}.json")
    except Exception as e:
        print(f"파싱 오류: {e}")
        print(f"원본: {res.text[:500]}")

    # 3. t1511 - KOSPI 지수
    print(f"\n--- t1511 (KOSPI 지수) ---")
    headers["tr_cd"] = "t1511"
    for shcode, name in [("001","KOSPI"), ("101","KOSDAQ")]:
        res = requests.post(f"{base}/index/market-data",
            headers=headers,
            json={"t1511InBlock": {"shcode": shcode}},
            timeout=10)
        print(f"{name}({shcode}) HTTP: {res.status_code}")
        try:
            raw = res.json()
            print(f"  키: {list(raw.keys())}")
            out = raw.get("t1511OutBlock", {})
            if out:
                print(f"  데이터: {out}")
            else:
                print(f"  전체: {raw}")
        except Exception as e:
            print(f"  오류: {e} / {res.text[:200]}")

print("\n완료!")
