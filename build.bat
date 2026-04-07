@echo off
chcp 65001 >nul
echo ==============================
echo  StockTrader 빌드 시작
echo ==============================

cd /d C:\stock_trader

REM Python 확인
where python >nul 2>&1
if errorlevel 1 (
    echo [오류] Python을 찾을 수 없습니다
    pause
    exit /b 1
)

REM 필수 패키지 설치
echo [설치] 필수 패키지 설치 중...
python -m pip install PyQt5 requests pyinstaller 2>&1
echo.

REM ── API 키 백업 (실전/모의 각각 따로) ──
if exist C:\StockTrader\StockTrader_Real\user_settings.json (
    copy /Y C:\StockTrader\StockTrader_Real\user_settings.json backup_real.json >nul
    echo [백업] 실전 API 키 백업 완료
)
if exist C:\StockTrader\StockTrader_Mock\user_settings.json (
    copy /Y C:\StockTrader\StockTrader_Mock\user_settings.json backup_mock.json >nul
    echo [백업] 모의 API 키 백업 완료
)

REM ==============================
REM  1. 실전투자 빌드
REM ==============================
echo.
echo [빌드] 실전투자 (StockTrader_Real) 빌드 중...
if exist build rmdir /s /q build
python -m PyInstaller real.spec --distpath C:\StockTrader -y --clean 2>&1
if errorlevel 1 (
    echo [오류] 실전투자 빌드 실패!
    pause
    exit /b 1
)
echo [완료] 실전투자 빌드 완료

REM ==============================
REM  2. 모의투자 빌드
REM ==============================
echo.
echo [빌드] 모의투자 (StockTrader_Mock) 빌드 중...
if exist build rmdir /s /q build
python -m PyInstaller mock.spec --distpath C:\StockTrader -y --clean 2>&1
if errorlevel 1 (
    echo [오류] 모의투자 빌드 실패!
    pause
    exit /b 1
)
echo [완료] 모의투자 빌드 완료

REM ── API 키 복원 (각각 원래 위치로) ──
if exist backup_real.json (
    copy /Y backup_real.json C:\StockTrader\StockTrader_Real\user_settings.json >nul
    del backup_real.json >nul
    echo [복원] 실전 API 키 복원 완료
)
if exist backup_mock.json (
    copy /Y backup_mock.json C:\StockTrader\StockTrader_Mock\user_settings.json >nul
    del backup_mock.json >nul
    echo [복원] 모의 API 키 복원 완료
)

echo.
echo ==============================
echo  빌드 완료!
echo  실전투자: C:\StockTrader\StockTrader_Real\StockTrader_Real.exe
echo  모의투자: C:\StockTrader\StockTrader_Mock\StockTrader_Mock.exe
echo ==============================
pause
