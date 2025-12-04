import re
from supabase import create_client, Client

SUPABASE_URL = "https://gqhrbvusvcaytcbnusdx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxaHJidnVzdmNheXRjYm51c2R4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MzM3MDQsImV4cCI6MjA3NTAwOTcwNH0.y3018JLs9A08sSZKHLXeMsITZ3oc4s2NDhNLxWqM9Ag"


# ======================================================
# 🔗 Supabase
# ======================================================
def get_supa() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ======================================================
# 🧼 Normalizar ciudad para poder comparar
# ======================================================
def norm_city(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().lower()
    reemplazos = [
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        ("ü", "u"),
    ]
    for a, b in reemplazos:
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9ñ ]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s or None


# ======================================================
# 🏃 Proceso principal
# ======================================================
def run():
    supa = get_supa()

    # 1) Cargar TODA la tabla postal_localidad (cp → localidad / provincia / regionid)
    print("📥 Cargando postal_localidad...")
    postal_res = (
        supa.table("postal_localidad")
        .select("postallocid,cp,localidad,provinciaid,regionid,provincia_nombre_raw,region_nombre_raw")
        .limit(50000)
        .execute()
    )
    postal_rows = postal_res.data or []
    print(f"   → {len(postal_rows)} filas cargadas.")

    # Índice por CP (string 5 dígitos) para buscar rápido
    postal_by_cp: dict[str, list[dict]] = {}
    for r in postal_rows:
        cp_val = r.get("cp")
        if cp_val is None:
            continue
        cp_str = str(cp_val).zfill(5)
        postal_by_cp.setdefault(cp_str, []).append(r)

    # 2) Cargar direcciones fiscales de España
    print("📥 Cargando direcciones fiscales...")
    dir_res = (
        supa.table("cliente_direccion")
        .select("*")
        .eq("tipo", "fiscal")
        .eq("pais", "ESPAÑA")
        .limit(20000)
        .execute()
    )
    direcciones = dir_res.data or []
    print(f"   → {len(direcciones)} direcciones fiscales encontradas.")

    total_candidatas = 0
    total_actualizadas = 0
    sin_cp = 0
    sin_match = 0

    # 3) Recorrer direcciones y arreglar SOLO las que tienen regionid o postallocid nulos
    for row in direcciones:
        cliente_direccionid = row["cliente_direccionid"]
        cp_val = row.get("cp")
        regionid = row.get("regionid")
        postallocid = row.get("postallocid")

        # Solo tocamos las que están incompletas
        if regionid is not None and postallocid is not None:
            continue

        if not cp_val:
            sin_cp += 1
            continue

        cp_str = str(cp_val).zfill(5)
        candidates = postal_by_cp.get(cp_str)
        if not candidates:
            sin_match += 1
            continue

        total_candidatas += 1

        ciudad_actual = row.get("ciudad")
        ciudad_norm = norm_city(ciudad_actual)

        # Intentar matchear por ciudad normalizada
        match = None
        if ciudad_norm:
            for cand in candidates:
                if norm_city(cand.get("localidad")) == ciudad_norm:
                    match = cand
                    break

        # Si no hay match exacto, cogemos el primero del CP
        if match is None:
            match = candidates[0]

        # Preparar UPDATE SOLO con las columnas que queremos corregir
        new_postallocid = match.get("postallocid")
        new_regionid = match.get("regionid")
        new_provincia = match.get("provincia_nombre_raw") or row.get("provincia")
        new_ciudad = match.get("localidad") or row.get("ciudad")

        update_fields = {
            "postallocid": int(new_postallocid) if new_postallocid is not None else None,
            "regionid": int(new_regionid) if new_regionid is not None else None,
            "provincia": new_provincia,
            "ciudad": new_ciudad,
        }

        # 4) UPDATE fila a fila (sin upsert, sin tocar clienteid ni nada más)
        supa.table("cliente_direccion").update(update_fields).eq(
            "cliente_direccionid", cliente_direccionid
        ).execute()

        total_actualizadas += 1
        print(
            f"   · Dirección {cliente_direccionid}: "
            f"cp={cp_str}, '{ciudad_actual}' → '{new_ciudad}', "
            f"prov='{row.get('provincia')}' → '{new_provincia}', "
            f"regionid={new_regionid}, postallocid={new_postallocid}"
        )

    print("✅ FIX COMPLETADO")
    print(f"   · Direcciones con cp pero sin match en postal_localidad: {sin_match}")
    print(f"   · Direcciones sin cp: {sin_cp}")
    print(f"   · Direcciones candidatas (con cp y faltando region/postallocid): {total_candidatas}")
    print(f"   · Direcciones actualizadas: {total_actualizadas}")


if __name__ == "__main__":
    run()
