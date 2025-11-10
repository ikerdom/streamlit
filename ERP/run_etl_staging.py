# run_etl_staging.py
from modules.etl_claudia_staging import load_facturas_to_staging, load_lineas_for_facturas

if __name__ == "__main__":
    print("🚀 Iniciando ETL Cloudia → Supabase (STAGING COMPLETO)...")

    # 1️⃣ Descargar todas las facturas
    load_facturas_to_staging()

    # 2️⃣ Descargar TODAS las líneas de las facturas
    load_lineas_for_facturas()

    print("✅ ETL terminado correctamente. Verifica stg_factura y stg_linea.")
