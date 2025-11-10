# ============================================
# modules/etl_claudia_transform.py
# ============================================
from datetime import date
from modules.supa_client import get_client

# ======================================================
# 🧹 RESET opcional (borra datos ERP antes de cargar)
# ======================================================
def reset_erp_data():
    print("🧹 Limpiando tablas ERP antes de cargar nuevos datos...")
    supa = get_client()

    # Orden correcto por FKs
    tablas_pk = [
        ("pedido_detalle", "pedido_detalleid"),
        ("pedido_totales", "pedidoid"),
        ("pedido", "pedidoid"),
        ("producto", "productoid"),
        ("cliente", "clienteid"),
    ]

    for tabla, pk in tablas_pk:
        try:
            # Forzar WHERE para evitar 21000
            supa.table(tabla).delete().gte(pk, 0).execute()
            print(f"   - Tabla {tabla} vaciada ✅")
        except Exception as e:
            print(f"   ⚠️ No se pudo vaciar {tabla}: {e}")

    print("✅ Datos previos eliminados correctamente.\n")

# ======================================================
# 🧩 FUNCIONES AUXILIARES
# ======================================================
def ensure_base_records(supa):
    """Crea registros mínimos en tablas maestras si faltan."""
    print("🔧 Verificando registros base...")

    # Forma de pago base (ID=1)
    fp = supa.table("forma_pago").select("formapagoid").eq("formapagoid", 1).execute()
    if not fp.data:
        supa.table("forma_pago").insert({
            "formapagoid": 1,
            "nombre": "Contado",
            "dias": 0,
            "habilitado": True
        }).execute()

    # Estado de pedido base (ID=2 = Pendiente)
    ep = supa.table("pedido_estado").select("estado_pedidoid").eq("estado_pedidoid", 2).execute()
    if not ep.data:
        supa.table("pedido_estado").insert({
            "estado_pedidoid": 2,
            "nombre": "Pendiente",
            "habilitado": True
        }).execute()

    # Región base (ID=1 = Península)
    rg = supa.table("region").select("regionid").eq("regionid", 1).execute()
    if not rg.data:
        supa.table("region").insert({
            "regionid": 1,
            "nombre": "Península",
            "habilitado": True
        }).execute()

    # Cliente base (ID=1) — requiere cliente_estado.id=1 existente en tu BBDD
    cl = supa.table("cliente").select("clienteid").eq("clienteid", 1).execute()
    if not cl.data:
        supa.table("cliente").insert({
            "clienteid": 1,
            "estadoid": 1,  # asegúrate de tener cliente_estado (1) creado
            "razon_social": "Cliente genérico Cloudia",
            "identificador": "CLOUDIA_BASE",
            "formapagoid": 1,
            "cuenta_comision": 0
        }).execute()
        print("✅ Cliente base creado (ID=1)")


def _chunk(lst, n):
    """Divide lista en bloques de tamaño n."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# ======================================================
# 🧾 TRANSFORM: stg_factura → pedido
# ======================================================
def transform_facturas_to_pedidos():
    supa = get_client()
    ensure_base_records(supa)
    print("🧾 Cargando facturas desde stg_factura...")

    res = supa.table("stg_factura").select("*").execute()
    facturas = res.data or []
    if not facturas:
        print("⚠️ No se encontraron facturas en staging.")
        return

    pedidos_rows = []
    for f in facturas:
        fid = f.get("id_origen")
        numero = f"FAC-{fid}"

        pedidos_rows.append({
            "numero": numero,
            "clienteid": 1,                 # cliente genérico
            "formapagoid": 1,               # contado
            "estado_pedidoid": 2,           # pendiente
            "fecha_pedido": f.get("fecha_emision") or str(date.today()),
            "fecha_limite": f.get("fecha_vencimiento"),
            "referencia_cliente": f.get("observaciones"),
            "regionid": 1,                  # Península
        })

    # Con limpieza previa, puedes usar insert directo; si prefieres idempotencia, deja upsert.
    supa.table("pedido").insert(pedidos_rows).execute()
    print(f"✅ {len(pedidos_rows)} pedidos insertados correctamente.")

# ======================================================
# 📦 TRANSFORM: stg_linea → pedido_detalle (agrupar por pedidoid + ean)
# ======================================================
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import math

def _chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def _to_decimal(x, default=Decimal("0")):
    try:
        if x is None or x == "":
            return default
        return Decimal(str(x))
    except (InvalidOperation, TypeError, ValueError):
        return default

def transform_lineas_to_pedido_detalle():
    supa = get_client()
    print("📦 Cargando líneas desde stg_linea...")

    # Mapa factura→pedido
    pedidos_res = supa.table("pedido").select("pedidoid, numero").execute()
    pedidos_map = {p["numero"].replace("FAC-", ""): p["pedidoid"] for p in (pedidos_res.data or [])}

    # Staging líneas
    res = supa.table("stg_linea").select("*").execute()
    lineas = res.data or []
    if not lineas:
        print("⚠️ No se encontraron líneas en staging.")
        return

    productos_creados = 0
    grupos = defaultdict(list)  # (pedidoid, ean) -> [líneas]

    # --- Agrupar por (pedidoid, ean)
    for l in lineas:
        id_factura = str(l.get("id_origen_factura"))
        pedidoid = pedidos_map.get(id_factura)
        if not pedidoid:
            continue

        ean = l.get("ean")
        if not ean or str(ean).strip() == "":
            # si no hay EAN, hacemos clave por línea (no rompe el índice porque UNIQ es (pedidoid, ean) y NULLs no chocan)
            ean = None

        grupos[(pedidoid, ean)].append(l)

    detalle_rows = []

    for (pedidoid, ean), g in grupos.items():
        base = g[0]
        nombre = (base.get("nombre") or "Producto sin nombre")[:250]

        # Normalizaciones numéricas
        iva_pct = _to_decimal(base.get("iva_pct") or base.get("tasaimpuesto") or 0)
        # sumamos en positivo para evitar negativos (ajustes/abonos)
        cantidad_sum = sum(abs(_to_decimal(li.get("cantidad") or 0)) for li in g)
        subtotal_sum = sum(abs(_to_decimal(li.get("subtotal") or 0)) for li in g)

        # total_linea puede venir o lo calculamos a partir de subtotal + IVA
        total_linea_sum = Decimal("0")
        for li in g:
            li_sub = abs(_to_decimal(li.get("subtotal") or 0))
            li_total = _to_decimal(li.get("total_linea"))
            if li_total == 0 and li_sub != 0:
                li_total = li_sub * (Decimal("1") + (iva_pct / Decimal("100")))
            total_linea_sum += abs(li_total)

        # cantidad = INTEGER -> redondeamos al entero más cercano, mínimo 1
        cantidad_int = int(max(1, int(round(float(cantidad_sum)))))  # evita 65.0 → 65

        # precio_unitario = subtotal_total / cantidad
        precio_unit = (subtotal_sum / Decimal(cantidad_int)) if cantidad_int else Decimal("0")

        # dto: tomamos el del primer registro si lo hay
        dto = _to_decimal(base.get("dto") or 0)

        productoid = None
        if ean:
            # intenta localizar/crear producto por EAN
            prod_res = supa.table("producto").select("productoid").eq("ean", ean).execute()
            if prod_res.data:
                productoid = prod_res.data[0]["productoid"]
            else:
                try:
                    insert_res = supa.table("producto").insert({
                        "nombre": nombre,
                        "ean": str(ean),
                        "precio_generico": float(precio_unit),  # NUMERIC en PG acepta float en API
                        "impuestoid": 3,  # IVA general por defecto
                        "publico": True
                    }).execute()
                    if insert_res.data:
                        productoid = insert_res.data[0]["productoid"]
                        productos_creados += 1
                except Exception as e:
                    print(f"⚠️ Error creando producto {ean}: {e}")

        detalle_rows.append({
            "pedidoid": pedidoid,
            "productoid": productoid,
            "ean": ean,  # puede ser None; los NULL no rompen el índice único (se tratan como distintos)
            "nombre_producto": nombre,
            "cantidad": cantidad_int,                               # <-- INTEGER SIEMPRE
            "precio_unitario": float(precio_unit.quantize(Decimal('0.01'))),
            "descuento_pct": float(dto.quantize(Decimal('0.01'))),
            "iva_pct": float(iva_pct.quantize(Decimal('0.01'))),
            "importe_base": float(subtotal_sum.quantize(Decimal('0.01'))),
            "importe_total_linea": float(total_linea_sum.quantize(Decimal('0.01'))),
        })

    if not detalle_rows:
        print("⚠️ No se insertaron líneas (IDs no coinciden).")
        return

    # Inserción por lotes, idempotente
    total_insertadas = 0
    for batch in _chunk(detalle_rows, 500):
        # Usa upsert para re-ejecuciones seguras (no colapsa si ya existen esas claves)
        supa.table("pedido_detalle").upsert(
            batch,
            on_conflict="pedidoid, ean"
        ).execute()
        total_insertadas += len(batch)

    print(f"✅ {total_insertadas} líneas insertadas/actualizadas correctamente (agrupadas).")
    if productos_creados > 0:
        print(f"🆕 {productos_creados} productos nuevos creados automáticamente.")

# ======================================================
# 💰 TRANSFORM: Calcular pedido_totales
# ======================================================
def update_pedido_totales():
    supa = get_client()
    print("💰 Calculando totales...")

    pedidos_res = supa.table("pedido").select("pedidoid").execute()
    pedidos = pedidos_res.data or []

    if not pedidos:
        print("⚠️ No hay pedidos para totalizar.")
        return

    total_rows = []
    for p in pedidos:
        pid = p["pedidoid"]
        dets_res = supa.table("pedido_detalle").select(
            "importe_base, importe_total_linea"
        ).eq("pedidoid", pid).execute()
        dets = dets_res.data or []

        base = sum(float(d.get("importe_base") or 0) for d in dets)
        total = sum(float(d.get("importe_total_linea") or 0) for d in dets)
        iva = total - base

        total_rows.append({
            "pedidoid": pid,
            "base_imponible": round(base, 2),
            "iva_importe": round(iva, 2),
            "total_importe": round(total, 2),
            # gastos_envio / envio_sin_cargo los dejamos por defecto
        })

    # upsert por PK pedidoid
    for batch in _chunk(total_rows, 500):
        supa.table("pedido_totales").upsert(batch, on_conflict="pedidoid").execute()

    print(f"✅ Totales calculados para {len(total_rows)} pedidos.")
