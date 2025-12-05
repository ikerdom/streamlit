@echo off
echo ==========================================
echo 🚀 Test de conexión a Supabase PostgreSQL
echo ==========================================

:: 🔑 Definir la cadena de conexión con password real y sslmode=require
set SUPABASE_URL=postgresql://postgres.iwtapkspwdogppxhnhes:EnteOrbe2025@aws-1-eu-west-3.pooler.supabase.com:6543/postgres
:: Ejecutar script de prueba
python test_connection.py

pause

