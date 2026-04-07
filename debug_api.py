"""
LS API 진단 - t1532 파라미터 탐색 + 업종지수 TR 추가 탐색
실행: python debug_api.py
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
print("토큰 OK\n")

def call(tr_cd, endpoint, body):
    headers = {
        "Content-Type" : "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "tr_cd"        : tr_cd,
        "tr_cont"      : "N",
    }
    res = requests.post(f"{base}{endpoint}", headers=headers, json=body, timeout=10)
    try:
        return res.status_code, res.json()
    except:
        return res.status_code, res.text

# ── t1532 파라미터 변형 탐색 ──
print("=" * 55)
print("t1532 파라미터 탐색")
print("=" * 55)

t1532_variants = [
    {"upcode": "",    "gubun": "1"},   # 전체 코스피
    {"upcode": "",    "gubun": "2"},   # 전체 코스닥
    {"upcode": "",    "gubun": "0"},   # 전체
    {"upcode": "001", "gubun": "1"},
    {"upcode": "001", "gubun": "2"},
    {"upcode": "001", "gubun": "0"},
    {"upcode": "002", "gubun": "1"},
    {"gubun": "1"},                    # upcode 없이
    {"gubun": "0"},
]

for params in t1532_variants:
    status, raw = call("t1532", "/stock/sector", {"t1532InBlock": params})
    if status == 200:
        rows = raw.get("t1532OutBlock", [])
        rsp = raw.get("rsp_cd", "?")
        if rows:
            print(f"✅ 파라미터={params} → {len(rows)}행")
            print(f"   첫행 키: {list(rows[0].keys())}")
            print(f"   첫행 값: {rows[0]}")
            # 저장
            pkey = str(params).replace(" ","").replace("'","").replace(":","=")
            with open(f"debug_t1532_{pkey}.json","w",encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False, indent=2)
            break
        else:
            print(f"   파라미터={params} → 0행 (rsp:{rsp})")
    else:
        print(f"   파라미터={params} → HTTP {status}")

# ── 추가 TR 탐색 ──
print("\n" + "=" * 55)
print("추가 TR 탐색 (업종지수 후보)")
print("=" * 55)

extra_tests = [
    ("t1537", "/stock/sector",       {"t1537InBlock": {"upcode": "001", "gubun": "1"}}),
    ("t1537", "/stock/sector",       {"t1537InBlock": {"upcode": "", "gubun": "0"}}),
    ("t8426", "/stock/sector",       {"t8426InBlock": {"gubun": "0"}}),
    ("t8426", "/stock/sector",       {"t8426InBlock": {"tmcode": "0008"}}),
    ("t1530", "/stock/sector",       {"t1530InBlock": {"upcode": "001"}}),
    ("t1531", "/stock/sector",       {"t1531InBlock": {"upcode": "001"}}),
    ("CSPAQ13700", "/stock/sector",  {"CSPAQ13700InBlock1": {}}),
    ("t1102", "/stock/market-data",  {"t1102InBlock": {"shcode": "005930"}}),  # 확인용: 삼성전자
]

for tr_cd, endpoint, body in extra_tests:
    status, raw = call(tr_cd, endpoint, body)
    if isinstance(raw, dict):
        rsp_cd = raw.get("rsp_cd", "")
        rows_key = [k for k in raw if "OutBlock" in k]
        if status == 200 and rows_key:
            rows = raw[rows_key[0]]
            cnt = len(rows) if isinstance(rows, list) else "dict"
            print(f"✅ {tr_cd} {endpoint} → {cnt}행")
            if isinstance(rows, list) and rows:
                print(f"   첫행 키: {list(rows[0].keys())}")
                print(f"   첫행 값: {rows[0]}")
            elif isinstance(rows, dict):
                print(f"   값: {rows}")
            with open(f"debug_{tr_cd}.json","w",encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False, indent=2)
        elif status == 200:
            print(f"   {tr_cd} {endpoint} → 200 OK, 키={list(raw.keys())}, rsp={rsp_cd}")
        else:
            rsp_msg = raw.get("rsp_msg","")
            print(f"   {tr_cd} → HTTP {status} [{rsp_cd}] {rsp_msg}")
    else:
        print(f"   {tr_cd} → HTTP {status} {str(raw)[:80]}")

# ── t8425 테마 + 등락률 얻는 방법 탐색 ──
print("\n" + "=" * 55)
print("t8426 테마 등락률 (t8425 다음 TR)")
print("=" * 55)
# t8425로 첫 번째 테마코드 가져오기
status, raw = call("t8425", "/stock/sector", {"t8425InBlock": {"gubun": "0"}})
if status == 200:
    themes = raw.get("t8425OutBlock", [])
    if themes:
        first_tmcode = themes[0]["tmcode"]
        print(f"테마코드 샘플: {first_tmcode} ({themes[0]['tmname']})")
        # 해당 테마코드로 등락률 조회 시도
        for tr in ["t8426", "t8427", "t8428"]:
            status2, raw2 = call(tr, "/stock/sector", {f"{tr}InBlock": {"tmcode": first_tmcode}})
            if isinstance(raw2, dict):
                rsp = raw2.get("rsp_cd","?")
                rsp_msg = raw2.get("rsp_msg","")
                out_keys = [k for k in raw2 if "OutBlock" in k]
                if status2 == 200 and out_keys:
                    rows = raw2[out_keys[0]]
                    cnt = len(rows) if isinstance(rows, list) else "dict"
                    print(f"✅ {tr} → {cnt}행")
                    if isinstance(rows, list) and rows:
                        print(f"   첫행: {rows[0]}")
                    elif isinstance(rows, dict):
                        print(f"   값: {rows}")
                else:
                    print(f"   {tr} → HTTP {status2} [{rsp}] {rsp_msg}")

print("\n완료!")
