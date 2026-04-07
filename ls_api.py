import requests
import json
import time
from datetime import datetime
from config import load_config

# LS Open API URL
# 실전/모의 모두 동일한 REST API 서버 (포트 8080)
# 포트 29443 = WebSocket 실시간 시세 전용 (모의투자)
# 포트 9443  = WebSocket 실시간 시세 전용 (실전투자)
URL_BASE = "https://openapi.ls-sec.co.kr:8080"

class LSApi:
    def __init__(self, mode="real"):
        self.config = load_config()
        self.mode = mode
        # 실전/모의 모두 동일한 REST API 서버 사용
        # 차이점: 실전키(ls_app_key) vs 모의키(ls_mock_key)
        self.base_url = URL_BASE
        if mode == "mock":
            self.app_key    = self.config["api"].get("ls_mock_key", "")
            self.app_secret = self.config["api"].get("ls_mock_secret", "")
        else:
            self.app_key    = self.config["api"].get("ls_app_key", "")
            self.app_secret = self.config["api"].get("ls_app_secret", "")
        self.access_token = None
        self.token_expire_at = 0   # 토큰 만료 시각 (unix timestamp)
        self.last_error = ""

    def _is_token_valid(self):
        """토큰이 존재하고 만료되지 않았으면 True (만료 60초 전부터 갱신)"""
        return self.access_token and time.time() < self.token_expire_at - 60

    def ensure_token(self):
        """토큰이 유효하지 않으면 재발급"""
        if not self._is_token_valid():
            return self.get_token()
        return True

    # ─────────────────────────────────────
    #  토큰 발급
    # ─────────────────────────────────────
    def get_token(self):
        # 앱키 유효성 검사
        if not self.app_key or not self.app_secret:
            mode_name = "모의투자" if self.mode == "mock" else "실전투자"
            self.last_error = f"{mode_name} App Key/Secret이 비어있습니다. 설정 > API 계정 설정에서 입력하세요."
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
        try:
            res = requests.post(url, headers=headers, data=data, timeout=10)
            res.raise_for_status()
            result = res.json()
            self.access_token = result.get("access_token")
            if not self.access_token:
                rsp_msg = result.get("rsp_msg", "")
                rsp_cd = result.get("rsp_cd", "")
                if rsp_msg:
                    self.last_error = f"[{rsp_cd}] {rsp_msg}"
                else:
                    self.last_error = f"토큰 응답 이상: {result}"
                print(f"[LS API] ❌ {self.last_error}")
                return False
            # 만료 시간 저장 (expires_in 없으면 기본 86400초=24시간)
            expires_in = int(result.get("expires_in", 86400))
            self.token_expire_at = time.time() + expires_in
            self.last_error = ""
            print(f"[LS API] ✅ 토큰 발급 성공: {self.access_token[:20]}... (만료:{expires_in}초)")
            return True
        except requests.exceptions.ConnectionError as e:
            self.last_error = "LS 서버 연결 실패 - 네트워크 확인"
            print(f"[LS API] ❌ {self.last_error}: {e}")
            return False
        except requests.exceptions.Timeout:
            self.last_error = f"LS 서버 응답 시간 초과 - 포트 {'29443' if self.mode == 'mock' else '8080'}"
            print(f"[LS API] ❌ {self.last_error}")
            return False
        except Exception as e:
            self.last_error = str(e)
            print(f"[LS API] ❌ 토큰 발급 실패: {e}")
            return False

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
        if not self.ensure_token():
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
            res = requests.post(url, headers=self._headers("CSPAQ12300"),
                                json=body, timeout=10)
            # 401: 토큰 만료 → 재발급 후 1회 재시도
            if res.status_code == 401:
                print("[LS API] 토큰 만료 - 재발급 시도")
                if self.get_token():
                    res = requests.post(url, headers=self._headers("CSPAQ12300"),
                                        json=body, timeout=10)
                else:
                    return None
            res.raise_for_status()
            data = res.json()
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
            res = requests.post(url, headers=self._headers("t1102"),
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
        """price=0 이면 시장가 주문. 실전/모의 모두 실제 체결"""
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
            res = requests.post(url, headers=self._headers("CSPAT00601"),
                                json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            mode_tag = "[모의]" if self.mode == "mock" else ""
            print(f"[LS API] ✅ {mode_tag}매수 주문 완료 - {stock_code} {qty}주")
            return data
        except Exception as e:
            print(f"[LS API] ❌ 매수 주문 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  주식 매도 주문 (CSPAT00601)
    # ─────────────────────────────────────
    def sell_order(self, stock_code, qty, price=0):
        """실전/모의 모두 실제 체결"""
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
            res = requests.post(url, headers=self._headers("CSPAT00601"),
                                json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            mode_tag = "[모의]" if self.mode == "mock" else ""
            print(f"[LS API] ✅ {mode_tag}매도 주문 완료 - {stock_code} {qty}주")
            return data
        except Exception as e:
            print(f"[LS API] ❌ 매도 주문 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  업종/지수 현재가 조회 (t1511)
    # ─────────────────────────────────────
    # 올바른 엔드포인트: /indextic/market-data
    # 올바른 필드명: upcode (shcode 아님)
    # KOSPI종합=001, KOSDAQ종합=301
    _SECTOR_CODES = [
        ("001", "KOSPI종합"),
        ("301", "KOSDAQ종합"),
        ("010", "전기전자"),
        ("005", "화학"),
        ("006", "의약품"),
        ("008", "철강금속"),
        ("012", "운수장비"),
        ("015", "건설업"),
        ("018", "금융업"),
        ("022", "서비스업"),
    ]

    def get_market_index(self, upcode="001"):
        """업종/지수 현재가 (t1511)
        upcode: 001=KOSPI종합, 301=KOSDAQ종합
        엔드포인트: /indextic/market-data
        """
        if not self.ensure_token():
            return None
        url = f"{self.base_url}/indextic/market-data"
        body = {"t1511InBlock": {"upcode": upcode}}
        try:
            res = requests.post(url, headers=self._headers("t1511"),
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
    #  테마 목록 조회 (t8425)
    # ─────────────────────────────────────
    def get_themes(self):
        """테마 목록 조회 (t8425) - tmname/tmcode 반환"""
        if not self.ensure_token():
            return []
        url = f"{self.base_url}/stock/sector"
        body = {"t8425InBlock": {"gubun": "0"}}
        try:
            res = requests.post(url, headers=self._headers("t8425"),
                                json=body, timeout=10)
            if res.status_code != 200:
                print(f"[t8425] HTTP {res.status_code}")
                return []
            rows = res.json().get("t8425OutBlock", [])
            result = [{"name": r.get("tmname", "").strip(),
                       "code": r.get("tmcode", "")} for r in rows if r.get("tmname")]
            print(f"[LS API] ✅ 테마 조회 완료: {len(result)}개")
            return result
        except Exception as e:
            print(f"[LS API] ❌ 테마 조회 실패: {e}")
            return []

    # ─────────────────────────────────────
    #  업종지수 조회 (t1511 반복 호출)
    # ─────────────────────────────────────
    def get_sector_indices(self):
        """주요 업종지수 조회 (t1511, /indextic/market-data)
        upcode 목록을 순회하며 각 업종의 현재가/등락률 수집
        """
        if not self.ensure_token():
            return []
        url = f"{self.base_url}/indextic/market-data"
        results = []
        for i, (upcode, display_name) in enumerate(self._SECTOR_CODES):
            if i > 0:
                time.sleep(0.2)   # TPS 제한 대응
            body = {"t1511InBlock": {"upcode": upcode}}
            try:
                res = requests.post(url, headers=self._headers("t1511"),
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

                # 업종명 (없으면 display_name 사용)
                name = str(row.get("hname", row.get("upnm", display_name))).strip() or display_name

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
