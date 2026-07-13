@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==========================================
echo       APAC VISITAS V2 - INICIALIZACAO
echo ==========================================
echo.

rem O sistema usa Python 3.12 no Windows para garantir compatibilidade
where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 --version >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=py -3.12"
    ) else (
        goto :python_nao_encontrado
    )
) else (
    python --version 2>nul | findstr /R /C:"Python 3\.12\." >nul
    if errorlevel 1 goto :python_nao_encontrado
    set "PYTHON_CMD=python"
)

rem Se existir um ambiente criado por outra versao do Python, recria automaticamente
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>nul
    if errorlevel 1 (
        echo Ambiente virtual antigo ou incompatível encontrado.
        echo Removendo somente a pasta .venv para recriar com Python 3.12...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual com Python 3.12...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :erro
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :erro

echo Verificando versao do Python do ambiente...
python -c "import sys; print('Python em uso:', sys.version); raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)"
if errorlevel 1 goto :erro

echo Atualizando ferramentas de instalacao...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :erro

echo Instalando dependencias para Windows...
python -m pip install --only-binary=:all: -r requirements-windows.txt
if errorlevel 1 goto :erro

echo.
echo Iniciando o sistema em http://127.0.0.1:5000
python run.py
if errorlevel 1 goto :erro

goto :fim

:python_nao_encontrado
echo.
echo ERRO: O Python 3.12 nao foi encontrado.
echo Instale o Python 3.12 de 64 bits e marque Add Python to PATH.
echo Depois execute novamente este arquivo.
pause
exit /b 1

:erro
echo.
echo Ocorreu um erro durante a instalacao ou inicializacao.
echo Confira as mensagens acima.
pause
exit /b 1

:fim
pause
endlocal
