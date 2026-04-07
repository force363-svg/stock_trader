"""
t1532 /stock/market-data 테스트
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

tmcode = "0008"

# t1532 - 모든 엔드포인트
print("=== t1532 테마별종목 ===")
for ep in ["/stock/market-data", "/stock/investinfo", "/stock/sector"]:
    res = requests.post(f"{base}{ep}", headers=hdr("t1532"),
        json={"t1532InBlock": {"tmcode": tmcode}}, timeout=10)
    raw = res.json()
    rows = raw.get("t1532OutBlock", [])
    rsp_cd  = raw.get("rsp_cd","?")
    rsp_msg = raw.get("rsp_msg","")
    # OutBlock 또는 OutBlock1 모두 확인
    rows1 = raw.get("t1532OutBlock1", rows)
    display_rows = rows1 if rows1 else rows
    if res.status_code == 200 and display_rows:
        row = display_rows[0] if isinstance(display_rows, list) else display_rows
        cnt = len(display_rows) if isinstance(display_rows, list) else 1
        key_used = "t1532OutBlock1" if rows1 else "t1532OutBlock"
        print(f"  ✅ {ep} [{key_used}] → {cnt}행")
        print(f"     첫행 키: {list(row.keys())}")
        print(f"     첫행: {row}")
    else:
        print(f"  ✗  {ep} → HTTP {res.status_code} [{rsp_cd}] {rsp_msg}, 응답키: {list(raw.keys())}")
    time.sleep(0.2)

# t1533 - /stock/market-data
print("\n=== t1533 테마별시세 ===")
for ep in ["/stock/market-data", "/stock/investinfo", "/stock/sector"]:
    res = requests.post(f"{base}{ep}", headers=hdr("t1533"),
        json={"t1533InBlock": {"gubun": "0"}}, timeout=10)
    raw = res.json()
    rows = raw.get("t1533OutBlock", [])
    rsp_cd  = raw.get("rsp_cd","?")
    rsp_msg = raw.get("rsp_msg","")
    if res.status_code == 200 and rows:
        row = rows[0] if isinstance(rows, list) else rows
        cnt = len(rows) if isinstance(rows, list) else 1
        print(f"  ✅ {ep} → {cnt}행, 첫행 키: {list(row.keys())}")
        print(f"     첫행: {row}")
    else:
        print(f"  ✗  {ep} → HTTP {res.status_code} [{rsp_cd}] {rsp_msg}")
    time.sleep(0.2)

# t1537 대안 테스트
print("\n=== t1537 대안 테마별종목 ===")
for ep in ["/stock/market-data", "/stock/sector"]:
    res = requests.post(f"{base}{ep}", headers=hdr("t1537"),
        json={"t1537InBlock": {"tmcode": tmcode}}, timeout=10)
    raw = res.json()
    # OutBlock 또는 OutBlock1 확인
    rows  = raw.get("t1537OutBlock", [])
    rows1 = raw.get("t1537OutBlock1", [])
    display = rows1 if rows1 else rows
    rsp_cd  = raw.get("rsp_cd","?")
    rsp_msg = raw.get("rsp_msg","")
    if res.status_code == 200 and display:
        row = display[0] if isinstance(display, list) else display
        cnt = len(display) if isinstance(display, list) else 1
        print(f"  ✅ {ep} → {cnt}행, 첫행 키: {list(row.keys())}")
        print(f"     첫행: {row}")
    else:
        print(f"  ✗  {ep} → HTTP {res.status_code} [{rsp_cd}] {rsp_msg}, 응답키: {list(raw.keys())}")
    time.sleep(0.2)

print("\n완료!")
