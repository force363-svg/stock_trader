import requests
import json
from datetime import datetime
from config import load_config

# LS Open API URL
URL_REAL = "https://openapi.ls-sec.co.kr:8080"
URL_MOCK = "https://openapi.ls-sec.co.kr:29443"

class LSApi:
    def __init__(self, mode="real"):
        self.config = load_config()
        self.mode = mode
        if mode == "mock":
            self.base_url   = URL_MOCK
            self.app_key    = self.config["api"].get("ls_mock_key", "")
            self.app_secret = self.config["api"].get("ls_mock_secret", "")
        else:
            self.base_url   = URL_REAL
            self.app_key    = self.config["api"].get("ls_app_key", "")
            self.app_secret = self.config["api"].get("ls_app_secret", "")
        self.access_token = None
        self.token_expire = None
        self.last_error = ""
        # 시스템 프록시 우회 세션 (포트 29443 차단 방지)
        self.session = requests.Session()
        self.session.trust_env = False  # 시스템 프록시/환경변수 무시

    # ─────────────────────────────────────
    #  토큰 발급
    # ─────────────────────────────────────
    def get_token(self):
        # API 키 빈값 체크
        if not self.app_key or not self.app_secret:
            self.last_error = "API 키가 설정되지 않았습니다. 설정 창에서 키를 입력해주세요."
            print(f"[LS API] ❌ {self.last_error}")
            return False

        url = f"{self.base_url}/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type"   : "client_credentials",
            "appkey"       : self.app_key,
            "appsecretkey" : self.app_secret,
            "scope"        : "oob"
        }
        verify = self.mode != "mock"
        print(f"[LS API] 토큰 요청: {url} (mode={self.mode}, key={self.app_key[:8]}...)")
        try:
            res = self.session.post(url, headers=headers, data=data,
                                    timeout=30, verify=verify)
            print(f"[LS API] HTTP {res.status_code}: {res.text[:200]}")
            res.raise_for_status()
            result = res.json()
            self.access_token = result.get("access_token")
            if not self.access_token:
                self.last_error = f"토큰 응답 이상: {result}"
                print(f"[LS API] ❌ {self.last_error}")
                return False
            self.last_error = ""
            print(f"[LS API] ✅ 토큰 발급 성공: {self.access_token[:20]}...")
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"[LS API] ❌ 토큰 발급 실패: {e}")
            return False

    def ensure_token(self) -> bool:
        """토큰 유효 확인 후 없으면 재발급"""
        if not self.access_token:
            return self.get_token()
        return True

    def _headers(self, tr_cd):
        return {
            "Content-Type" : "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "tr_cd"        : tr_cd,
            "tr_cont"      : "N",
        }

    # ─────────────────────────────────────
    #  잔고 조회 (CSPAQ12300)
    # ─────────────────────────────────────
    def get_balance(self):
        if not self.access_token:
            if not self.get_token():
                return None

        url = f"{self.base_url}/stock/accno"
        body = {
            "CSPAQ12300InBlock1": {
                "BalCreTp"   : "0",
                "CmsnAppTpCd": "0",
                "D2balBaseSeqTp": "0",
                "UprcTpCd"   : "0"
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("CSPAQ12300"),
                                json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            # OutBlock2 = 계좌요약 (dict), OutBlock3 = 보유종목 리스트 (list)
            out2 = data.get("CSPAQ12300OutBlock2", {})
            out3 = data.get("CSPAQ12300OutBlock3", [])
            if isinstance(out3, dict):
                out3 = [out3]
            print(f"[LS API] ✅ 잔고 조회 완료 - {len(out3)}종목")
            return {"holdings": out3, "summary": out2}
        except Exception as e:
            print(f"[LS API] ❌ 잔고 조회 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  잔고 데이터를 UI용으로 파싱
    # ─────────────────────────────────────
    def get_holdings_for_ui(self):
        """보유종목을 UI 테이블에 표시할 형태로 변환"""
        result = self.get_balance()
        if not result:
            return [], {}

        holdings = result.get("holdings", [])
        summary = result.get("summary", {})

        ui_data = []
        for h in holdings:
            try:
                name = h.get("IsuNm", "").strip()
                if not name:
                    continue
                stock_code = h.get("IsuNo", "")
                buy_price = int(float(h.get("AvrUprc", 0)))
                cur_price = int(float(h.get("NowPrc", 0)))
                qty = int(float(h.get("BalQty", 0)))
                eval_amt = int(float(h.get("BalEvalAmt", 0)))
                pnl_amt = int(float(h.get("EvalPnl", 0)))
                pnl_rate_raw = float(h.get("PnlRat", 0))
                # PnlRat이 소수점 형태면 (예: -0.020654) 100을 곱해 퍼센트로 변환
                if -1 < pnl_rate_raw < 1 and pnl_rate_raw != 0:
                    pnl_rate = pnl_rate_raw * 100
                else:
                    pnl_rate = pnl_rate_raw
                sell_able_qty = int(float(h.get("SellAbleQty", 0)))

                if qty <= 0:
                    continue

                # 등락률 계산 (현재가 vs 전일종가)
                prev_price = int(float(h.get("PrdayCprc", 0)))
                if prev_price > 0:
                    day_change = ((cur_price - prev_price) / prev_price) * 100
                else:
                    day_change = 0.0

                ui_data.append({
                    "name": name,
                    "code": stock_code,
                    "buy_price": f"{buy_price:,}",
                    "cur_price": f"{cur_price:,}",
                    "day_change": f"{day_change:+.2f}%",
                    "pnl_rate": f"{pnl_rate:+.2f}%",
                    "qty": f"{qty}주",
                    "eval_amt": f"{eval_amt:,}",
                    "pnl_amt": f"{pnl_amt:+,}",
                    "raw_qty": sell_able_qty if sell_able_qty > 0 else qty,
                    "raw_code": stock_code,
                })
            except Exception as e:
                print(f"[파싱오류] {h.get('IsuNm','?')}: {e}")
                continue

        # 계좌 요약 — 보유종목 데이터에서 직접 합산
        total_eval = 0
        total_pnl = 0
        total_buy = 0
        for h in holdings:
            try:
                total_eval += int(float(h.get("BalEvalAmt", 0)))
                total_pnl += int(float(h.get("EvalPnl", 0)))
                total_buy += int(float(h.get("PchsAmt", 0)))
            except:
                pass

        if total_buy > 0:
            total_pnl_rate = (total_pnl / total_buy) * 100
        else:
            total_pnl_rate = 0.0

        account_summary = {
            "total_eval": f"{total_eval:,}원",
            "total_pnl": f"{total_pnl:+,}원",
            "total_pnl_rate": f"{total_pnl_rate:+.2f}%",
            "stock_count": f"{len(ui_data)}종목",
        }

        return ui_data, account_summary

    # ─────────────────────────────────────
    #  현재가 조회 (t1102)
    # ─────────────────────────────────────
    def get_price(self, stock_code):
        if not self.access_token:
            if not self.get_token():
                return None

        url = f"{self.base_url}/stock/market-data"
        body = {
            "t1102InBlock": {
                "shcode": stock_code
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("t1102"),
                                json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            out = data.get("t1102OutBlock", {})
            return out
        except Exception as e:
            print(f"[LS API] ❌ 현재가 조회 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  주식 매수 주문 (CSPAT00601)
    # ─────────────────────────────────────
    def buy_order(self, stock_code, qty, price=0):
        """price=0 이면 시장가 주문"""
        if not self.access_token:
            if not self.get_token():
                return None

        url = f"{self.base_url}/stock/order"
        ord_prc_ptn_cd = "03" if price == 0 else "00"
        body = {
            "CSPAT00601InBlock1": {
                "IsuNo"       : stock_code,
                "OrdQty"      : qty,
                "OrdPrc"      : price,
                "BnsTpCd"     : "2",
                "OrdprcPtnCd" : ord_prc_ptn_cd,
                "MgntrnCode"  : "000",
                "LoanDt"      : "",
                "OrdCndiTpCd" : "0"
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("CSPAT00601"),
                                json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            print(f"[LS API] ✅ 매수 주문 완료 - {stock_code} {qty}주")
            return data
        except Exception as e:
            print(f"[LS API] ❌ 매수 주문 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  주식 매도 주문 (CSPAT00601)
    # ─────────────────────────────────────
    def sell_order(self, stock_code, qty, price=0):
        if not self.access_token:
            if not self.get_token():
                return None

        url = f"{self.base_url}/stock/order"
        ord_prc_ptn_cd = "03" if price == 0 else "00"
        body = {
            "CSPAT00601InBlock1": {
                "IsuNo"       : stock_code,
                "OrdQty"      : qty,
                "OrdPrc"      : price,
                "BnsTpCd"     : "1",
                "OrdprcPtnCd" : ord_prc_ptn_cd,
                "MgntrnCode"  : "000",
                "LoanDt"      : "",
                "OrdCndiTpCd" : "0"
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("CSPAT00601"),
                                json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            print(f"[LS API] ✅ 매도 주문 완료 - {stock_code} {qty}주")
            return data
        except Exception as e:
            print(f"[LS API] ❌ 매도 주문 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  업종/지수 현재가 조회 (t1511)
    # ─────────────────────────────────────
    # 올바른 엔드포인트: /indtp/market-data
    # 올바른 필드명: upcode (shcode 아님)
    # KOSPI종합=001, KOSDAQ종합=301
    _SECTOR_CODES = [
        # KOSPI종합/KOSDAQ종합은 상단 바에 표시 → 여기서 제외
        ("002", "음식료"),
        ("003", "섬유의복"),
        ("004", "종이목재"),
        ("005", "화학"),
        ("006", "의약품"),
        ("007", "비금속"),
        ("008", "철강금속"),
        ("009", "기계"),
        ("010", "전기전자"),
        ("011", "의료정밀"),
        ("012", "운수장비"),
        ("013", "유통업"),
        ("015", "건설업"),
        ("017", "통신업"),
        ("018", "금융업"),
    ]

    def get_market_index(self, upcode="001"):
        """업종/지수 현재가 (t1511)
        upcode: 001=KOSPI종합, 301=KOSDAQ종합
        엔드포인트: /indtp/market-data
        """
        if not self.ensure_token():
            return None
        url = f"{self.base_url}/indtp/market-data"
        body = {"t1511InBlock": {"upcode": upcode}}
        try:
            res = self.session.post(url, headers=self._headers("t1511"),
                                json=body, timeout=10)
            if res.status_code != 200:
                print(f"[LS API] ❌ 지수 조회 실패({upcode}): HTTP {res.status_code} - {res.text[:200]}")
                return None
            data = res.json()
            out = data.get("t1511OutBlock", {})
            if out:
                print(f"[LS API] ✅ 지수 조회 완료({upcode}): {out}")
            else:
                print(f"[LS API] ⚠ 지수 응답 키 없음({upcode}): {list(data.keys())}")
            return out if out else None
        except Exception as e:
            print(f"[LS API] ❌ 지수 조회 실패({upcode}): {e}")
            return None

    # ─────────────────────────────────────
    #  상승테마 조회 (t8425) - /stock/investinfo
    # ─────────────────────────────────────
    def get_themes(self):
        """상승테마 조회 (t1533 - 테마별시세조회)
        t1533: 테마 전체의 diff(등락률)/avgdiff 한 번에 제공
        gubun=0(전체), diff 기준 내림차순 정렬
        엔드포인트: /stock/investinfo 시도 → /stock/sector 폴백
        """
        if not self.ensure_token():
            return []

        endpoints = ["/stock/investinfo", "/stock/sector"]
        for endpoint in endpoints:
            try:
                body = {"t1533InBlock": {"gubun": "0"}}
                res = self.session.post(f"{self.base_url}{endpoint}",
                                    headers=self._headers("t1533"),
                                    json=body, timeout=10)
                print(f"[t1533] {endpoint} → HTTP {res.status_code}")
                if res.status_code != 200:
                    continue
                raw = res.json()
                rows = raw.get("t1533OutBlock", [])
                if not rows:
                    print(f"[t1533] {endpoint} 빈 응답: {list(raw.keys())}")
                    continue
                first = rows[0] if isinstance(rows, list) else rows
                print(f"[t1533] 첫행 키: {list(first.keys())}")
                result = []
                for r in (rows if isinstance(rows, list) else [rows]):
                    name = r.get("tmname", "").strip()
                    if not name:
                        continue
                    try:
                        diff = float(r.get("diff", r.get("avgdiff", 0)))
                    except:
                        diff = 0.0
                    sign = "+" if diff >= 0 else ""
                    result.append({
                        "name":     name,
                        "code":     r.get("tmcode", ""),
                        "diff":     diff,
                        "diff_str": f"{sign}{diff:.2f}%",
                    })
                result.sort(key=lambda x: x["diff"], reverse=True)
                top = result[0] if result else None
                print(f"[LS API] ✅ 상승테마 {len(result)}개"
                      + (f", 1위: {top['name']} {top['diff_str']}" if top else ""))
                return result
            except Exception as e:
                print(f"[t1533] {endpoint} 오류: {e}")

        print("[LS API] ❌ t1533 실패 - t8425 폴백")
        # t8425 폴백 (등락률 없이 이름만)
        try:
            res = self.session.post(f"{self.base_url}/stock/sector",
                                headers=self._headers("t8425"),
                                json={"t8425InBlock": {"gubun": "0"}}, timeout=10)
            rows = res.json().get("t8425OutBlock", [])
            return [{"name": r.get("tmname","").strip(), "code": r.get("tmcode",""),
                     "diff": 0.0, "diff_str": "-"} for r in rows if r.get("tmname")]
        except:
            return []

    # ─────────────────────────────────────
    #  테마별 종목 조회 (t1532)
    # ─────────────────────────────────────
    def get_theme_stocks(self, tmcode):
        """테마 내 종목 조회 (t1532, /stock/investinfo)"""
        if not self.ensure_token():
            return []
        body_t1532 = {"t1532InBlock": {"tmcode": tmcode}}
        body_t1537 = {"t1537InBlock": {"tmcode": tmcode}}
        # 엔드포인트 + TR 우선순위 시도
        attempts = [
            ("/stock/market-data", "t1532", body_t1532),
            ("/stock/market-data", "t1537", body_t1537),
            ("/stock/sector",      "t1532", body_t1532),
            ("/stock/sector",      "t1537", body_t1537),
        ]
        for endpoint, tr_cd, body in attempts:
            try:
                res = self.session.post(f"{self.base_url}{endpoint}",
                                    headers=self._headers(tr_cd),
                                    json=body, timeout=10)
                if res.status_code != 200:
                    continue
                raw = res.json()
                # OutBlock1 우선, 없으면 OutBlock
                rows = (raw.get(f"{tr_cd}OutBlock1") or
                        raw.get(f"{tr_cd}OutBlock") or [])
                if isinstance(rows, dict):
                    rows = [rows]
                if not rows:
                    continue
                result = []
                for r in rows:
                    name = r.get("hname", r.get("isuNm", "")).strip()
                    shcode = r.get("shcode", r.get("isu_cd", ""))
                    try:
                        price = int(float(r.get("price", r.get("close", 0))))
                        price_str = f"{price:,}"
                    except:
                        price_str = "-"
                    try:
                        diff = float(r.get("diff", r.get("rate", 0)))
                        sign = "+" if diff >= 0 else ""
                        diff_str = f"{sign}{diff:.2f}%"
                    except:
                        diff_str = "-"
                    if name:
                        result.append((name, price_str, diff_str, shcode))
                print(f"[{tr_cd}] ✅ 테마({tmcode}) 종목 {len(result)}개 ({endpoint})")
                return result
            except Exception as e:
                print(f"[{tr_cd}] {endpoint} 오류: {e}")
        print(f"[테마종목] ❌ tmcode={tmcode} 조회 실패")
        return []

    # ─────────────────────────────────────
    #  일봉 데이터 조회 (t1305)
    #  최근 n봉 OHLCV 반환
    # ─────────────────────────────────────
    def get_daily_ohlcv(self, stock_code: str, count: int = 250) -> list:
        """
        일봉 OHLCV 조회 (t1305)
        반환: [{"date","open","high","low","close","volume"}, ...] 최신순
        """
        if not self.ensure_token():
            return []
        url = f"{self.base_url}/stock/chart"
        body = {
            "t1305InBlock": {
                "shcode"  : stock_code,
                "dwmcode" : "2",        # 1=일봉, 2=주봉, 3=월봉 → 1 사용
                "date"    : "",
                "cnt"     : count,
                "cts_date": ""
            }
        }
        # 일봉 파라미터 수정
        body["t1305InBlock"]["dwmcode"] = "1"
        try:
            res = self.session.post(url, headers=self._headers("t1305"),
                                json=body, timeout=15)
            if res.status_code != 200:
                return []
            data = res.json()
            rows = data.get("t1305OutBlock1", [])
            if isinstance(rows, dict):
                rows = [rows]
            result = []
            for r in rows:
                try:
                    result.append({
                        "date"  : str(r.get("date", "")),
                        "open"  : int(float(r.get("open",  0))),
                        "high"  : int(float(r.get("high",  0))),
                        "low"   : int(float(r.get("low",   0))),
                        "close" : int(float(r.get("close", 0))),
                        "volume": int(float(r.get("jdiff_vol", r.get("volume", 0))))
                    })
                except:
                    continue
            return result
        except Exception as e:
            print(f"[LS API] ❌ 일봉 조회 실패({stock_code}): {e}")
            return []

    # ─────────────────────────────────────
    #  분봉 데이터 조회 (t8410)
    # ─────────────────────────────────────
    def get_minute_ohlcv(self, stock_code: str, tick_range: int = 60,
                         count: int = 100) -> list:
        """
        분봉 OHLCV 조회 (t8410)
        tick_range: 1/3/5/10/15/30/60/120 분봉
        반환: [{"time","open","high","low","close","volume"}, ...] 최신순
        """
        if not self.ensure_token():
            return []
        url = f"{self.base_url}/stock/chart"
        body = {
            "t8410InBlock": {
                "shcode"    : stock_code,
                "ncnt"      : tick_range,
                "qrycnt"    : count,
                "nday"      : "0",
                "sdate"     : "",
                "stime"     : "",
                "edate"     : "",
                "etime"     : "",
                "cts_date"  : "",
                "cts_time"  : "",
                "comp_yn"   : "N"
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("t8410"),
                                json=body, timeout=15)
            if res.status_code != 200:
                return []
            data = res.json()
            rows = data.get("t8410OutBlock1", [])
            if isinstance(rows, dict):
                rows = [rows]
            result = []
            for r in rows:
                try:
                    result.append({
                        "time"  : str(r.get("date", "") + r.get("time", "")),
                        "open"  : int(float(r.get("open",   0))),
                        "high"  : int(float(r.get("high",   0))),
                        "low"   : int(float(r.get("low",    0))),
                        "close" : int(float(r.get("close",  0))),
                        "volume": int(float(r.get("jdiff_vol", r.get("volume", 0))))
                    })
                except:
                    continue
            return result
        except Exception as e:
            print(f"[LS API] ❌ 분봉 조회 실패({stock_code}): {e}")
            return []

    # ─────────────────────────────────────
    #  외인/기관 수급 조회 (t1716)
    #  최근 5일 순매수 데이터
    # ─────────────────────────────────────
    def get_supply_demand(self, stock_code: str, count: int = 5) -> list:
        """
        외인/기관 수급 조회 (t1716)
        반환: [{"date","foreign_net","inst_net","total_net"}, ...] 최신순
        """
        if not self.ensure_token():
            return []
        url = f"{self.base_url}/stock/investinfo"
        body = {
            "t1716InBlock": {
                "shcode" : stock_code,
                "gubun"  : "0",   # 0=일별
                "cnt"    : count
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("t1716"),
                                json=body, timeout=10)
            if res.status_code != 200:
                return []
            data = res.json()
            rows = data.get("t1716OutBlock1", data.get("t1716OutBlock", []))
            if isinstance(rows, dict):
                rows = [rows]
            result = []
            for r in rows:
                try:
                    foreign_net = int(float(r.get("forgn_netq",  r.get("for_netqty",  0))))
                    inst_net    = int(float(r.get("orgn_netq",   r.get("org_netqty",  0))))
                    result.append({
                        "date"       : str(r.get("date", "")),
                        "foreign_net": foreign_net,
                        "inst_net"   : inst_net,
                        "total_net"  : foreign_net + inst_net
                    })
                except:
                    continue
            return result
        except Exception as e:
            print(f"[LS API] ❌ 수급 조회 실패({stock_code}): {e}")
            return []

    # ─────────────────────────────────────
    #  전종목 리스트 조회 (t8430)
    # ─────────────────────────────────────
    def get_stock_list(self, market: str = "0") -> list:
        """
        전종목 코드/이름 조회 (t8430)
        market: 0=전체, 1=코스피, 2=코스닥
        반환: [{"code","name","market","price"}, ...]
        """
        if not self.ensure_token():
            return []
        url = f"{self.base_url}/stock/market-data"
        body = {
            "t8430InBlock": {
                "gubun": market
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("t8430"),
                                json=body, timeout=20)
            if res.status_code != 200:
                print(f"[LS API] ❌ 전종목 조회 실패: HTTP {res.status_code}")
                return []
            data = res.json()
            rows = data.get("t8430OutBlock", [])
            if isinstance(rows, dict):
                rows = [rows]
            result = []
            for r in rows:
                try:
                    code  = r.get("shcode", "").strip()
                    name  = r.get("hname",  "").strip()
                    mkt   = "KOSPI" if r.get("gubun", "") == "1" else "KOSDAQ"
                    price = int(float(r.get("price", 0)))
                    if code and name:
                        result.append({"code": code, "name": name,
                                       "market": mkt, "price": price})
                except:
                    continue
            print(f"[LS API] ✅ 전종목 {len(result)}개")
            return result
        except Exception as e:
            print(f"[LS API] ❌ 전종목 조회 실패: {e}")
            return []

    # ─────────────────────────────────────
    #  업종지수 조회 (t1511 반복 호출)
    # ─────────────────────────────────────
    def get_sector_indices(self):
        """주요 업종지수 조회 (t1511, /indtp/market-data)
        upcode 목록을 순회하며 각 업종의 현재가/등락률 수집
        """
        if not self.ensure_token():
            return []
        url = f"{self.base_url}/indtp/market-data"
        results = []
        for i, (upcode, display_name) in enumerate(self._SECTOR_CODES):
            if i > 0:
                time.sleep(0.2)   # TPS 제한 대응
            body = {"t1511InBlock": {"upcode": upcode}}
            try:
                res = self.session.post(url, headers=self._headers("t1511"),
                                    json=body, timeout=10)
                if res.status_code != 200:
                    print(f"[t1511] {upcode} HTTP {res.status_code}: {res.text[:100]}")
                    results.append({"name": display_name, "index": "-", "change": "-", "foreign": "-", "inst": "-"})
                    continue
                data = res.json()
                out = data.get("t1511OutBlock", {})
                if not out:
                    print(f"[t1511] {upcode} OutBlock 없음: {list(data.keys())}")
                    results.append({"name": display_name, "index": "-", "change": "-", "foreign": "-", "inst": "-"})
                    continue

                row = out[0] if isinstance(out, list) else out

                # 업종명 (없으면 display_name 사용) - 내부 공백 정규화
                raw_name = str(row.get("hname", row.get("upnm", display_name)))
                name = " ".join(raw_name.split()) or display_name

                # 현재지수 (pricejisu)
                try:
                    jisu = float(str(row.get("pricejisu", 0)).replace(",", ""))
                except:
                    jisu = 0.0

                # 대비(change) + 구분(sign): 1=상승 2=하락 3=보합
                try:
                    chg_val = float(str(row.get("change", 0)).replace(",", ""))
                except:
                    chg_val = 0.0
                sign_cd = str(row.get("sign", "3"))  # 1=상승,2=하락,3=보합

                # 등락률 계산: change / (pricejisu - change) * 100
                prev = jisu - chg_val
                if prev > 0:
                    rt = chg_val / prev * 100
                    if sign_cd == "2":   # 하락이면 음수
                        rt = -abs(rt)
                    elif sign_cd == "1":
                        rt = abs(rt)
                    sign_str = "+" if rt >= 0 else ""
                    change_str = f"{sign_str}{rt:.2f}%"
                else:
                    change_str = "-"

                idx_str = f"{jisu:,.2f}" if jisu > 0 else "-"
                results.append({
                    "name":    name,
                    "index":   idx_str,
                    "change":  change_str,
                    "foreign": "-",
                    "inst":    "-",
                })
                print(f"[t1511] ✅ {upcode} {name}: {idx_str} ({change_str})")
            except Exception as e:
                print(f"[t1511] {upcode} 오류: {e}")
                results.append({"name": display_name, "index": "-", "change": "-", "foreign": "-", "inst": "-"})

        print(f"[t1511] 업종지수 조회 완료: {len(results)}개")
        return results


# ─────────────────────────────────────
#  테스트 실행
# ─────────────────────────────────────
if __name__ == "__main__":
    api = LSApi()
    print("=== LS Open API 연결 테스트 ===")
    if api.get_token():
        print("✅ 토큰 발급 성공!")
        holdings, summary = api.get_holdings_for_ui()
        if holdings:
            print(f"✅ 보유종목 {len(holdings)}개:")
            for h in holdings[:5]:
                print(f"  {h['name']} | {h['cur_price']} | {h['pnl_rate']}")
        print(f"계좌요약: {summary}")
    else:
        print("❌ 연결 실패 - App Key/Secret 확인하세요")
