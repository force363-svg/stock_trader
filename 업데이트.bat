@echo off
chcp 65001 >nul
echo ==============================
echo  StockTrader 업데이트 시작
echo ==============================

cd /d C:\stock_trader

REM ── 최신 코드 받기 ──
echo [1/4] 최신 코드 받는 중...
git pull origin main
echo.

REM ── API 키 백업 ──
echo [2/4] API 키 백업 중...
if exist C:\StockTrader\StockTrader_Real\user_settings.json (
    copy /Y C:\StockTrader\StockTrader_Real\user_settings.json backup_real.json >nul
)
if exist C:\StockTrader\StockTrader_Mock\user_settings.json (
    copy /Y C:\StockTrader\StockTrader_Mock\user_settings.json backup_mock.json >nul
)
echo 완료

REM ── 실전투자 빌드 ──
echo.
echo [3/4] 실전투자 빌드 중...
if exist build rmdir /s /q build
python -m PyInstaller 실전투자.spec --distpath C:\StockTrader -y --clean >nul 2>&1
if errorlevel 1 (
    echo [오류] 실전투자 빌드 실패
    pause
    exit /b 1
)
echo 완료

REM ── 모의투자 빌드 ──
echo.
echo [4/4] 모의투자 빌드 중...
if exist build rmdir /s /q build
python -m PyInstaller 모의투자.spec --distpath C:\StockTrader -y --clean
if errorlevel 1 (
    echo [오류] 모의투자 빌드 실패
    pause
    exit /b 1
)
echo 완료

REM ── API 키 복원 ──
if exist backup_real.json (
    copy /Y backup_real.json C:\StockTrader\StockTrader_Real\user_settings.json >nul
    del backup_real.json >nul
)
if exist backup_mock.json (
    copy /Y backup_mock.json C:\StockTrader\StockTrader_Mock\user_settings.json >nul
    del backup_mock.json >nul
)

echo.
echo ==============================
echo  업데이트 완료!
echo ==============================
pause
