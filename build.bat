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

REM user_settings.json 백업 (API 키 보호)
if exist C:\StockTrader_Real\user_settings.json (
    copy /Y C:\StockTrader_Real\user_settings.json user_settings_backup.json >nul
    echo [백업] 실전 user_settings.json 백업 완료
)

REM ==============================
REM  1. 실전투자 빌드
REM ==============================
echo.
echo [빌드] 실전투자 (StockTrader_Real) 빌드 중...
if exist build rmdir /s /q build
python -m PyInstaller 실전투자.spec --distpath C:\ -y --clean 2>&1
if errorlevel 1 (
    echo [오류] 실전투자 빌드 실패!
    pause
    exit /b 1
)
echo [완료] 실전투자 빌드 완료 → C:\StockTrader_Real\StockTrader_Real.exe

REM ==============================
REM  2. 모의투자 빌드
REM ==============================
echo.
echo [빌드] 모의투자 (StockTrader_Mock) 빌드 중...
if exist build rmdir /s /q build
python -m PyInstaller 모의투자.spec --distpath C:\ -y --clean 2>&1
if errorlevel 1 (
    echo [오류] 모의투자 빌드 실패!
    pause
    exit /b 1
)
echo [완료] 모의투자 빌드 완료 → C:\StockTrader_Mock\StockTrader_Mock.exe

REM user_settings.json 복원
if exist user_settings_backup.json (
    copy /Y user_settings_backup.json C:\StockTrader_Real\user_settings.json >nul
    copy /Y user_settings_backup.json C:\StockTrader_Mock\user_settings.json >nul
    del user_settings_backup.json >nul
    echo [복원] user_settings.json 양쪽 복원 완료
)

echo.
echo ==============================
echo  빌드 완료!
echo  실전투자: C:\StockTrader_Real\StockTrader_Real.exe
echo  모의투자: C:\StockTrader_Mock\StockTrader_Mock.exe
echo ==============================
pause
