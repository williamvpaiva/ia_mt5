@echo off
setlocal
echo ========================================
echo   IA_MT5 Bridge - MetaTrader 5 Bridge
echo ========================================
echo.
echo Iniciando MT5 Bridge API...
echo.

pushd "%~dp0"

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

if "%MT5_BRIDGE_HOST%"=="" set MT5_BRIDGE_HOST=0.0.0.0
if "%MT5_BRIDGE_PORT%"=="" set MT5_BRIDGE_PORT=5001

REM Inicia a MT5 Bridge
echo Iniciando servidor UVICORN em %MT5_BRIDGE_HOST%:%MT5_BRIDGE_PORT%...
echo.
python -m uvicorn mt5_bridge:app --host %MT5_BRIDGE_HOST% --port %MT5_BRIDGE_PORT% --reload

popd
pause
