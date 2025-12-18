import os
import sys
from typing import Dict, Any, Optional

# -------------------------------------------------------
# PATHS
# -------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from supa_client import get_client  # noqa

# -------------------------------------------------------
# CONFIG
# -------------------------------------------------------
PAGE_SIZE = 500
BATCH_SIZE = 500

START_OFFSET = 0  # si se corta, cambia esto

T_ALBARAN = "albaran"
T_ALBARAN_NORM = "albaran_norm"
T_CLIENTE = "cliente"

# -------------------------------------------------------
# HELPERS
# -------------------------------------------------------
def to_int(v) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(float(v))
    except Exception:
        return None

def clean_nan(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: (None if v in ("", "null") else v) for k, v in d.items()}

def chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

# -------------------------------------------------------
# CLIENTE (SOLO razon_social)
# -------------------------------------------------------
def get_or_create_cliente(supa, razon_social: Optional[str], cache: Dict[str, int]) -> int:
    razon_social = (razon_social or "").strip() or "CLIENTE EXTERNO"
    key = razon_social.lower()[:255]

    if key in cache:
        return cache[key]

    found = (
        supa.table(T_CLIENTE)
        .select("clienteid")
        .ilike("razon_social", f"%{razon_social[:120]}%")
        .limit(1)
        .execute()
        .data
        or []
    )
    if found:
        cid = int(found[0]["clienteid"])
        cache[key] = cid
        return cid

    resp = (
        supa.table(T_CLIENTE)
        .insert({
            "razon_social": razon_social[:255],
            "observaciones": "CLIENTE EXTERNO (ALBARAN)",
        })
        .execute()
    )

    cid = int(resp.data[0]["clienteid"])
    cache[key] = cid
    return cid

# -------------------------------------------------------
# PRELOAD ALBARANES YA NORMALIZADOS
# -------------------------------------------------------
def preload_albaranes_norm(supa) -> Dict[int, int]:
    rows = (
        supa.table(T_ALBARAN_NORM)
        .select("albaran_norm_id,albaran_id_origen")
        .execute()
        .data
        or []
    )

    return {
        to_int(r["albaran_id_origen"]): to_int(r["albaran_norm_id"])
        for r in rows
        if to_int(r.get("albaran_id_origen")) is not None
    }

# -------------------------------------------------------
# TRANSFORM SIMPLE
# -------------------------------------------------------
def transform_albaranes_norm_simple():
    supa = get_client()
    cliente_cache: Dict[str, int] = {}

    print("🚚 TRANSFORM ALBARAN → ALBARAN_NORM (SOLO CLIENTE)")

    albaran_norm_map = preload_albaranes_norm(supa)
    print(f"🔁 Albaranes ya normalizados: {len(albaran_norm_map)}")

    offset = START_OFFSET
    inserted = 0
    skipped = 0

    while True:
        page = (
            supa.table(T_ALBARAN)
            .select("albaran_id,cliente,numero,serie,fecha_albaran")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
            .data
            or []
        )

        if not page:
            break

        rows = []

        for a in page:
            alb_id = to_int(a.get("albaran_id"))
            if alb_id is None:
                skipped += 1
                continue

            if alb_id in albaran_norm_map:
                continue

            cliente_id = get_or_create_cliente(
                supa,
                a.get("cliente"),
                cliente_cache
            )

            rows.append(clean_nan({
                "albaran_id_origen": alb_id,
                "cliente_id": cliente_id,
                "numero": a.get("numero"),
                "serie": a.get("serie"),
                "fecha_albaran": a.get("fecha_albaran"),
            }))

        for part in chunks(rows, BATCH_SIZE):
            if not part:
                continue
            resp = supa.table(T_ALBARAN_NORM).insert(part).execute()
            for r in resp.data or []:
                albaran_norm_map[to_int(r["albaran_id_origen"])] = to_int(r["albaran_norm_id"])
            inserted += len(part)

        offset += PAGE_SIZE
        print(f"   · leídos={offset} nuevos_insertados={inserted}")

    print("✅ TRANSFORM FINALIZADO")
    print(f"   · nuevos: {inserted}")
    print(f"   · total norm: {len(albaran_norm_map)}")
    print(f"   · sin id: {skipped}")

# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
if __name__ == "__main__":
    transform_albaranes_norm_simple()
