# modules/etl_transform_to_erp_producto.py

from datetime import datetime
import pandas as pd


# ==========================================================
# Helpers de limpieza / mapping
# ==========================================================
def clean_ean(value):
    if value is None:
        return None
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s or None


def map_publico(value):
    if value is None:
        return None
    v = str(value).strip().lower()
    if v in ("si", "sí", "true", "1"):
        return True
    if v in ("no", "false", "0"):
        return False
    return None


def map_impuesto_nombre_y_id(tipo_producto):
    if not tipo_producto:
        return "IVA General", 3

    t = str(tipo_producto).strip().lower()
    if t == "libro":
        return "IVA Libros", 1
    if t in ("ebook", "e-book", "digital"):
        return "IVA Digital", 2
    return "IVA General", 3

import time
import httpx

# ==========================================================
# LECTOR COMPLETO DE STAGING EN PAGINAS DE 1000 (ROBUSTO Y SIN WARNING)
# ==========================================================
def read_all_staging_rows(supabase, table_name):
    all_rows = []
    batch = 0
    page_size = 1000
    seguir = True

    while seguir:
        start = batch * page_size
        end = start + page_size - 1

        exito = False

        for intento in range(5):  # hasta 5 reintentos
            try:
                res = (
                    supabase
                    .table(table_name)
                    .select("*")
                    .range(start, end)
                    .execute()
                )

                rows = res.data or []
                all_rows.extend(rows)

                # Si devolvió menos que 1000 → último batch
                if len(rows) < page_size:
                    seguir = False

                exito = True
                break  # salir de intentos

            except Exception as e:
                print(f"⚠ Error leyendo batch {batch}, intento {intento+1}: {e}")
                time.sleep(0.8)

        if not exito:
            raise Exception(f"❌ No se pudo leer batch {batch}: errores repetidos.")

        batch += 1

    return all_rows

# ==========================================================
# TRANSFORMACIÓN
# ==========================================================
def transformar_productos_desde_staging(supabase):

    # Leer TODAS las filas del staging
    rows = read_all_staging_rows(supabase, "stg_xls_producto")

    print("=== DEBUG: Filas leídas del staging:", len(rows))

    df = pd.DataFrame(rows)

    productos_limpios = []
    auditoria = []
    descartado = []

    for _, row in df.iterrows():
        try:
            # Campos obligatorios
            nombre = row.get("nombre")
            categoria_raiz = row.get("categoria_raiz")
            familia = row.get("familia")
            id_externo = row.get("id_externo")

            if not nombre or not categoria_raiz or not familia or not id_externo:
                descartado.append({
                    "stg_id": row.get("id"),
                    "id_externo": id_externo,
                    "motivo": "Campos obligatorios faltan"
                })
                continue

            # Limpieza
            ean = clean_ean(row.get("ean"))
            isbn = clean_ean(row.get("isbn"))
            publico = map_publico(row.get("publico"))
            tipo_producto = row.get("tipo_producto")
            impuesto_nombre, impuestoid_sugerido = map_impuesto_nombre_y_id(tipo_producto)

            # --- NUEVOS CAMPOS ---
            cuerpo_certificado = row.get("cuerpo_certificado")
            autores_raw = row.get("autor_nombre")

            # autores_raw = "Antonio; Donato; María" -> lista limpia
            if autores_raw:
                autores = ", ".join(
                    [a.strip() for a in str(autores_raw).split(";") if a.strip()]
                )
            else:
                autores = None

            productos_limpios.append({
                "nombre": nombre,
                "titulo": row.get("titulo"),
                "fecha_alta": row.get("fecha_alta"),
                "ean": ean,
                "isbn": isbn,
                "referencia": id_externo,
                "portada_url": row.get("portada_url"),
                "fecha_publicacion": row.get("fecha_publicacion"),
                "paginas_totales": row.get("total_paginas"),
                "precio_generico": row.get("pvp"),
                "publico": publico,
                "tipo": tipo_producto,
                "id_origen": f"claudia:{id_externo}",

                # Nuevos campos añadidos
                "cuerpo_certificado": cuerpo_certificado,
                "autores": autores,

                # Mapeos internos
                "categoria_raiz": categoria_raiz,
                "familia": familia,
                "proveedor_nombre": row.get("proveedor"),
                "producto_tipo_nombre": tipo_producto,
                "impuesto_nombre": impuesto_nombre,
                "impuestoid_sugerido": impuestoid_sugerido,
            })

        except Exception as e:
            descartado.append({
                "stg_id": row.get("id"),
                "id_externo": row.get("id_externo"),
                "motivo": f"Excepción en transformación: {e}"
            })

    return productos_limpios, auditoria, descartado
