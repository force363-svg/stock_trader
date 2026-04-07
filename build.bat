@echo off
chcp 65001 >nul
echo ==============================
echo  StockTrader 빌드 시작
echo ==============================

cd /d C:\stock_trader

REM 올바른 Python 찾기
where python >nul 2>&1
if errorlevel 1 (
    echo [오류] Python을 찾을 수 없습니다
    pause
    exit /b 1
)

REM 같은 Python으로 패키지 설치 + 빌드 (경로 불일치 방지)
echo [설치] 필수 패키지 설치 중...
python -m pip install PyQt5 requests pyinstaller 2>&1
echo.

REM config.json 백업
if exist C:\StockTrader\config.json (
    copy /Y C:\StockTrader\config.json config_backup.json >nul
    echo [백업] config.json 백업 완료
)

REM 빌드
echo [빌드] 빌드 중...
python -m PyInstaller 주식자동매매.spec --distpath C:\ -y 2>&1

REM config.json 복원
if exist config_backup.json (
    copy /Y config_backup.json C:\StockTrader\config.json >nul
    del config_backup.json >nul
    echo [복원] config.json 복원 완료
) else (
    copy /Y config.json C:\StockTrader\ >nul
    echo [복사] config.json 복사 완료
)

echo ==============================
echo  빌드 완료!
echo  실행: C:\StockTrader\StockTrader.exe
echo ==============================
pause
