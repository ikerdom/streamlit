@echo off
REM Inicializa el entorno dentro de ENV: crea .venv, instala requisitos y copia .env si falta.
setlocal
cd /d "%~dp0"

echo === Comprobando Python en PATH ===
python --version >NUL 2>&1
if errorlevel 1 (
    echo Python no esta instalado o no esta en PATH.
    echo Descarga: https://www.python.org/downloads/ y marca "Add Python to PATH".
    pause
    exit /b 1
)

echo === Creando entorno virtual si no existe (./.venv) ===
if not exist ".venv\Scripts\activate.bat" (
    python -m venv .venv
)

echo === Activando entorno virtual ===
call .venv\Scripts\activate.bat

echo === Instalando dependencias ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo === Copiando .env si falta ===
if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >NUL
        echo Se copio .env.example a .env. Edita .env y rellena los valores proporcionados por IT.
    ) else (
        echo No hay .env ni .env.example. Crea .env manualmente.
    )
)

echo === Entorno listo. Usa run_all.bat para arrancar backend+frontend. ===
pause
endlocal
