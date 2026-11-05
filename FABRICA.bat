@echo off
title Central da Fabrica
cd /d "%~dp0"
rem Cria um atalho na Area de Trabalho na primeira vez
if not exist "%USERPROFILE%\Desktop\Fabrica de Videos.lnk" (
  powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Fabrica de Videos.lnk');$s.TargetPath='%~dp0FABRICA.bat';$s.WorkingDirectory='%~dp0';$s.IconLocation='%SystemRoot%\System32\imageres.dll,18';$s.Save()" >nul 2>&1
)
echo.
echo   Abrindo a Central da Fabrica no navegador...
echo   Deixe esta janela aberta enquanto usa (pode minimizar).
echo.
.venv\Scripts\python.exe pipeline\central.py
pause
