"""
HTS 연동 테스트 스크립트
- PostMessage 방식 (포커스 불필요)
- LS증권 투혼 HTS가 실행된 상태에서 실행
"""
import ctypes
import time

user32 = ctypes.windll.user32

# ── 테스트 1: HTS 창 찾기 ──
print("=" * 50)
print("테스트 1: HTS 창 찾기")
print("=" * 50)

hts_hwnd = None
def enum_cb(hwnd, _):
    global hts_hwnd
    if hts_hwnd:
        return True
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            if "투혼" in title:
                hts_hwnd = hwnd
                print(f"  ✅ 찾음: '{title}' (핸들: {hwnd})")
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

if not hts_hwnd:
    print("  ❌ HTS 창을 찾을 수 없음!")
    print("  → LS증권 투혼이 실행 중인지 확인하세요")
    exit()

# ── 테스트 2: PostMessage로 종목코드 전송 ──
print()
print("=" * 50)
print("테스트 2: PostMessage로 삼성전자(005930) 전송")
print("=" * 50)

test_code = "005930"
WM_CHAR = 0x0102
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D

print(f"  3초 후 전송합니다...")
print(f"  → HTS에서 종목코드 입력창을 클릭해두세요!")
time.sleep(3)

try:
    for ch in test_code:
        result = user32.PostMessageW(hts_hwnd, WM_CHAR, ord(ch), 0)
        print(f"  → '{ch}' 전송 (result={result})")
        time.sleep(0.05)

    time.sleep(0.1)
    user32.PostMessageW(hts_hwnd, WM_KEYDOWN, VK_RETURN, 0)
    time.sleep(0.01)
    user32.PostMessageW(hts_hwnd, WM_KEYUP, VK_RETURN, 0)
    print(f"  → Enter 전송 OK")
    print(f"  ✅ 전송 완료! HTS에서 삼성전자가 나오는지 확인하세요")
except Exception as e:
    print(f"  ❌ 오류: {e}")

# ── 테스트 3: SK하이닉스 전송 ──
print()
print("=" * 50)
print("테스트 3: SK하이닉스(000660) 전송 (5초 후)")
print("=" * 50)
print("  → HTS 종목코드 입력창을 다시 클릭해두세요!")
time.sleep(5)

try:
    for ch in "000660":
        user32.PostMessageW(hts_hwnd, WM_CHAR, ord(ch), 0)
        time.sleep(0.05)
    time.sleep(0.1)
    user32.PostMessageW(hts_hwnd, WM_KEYDOWN, VK_RETURN, 0)
    time.sleep(0.01)
    user32.PostMessageW(hts_hwnd, WM_KEYUP, VK_RETURN, 0)
    print(f"  ✅ 전송 완료! HTS에서 SK하이닉스가 나오는지 확인하세요")
except Exception as e:
    print(f"  ❌ 오류: {e}")

print()
print("=" * 50)
print("HTS에서 종목이 바뀌었나요?")
print("  → 바뀌었으면 성공!")
print("  → 안 바뀌었으면 알려주세요")
print("=" * 50)
