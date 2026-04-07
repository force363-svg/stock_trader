"""
t1511 유효한 엔드포인트 탐색
실행: python debug_api.py
"""
import requests
from config import load_config

config = load_config()
app_key    = config["api"].get("ls_app_key", "")
app_secret = config["api"].get("ls_app_secret", "")
base = "https://openapi.ls-sec.co.kr:8080"

res = requests.post(f"{base}/oauth2/token",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={"grant_type":"client_credentials","appkey":app_key,"appsecretkey":app_secret,"scope":"oob"},
    timeout=10)
token = res.json().get("access_token", "")
print("토큰 OK\n")

def try_t1511(endpoint, body_key, code_key, code_val):
    headers = {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd"        : "t1511",
        "tr_cont"      : "N",
    }
    body = {body_key: {code_key: code_val}}
    try:
        res = requests.post(f"{base}{endpoint}", headers=headers, json=body, timeout=10)
        raw = res.json()
        rsp = raw.get("rsp_cd", "")
        if res.status_code == 200 and "t1511OutBlock" in raw:
            out = raw["t1511OutBlock"]
            row = out[0] if isinstance(out, list) else out
            print(f"✅ endpoint={endpoint} body={body_key} {code_key}={code_val}")
            print(f"   필드: {list(row.keys())}")
            print(f"   값:   {row}")
            return True
        else:
            msg = raw.get("rsp_msg", raw.get("error", ""))
            print(f"   {endpoint} [{code_key}={code_val}] → {res.status_code} [{rsp}] {msg}")
    except Exception as e:
        print(f"   {endpoint} 오류: {e}")
    return False

endpoints = [
    "/stock/market-data",
    "/stock/sector",
    "/indextic/market-data",
    "/index/market-data",
    "/stock/index",
    "/index",
    "/market/index",
]
body_variants = [
    ("t1511InBlock", "upcode", "001"),
    ("t1511InBlock", "shcode", "001"),
    ("t1511InBlock", "upcode", "0001"),
    ("t1511InBlock", "upcode", "U001"),
]

found = False
for ep in endpoints:
    for bk, ck, cv in body_variants:
        if try_t1511(ep, bk, ck, cv):
            found = True
            break
    if found:
        break

if not found:
    print("\n모든 조합 실패 - t1511 지원 안될 수 있음")
    # 대안: t1102로 KOSPI ETF (069500=KODEX200) 지수 대체 조회
    print("\n대안 확인: t1102로 KODEX200(069500) 조회")
    headers = {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd"        : "t1102",
        "tr_cont"      : "N",
    }
    res = requests.post(f"{base}/stock/market-data", headers=headers,
        json={"t1102InBlock": {"shcode": "069500"}}, timeout=10)
    raw = res.json()
    out = raw.get("t1102OutBlock", {})
    if out:
        row = out[0] if isinstance(out, list) else out
        print(f"t1102 필드: {list(row.keys())}")
        print(f"t1102 값:   {row}")

print("\n완료!")
