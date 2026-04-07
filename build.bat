@echo off
chcp 65001 >nul
echo ==============================
echo  StockTrader 빌드 시작
echo ==============================

cd /d C:\stock_trader

REM config.json 백업 (사용자가 저장한 API 키 보존)
if exist dist\StockTrader\config.json (
    copy /Y dist\StockTrader\config.json config_backup.json >nul
    echo [백업] 기존 config.json 백업 완료
)

REM 빌드
python -m PyInstaller 주식자동매매.spec --distpath dist -y

REM config.json 복원 (백업이 있으면 복원, 없으면 템플릿 복사)
if exist config_backup.json (
    copy /Y config_backup.json dist\StockTrader\config.json >nul
    del config_backup.json >nul
    echo [복원] 기존 config.json 복원 완료
) else (
    copy /Y config.json dist\StockTrader\ >nul
    echo [복사] 새 config.json 복사 완료
)

echo ==============================
echo  빌드 완료!
echo ==============================
pause
