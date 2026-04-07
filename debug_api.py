"""
t1532/t1533 정확한 엔드포인트 탐색
[주식] 투자정보 구독 확인 → 엔드포인트 경로가 다를 가능성
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

# 투자정보 관련 가능한 모든 엔드포인트
endpoints = [
    "/stock/investinfo",
    "/stock/invest",
    "/stock/info",
    "/stock/theme",
    "/stock/themes",
    "/stock/invest-info",
    "/stock/themeinfo",
    "/stock/market-data",
    "/stock/sector",
]

print("=== t1532 엔드포인트 탐색 ===")
for ep in endpoints:
    try:
        res = requests.post(f"{base}{ep}", headers=hdr("t1532"),
            json={"t1532InBlock": {"tmcode": "0030"}}, timeout=10)  # 0030=조선
        raw = res.json()
        rsp_cd  = raw.get("rsp_cd","?")
        rsp_msg = raw.get("rsp_msg","")
        all_keys = list(raw.keys())
        # OutBlock 계열 키 찾기
        out_keys = [k for k in all_keys if "OutBlock" in k or "outblock" in k.lower()]
        has_data = any(raw.get(k) for k in out_keys)
        if res.status_code == 200:
            print(f"  200 {ep} [{rsp_cd}] {rsp_msg}")
            print(f"      키: {all_keys}, OutBlock키: {out_keys}, 데이터있음: {has_data}")
            if has_data:
                for k in out_keys:
                    rows = raw[k]
                    if rows:
                        row = rows[0] if isinstance(rows,list) else rows
                        print(f"      ✅ [{k}] {len(rows) if isinstance(rows,list) else 1}행, 첫행: {row}")
        else:
            print(f"  {res.status_code} {ep} [{rsp_cd}] {rsp_msg}")
    except Exception as e:
        print(f"  ERR {ep}: {e}")
    time.sleep(0.2)

print()
print("=== t1533 엔드포인트 탐색 ===")
for ep in endpoints:
    try:
        res = requests.post(f"{base}{ep}", headers=hdr("t1533"),
            json={"t1533InBlock": {"gubun": "0"}}, timeout=10)
        raw = res.json()
        rsp_cd  = raw.get("rsp_cd","?")
        rsp_msg = raw.get("rsp_msg","")
        out_keys = [k for k in raw.keys() if "OutBlock" in k]
        has_data = any(raw.get(k) for k in out_keys)
        if res.status_code == 200:
            print(f"  200 {ep} [{rsp_cd}] {rsp_msg} OutBlock키: {out_keys} 데이터: {has_data}")
            if has_data:
                for k in out_keys:
                    rows = raw[k]
                    if rows:
                        row = rows[0] if isinstance(rows,list) else rows
                        print(f"      ✅ [{k}] 첫행: {row}")
        else:
            print(f"  {res.status_code} {ep} [{rsp_cd}] {rsp_msg}")
    except Exception as e:
        print(f"  ERR {ep}: {e}")
    time.sleep(0.2)

print("\n완료!")
