@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul 2>nul
title Skymail API Studio - Gerar EXE

echo.
echo  ================================================
echo    Skymail API Studio - Gerar executavel Windows
echo  ================================================
echo.

REM Localiza o Python (venv tem prioridade)
set "PYEXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYEXE%" (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set "PYEXE=python"
    ) else (
        echo [ERRO] Python nao encontrado.
        echo        Instale em: https://python.org/downloads
        pause & exit /b 1
    )
)

echo  Python: %PYEXE%
echo.

REM ── Passo 1: instalar PyInstaller ──────────────────────────
echo [1/3] Instalando PyInstaller...
"%PYEXE%" -m pip install pyinstaller --quiet
if not %ERRORLEVEL%==0 (
    echo.
    echo [ERRO] Falha ao instalar PyInstaller.
    pause & exit /b 1
)
echo       OK

REM ── Passo 2: compilar ──────────────────────────────────────
echo.
echo [2/3] Compilando (pode levar 1-3 minutos)...
echo.

"%PYEXE%" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "SkymailAPIStudio" ^
    --collect-data ttkbootstrap ^
    skymail_gui.py

if not %ERRORLEVEL%==0 (
    echo.
    echo [ERRO] Falha no build. Verifique as mensagens acima.
    pause & exit /b 1
)

REM ── Passo 3: resultado ─────────────────────────────────────
echo.
echo  ================================================
echo  [3/3] Executavel gerado com sucesso!
echo.
echo    dist\SkymailAPIStudio.exe
echo.
echo  Copie o arquivo .exe para qualquer pasta e
echo  execute - nao precisa de Python instalado.
echo  ================================================
echo.
pause
endlocal
