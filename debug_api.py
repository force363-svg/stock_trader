"""
LS API 진단 스크립트 - 업종지수/테마 TR 탐색
실행: python debug_api.py
"""
import json
import requests
from config import load_config

config = load_config()
app_key    = config["api"].get("ls_app_key", "")
app_secret = config["api"].get("ls_app_secret", "")

if not app_key or not app_secret:
    print("실전 API 키 없음")
    exit()

base = "https://openapi.ls-sec.co.kr:8080"

# 토큰 발급
res = requests.post(f"{base}/oauth2/token",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={"grant_type":"client_credentials","appkey":app_key,"appsecretkey":app_secret,"scope":"oob"},
    timeout=10)
token = res.json().get("access_token", "")
if not token:
    print("토큰 실패:", res.json())
    exit()
print("토큰 OK\n")

def test_tr(desc, tr_cd, endpoint, body):
    print(f"{'─'*50}")
    print(f"[{tr_cd}] {desc}")
    print(f"  endpoint: {endpoint}")
    headers = {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd"        : tr_cd,
        "tr_cont"      : "N",
    }
    try:
        res = requests.post(f"{base}{endpoint}", headers=headers, json=body, timeout=10)
        print(f"  HTTP: {res.status_code}")
        if res.status_code == 200:
            raw = res.json()
            print(f"  응답 키: {list(raw.keys())}")
            for k, v in raw.items():
                if k in ("rsp_cd","rsp_msg"):
                    print(f"  {k}: {v}")
                elif isinstance(v, list):
                    print(f"  [{k}] 리스트 {len(v)}행")
                    if v:
                        print(f"    첫행 키: {list(v[0].keys())}")
                        print(f"    첫행 값: {v[0]}")
                elif isinstance(v, dict):
                    print(f"  [{k}] = {v}")
            # json 저장
            fname = f"debug_{tr_cd}.json"
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False, indent=2)
            print(f"  → 저장: {fname}")
        else:
            print(f"  응답: {res.text[:300]}")
    except Exception as e:
        print(f"  오류: {e}")
    print()

# ── 업종지수 후보 TR들 ──
test_tr("업종현재가(단일)", "t1521",
    "/stock/sector",
    {"t1521InBlock": {"upcode": "001"}})  # 001=종합

test_tr("업종현재가(단일) - shcode방식", "t1511",
    "/stock/market-data",
    {"t1511InBlock": {"shcode": "001"}})

test_tr("업종현재가(단일) - /stock/index", "t1511",
    "/stock/index",
    {"t1511InBlock": {"shcode": "001"}})

test_tr("전업종현재가 t8424", "t8424",
    "/stock/sector",
    {"t8424InBlock": {"gubun": "0"}})

test_tr("전업종현재가 t8424 - market-data", "t8424",
    "/stock/market-data",
    {"t8424InBlock": {"gubun": "0"}})

test_tr("KOSPI지수 t1200", "t1200",
    "/stock/market-data",
    {"t1200InBlock": {"shcode": "001"}})

test_tr("업종지수 t1532", "t1532",
    "/stock/sector",
    {"t1532InBlock": {"upcode": "001", "gubun": "1"}})

# ── 테마(t8425) 첫 5행 상세 확인 ──
print("="*50)
print("[t8425] 테마 데이터 전체 필드 재확인")
headers = {
    "Content-Type" : "application/json; charset=utf-8",
    "authorization": f"Bearer {token}",
    "tr_cd"        : "t8425",
    "tr_cont"      : "N",
}
res = requests.post(f"{base}/stock/sector", headers=headers,
    json={"t8425InBlock": {"gubun": "0"}}, timeout=10)
raw = res.json()
rows = raw.get("t8425OutBlock", [])
print(f"전체 {len(rows)}행, 첫 5행:")
for i, row in enumerate(rows[:5]):
    print(f"  [{i}] {row}")

print("\n완료!")
