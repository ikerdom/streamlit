# ============================================
# run_etl_transform.py
# ============================================
from modules.etl_claudia_transform import (
    transform_facturas_to_pedidos,
    transform_lineas_to_pedido_detalle,
    update_pedido_totales,
    reset_erp_data,          # ⬅️ limpieza opcional
)
from modules.supa_client import get_client

# Cambia a False si no quieres que se limpie antes de cada ejecución
#CLEAN_RESET = True

if __name__ == "__main__":
    print("🚀 Iniciando ETL Cloudia → ERP (Transform & Load)...")

#   if CLEAN_RESET:
#        reset_erp_data()

    # IMPORTANTE: antes de esto, ejecuta tu run_etl_staging.py
    # para poblar stg_factura y stg_linea.
    transform_facturas_to_pedidos()
    transform_lineas_to_pedido_detalle()
    update_pedido_totales()

    print("✅ ETL completado correctamente.")
