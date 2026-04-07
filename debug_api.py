"""
t1532 원시 응답 확인 + t8425 연속조회(tr_cont=Y) 테스트
실행: python debug_api.py
"""
import json, requests, time
from config import load_config

config = load_config()
app_key    = config["api"].get("ls_app_key", "")
app_secret = config["api"].get("ls_app_secret", "")
base = "https://openapi.ls-sec.co.kr:8080"

res = requests.post(f"{base}/oauth2/token",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={"grant_type":"client_credentials","appkey":app_key,"appsecretkey":app_secret,"scope":"oob"},
    timeout=10)
token = res.json().get("access_token","")
print("토큰 OK\n")

def hdr(tr_cd, cont="N"):
    return {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd"        : tr_cd,
        "tr_cont"      : cont,
    }

# ── 1. t1532 전체 응답 키 확인 ──
print("=== t1532 원시 응답 ===")
res = requests.post(f"{base}/stock/sector",
    headers=hdr("t1532"),
    json={"t1532InBlock": {"tmcode": "0008"}}, timeout=10)
raw = res.json()
print(f"HTTP: {res.status_code}")
print(f"모든 키: {list(raw.keys())}")
for k, v in raw.items():
    if isinstance(v, list):
        print(f"  [{k}] 리스트 {len(v)}행" + (f", 첫행: {v[0]}" if v else ""))
    else:
        print(f"  [{k}] = {v}")

time.sleep(0.3)

# ── 2. t8425 첫 행에 diff 필드 있는지 다시 확인 ──
print("\n=== t8425 첫 3행 전체 필드 ===")
res = requests.post(f"{base}/stock/sector",
    headers=hdr("t8425"),
    json={"t8425InBlock": {"gubun": "0"}}, timeout=10)
rows = res.json().get("t8425OutBlock", [])
for row in rows[:3]:
    print(f"  {row}")

time.sleep(0.3)

# ── 3. t8425 연속조회 (tr_cont=Y) 로 추가 필드 있는지 확인 ──
print("\n=== t8425 연속조회 헤더(tr_cont=Y) ===")
res = requests.post(f"{base}/stock/sector",
    headers=hdr("t8425", "Y"),
    json={"t8425InBlock": {"gubun": "0"}}, timeout=10)
raw2 = res.json()
rows2 = raw2.get("t8425OutBlock", [])
print(f"HTTP: {res.status_code}, 행수: {len(rows2)}")
if rows2:
    print(f"첫행 키: {list(rows2[0].keys())}")
    print(f"첫행: {rows2[0]}")

time.sleep(0.3)

# ── 4. t1533 /stock/sector 전체 응답 확인 ──
print("\n=== t1533 /stock/sector 전체 응답 ===")
res = requests.post(f"{base}/stock/sector",
    headers=hdr("t1533"),
    json={"t1533InBlock": {"gubun": "0"}}, timeout=10)
raw3 = res.json()
print(f"모든 키: {list(raw3.keys())}")
for k, v in raw3.items():
    if isinstance(v, list):
        print(f"  [{k}] 리스트 {len(v)}행" + (f", 첫행: {v[0]}" if v else ""))
    elif isinstance(v, dict):
        print(f"  [{k}] dict: {v}")
    else:
        print(f"  [{k}] = {v}")

print("\n완료!")
