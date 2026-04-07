"""
t8425 실시간 코드 → t1532 즉시 호출 (0.5초 딜레이)
실행: python debug_api.py
"""
import requests, time
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

def hdr(tr_cd):
    return {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd"        : tr_cd,
        "tr_cont"      : "N",
        "tr_cont_key"  : "",
    }

# Step 1: t8425로 실시간 tmcode 수신
print("=== Step 1: t8425 실시간 테마 목록 ===")
res = requests.post(f"{base}/stock/sector", headers=hdr("t8425"),
    json={"t8425InBlock": {"gubun": "0"}}, timeout=10)
themes = res.json().get("t8425OutBlock", [])
print(f"수신: {len(themes)}개 테마")
print(f"처음 5개: {[(t['tmcode'], t['tmname'][:10]) for t in themes[:5]]}\n")

time.sleep(0.5)

# Step 2: 받은 코드로 t1532 즉시 호출 (처음 5개만)
print("=== Step 2: t1532 즉시 호출 (실시간 코드 사용) ===")
for t in themes[:5]:
    tmcode = t["tmcode"]
    tmname = t["tmname"]
    time.sleep(0.5)  # 문서 권장 딜레이
    res = requests.post(f"{base}/stock/sector", headers=hdr("t1532"),
        json={"t1532InBlock": {"tmcode": tmcode}}, timeout=10)
    raw = res.json()
    # 전체 응답 키 출력
    print(f"\n[{tmcode}] {tmname[:15]}")
    print(f"  HTTP {res.status_code}, 응답 키: {list(raw.keys())}")
    for k, v in raw.items():
        if k in ("rsp_cd", "rsp_msg"):
            print(f"  {k}: {v}")
        elif isinstance(v, list):
            print(f"  [{k}] {len(v)}행" + (f", 첫행: {v[0]}" if v else " (비어있음)"))
        elif isinstance(v, dict):
            has = any(val for val in v.values() if val)
            print(f"  [{k}] dict {'(데이터있음)' if has else '(빈값)'}: {v}")

print("\n완료!")
