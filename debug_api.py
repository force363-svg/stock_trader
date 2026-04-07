"""
t1537 날짜/시간 파라미터 추가 테스트
실행: python debug_api.py
"""
import requests, time
from datetime import datetime
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
today = datetime.now().strftime("%Y%m%d")
now_time = datetime.now().strftime("%H%M%S")
print(f"토큰 OK, 오늘={today}, 시간={now_time}\n")

def hdr(tr_cd, cont="N"):
    return {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd"        : tr_cd,
        "tr_cont"      : cont,
        "tr_cont_key"  : "",
    }

# t1537 다양한 날짜/구분 조합
bodies = [
    {"t1537InBlock": {"gubun": "0", "date": today}},
    {"t1537InBlock": {"gubun": "0", "date": today, "time": now_time}},
    {"t1537InBlock": {"date": today}},
    {"t1537InBlock": {"date": today, "tmcode": ""}},
    {"t1537InBlock": {"gubun": "0", "upcode": ""}},
    {"t1537InBlock": {"gubun": "0", "upcode": "001"}},
]

print("=== t1537 /stock/sector 파라미터 조합 ===")
for body in bodies:
    res = requests.post(f"{base}/stock/sector", headers=hdr("t1537"),
        json=body, timeout=10)
    raw = res.json()
    rows = raw.get("t1537OutBlock", [])
    rsp_cd = raw.get("rsp_cd","?")
    inb = body.get("t1537InBlock",{})
    if isinstance(rows, list) and rows:
        row = rows[0]
        has_data = any(v for v in row.values() if v)
        print(f"  {'✅' if has_data else '⚠ '} {inb}")
        print(f"     {len(rows)}행, 첫행: {row}")
    elif isinstance(rows, dict) and any(rows.values()):
        print(f"  ✅ {inb} dict: {rows}")
    else:
        print(f"  ✗  {inb} → [{rsp_cd}] 0행 또는 빈값")
    time.sleep(0.3)

# 연속조회(tr_cont=Y) 시도
print("\n=== t1537 연속조회 tr_cont=Y ===")
res = requests.post(f"{base}/stock/sector",
    headers=hdr("t1537", "Y"),
    json={"t1537InBlock": {"gubun": "0"}}, timeout=10)
raw = res.json()
rows = raw.get("t1537OutBlock", [])
print(f"HTTP {res.status_code}, 행수: {len(rows) if isinstance(rows,list) else 1}")
if rows:
    print(f"첫행: {rows[0] if isinstance(rows,list) else rows}")

print("\n완료!")
