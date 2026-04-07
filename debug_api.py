"""
t1511 + t8424 응답 필드 확인 (/indtp/market-data)
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

def call(tr_cd, body):
    headers = {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd"        : tr_cd,
        "tr_cont"      : "N",
    }
    res = requests.post(f"{base}/indtp/market-data", headers=headers, json=body, timeout=10)
    print(f"[{tr_cd}] HTTP {res.status_code}")
    raw = res.json()
    out_key = f"{tr_cd}OutBlock"
    out = raw.get(out_key, {})
    row = out[0] if isinstance(out, list) else out
    if row:
        print(f"  필드: {list(row.keys())}")
        print(f"  값:   {row}")
    else:
        print(f"  응답: {raw}")
    print()

# t1511 - 업종현재가 (KOSPI종합)
call("t1511", {"t1511InBlock": {"upcode": "001"}})

# t1511 - KOSDAQ종합
call("t1511", {"t1511InBlock": {"upcode": "301"}})

# t8424 - 전체업종
call("t8424", {"t8424InBlock": {"gubun": "0"}})

print("완료!")
