@echo off
chcp 65001 >nul
echo ==============================
echo  StockTrader 빌드 시작
echo ==============================

cd /d C:\stock_trader
git pull origin main
python -m PyInstaller 주식자동매매.spec --distpath dist -y
copy /Y config.json dist\StockTrader\

echo ==============================
echo  빌드 완료!
echo ==============================
pause
