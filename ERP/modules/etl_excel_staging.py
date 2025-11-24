# modules/etl_excel_staging.py
import os
import pandas as pd
import re
import unicodedata
from datetime import datetime, date
from numbers import Number
from modules.supa_client import get_client

EXCEL_PATH = os.getenv("EXCEL_PATH", "catalogo_productos (2).xlsx")

# =====================================================
# 🔧 HELPERS
# =====================================================

def norm(s: str) -> str:
    """Normaliza texto: sin tildes, mayúsculas; convierte no [A-Z0-9_] en '_' y condensa."""
    if s is None:
        return ""
    s = str(s)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = s.strip().upper()
    s = re.sub(r"[^A-Z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")

def to_date_safe(val):
    """Convierte a 'YYYY-MM-DD' o None."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    try:
        parsed = pd.to_datetime(val, errors="coerce", dayfirst=False)
        if pd.isna(parsed):
            return None
        return parsed.date().isoformat()
    except Exception:
        return None

def to_num_safe(val):
    """Convierte a float o None (sin NaN/Inf)."""
    if val is None:
        return None
    try:
        f = float(val)
        if pd.isna(f) or f == float("inf") or f == float("-inf"):
            return None
        return f
    except Exception:
        return None

def to_str_safe(val):
    """Convierte a str o None; fechas a ISO; números manteniendo formato simple."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return to_date_safe(val)
    if isinstance(val, Number):
        # Evitar "nan", "inf" en cadenas
        f = to_num_safe(val)
        return None if f is None else str(f)
    s = str(val).strip()
    return s if s != "" else None

def safe_json_like(v):
    """Devuelve un valor JSON-compatible (None, bool, float, int, str, dict, list)."""
    # None
    if v is None:
        return None
    # pandas NA / NaN / ±Inf
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    if isinstance(v, float) and (v == float("inf") or v == float("-inf")):
        return None
    # fechas
    if isinstance(v, (datetime, date)):
        return to_date_safe(v)
    # números
    if isinstance(v, Number):
        f = to_num_safe(v)
        return f
    # strings
    s = str(v)
    return s

def safe_json(row_like) -> dict:
    """Limpia una Serie/dict para que sea JSON válido (sin NaN/Inf y con fechas a ISO)."""
    clean = {}
    # row_like puede ser pd.Series (preferimos .items())
    items = row_like.items() if hasattr(row_like, "items") else {}
    for k, v in items:
        try:
            clean[str(k)] = safe_json_like(v)
        except Exception:
            clean[str(k)] = None
    return clean

def insert_rows(supa, table: str, rows: list[dict], chunk=500):
    """Upsert por lotes con manejo de errores."""
    if not rows:
        print(f"   · {table}: no hay filas que insertar")
        return
    for i in range(0, len(rows), chunk):
        batch = rows[i:i+chunk]
        resp = supa.table(table).upsert(batch).execute()
        # La lib de supabase no lanza excepción si PostgREST responde 4xx, pero resp.error puede existir
        if hasattr(resp, "error") and resp.error:
            raise RuntimeError(f"Error upsert {table} (lote {i}-{i+len(batch)}): {resp.error}")
    print(f"✅ Insertadas/Upsert {len(rows)} filas en {table}")

def table_exists(supa, table: str) -> bool:
    """Intenta un select 0 filas; si falla con error PGRST, asumimos que no existe."""
    try:
        supa.table(table).select("id").limit(0).execute()
        return True
    except Exception as e:
        msg = str(e).lower()
        if "relation" in msg and "does not exist" in msg:
            return False
        if "not found" in msg or "pgrst" in msg:
            return False
        # Algunos clientes envuelven el error; intentamos heurística
        return False

def resolve_sheet_name(xls: pd.ExcelFile, wanted_list: list[str]) -> str:
    """Busca hoja por coincidencia parcial, tolerante a mayúsculas y paréntesis."""
    lower_map = {s.lower(): s for s in xls.sheet_names}
    for w in wanted_list:
        if w.lower() in lower_map:
            return lower_map[w.lower()]
    for s in xls.sheet_names:
        for w in wanted_list:
            if w.lower() in s.lower():
                return s
    raise ValueError(f"No se encontró ninguna hoja entre {wanted_list}. Hojas disponibles: {xls.sheet_names}")

def read_sheet(xls: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    """Lee hoja Excel probando headers (0–5) hasta encontrar cabeceras 'no-unnamed'."""
    best_df = None
    for header_row in range(0, 6):
        df = pd.read_excel(xls, sheet_name=sheet_name, dtype=object, header=header_row, engine="openpyxl")
        # preservar nombres originales pero añade columna normalizada para mapeo
        df.columns = [norm(c) for c in df.columns]
        df = df.dropna(how="all")
        unnamed_count = sum(str(c).startswith("UNNAMED") for c in df.columns)
        if unnamed_count < len(df.columns) / 2:
            best_df = df
            print(f"   ✅ Cabecera detectada en fila {header_row} para hoja '{sheet_name}'")
            break
    if best_df is None:
        best_df = df
        print(f"   ⚠️ No se detectó cabecera clara, usando header=0 por defecto en '{sheet_name}'")

    print(f"   · {sheet_name}: shape={best_df.shape}")
    print(f"   · columnas detectadas: {list(best_df.columns)[:12]}{' ...' if len(best_df.columns)>12 else ''}")
    return best_df

def print_create_ddl(nombre_tabla: str, ddl: str):
    print(f"\n⚠️ La tabla '{nombre_tabla}' no existe. Crea esta tabla en Supabase y vuelve a ejecutar:\n{ddl}\n")

# =====================================================
# 🚀 ETL PRINCIPAL
# =====================================================

def load_excel_to_staging():
    print("📥 Cargando Excel → STAGING ...")
    print(f"📄 Usando Excel: {EXCEL_PATH}")
    xls = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")
    supa = get_client()

    SHEETS_WANTED = {
        "clientes": ["CL_TERCERO", "CLIENTES", "CL_TERCERO (CLIENTES) - CL_TERC"],
        "productos": ["CL_PRODUCTO", "CL_PRODUCTO - CL_PRODUCTO"],
        "pedidos":   ["CL_PEDIDO", "CL_PEDIDO (PEDIDOS POR CLIENTES"],
        # Parte 2: "producto_ref": ["CL_PRODUCTOREFERENCIA"], "pedido_linea": ["CL_PEDIDOLINEA"]
    }

    # ----------------------------
    # CLIENTES -> stg_xls_cliente
    # ----------------------------
    try:
        table = "stg_xls_cliente"
        if not table_exists(supa, table):
            ddl = """CREATE TABLE public.stg_xls_cliente (
  id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  id_externo text,
  razon_social text,
  cif text,
  nombre_comercial text,
  fecha_alta date,
  fecha_baja date,
  canal_analitica text,
  raw_json jsonb,
  inserted_at timestamp without time zone DEFAULT now()
);"""
            print_create_ddl(table, ddl)
        else:
            sheet_cli = resolve_sheet_name(xls, SHEETS_WANTED["clientes"])
            dfc = read_sheet(xls, sheet_cli)

            map_cli = {
                "ID": "id_externo",
                "RAZONSOCIAL": "razon_social",
                "CIF": "cif",
                "SG_NOMBRECOMERCIAL": "nombre_comercial",
                "RCI_FECHAALTA": "fecha_alta",
                "RCI_FECHABAJA": "fecha_baja",
                "CANALANALITICA": "canal_analitica",
            }
            map_cli_norm = {norm(k): v for k, v in map_cli.items()}
            present_cli = [c for c in dfc.columns if c in map_cli_norm]

            data_cli = []
            for _, r in dfc.iterrows():
                rec = {}
                raw = safe_json(r)  # <- JSON limpio
                for src in present_cli:
                    dst = map_cli_norm[src]
                    val = r.get(src, None)
                    if dst in ("fecha_alta", "fecha_baja"):
                        rec[dst] = to_date_safe(val)
                    else:
                        rec[dst] = to_str_safe(val)
                # fallback id_externo si falta
                if not rec.get("id_externo"):
                    id_fallback = r.get(norm("ID"))
                    rec["id_externo"] = to_str_safe(id_fallback)
                rec["raw_json"] = raw
                if rec.get("id_externo"):
                    data_cli.append(rec)

            insert_rows(supa, table, data_cli)
    except Exception as e:
        print(f"❌ Error clientes: {e}")

    # ----------------------------
    # PRODUCTOS -> stg_xls_producto
    # ----------------------------
    try:
        table = "stg_xls_producto"
        if not table_exists(supa, table):
            ddl = """CREATE TABLE public.stg_xls_producto (
  id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  id_externo text,
  nombre text,
  titulo text,
  descripcion text,
  producto_tipo_raw text,
  fecha_alta date,
  estado_raw text,
  raw_json jsonb,
  inserted_at timestamp without time zone DEFAULT now()
);"""
            print_create_ddl(table, ddl)
        else:
            sheet_pro = resolve_sheet_name(xls, SHEETS_WANTED["productos"])
            dfp = read_sheet(xls, sheet_pro)

            map_pro = {
                "ID": "id_externo",
                "NOMBRE": "nombre",
                "TITULO": "titulo",
                "DESCRIPCION": "descripcion",
                "IDPRODUCTOTIPO": "producto_tipo_raw",
                "FECHAALTA": "fecha_alta",
                "IDPRODUCTOESTADO": "estado_raw",
            }
            map_pro_norm = {norm(k): v for k, v in map_pro.items()}
            present_pro = [c for c in dfp.columns if c in map_pro_norm]

            data_pro = []
            for _, r in dfp.iterrows():
                rec = {}
                raw = safe_json(r)
                for src in present_pro:
                    dst = map_pro_norm[src]
                    val = r.get(src, None)
                    if dst == "fecha_alta":
                        rec[dst] = to_date_safe(val)
                    else:
                        rec[dst] = to_str_safe(val)
                if not rec.get("id_externo"):
                    id_fallback = r.get(norm("ID"))
                    rec["id_externo"] = to_str_safe(id_fallback)

                # ⚠️ Si no hay nombre, dejamos algo reconocible: "Producto {id_externo}"
                if not rec.get("nombre"):
                    rec["nombre"] = f"Producto {rec['id_externo']}" if rec.get("id_externo") else "Producto_sin_nombre"

                rec["raw_json"] = raw
                if rec.get("id_externo"):
                    data_pro.append(rec)

            insert_rows(supa, table, data_pro)
    except Exception as e:
        print(f"❌ Error productos: {e}")

    # ----------------------------
    # PEDIDOS -> stg_xls_pedido
    # ----------------------------
    try:
        table = "stg_xls_pedido"
        if not table_exists(supa, table):
            ddl = """CREATE TABLE public.stg_xls_pedido (
  id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  id_externo text,
  numero_raw text,
  id_tercero_raw text,
  fecha_pedido date,
  estado_raw text,
  forma_pago_raw text,
  total_base numeric,
  total_impuestos numeric,
  total numeric,
  observaciones text,
  raw_json jsonb,
  inserted_at timestamp without time zone DEFAULT now()
);"""
            print_create_ddl(table, ddl)
        else:
            sheet_ped = resolve_sheet_name(xls, SHEETS_WANTED["pedidos"])
            dfpe = read_sheet(xls, sheet_ped)

            map_ped = {
                "ID": "id_externo",
                "IDNUMERO": "numero_raw",
                "IDTERCERO": "id_tercero_raw",
                "FECHAPEDIDO": "fecha_pedido",
                "IDPEDIDOESTADO": "estado_raw",
                "IDFORMADEPAGO": "forma_pago_raw",
                "TOTALBASEIMPONIBLE": "total_base",
                "TOTALIMPUESTOS": "total_impuestos",
                "TOTAL": "total",
                "OBSERVACIONES": "observaciones",
            }
            map_ped_norm = {norm(k): v for k, v in map_ped.items()}
            present_ped = [c for c in dfpe.columns if c in map_ped_norm]

            data_ped = []
            for _, r in dfpe.iterrows():
                rec = {}
                raw = safe_json(r)
                for src in present_ped:
                    dst = map_ped_norm[src]
                    val = r.get(src, None)
                    if dst in ("fecha_pedido",):
                        rec[dst] = to_date_safe(val)
                    elif dst in ("total_base", "total_impuestos", "total"):
                        rec[dst] = to_num_safe(val)
                    else:
                        rec[dst] = to_str_safe(val)
                if not rec.get("id_externo"):
                    id_fallback = r.get(norm("ID"))
                    rec["id_externo"] = to_str_safe(id_fallback)
                rec["raw_json"] = raw
                if rec.get("id_externo"):
                    data_ped.append(rec)

            insert_rows(supa, table, data_ped)
    except Exception as e:
        print(f"❌ Error pedidos: {e}")
    # ----------------------------
    # PRODUCTO REFERENCIA -> stg_xls_producto_ref  (si existe)
    # ----------------------------
    try:
        table = "stg_xls_producto_ref"
        if not table_exists(supa, table):
            ddl = """CREATE TABLE public.stg_xls_producto_ref (
  id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  id_externo text,
  id_producto text,
  ean text,
  referencia text,
  principal text,
  url_imagen text,
  nombre text,
  fecha_alta date,
  fecha_baja date,
  raw_json jsonb,
  inserted_at timestamp without time zone DEFAULT now()
);"""
            print_create_ddl(table, ddl)
        else:
            sheet_pref = resolve_sheet_name(xls, ["CL_PRODUCTOREFERENCIA", "CL_PRODUCTOREFERENCIA (DETALLES"])
            dfr = read_sheet(xls, sheet_pref)

            map_pref = {
                "ID": "id_externo",
                "IDPRODUCTO": "id_producto",
                "EAN": "ean",
                "REFERENCIA": "referencia",
                "PRINCIPAL": "principal",
                "URLIMAGEN": "url_imagen",
                "NOMBRE": "nombre",
                "FECHAALTA": "fecha_alta",
                "FECHABAJA": "fecha_baja",
            }
            map_pref_norm = {norm(k): v for k, v in map_pref.items()}
            present_pref = [c for c in dfr.columns if c in map_pref_norm]

            data_pref = []
            for _, r in dfr.iterrows():
                rec = {}
                raw = safe_json(r)
                for src in present_pref:
                    dst = map_pref_norm[src]
                    val = r.get(src, None)
                    if dst in ("fecha_alta", "fecha_baja"):
                        rec[dst] = to_date_safe(val)
                    else:
                        rec[dst] = to_str_safe(val)
                if not rec.get("id_externo"):
                    id_fallback = r.get(norm("ID"))
                    rec["id_externo"] = to_str_safe(id_fallback)

                # EAN/REFERENCIA importantes: normalizamos espacios
                if rec.get("ean"):
                    rec["ean"] = rec["ean"].replace(" ", "")
                if rec.get("referencia"):
                    rec["referencia"] = rec["referencia"].strip()

                # Nombre “rescatable”
                if not rec.get("nombre"):
                    # Si viene vacío, intenta construir algo
                    base = rec.get("referencia") or rec.get("ean") or rec.get("id_externo")
                    rec["nombre"] = f"Ref {base}" if base else "ProductoRef_sin_nombre"

                rec["raw_json"] = raw
                if rec.get("id_externo"):
                    data_pref.append(rec)

            insert_rows(supa, table, data_pref)
    except Exception as e:
        print(f"❌ Error producto referencia: {e}")

    # ----------------------------
    # PEDIDO LÍNEA -> stg_xls_pedido_linea  (si existe)
    # ----------------------------
    try:
        table = "stg_xls_pedido_linea"
        if not table_exists(supa, table):
            ddl = """CREATE TABLE public.stg_xls_pedido_linea (
  id integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  id_externo text,
  id_pedido text,
  id_pedido_estado text,
  id_pedido_linea_origen text,
  id_producto_referencia text,
  ean text,
  referencia text,
  nombre text,
  cantidad numeric,
  precio_unit numeric,
  dto numeric,
  iva_pct numeric,
  subtotal numeric,
  total_linea numeric,
  fecha_limite date,
  fecha_completado date,
  fecha_anulado date,
  raw_json jsonb,
  inserted_at timestamp without time zone DEFAULT now()
);"""
            print_create_ddl(table, ddl)
        else:
            sheet_pl = resolve_sheet_name(xls, ["CL_PEDIDOLINEA", "CL_PEDIDOLINEA (PRODUCTOS POR P"])
            dfl = read_sheet(xls, sheet_pl)

            map_pl = {
                "ID": "id_externo",
                "IDPEDIDO": "id_pedido",
                "IDPEDIDOESTADO": "id_pedido_estado",
                "IDPEDIDOLINEAORIGEN": "id_pedido_linea_origen",
                "IDPRODUCTOREFERENCIA": "id_producto_referencia",
                "EAN": "ean",
                "REFERENCIA": "referencia",
                "NOMBRE": "nombre",
                "CANTIDAD": "cantidad",
                "PRECIOUNITARIO": "precio_unit",
                "DESCUENTO": "dto",
                "IVA": "iva_pct",
                "SUBTOTAL": "subtotal",
                "TOTALLINEA": "total_linea",
                "FECHALIMITE": "fecha_limite",
                "FECHACOMPLETADO": "fecha_completado",
                "FECHAANULADO": "fecha_anulado",
            }
            map_pl_norm = {norm(k): v for k, v in map_pl.items()}
            present_pl = [c for c in dfl.columns if c in map_pl_norm]

            data_pl = []
            for _, r in dfl.iterrows():
                rec = {}
                raw = safe_json(r)
                for src in present_pl:
                    dst = map_pl_norm[src]
                    val = r.get(src, None)
                    if dst in ("fecha_limite", "fecha_completado", "fecha_anulado"):
                        rec[dst] = to_date_safe(val)
                    elif dst in ("cantidad", "precio_unit", "dto", "iva_pct", "subtotal", "total_linea"):
                        rec[dst] = to_num_safe(val)
                    else:
                        rec[dst] = to_str_safe(val)

                if not rec.get("id_externo"):
                    id_fallback = r.get(norm("ID"))
                    rec["id_externo"] = to_str_safe(id_fallback)

                # Limpiezas útiles
                if rec.get("ean"):
                    rec["ean"] = rec["ean"].replace(" ", "")
                if rec.get("referencia"):
                    rec["referencia"] = rec["referencia"].strip()

                # Nombre de línea si falta
                if not rec.get("nombre"):
                    base = rec.get("referencia") or rec.get("ean") or rec.get("id_producto_referencia")
                    rec["nombre"] = f"Línea {base}" if base else "Linea_sin_nombre"

                rec["raw_json"] = raw
                if rec.get("id_externo"):
                    data_pl.append(rec)

            insert_rows(supa, table, data_pl)
    except Exception as e:
        print(f"❌ Error pedido línea: {e}")
