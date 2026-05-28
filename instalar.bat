@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul 2>nul
mode con: cols=64 lines=34
title  Skymail API Studio - Instalador
color 0B

if not exist "%CD%\logs" mkdir "%CD%\logs"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
if not defined TS set "TS=%RANDOM%"
set "INST_LOG=%CD%\logs\instalacao_%TS%.log"
set "VENV_PY=%CD%\.venv\Scripts\python.exe"
set "PY_VER=3.12.10"
set "PY_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-amd64.exe"
set "PY_INSTALLER=%TEMP%\python-%PY_VER%-amd64.exe"

cls
echo.
echo  ================================================================
echo      S K Y M A I L  -  A P I  S T U D I O
echo      Instalador e Lancador
echo  ================================================================
echo.
echo  [%DATE% %TIME%] Iniciando instalador >> "%INST_LOG%"

REM ================================================================
REM  FASE 0 — Ja esta tudo instalado? Pular direto para execucao
REM ================================================================
if exist "%VENV_PY%" (
    echo  [+] Ambiente virtual encontrado. Verificando dependencias...
    "%VENV_PY%" -c "import requests,ttkbootstrap" >nul 2>nul
    if not ERRORLEVEL 1 (
        echo  [+] Dependencias ........... OK
        echo.
        goto :launch
    )
    echo  [-] Dependencias incompletas. Reinstalando...
    goto :install_deps
)

REM ================================================================
REM  FASE 1 — Localizar Python no sistema
REM ================================================================
echo  ----------------------------------------------------------
echo    Verificando Python no sistema...
echo  ----------------------------------------------------------
echo.

set "PYEXE="

REM Verificar no PATH
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    for /f "delims=" %%p in ('where python 2^>nul') do (
        if not defined PYEXE set "PYEXE=%%p"
    )
)

REM Validar versao minima (3.9+)
if defined PYEXE (
    for /f "tokens=2 delims= " %%v in ('"%PYEXE%" --version 2^>^&1') do set "FOUND_VER=%%v"
    for /f "tokens=1,2 delims=." %%a in ("%FOUND_VER%") do (
        if %%a LSS 3 set "PYEXE="
        if %%a==3 if %%b LSS 9 set "PYEXE="
    )
)

REM Verificar instalacoes conhecidas do Python (sem PATH)
if not defined PYEXE (
    for %%v in (313 312 311 310 39) do (
        if not defined PYEXE (
            if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" (
                set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
            )
        )
    )
)

if defined PYEXE (
    echo  [+] Python encontrado: %PYEXE%
    echo  [%DATE% %TIME%] Python: %PYEXE% >> "%INST_LOG%"
    goto :setup_venv
)

REM ================================================================
REM  FASE 2 — Python nao encontrado: baixar e instalar
REM ================================================================
echo  ----------------------------------------------------------
echo    Python nao encontrado.
echo    Baixando Python %PY_VER% (pode levar alguns minutos)...
echo  ----------------------------------------------------------
echo.

echo  [%DATE% %TIME%] Baixando Python %PY_URL% >> "%INST_LOG%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%'"

if not exist "%PY_INSTALLER%" (
    echo.
    echo  ================================================================
    echo    [ERRO] Falha ao baixar o Python.
    echo    Verifique sua conexao com a internet e tente novamente.
    echo    Ou instale manualmente em: https://python.org/downloads
    echo  ================================================================
    echo.
    echo  [%DATE% %TIME%] ERRO: falha no download >> "%INST_LOG%"
    pause
    exit /b 1
)

echo  [+] Download concluido. Instalando Python silenciosamente...
echo  [%DATE% %TIME%] Instalando Python... >> "%INST_LOG%"

"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0 Include_launcher=1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ================================================================
    echo    [ERRO] Falha na instalacao do Python.
    echo    Tente instalar manualmente em: https://python.org/downloads
    echo  ================================================================
    echo.
    echo  [%DATE% %TIME%] ERRO: falha na instalacao >> "%INST_LOG%"
    pause
    exit /b 1
)

del /f /q "%PY_INSTALLER%" >nul 2>nul

REM Localizar Python recem-instalado
for %%v in (312 313 311 310 39) do (
    if not defined PYEXE (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" (
            set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
        )
    )
)

REM Tentar pelo PATH atualizado
if not defined PYEXE (
    for /f "delims=" %%p in ('powershell -NoProfile -Command "(Get-Command python -ErrorAction SilentlyContinue).Source" 2^>nul') do (
        if not defined PYEXE set "PYEXE=%%p"
    )
)

if not defined PYEXE (
    echo.
    echo  ================================================================
    echo    [ERRO] Python instalado mas nao localizado.
    echo    Reinicie o computador e execute este arquivo novamente.
    echo  ================================================================
    echo.
    pause
    exit /b 1
)

echo  [+] Python %PY_VER% instalado com sucesso.
echo  [%DATE% %TIME%] Python instalado em: %PYEXE% >> "%INST_LOG%"

REM ================================================================
REM  FASE 3 — Criar ambiente virtual
REM ================================================================
:setup_venv
echo.
echo  ----------------------------------------------------------
echo    Criando ambiente virtual...
echo  ----------------------------------------------------------
echo.

if exist "%CD%\.venv" (
    echo  [*] Removendo venv antigo...
    rmdir /s /q "%CD%\.venv" >nul 2>nul
)

"%PYEXE%" -m venv "%CD%\.venv"
if not exist "%VENV_PY%" (
    echo.
    echo  ================================================================
    echo    [ERRO] Falha ao criar o ambiente virtual.
    echo  ================================================================
    echo.
    echo  [%DATE% %TIME%] ERRO: falha ao criar venv >> "%INST_LOG%"
    pause
    exit /b 1
)

echo  [+] Ambiente virtual criado.
echo  [%DATE% %TIME%] venv criado >> "%INST_LOG%"

REM ================================================================
REM  FASE 4 — Instalar dependencias
REM ================================================================
:install_deps
echo.
echo  ----------------------------------------------------------
echo    Instalando dependencias (requests, ttkbootstrap)...
echo  ----------------------------------------------------------
echo.

"%VENV_PY%" -m pip install --upgrade pip --quiet
"%VENV_PY%" -m pip install -r "%CD%\requirements.txt" --quiet
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ================================================================
    echo    [ERRO] Falha ao instalar dependencias.
    echo        Consulte o log: %INST_LOG%
    echo  ================================================================
    echo.
    echo  [%DATE% %TIME%] ERRO: falha no pip install >> "%INST_LOG%"
    pause
    exit /b 1
)

echo  [+] Dependencias instaladas com sucesso.
echo  [%DATE% %TIME%] Dependencias OK >> "%INST_LOG%"

REM ================================================================
REM  FASE 5 — Abrir interface
REM ================================================================
:launch
echo.
echo  ================================================================
echo    Abrindo Skymail API Studio...
echo  ================================================================
echo.

echo  [%DATE% %TIME%] Iniciando GUI >> "%INST_LOG%"
"%VENV_PY%" "%CD%\skymail_gui.py" 1>>"%INST_LOG%" 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ================================================================
    echo    [ERRO] A interface encerrou com erro.
    echo        Consulte o log: %INST_LOG%
    echo  ================================================================
    echo.
    pause
    exit /b 1
)

endlocal
