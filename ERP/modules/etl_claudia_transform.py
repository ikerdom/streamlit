# ============================================
# ETL Cloudia – Versión DEFINITIVA ROBUSTA
# ============================================

import unicodedata
from datetime import date
from modules.supa_client import get_client


# -------------------------------------------------------------
# NORMALIZAR TEXTO
# -------------------------------------------------------------
def normalize(text):
    if not text:
        return ""
    text = text.strip().lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(text.split())


def norm_ean(v):
    if v is None:
        return None
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s or None


def norm_ref(v):
    if v is None:
        return None
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s or None


# -------------------------------------------------------------
# MAPEOS BÁSICOS
# -------------------------------------------------------------
def map_formapagoid(fp):
    if not fp:
        return 1
    s = fp.lower()
    if "tarjeta" in s:
        return 5
    if "recibo" in s or "dom" in s:
        return 2
    if "60" in s:
        return 4
    if "30" in s:
        return 3
    if "transfer" in s:
        return 3
    return 1


def map_estado_pedidoid(e):
    if not e:
        return 1
    s = e.lower()
    if "export" in s or "factur" in s:
        return 2
    if "pend" in s:
        return 1
    if "anul" in s or "cancel" in s:
        return 3
    return 1


def map_tipo_pedidoid(t):
    if not t:
        return 1
    s = t.upper()
    if s == "VEN":
        return 1
    if s == "COM":
        return 2
    if s in ("DEV", "ABN"):
        return 3
    return 1


MAP_TRABAJADOR = {
    "iker@entenova.com": 5,
    "maria@entenova.com": 6,
    "maria.santos@empresa.com": 3,
    "ivan.gomez@empresa.com": 4,
    "idomingiba1@gmail.com": 13,
}

def map_trabajadorid(email):
    if not email:
        return None
    return MAP_TRABAJADOR.get(email.strip().lower())


# -------------------------------------------------------------
# CLIENTE
# -------------------------------------------------------------
def build_cliente_index(clientes):
    idx = {}
    for c in clientes:
        n = normalize(c.get("razon_social"))
        if n:
            idx[n] = c["clienteid"]
    return clientes, idx

def find_or_create_clienteid(supa, nombre_cliente, id_origen, clientes, idx):
    """
    MATCH EXACTO → MATCH APROXIMADO → UPSERT SEGURO POR IDENTIFICADOR
    Nunca volverá a romper por duplicate key (cliente_identificador_key)
    """

    if not nombre_cliente:
        return 1  # fallback cliente genérico

    norm = normalize(nombre_cliente)

    # 1) Match exacto memoria
    if norm in idx:
        return idx[norm]

    # 2) Match aproximado
    for c in clientes:
        rn = normalize(c.get("razon_social"))
        if rn and (norm in rn or rn in norm) and len(norm) >= 4:
            cid = c["clienteid"]
            idx[norm] = cid
            return cid

    # 3) UPSERT TOTAL (si existe lo devuelve, si no lo crea)
    nuevo = {
        "identificador": f"CLOUDIA_AUTO_{id_origen}",
        "razon_social": nombre_cliente,
        "estadoid": 1,
        "formapagoid": 1,
        "perfil_completo": False,
        "tipo_cliente": "cliente",
    }

    res = supa.table("cliente").upsert(
        nuevo,
        on_conflict="identificador",
        returning="representation"   # ← super importante
    ).execute()

    data = res.data or []
    if not data:
        return 1

    cid = data[0]["clienteid"]

    # añadir a cache local
    nuevo["clienteid"] = cid
    clientes.append(nuevo)
    idx[norm] = cid

    return cid

# -------------------------------------------------------------
# PRODUCTOS
# -------------------------------------------------------------
def build_producto_indexes(productos):
    idx_ean = {}
    idx_ref = {}
    for p in productos:
        e = norm_ean(p.get("ean"))
        r = norm_ref(p.get("referencia"))
        if e:
            idx_ean[e] = p["productoid"]
        if r:
            idx_ref[r] = p["productoid"]
    return idx_ean, idx_ref


def find_or_create_clienteid(supa, nombre_cliente, id_origen, clientes, idx):
    if not nombre_cliente:
        return 1

    norm = normalize(nombre_cliente)

    # Cache exacta
    if norm in idx:
        return idx[norm]

    # búsqueda aproximada
    for c in clientes:
        rn = normalize(c.get("razon_social"))
        if rn and (norm in rn or rn in norm):
            cid = c["clienteid"]
            idx[norm] = cid
            return cid

    # UPSERT SOLO SI NO EXISTE
    nuevo = {
        "identificador": f"CLOUDIA_AUTO_{id_origen}",
        "razon_social": nombre_cliente,
        "estadoid": 1,
        "formapagoid": 1,
        "perfil_completo": False,
        "tipo_cliente": "cliente",
    }

    res = supa.table("cliente").upsert(
        nuevo, 
        on_conflict="identificador", 
        returning="representation"
    ).execute()

    cid = res.data[0]["clienteid"]
    nuevo["clienteid"] = cid
    clientes.append(nuevo)
    idx[norm] = cid

    return cid


def transform_stg_factura_to_factura():
    supa = get_client()
    print("🧾 Transformando stg_factura → factura...")

    PAGE = 1000
    offset = 0
    total = 0

    # cache clientes
    cli_res = supa.table("cliente").select("clienteid, razon_social").execute()
    clientes, idx = build_cliente_index(cli_res.data or [])

    while True:
        res = (
            supa.table("stg_factura")
            .select("*")
            .order("id_origen")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        batch = res.data or []
        if not batch:
            break

        rows = []
        for f in batch:
            cid = find_or_create_clienteid(
                supa, f.get("nombre_cliente"), f.get("id_origen"), clientes, idx
            )

            ff = dict(f)
            ff["clienteid"] = cid
            rows.append(ff)

        supa.table("factura").upsert(
            rows, on_conflict="id_origen"
        ).execute()

        total += len(rows)
        print(f"   → Página {offset//PAGE+1}: {len(rows)} facturas procesadas")
        offset += PAGE

    print(f"✅ TOTAL FACTURAS: {total}")
def transform_stg_linea_to_factura_linea():
    supa = get_client()
    print("📦 Transformando stg_linea → factura_linea (paginado)...")

    PAGE = 1000
    offset = 0
    total = 0

    while True:
        res = (
            supa.table("stg_linea")
            .select("*")
            .order("id_origen_linea")
            .range(offset, offset + PAGE - 1)
            .execute()
        )

        batch = res.data or []
        if not batch:
            break

        rows = []
        for l in batch:
            ff = {
                "id_origen_linea": l["id_origen_linea"],
                "id_origen_factura": l["id_origen_factura"],
                "ean": l.get("ean"),
                "nombre": l.get("nombre"),
                "cantidad": l.get("cantidad"),
                "precio_unit": l.get("precio_unit"),
                "dto": l.get("dto"),
                "iva_pct": l.get("iva_pct"),
                "subtotal": l.get("subtotal"),
                "total_linea": l.get("total_linea"),
                "extra_jsonb": l.get("extra_jsonb"),
                "idproductoreferencia": l.get("idproductoreferencia"),
            }
            rows.append(ff)

        supa.table("factura_linea").upsert(
            rows,
            on_conflict="id_origen_linea"
        ).execute()

        total += len(rows)
        print(f"   → Página {offset//PAGE+1}: {len(rows)} líneas procesadas")
        offset += PAGE

    print(f"✅ TOTAL LÍNEAS: {total}")


# -------------------------------------------------------------
# BLOQUE 3 — PEDIDOS (SIN TIMEOUT)
# -------------------------------------------------------------
def transform_factura_to_pedido():
    supa = get_client()
    print("🧾 Generando pedidos...")

    BATCH = 500
    offset = 0
    total = 0

    while True:
        res = (
            supa.table("factura")
            .select("*")
            .order("id_origen")
            .range(offset, offset + BATCH - 1)
            .execute()
        )

        batch = res.data or []
        if not batch:
            break

        rows = []
        for f in batch:
            raw = f.get("raw_json") or {}
            creador = raw.get("creado_por")

            rows.append({
                "numero": f.get("numero_serie") or f"FAC-{f['id_origen']}",
                "id_origen_factura": f["id_origen"],
                "clienteid": f.get("clienteid") or 1,
                "formapagoid": map_formapagoid(f.get("forma_pago")),
                "estado_pedidoid": map_estado_pedidoid(f.get("factura_estado")),
                "tipo_pedidoid": map_tipo_pedidoid(f.get("tipo_documento")),
                "fecha_pedido": f.get("fecha_emision") or str(date.today()),
                "fecha_limite": f.get("fecha_vencimiento"),
                "base_imponible": f.get("base_imponible"),
                "impuestos": f.get("impuestos"),
                "total_pedido": f.get("total_calculado"),
                "referencia_cliente": f.get("observaciones"),
                "trabajadorid": map_trabajadorid(creador),
            })

        supa.table("pedido").upsert(rows, on_conflict="numero").execute()
        total += len(rows)
        print(f"   → Página {offset//BATCH+1}: {len(rows)} pedidos")

        offset += BATCH

    print(f"✅ TOTAL PEDIDOS: {total}")

def generar_pedidos_desde_facturas():
    supa = get_client()
    print("🧾 Generando pedidos desde facturas...")

    PAGE = 1000
    offset = 0
    total = 0

    while True:
        res = (
            supa.table("factura")
            .select("*")
            .order("id_origen")
            .range(offset, offset + PAGE - 1)
            .execute()
        )

        batch = res.data or []
        if not batch:
            break

        rows = []
        for f in batch:
            rows.append({
                "id_origen": f["id_origen"],
                "clienteid": f["clienteid"],
                "total": f["total_declarado"],
                "fecha": f["fecha_emision"],
            })

        supa.table("pedido").upsert(rows, on_conflict="id_origen").execute()

        total += len(rows)
        print(f"   → Página {offset//PAGE+1}: {len(rows)} pedidos generados")
        offset += PAGE

    print(f"✅ TOTAL PEDIDOS: {total}")

# -------------------------------------------------------------
# RUN GLOBAL
# -------------------------------------------------------------
def run_etl_claudia_facturas():
    print("\n🚀 INICIANDO ETL CLOUDIA → ERP\n")
    transform_stg_factura_to_factura()
    transform_stg_linea_to_factura_linea()
    transform_factura_to_pedido()
    print("\n🎯 FIN COMPLETO\n")
