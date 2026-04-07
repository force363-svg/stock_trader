@echo off
cd /d %~dp0
echo [1/3] Building exe...
pyinstaller build.spec --clean --noconfirm
if exist "dist\StockTrader\StockTrader.exe" (
    echo [2/4] Copying config.json...
    copy /Y "config.json" "dist\StockTrader\config.json" >nul
    echo [3/4] Creating signals folder...
    if not exist "dist\StockTrader\signals" mkdir "dist\StockTrader\signals"
    echo [4/4] Copying ai_engine...
    xcopy /Y /E /I "ai_engine" "dist\StockTrader\ai_engine" >nul
    echo BUILD SUCCESS!
    explorer "dist\StockTrader"
) else (
    echo BUILD FAILED.
)
pause
