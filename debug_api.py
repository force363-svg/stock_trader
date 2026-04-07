"""
t1532 type 파라미터 추가 테스트
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

tmcodes = ["0012", "0030", "0014"]  # 반도체장비, 조선, 반도체재료

# t1532 다양한 바디 조합
bodies = [
    {"t1532InBlock": {"tmcode": "0012"}},
    {"t1532InBlock": {"tmcode": "0012", "type": "0"}},
    {"t1532InBlock": {"tmcode": "0012", "type": "1"}},
    {"t1532InBlock": {"tmcode": "0012", "gubun": "0"}},
    {"t1532InBlock": {"tmcode": "12"}},        # 앞 0 제거
    {"t1532InBlock": {"tmcode": "0012", "dummy": ""}},
]

print("=== t1532 /stock/sector - 바디 조합 테스트 ===")
for body in bodies:
    for ep in ["/stock/sector", "/stock/market-data"]:
        res = requests.post(f"{base}{ep}", headers=hdr("t1532"), json=body, timeout=10)
        raw = res.json()
        rsp_cd  = raw.get("rsp_cd","?")
        rsp_msg = raw.get("rsp_msg","")
        all_keys = [k for k in raw.keys() if "OutBlock" in k]
        has_data = any(raw.get(k) for k in all_keys)
        if res.status_code == 200 and has_data:
            for k in all_keys:
                rows = raw[k]
                if rows:
                    row = rows[0] if isinstance(rows,list) else rows
                    cnt = len(rows) if isinstance(rows,list) else 1
                    print(f"  ✅ {ep} body={list(body['t1532InBlock'].keys())}")
                    print(f"     [{k}] {cnt}행, 첫행키: {list(row.keys())}")
                    print(f"     첫행: {row}")
        else:
            inblock = body.get("t1532InBlock",{})
            print(f"  ✗  {ep} {inblock} → [{rsp_cd}] {rsp_msg or '0행'}")
        time.sleep(0.15)

print("\n완료!")
