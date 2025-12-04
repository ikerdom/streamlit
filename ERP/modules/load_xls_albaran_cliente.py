import pandas as pd
import json
import re
from supabase import create_client, Client

SUPABASE_URL = "https://gqhrbvusvcaytcbnusdx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxaHJidnVzdmNheXRjYm51c2R4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MzM3MDQsImV4cCI6MjA3NTAwOTcwNH0.y3018JLs9A08sSZKHLXeMsITZ3oc4s2NDhNLxWqM9Ag"

TABLE_NAME = "stg_xls_albaran_cliente"
EXCEL_FILE = "inf1ClientesAlbaranes_ORBE crm.xlsx"  # debe estar en /modules


# ============================================================
# 🔧 Crear cliente Supabase
# ============================================================
def get_supa() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================
# 🧼 Normalizadores
# ============================================================
def normalize_text(t: str) -> str:
    if not t:
        return None
    t = t.lower().strip()

    # quitar nº , num, etc.
    t = t.replace(" nº", " ").replace(" n°", " ").replace(" num", " ")
    t = re.sub(r"[^a-z0-9áéíóúñü ]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t if t else None


def join_address(vp, dom):
    if vp and dom:
        return f"{vp} {dom}".strip()
    return vp or dom or None


# ============================================================
# ☎️ Normalizador de teléfonos (MEJORADO)
# ============================================================
def split_phones(raw: str):
    if not raw:
        return None, None, None

    # Separadores típicos
    parts = re.split(r"[\/,;]| y | o | - |\s{2,}", raw)

    clean = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # quitar paréntesis, espacios internos, guiones
        p = re.sub(r"[^\d]", "", p)
        if len(p) >= 6:  # número real
            clean.append(p)

    clean = list(dict.fromkeys(clean))  # quitar duplicados

    # rellenar
    tel1 = clean[0] if len(clean) >= 1 else None
    tel2 = clean[1] if len(clean) >= 2 else None
    tel3 = clean[2] if len(clean) >= 3 else None

    return tel1, tel2, tel3


# ============================================================
# 📤 Cargar Excel y limpiar
# ============================================================
def load_excel():
    df = pd.read_excel(f"modules/{EXCEL_FILE}", dtype=str)
    df = df.fillna("")

    rename_map = {
        "RAZONSOCIAL": "razonsocial",
        "NOMBRE": "nombre_comercial",
        "CIFDNI": "cifdni",
        "VIAPUBLICA": "viapublica",
        "DOMICILIO": "domicilio",
        "CODIGOPOSTAL": "codigopostal",
        "PROVINCIA": "provincia",
        "MUNICIPIO": "municipio",
        "TELEFONO": "telefono",
        "TELEFONO2": "telefono2",
        "TELEFONO3": "telefono3",
        "FAX": "fax",
        "CODIGOCUENTA": "codigocuenta",
        "CODIGOCUENTAEFECTO": "codigocuentaefecto",
        "CODIGOCUENTAIMPAGADO": "codigocuentaimpagado",
    }

    df.rename(columns=rename_map, inplace=True)
    return df


# ============================================================
# 🚀 Insertar datos en staging
# ============================================================
def upload_to_staging(df):
    supa = get_supa()

    print("🗑️ Borrando staging anterior...")
    supa.table(TABLE_NAME).delete().neq("stg_id", 0).execute()

    rows = []

    for i, row in df.iterrows():
        razon = row.get("razonsocial", "").strip()
        nombre = row.get("nombre_comercial", "").strip()

        full_address = join_address(row.get("viapublica", ""), row.get("domicilio", ""))

        # teléfonos limpios
        tel1, tel2, tel3 = split_phones(row.get("telefono", ""))

        item = {
            "input_row_number": i + 1,
            "razonsocial": razon or None,
            "nombre_comercial": nombre or None,
            "cifdni": row.get("cifdni", "").strip() or None,
            "viapublica": row.get("viapublica", "").strip() or None,
            "domicilio": row.get("domicilio", "").strip() or None,
            "codigopostal": row.get("codigopostal", "").strip() or None,
            "provincia": row.get("provincia", "").strip() or None,
            "municipio": row.get("municipio", "").strip() or None,
            "telefono": tel1,
            "telefono2": tel2,
            "telefono3": tel3,
            "fax": row.get("fax", "").strip() or None,
            "codigocuenta": row.get("codigocuenta", "").strip() or None,
            "codigocuentaefecto": row.get("codigocuentaefecto", "").strip() or None,
            "codigocuentaimpagado": row.get("codigocuentaimpagado", "").strip() or None,
            "raw_direccion": full_address,
            "raw_json": row.to_dict(),       # JSON CRUDO REAL
            "normalized_razon_social": normalize_text(razon),
            "normalized_direccion": normalize_text(full_address),
            "load_status": "pendiente",
            "load_errors": None,
        }

        rows.append(item)

    print(f"⬆️ Subiendo {len(rows)} filas a staging...")

    batch = 100
    for i in range(0, len(rows), batch):
        supa.table(TABLE_NAME).insert(rows[i:i+batch]).execute()

    print("✅ Staging cargado correctamente.")


# ============================================================
# 🏁 RUN
# ============================================================
def run():
    df = load_excel()
    upload_to_staging(df)


if __name__ == "__main__":
    run()
