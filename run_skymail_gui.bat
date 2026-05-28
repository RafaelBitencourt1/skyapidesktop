@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul 2>nul
mode con: cols=62 lines=26
title  Skymail API Studio
color 0B

if not exist "%CD%\logs" mkdir "%CD%\logs"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
if not defined TS set "TS=%RANDOM%"
set "GUI_LOG=%CD%\logs\gui_startup_%TS%.log"
set "PYEXE=%CD%\.venv\Scripts\python.exe"

cls
echo.
echo  ==========================================================
echo      S K Y M A I L  -  A P I  S T U D I O
echo      Automacao de endpoints da plataforma Skymail
echo  ==========================================================
echo.
echo  ----------------------------------------------------------
echo    Verificando ambiente de execucao...
echo  ----------------------------------------------------------
echo.

REM Python: venv
if exist "%PYEXE%" (
    echo  [+] Python ......... .venv\Scripts\python.exe
    goto :check_deps
)

REM Python: sistema
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set "PYEXE=python"
    echo  [+] Python ......... sistema
    goto :check_deps
)

echo.
echo  ==========================================================
echo    [!] ERRO: Python nao encontrado.
echo        Instale em: https://python.org/downloads
echo  ==========================================================
echo.
pause
exit /b 1

:check_deps
echo  [*] Verificando dependencias...
"%PYEXE%" -c "import tkinter,requests,ttkbootstrap" >nul 2>nul
if not %ERRORLEVEL%==0 (
    echo  [*] Instalando dependencias...
    "%PYEXE%" -m pip install requests ttkbootstrap --quiet
    if not %ERRORLEVEL%==0 (
        echo.
        echo  ==========================================================
        echo    [ERRO] Falha ao instalar dependencias.
        echo        Consulte: %GUI_LOG%
        echo  ==========================================================
        echo.
        pause
        exit /b 1
    )
)
echo  [+] Dependencias ...... OK
echo.
echo  ----------------------------------------------------------
echo    Abrindo interface grafica...
echo  ----------------------------------------------------------
echo.

echo [%DATE% %TIME%] Iniciando GUI >> "%GUI_LOG%"
"%PYEXE%" "%CD%\skymail_gui.py" 1>>"%GUI_LOG%" 2>&1
if not %ERRORLEVEL%==0 (
    echo.
    echo  ==========================================================
    echo    [ERRO] A interface encerrou com erro.
    echo        Consulte: %GUI_LOG%
    echo  ==========================================================
    echo.
    pause
    exit /b 1
)
endlocal
