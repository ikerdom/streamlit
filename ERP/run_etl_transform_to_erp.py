# run_etl_transform_to_erp.py

from supabase import create_client, Client
from modules.etl_transform_to_erp_producto import transformar_productos_desde_staging


from supabase import create_client, Client
from modules.etl_transform_to_erp_producto import transformar_productos_desde_staging
import unicodedata

from supabase import create_client, Client
from modules.etl_transform_to_erp_producto import transformar_productos_desde_staging
import unicodedata

from supabase import create_client, Client
from modules.etl_transform_to_erp_producto import transformar_productos_desde_staging
import unicodedata

import modules.etl_transform_to_erp_producto as etlmod
print(">>> USANDO ARCHIVO:", etlmod.__file__)

# -----------------------------------------------
# NORMALIZAR CLAVE PARA COMPARAR (sin acentos, sin espacios, lowercase)
# -----------------------------------------------
def norm_key(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.strip().lower()


# -----------------------------------------------
# NORMALIZAR NOMBRE PARA GUARDAR EN BBDD (formato único)
# -----------------------------------------------
def normalize_display_name(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.strip()
    return s.title()


# -----------------------------------------------
# EJECUCIÓN PRINCIPAL DEL ETL
# -----------------------------------------------
def run_etl_productos():
    SUPABASE_URL = "https://gqhrbvusvcaytcbnusdx.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxaHJidnVzdmNheXRjYm51c2R4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MzM3MDQsImV4cCI6MjA3NTAwOTcwNH0.y3018JLs9A08sSZKHLXeMsITZ3oc4s2NDhNLxWqM9Ag"


    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ======================================================
    # 1) Transformación desde staging
    # ======================================================
    productos_limpios, auditoria, descartado = transformar_productos_desde_staging(supabase)

    if descartado:
        print(f"⚠ {len(descartado)} filas descartadas. No se cargará ningún producto.")
        return

    if not productos_limpios:
        print("No hay productos válidos que cargar.")
        return

    # ======================================================
    # 2) Sets únicos para catálogos
    # ======================================================
    proveedores_set = set()
    familias_set = set()
    categorias_raiz_set = set()
    categoria_familia_pairs = set()
    tipos_set = set()

    for p in productos_limpios:
        if p["proveedor_nombre"]:
            proveedores_set.add(p["proveedor_nombre"])

        familias_set.add(p["familia"])
        categorias_raiz_set.add(p["categoria_raiz"])
        categoria_familia_pairs.add((p["categoria_raiz"], p["familia"]))

        if p["producto_tipo_nombre"]:
            tipos_set.add((p["producto_tipo_nombre"], p["impuestoid_sugerido"]))

    # ======================================================
    # 3) PROVEEDORES
    # ======================================================
    proveedores_map = {}
    res = supabase.table("producto_proveedor").select("*").execute()
    for row in res.data or []:
        proveedores_map[norm_key(row["razon_social"])] = row["proveedorid"]

    nuevos = []
    nuevos_keys = set()

    for nombre in proveedores_set:
        nk = norm_key(nombre)
        if nk in proveedores_map:
            continue

        canonical = normalize_display_name(nombre)
        nk2 = norm_key(canonical)

        if nk2 in nuevos_keys:
            continue

        nuevos.append({"razon_social": canonical})
        nuevos_keys.add(nk2)

    if nuevos:
        inserted = supabase.table("producto_proveedor").insert(nuevos).execute()
        for row in inserted.data or []:
            proveedores_map[norm_key(row["razon_social"])] = row["proveedorid"]

    # ======================================================
    # 4) FAMILIAS
    # ======================================================
    familias_map = {}
    res = supabase.table("producto_familia").select("*").execute()
    for row in res.data or []:
        canonical = normalize_display_name(row["nombre"])
        familias_map[norm_key(canonical)] = row["familia_productoid"]

    nuevos = []
    nuevos_keys = set()

    for nombre in familias_set:
        nk = norm_key(nombre)
        if nk in familias_map:
            continue

        canonical = normalize_display_name(nombre)
        nk2 = norm_key(canonical)

        if nk2 in nuevos_keys:
            continue

        nuevos.append({"nombre": canonical})
        nuevos_keys.add(nk2)

    if nuevos:
        inserted = supabase.table("producto_familia").insert(nuevos).execute()
        for row in inserted.data or []:
            canonical = normalize_display_name(row["nombre"])
            familias_map[norm_key(canonical)] = row["familia_productoid"]

    # ======================================================
    # 5) CATEGORÍA ÁRBOL
    # ======================================================
    cat_arbol_map = {}
    cat_raiz_map = {}
    cat_fam_map = {}

    res = supabase.table("producto_categoria_arbol").select("*").execute()
    for c in res.data or []:
        cat_arbol_map[c["categoria_arbolid"]] = c
        if c["nivel"] == 1:
            canonical = normalize_display_name(c["nombre"])
            cat_raiz_map[norm_key(canonical)] = c["categoria_arbolid"]

    # --- Nivel 1 ---
    nuevos_cat1 = []
    nuevos_keys = set()

    for raiz in categorias_raiz_set:
        nk = norm_key(raiz)
        if nk in cat_raiz_map:
            continue

        canonical = normalize_display_name(raiz)
        nk2 = norm_key(canonical)

        if nk2 in nuevos_keys:
            continue

        nuevos_cat1.append({"nombre": canonical, "nivel": 1, "padreid": None})
        nuevos_keys.add(nk2)

    if nuevos_cat1:
        inserted = supabase.table("producto_categoria_arbol").insert(nuevos_cat1).execute()
        for c in inserted.data or []:
            canonical = normalize_display_name(c["nombre"])
            cat_raiz_map[norm_key(canonical)] = c["categoria_arbolid"]

    # Recargar categorías
    res = supabase.table("producto_categoria_arbol").select("*").execute()
    for c in res.data or []:
        cat_arbol_map[c["categoria_arbolid"]] = c

    # --- Nivel 2 ---
    for c in res.data or []:
        if c["nivel"] == 2:
            padre = c["padreid"]
            p = cat_arbol_map.get(padre)
            if p:
                raiz_c = normalize_display_name(p["nombre"])
                fam_c = normalize_display_name(c["nombre"])
                cat_fam_map[(norm_key(raiz_c), norm_key(fam_c))] = c["categoria_arbolid"]

    nuevos_cat2 = []
    nuevos_keys = set()

    for raiz, fam in categoria_familia_pairs:
        nk_pair = (norm_key(raiz), norm_key(fam))
        if nk_pair in cat_fam_map:
            continue

        padreid = cat_raiz_map[norm_key(normalize_display_name(raiz))]

        canonical_fam = normalize_display_name(fam)
        nk2 = (norm_key(normalize_display_name(raiz)), norm_key(canonical_fam))

        if nk2 in nuevos_keys:
            continue

        nuevos_cat2.append({
            "nombre": canonical_fam,
            "nivel": 2,
            "padreid": padreid
        })
        nuevos_keys.add(nk2)

    if nuevos_cat2:
        inserted = supabase.table("producto_categoria_arbol").insert(nuevos_cat2).execute()
        for c in inserted.data or []:
            if c["nivel"] == 2:
                padre = c["padreid"]
                p = cat_arbol_map.get(padre)
                if p:
                    raiz_c = normalize_display_name(p["nombre"])
                    fam_c = normalize_display_name(c["nombre"])
                    cat_fam_map[(norm_key(raiz_c), norm_key(fam_c))] = c["categoria_arbolid"]

    # ======================================================
    # 6) TIPOS DE PRODUCTO
    # ======================================================
    tipos_map = {}
    res = supabase.table("producto_tipo").select("*").execute()
    for row in res.data or []:
        canonical = normalize_display_name(row["nombre"])
        tipos_map[norm_key(canonical)] = row["producto_tipoid"]

    nuevos = []
    nuevos_keys = set()

    for nombre, impuestoid in tipos_set:
        nk = norm_key(nombre)
        if nk in tipos_map:
            continue

        canonical = normalize_display_name(nombre)
        nk2 = norm_key(canonical)

        if nk2 in nuevos_keys:
            continue

        nuevos.append({
            "nombre": canonical,
            "impuestoid": impuestoid
        })
        nuevos_keys.add(nk2)

    if nuevos:
        inserted = supabase.table("producto_tipo").insert(nuevos).execute()
        for row in inserted.data or []:
            canonical = normalize_display_name(row["nombre"])
            tipos_map[norm_key(canonical)] = row["producto_tipoid"]

    print("=====================================================")
    print("STAGING LIMPIO (productos_limpios):", len(productos_limpios))
    print("=====================================================")

    # ======================================================
    # 7) Construcción de PRODUCTOS finales
    # ======================================================
    productos_final = []

    for p in productos_limpios:
        raiz = norm_key(p["categoria_raiz"])
        fam = norm_key(p["familia"])
        categoriaid = cat_fam_map.get((raiz, fam))

        if categoriaid is None:
            print("❌ Categoría NO encontrada:", p["categoria_raiz"], "/", p["familia"])
            continue

        proveedorid = None
        if p["proveedor_nombre"]:
            proveedorid = proveedores_map.get(norm_key(p["proveedor_nombre"]))

        familia_productoid = familias_map.get(fam)

        producto_tipoid = None
        if p["producto_tipo_nombre"]:
            producto_tipoid = tipos_map.get(norm_key(p["producto_tipo_nombre"]))

        productos_final.append({
            "nombre": p["nombre"],
            "titulo": p["titulo"],
            "fecha_alta": p["fecha_alta"],
            "ean": p["ean"],
            "isbn": p["isbn"],
            "referencia": p["referencia"],
            "producto_tipoid": producto_tipoid,
            "categoriaid": categoriaid,
            "portada_url": p["portada_url"],
            "fecha_publicacion": p["fecha_publicacion"],
            "paginas_totales": p["paginas_totales"],
            "precio_generico": p["precio_generico"],
            "publico": p["publico"],
            "tipo": p["tipo"],
            "impuestoid": p["impuestoid_sugerido"],
            "proveedorid": proveedorid,
            "familia_productoid": familia_productoid,
            "id_origen": p["id_origen"],
            "cuerpo_certificado": p["cuerpo_certificado"],
            "autores": p["autores"] 
        })

    print("=====================================================")
    print("PRODUCTOS FINALES:", len(productos_final))
    print("=====================================================")

    # ======================================================
    # 8) UPSERT FINAL EN DOS FASES (EAN / ID_ORIGEN)
    # ======================================================
    BATCH = 300
    total = 0

    productos_con_ean = [p for p in productos_final if p["ean"]]
    productos_sin_ean = [p for p in productos_final if not p["ean"]]

    # --- 1) Upsert por EAN (los que sí tienen EAN) ---
    for i in range(0, len(productos_con_ean), BATCH):
        batch = productos_con_ean[i:i+BATCH]
        supabase.table("producto").upsert(
            batch,
            on_conflict="ean"
        ).execute()
        total += len(batch)

    # --- 2) Upsert por id_origen (los que NO tienen EAN) ---
    for i in range(0, len(productos_sin_ean), BATCH):
        batch = productos_sin_ean[i:i+BATCH]
        supabase.table("producto").upsert(
            batch,
            on_conflict="id_origen"
        ).execute()
        total += len(batch)

    print(f"✅ Insertados/actualizados {total} productos en batches de {BATCH}.")

# -----------------------------------------------
if __name__ == "__main__":
    
    run_etl_productos()

