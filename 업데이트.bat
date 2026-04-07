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
echo [1/3] 최신 코드 받는 중...
git pull origin main
echo.

REM ── engine_config.json 복사 (없을 때만 → 기존 설정 보존) ──
if not exist "C:\StockTrader\engine_config.json" (
    copy "C:\stock_trader\engine_config.json" "C:\StockTrader\engine_config.json" >nul
    echo engine_config.json 복사 완료
)

REM ── 실전투자 빌드 ──
echo [2/3] 실전투자 빌드 중...
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
echo [3/3] 모의투자 빌드 중...
if exist build rmdir /s /q build
python -m PyInstaller mock.spec --distpath C:\StockTrader -y --clean >nul 2>&1
if errorlevel 1 (
    echo [오류] 모의투자 빌드 실패
    pause
    exit /b 1
)
echo 완료

echo.
echo ==============================
echo  업데이트 완료!
echo  설정/API키: C:\StockTrader\user_settings.json (빌드해도 유지됨)
echo ==============================
pause
