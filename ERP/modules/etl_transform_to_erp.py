# modules/etl_transform_to_erp.py
import os
import json
import pandas as pd
from datetime import datetime
from modules.supa_client import get_client
from modules.etl_excel_staging import (
    to_date_safe, to_num_safe, to_str_safe, safe_json, insert_rows
)
import os

OUT_DIR = "etl_output"
os.makedirs(OUT_DIR, exist_ok=True)


def transform_clientes(supa):
    print("🧩 Transformando CLIENTES...")

    # 1) Leer staging
    resp = supa.table("stg_xls_cliente").select("id_externo,cif,razon_social,nombre_comercial").execute()
    rows = resp.data or []
    print(f"   · Filas obtenidas: {len(rows)}")

    validos, descartes = [], []

    for r in rows:
        cif = (r.get("cif") or "").strip().upper()
        razon = (r.get("razon_social") or "").strip()
        nombre_com = (r.get("nombre_comercial") or "").strip()

        if not cif:
            descartes.append({**r, "motivo": "Falta CIF"})
            continue

        rec = {
            "identificador": cif,                                     # UNIQUE en tu tabla
            "razon_social": razon or nombre_com or f"Cliente {cif}",  # requerido
            "estadoid": 1,                                            # Activo
            "tipo_cliente": "cliente",                                # cumple el CHECK
        }
        validos.append(rec)

    print(f"   ✅ {len(validos)} válidos, ❌ {len(descartes)} descartados")

    # 2) Auditoría a /output
    pd.DataFrame(validos).to_csv(os.path.join(OUT_DIR, "cliente_valido.csv"), index=False)
    if descartes:
        pd.DataFrame(descartes).to_csv(os.path.join(OUT_DIR, "auditoria_cliente.csv"), index=False)
        with open(os.path.join(OUT_DIR, "cliente_descartado.txt"), "w", encoding="utf-8") as f:
            for d in descartes:
                f.write(f"{(d.get('cif') or '').strip().upper()} — {d.get('motivo')}\n")

    # 3️⃣ Upsert individual (evita conflicto de duplicados)
    if validos:
        print("   ⬆️ Insertando en 'cliente' individualmente (evita duplicados)…")
        for rec in validos:
            try:
                supa.table("cliente").upsert(rec, on_conflict="identificador").execute()
            except Exception as e:
                print(f"   ⚠️ Error con {rec.get('identificador')}: {e}")


    print("   ✅ CLIENTES transformados.")

import os
import pandas as pd
from modules.etl_excel_staging import to_date_safe

OUT_DIR = "etl_output"

def transform_pedidos(supa):
    print("🧩 Transformando PEDIDOS...")

    # Asegurar carpeta de salida
    os.makedirs(OUT_DIR, exist_ok=True)

    # ---------------------------------------------------------
    # 1️⃣ Leer staging
    # ---------------------------------------------------------
    resp = supa.table("stg_xls_pedido").select("*").execute()
    rows = resp.data or []
    print(f"   · Filas obtenidas: {len(rows)}")

    if not rows:
        print("   ⚠️ No hay pedidos en staging.")
        return

    # ---------------------------------------------------------
    # 2️⃣ Preparar equivalencias cliente y forma de pago
    # ---------------------------------------------------------
    # Mapa staging id_externo → razon_social
    stg_cli_resp = supa.table("stg_xls_cliente").select("id_externo, razon_social").execute()
    stg_clientes_map = {}
    for c in stg_cli_resp.data or []:
        if c.get("id_externo"):
            stg_clientes_map[str(c["id_externo"]).strip()] = c["razon_social"].strip().upper()

    # Mapa razon_social → clienteid (ERP real)
    cli_resp = supa.table("cliente").select("clienteid, razon_social").execute()
    clientes_real_map = {c["razon_social"].strip().upper(): c["clienteid"] for c in cli_resp.data or []}

    # Mapa formas de pago (para validar IDs)
    fp_resp = supa.table("forma_pago").select("formapagoid").execute()
    formas_pago_validas = [int(r["formapagoid"]) for r in fp_resp.data or []]

    pedidos_valido, pedidos_desc = [], []

    # ---------------------------------------------------------
    # 3️⃣ Procesar cada pedido
    # ---------------------------------------------------------
    for r in rows:
        try:
            id_externo = str(r.get("id_externo")).strip()
            tercero_id = str(r.get("id_tercero_raw") or "").strip()
            fecha_pedido = to_date_safe(r.get("fecha_pedido"))
            forma_raw = r.get("forma_pago_raw")
            estado_raw = r.get("estado_raw")
            total_base = r.get("total_base") or 0
            total_impuestos = r.get("total_impuestos") or 0
            total = r.get("total") or 0
            observaciones = (r.get("observaciones") or "").strip()

            # Buscar razon_social staging
            razon_stg = stg_clientes_map.get(tercero_id)
            if not razon_stg:
                pedidos_desc.append({**r, "motivo": f"No se encontró cliente en staging para id_tercero_raw={tercero_id}"})
                continue

            # Buscar clienteid real por razón social
            clienteid = clientes_real_map.get(razon_stg)
            if not clienteid:
                pedidos_desc.append({**r, "motivo": f"No se encontró cliente real para razón_social={razon_stg}"})
                continue

            # Forma de pago (default 1 = Contado)
            try:
                formapagoid = int(float(forma_raw)) if str(forma_raw).replace('.', '', 1).isdigit() else 1
            except:
                formapagoid = 1
            if formapagoid not in formas_pago_validas:
                formapagoid = 1

            # Estado pedido (mapear 8→3 Confirmado, otros→1 Borrador)
            estadoid = 3 if str(estado_raw) == "8" else 1

            rec = {
                "numero": str(r.get("id_pedido") or r.get("IDPEDIDO") or r.get("id_externo")).strip(),
                "clienteid": clienteid,
                "fecha_pedido": fecha_pedido,
                "formapagoid": formapagoid,
                "estado_pedidoid": estadoid,
                "regionid": 1,  # Península
            }

            pedidos_valido.append(rec)

        except Exception as e:
            pedidos_desc.append({**r, "motivo": f"Error general: {e}"})

    # ---------------------------------------------------------
    # 4️⃣ Auditoría y guardado
    # ---------------------------------------------------------
    print(f"   ✅ {len(pedidos_valido)} válidos, ❌ {len(pedidos_desc)} descartados")

    if pedidos_valido:
        pd.DataFrame(pedidos_valido).to_csv(os.path.join(OUT_DIR, "pedido_valido.csv"), index=False)
    if pedidos_desc:
        pd.DataFrame(pedidos_desc).to_csv(os.path.join(OUT_DIR, "auditoria_pedido.csv"), index=False)
        with open(os.path.join(OUT_DIR, "pedido_descartado.txt"), "w", encoding="utf-8") as f:
            for d in pedidos_desc:
                f.write(f"{d.get('id_externo')} — {d.get('motivo')}\n")

    # ---------------------------------------------------------
    # 5️⃣ Inserción en ERP real
    # ---------------------------------------------------------
    if pedidos_valido:
        print("   ⬆️ Insertando pedidos en tabla 'pedido'...")
        for rec in pedidos_valido:
            try:
                supa.table("pedido").upsert(rec, on_conflict="numero").execute()
            except Exception as e:
                print(f"   ⚠️ Error insertando pedido {rec.get('numero')}: {e}")

    print("   ✅ PEDIDOS transformados.")


# ==========================================================
# 🚀 Transformar PRODUCTOS desde staging → ERP
# ==========================================================
from modules.etl_excel_staging import to_date_safe, to_str_safe

def transform_productos(supa):
    import os, pandas as pd

    print("🧩 Transformando PRODUCTOS...")

    OUT_DIR = "etl_output"
    os.makedirs(OUT_DIR, exist_ok=True)

    # ---------------------------------------------------------
    # 1️⃣ Cargar staging de producto y referencia
    # ---------------------------------------------------------
    df_prod = pd.DataFrame(supa.table("stg_xls_producto").select("*").execute().data or [])
    df_ref = pd.DataFrame(supa.table("stg_xls_producto_ref").select("*").execute().data or [])
    print(f"   · Productos: {len(df_prod)} filas | Referencias: {len(df_ref)} filas")

    if df_prod.empty:
        print("   ⚠️ No hay productos en staging.")
        return

    # ---------------------------------------------------------
    # 2️⃣ Cargar catálogo de tipos de producto
    # ---------------------------------------------------------
    tipo_map = {}
    tipo_rows = supa.table("producto_tipo").select("producto_tipoid, nombre").execute().data or []
    for r in tipo_rows:
        tipo_map[str(r["nombre"]).strip().upper()] = r["producto_tipoid"]

    # ---------------------------------------------------------
    # 3️⃣ Fusionar producto y referencia
    # ---------------------------------------------------------
    cols_ref = [c for c in df_ref.columns if c not in df_prod.columns or c in ("ean", "referencia", "urlimagen", "urlimagenproveedor")]
    df = df_prod.merge(df_ref[cols_ref], how="left", left_on="id_externo", right_on="id_producto", suffixes=("", "_ref"))

    productos_valido, productos_desc = [], []

    # ---------------------------------------------------------
    # 4️⃣ Procesar cada fila
    # ---------------------------------------------------------
    for _, r in df.iterrows():
        try:
            id_externo = to_str_safe(r.get("id_externo"))
            if not id_externo:
                raise ValueError("Sin id_externo")

            nombre = (to_str_safe(r.get("nombre")) or "Producto sin nombre").strip()[:250]
            titulo = to_str_safe(r.get("titulo")) or None
            descripcion = to_str_safe(r.get("descripcion")) or None

            # URLs e imagen
            url_img = to_str_safe(r.get("urlimagen")) or to_str_safe(r.get("urlimagenproveedor"))
            portada_url = url_img if url_img and len(url_img) > 5 else None

            # Fecha alta
            fecha_alta = to_date_safe(r.get("fecha_alta")) or to_date_safe(r.get("fechaalta")) or None

            # Identificadores varios
            ean = to_str_safe(r.get("ean"))
            referencia = to_str_safe(r.get("referencia"))
            # Prioriza un ISBN real, si no existe usa CODIGOCERTESPEC como identificador alternativo
            isbn = to_str_safe(r.get("isbn")) or to_str_safe(r.get("codigocertespec")) or None

            # Mapeo del tipo
            tipo_raw = str(r.get("producto_tipo_raw") or r.get("idproductotipo") or "").strip()
            tipoid = None
            tipo_texto = "OTRO"

            if tipo_raw in ("1.0", "1", "MANUAL"):
                tipoid = tipo_map.get("MANUAL")
                tipo_texto = "Manual"
            elif tipo_raw in ("2.0", "2", "CUADERNO"):
                tipoid = tipo_map.get("CUADERNO")
                tipo_texto = "Cuaderno"
            elif tipo_raw in ("3.0", "3", "LIBRO"):
                tipoid = tipo_map.get("LIBRO")
                tipo_texto = "Libro"
            else:
                tipoid = tipo_map.get("OTRO")

            rec = {
                "nombre": nombre,
                "titulo": titulo,
                "sinopsis": descripcion,
                "fecha_alta": fecha_alta,
                "producto_tipoid": tipoid,
                "tipo": tipo_texto,
                "ean": ean,
                "isbn": isbn,
                "referencia": referencia,
                "portada_url": portada_url,
                "id_origen": id_externo,
            }

            productos_valido.append(rec)

        except Exception as e:
            productos_desc.append({**r.to_dict(), "motivo": str(e)})

    # ---------------------------------------------------------
    # 5️⃣ Auditoría
    # ---------------------------------------------------------
    pd.DataFrame(productos_valido).to_csv(os.path.join(OUT_DIR, "producto_valido.csv"), index=False)
    if productos_desc:
        pd.DataFrame(productos_desc).to_csv(os.path.join(OUT_DIR, "auditoria_producto.csv"), index=False)
        with open(os.path.join(OUT_DIR, "producto_descartado.txt"), "w", encoding="utf-8") as f:
            for d in productos_desc:
                f.write(f"{d.get('id_externo')} — {d.get('motivo')}\n")

    print(f"   ✅ {len(productos_valido)} válidos, ❌ {len(productos_desc)} descartados")

    # ---------------------------------------------------------
    # 6️⃣ Inserción
    # ---------------------------------------------------------
    if productos_valido:
        print("   ⬆️ Insertando productos en tabla 'producto'...")
        for rec in productos_valido:
            try:
                supa.table("producto").upsert(rec, on_conflict="id_origen").execute()
            except Exception as e:
                print(f"   ⚠️ Error insertando producto {rec.get('nombre')}: {e}")

    print("   ✅ PRODUCTOS transformados.")

# ==========================================================
# 🧾 Transformar LÍNEAS DE PEDIDO (solo mapea por IDPEDIDO)
# ==========================================================
import os, re, json
import pandas as pd
from decimal import Decimal, InvalidOperation
from collections import defaultdict

OUT_DIR = "etl_output"

def normalize_key(v):
    if v is None:
        return ""
    try:
        return str(int(float(str(v).strip())))
    except Exception:
        return str(v).strip()

# ==========================================================
# 🧾 Transformar LÍNEAS DE PEDIDO (definitivo)
# ==========================================================
import json
import os
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import pandas as pd
import re

OUT_DIR = "etl_output"

def normalize_key(v):
    """Convierte 849117.0 → '849117', elimina ceros a la izquierda"""
    if v is None:
        return ""
    s = str(v).strip()
    if s == "":
        return ""
    try:
        f = float(s)
        if f.is_integer():
            s = str(int(f))
        else:
            s = str(f)
    except Exception:
        pass
    s = re.sub(r"\.0+$", "", s)
    s = re.sub(r"^0+(?=\d)", "", s)
    return s
def transform_pedido_lineas(supa):
    print("🧩 Transformando LÍNEAS DE PEDIDO...")

    # imports locales para no depender de la cabecera del módulo
    import os, json
    from decimal import Decimal, InvalidOperation
    from collections import defaultdict
    from datetime import datetime
    import pandas as pd

    OUT_DIR = "etl_output"
    os.makedirs(OUT_DIR, exist_ok=True)

    # -------------------- Helpers --------------------
    def clean_key(val):
        """Normaliza claves: quita .0, comas y espacios -> string"""
        if val is None:
            return ""
        s = str(val).strip()
        if s.endswith(".0"):
            s = s[:-2]
        return s.replace(",", "").replace(" ", "")

    def to_dec(v, default="0"):
        try:
            if v is None or str(v).strip() == "":
                return Decimal(default)
            return Decimal(str(v))
        except InvalidOperation:
            return Decimal(default)

    def safe_json(v):
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return {}

    def safe_to_csv(df_out, filename):
        path = os.path.join(OUT_DIR, filename)
        try:
            df_out.to_csv(path, index=False)
        except PermissionError:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            alt = filename.replace(".csv", f"_{ts}.csv")
            df_out.to_csv(os.path.join(OUT_DIR, alt), index=False)

    # -------------------- Leer staging --------------------
    df = pd.DataFrame(supa.table("stg_xls_pedido_linea").select("*").execute().data or [])
    print(f"   · Leídas {len(df)} filas de stg_xls_pedido_linea")
    if df.empty:
        print("   ⚠️ No hay líneas de pedido en staging.")
        return

    # -------------------- Mapas pedido/producto --------------------
    # pedido.numero (texto) -> pedidoid
    pedidos_map = {}
    for p in supa.table("pedido").select("pedidoid, numero").execute().data or []:
        key = clean_key(p.get("numero"))
        if key:
            pedidos_map[key] = int(p["pedidoid"])

    # referencia / id_origen / ean -> productoid
    productos_map = {}
    for pr in supa.table("producto").select("productoid, referencia, id_origen, ean").execute().data or []:
        pid = int(pr["productoid"])
        for k in (pr.get("referencia"), pr.get("id_origen"), pr.get("ean")):
            ck = clean_key(k)
            if ck:
                productos_map[ck] = pid

    # -------------------- Estado actual pedido_detalle --------------------
    lineas_existentes = defaultdict(set)
    max_linea = defaultdict(int)
    id_origen_existentes = set()

    for row in supa.table("pedido_detalle").select("pedidoid,linea,id_origen").execute().data or []:
        try:
            pid = int(row["pedidoid"])
        except Exception:
            continue
        if row.get("id_origen"):
            id_origen_existentes.add(str(row["id_origen"]).strip())
        ln = row.get("linea")
        if ln is not None:
            try:
                ln = int(float(ln))
                lineas_existentes[pid].add(ln)
                if ln > max_linea[pid]:
                    max_linea[pid] = ln
            except Exception:
                pass

    # -------------------- Transformar filas --------------------
    lineas_valido, lineas_desc = [], []

    for _, r in df.iterrows():
        raw_row = r.to_dict()
        try:
            # --- id_origen (obligatorio y anti-duplicados) ---
            id_origen = str(r.get("id_externo") or r.get("ID") or r.get("id") or r.get("id_linea") or "").strip()
            if not id_origen or id_origen.lower() == "nan":
                raise ValueError("Sin ID de línea origen")
            if id_origen in id_origen_existentes:
                continue  # ya insertada

            j = safe_json(r.get("raw_json"))

            # --- Pedido: SOLO por número (stg → pedido.numero) ---
            pedido_key = clean_key(r.get("id_pedido") or r.get("id_pedido_raw"))
            if not pedido_key:
                pedido_key = clean_key(j.get("IDPEDIDO"))
            pedidoid = pedidos_map.get(pedido_key)
            if not pedidoid:
                raise ValueError(f"Pedido no encontrado ({pedido_key})")

            # --- Producto: referencia / id_origen / EAN ---
            prod_key = clean_key(
                r.get("id_producto_referencia") or r.get("id_ref_raw") or r.get("referencia") or r.get("id_producto_raw")
            )
            if not prod_key:
                prod_key = clean_key(j.get("IDPRODUCTOREFERENCIA") or j.get("REFERENCIA") or j.get("EAN"))
            productoid = productos_map.get(prod_key)
            if not productoid:
                raise ValueError(f"Producto no encontrado ({prod_key})")

            # --- Número de línea ---
            linea_raw = r.get("id_pedido_linea_origen") or r.get("linea") or j.get("IDPEDIDOLINEAORIGEN")
            try:
                linea_num = int(float(linea_raw))
            except Exception:
                linea_num = None

            if linea_num is None or linea_num in lineas_existentes[pedidoid]:
                # Siguiente libre
                linea_num = max_linea[pedidoid] + 1
                while linea_num in lineas_existentes[pedidoid]:
                    linea_num += 1
            lineas_existentes[pedidoid].add(linea_num)
            if linea_num > max_linea[pedidoid]:
                max_linea[pedidoid] = linea_num

            # --- Cantidad / Precio / Descuento / Total ---
            cantidad = to_dec(r.get("cantidad") or j.get("CANTIDAD"), "1")

            # Preferimos precio_unitario explícito, si no PRECIO/PRECIODTO del json
            precio = r.get("precio_unitario")
            if precio in (None, "", "0", 0):
                precio = j.get("PRECIO") or j.get("PRECIODTO")
            precio = to_dec(precio, "0")

            descuento_pct = to_dec(r.get("descuento_pct") or j.get("DTO"), "0")

            subtotal = r.get("subtotal") or j.get("SUBTOTAL")
            if subtotal is not None and str(subtotal).strip() != "":
                total_linea = to_dec(subtotal, "0")
            else:
                total_linea = cantidad * precio * (Decimal("1") - (descuento_pct / Decimal("100")))

            rec = {
                "pedidoid": int(pedidoid),
                "productoid": int(productoid),
                "linea": int(linea_num),
                "cantidad": float(cantidad),
                "precio_unitario": float(precio),
                "descuento_pct": float(descuento_pct),
                "total_linea": float(total_linea),
                "id_origen": id_origen,
                "raw_json": json.dumps(raw_row, ensure_ascii=False),
            }
            lineas_valido.append(rec)

        except Exception as e:
            err = raw_row.copy()
            err["motivo"] = str(e)
            lineas_desc.append(err)

    # -------------------- Auditoría --------------------
    if lineas_valido:
        safe_to_csv(pd.DataFrame(lineas_valido), "pedido_linea_valido.csv")
    if lineas_desc:
        safe_to_csv(pd.DataFrame(lineas_desc), "auditoria_pedido_linea.csv")
        # TXT simple con fallback si está abierto
        try:
            with open(os.path.join(OUT_DIR, "pedido_linea_descartado.txt"), "w", encoding="utf-8") as f:
                for d in lineas_desc:
                    f.write(f"{d.get('id_externo') or d.get('ID') or ''} — {d.get('motivo')}\n")
        except PermissionError:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(os.path.join(OUT_DIR, f"pedido_linea_descartado_{ts}.txt"), "w", encoding="utf-8") as f:
                for d in lineas_desc:
                    f.write(f"{d.get('id_externo') or d.get('ID') or ''} — {d.get('motivo')}\n")

    print(f"   ✅ {len(lineas_valido)} válidas, ❌ {len(lineas_desc)} descartadas")
    # ---------------------------------------------------------
    # 5️⃣ Inserción segura (corrige tipos numéricos)
    # ---------------------------------------------------------
    if lineas_valido:
        print("   ⬆️ Insertando líneas en 'pedido_detalle'...")

        for rec in lineas_valido:
            try:
                # Asegurar tipos exactos
                rec["pedidoid"] = int(rec["pedidoid"])
                rec["productoid"] = int(rec["productoid"])
                rec["linea"] = int(rec["linea"])

                # cantidad debe ser INTEGER en BBDD
                if rec.get("cantidad") is not None:
                    rec["cantidad"] = int(float(rec["cantidad"]))

                # los demás son decimales (NUMERIC)
                for num_key in ["precio_unitario", "descuento_pct", "total_linea"]:
                    if rec.get(num_key) is not None:
                        rec[num_key] = round(float(rec[num_key]), 6)

                # Insertar solo si no existe por id_origen
                exists = (
                    supa.table("pedido_detalle")
                    .select("id_origen")
                    .eq("id_origen", rec["id_origen"])
                    .execute()
                )
                if not exists.data:
                    supa.table("pedido_detalle").insert(rec).execute()

            except Exception as e:
                print(f"   ⚠️ Error insertando línea {rec.get('id_origen')}: {e}")

    print("   ✅ LÍNEAS DE PEDIDO transformadas.")

def main():
    supa = get_client()
    transform_clientes(supa)
    transform_productos(supa)   # ← añade esta línea
    transform_pedidos(supa)
    transform_pedido_lineas(supa)  # la añadiremos después



if __name__ == "__main__":
    main()
