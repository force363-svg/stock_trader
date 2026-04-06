@echo off
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\주식자동매매.lnk'); $Shortcut.TargetPath = 'C:\stock_trader\실행.bat'; $Shortcut.WorkingDirectory = 'C:\stock_trader'; $Shortcut.IconLocation = 'C:\Windows\System32\shell32.dll,48'; $Shortcut.Save()"
echo 바탕화면에 바로가기가 생성됐습니다!
pause
