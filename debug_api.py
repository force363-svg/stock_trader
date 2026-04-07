"""
t1511 응답 필드 정확히 확인
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

headers = {
    "Content-Type" : "application/json; charset=utf-8",
    "authorization": f"Bearer {token}",
    "tr_cd"        : "t1511",
    "tr_cont"      : "N",
}

# KOSPI 종합만 조회해서 전체 필드 출력
res = requests.post(f"{base}/indextic/market-data",
    headers=headers,
    json={"t1511InBlock": {"upcode": "001"}},
    timeout=10)

print(f"HTTP: {res.status_code}")
raw = res.json()
print(f"응답 키: {list(raw.keys())}")

out = raw.get("t1511OutBlock", {})
print(f"\nt1511OutBlock 타입: {type(out)}")

row = out[0] if isinstance(out, list) else out
print(f"\n모든 필드 목록:")
for k, v in row.items():
    print(f"  {k:30s} = {v}")
