# modules/etl_claudia_staging.py
import requests
import time
from modules.supa_client import get_client

# ============================================
# 🔗 ENDPOINTS CLOUDIA
# ============================================
# Facturas (paginadas de 25 en 25 con ?offset=)
BASE_URL = "http://app.cloud-ia.es:8080/ords/cloudia_integracion_ia/ia/facturas"

# Líneas de factura (también paginadas de 25 en 25 con ?offset=)
LINES_BASE_URL = "https://app.cloud-ia.es/ords/cloudia_integracion_ia/ia/facturas/{}/linea_detalle"

HEADERS = {"Content-Type": "application/json"}


# ============================================
# 🧰 HELPER: petición con reintentos
# ============================================
def fetch_json(url: str, retries: int = 3, sleep: float = 1.0):
    """Descarga JSON con reintentos (verify=False por el certificado de Cloudia)."""
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, verify=False, timeout=20)
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception as e:
                    print(f"   ❌ Error parseando JSON ({url}): {e}")
                    return None
            else:
                print(f"   ⚠️ HTTP {r.status_code} en {url}")
        except Exception as e:
            print(f"   ⚠️ Error petición ({attempt}/{retries}) {url}: {e}")
        time.sleep(sleep)

    print(f"   ❌ Sin respuesta válida tras {retries} intentos: {url}")
    return None


# ============================================
# 📄 1) FACTURAS → stg_factura
# ============================================
def load_facturas_to_staging():
    print("📥 Iniciando descarga completa de FACTURAS Cloudia → STAGING...")
    supa = get_client()

    offset = 0
    page_size = 25  # Cloudia devuelve bloques de 25
    total_insertadas = 0
    seen_ids = set()

    while True:
        # Primera página sin offset, resto con ?offset=NNN
        url = BASE_URL if offset == 0 else f"{BASE_URL}?offset={offset}"
        print(f"➡️ Consultando página offset={offset} ... {url}")

        data = fetch_json(url)
        if not data or "items" not in data:
            print("❌ Error: Cloudia devolvió respuesta vacía o inválida.")
            break

        items = data.get("items") or []
        if not items:
            print("🏁 No hay más facturas. Fin del proceso.")
            break

        batch_insert = []
        for f in items:
            # Cloudia usa factura_id en minúscula
            fid = f.get("factura_id") or f.get("ID") or f.get("id")
            if fid is None:
                continue

            try:
                fid_int = int(fid)
            except Exception:
                continue

            # Evitar duplicados si Cloudia repite algo
            if fid_int in seen_ids:
                continue
            seen_ids.add(fid_int)

            batch_insert.append(
                {
                    "id_origen": fid_int,
                    "nombre_cliente": f.get("nombre_cliente"),
                    "factura_estado": f.get("factura_estado"),
                    "forma_pago": f.get("forma_pago"),
                    "fecha_emision": f.get("fecha_emision"),
                    "fecha_vencimiento": f.get("fecha_vencimiento"),
                    "total_declarado": f.get("total_declarado"),
                    "observaciones": f.get("observaciones"),
                    "raw_json": f,
                }
            )

        if batch_insert:
            try:
                supa.table("stg_factura").upsert(batch_insert).execute()
                print(f"   ✔ Insertadas/Actualizadas {len(batch_insert)} facturas")
                total_insertadas += len(batch_insert)
            except Exception as e:
                print(f"   ❌ Error insertando facturas en Supabase: {e}")

        # Si viene menos de 25, es la última página
        if len(items) < page_size:
            print("🏁 Última página de facturas (menos de 25 elementos).")
            break

        offset += page_size

    print(f"🎉 TOTAL FACTURAS INSERTADAS: {total_insertadas}")
    return total_insertadas

def load_lineas_to_staging(batch_size_facturas: int = 500):
    """
    Descarga TODAS las líneas de TODAS las facturas que haya en stg_factura,
    en batches de facturas para no saturar ni Cloudia ni Supabase.
    """

    print("\n📦 Descargando líneas de factura Cloudia → STAGING...")
    supa = get_client()

    # 1) Contar cuántas facturas tenemos en staging
    res_count = supa.table("stg_factura").select("id_origen", count="exact").execute()
    total_facturas = res_count.count or len(res_count.data or [])
    if total_facturas == 0:
        print("⚠️ No hay facturas en stg_factura. Nada que hacer.")
        return 0

    print(f"🔎 Total facturas en staging: {total_facturas}")

    total_lineas_insertadas = 0
    offset_facturas = 0
    indice_global = 0  # para el log (1/5620, 2/5620, ...)

    while offset_facturas < total_facturas:
        # 2) Cargar un batch de facturas (paginado por rango)
        hasta = min(offset_facturas + batch_size_facturas - 1, total_facturas - 1)
        res_batch = (
            supa.table("stg_factura")
            .select("id_origen")
            .order("id_origen")
            .range(offset_facturas, hasta)
            .execute()
        )
        facturas_batch = res_batch.data or []
        if not facturas_batch:
            break

        for f in facturas_batch:
            indice_global += 1
            fid = f.get("id_origen")
            if not fid:
                continue

            print(f"\n➡️ ({indice_global}/{total_facturas}) Descargando líneas de factura {fid}")

            # 3) Paginación de líneas de esa factura
            line_offset = 0
            while True:
                if line_offset == 0:
                    url = LINES_BASE_URL.format(fid)
                else:
                    url = f"{LINES_BASE_URL.format(fid)}?offset={line_offset}"

                print(f"   ↪️ Página líneas offset={line_offset} ... {url}")
                data = fetch_json(url)
                items = (data or {}).get("items") or []

                if not items:
                    if line_offset == 0:
                        print(f"   ⚠️ Ninguna línea válida en offset 0 para factura {fid}")
                    print(f"   🔚 No hay más páginas de líneas para factura {fid}")
                    break

                batch_lineas = []
                for line in items:
                    lid = line.get("id") or line.get("ID")
                    if not lid:
                        continue

                    batch_lineas.append({
                        "id_origen_linea": int(lid),
                        "id_origen_factura": int(fid),
                        "ean": line.get("ean") or line.get("EAN"),
                        "nombre": line.get("nombre") or line.get("NOMBRE"),
                        "cantidad": line.get("cantidad") or line.get("CANTIDAD"),
                        "precio_unit": line.get("precio") or line.get("PRECIO") or line.get("PRECIO_UNIT"),
                        "dto": line.get("dto") or line.get("DTO"),
                        "iva_pct": line.get("tasaimpuesto") or line.get("TASAIMPUESTO") or line.get("IVA_PCT"),
                        "subtotal": line.get("subtotal") or line.get("SUBTOTAL"),
                        "total_linea": (
                            line.get("TOTALLINEA")
                            or line.get("total_linea")
                            or line.get("subtotal")
                            or line.get("SUBTOTAL")
                        ),
                        "extra_jsonb": line,
                    })

                if batch_lineas:
                    supa.table("stg_linea").upsert(batch_lineas).execute()
                    print(f"   ✔ {len(batch_lineas)} líneas insertadas (factura {fid}, offset={line_offset})")
                    total_lineas_insertadas += len(batch_lineas)

                # 4) Siguiente página de líneas de esa factura
                line_offset += 25  # Cloudia pagina de 25 en 25

        # 5) Siguiente batch de facturas
        offset_facturas += batch_size_facturas

    print(f"\n🎉 TOTAL LÍNEAS INSERTADAS: {total_lineas_insertadas}")
    return total_lineas_insertadas


# ============================================
# 🚀 3) RUN GLOBAL
# ============================================
def run_staging():
    print("\n🚀 Iniciando ETL COMPLETO Cloudia → Staging\n")
    facturas = load_facturas_to_staging()
    lineas = load_lineas_to_staging()
    print("\n🎯 ETL COMPLETO")
    print(f"   • Facturas insertadas: {facturas}")
    print(f"   • Líneas insertadas:   {lineas}")
