"""
t1511 전체 필드 파일 저장
실행: python debug_api.py
결과: debug_t1511.txt 확인
"""
import json
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
print("토큰 OK")

headers = {
    "Content-Type" : "application/json; charset=utf-8",
    "authorization": f"Bearer {token}",
    "tr_cd"        : "t1511",
    "tr_cont"      : "N",
}

# KOSPI 종합 (001) 조회
res = requests.post(f"{base}/indtp/market-data", headers=headers,
    json={"t1511InBlock": {"upcode": "001"}}, timeout=10)
raw = res.json()
out = raw.get("t1511OutBlock", {})
row = out[0] if isinstance(out, list) else out

# 파일로 저장 (잘리지 않게)
with open("debug_t1511.txt", "w", encoding="utf-8") as f:
    f.write("=== t1511OutBlock 전체 필드 (KOSPI 001) ===\n\n")
    for k, v in row.items():
        f.write(f"  {k:30s} = {repr(v)}\n")

print("→ debug_t1511.txt 저장 완료")
print("\n전체 필드:")
for k, v in row.items():
    print(f"  {k:30s} = {v}")
