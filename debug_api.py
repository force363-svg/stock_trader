"""
t1532 다양한 tmcode 테스트
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

# 먼저 t8425로 실제 tmcode 전부 가져오기
res = requests.post(f"{base}/stock/sector", headers=hdr("t8425"),
    json={"t8425InBlock": {"gubun": "0"}}, timeout=10)
all_themes = res.json().get("t8425OutBlock", [])
print(f"전체 테마: {len(all_themes)}개\n")
time.sleep(0.2)

# t1532로 여러 tmcode 시도
print("=== t1532 /stock/sector - 다양한 tmcode ===")
found = False
for t in all_themes[:20]:
    tmcode = t.get("tmcode","")
    tmname = t.get("tmname","")
    res = requests.post(f"{base}/stock/sector", headers=hdr("t1532"),
        json={"t1532InBlock": {"tmcode": tmcode}}, timeout=10)
    raw = res.json()
    rows = raw.get("t1532OutBlock", [])
    if rows:
        row = rows[0] if isinstance(rows, list) else rows
        cnt = len(rows) if isinstance(rows, list) else 1
        print(f"  ✅ tmcode={tmcode} ({tmname}) → {cnt}행")
        print(f"     첫행 키: {list(row.keys())}")
        print(f"     첫행:   {row}")
        found = True
        break
    else:
        print(f"  ✗  tmcode={tmcode} ({tmname[:15]}) → 0행")
    time.sleep(0.15)

if not found:
    print("\n처음 20개 모두 0행 - t1532 자체가 지원 안 될 수 있음")

print("\n완료!")
