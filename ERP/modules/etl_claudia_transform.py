# ============================================
# modules/etl_claudia_facturas.py
# Transformación REAL:
#   stg_factura  → factura
#   stg_linea    → factura_linea
#   factura      → pedido  (cliente real)
# ============================================

import unicodedata
from datetime import date
from modules.supa_client import get_client


# --------------------------------------------
# NORMALIZADOR para comparar nombres de cliente
# --------------------------------------------
def normalize(text):
    if not text:
        return ""
    text = text.strip().lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return text.replace(",", "").replace(".", "").replace("  ", " ")


# --------------------------------------------
# MATCH cliente por "razon_social" casi exacta
# --------------------------------------------
def find_clienteid(supa, nombre_cliente):
    if not nombre_cliente:
        return 1  # cliente genérico

    nombre_norm = normalize(nombre_cliente)

    res = supa.table("cliente").select("clienteid, razon_social").execute()
    clientes = res.data or []

    # 1) Match exacto normalizado
    for c in clientes:
        if normalize(c["razon_social"]) == nombre_norm:
            return c["clienteid"]

    # 2) Match casi exacto (contiene / contenido)
    for c in clientes:
        rn = normalize(c["razon_social"])
        if nombre_norm in rn or rn in nombre_norm:
            if len(nombre_norm) >= 4:
                return c["clienteid"]

    return 1  # fallback: cliente genérico CLOUDIA


# =========================================================
# 1) Transformar stg_factura → factura
# =========================================================
def transform_stg_factura_to_factura():
    supa = get_client()
    print("🧾 Transformando stg_factura → factura...")

    # Cargar staging
    res = supa.table("stg_factura").select("*").execute()
    facturas = res.data or []
    if not facturas:
        print("⚠️ No hay facturas en staging.")
        return

    factura_rows = []

    for f in facturas:
        clienteid = find_clienteid(supa, f.get("nombre_cliente"))

        factura_rows.append({
            "id_origen": f.get("id_origen"),
            "clienteid": clienteid,
            "nombre_cliente": f.get("nombre_cliente"),
            "factura_estado": f.get("factura_estado"),
            "forma_pago": f.get("forma_pago"),
            "fecha_emision": f.get("fecha_emision"),
            "fecha_vencimiento": f.get("fecha_vencimiento"),
            "total_declarado": f.get("total_declarado"),
            "observaciones": f.get("observaciones"),
            "raw_json": f.get("raw_json")
        })

    # UPSERT idempotente
    supa.table("factura").upsert(
        factura_rows,
        on_conflict="id_origen"
    ).execute()

    print(f"✅ {len(factura_rows)} facturas insertadas/actualizadas.")


# =========================================================
# 2) Transformar stg_linea → factura_linea
# =========================================================
def transform_stg_linea_to_factura_linea():
    supa = get_client()
    print("📦 Transformando stg_linea → factura_linea...")

    # Map id_origen → facturaid real
    fac_res = supa.table("factura").select("facturaid, id_origen").execute()
    mapa = {str(f["id_origen"]): f["facturaid"] for f in fac_res.data or []}

    # Cargar líneas staging
    res = supa.table("stg_linea").select("*").execute()
    lineas = res.data or []
    if not lineas:
        print("⚠️ No hay líneas en staging.")
        return

    rows = []
    for l in lineas:
        facturaid = mapa.get(str(l.get("id_origen_factura")))
        if not facturaid:
            continue

        rows.append({
            "facturaid": facturaid,
            "id_origen_linea": l.get("id_origen_linea"),
            "ean": l.get("ean"),
            "nombre": l.get("nombre"),
            "cantidad": l.get("cantidad"),
            "precio_unit": l.get("precio_unit"),
            "dto": l.get("dto"),
            "iva_pct": l.get("iva_pct"),
            "subtotal": l.get("subtotal"),
            "total_linea": l.get("total_linea"),
            "extra_jsonb": l.get("extra_jsonb")
        })

    supa.table("factura_linea").upsert(
        rows,
        on_conflict="id_origen_linea"
    ).execute()

    print(f"✅ {len(rows)} líneas insertadas/actualizadas.")


# =========================================================
# 3) Transformar factura → pedido (cliente real)
# =========================================================
def transform_factura_to_pedido():
    supa = get_client()
    print("🧾 Generando pedidos desde facturas...")

    res = supa.table("factura").select("*").execute()
    facturas = res.data or []
    if not facturas:
        print("⚠️ No hay facturas.")
        return

    pedidos_rows = []

    for f in facturas:
        pedidos_rows.append({
            "numero": f"FAC-{f['id_origen']}",
            "clienteid": f.get("clienteid") or 1,
            "formapagoid": 1,
            "estado_pedidoid": 2,
            "fecha_pedido": f.get("fecha_emision") or str(date.today()),
            "fecha_limite": f.get("fecha_vencimiento"),
            "referencia_cliente": f.get("observaciones"),
            "regionid": 1,
        })

    supa.table("pedido").upsert(
        pedidos_rows,
        on_conflict="numero"
    ).execute()

    print(f"✅ {len(pedidos_rows)} pedidos generados/actualizados.")
