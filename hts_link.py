"""
HTS 종목 연동 모듈 (LS증권 투혼)
방식: AttachThreadInput + SetFocus + SendInput 키보드
- 창 전환 없음 (깜빡임 없음)
- 마우스 이동 없음
"""

import ctypes
import ctypes.wintypes
import re
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Windows Messages (컨트롤 탐색용)
WM_GETTEXT        = 0x000D
WM_GETTEXTLENGTH  = 0x000E

# SendInput 상수
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP   = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_RETURN  = 0x0D
VK_CONTROL = 0x11
VK_A       = 0x41

AFX_STOCK_CLASS = "Afx:00D60000:b:00010005:00000000:00000000"
STOCK_CODE_RE = re.compile(r'^\d{6}$')

# SendInput 구조체
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long), ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("value", _INPUT_UNION)]

EXTRA = ctypes.cast(ctypes.pointer(ctypes.c_ulong(0)), ctypes.POINTER(ctypes.c_ulong))


class HTSLinker:

    def __init__(self, log_callback=None):
        self.log_callback = log_callback or print

    # ── 투혼 메인 창 찾기 ──
    def find_main_window(self):
        found = [None]
        def cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    if "투혼" in buf.value:
                        found[0] = hwnd
                        return False
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(WNDENUMPROC(cb), 0)
        return found[0]

    # ── 종목코드 Edit hwnd 찾기 ──
    def _find_edit_hwnd(self, main_hwnd):
        results = []
        def cb(hwnd, _):
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            if cls_buf.value == AFX_STOCK_CLASS:
                tlen = user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
                if tlen > 0:
                    tbuf = ctypes.create_unicode_buffer(tlen + 1)
                    user32.SendMessageW(hwnd, WM_GETTEXT, tlen + 1, tbuf)
                    if STOCK_CODE_RE.match(tbuf.value):
                        results.append(hwnd)
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumChildWindows(main_hwnd, WNDENUMPROC(cb), 0)
        return results[0] if results else None

    # ── 물리 키 입력 ──
    def _key(self, vk, up=False):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.value.ki.wVk = vk
        inp.value.ki.dwFlags = KEYEVENTF_KEYUP if up else 0
        inp.value.ki.dwExtraInfo = EXTRA
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

    # ── 유니코드 문자 입력 ──
    def _char(self, ch):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.value.ki.wVk = 0
        inp.value.ki.wScan = ord(ch)
        inp.value.ki.dwFlags = KEYEVENTF_UNICODE
        inp.value.ki.dwExtraInfo = EXTRA
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        inp.value.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        time.sleep(0.01)

    # ── 메인 전송 ──
    def send(self, stock_code, stock_name=""):
        code = stock_code.replace("A", "").replace("a", "").strip()
        if not code:
            return False, f"종목코드 없음 ({stock_name})"
        if not STOCK_CODE_RE.match(code):
            return False, f"잘못된 종목코드: {code}"

        hwnd = self.find_main_window()
        if not hwnd:
            return False, "HTS(투혼) 미실행"

        edit_hwnd = self._find_edit_hwnd(hwnd)
        if not edit_hwnd:
            return False, "종목코드 컨트롤 없음"

        # HTS 스레드에 연결
        hts_tid = user32.GetWindowThreadProcessId(hwnd, None)
        cur_tid = kernel32.GetCurrentThreadId()
        attached = False

        try:
            if cur_tid != hts_tid:
                attached = bool(user32.AttachThreadInput(cur_tid, hts_tid, True))

            # Edit 컨트롤에 포커스 (창 전환 없음)
            prev_focus = user32.SetFocus(edit_hwnd)
            time.sleep(0.05)

            # Ctrl+A (전체선택)
            self._key(VK_CONTROL)
            self._key(VK_A)
            time.sleep(0.01)
            self._key(VK_A, up=True)
            self._key(VK_CONTROL, up=True)
            time.sleep(0.03)

            # 종목코드 타이핑
            for ch in code:
                self._char(ch)
            time.sleep(0.05)

            # Enter
            self._key(VK_RETURN)
            time.sleep(0.01)
            self._key(VK_RETURN, up=True)

            # 포커스 복원
            if prev_focus:
                user32.SetFocus(prev_focus)

            return True, f"HTS 연동: {stock_name}({code})"

        except Exception as e:
            return False, f"HTS 전송 실패: {e}"

        finally:
            if attached:
                user32.AttachThreadInput(cur_tid, hts_tid, False)


if __name__ == "__main__":
    import sys
    code = sys.argv[1] if len(sys.argv) > 1 else "005930"
    linker = HTSLinker()
    ok, msg = linker.send(code, "test")
    print(f"{'OK' if ok else 'FAIL'} {msg}")
    input("Enter to exit...")
