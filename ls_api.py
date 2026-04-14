import requests
import json
import time
import os
import sys
from datetime import datetime
from config import load_config

# LS Open API URL
URL_REAL = "https://openapi.ls-sec.co.kr:8080"
URL_MOCK = "https://openapi.ls-sec.co.kr:8080"

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
            print(f"[LS API] [실패] {self.last_error}")
            return False

        url = f"{self.base_url}/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type"   : "client_credentials",
            "appkey"       : self.app_key,
            "appsecretkey" : self.app_secret,
            "scope"        : "oob"
        }
        verify = True
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
                print(f"[LS API] [실패] {self.last_error}")
                return False
            self.last_error = ""
            print(f"[LS API] [성공] 토큰 발급 성공: {self.access_token[:20]}...")
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"[LS API] [실패] 토큰 발급 실패: {e}")
            return False

    def ensure_token(self) -> bool:
        """토큰 유효 확인 후 없으면 재발급"""
        if not self.access_token:
            return self.get_token()
        return True

    def _headers(self, tr_cd, tr_cont="N", tr_cont_key=""):
        h = {
            "Content-Type" : "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "tr_cd"        : tr_cd,
            "tr_cont"      : tr_cont,
        }
        if tr_cont_key:
            h["tr_cont_key"] = tr_cont_key
        return h

    # ─────────────────────────────────────
    #  주문가능 현금 조회
    # ─────────────────────────────────────
    def get_available_cash(self) -> int:
        """주문 가능한 현금(예수금) 조회. 실패 시 0 반환."""
        # 1차: t0424(주식잔고2) — 가장 정확
        try:
            cash = self._get_cash_t0424()
            if cash > 0:
                return cash
        except Exception as e:
            print(f"[LS API] 주문가능금액 t0424 오류: {e}")

        # 2차: CSPAQ12300 OutBlock2 필드
        try:
            result = self.get_balance()
            if result:
                summary = result.get("summary", {})
                for key in ("MnyOrdAbleAmt", "D2Dps", "DpsastTotamt", "Dps"):
                    val = summary.get(key, 0)
                    try:
                        cash = int(float(val))
                        if cash > 0:
                            return cash
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            print(f"[LS API] 주문가능금액 CSPAQ 오류: {e}")

        # 3차: 최근 t0424 캐시 사용 (API 일시 실패 방어)
        if hasattr(self, '_last_available_cash') and self._last_available_cash > 0:
            print(f"[LS API] 주문가능금액 캐시 사용: {self._last_available_cash:,}원")
            return self._last_available_cash

        print(f"[LS API] 주문가능금액 조회 실패 — 0원 반환")
        return 0

    def _get_t0424_data(self) -> dict:
        """t0424(주식잔고2) 전체 데이터 반환"""
        if not self.ensure_token():
            return {}
        url = f"{self.base_url}/stock/accno"
        body = {
            "t0424InBlock": {
                "pession": "0",
                "chegb": "0",
                "dangb": "0",
                "charge": "0",
                "cts_expcode": ""
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("t0424"),
                                json=body, timeout=10)
            # 디버그 (모의/실투 구분)
            try:
                _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if getattr(sys, 'frozen', False):
                    _base = os.path.dirname(os.path.dirname(sys.executable))
                _mode = "mock" if "mock" in os.path.basename(sys.executable).lower() else "real" if getattr(sys, 'frozen', False) else "dev"
                with open(os.path.join(_base, f"debug_t0424_{_mode}.txt"), "w", encoding="utf-8") as f:
                    f.write(f"mode: {_mode}\n")
                    f.write(f"url: {url}\n")
                    f.write(f"status: {res.status_code}\n")
                    f.write(f"response: {res.text[:5000]}\n")
            except Exception:
                pass
            if res.status_code != 200:
                return {}
            data = res.json()
            return data.get("t0424OutBlock", {})
        except Exception:
            return {}

    def _get_cash_t0424(self) -> int:
        """t0424(주식잔고2)로 예수금/주문가능금액 조회"""
        out = self._get_t0424_data()
        if not out:
            return 0
        # sunamt1(추정D2예수금)
        for key in ("sunamt1",):
            val = out.get(key, 0)
            try:
                v = int(float(val))
                if v > 0:
                    self._last_available_cash = v  # 캐시 저장
                    return v
            except:
                continue
        # 추정순자산 - 평가금액 = 현금
        try:
            sunamt = int(float(out.get("sunamt", 0)))
            tappamt = int(float(out.get("tappamt", 0)))
            if sunamt > tappamt:
                return sunamt - tappamt
        except:
            pass
        return 0

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
            data = res.json()
            # 잔고 조회 디버그
            try:
                import os as _os2, sys as _sys2
                _b = _os2.path.dirname(_os2.path.dirname(_sys2.executable)) if getattr(_sys2, 'frozen', False) else _os2.path.dirname(_os2.path.abspath(__file__))
                with open(_os2.path.join(_b, "debug_balance.txt"), "w", encoding="utf-8") as _bf:
                    _bf.write(f"status: {res.status_code}\n")
                    _bf.write(f"keys: {list(data.keys())}\n")
                    _bf.write(f"response: {str(data)[:2000]}\n")
            except Exception:
                pass
            res.raise_for_status()
            # OutBlock2 = 계좌요약 (dict), OutBlock3 = 보유종목 리스트 (list)
            out2 = data.get("CSPAQ12300OutBlock2", {})
            out3 = data.get("CSPAQ12300OutBlock3", [])
            if isinstance(out3, dict):
                out3 = [out3]
            print(f"[LS API] [성공] 잔고 조회 완료 - {len(out3)}종목")
            return {"holdings": out3, "summary": out2}
        except Exception as e:
            print(f"[LS API] [실패] 잔고 조회 실패: {e}")
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

        # 디버그: API 응답 키 확인 (C:\StockTrader\debug_holdings.txt)
        try:
            import sys as _sys
            if getattr(_sys, 'frozen', False):
                _dbg_dir = os.path.dirname(os.path.dirname(_sys.executable))
            else:
                _dbg_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(_dbg_dir, "debug_holdings.txt"), "w", encoding="utf-8") as _dbg:
                _dbg.write(f"holdings count: {len(holdings)}\n")
                for i, h in enumerate(holdings[:3]):
                    _dbg.write(f"\n--- holding[{i}] keys: {list(h.keys())}\n")
                    for k, v in h.items():
                        _dbg.write(f"  {k}: {v}\n")
        except Exception:
            pass


        ui_data = []
        for h in holdings:
            try:
                name = h.get("IsuNm", "").strip()
                if not name:
                    continue
                stock_code = h.get("IsuNo", "")
                buy_price = int(float(h.get("AvrUprc", 0)))
                cur_price = int(float(h.get("NowPrc", 0)))
                # BnsBaseBalQty = 매매기준잔고 (HTS와 동일한 실제 보유수량)
                qty = int(float(h.get("BnsBaseBalQty", 0)))
                if qty <= 0:
                    continue  # 전량매도 종목 제외 (미결제만 남은 경우)
                eval_amt = int(float(h.get("BalEvalAmt", 0)))
                pnl_amt = int(float(h.get("EvalPnl", 0)))
                pch_amt = int(float(h.get("PchsAmt", 0)))
                # 수익률 = 평가손익 / 매입금액 (HTS와 동일, 수수료 포함)
                if pch_amt > 0:
                    pnl_rate = (pnl_amt / pch_amt) * 100
                elif buy_price > 0:
                    pnl_rate = (cur_price - buy_price) / buy_price * 100
                else:
                    pnl_rate = 0.0
                sell_able_qty = int(float(h.get("SellAbleQty", 0)))

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
                    "raw_buy_price": buy_price,
                    "raw_cur_price": cur_price,
                    "raw_pnl_rate": pnl_rate,
                })
            except Exception as e:
                print(f"[파싱오류] {h.get('IsuNm','?')}: {e}")
                continue

        # 계좌 요약 — t0424 + CSPAQ12300 조합
        total_pnl = int(float(summary.get("EvalPnlSum", 0)))
        total_buy = int(float(summary.get("PchsAmt", 0)))
        tappamt = int(float(summary.get("BalEvalAmt", 0)))
        total_pnl_rate = 0.0

        # t0424: 추정자산(sunamt) + 실현손익(dtsunik) — 장 마감 후에도 정확
        t0424 = None
        total_asset = 0
        realized_pnl = 0
        try:
            t0424 = self._get_t0424_data()
            if t0424:
                total_asset = int(float(t0424.get("sunamt", 0)))
                realized_pnl = int(float(t0424.get("dtsunik", 0)))
        except Exception:
            pass

        # t0424 실패 시 CSPAQ12300 폴백
        if total_asset == 0:
            total_asset = int(float(summary.get("DpsastTotamt", 0)))

        # 보유종목에서 합산 (최후 폴백)
        if total_buy == 0:
            for h in holdings:
                try:
                    total_buy += int(float(h.get("PchsAmt", 0)))
                except:
                    pass
        if total_pnl == 0:
            for h in holdings:
                try:
                    total_pnl += int(float(h.get("EvalPnl", 0)))
                except:
                    pass
        if total_buy > 0 and total_pnl_rate == 0:
            total_pnl_rate = (total_pnl / total_buy) * 100


        account_summary = {
            "total_eval": f"{total_asset:,}",
            "realized_pnl": f"{realized_pnl:+,}",
            "total_buy": f"{total_buy:,}",
            "total_appamt": f"{tappamt:,}" if tappamt else f"{total_buy + total_pnl:,}",
            "total_pnl": f"{total_pnl:+,}",
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
            if res.status_code in (429, 500):
                import time as _time
                _time.sleep(2)
                res = self.session.post(url, headers=self._headers("t1102"),
                                    json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            out = data.get("t1102OutBlock", {})
            # 상장주식수 필드 통일 (t1102: listcnt 또는 total_stock)
            for key in ("listcnt", "total_stock", "lstqty"):
                if key in out and "listing" not in out:
                    try:
                        out["listing"] = int(float(out[key]))
                    except Exception:
                        pass
                    break
            # 디버그: t1102 응답 키 기록 (1회만)
            try:
                import os, sys
                _base = os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                _dbg_path = os.path.join(_base, "debug_t1102_keys.txt")
                if not os.path.exists(_dbg_path):
                    with open(_dbg_path, "w", encoding="utf-8") as _f:
                        _f.write(f"t1102 keys: {list(out.keys())}\n")
                        # 상장주식수 관련 필드 찾기
                        for k, v in out.items():
                            if isinstance(v, (int, float, str)) and str(v).isdigit() and int(v) > 1000000:
                                _f.write(f"  {k} = {v}\n")
            except Exception:
                pass
            return out
        except Exception as e:
            print(f"[LS API] [실패] 현재가 조회 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  주식 매수 주문 (CSPAT00601)
    # ─────────────────────────────────────
    def buy_order(self, stock_code, qty, price=0):
        """price=0 이면 시장가 주문"""
        if not self.access_token:
            if not self.get_token():
                return None

        # LS 주문 API는 종목코드에 "A" prefix 필요
        stock_code = stock_code.strip()
        if not stock_code.startswith("A"):
            stock_code = "A" + stock_code

        url = f"{self.base_url}/stock/order"
        ord_prc_ptn_cd = "03" if price == 0 else "00"
        body = {
            "CSPAT00601InBlock1": {
                "IsuNo"        : stock_code,
                "OrdQty"       : qty,
                "OrdPrc"       : price,
                "BnsTpCode"    : "2",
                "OrdprcPtnCode": ord_prc_ptn_cd,
                "MgntrnCode"   : "000",
                "LoanDt"       : "",
                "OrdCndiTpCode": "0"
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("CSPAT00601"),
                                json=body, timeout=10)
            # 주문 응답 디버그 기록
            try:
                import os as _os, sys as _sys, json as _json
                _base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
                if getattr(_sys, 'frozen', False):
                    _base = _os.path.dirname(_os.path.dirname(os.path.dirname(_sys.executable)))
                with open(_os.path.join(_base, "debug_order.txt"), "a", encoding="utf-8") as _f:
                    from datetime import datetime as _dt
                    _f.write(f"[{_dt.now().strftime('%H:%M:%S')}] [BUILD_V2] BUY {stock_code} {qty}주\n")
                    _f.write(f"  body: {_json.dumps(body, ensure_ascii=False)}\n")
                    _f.write(f"  status: {res.status_code}\n")
                    _f.write(f"  response: {res.text[:500]}\n\n")
            except Exception:
                pass
            res.raise_for_status()
            data = res.json()
            print(f"[LS API] [성공] 매수 주문 완료 - {stock_code} {qty}주")
            return data
        except Exception as e:
            print(f"[LS API] [실패] 매수 주문 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  주식 매도 주문 (CSPAT00601)
    # ─────────────────────────────────────
    def sell_order(self, stock_code, qty, price=0):
        if not self.access_token:
            if not self.get_token():
                return None

        # LS 주문 API는 종목코드에 "A" prefix 필요
        stock_code = stock_code.strip()
        if not stock_code.startswith("A"):
            stock_code = "A" + stock_code

        url = f"{self.base_url}/stock/order"
        ord_prc_ptn_cd = "03" if price == 0 else "00"
        body = {
            "CSPAT00601InBlock1": {
                "IsuNo"        : stock_code,
                "OrdQty"       : qty,
                "OrdPrc"       : price,
                "BnsTpCode"    : "1",
                "OrdprcPtnCode": ord_prc_ptn_cd,
                "MgntrnCode"   : "000",
                "LoanDt"       : "",
                "OrdCndiTpCode": "0"
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("CSPAT00601"),
                                json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            print(f"[LS API] [성공] 매도 주문 완료 - {stock_code} {qty}주")
            return data
        except Exception as e:
            print(f"[LS API] [실패] 매도 주문 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  미체결 주문 조회 (CSPAQ13700)
    # ─────────────────────────────────────
    def get_unfilled_orders(self):
        """미체결 주문 목록 조회"""
        if not self.access_token:
            if not self.get_token():
                return []

        url = f"{self.base_url}/stock/accno"
        body = {
            "CSPAQ13700InBlock1": {
                "OrdMktCode": "00",
                "BnsTpCode": "0",
                "IsuNo": "",
                "ExecYn": "N",
                "OrdDt": "",
                "SrtOrdNo2": 0,
                "BkseqTpCode": "0",
                "OrdPtnCode": "00"
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("CSPAQ13700"),
                                json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            orders = data.get("CSPAQ13700OutBlock3", [])
            if isinstance(orders, dict):
                orders = [orders]
            result = []
            for o in orders:
                unf_qty = int(o.get("UnercQty", 0))
                if unf_qty <= 0:
                    continue
                result.append({
                    "order_no": o.get("OrdNo", ""),
                    "stock_code": o.get("IsuNo", "").replace("A", ""),
                    "stock_name": o.get("IsuNm", ""),
                    "bns_type": "BUY" if o.get("BnsTpCode") == "2" else "SELL",
                    "order_qty": int(o.get("OrdQty", 0)),
                    "unfilled_qty": unf_qty,
                    "order_price": float(o.get("OrdPrc", 0)),
                    "order_time": o.get("OrdTime", ""),
                })
            return result
        except Exception as e:
            print(f"[LS API] [실패] 미체결 조회 실패: {e}")
            return []

    # ─────────────────────────────────────
    #  주문 취소 (CSPAT00801)
    # ─────────────────────────────────────
    def cancel_order(self, order_no, stock_code, qty):
        """미체결 주문 취소"""
        if not self.access_token:
            if not self.get_token():
                return None

        stock_code = stock_code.strip()
        if not stock_code.startswith("A"):
            stock_code = "A" + stock_code

        url = f"{self.base_url}/stock/order"
        body = {
            "CSPAT00801InBlock1": {
                "OrgOrdNo": int(order_no),
                "IsuNo": stock_code,
                "OrdQty": qty,
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("CSPAT00801"),
                                json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            print(f"[LS API] [성공] 주문 취소 완료 - 원주문:{order_no}")
            return data
        except Exception as e:
            print(f"[LS API] [실패] 주문 취소 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  주문 정정 (CSPAT00701)
    # ─────────────────────────────────────
    def modify_order(self, order_no, stock_code, qty, new_price):
        """미체결 주문 가격 정정 (하향 추적용)"""
        if not self.access_token:
            if not self.get_token():
                return None

        stock_code = stock_code.strip()
        if not stock_code.startswith("A"):
            stock_code = "A" + stock_code

        ord_prc_ptn_cd = "03" if new_price == 0 else "00"
        url = f"{self.base_url}/stock/order"
        body = {
            "CSPAT00701InBlock1": {
                "OrgOrdNo": int(order_no),
                "IsuNo": stock_code,
                "OrdQty": qty,
                "OrdPrc": new_price,
                "OrdprcPtnCode": ord_prc_ptn_cd,
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("CSPAT00701"),
                                json=body, timeout=10)
            res.raise_for_status()
            data = res.json()
            print(f"[LS API] [성공] 주문 정정 완료 - 원주문:{order_no} → {new_price:,}원")
            return data
        except Exception as e:
            print(f"[LS API] [실패] 주문 정정 실패: {e}")
            return None

    # ─────────────────────────────────────
    #  업종/지수 현재가 조회 (t1511)
    # ─────────────────────────────────────
    # 올바른 엔드포인트: /indtp/market-data
    # 올바른 필드명: upcode (shcode 아님)
    # KOSPI종합=001, KOSDAQ종합=301
    _SECTOR_CODES = [
        # KOSPI 업종 (001 종합 제외)
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
        ("014", "전기가스"),
        ("015", "건설업"),
        ("016", "운수창고"),
        ("017", "통신업"),
        ("018", "금융업"),
        ("019", "은행"),
        ("020", "증권"),
        ("021", "보험"),
        ("022", "서비스업"),
        ("024", "제조업"),
        # KOSDAQ 업종 (301 종합 제외)
        ("302", "IT"),
        ("303", "IT H/W"),
        ("304", "IT S/W"),
        ("305", "인터넷"),
        ("306", "디지털컨텐츠"),
        ("307", "소프트웨어"),
        ("308", "컴퓨터"),
        ("309", "통신장비"),
        ("310", "반도체"),
        ("311", "IT부품"),
        ("312", "통신서비스"),
        ("313", "방송서비스"),
        ("314", "IT종합"),
        ("315", "비IT"),
        ("316", "바이오/헬스케어"),
        ("317", "제조"),
        ("318", "건설"),
        ("319", "유통"),
        ("320", "음식료/담배"),
        ("321", "섬유/의류"),
        ("322", "제지/목재"),
        ("323", "화학"),
        ("324", "금속/광물"),
        ("325", "기계/장비"),
        ("326", "기타제조"),
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
                print(f"[LS API] [실패] 지수 조회 실패({upcode}): HTTP {res.status_code} - {res.text[:200]}")
                return None
            data = res.json()
            out = data.get("t1511OutBlock", {})
            if out:
                print(f"[LS API] [성공] 지수 조회 완료({upcode}): {out}")
            else:
                print(f"[LS API] ⚠ 지수 응답 키 없음({upcode}): {list(data.keys())}")
            return out if out else None
        except Exception as e:
            print(f"[LS API] [실패] 지수 조회 실패({upcode}): {e}")
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
                # OutBlock1 우선 (테마 목록), 없으면 OutBlock
                rows = raw.get("t1533OutBlock1", raw.get("t1533OutBlock", []))
                if not rows or (isinstance(rows, dict) and "tmname" not in rows):
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
                print(f"[LS API] [성공] 상승테마 {len(result)}개"
                      + (f", 1위: {top['name']} {top['diff_str']}" if top else ""))
                return result
            except Exception as e:
                print(f"[t1533] {endpoint} 오류: {e}")

        print("[LS API] [실패] t1533 실패 - t8425 폴백")
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
                print(f"[{tr_cd}] [성공] 테마({tmcode}) 종목 {len(result)}개 ({endpoint})")
                return result
            except Exception as e:
                print(f"[{tr_cd}] {endpoint} 오류: {e}")
        print(f"[테마종목] [실패] tmcode={tmcode} 조회 실패")
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
        url = f"{self.base_url}/stock/market-data"
        body = {
            "t1305InBlock": {
                "shcode"  : stock_code,
                "dwmcode" : 1,          # 1=일, 2=주, 3=월
                "date"    : "",
                "idx"     : 0,
                "cnt"     : count
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("t1305"),
                                json=body, timeout=15)
            # 디버그: 첫 호출의 API 응답 전체를 파일에 기록
            if not hasattr(self, '_t1305_debug_done'):
                self._t1305_debug_done = True
                try:
                    import os, sys
                    dbg_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    if getattr(sys, 'frozen', False):
                        dbg_base = os.path.dirname(os.path.dirname(sys.executable))
                    with open(os.path.join(dbg_base, "debug_t1305.txt"), "w", encoding="utf-8") as f:
                        f.write(f"code: {stock_code}\n")
                        f.write(f"url: {url}\n")
                        f.write(f"request_body: {json.dumps(body, ensure_ascii=False)}\n")
                        f.write(f"status: {res.status_code}\n")
                        f.write(f"response: {res.text[:3000]}\n")
                except:
                    pass
            if res.status_code != 200:
                # 속도제한(429/500) → 2초 대기 후 1회 재시도
                if res.status_code in (429, 500) and not getattr(self, '_t1305_retrying', False):
                    self._t1305_retrying = True
                    import time as _time
                    _time.sleep(2)
                    try:
                        res2 = self.session.post(url, headers=self._headers("t1305"),
                                              json=body, timeout=15)
                        if res2.status_code == 200:
                            self._t1305_retrying = False
                            data = res2.json()
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
                    except Exception:
                        pass
                    self._t1305_retrying = False
                self._log_daily_fail(stock_code, f"HTTP_{res.status_code}", res.text[:200])
                return []
            data = res.json()
            rows = data.get("t1305OutBlock1", [])
            if not rows:
                self._log_daily_fail(stock_code, "empty_response", str(list(data.keys())[:10]))
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
            self._log_daily_fail(stock_code, "exception", str(e))
            return []

    def _log_daily_fail(self, code: str, reason: str, detail: str = ""):
        """일봉 조회 실패 로그 → debug_daily_fail.txt (최근 50건)"""
        try:
            import os as _os, sys as _sys
            from datetime import datetime as _dt
            base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
            if getattr(_sys, 'frozen', False):
                base = _os.path.dirname(_os.path.dirname(os.path.dirname(_sys.executable)))
            path = _os.path.join(base, "debug_daily_fail.txt")
            # 기존 로그 읽기 (최근 50줄 유지)
            lines = []
            if _os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-49:]
            line = f"[{_dt.now().strftime('%H:%M:%S')}] {code} | {reason} | {detail[:100]}\n"
            lines.append(line)
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception:
            pass

    # ─────────────────────────────────────
    #  분봉 데이터 조회 (t8410)
    # ─────────────────────────────────────
    def get_minute_ohlcv(self, stock_code: str, tick_range: int = 60,
                         count: int = 100) -> list:
        """
        분봉 OHLCV 조회 (t8412 - 주식챠트 N분)
        tick_range: 1/3/5/10/15/30/60/120 분봉
        반환: [{"time","open","high","low","close","volume"}, ...] 최신순
        """
        if not self.ensure_token():
            return []
        url = f"{self.base_url}/stock/chart"
        today = datetime.now().strftime("%Y%m%d")
        # 시작일: 분봉 수에 따라 충분한 기간 동적 계산
        from datetime import timedelta
        candles_per_day = max(1, 390 // tick_range)  # 390분(장중) / N분봉
        trading_days_needed = (count // candles_per_day) + 10
        calendar_days = max(60, int(trading_days_needed * 2.5))  # 주말/공휴일 넉넉히
        sdate = (datetime.now() - timedelta(days=calendar_days)).strftime("%Y%m%d")
        body = {
            "t8412InBlock": {
                "shcode"    : stock_code,
                "ncnt"      : tick_range,
                "qrycnt"    : count,
                "nday"      : "0",
                "sdate"     : sdate,
                "stime"     : "",
                "edate"     : today,
                "etime"     : "",
                "cts_date"  : "",
                "cts_time"  : "",
                "comp_yn"   : "N"
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("t8412"),
                                json=body, timeout=15)
            if res.status_code != 200:
                # TPS 초과(429/500) → 2초 대기 후 재시도
                if res.status_code in (429, 500):
                    import time as _time
                    _time.sleep(2)
                    res = self.session.post(url, headers=self._headers("t8412"),
                                        json=body, timeout=15)
                if res.status_code != 200:
                    print(f"[LS API] [실패] 분봉 t8412 HTTP {res.status_code}: {res.text[:300]}")
                    return []
            data = res.json()
            # 디버그: 첫 호출의 분봉 응답 기록
            if not hasattr(self, '_t8412_debug_done'):
                self._t8412_debug_done = True
                try:
                    import os, sys
                    _base = os.path.dirname(os.path.dirname(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                    with open(os.path.join(_base, "debug_t8412.txt"), "w", encoding="utf-8") as _f:
                        _f.write(f"code: {stock_code}, tick: {tick_range}, qrycnt: {count}\n")
                        _f.write(f"sdate: {sdate}, edate: {today}\n")
                        _f.write(f"calendar_days: {calendar_days}, trading_days_needed: {trading_days_needed}\n")
                        _out0 = data.get("t8412OutBlock", {})
                        _f.write(f"OutBlock: {_out0}\n")
                        _rows = data.get("t8412OutBlock1", [])
                        _f.write(f"OutBlock1 count: {len(_rows)}\n")
                        if _rows:
                            _f.write(f"first: {_rows[0]}\n")
                            _f.write(f"last: {_rows[-1]}\n")
                except Exception:
                    pass
            rows = data.get("t8412OutBlock1", [])
            if not rows:
                print(f"[LS API] ⚠ 분봉 t8412 응답 키 없음({stock_code}): {list(data.keys())[:10]}")
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
            print(f"[LS API] [실패] 분봉 조회 실패({stock_code}): {e}")
            return []

    # ─────────────────────────────────────
    #  외인/기관 수급 조회 (t1716)
    #  최근 5일 순매수 데이터
    # ─────────────────────────────────────
    def get_supply_demand(self, stock_code: str, count: int = 20) -> list:
        """
        외인/기관 수급 조회 (t1716)
        반환: [{"date","foreign_net","inst_net","total_net"}, ...] 최신순
        """
        if not self.ensure_token():
            return []
        url = f"{self.base_url}/stock/frgr-itt"
        today = datetime.now().strftime("%Y%m%d")
        from datetime import timedelta
        fromdt = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
        body = {
            "t1716InBlock": {
                "shcode"   : stock_code,
                "gubun"    : "0",      # 0=일간순매수, 1=기간누적순매수
                "fromdt"   : fromdt,
                "todt"     : today,
                "prapp"    : 0,
                "prgubun"  : "0",      # 0=PR감산 미적용
                "orggubun" : "0",
                "frggubun" : "0"
            }
        }
        try:
            res = self.session.post(url, headers=self._headers("t1716"),
                                json=body, timeout=10)
            # 디버그: 첫 호출의 API 응답 기록
            if not hasattr(self, '_t1716_debug_done'):
                self._t1716_debug_done = True
                try:
                    import os, sys
                    dbg_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    if getattr(sys, 'frozen', False):
                        dbg_base = os.path.dirname(os.path.dirname(sys.executable))
                    with open(os.path.join(dbg_base, "debug_t1716.txt"), "w", encoding="utf-8") as f:
                        f.write(f"code: {stock_code}\n")
                        f.write(f"url: {url}\n")
                        f.write(f"request_body: {json.dumps(body, ensure_ascii=False)}\n")
                        f.write(f"status: {res.status_code}\n")
                        f.write(f"response: {res.text[:3000]}\n")
                except:
                    pass
            if res.status_code != 200:
                if res.status_code in (429, 500):
                    import time as _time
                    _time.sleep(2)
                    res = self.session.post(url, headers=self._headers("t1716"),
                                        json=body, timeout=15)
                if res.status_code != 200:
                    print(f"[LS API] [실패] 수급 t1716 HTTP {res.status_code}: {res.text[:300]}")
                    return []
            data = res.json()
            rows = data.get("t1716OutBlock", data.get("t1716OutBlock1", []))
            if not rows:
                print(f"[LS API] ⚠ 수급 t1716 응답 키 없음({stock_code}): {list(data.keys())[:10]}")
            if isinstance(rows, dict):
                rows = [rows]
            result = []
            for r in rows:
                try:
                    # t1716 OutBlock 필드:
                    # krx_0008=개인, krx_0009=외국인, krx_0018=기관합계
                    # pgmvol=프로그램, fsc_0009=금감원외국인, gm_volume=기금(연기금)
                    foreign_net = int(float(r.get("krx_0009", r.get("forgn_netq", 0))))
                    inst_net    = int(float(r.get("krx_0018", r.get("orgn_netq",  0))))
                    personal    = int(float(r.get("krx_0008", 0)))
                    program     = int(float(r.get("pgmvol", 0)))
                    fund        = int(float(r.get("gm_volume", 0)))
                    fsc_foreign = int(float(r.get("fsc_0009", 0)))
                    result.append({
                        "date"       : str(r.get("date", "")),
                        "foreign_net": foreign_net,
                        "inst_net"   : inst_net,
                        "total_net"  : foreign_net + inst_net,
                        "personal"   : personal,
                        "program"    : program,
                        "fund"       : fund,
                        "fsc_foreign": fsc_foreign,
                    })
                except:
                    continue
            return result
        except Exception as e:
            print(f"[LS API] [실패] 수급 조회 실패({stock_code}): {e}")
            return []

    # ─────────────────────────────────────
    #  재무 데이터 조회 (t3320)
    # ─────────────────────────────────────
    def get_financial(self, stock_code: str) -> dict:
        """
        기업 재무 데이터 조회 (t3320)
        반환: {
            "roe": float, "roa": float,
            "op_profit_year": int, "op_profit_quarter": int,
            "op_profit_year_rate": float, "op_profit_quarter_rate": float,
            "reserve_ratio": float,
            "per": float, "pbr": float, "eps": int, "bps": int,
        }
        """
        if not self.ensure_token():
            return {}

        code = stock_code
        if code.startswith("A") and len(code) == 7:
            code = code[1:]

        body = {"t3320InBlock": {"gicode": code}}

        try:
            res = self.session.post(
                f"{self.base_url}/stock/investinfo",
                headers=self._headers("t3320"),
                json=body, timeout=15
            )
            if not res or res.status_code != 200:
                if res and res.status_code in (429, 500):
                    import time as _time
                    _time.sleep(2)
                    res = self.session.post(
                        f"{self.base_url}/stock/investinfo",
                        headers=self._headers("t3320"),
                        json=body, timeout=15)
                if not res or res.status_code != 200:
                    return {}

            data = res.json()
            out = data.get("t3320OutBlock", {})
            out1 = data.get("t3320OutBlock1", {})  # dict일 수 있음

            result = {}

            # OutBlock1이 dict인 경우: per/eps/pbr/roa/roe/bps 직접 읽기
            # (실제 API 응답에서 OutBlock1이 재무비율 dict로 옴)
            fin_src = out1 if isinstance(out1, dict) and out1 else out
            if fin_src:
                try:
                    result["per"] = float(fin_src.get("per", 0) or 0)
                    result["pbr"] = float(fin_src.get("pbr", 0) or 0)
                    result["eps"] = int(float(fin_src.get("eps", 0) or 0))
                    result["bps"] = int(float(fin_src.get("bps", 0) or 0))
                    result["roe"] = float(fin_src.get("roe", 0) or 0)
                    result["roa"] = float(fin_src.get("roa", 0) or 0)
                    result["ebitda"] = float(fin_src.get("ebitda", 0) or 0)
                except Exception:
                    pass

            # OutBlock에서 추가 정보 (유보율 등)
            if out and isinstance(out, dict):
                try:
                    if "cashrate" in out:
                        result["reserve_ratio"] = float(out.get("cashrate", 0) or 0)
                    elif "yg_rate" in out:
                        result["reserve_ratio"] = float(out.get("yg_rate", 0) or 0)
                except Exception:
                    pass

            # OutBlock1이 list인 경우 (혹시 다른 환경에서): 연도/분기별 실적
            if isinstance(out1, list) and out1:
                try:
                    yearly = [r for r in out1 if isinstance(r, dict) and r.get("gubun", "") in ("년", "Y", "annual")]
                    if len(yearly) >= 2:
                        cur = float(yearly[0].get("op_profit", yearly[0].get("영업이익", 0)) or 0)
                        prev = float(yearly[1].get("op_profit", yearly[1].get("영업이익", 0)) or 0)
                        result["op_profit_year"] = int(cur)
                        result["op_profit_year_rate"] = ((cur - prev) / abs(prev) * 100) if prev != 0 else 0

                    quarter = [r for r in out1 if isinstance(r, dict) and r.get("gubun", "") in ("분기", "Q", "quarter")]
                    if len(quarter) >= 2:
                        cur = float(quarter[0].get("op_profit", quarter[0].get("영업이익", 0)) or 0)
                        prev = float(quarter[1].get("op_profit", quarter[1].get("영업이익", 0)) or 0)
                        result["op_profit_quarter"] = int(cur)
                        result["op_profit_quarter_rate"] = ((cur - prev) / abs(prev) * 100) if prev != 0 else 0
                except Exception:
                    pass

            return result

        except Exception as e:
            print(f"[LS API] [실패] 재무 조회 실패({stock_code}): {e}")
            return {}

    # ─────────────────────────────────────
    #  재무순위종합 조회 (t3341) — 캐시 방식
    # ─────────────────────────────────────
    _t3341_cache = {}   # {gubun1: {code: {field: value}}}
    _t3341_loaded = set()

    def _load_t3341(self, gubun1: str) -> dict:
        """t3341 페이지네이션으로 전 종목 dict 캐시"""
        if gubun1 in self._t3341_loaded:
            return self._t3341_cache.get(gubun1, {})

        if not self.ensure_token():
            return {}

        cache = {}
        idx = 0
        max_pages = 20  # 최대 20페이지 (2000종목)

        try:
            for page in range(max_pages):
                body = {
                    "t3341InBlock": {
                        "gubun": "0",       # 시장구분: 0=전체
                        "gubun1": gubun1,   # 순위구분: 2=영업이익증가율, 5=유보율
                        "gubun2": "1",      # 대비구분: 1 고정
                        "idx": idx
                    }
                }

                headers = self._headers("t3341")
                if page > 0:
                    headers["tr_cont"] = "Y"

                res = self.session.post(
                    f"{self.base_url}/stock/investinfo",
                    headers=headers,
                    json=body, timeout=15
                )

                if res.status_code != 200:
                    break

                data = res.json()
                out = data.get("t3341OutBlock", {})
                out1 = data.get("t3341OutBlock1", [])

                if not isinstance(out1, list) or not out1:
                    break

                for item in out1:
                    if not isinstance(item, dict):
                        continue
                    item_code = item.get("shcode", "").replace("A", "")
                    if item_code:
                        cache[item_code] = item

                # 다음 페이지
                next_idx = out.get("idx", 0) if isinstance(out, dict) else 0
                if next_idx == 0 or next_idx == idx:
                    break
                idx = next_idx
                time.sleep(1.0)  # API 호출 간격 (너무 빠르면 빈 응답)

        except Exception as e:
            print(f"[LS API] t3341 gubun1={gubun1} 로드 실패: {e}")

        self._t3341_loaded.add(gubun1)
        self._t3341_cache[gubun1] = cache
        print(f"[LS API] t3341 gubun1={gubun1} 로드 완료: {len(cache)}종목")
        return cache

    def get_financial_ranking(self, stock_code: str) -> dict:
        """
        재무순위종합 (t3341) - 영업이익증가율, 유보율 조회
        한 번 호출 후 캐시에서 조회 (종목별 반복 호출 안함)
        """
        code = stock_code
        if code.startswith("A") and len(code) == 7:
            code = code[1:]

        result = {}

        # gubun1=2: 영업이익증가율
        cache2 = self._load_t3341("2")
        if code in cache2:
            item = cache2[code]
            val = item.get("operatingincomegrowt")
            if val is not None:
                try:
                    result["op_profit_year_rate"] = round(float(val or 0), 2)
                except (ValueError, TypeError):
                    pass

        # gubun1=5: 유보율
        cache5 = self._load_t3341("5")
        if code in cache5:
            item = cache5[code]
            val = item.get("enterpriseratio")
            if val is not None:
                try:
                    result["reserve_ratio"] = round(float(val or 0), 2)
                except (ValueError, TypeError):
                    pass

        return result

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

        # t8430 엔드포인트: /stock/etc 시도, 실패 시 /stock/market-data 폴백
        endpoints = [
            f"{self.base_url}/stock/etc",
            f"{self.base_url}/stock/market-data",
        ]
        body = {
            "t8430InBlock": {
                "gubun": market
            }
        }

        for url in endpoints:
            try:
                print(f"[LS API] t8430 요청: {url}")
                res = self.session.post(url, headers=self._headers("t8430"),
                                    json=body, timeout=30)

                # 디버그: 응답 기록
                self._debug_t8430(url, res)

                if res.status_code != 200:
                    print(f"[LS API] [실패] t8430 HTTP {res.status_code} @ {url} | {res.text[:200]}")
                    continue

                data = res.json()
                rows = data.get("t8430OutBlock", [])
                if isinstance(rows, dict):
                    rows = [rows]

                if not rows:
                    print(f"[LS API] [경고] t8430 응답 키: {list(data.keys())} | OutBlock 비어있음 @ {url}")
                    continue

                result = []
                for r in rows:
                    try:
                        code  = r.get("shcode", "").strip()
                        name  = r.get("hname",  "").strip()
                        mkt   = "KOSPI" if r.get("gubun", "") == "1" else "KOSDAQ"
                        # t8430은 price 필드 없음 → jnilclose(전일종가) 또는 recprice(기준가) 사용
                        price = int(float(r.get("price", 0) or r.get("jnilclose", 0) or r.get("recprice", 0)))
                        etf   = r.get("etfgubun", "0")
                        if not code or not name:
                            continue
                        # ETF/ETN 제외
                        if etf not in ("0", ""):
                            continue
                        # 가격 범위 사전 필터 (1000~500000)
                        if price > 0 and not (1000 <= price <= 500000):
                            continue
                        result.append({"code": code, "name": name,
                                       "market": mkt, "price": price})
                    except:
                        continue

                if result:
                    print(f"[LS API] [성공] 전종목 {len(result)}개 (raw:{len(rows)}) @ {url}")
                    # 성공 시 파일 캐시 (다음 실패 대비)
                    self._save_stock_cache(result)
                    return result
                else:
                    print(f"[LS API] [경고] 파싱 결과 0개 @ {url}")

            except Exception as e:
                print(f"[LS API] [실패] t8430 @ {url}: {e}")
                continue

        # 모든 엔드포인트 실패 → 파일 캐시에서 복구
        cached = self._load_stock_cache()
        if cached:
            print(f"[LS API] [복구] 캐시에서 {len(cached)}종목 로드")
            return cached

        print("[LS API] [실패] 전종목 조회 완전 실패 (캐시도 없음)")
        return []

    def _debug_t8430(self, url: str, res):
        """t8430 API 응답 디버그 파일 기록"""
        try:
            from config import load_config
            import os, sys
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(os.path.dirname(sys.executable))
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            dbg = {
                "url": url,
                "status": res.status_code,
                "headers": dict(res.headers),
                "body_preview": res.text[:500],
                "timestamp": datetime.now().isoformat(),
            }
            with open(os.path.join(base, "debug_t8430.json"), "w", encoding="utf-8") as f:
                json.dump(dbg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _save_stock_cache(self, stocks: list):
        """종목 리스트 파일 캐시 저장"""
        try:
            import os, sys
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(os.path.dirname(sys.executable))
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, "stock_list_cache.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"stocks": stocks, "date": datetime.now().strftime("%Y%m%d")}, f, ensure_ascii=False)
        except Exception:
            pass

    def _load_stock_cache(self) -> list:
        """종목 리스트 파일 캐시 로드 (당일 것만)"""
        try:
            import os, sys
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(os.path.dirname(sys.executable))
            else:
                base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, "stock_list_cache.json")
            if not os.path.exists(path):
                return []
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 당일 캐시만 사용
            if data.get("date") == datetime.now().strftime("%Y%m%d"):
                return data.get("stocks", [])
            return []
        except Exception:
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
                time.sleep(0.1)   # TPS 제한 대응
            body = {"t1511InBlock": {"upcode": upcode}}
            try:
                res = self.session.post(url, headers=self._headers("t1511"),
                                    json=body, timeout=10)
                if res.status_code != 200:
                    print(f"[t1511] {upcode} HTTP {res.status_code}: {res.text[:100]}")
                    continue  # 실패한 코드는 제외
                data = res.json()
                out = data.get("t1511OutBlock", {})
                if not out:
                    print(f"[t1511] {upcode} OutBlock 없음: {list(data.keys())}")
                    continue  # 데이터 없는 코드는 제외
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

                # 등락률: API가 직접 제공하는 diffjisu 사용
                try:
                    rt = float(str(row.get("diffjisu", 0)).replace(",", ""))
                except:
                    rt = 0.0
                # sign: 2=상승, 5=하락, 3=보합
                sign_cd = str(row.get("sign", "3"))
                if sign_cd == "5":
                    rt = -abs(rt)
                elif sign_cd == "2":
                    rt = abs(rt)
                sign_str = "+" if rt >= 0 else ""
                change_str = f"{sign_str}{rt:.2f}%"

                idx_str = f"{jisu:,.2f}" if jisu > 0 else "-"
                # 등락률 퍼센트 계산
                if jisu > 0:
                    diff_pct = rt / jisu * 100
                else:
                    diff_pct = 0.0

                results.append({
                    "name":    name,
                    "index":   idx_str,
                    "change":  change_str,
                    "diff":    round(diff_pct, 2),   # AI 캐시용 숫자 등락률
                    "foreign": "-",
                    "inst":    "-",
                })
                print(f"[t1511] [성공] {upcode} {name}: {idx_str} ({change_str})")
            except Exception as e:
                print(f"[t1511] {upcode} 오류: {e}")
                results.append({"name": display_name, "index": "-", "change": "-", "foreign": "-", "inst": "-"})

        print(f"[t1511] 업종지수 조회 완료: {len(results)}개")
        return results

    # ─────────────────────────────────────
    #  서버 조건검색 목록 조회 (t1866)
    # ─────────────────────────────────────
    def get_condition_list(self):
        """서버에 저장된 조건검색 목록 조회.
        Returns: [{"index": "...", "name": "..."}, ...] 또는 빈 리스트
        """
        # 디버그 경로
        import sys as _s
        _bd = os.path.dirname(os.path.dirname(_s.executable)) if getattr(_s, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        _dbg_path = os.path.join(_bd, "debug_t1866.txt")
        dbg_lines = []

        if not self.ensure_token():
            dbg_lines.append("FAIL: ensure_token() returned False")
            try:
                with open(_dbg_path, "w", encoding="utf-8") as _df:
                    _df.write("\n".join(dbg_lines))
            except Exception:
                pass
            return []

        url = f"{self.base_url}/stock/item-search"
        body = {"t1866InBlock": {"user_id": "kdw0924", "gb": "0", "group_name": "", "cont": "", "cont_key": ""}}
        dbg_lines.append(f"token: {self.access_token[:20]}...")
        dbg_lines.append(f"url: {url}")
        dbg_lines.append(f"body: {body}")

        try:
            res = self.session.post(url, headers=self._headers("t1866"),
                                    json=body, timeout=10)
            dbg_lines.append(f"status: {res.status_code}")
            dbg_lines.append(f"response: {res.text[:2000]}")

            res.raise_for_status()
            data = res.json()
            dbg_lines.append(f"keys: {list(data.keys())}")

            out = data.get("t1866OutBlock1", [])
            if isinstance(out, dict):
                out = [out]
            dbg_lines.append(f"OutBlock1 count: {len(out)}")

            result = []
            for item in out:
                group = str(item.get("group_name", "")).strip()
                name = str(item.get("query_name", "")).strip()
                display = f"[{group}] {name}" if group else name
                result.append({
                    "index": str(item.get("query_index", "")),
                    "name": display,
                    "group": group,
                })
            dbg_lines.append(f"result: {len(result)}개")
            for r in result:
                dbg_lines.append(f"  [{r['index']}] {r['name']}")
            return result
        except Exception as e:
            dbg_lines.append(f"EXCEPTION: {e}")
            return []
        finally:
            try:
                with open(_dbg_path, "w", encoding="utf-8") as _df:
                    _df.write("\n".join(dbg_lines))
            except Exception:
                pass

    # ─────────────────────────────────────
    #  서버 조건검색 실행 (t1859)
    # ─────────────────────────────────────
    def run_condition_search(self, query_index):
        """서버 조건검색 실행.
        Args: query_index - t1866에서 받은 조건 인덱스
        Returns: [{"code": "005930", "name": "삼성전자"}, ...] 또는 빈 리스트
        """
        import sys as _s
        _bd = os.path.dirname(os.path.dirname(_s.executable)) if getattr(_s, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        _dbg_path = os.path.join(_bd, "debug_t1859.txt")
        dbg = []

        if not self.ensure_token():
            dbg.append("FAIL: ensure_token")
            try:
                with open(_dbg_path, "w", encoding="utf-8") as f: f.write("\n".join(dbg))
            except: pass
            return []
        url = f"{self.base_url}/stock/item-search"
        body = {"t1859InBlock": {"query_index": str(query_index)}}
        dbg.append(f"query_index: [{query_index}]")
        dbg.append(f"url: {url}")

        try:
            all_results = []
            tr_cont = "N"
            tr_cont_key = ""
            page = 0

            while True:
                page += 1
                res = self.session.post(url,
                    headers=self._headers("t1859", tr_cont=tr_cont, tr_cont_key=tr_cont_key),
                    json=body, timeout=30)
                dbg.append(f"[page {page}] status: {res.status_code}")
                res.raise_for_status()
                data = res.json()

                out = data.get("t1859OutBlock1", [])
                if isinstance(out, dict):
                    out = [out]
                dbg.append(f"[page {page}] count: {len(out)}")

                for item in out:
                    code = str(item.get("shcode", "")).strip()
                    name = str(item.get("hname", "")).strip()
                    if code:
                        all_results.append({"code": code, "name": name})

                # 연속 조회 확인
                resp_cont = res.headers.get("tr_cont", "N")
                resp_cont_key = res.headers.get("tr_cont_key", "")
                dbg.append(f"[page {page}] tr_cont={resp_cont}, tr_cont_key={resp_cont_key}")

                if resp_cont == "Y" and resp_cont_key:
                    tr_cont = "Y"
                    tr_cont_key = resp_cont_key
                    time.sleep(0.3)
                else:
                    break

                if page >= 10:  # 안전장치
                    break

            dbg.append(f"TOTAL: {len(all_results)}종목")
            print(f"[t1859] 조건검색 '{query_index}' 결과: {len(all_results)}종목 ({page}페이지)")
            return all_results
        except Exception as e:
            dbg.append(f"EXCEPTION: {e}")
            print(f"[t1859] 오류: {e}")
            return []
        finally:
            try:
                with open(_dbg_path, "w", encoding="utf-8") as f: f.write("\n".join(dbg))
            except: pass


# ─────────────────────────────────────
#  테스트 실행
# ─────────────────────────────────────
if __name__ == "__main__":
    api = LSApi()
    print("=== LS Open API 연결 테스트 ===")
    if api.get_token():
        print("[성공] 토큰 발급 성공!")
        holdings, summary = api.get_holdings_for_ui()
        if holdings:
            print(f"[성공] 보유종목 {len(holdings)}개:")
            for h in holdings[:5]:
                print(f"  {h['name']} | {h['cur_price']} | {h['pnl_rate']}")
        print(f"계좌요약: {summary}")
    else:
        print("[실패] 연결 실패 - App Key/Secret 확인하세요")
