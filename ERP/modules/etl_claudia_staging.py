import requests
import urllib3
from modules.supa_client import get_client

# =====================================
# ⚙️ CONFIG Cloudia API
# =====================================
URL_FACTURAS = "http://app.cloud-ia.es:8080/ords/cloudia_integracion_ia/ia/facturas"
URL_LINEAS   = "https://app.cloud-ia.es/ords/cloudia_integracion_ia/ia/facturas/{idfactura}/linea_detalle"
PAGE_SIZE    = 100  # Cloudia devuelve 25 por defecto
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 👉 Control global: número de páginas / facturas a procesar
LIMIT = 100   # Cambia este número o pon None para todas


# =====================================
# 🧩 AUXILIARES
# =====================================
def _fetch(url: str):
    """Descarga JSON permitiendo conexiones inseguras (por certificado mal emitido en Cloudia)."""
    print(f"📡 Descargando (SSL verificado=OFF): {url}")
    r = requests.get(url, timeout=30, verify=False)
    r.raise_for_status()
    return r.json()


def _normalize_factura(f):
    return {
        "id_origen":        f.get("factura_id"),
        "nombre_cliente":   f.get("nombre_cliente"),
        "factura_estado":   f.get("factura_estado"),
        "forma_pago":       f.get("forma_pago"),
        "fecha_emision":    f.get("fecha_emision"),
        "fecha_vencimiento":f.get("fecha_vencimiento"),
        "total_declarado":  f.get("total_declarado"),
        "observaciones":    f.get("observaciones"),
        "raw_json":         f,
    }


def _normalize_linea(l):
    subtotal = l.get("subtotal") or 0
    iva_pct  = l.get("tasaimpuesto") or 0
    total_linea = subtotal * (1 + (float(iva_pct) / 100.0))
    return {
        "id_origen_linea":   l.get("id"),
        "id_origen_factura": l.get("idfactura"),
        "ean":               l.get("ean"),
        "nombre":            l.get("nombre"),
        "cantidad":          l.get("cantidad"),
        "precio_unit":       l.get("precio"),
        "dto":               l.get("dto"),
        "iva_pct":           iva_pct,
        "subtotal":          subtotal,
        "total_linea":       total_linea,
        "extra_jsonb":       l,
    }

def load_facturas_to_staging():
    supa = get_client()
    url = URL_FACTURAS
    total_inserted = 0
    all_rows = []

    while url:
        data = _fetch(url)
        items = data.get("items", [])
        if not items:
            break

        for f in items:
            all_rows.append(_normalize_factura(f))
            if LIMIT and len(all_rows) >= LIMIT:
                url = None  # detener el bucle externo
                break

        # avanzar solo si aún queremos más
        if url:
            next_links = [l for l in data.get("links", []) if l.get("rel") == "next"]
            url = next_links[0]["href"] if next_links else None

        if LIMIT and len(all_rows) >= LIMIT:
            print(f"⏹️ Límite de {LIMIT} facturas alcanzado")
            break

    if all_rows:
        supa.table("stg_factura").upsert(all_rows, on_conflict="id_origen").execute()
        total_inserted = len(all_rows)

    print(f"🏁 Hecho. Total facturas insertadas: {total_inserted}")


# =====================================
# 2️⃣ Descargar LÍNEAS → stg_linea
# =====================================
def load_lineas_for_facturas():
    supa = get_client()
    res = supa.table("stg_factura").select("id_origen").execute()
    facturas = res.data or []

    if LIMIT:
        facturas = facturas[:LIMIT]
        print(f"📋 Procesando solo las primeras {LIMIT} facturas")

    total_inserted = 0

    for f in facturas:
        fid = f["id_origen"]
        try:
            data = _fetch(URL_LINEAS.format(idfactura=fid))
            items = data.get("items", [])
            if not items:
                print(f"⚠️ Factura {fid}: sin líneas.")
                continue

            rows = [_normalize_linea(l) for l in items]
            supa.table("stg_linea").upsert(rows, on_conflict="id_origen_linea").execute()
            total_inserted += len(rows)
            print(f"🧾 Factura {fid}: {len(rows)} líneas insertadas ✅")
        except Exception as e:
            print(f"❌ Error al procesar factura {fid}: {e}")

    print(f"🏁 Hecho. Total líneas insertadas: {total_inserted}")
