"""
xingAPI COM 연동 모듈
- 로그인 (모의/실전)
- t1857 e종목검색 (ACF 파일 기반 조건검색)
- t1404 관리/불성실/투자유의 조회
- t1405 투자경고/매매정지/정리매매 조회
"""
import os
import sys
import time
import json
import traceback
import pythoncom
import win32com.client

# xingAPI 설치 경로
XING_PATH = r"C:\ls_sec\xingapi"
RES_PATH = os.path.join(XING_PATH, "Res")


def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _debug_log(msg: str):
    """디버그 로그 파일에 기록"""
    try:
        path = os.path.join(_get_base_dir(), "debug_xing.txt")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


class XASessionEvents:
    """XA_Session 이벤트 핸들러"""
    login_ok = False
    login_msg = ""

    def OnLogin(self, code, msg):
        XASessionEvents.login_ok = (code == "0000")
        XASessionEvents.login_msg = msg

    def OnDisconnect(self):
        print("[xingAPI] 연결 해제됨")

    def OnLogout(self):
        print("[xingAPI] 로그아웃")


class XAQueryEvents:
    """XA_DataSet 이벤트 핸들러"""
    query_done = False
    query_msg_code = ""
    query_msg = ""

    def OnReceiveData(self, tr_code):
        XAQueryEvents.query_done = True

    def OnReceiveMessage(self, error, msg_code, msg):
        XAQueryEvents.query_msg_code = msg_code
        XAQueryEvents.query_msg = msg
        if error:
            print(f"[xingAPI] 오류: [{msg_code}] {msg}")


class XingAPI:
    """xingAPI COM 래퍼 클래스"""

    def __init__(self):
        self.session = None
        self.connected = False
        self.mode = "mock"  # "mock" or "real"
        self._login_id = ""
        self.account = ""
        self.accounts = []

    # ─────────────────────────────────────
    #  로그인
    # ─────────────────────────────────────
    def login(self, user_id: str, password: str, mode: str = "mock",
              cert_password: str = "", cert_path: str = "") -> tuple:
        """
        xingAPI COM 로그인
        Args:
            user_id: 사용자 ID
            password: 비밀번호
            mode: "mock" (모의투자) / "real" (실전투자)
            cert_password: 공인인증서 비밀번호 (실전만)
        Returns:
            (성공여부, 메시지)
        """
        # 디버그 로그 초기화
        try:
            path = os.path.join(_get_base_dir(), "debug_xing.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] === xingAPI 로그인 시작 ===\n")
        except Exception:
            pass

        try:
            # PyInstaller 환경에서 인증 모듈 DLL 로드를 위해 PATH 추가
            if XING_PATH not in os.environ.get("PATH", ""):
                os.environ["PATH"] = XING_PATH + ";" + os.environ.get("PATH", "")
                _debug_log(f"PATH에 xingAPI 경로 추가: {XING_PATH}")

            _debug_log(f"CoInitialize 시작")
            pythoncom.CoInitialize()
            _debug_log(f"CoInitialize 완료")

            _debug_log(f"XA_Session 생성 시작")
            self.session = win32com.client.DispatchWithEvents(
                "XA_Session.XASession", XASessionEvents
            )
            _debug_log(f"XA_Session 생성 완료")
            self.mode = mode
            self._login_id = user_id

            # 서버 연결
            if mode == "real":
                server = "hts.ls-sec.co.kr"
            else:
                server = "demo.ls-sec.co.kr"

            # xingAPI 모듈 경로 설정 (인증 모듈 DLL 위치)
            try:
                self.session.SetPath(XING_PATH)
                _debug_log(f"SetPath: {XING_PATH}")
            except Exception as e:
                _debug_log(f"SetPath 오류: {e}")

            _debug_log(f"ConnectServer: {server}:20001")
            self.session.ConnectServer(server, 20001)
            _debug_log(f"ConnectServer 완료")

            # 로그인
            XASessionEvents.login_ok = False
            XASessionEvents.login_msg = ""

            server_type = 0
            show_cert_err = (mode == "real")
            _debug_log(f"Login 호출: user={user_id}, mode={mode}, server_type={server_type}")
            self.session.Login(user_id, password, cert_password, server_type, show_cert_err)

            # 로그인 응답 대기 (최대 30초)
            for i in range(300):
                pythoncom.PumpWaitingMessages()
                if XASessionEvents.login_msg:
                    break
                time.sleep(0.1)

            _debug_log(f"Login 결과: ok={XASessionEvents.login_ok}, msg={XASessionEvents.login_msg}")

            if XASessionEvents.login_ok:
                self.connected = True
                # 계좌번호 저장
                try:
                    acc_count = self.session.GetAccountListCount()
                    self.accounts = []
                    for i in range(acc_count):
                        self.accounts.append(self.session.GetAccountList(i))
                    if self.accounts:
                        self.account = self.accounts[0]
                        _debug_log(f"계좌: {self.accounts}")
                except Exception:
                    self.account = ""
                    self.accounts = []
                _debug_log(f"로그인 성공: {server} ({mode})")
                return True, XASessionEvents.login_msg
            else:
                _debug_log(f"로그인 실패: {XASessionEvents.login_msg}")
                return False, XASessionEvents.login_msg

        except Exception as e:
            _debug_log(f"로그인 예외: {e}\n{traceback.format_exc()}")
            return False, str(e)

    def logout(self):
        """로그아웃 및 연결 해제"""
        try:
            if self.session and self.connected:
                self.session.DisconnectServer()
                self.connected = False
                print("[xingAPI] 로그아웃 완료")
        except Exception as e:
            print(f"[xingAPI] 로그아웃 오류: {e}")

    def is_connected(self) -> bool:
        return self.connected

    # ─────────────────────────────────────
    #  TR 조회 헬퍼
    # ─────────────────────────────────────
    def _query_tr(self, tr_code: str, in_block: str, fields: dict,
                  timeout: float = 10.0) -> object:
        """
        TR 조회 공통 헬퍼
        Returns: XAQuery 객체 (결과 읽기용) 또는 None
        """
        if not self.connected:
            _debug_log(f"{tr_code} 미연결 상태 - 조회 불가")
            return None

        try:
            _debug_log(f"{tr_code} XAQuery 생성")
            query = win32com.client.DispatchWithEvents(
                "XA_DataSet.XAQuery", XAQueryEvents
            )
            res_file = os.path.join(RES_PATH, f"{tr_code}.res")
            _debug_log(f"{tr_code} ResFile: {res_file} (존재: {os.path.exists(res_file)})")
            query.ResFileName = res_file

            # InBlock 필드 설정
            for field_name, value in fields.items():
                query.SetFieldData(in_block, field_name, 0, str(value))

            # 요청
            XAQueryEvents.query_done = False
            XAQueryEvents.query_msg_code = ""
            XAQueryEvents.query_msg = ""

            # t1857은 RequestService 사용 (일반 Request로는 동작 안 함)
            if tr_code == "t1857":
                ret = query.RequestService(tr_code, "")
                _debug_log(f"{tr_code} RequestService 반환: {ret}")
            else:
                ret = query.Request(False)
                _debug_log(f"{tr_code} Request 반환: {ret}")
            if ret < 0:
                _debug_log(f"{tr_code} 요청 실패: {ret}")
                return None

            # 응답 대기
            elapsed = 0
            while not XAQueryEvents.query_done and elapsed < timeout:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.1)
                elapsed += 0.1

            _debug_log(f"{tr_code} 응답: done={XAQueryEvents.query_done}, msg=[{XAQueryEvents.query_msg_code}] {XAQueryEvents.query_msg}, elapsed={elapsed:.1f}s")

            if not XAQueryEvents.query_done:
                _debug_log(f"{tr_code} 타임아웃 ({timeout}초)")
                return None

            return query

        except Exception as e:
            _debug_log(f"{tr_code} 예외: {e}\n{traceback.format_exc()}")
            return None

    # ─────────────────────────────────────
    #  t1857 e종목검색 (ACF 파일 기반)
    # ─────────────────────────────────────
    def search_by_condition(self, acf_path: str, real_time: bool = False) -> list:
        """
        ACF 파일 기반 조건검색 (t1857)
        Args:
            acf_path: ACF 파일 경로
            real_time: True면 실시간 감시, False면 1회 조회
        Returns:
            [{"code": "005930", "name": "삼성전자", "price": 70000, ...}, ...]
        """
        # 경로를 Windows 형식으로 변환
        acf_path = os.path.normpath(acf_path)
        _debug_log(f"t1857 조건검색 시작: {acf_path}")
        if not os.path.exists(acf_path):
            _debug_log(f"ACF 파일 없음: {acf_path}")
            return []

        # xingAPI Condi 폴더에 ACF 복사 (COM이 여기서 찾을 수 있음)
        try:
            condi_dir = os.path.join(XING_PATH, "Condi")
            os.makedirs(condi_dir, exist_ok=True)
            condi_copy = os.path.join(condi_dir, os.path.basename(acf_path))
            if not os.path.exists(condi_copy) or \
               os.path.getmtime(acf_path) > os.path.getmtime(condi_copy):
                import shutil
                shutil.copy2(acf_path, condi_copy)
                _debug_log(f"ACF 복사: {condi_copy}")
        except Exception as e:
            _debug_log(f"ACF 복사 실패: {e}")

        fields = {
            "sRealFlag": "1" if real_time else "0",
            "sSearchFlag": "F",           # F: 파일검색
            "query_index": acf_path,
        }
        _debug_log(f"t1857 조건검색: query_index={acf_path}")

        query = self._query_tr("t1857", "t1857InBlock", fields, timeout=30.0)
        if not query:
            _debug_log("t1857 _query_tr 반환값 None")
            print("[xingAPI] t1857 조건검색 실패")
            return []

        # OutBlock: 검색종목수
        try:
            result_count = int(query.GetFieldData("t1857OutBlock", "result_count", 0) or 0)
        except Exception as e:
            _debug_log(f"t1857 result_count 파싱 오류: {e}")
            result_count = 0

        _debug_log(f"t1857 결과: {result_count}종목")
        print(f"[xingAPI] t1857 조건검색 결과: {result_count}종목")

        # OutBlock1: 종목 리스트
        results = []
        for i in range(result_count):
            try:
                code = query.GetFieldData("t1857OutBlock1", "shcode", i).strip()
                name = query.GetFieldData("t1857OutBlock1", "hname", i).strip()
                price = int(query.GetFieldData("t1857OutBlock1", "price", i) or 0)
                sign = query.GetFieldData("t1857OutBlock1", "sign", i).strip()
                change = int(query.GetFieldData("t1857OutBlock1", "change", i) or 0)
                diff = float(query.GetFieldData("t1857OutBlock1", "diff", i) or 0)
                volume = int(query.GetFieldData("t1857OutBlock1", "volume", i) or 0)
                job_flag = query.GetFieldData("t1857OutBlock1", "JobFlag", i).strip()

                if code:
                    results.append({
                        "code": code,
                        "name": name,
                        "price": price,
                        "sign": sign,
                        "change": change,
                        "diff": diff,
                        "volume": volume,
                        "job_flag": job_flag,
                    })
            except Exception as e:
                print(f"[xingAPI] t1857 행 {i} 파싱 오류: {e}")
                continue

        return results

    # ─────────────────────────────────────
    #  t1866 서버저장조건 리스트 조회
    # ─────────────────────────────────────
    def get_server_conditions(self) -> list:
        """
        서버에 저장된 조건식 목록 조회 (t1866)
        Returns:
            [{"index": "kdw0924 0001", "group": "매수", "name": "기본"}, ...]
        """
        fields = {
            "user_id": self._login_id,
            "gb": "0",
            "group_name": "",
            "cont": "",
            "cont_key": "",
        }
        query = self._query_tr("t1866", "t1866InBlock", fields)
        if not query:
            return []

        try:
            count = int(query.GetFieldData("t1866OutBlock", "result_count", 0) or 0)
        except Exception:
            count = 0

        conditions = []
        for i in range(count):
            try:
                idx = query.GetFieldData("t1866OutBlock1", "query_index", i).strip()
                grp = query.GetFieldData("t1866OutBlock1", "group_name", i).strip()
                name = query.GetFieldData("t1866OutBlock1", "query_name", i).strip()
                conditions.append({"index": idx, "group": grp, "name": name})
            except Exception:
                break

        print(f"[xingAPI] t1866 서버조건: {len(conditions)}개")
        return conditions

    # ─────────────────────────────────────
    #  t1857 서버 조건 검색
    # ─────────────────────────────────────
    def search_by_server_condition(self, query_index: str) -> list:
        """
        서버 저장 조건으로 검색 (t1857 sSearchFlag=S)
        Args:
            query_index: t1866에서 받은 조건 index (예: "kdw0924 0001")
        Returns:
            [{"code": "005930", "name": "삼성전자", ...}, ...]
        """
        fields = {
            "sRealFlag": "0",
            "sSearchFlag": "S",
            "query_index": query_index,
        }
        _debug_log(f"t1857 서버조건 검색: index={query_index}")

        query = self._query_tr("t1857", "t1857InBlock", fields, timeout=30.0)
        if not query:
            return []

        try:
            result_count = int(query.GetFieldData("t1857OutBlock", "result_count", 0) or 0)
        except Exception:
            result_count = 0

        _debug_log(f"t1857 서버조건 결과: {result_count}종목")
        print(f"[xingAPI] t1857 서버조건 결과: {result_count}종목")

        results = []
        for i in range(result_count):
            try:
                code = query.GetFieldData("t1857OutBlock1", "shcode", i).strip()
                name = query.GetFieldData("t1857OutBlock1", "hname", i).strip()
                price = int(query.GetFieldData("t1857OutBlock1", "price", i) or 0)
                sign = query.GetFieldData("t1857OutBlock1", "sign", i).strip()
                change = int(query.GetFieldData("t1857OutBlock1", "change", i) or 0)
                diff = float(query.GetFieldData("t1857OutBlock1", "diff", i) or 0)
                volume = int(query.GetFieldData("t1857OutBlock1", "volume", i) or 0)
                job_flag = query.GetFieldData("t1857OutBlock1", "JobFlag", i).strip()

                if code:
                    results.append({
                        "code": code,
                        "name": name,
                        "price": price,
                        "sign": sign,
                        "change": change,
                        "diff": diff,
                        "volume": volume,
                        "job_flag": job_flag,
                    })
            except Exception as e:
                _debug_log(f"t1857 서버조건 행 {i} 파싱 오류: {e}")
                continue

        return results

    # ─────────────────────────────────────
    #  t1404 관리/불성실/투자유의 조회
    # ─────────────────────────────────────
    def get_managed_stocks(self, gubun: str = "0") -> list:
        """
        관리종목/불성실공시/투자유의 종목 조회 (t1404)
        Args:
            gubun: 0=관리, 1=불성실, 2=투자유의
        Returns:
            [{"code": "...", "name": "...", "type": "..."}, ...]
        """
        fields = {"gubun": gubun}
        query = self._query_tr("t1404", "t1404InBlock", fields)
        if not query:
            return []

        results = []
        idx = 0
        while True:
            try:
                code = query.GetFieldData("t1404OutBlock1", "shcode", idx)
                if not code or not code.strip():
                    break
                name = query.GetFieldData("t1404OutBlock1", "hname", idx).strip()
                results.append({
                    "code": code.strip(),
                    "name": name,
                    "type": ["관리종목", "불성실공시", "투자유의"][int(gubun)],
                })
                idx += 1
            except Exception:
                break

        print(f"[xingAPI] t1404 ({['관리종목','불성실공시','투자유의'][int(gubun)]}): {len(results)}종목")
        return results

    # ─────────────────────────────────────
    #  t1405 투자경고/매매정지/정리매매 조회
    # ─────────────────────────────────────
    def get_warning_stocks(self, gubun: str = "0") -> list:
        """
        투자경고/매매정지/정리매매 종목 조회 (t1405)
        Args:
            gubun: 0=투자경고, 1=매매정지, 2=정리매매
        Returns:
            [{"code": "...", "name": "...", "type": "..."}, ...]
        """
        fields = {"gubun": gubun}
        query = self._query_tr("t1405", "t1405InBlock", fields)
        if not query:
            return []

        results = []
        idx = 0
        while True:
            try:
                code = query.GetFieldData("t1405OutBlock1", "shcode", idx)
                if not code or not code.strip():
                    break
                name = query.GetFieldData("t1405OutBlock1", "hname", idx).strip()
                results.append({
                    "code": code.strip(),
                    "name": name,
                    "type": ["투자경고", "매매정지", "정리매매"][int(gubun)],
                })
                idx += 1
            except Exception:
                break

        print(f"[xingAPI] t1405 ({['투자경고','매매정지','정리매매'][int(gubun)]}): {len(results)}종목")
        return results

    # ─────────────────────────────────────
    #  제외종목 전체 조회 (t1404 + t1405)
    # ─────────────────────────────────────
    def get_all_excluded_codes(self) -> set:
        """
        제외해야 할 종목코드 전체 SET 반환
        관리종목 + 불성실공시 + 투자유의 + 투자경고 + 매매정지 + 정리매매
        """
        excluded = set()

        # t1404: 관리(0), 불성실(1), 투자유의(2)
        for g in ["0", "1", "2"]:
            stocks = self.get_managed_stocks(g)
            for s in stocks:
                excluded.add(s["code"])
            time.sleep(1.0)  # TPS 제한

        # t1405: 투자경고(0), 매매정지(1), 정리매매(2)
        for g in ["0", "1", "2"]:
            stocks = self.get_warning_stocks(g)
            for s in stocks:
                excluded.add(s["code"])
            time.sleep(1.0)  # TPS 제한

        print(f"[xingAPI] 제외종목 합계: {len(excluded)}종목")
        return excluded

    # ─────────────────────────────────────
    #  창고 저장 (조건검색 결과)
    # ─────────────────────────────────────
    def save_warehouse(self, stocks: list, path: str = None):
        """
        조건검색 결과를 창고 파일로 저장
        """
        if path is None:
            base = _get_base_dir()
            mode_str = "mock" if self.mode == "mock" else "real"
            path = os.path.join(base, f"warehouse_{mode_str}.json")

        data = {
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": self.mode,
            "count": len(stocks),
            "stocks": stocks,
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[xingAPI] 창고 저장: {len(stocks)}종목 → {path}")
        except Exception as e:
            print(f"[xingAPI] 창고 저장 오류: {e}")

    @staticmethod
    def load_warehouse(mode: str = "mock") -> list:
        """
        창고 파일에서 종목 리스트 로드
        Returns: [{"code": "...", "name": "...", ...}, ...]
        """
        base = _get_base_dir()
        path = os.path.join(base, f"warehouse_{mode}.json")

        if not os.path.exists(path):
            print(f"[xingAPI] 창고 파일 없음: {path}")
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            stocks = data.get("stocks", [])
            updated = data.get("updated", "?")
            print(f"[xingAPI] 창고 로드: {len(stocks)}종목 (갱신: {updated})")
            return stocks
        except Exception as e:
            print(f"[xingAPI] 창고 로드 오류: {e}")
            return []

    # ─────────────────────────────────────
    #  t1511 업종/지수 현재가
    # ─────────────────────────────────────
    def get_market_index(self, upcode: str = "001") -> dict | None:
        """
        업종/지수 현재가 조회 (t1511)
        upcode: 001=KOSPI종합, 301=KOSDAQ종합
        Returns: {"jisu": "2,845.12", "sign": "2", "change": "+15.30", "diff": "+0.54", ...}
        """
        query = self._query_tr("t1511", "t1511InBlock", {"upcode": upcode})
        if not query:
            return None
        try:
            out = {}
            for field in ["pricejisu", "jniljisu", "sign", "change",
                          "diffjisu", "volume", "openjisu", "highjisu", "lowjisu"]:
                val = query.GetFieldData("t1511OutBlock", field, 0)
                out[field] = val
            return out if out.get("pricejisu") else None
        except Exception as e:
            print(f"[xingAPI] t1511 오류: {e}")
            return None

    # ─────────────────────────────────────
    #  t8407 멀티종목 현재가 (등락률 등)
    # ─────────────────────────────────────
    def get_multi_price(self, codes: list) -> dict:
        """
        멀티종목 현재가 조회 (t8407)
        codes: ["005930", "000660", ...]
        Returns: {"005930": {"price":73400, "sign":"2", "change":500, "diff":0.69}, ...}
        """
        if not codes:
            return {}
        shcode = "".join(c.ljust(6) for c in codes[:50])
        query = self._query_tr("t8407", "t8407InBlock", {
            "nrec": len(codes[:50]),
            "shcode": shcode,
        })
        if not query:
            return {}
        try:
            count = query.GetBlockCount("t8407OutBlock1")
            result = {}
            for i in range(count):
                code = query.GetFieldData("t8407OutBlock1", "shcode", i).strip()
                if not code:
                    continue
                try:
                    price = int(query.GetFieldData("t8407OutBlock1", "price", i) or 0)
                    sign = query.GetFieldData("t8407OutBlock1", "sign", i).strip()
                    change = int(query.GetFieldData("t8407OutBlock1", "change", i) or 0)
                    diff = float(query.GetFieldData("t8407OutBlock1", "diff", i) or 0)
                    jnilclose = int(query.GetFieldData("t8407OutBlock1", "jnilclose", i) or 0)
                except (ValueError, TypeError):
                    price = change = jnilclose = 0
                    sign = "3"
                    diff = 0.0
                result[code] = {
                    "price": price,
                    "sign": sign,
                    "change": change,
                    "diff": diff,
                    "jnilclose": jnilclose,
                }
            return result
        except Exception as e:
            print(f"[xingAPI] t8407 오류: {e}")
            return {}

    # ─────────────────────────────────────
    #  t0424 주식잔고 조회
    # ─────────────────────────────────────
    def get_holdings(self) -> tuple:
        """
        주식잔고 조회 (t0424)
        Returns: (holdings_list, summary_dict)
        holdings_list: 잔고>0인 보유종목만
        summary_dict: 서버 OutBlock 요약 그대로 (HTS와 동일)
        """
        if not self.account:
            print("[xingAPI] t0424: 계좌번호 없음")
            return [], {}
        query = self._query_tr("t0424", "t0424InBlock", {
            "accno": self.account,
            "passwd": "",
            "prcgb": "2",
            "chegb": "0",
            "dangb": "0",
            "charge": "0",
            "cts_expcode": "",
        })
        if not query:
            return [], {}

        try:
            # OutBlock (서버 요약)
            summary = {}
            for field in ["sunamt", "dtsunik", "mamt", "sunamt1",
                          "cts_expcode", "tappamt", "tdtsunik"]:
                summary[field] = query.GetFieldData("t0424OutBlock", field, 0)
            _debug_log(f"t0424 OutBlock: {summary}")

            # OutBlock1 (종목별)
            count = query.GetBlockCount("t0424OutBlock1")
            _debug_log(f"t0424 전체 {count}종목")
            holdings = []
            for i in range(count):
                item = {}
                for field in ["expcode", "jangb", "janqty", "mdposqt",
                              "pamt", "mamt", "sinamt", "lastdt",
                              "msat", "mpms", "mdat", "mpmd",
                              "jsat", "jpms", "jdat", "jpmd",
                              "hname", "price", "appamt", "dtsunik",
                              "sunikrt", "fee", "tax"]:
                    item[field] = query.GetFieldData("t0424OutBlock1", field, i)

                code = item.get("expcode", "")
                if not code:
                    continue

                try:
                    qty = int(item.get("janqty", "0"))
                    buy_price = int(item.get("pamt", "0"))
                    cur_price = int(item.get("price", "0"))
                    eval_amt = int(item.get("appamt", "0"))
                    pnl_amt = int(item.get("dtsunik", "0"))
                    pnl_rate = float(item.get("sunikrt", "0"))
                except (ValueError, TypeError):
                    qty = buy_price = cur_price = eval_amt = pnl_amt = 0
                    pnl_rate = 0.0

                # 전 종목 디버그 (잔고 유무 관계없이)
                _debug_log(f"  [{i}] {item.get('hname','')}({code}) 잔고={qty} 매입단가={buy_price} 현재가={cur_price} 평가={eval_amt} 손익={pnl_amt} 수익률={pnl_rate} 매입금액={item.get('mamt','')} 수수료={item.get('fee','')} 세금={item.get('tax','')}")

                if qty <= 0:
                    continue

                holdings.append({
                    "code": code,
                    "name": item.get("hname", ""),
                    "qty": qty,
                    "buy_price": buy_price,
                    "cur_price": cur_price,
                    "eval_amt": eval_amt,
                    "pnl_amt": pnl_amt,
                    "pnl_rate": pnl_rate,
                })
            _debug_log(f"t0424 보유={len(holdings)}종목 (제외={count - len(holdings)})")
            return holdings, summary
        except Exception as e:
            print(f"[xingAPI] t0424 오류: {e}")
            return [], {}

    # ─────────────────────────────────────
    #  조건검색 + 통합 실행
    # ─────────────────────────────────────
    def run_full_scan(self, acf_path: str) -> list:
        """
        ACF 조건검색 실행 → 제외종목 필터 → 창고 저장
        Returns: 최종 종목 리스트
        """
        print("=" * 50)
        print("[xingAPI] 전체 스캔 시작")
        print("=" * 50)

        # 1. ACF 조건검색
        stocks = self.search_by_condition(acf_path)
        if not stocks:
            # 장중이면 창고 비움, 장 외 시간이면 기존 창고 유지
            from datetime import datetime
            now_hm = datetime.now().strftime("%H:%M")
            weekday = datetime.now().weekday()  # 0=월 ~ 6=일
            is_market_hours = weekday < 5 and "09:00" <= now_hm <= "15:30"
            if is_market_hours:
                print("[xingAPI] 조건검색 결과 없음 (장중) → 창고 비움")
                self.save_warehouse([])
            else:
                print("[xingAPI] 조건검색 결과 없음 (장외) → 기존 창고 유지")
            return []
        print(f"[xingAPI] 1단계 조건검색: {len(stocks)}종목")

        # 2. 창고 저장 (ACF에서 이미 필터 적용됨)
        self.save_warehouse(stocks)

        print("=" * 50)
        print(f"[xingAPI] 전체 스캔 완료: 최종 {len(stocks)}종목")
        print("=" * 50)

        return stocks


# ─────────────────────────────────────
#  테스트용
# ─────────────────────────────────────
if __name__ == "__main__":
    xing = XingAPI()

    # 모의투자 로그인 테스트
    ok, msg = xing.login("kdw0924", "비밀번호", mode="mock")
    print(f"로그인: {ok} - {msg}")

    if ok:
        # ACF 조건검색 테스트
        acf = r"C:\Users\force\Downloads\기본찾기.ACF"
        if os.path.exists(acf):
            results = xing.run_full_scan(acf)
            for s in results[:10]:
                print(f"  {s['code']} {s['name']} {s['price']:,}")

        xing.logout()
