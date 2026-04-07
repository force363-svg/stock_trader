@echo off
chcp 65001 >nul
echo ==============================
echo  StockTrader 업데이트 시작
echo ==============================

cd /d C:\stock_trader

REM ── 실행 중인 프로그램 자동 종료 ──
taskkill /F /IM StockTrader_Real.exe /T >nul 2>&1
taskkill /F /IM StockTrader_Mock.exe /T >nul 2>&1

REM ── 최신 코드 받기 ──
echo [1/4] 최신 코드 받는 중...
git pull origin main
echo.

REM ── API 키 백업 ──
echo [2/4] API 키 백업 중...
if exist C:\StockTrader\StockTrader_Real\user_settings.json (
    copy /Y C:\StockTrader\StockTrader_Real\user_settings.json C:\stock_trader\backup_real.json >nul
    echo    실전 API 키 백업 완료
) else (
    echo    실전 user_settings.json 없음 - 건너뜀
)
if exist C:\StockTrader\StockTrader_Mock\user_settings.json (
    copy /Y C:\StockTrader\StockTrader_Mock\user_settings.json C:\stock_trader\backup_mock.json >nul
    echo    모의 API 키 백업 완료
) else (
    echo    모의 user_settings.json 없음 - 건너뜀
)

REM ── 실전투자 빌드 ──
echo.
echo [3/4] 실전투자 빌드 중...
if exist build rmdir /s /q build
python -m PyInstaller real.spec --distpath C:\StockTrader -y --clean >nul 2>&1
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
python -m PyInstaller mock.spec --distpath C:\StockTrader -y --clean >nul 2>&1
if errorlevel 1 (
    echo [오류] 모의투자 빌드 실패
    pause
    exit /b 1
)
echo 완료

REM ── API 키 복원 ──
echo.
echo API 키 복원 중...
if exist C:\stock_trader\backup_real.json (
    copy /Y C:\stock_trader\backup_real.json C:\StockTrader\StockTrader_Real\user_settings.json >nul
    del C:\stock_trader\backup_real.json >nul
    echo    실전 API 키 복원 완료
)
if exist C:\stock_trader\backup_mock.json (
    copy /Y C:\stock_trader\backup_mock.json C:\StockTrader\StockTrader_Mock\user_settings.json >nul
    del C:\stock_trader\backup_mock.json >nul
    echo    모의 API 키 복원 완료
)

echo.
echo ==============================
echo  업데이트 완료!
echo ==============================
pause
