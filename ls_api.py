import requests
import json
from datetime import datetime
from config import load_config

# LS Open API 기본 URL
BASE_URL = "https://openapi.ls-sec.co.kr:8080"

class LSApi:
    def __init__(self):
        self.config = load_config()
        self.app_key    = self.config["api"]["ls_app_key"]
        self.app_secret = self.config["api"]["ls_app_secret"]
        self.access_token = None
        self.token_expire = None

    # ─────────────────────────────────────
    #  토큰 발급
    # ─────────────────────────────────────
    def get_token(self):
        url = f"{BASE_URL}/oauth2/token"
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
                print(f"[LS API] ❌ 토큰 응답 이상: {result}")
                return False
            print(f"[LS API] ✅ 토큰 발급 성공: {self.access_token[:20]}...")
            return True
        except Exception as e:
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
        if not self.access_token:
            if not self.get_token():
                return None

        url = f"{BASE_URL}/stock/accno"
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

        url = f"{BASE_URL}/stock/market-data"
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
        """price=0 이면 시장가 주문"""
        if not self.access_token:
            if not self.get_token():
                return None

        url = f"{BASE_URL}/stock/order"
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

        url = f"{BASE_URL}/stock/order"
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
            print(f"[LS API] ✅ 매도 주문 완료 - {stock_code} {qty}주")
            return data
        except Exception as e:
            print(f"[LS API] ❌ 매도 주문 실패: {e}")
            return None


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
