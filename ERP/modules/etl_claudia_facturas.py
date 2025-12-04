# ============================================
# modules/etl_claudia_facturas.py
#  - stg_factura       → factura
#  - stg_linea         → factura_linea
#  - factura           → pedido
#  - factura_linea     → pedido_detalle
#  - pedido_detalle    → pedido_totales
# ============================================

from datetime import date
from decimal import Decimal, InvalidOperation
from collections import defaultdict

from modules.supa_client import get_client


# --------------------------------------------
# Helpers numéricos y de chunks
# --------------------------------------------
def _chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _to_decimal(x, default=Decimal("0")):
    try:
        if x is None or x == "":
            return default
        return Decimal(str(x))
    except (InvalidOperation, TypeError, ValueError):
        return default


# --------------------------------------------
# Registros base (forma_pago, cliente base, etc.)
# --------------------------------------------
def ensure_base_records(supa):
    print("🔧 Verificando registros base (forma_pago, cliente base, etc.)...")

    # Forma de pago base (ID=1) Contado
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

    # Cliente base (ID=1) — por seguridad
    cl = supa.table("cliente").select("clienteid").eq("clienteid", 1).execute()
    if not cl.data:
        supa.table("cliente").insert({
            "clienteid": 1,
            "estadoid": 1,  # cliente_estado 1 debe existir
            "razon_social": "Cliente genérico Cloudia",
            "identificador": "CLOUDIA_BASE",
            "formapagoid": 1,
            "cuenta_comision": 0,
            "tipo_cliente": "cliente",
            "estado_presupuesto": "pendiente",
        }).execute()
        print("✅ Cliente base creado (ID=1)")

# ============================================
# 1) STAGING → FACTURA
# ============================================
def transform_stg_factura_to_factura():
    supa = get_client()
    print("🧾 Transformando stg_factura → factura ...")

    res = supa.table("stg_factura").select("*").execute()
    facturas = res.data or []
    if not facturas:
        print("⚠️ No se encontraron facturas en stg_factura.")
        return

    rows = []
    for f in facturas:
        rows.append({
            "id_origen": f.get("id_origen"),

            # 🆕 CAMPOS NUEVOS
            "tipo_documento": f.get("tipo_documento"),
            "factura_serie": f.get("factura_serie"),
            "factura_numero": f.get("factura_numero"),
            "nombre_empresa": f.get("nombre_empresa"),
            "tipo_tercero": f.get("tipo_tercero"),

            # Campos que ya teníamos
            "nombre_cliente": f.get("nombre_cliente"),
            "factura_estado": f.get("factura_estado"),
            "forma_pago": f.get("forma_pago"),
            "fecha_emision": f.get("fecha_emision"),
            "fecha_vencimiento": f.get("fecha_vencimiento"),
            "total_declarado": f.get("total_declarado"),
            "observaciones": f.get("observaciones"),
            "raw_json": f.get("raw_json"),
        })

    # Idempotente por id_origen
    total = 0
    for batch in _chunk(rows, 1000):
        supa.table("factura").upsert(
            batch,
            on_conflict="id_origen"
        ).execute()
        total += len(batch)

    print(f"✅ {total} facturas upsertadas en factura.")



# ============================================
# 2) STAGING → FACTURA_LINEA
# ============================================
def transform_stg_linea_to_factura_linea():
    supa = get_client()
    print("📦 Transformando stg_linea → factura_linea ...")

    res = supa.table("stg_linea").select("*").execute()
    lineas = res.data or []
    if not lineas:
        print("⚠️ No se encontraron líneas en stg_linea.")
        return

    rows = []
    for l in lineas:
        rows.append({
            "id_origen_linea": l.get("id_origen_linea"),
            "id_origen_factura": l.get("id_origen_factura"),
            "ean": l.get("ean"),
            "nombre": l.get("nombre"),
            "cantidad": l.get("cantidad"),
            "precio_unit": l.get("precio_unit"),
            "dto": l.get("dto"),
            "iva_pct": l.get("iva_pct"),
            "subtotal": l.get("subtotal"),
            "total_linea": l.get("total_linea"),
            "extra_jsonb": l.get("extra_jsonb"),
        })

    total = 0
    for batch in _chunk(rows, 1000):
        supa.table("factura_linea").upsert(
            batch,
            on_conflict="id_origen_linea"
        ).execute()
        total += len(batch)

    print(f"✅ {total} líneas upsertadas en factura_linea.")


# ============================================
# 3) FACTURA → PEDIDO (enlazando cliente)
# ============================================
def _obtener_o_crear_cliente_por_nombre(supa, nombre_cliente: str) -> int:
    """
    Busca cliente por razon_social. Si no existe, lo crea con identificador ficticio CLOUDIA_XXXX.
    Devuelve clienteid.
    """
    if not nombre_cliente:
        return 1  # Cliente genérico

    nombre_cliente = nombre_cliente.strip()

    # 1) Buscar por razón social exacta
    res = supa.table("cliente").select("clienteid").eq("razon_social", nombre_cliente).execute()
    if res.data:
        return res.data[0]["clienteid"]

    # 3) Crear cliente nuevo con identificador falso pero NO NULL
    pseudo_ident = "CLOUDIA_AUTO_" + str(abs(hash(nombre_cliente)))[0:10]

    try:
        insert_res = supa.table("cliente").insert({
            "estadoid": 1,
            "razon_social": nombre_cliente,
            "grupoid": None,
            "categoriaid": None,
            "cuenta_comision": 0,
            "observaciones": None,
            "formapagoid": 1,           # Contado por defecto
            "identificador": pseudo_ident,
            "trabajadorid": None,
            "perfil_completo": False,
            "tipo_cliente": "cliente",
            "estado_presupuesto": "pendiente",
            "tarifaid": None
        }).execute()
        if insert_res.data:
            nuevo_id = insert_res.data[0]["clienteid"]
            return nuevo_id
    except Exception as e:
        print(f"⚠️ Error creando cliente '{nombre_cliente}': {e}")

    # Si algo falla, usar el genérico
    return 1


def transform_factura_to_pedido():
    supa = get_client()
    ensure_base_records(supa)

    print("🧾 Transformando factura → pedido ...")

    res = supa.table("factura").select("*").execute()
    facturas = res.data or []
    if not facturas:
        print("⚠️ No hay facturas en tabla factura.")
        return

    pedidos_rows = []
    vistos = set()

    for f in facturas:
        fid = f.get("id_origen")
        if fid is None:
            continue

        numero = f"FAC-{fid}"

        if numero in vistos:
            continue
        vistos.add(numero)

        nombre_cliente = f.get("nombre_cliente")
        clienteid = _obtener_o_crear_cliente_por_nombre(supa, nombre_cliente)

        fecha_emision = f.get("fecha_emision") or str(date.today())
        fecha_vencimiento = f.get("fecha_vencimiento")

        pedidos_rows.append({
            "numero": numero,
            "clienteid": clienteid,
            "formapagoid": 1,
            "estado_pedidoid": 2,
            "fecha_pedido": fecha_emision,
            "fecha_limite": fecha_vencimiento,
            "referencia_cliente": f.get("observaciones"),
            "regionid": 1,
            "id_origen": fid
        })

    if not pedidos_rows:
        print("⚠️ No hay pedidos que insertar.")
        return

    total = 0
    for batch in _chunk(pedidos_rows, 500):
        supa.table("pedido").upsert(
            batch,
            on_conflict="numero"
        ).execute()
        total += len(batch)

    print(f"✅ {total} pedidos insertados/actualizados.")


# ============================================
# 4) FACTURA_LINEA → PEDIDO_DETALLE
# ============================================
def transform_factura_linea_to_pedido_detalle():
    supa = get_client()
    print("📦 Transformando factura_linea → pedido_detalle ...")

    # Mapa factura (id_origen) → pedidoid
    pedidos_res = supa.table("pedido").select("pedidoid,id_origen,numero").execute()
    pedidos = pedidos_res.data or []

    factura_to_pedido = {}
    for p in pedidos:
        pid = p["pedidoid"]
        fid = p.get("id_origen")
        if fid is not None:
            factura_to_pedido[int(fid)] = pid
        else:
            numero = p.get("numero")
            if numero and numero.startswith("FAC-"):
                try:
                    fid2 = int(numero.replace("FAC-", ""))
                    factura_to_pedido[fid2] = pid
                except ValueError:
                    pass

    if not factura_to_pedido:
        print("⚠️ No hay mapa factura→pedido. ¿Has ejecutado antes transform_factura_to_pedido?")
        return

    # Cargar todas las líneas de factura_linea
    res = supa.table("factura_linea").select("*").execute()
    lineas = res.data or []
    if not lineas:
        print("⚠️ No hay líneas en factura_linea.")
        return

    detalle_rows = []
    productos_creados = 0

    for l in lineas:
        fid = l.get("id_origen_factura")
        if fid is None:
            continue

        try:
            fid_int = int(fid)
        except (TypeError, ValueError):
            continue

        pedidoid = factura_to_pedido.get(fid_int)
        if not pedidoid:
            continue

        ean = l.get("ean")
        nombre = l.get("nombre") or "Producto sin nombre"
        nombre = nombre.strip()[:250]

        cantidad = _to_decimal(l.get("cantidad") or 0)
        if cantidad <= 0:
            cantidad = Decimal("1")
        cantidad_int = int(round(float(cantidad))) or 1

        precio_unit = _to_decimal(l.get("precio_unit") or 0)
        dto_pct = _to_decimal(l.get("dto") or 0)
        iva_pct = _to_decimal(l.get("iva_pct") or 0)
        subtotal = _to_decimal(l.get("subtotal") or 0)
        total_linea = _to_decimal(l.get("total_linea") or 0)

        # Si no viene subtotal, lo calculamos
        if subtotal == 0 and precio_unit != 0:
            subtotal = (precio_unit * cantidad) * (Decimal("1") - dto_pct / Decimal("100"))

        # Si no viene total_linea, lo calculamos desde subtotal+IVA
        if total_linea == 0 and subtotal != 0:
            total_linea = subtotal * (Decimal("1") + iva_pct / Decimal("100"))

        # Buscar/crear producto por EAN si existe
        productoid = None
        if ean:
            try:
                prod_res = supa.table("producto").select("productoid").eq("ean", str(ean)).execute()
                if prod_res.data:
                    productoid = prod_res.data[0]["productoid"]
                else:
                    # Crear producto básico, con limpieza para evitar errores de JSON
                    nombre_limpio = (nombre or "Producto sin nombre").strip()[:250]

                    try:
                        if precio_unit not in [None, "", Decimal("0"), 0]:
                            precio_val = float(precio_unit)
                            if precio_val != precio_val:  # NaN
                                precio_val = None
                        else:
                            precio_val = None
                    except Exception:
                        precio_val = None

                    row = {
                        "nombre": nombre_limpio,
                        "ean": str(ean),
                        "impuestoid": 3,     # IVA 21% genérico
                        "publico": True,
                    }
                    if precio_val is not None:
                        row["precio_generico"] = precio_val

                    # Eliminar claves con valores claramente problemáticos (por si acaso)
                    row = {
                        k: v for k, v in row.items()
                        if v is not None
                        and not (isinstance(v, float) and (v != v))  # NaN
                    }

                    try:
                        ins_res = supa.table("producto").insert(row).execute()
                        if ins_res.data:
                            productoid = ins_res.data[0]["productoid"]
                            productos_creados += 1
                    except Exception as e:
                        # Si da error (por ejemplo JSON 556), saltamos el producto y seguimos
                        print(f"⚠️ Error creando producto para EAN {ean}: {e}")
                        productoid = None
            except Exception as e:
                print(f"⚠️ Error buscando/creando producto para EAN {ean}: {e}")
                productoid = None

        # Construimos la línea de pedido_detalle
        try:
            detalle_rows.append({
                "pedidoid": pedidoid,
                "productoid": productoid,
                "ean": str(ean) if ean else None,
                "isbn": None,
                "nombre_producto": nombre,
                "referencia": None,
                "cantidad": cantidad_int,
                "unidad": "ud",
                "precio_unitario": float(precio_unit.quantize(Decimal("0.01"))) if precio_unit is not None else 0.0,
                "descuento_pct": float(dto_pct.quantize(Decimal("0.01"))) if dto_pct is not None else 0.0,
                "comision_pct": 0.0,
                "estado_linea_pedidoid": None,
                "importe_total_linea": float(total_linea.quantize(Decimal("0.01"))) if total_linea is not None else 0.0,
                "fecha_estado": None,
                "precio_real": float(precio_unit.quantize(Decimal("0.01"))) if precio_unit is not None else 0.0,
                "iva_pct": float(iva_pct.quantize(Decimal("0.01"))) if iva_pct is not None else 0.0,
                "importe_base": float(subtotal.quantize(Decimal("0.01"))) if subtotal is not None else 0.0,
                "id_origen": l.get("id_origen_linea"),
                "raw_json": l.get("extra_jsonb"),
            })
        except Exception as e:
            # Si algo muy raro en los datos rompe incluso esto, solo log y seguimos
            print(f"⚠️ Error construyendo línea de pedido para factura {fid_int}, EAN {ean}: {e}")

    if not detalle_rows:
        print("⚠️ No se generaron líneas de pedido (¿no hay relación factura↔pedido?).")
        return

    total_insertadas = 0
    for batch in _chunk(detalle_rows, 500):
        try:
            supa.table("pedido_detalle").upsert(
                batch,
                on_conflict="id_origen"
            ).execute()
            total_insertadas += len(batch)
        except Exception as e:
            # Si alguna línea del batch tiene JSON malo, lo logueamos y seguimos con el resto
            print(f"⚠️ Error upsertando batch de pedido_detalle: {e}")

    print(f"✅ {total_insertadas} líneas de pedido insertadas/actualizadas.")
    if productos_creados > 0:
        print(f"🆕 {productos_creados} productos nuevos creados automáticamente.")


# ============================================
# 5) PEDIDO_DETALLE → PEDIDO_TOTALES
# ============================================
def update_pedido_totales_from_detalle():
    supa = get_client()
    print("💰 Calculando totales desde pedido_detalle ...")

    pedidos_res = supa.table("pedido").select("pedidoid").execute()
    pedidos = pedidos_res.data or []
    if not pedidos:
        print("⚠️ No hay pedidos en la tabla pedido.")
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
        })

    if not total_rows:
        print("⚠️ No hay totales que calcular.")
        return

    for batch in _chunk(total_rows, 500):
        supa.table("pedido_totales").upsert(
            batch,
            on_conflict="pedidoid"
        ).execute()

    print(f"✅ Totales calculados/actualizados para {len(total_rows)} pedidos.")


# ============================================
# Orquestador principal
# ============================================
def run_facturas_etl():
    print("\n=============== ETL CLOUDIA → ERP ===============\n")

    # 1) STAGING → FACTURA
    transform_stg_factura_to_factura()

    # 2) STAGING → FACTURA_LINEA
    transform_stg_linea_to_factura_linea()

    # 3) FACTURA → PEDIDO (con clientes enlazados)
    transform_factura_to_pedido()

    # 4) FACTURA_LINEA → PEDIDO_DETALLE
    transform_factura_linea_to_pedido_detalle()

    # 5) PEDIDO_DETALLE → PEDIDO_TOTALES
    update_pedido_totales_from_detalle()

    print("\n🎯 ETL COMPLETO\n")
