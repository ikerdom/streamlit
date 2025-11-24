# modules/etl_catalogo_productos_staging.py
import os
import math
import pandas as pd
from datetime import datetime
from modules.supa_client import get_client
from modules.etl_excel_staging import (
    to_date_safe, to_str_safe, to_num_safe, safe_json, insert_rows
)

EXCEL_PATH = "catalogo_productos (2).xlsx"
SHEET_NAME = "Productos"
OUT_DIR = "etl_output"
os.makedirs(OUT_DIR, exist_ok=True)

# -------------------------------------------------------------------
# Config: lista blanca de columnas por si el staging aún no tiene todo
# (Si ya añadiste todas las columnas con ALTER TABLE, déjalo igual)
# -------------------------------------------------------------------
ALLOWED_STG_PRODUCTO = {
    # base originales
    "id_externo", "nombre", "titulo", "descripcion",
    "producto_tipo_raw", "fecha_alta", "estado_raw",
    "raw_json", "isbn", "precio_venta", "familia",
    # ampliaciones solicitadas (si las añadiste)
    "categoria_raiz", "proveedor", "autor_nombre", "autor_apellidos",
    "portada_url", "codigo_certificado", "codigo_modulo_unidad",
    "horas_formacion", "fecha_baja_producto", "fecha_baja_referencia",
    "fecha_publicacion", "total_paginas", "publico", "catalogado",
    "produccion", "distribucion", "ean"
}

ALLOWED_STG_PRODUCTO_REF = {
    # base
    "id_externo", "id_producto", "ean", "referencia", "nombre",
    "nombre_ref", "precio_venta", "url_imagen", "fecha_alta",
    "fecha_baja", "principal", "raw_json",
    # si mantienes estos del modelo previo:
    "id_producto_origen", "stock_minimo", "fecha_fin_stock", "validado",
}


# --------------------------
# Helpers de limpieza/parseo
# --------------------------
def clean_json_compliant(obj):
    """Reemplaza NaN/Inf/-Inf por None dentro de dict/list (recursivo)."""
    if isinstance(obj, dict):
        return {k: clean_json_compliant(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_json_compliant(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj

def parse_price(value):
    """
    Convierte '  8,50' → 8.50, '39.50' → 39.50, valores raros → None.
    """
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    # Cambia coma decimal a punto, elimina espacios
    s = s.replace(" ", "").replace("\u00A0", "")
    # Quita separadores de miles típicos
    # Heurística: si hay coma y punto, asumimos coma=mil, punto=decimal, etc. pero aquí
    # el dataset usa coma como decimal en general.
    s = s.replace(".", "").replace(",", ".")
    try:
        f = float(s)
        if math.isfinite(f):
            return f
    except Exception:
        return None
    return None

def parse_bool_si_no(value):
    """'SI'/'NO' (cualquier case/espacios) → True/False/None"""
    if value is None:
        return None
    s = str(value).strip().upper()
    if s == "SI":
        return True
    if s == "NO":
        return False
    return None

def filter_allowed(rec: dict, allowed: set[str]) -> dict:
    """Deja solo las claves permitidas para evitar errores de columnas inexistentes."""
    return {k: v for k, v in rec.items() if k in allowed}


def load_catalogo_productos_to_staging():
    print(f"📥 Cargando '{EXCEL_PATH}' hoja '{SHEET_NAME}' ...")

    # leer todo el Excel (sin límites)
    xls = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")
    df = pd.read_excel(xls, sheet_name=SHEET_NAME, dtype=object, engine="openpyxl")
    print(f"   · Filas leídas: {len(df)}")
    print(f"   · Columnas: {list(df.columns)}")

    # eliminar filas completamente vacías
    df = df.dropna(how="all")
    print(f"   · Filas tras limpieza: {len(df)}")

    supa = get_client()

    # ================================
    # 1) Productos -> stg_xls_producto
    # ================================
    productos = []
    for idx, r in df.iterrows():
        base_id = (
            to_str_safe(r.get("CODIGO_MODULO_UNIDAD"))
            or to_str_safe(r.get("CODIGO_CERTIFICADO"))
            or to_str_safe(r.get("EAN"))
            or to_str_safe(r.get("ISBN"))
            or f"NOID"
        )

        # Aseguramos unicidad absoluta
        id_externo = f"{base_id}_{idx}"


        # Texto / títulos
        titulo_automatico = to_str_safe(r.get("TITULO_AUTOMATICO"))
        cuerpo_certificado = to_str_safe(r.get("CUERPO_CERTIFICADO"))
        nombre = titulo_automatico or cuerpo_certificado or f"Producto_{idx}"
        titulo = cuerpo_certificado  # guardamos también el cuerpo como título contextual

        # Tipos, fechas y numéricos
        producto_tipo_raw = to_str_safe(r.get("TIPO_PRODUCTO"))
        fecha_alta            = to_date_safe(r.get("FECHA_ALTA"))
        fecha_baja_producto   = to_date_safe(r.get("FECHA_BAJA_PRODUCTO"))
        fecha_baja_referencia = to_date_safe(r.get("FECHA_BAJA_REFERENCIA"))
        fecha_publicacion     = to_date_safe(r.get("FECHA_PUBLICACION"))

        # ISBN/EAN tal como vienen (sin formatear a int para no perder ceros)
        isbn = to_str_safe(r.get("ISBN"))
        ean  = to_str_safe(r.get("EAN"))

        # PVP → precio_venta (coma decimal → punto; quita espacios y miles)
        pvp_raw = r.get("PVP")
        precio_venta = None
        if pvp_raw is not None:
            s = str(pvp_raw).strip().replace("\u00A0", "").replace(" ", "")
            if s != "":
                s = s.replace(".", "").replace(",", ".")
                try:
                    precio_venta = float(s)
                except Exception:
                    precio_venta = to_num_safe(pvp_raw)

        # horas_formacion / total_paginas numéricos (forzamos enteros si son válidos)
        horas_formacion = None
        try:
            hf = to_num_safe(r.get("HORAS_FORMACION"))
            if hf is not None and str(hf).strip() != "":
                horas_formacion = int(float(hf))
        except Exception:
            horas_formacion = None

        total_paginas = None
        try:
            tp = to_num_safe(r.get("TOTAL_PAGINAS"))
            if tp is not None and str(tp).strip() != "":
                total_paginas = int(float(tp))
        except Exception:
            total_paginas = None


        # Booleans SI/NO
        def si_no(v):
            if v is None: return None
            t = str(v).strip().upper()
            if t == "SI": return True
            if t == "NO": return False
            return None

        publico     = si_no(r.get("PUBLICO"))
        catalogado  = si_no(r.get("CATALOGADO"))
        produccion  = si_no(r.get("PRODUCCION"))
        distribucion= si_no(r.get("DISTRIBUCION"))

        # Resto de campos de contexto
        categoria_raiz = to_str_safe(r.get("CATEGORIA_RAIZ"))
        familia        = to_str_safe(r.get("FAMILIA"))
        proveedor      = to_str_safe(r.get("PROVEEDOR"))
        autor_nombre   = to_str_safe(r.get("AUTOR_NOMBRE"))
        autor_apellidos= to_str_safe(r.get("AUTOR_APELLIDOS"))
        portada_url    = to_str_safe(r.get("PORTADA_URL"))
        codigo_certificado    = to_str_safe(r.get("CODIGO_CERTIFICADO"))
        codigo_modulo_unidad  = to_str_safe(r.get("CODIGO_MODULO_UNIDAD"))

        # Construimos el registro
        rec = {
            "id_externo": id_externo,
            "nombre": nombre,
            "titulo": titulo,

            "categoria_raiz": categoria_raiz,
            "familia": familia,
            "cuerpo_certificado": cuerpo_certificado,
            "proveedor": proveedor,
            "autor_nombre": autor_nombre,
            "autor_apellidos": autor_apellidos,
            "portada_url": portada_url,
            "codigo_certificado": codigo_certificado,
            "codigo_modulo_unidad": codigo_modulo_unidad,
            "titulo_automatico": titulo_automatico,

            "isbn": isbn,
            "ean": ean,
            "horas_formacion": horas_formacion,
            "tipo_producto": producto_tipo_raw,
            "producto_tipo_raw": producto_tipo_raw,

            "fecha_alta": fecha_alta,
            "fecha_baja_producto": fecha_baja_producto,
            "fecha_baja_referencia": fecha_baja_referencia,
            "fecha_publicacion": fecha_publicacion,

            "pvp": precio_venta,
            "precio_venta": precio_venta,
            "total_paginas": total_paginas,

            "publico": publico,
            "catalogado": catalogado,
            "produccion": produccion,
            "distribucion": distribucion,

            "raw_json": safe_json(r),
        }

        # 🚨 NUEVO: limpia NaN/Inf/None inválidos ANTES de añadir
        rec = clean_json_compliant(rec)
        productos.append(rec)

    # deduplicación por id_externo
    if productos:
        dfp = pd.DataFrame(productos)
        if "id_externo" in dfp.columns:
            dfp = dfp.drop_duplicates(subset=["id_externo"])
        productos = dfp.to_dict("records")

    print(f"   ✅ {len(productos)} productos listos para staging")

    # limpieza previa y carga en lotes
    supa.table("stg_xls_producto").delete().neq("id", 0).execute()
    for i in range(0, len(productos), 1000):
        batch = productos[i:i+1000]
        # 🚨 NUEVO: limpiar cada lote antes del insert
        batch = [clean_json_compliant(b) for b in batch]
        insert_rows(supa, "stg_xls_producto", batch, chunk=1000)
        print(f"   · Insertado lote productos {i//1000+1}")

    # =======================================
    # 2) Referencias -> stg_xls_producto_ref
    # =======================================
    refs = []
    for idx, r in df.iterrows():
        # === BLOQUE NUEVO (REFERENCIAS → stg_xls_producto_ref) ===
        id_externo_ref = (
            to_str_safe(r.get("CODIGO_MODULO_UNIDAD"))
            or to_str_safe(r.get("CODIGO_CERTIFICADO"))
            or to_str_safe(r.get("EAN"))
            or to_str_safe(r.get("ISBN"))
        )
        if not id_externo_ref:
            id_externo_ref = f"NOREF_{idx}"

        rec = {
            "id_externo": id_externo_ref,
            "id_producto": id_externo_ref,                        # 1:1 con producto
            "ean": to_str_safe(r.get("EAN")),
            "referencia": to_str_safe(r.get("ISBN")),             # ISBN como referencia (acordado)
            "nombre": to_str_safe(r.get("TITULO_AUTOMATICO"))
                      or to_str_safe(r.get("CUERPO_CERTIFICADO"))
                      or f"Ref_{idx}",
            "nombre_ref": to_str_safe(r.get("FAMILIA")),
            "precio_venta": parse_price(r.get("PVP")),
            "url_imagen": to_str_safe(r.get("PORTADA_URL")),
            "fecha_alta": to_date_safe(r.get("FECHA_ALTA")),
            "fecha_baja": to_date_safe(r.get("FECHA_BAJA_PRODUCTO")),
            "principal": "1",
            "raw_json": safe_json(r),
        }
        refs.append(rec)

    # deduplicación por id_externo de referencia
    if refs:
        dfr = pd.DataFrame(refs)
        if "id_externo" in dfr.columns:
            dfr = dfr.drop_duplicates(subset=["id_externo"])
        refs = dfr.to_dict("records")

    print(f"   ✅ {len(refs)} referencias listadas para staging")

    supa.table("stg_xls_producto_ref").delete().neq("id", 0).execute()
    for i in range(0, len(refs), 1000):
        batch = refs[i:i+1000]
        batch = [clean_json_compliant(rec) for rec in batch]
        insert_rows(supa, "stg_xls_producto_ref", batch, chunk=1000)
        print(f"   · Insertado lote referencias {i//1000+1}")

    print("🎯 Carga de catálogo completada en staging.")


if __name__ == "__main__":
    load_catalogo_productos_to_staging()
