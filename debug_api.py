"""
t1537 올바른 파라미터로 테스트 (전체 테마 등락률)
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

endpoints = ["/stock/sector", "/stock/market-data", "/stock/investinfo"]

# t1537 - 올바른 파라미터 조합 (전체 테마, gubun=0)
bodies = [
    {"t1537InBlock": {"gubun": "0"}},
    {"t1537InBlock": {"gubun": "1"}},
    {"t1537InBlock": {"dummy": ""}},
    {"t1537InBlock": {}},
]

print("=== t1537 전체 테마 등락률 조회 ===")
for ep in endpoints:
    for body in bodies:
        res = requests.post(f"{base}{ep}", headers=hdr("t1537"), json=body, timeout=10)
        raw = res.json()
        rsp_cd  = raw.get("rsp_cd","?")
        rsp_msg = raw.get("rsp_msg","")
        out_keys = [k for k in raw.keys() if "OutBlock" in k]
        has_data = any(raw.get(k) for k in out_keys)
        inb = body.get("t1537InBlock",{})
        if res.status_code == 200 and has_data:
            for k in out_keys:
                rows = raw[k]
                if rows:
                    row = rows[0] if isinstance(rows,list) else rows
                    cnt = len(rows) if isinstance(rows,list) else 1
                    print(f"  ✅ {ep} {inb} [{k}] {cnt}행")
                    print(f"     첫행 키: {list(row.keys())}")
                    print(f"     첫행:   {row}")
        else:
            print(f"  ✗  {ep} {inb} → {res.status_code} [{rsp_cd}] {rsp_msg or '0행'}")
        time.sleep(0.2)

print("\n완료!")
