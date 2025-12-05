@echo off



set SUPABASE_URL=postgresql://postgres.gqhrbvusvcaytcbnusdx:HbBr71pNXJqS57P9@aws-1-eu-west-3.pooler.supabase.com:6543/postgres?sslmode=require






setlocal


REM Ruta a tu Python 3.11
set PYTHON_EXE=C:\Users\nacho\AppData\Local\Programs\Python\Python311\python.exe

REM Ruta al archivo app.py (ajusta si está en otra carpeta)
set APP_FILE=%~dp0app.py

echo Ejecutando Streamlit con: %PYTHON_EXE%
echo App: %APP_FILE%
echo.

"%PYTHON_EXE%" -m streamlit run "%APP_FILE%" --server.port 8501 --server.address localhost


endlocal
pause
