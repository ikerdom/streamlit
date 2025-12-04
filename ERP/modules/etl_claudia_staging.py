# modules/etl_claudia_staging.py
import requests
import time
import urllib3
from modules.supa_client import get_client

# Cloudia usa HTTPS sin certificado correcto → desactivamos warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================
# 🔗 ENDPOINTS CLOUDIA
# ============================================================
BASE_URL = "http://app.cloud-ia.es:8080/ords/cloudia_integracion_ia/ia/facturas"
LINES_BASE_URL = "https://app.cloud-ia.es/ords/cloudia_integracion_ia/ia/facturas/{}/linea_detalle"
HEADERS = {"Content-Type": "application/json"}


# ============================================================
# 🧰 HELPER: petición con reintentos + backoff
# ============================================================
def fetch_json(url: str, retries: int = 5, sleep: float = 1.0):
    """
    Devuelve el JSON, o None si falla incluso tras reintentos.
    NO interpreta los errores como fin de líneas; el caller decide.
    """
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, verify=False, timeout=30)

            if r.status_code == 200:
                try:
                    return r.json()
                except Exception as e:
                    print(f"   ❌ Error parseando JSON: {e}")
                    return None

            print(f"   ⚠️ HTTP {r.status_code} en {url}")

        except Exception as e:
            print(f"   ⚠️ Error petición {attempt}/{retries}: {e}")

        # backoff
        time.sleep(sleep * attempt)

    # No se pudo obtener respuesta válida
    print(f"   ❌ Fallo definitivo tras {retries} intentos → {url}")
    return None



# ============================================================
# 📄 1) FACTURAS → stg_factura
# ============================================================
def load_facturas_to_staging():
    print("📥 Descargando FACTURAS Cloudia → STAGING...")
    supa = get_client()

    offset = 0
    total_insertadas = 0
    page_size = 25
    seen_ids = set()

    while True:
        url = BASE_URL if offset == 0 else f"{BASE_URL}?offset={offset}"
        print(f"\n➡️ Consulta offset={offset} ...")

        data = fetch_json(url)
        if not data or "items" not in data:
            print("❌ Error: respuesta inválida (fin prematuro).")
            break

        items = data.get("items") or []
        if not items:
            print("🏁 Fin de facturas.")
            break

        batch = []

        for f in items:
            fid = f.get("factura_id") or f.get("ID") or f.get("id")
            if not fid:
                continue

            try:
                fid_int = int(fid)
            except:
                continue

            if fid_int in seen_ids:
                continue
            seen_ids.add(fid_int)

            batch.append({
                "id_origen": fid_int,
                "nombre_cliente": f.get("nombre_cliente"),
                "factura_estado": f.get("factura_estado"),
                "forma_pago": f.get("forma_pago"),
                "fecha_emision": f.get("fecha_emision"),
                "fecha_vencimiento": f.get("fecha_vencimiento"),
                "total_declarado": f.get("total_declarado"),
                "observaciones": f.get("observaciones"),

                # Nuevos campos
                "tipo_documento": f.get("tipo_documento"),
                "factura_serie": f.get("factura_serie"),
                "factura_numero": f.get("factura_numero"),
                "nombre_empresa": f.get("nombre_empresa"),
                "tipo_tercero": f.get("tipo_tercero"),
                "numero_serie": f.get("numero_serie"),
                "base_imponible": f.get("base_imponible"),
                "impuestos": f.get("impuestos"),
                "total_calculado": f.get("total_calculado"),

                # JSON completo original
                "raw_json": f,
            })

        if batch:
            try:
                supa.table("stg_factura").upsert(batch).execute()
                print(f"   ✔ {len(batch)} facturas procesadas")
                total_insertadas += len(batch)
            except Exception as e:
                print(f"   ❌ Error insertando batch facturas: {e}")

        if len(items) < page_size:
            print("🏁 Última página.")
            break

        offset += page_size

    print(f"\n🎉 TOTAL FACTURAS INSERTADAS = {total_insertadas}")
    return total_insertadas



# ============================================================
# 📦 2) LÍNEAS → stg_linea (con reintentos y FIN REAL)
# ============================================================
def load_lineas_to_staging(batch_size_facturas: int = 300):
    print("\n📦 Descargando líneas → STAGING...")
    supa = get_client()

    res_count = supa.table("stg_factura").select("id_origen", count="exact").execute()
    total_facturas = res_count.count or len(res_count.data or [])

    print(f"🔎 Total facturas: {total_facturas}")

    total_lineas_insertadas = 0
    offset_facturas = 0
    indice_global = 0

    while offset_facturas < total_facturas:

        hasta = min(offset_facturas + batch_size_facturas - 1, total_facturas - 1)

        batch_facts = (
            supa.table("stg_factura")
            .select("id_origen")
            .order("id_origen")
            .range(offset_facturas, hasta)
            .execute()
        ).data or []

        for f in batch_facts:
            indice_global += 1
            fid = f.get("id_origen")
            if not fid:
                continue

            print(f"\n➡️ ({indice_global}/{total_facturas}) Factura {fid}")

            line_offset = 0

            while True:
                url = (
                    LINES_BASE_URL.format(fid)
                    if line_offset == 0
                    else f"{LINES_BASE_URL.format(fid)}?offset={line_offset}"
                )
                print(f"   ↪️ offset líneas = {line_offset}")

                data = fetch_json(url)

                # ❌ Caso: error (503/500/timeout/JSON malo)
                if data is None:
                    print(f"   ⚠️ Error leyendo offset {line_offset} en factura {fid}. Reintentando...")
                    time.sleep(1)
                    continue     # <<-- CLAVE: no cortar, reintentar

                items = (data or {}).get("items") or []

                # ✔️ Caso: offset válido pero sin items = fin real
                if not items:
                    print(f"   🔚 Fin REAL líneas factura {fid}")
                    break

                batch = []

                for line in items:
                    lid = line.get("id") or line.get("ID")
                    if not lid:
                        continue
                    try:
                        lid_int = int(lid)
                    except:
                        continue

                    batch.append({
                        "id_origen_linea": lid_int,
                        "id_origen_factura": int(fid),
                        "ean": line.get("ean") or line.get("EAN"),
                        "nombre": line.get("nombre"),
                        "cantidad": line.get("cantidad"),
                        "precio_unit": line.get("precio"),
                        "dto": line.get("dto"),
                        "iva_pct": line.get("tasaimpuesto"),
                        "subtotal": line.get("subtotal"),
                        "total_linea": (
                            line.get("total_linea")
                            or line.get("TOTALLINEA")
                            or line.get("subtotal")
                        ),
                        "idproductoreferencia": line.get("idproductoreferencia"),
                        "extra_jsonb": line,
                    })

                # Insertamos batch de líneas
                try:
                    supa.table("stg_linea").upsert(batch).execute()
                    print(f"   ✔ {len(batch)} líneas insertadas")
                except Exception as e:
                    print(f"   ❌ Error insertando líneas: {e}")

                total_lineas_insertadas += len(batch)

                # Avanzar a siguiente página
                line_offset += 25

        offset_facturas += batch_size_facturas

    print(f"\n🎉 TOTAL LÍNEAS INSERTADAS = {total_lineas_insertadas}")
    return total_lineas_insertadas



# ============================================================
# 🚀 ETL COMPLETO
# ============================================================
def run_staging():
    print("\n🚀 ETL COMPLETO Cloudia → STAGING\n")

    facturas = load_facturas_to_staging()
    lineas = load_lineas_to_staging()

    print("\n🎯 FIN ETL")
    print(f"   • Facturas: {facturas}")
    print(f"   • Líneas:   {lineas}")
