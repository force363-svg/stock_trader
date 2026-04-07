"""
t8425 엔드포인트/바디 탐색
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

def test(endpoint, body):
    headers = {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd"        : "t8425",
        "tr_cont"      : "N",
    }
    res = requests.post(f"{base}{endpoint}", headers=headers, json=body, timeout=10)
    raw = res.json()
    rows = raw.get("t8425OutBlock", [])
    rsp  = raw.get("rsp_cd","?")
    rsp_msg = raw.get("rsp_msg","")
    print(f"  {endpoint} body={body}")
    print(f"  HTTP {res.status_code} [{rsp}] {rsp_msg}")
    if rows:
        row = rows[0] if isinstance(rows, list) else rows
        print(f"  ✅ {len(rows) if isinstance(rows,list) else 1}행, 첫행 키: {list(row.keys())}")
        print(f"  첫행: {row}")
    else:
        print(f"  응답키: {list(raw.keys())}")
    print()

# 기존에 작동했던 방식
test("/stock/sector",     {"t8425InBlock": {"gubun": "0"}})

# 문서 기반 새 방식
test("/stock/investinfo", {"t8425InBlock": {"dummy": ""}})
test("/stock/investinfo", {"t8425InBlock": {"gubun": "0"}})
test("/stock/investinfo", {"t8425InBlock": {}})

# 다른 엔드포인트 시도
test("/stock/market-data",{"t8425InBlock": {"dummy": ""}})

print("완료!")
