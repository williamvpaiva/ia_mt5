@echo off
echo ========================================
echo   IA_MT5 Bridge - MetaTrader 5 Bridge
echo ========================================
echo.
echo Iniciando MT5 Bridge API...
echo.

REM Verifica se o Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python nao instalado ou nao no PATH
    pause
    exit /b 1
)

REM Verifica se o MetaTrader5 está instalado
python -c "import MetaTrader5" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: MetaTrader5 package nao instalado
    echo Execute: pip install MetaTrader5
    pause
    exit /b 1
)

REM Inicia a MT5 Bridge
echo Iniciando servidor UVICORN na porta 5000...
echo.
python -m uvicorn mt5_bridge:app --host 0.0.0.0 --port 5000 --reload

pause
