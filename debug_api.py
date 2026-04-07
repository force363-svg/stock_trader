"""
t1533 엔드포인트 탐색 + /stock/investinfo 가능한 TR 확인
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

def try_tr(tr_cd, endpoint, body):
    headers = {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd"        : tr_cd,
        "tr_cont"      : "N",
    }
    res = requests.post(f"{base}{endpoint}", headers=headers, json=body, timeout=10)
    raw = res.json()
    out_key = f"{tr_cd}OutBlock"
    rows = raw.get(out_key, [])
    rsp_cd  = raw.get("rsp_cd","?")
    rsp_msg = raw.get("rsp_msg","")
    if res.status_code == 200 and rows:
        row = rows[0] if isinstance(rows, list) else rows
        cnt = len(rows) if isinstance(rows, list) else 1
        print(f"  ✅ {tr_cd} {endpoint} → {cnt}행")
        print(f"     첫행 키: {list(row.keys())}")
        print(f"     첫행 값: {dict(list(row.items())[:5])}")
        return True
    else:
        print(f"  ✗  {tr_cd} {endpoint} → HTTP {res.status_code} [{rsp_cd}] {rsp_msg}")
        return False

endpoints = [
    "/stock/investinfo",
    "/stock/sector",
    "/stock/market-data",
    "/indtp/market-data",
]

# t1533 전 엔드포인트 테스트
print("=== t1533 테마별시세 ===")
for ep in endpoints:
    try_tr("t1533", ep, {"t1533InBlock": {"gubun": "0"}})
    time.sleep(0.2)

print()
print("=== t1532 테마별종목 (tmcode=0008) ===")
for ep in ["/stock/investinfo", "/stock/sector"]:
    try_tr("t1532", ep, {"t1532InBlock": {"tmcode": "0008"}})
    time.sleep(0.2)

print()
print("=== /stock/investinfo 에서 되는 TR 탐색 ===")
test_trs = [
    ("t8430", {"t8430InBlock": {"gubun": "0"}}),
    ("t8440", {"t8440InBlock": {"gubun": "0"}}),
    ("t1530", {"t1530InBlock": {"tmcode": "0008"}}),
    ("t1531", {"t1531InBlock": {"tmcode": "0008"}}),
    ("t1534", {"t1534InBlock": {"tmcode": "0008"}}),
    ("t1535", {"t1535InBlock": {"tmcode": "0008"}}),
]
for tr, body in test_trs:
    try_tr(tr, "/stock/investinfo", body)
    time.sleep(0.2)

print("\n완료!")
