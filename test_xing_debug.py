"""
xingAPI COM 진단 스크립트 v3
- RequestService + LoadFromResFile 방식으로 t1857 테스트
"""
import os
import sys
import time
import pythoncom
import win32com.client

XING_PATH = r"C:\ls_sec\xingapi"
RES_PATH = os.path.join(XING_PATH, "Res")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_xing_diag.txt")


def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class SessionEvents:
    login_ok = False
    login_msg = ""
    def OnLogin(self, code, msg):
        SessionEvents.login_ok = (code == "0000")
        SessionEvents.login_msg = msg
    def OnDisconnect(self):
        log("세션 연결 해제")


class QueryEvents:
    done = False
    msg_code = ""
    msg_text = ""
    def OnReceiveData(self, tr_code):
        QueryEvents.done = True
        log(f"  [이벤트] OnReceiveData: {tr_code}")
    def OnReceiveMessage(self, error, msg_code, msg):
        QueryEvents.msg_code = msg_code
        QueryEvents.msg_text = msg
        log(f"  [이벤트] OnReceiveMessage: error={error}, code={msg_code}, msg={msg}")
    def OnReceiveSearchRealData(self, tr_code):
        QueryEvents.done = True
        log(f"  [이벤트] OnReceiveSearchRealData: {tr_code}")


def wait_response(timeout=30.0):
    elapsed = 0
    while not QueryEvents.done and elapsed < timeout:
        pythoncom.PumpWaitingMessages()
        time.sleep(0.05)
        elapsed += 0.05
    return QueryEvents.done


def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] === xingAPI 진단 v3 (RequestService) ===\n")

    pythoncom.CoInitialize()

    # ── 로그인 ──
    log("로그인 시작...")
    session = win32com.client.DispatchWithEvents("XA_Session.XASession", SessionEvents)
    session.ConnectServer("demo.ls-sec.co.kr", 20001)

    SessionEvents.login_ok = False
    SessionEvents.login_msg = ""

    user_id = input("ID: ").strip()
    password = input("PW: ").strip()
    session.Login(user_id, password, "", 0, False)

    for _ in range(300):
        pythoncom.PumpWaitingMessages()
        if SessionEvents.login_msg:
            break
        time.sleep(0.1)

    if not SessionEvents.login_ok:
        log(f"❌ 로그인 실패: {SessionEvents.login_msg}")
        return
    log(f"✅ 로그인 성공")
    time.sleep(1)

    # ── t1866 서버조건 목록 (기존 방식 - 정상 동작 확인용) ──
    log("=" * 50)
    log("t1866 서버조건 목록 조회")
    log("=" * 50)

    QueryEvents.done = False
    QueryEvents.msg_code = ""
    QueryEvents.msg_text = ""

    q1866 = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", QueryEvents)
    q1866.ResFileName = os.path.join(RES_PATH, "t1866.res")
    q1866.SetFieldData("t1866InBlock", "user_id", 0, user_id)
    q1866.SetFieldData("t1866InBlock", "gb", 0, "0")
    q1866.SetFieldData("t1866InBlock", "group_name", 0, "")
    q1866.SetFieldData("t1866InBlock", "cont", 0, "")
    q1866.SetFieldData("t1866InBlock", "cont_key", 0, "")
    ret = q1866.Request(False)
    log(f"  Request 반환: {ret}")
    wait_response()

    count = int(q1866.GetFieldData("t1866OutBlock", "result_count", 0) or 0)
    log(f"  서버조건 수: {count}")
    conditions = []
    for i in range(count):
        idx = q1866.GetFieldData("t1866OutBlock1", "query_index", i).strip()
        grp = q1866.GetFieldData("t1866OutBlock1", "group_name", i).strip()
        name = q1866.GetFieldData("t1866OutBlock1", "query_name", i).strip()
        log(f"  [{i}] index='{idx}' group={grp} name={name}")
        conditions.append(idx)

    time.sleep(1.5)

    # ── t1857 테스트: 방법1 - RequestService + 서버조건 ──
    if conditions:
        log("")
        log("=" * 50)
        log("방법1: RequestService + 서버조건 (sSearchFlag=S)")
        log("=" * 50)

        for cond_idx in conditions[:3]:  # 처음 3개만 테스트
            QueryEvents.done = False
            QueryEvents.msg_code = ""
            QueryEvents.msg_text = ""

            q = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", QueryEvents)
            res_file = os.path.join(RES_PATH, "t1857.res")
            q.ResFileName = res_file

            q.SetFieldData("t1857InBlock", "sRealFlag", 0, "0")
            q.SetFieldData("t1857InBlock", "sSearchFlag", 0, "S")
            q.SetFieldData("t1857InBlock", "query_index", 0, cond_idx)

            log(f"  index='{cond_idx}' → RequestService 호출")
            ret = q.RequestService("t1857", "")
            log(f"  RequestService 반환: {ret}")

            if ret < 0:
                log(f"  ❌ 실패 (ret={ret})")
            elif wait_response():
                cnt = q.GetFieldData("t1857OutBlock", "result_count", 0)
                log(f"  result_count='{cnt}'")
                cnt_int = int(cnt or 0)
                if cnt_int > 0:
                    log(f"  ✅ {cnt_int}종목!")
                    for i in range(min(cnt_int, 5)):
                        code = q.GetFieldData("t1857OutBlock1", "shcode", i).strip()
                        name = q.GetFieldData("t1857OutBlock1", "hname", i).strip()
                        log(f"    {code} {name}")
                else:
                    log(f"  결과: 0종목")
            else:
                log(f"  ❌ 타임아웃")

            time.sleep(1.5)

    # ── t1857 테스트: 방법2 - RequestService + ACF 파일 ──
    acf_path = os.path.normpath(r"C:\Users\force\Downloads\모의자동.ACF")
    if os.path.exists(acf_path):
        log("")
        log("=" * 50)
        log("방법2: RequestService + ACF 파일 (sSearchFlag=F)")
        log("=" * 50)

        QueryEvents.done = False
        QueryEvents.msg_code = ""
        QueryEvents.msg_text = ""

        q = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", QueryEvents)
        q.ResFileName = os.path.join(RES_PATH, "t1857.res")

        q.SetFieldData("t1857InBlock", "sRealFlag", 0, "0")
        q.SetFieldData("t1857InBlock", "sSearchFlag", 0, "F")
        q.SetFieldData("t1857InBlock", "query_index", 0, acf_path)

        log(f"  ACF='{acf_path}' → RequestService 호출")
        ret = q.RequestService("t1857", "")
        log(f"  RequestService 반환: {ret}")

        if ret < 0:
            log(f"  ❌ 실패 (ret={ret})")
        elif wait_response():
            cnt = q.GetFieldData("t1857OutBlock", "result_count", 0)
            log(f"  result_count='{cnt}'")
            cnt_int = int(cnt or 0)
            if cnt_int > 0:
                log(f"  ✅ {cnt_int}종목!")
                for i in range(min(cnt_int, 10)):
                    code = q.GetFieldData("t1857OutBlock1", "shcode", i).strip()
                    name = q.GetFieldData("t1857OutBlock1", "hname", i).strip()
                    log(f"    {code} {name}")
            else:
                log(f"  결과: 0종목")
        else:
            log(f"  ❌ 타임아웃")

    # ── t1857 테스트: 방법3 - LoadFromResFile + RequestService ──
    if conditions:
        log("")
        log("=" * 50)
        log("방법3: LoadFromResFile + RequestService + 서버조건")
        log("=" * 50)

        cond_idx = conditions[0]

        QueryEvents.done = False
        QueryEvents.msg_code = ""
        QueryEvents.msg_text = ""

        q = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", QueryEvents)
        res_file = os.path.join(RES_PATH, "t1857.res")
        q.LoadFromResFile(res_file)

        q.SetFieldData("t1857InBlock", "sRealFlag", 0, "0")
        q.SetFieldData("t1857InBlock", "sSearchFlag", 0, "S")
        q.SetFieldData("t1857InBlock", "query_index", 0, cond_idx)

        log(f"  LoadFromResFile + index='{cond_idx}' → RequestService")
        ret = q.RequestService("t1857", "")
        log(f"  RequestService 반환: {ret}")

        if ret < 0:
            log(f"  ❌ 실패 (ret={ret})")
        elif wait_response():
            cnt = q.GetFieldData("t1857OutBlock", "result_count", 0)
            log(f"  result_count='{cnt}'")
            cnt_int = int(cnt or 0)
            if cnt_int > 0:
                log(f"  ✅ {cnt_int}종목!")
                for i in range(min(cnt_int, 10)):
                    code = q.GetFieldData("t1857OutBlock1", "shcode", i).strip()
                    name = q.GetFieldData("t1857OutBlock1", "hname", i).strip()
                    log(f"    {code} {name}")
            else:
                log(f"  결과: 0종목")
        else:
            log(f"  ❌ 타임아웃")

    # ── t1857 테스트: 방법4 - Request(False) + LoadFromResFile ──
    if conditions:
        log("")
        log("=" * 50)
        log("방법4: LoadFromResFile + Request(False) + 서버조건")
        log("=" * 50)

        cond_idx = conditions[0]

        QueryEvents.done = False
        QueryEvents.msg_code = ""
        QueryEvents.msg_text = ""

        q = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", QueryEvents)
        res_file = os.path.join(RES_PATH, "t1857.res")
        q.LoadFromResFile(res_file)

        q.SetFieldData("t1857InBlock", "sRealFlag", 0, "0")
        q.SetFieldData("t1857InBlock", "sSearchFlag", 0, "S")
        q.SetFieldData("t1857InBlock", "query_index", 0, cond_idx)

        log(f"  LoadFromResFile + index='{cond_idx}' → Request(False)")
        ret = q.Request(False)
        log(f"  Request 반환: {ret}")

        if ret < 0:
            log(f"  ❌ 실패 (ret={ret})")
        elif wait_response():
            cnt = q.GetFieldData("t1857OutBlock", "result_count", 0)
            log(f"  result_count='{cnt}'")
            cnt_int = int(cnt or 0)
            if cnt_int > 0:
                log(f"  ✅ {cnt_int}종목!"  )
                for i in range(min(cnt_int, 10)):
                    code = q.GetFieldData("t1857OutBlock1", "shcode", i).strip()
                    name = q.GetFieldData("t1857OutBlock1", "hname", i).strip()
                    log(f"    {code} {name}")
            else:
                log(f"  결과: 0종목")
        else:
            log(f"  ❌ 타임아웃")

    log("")
    log("=" * 50)
    log("진단 완료!")
    log("=" * 50)

    session.DisconnectServer()


if __name__ == "__main__":
    main()
