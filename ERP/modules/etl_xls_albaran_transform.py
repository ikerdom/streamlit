import json
import re
from typing import Dict, Any, Optional, Tuple

from supabase import create_client, Client

# ============================================================
# 🔐 CONFIG SUPABASE (mismas credenciales que el loader)
# ============================================================
SUPABASE_URL = "https://gqhrbvusvcaytcbnusdx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxaHJidnVzdmNheXRjYm51c2R4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MzM3MDQsImV4cCI6MjA3NTAwOTcwNH0.y3018JLs9A08sSZKHLXeMsITZ3oc4s2NDhNLxWqM9Ag"

TABLE_STG = "stg_xls_albaran_cliente"

DEFAULT_ESTADOID = 1       # cliente_estadoid "Activo"
DEFAULT_FORMAPAGOID = 1    # forma_pago por defecto (si existe)
DEFAULT_TIPO_CLIENTE = "cliente"
DEFAULT_ESTADO_PRESUPUESTO = "pendiente"


# ============================================================
# 🔧 Cliente Supabase
# ============================================================
def get_supa() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ============================================================
# 🧼 Normalizadores / helpers
# ============================================================
def normalize_basic(text: Optional[str]) -> Optional[str]:
    """Minúsculas, sin símbolos raros, espacios normalizados."""
    if not text:
        return None
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9áéíóúñü ]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t if t else None


def tidy_name(text: Optional[str]) -> Optional[str]:
    """Capitalizar tipo nombre propio: 'madrid' -> 'Madrid'."""
    if not text:
        return None
    text = text.strip()
    return text.title() if text else None


def normalize_prov_key(text: Optional[str]) -> Optional[str]:
    """Clave de comparación para provincia (tolerante a mayúsculas/acentos)."""
    return normalize_basic(text)


def extract_main_phone(raw: Optional[str]) -> Optional[str]:
    """
    Extrae un teléfono principal de cadenas como:
    '944 794 520 / 944795595' -> '944 794 520'
    '(96) 541 21 31' -> '(96) 541 21 31'
    """
    if not raw:
        return None
    txt = raw.strip()
    # Cortar por separadores típicos
    parts = re.split(r"[\/,;]| y ", txt)
    main = parts[0].strip()
    return main or None


def build_direccion(vp: Optional[str], dom: Optional[str]) -> Optional[str]:
    """
    Construye la dirección a partir de viapublica + domicilio,
    evitando duplicar texto si son iguales.
    """
    vp = (vp or "").strip()
    dom = (dom or "").strip()

    norm_vp = normalize_basic(vp)
    norm_dom = normalize_basic(dom)

    if vp and (not dom or norm_vp == norm_dom):
        return vp
    if dom and not vp:
        return dom
    if vp and dom:
        return f"{vp} {dom}"
    return None


# ============================================================
# 📚 Cache de provincias (nombre + regionid)
# ============================================================
def load_provincia_map(supa: Client) -> Dict[str, Dict[str, Any]]:
    """
    Devuelve un dict:
      key = provincia normalizada (normalize_prov_key)
      value = {"nombre": nombre_oficial, "provinciaid": ..., "regionid": ...}
    """
    res = supa.table("provincia").select(
        "provinciaid,nombre,regionid"
    ).execute()
    data = res.data or []

    mapping: Dict[str, Dict[str, Any]] = {}
    for row in data:
        key = normalize_prov_key(row.get("nombre"))
        if key:
            mapping[key] = {
                "nombre": row.get("nombre"),
                "provinciaid": row.get("provinciaid"),
                "regionid": row.get("regionid"),
            }
    return mapping


def resolve_provincia_info(
    prov_raw: Optional[str],
    provincia_map: Dict[str, Dict[str, Any]],
) -> Tuple[Optional[str], Optional[int]]:
    """
    A partir del texto de provincia del Excel, devuelve:
      (nombre_oficial, regionid)
    o (None, None) si no se reconoce.
    """
    if not prov_raw:
        return None, None
    key = normalize_prov_key(prov_raw)
    if not key:
        return None, None
    info = provincia_map.get(key)
    if not info:
        return None, None
    return info["nombre"], info["regionid"]


# ============================================================
# 🔎 Resolución de clientes
# ============================================================
def find_cliente_by_identificador(
    supa: Client, identificador: str
) -> Optional[int]:
    res = (
        supa.table("cliente")
        .select("clienteid")
        .eq("identificador", identificador)
        .limit(1)
        .execute()
    )
    data = res.data or []
    return data[0]["clienteid"] if data else None


def find_cliente_by_razon_norm(
    supa: Client, razon_norm: str
) -> Optional[int]:
    res = (
        supa.table("cliente")
        .select("clienteid")
        .eq("razon_social_normalizada", razon_norm)
        .limit(1)
        .execute()
    )
    data = res.data or []
    return data[0]["clienteid"] if data else None


def ensure_cliente(
    supa: Client, stg_row: Dict[str, Any]
) -> Tuple[int, bool, str]:
    """
    Garantiza que exista un cliente para la fila del staging.

    Orden:
      1) Buscar por CIF/NIF -> cliente.identificador
      2) Buscar por razon_social_normalizada
      3) Crear nuevo cliente

    Devuelve:
      (clienteid, creado_nuevo (bool), modo_resolucion)
    """
    cif = (stg_row.get("cifdni") or "").strip() or None
    razon = (stg_row.get("razonsocial") or "").strip() or None
    razon_norm = stg_row.get("normalized_razon_social") or normalize_basic(razon)

    # 1) Por identificador = CIF/NIF
    if cif:
        existing_id = find_cliente_by_identificador(supa, cif)
        if existing_id:
            return existing_id, False, "identificador"

    # 2) Por razón social normalizada
    if razon_norm:
        existing_id = find_cliente_by_razon_norm(supa, razon_norm)
        if existing_id:
            return existing_id, False, "razon_social_normalizada"

    # 3) Crear nuevo cliente
    if not razon:
        raise ValueError("No hay razon_social en staging para crear cliente")

    identificador = cif or f"CLOUDIA_ALB_{stg_row['stg_id']}"

    payload = {
        "estadoid": DEFAULT_ESTADOID,
        "razon_social": razon,
        "grupoid": None,
        "categoriaid": None,
        "cuenta_comision": 0,
        "observaciones": None,
        "formapagoid": DEFAULT_FORMAPAGOID,
        "identificador": identificador,
        "trabajadorid": None,
        "perfil_completo": False,
        "tipo_cliente": DEFAULT_TIPO_CLIENTE,
        "estado_presupuesto": DEFAULT_ESTADO_PRESUPUESTO,
        "tarifaid": None,
        "razon_social_normalizada": razon_norm,
    }

    res = supa.table("cliente").insert(payload).execute()
    data = res.data or []
    if not data:
        raise RuntimeError("No se pudo crear cliente")
    clienteid = data[0]["clienteid"]
    return clienteid, True, "creado"


# ============================================================
# 🏠 Direcciones de cliente (solo fiscal desde este Excel)
# ============================================================
def get_cliente_direcciones(
    supa: Client, clienteid: int
) -> Dict[str, Any]:
    """Devuelve direcciones del cliente, indexadas por tipo."""
    res = (
        supa.table("cliente_direccion")
        .select("cliente_direccionid,tipo,direccion,cp,ciudad,provincia,regionid,telefono")
        .eq("clienteid", clienteid)
        .execute()
    )
    data = res.data or []
    # Agrupamos por tipo (puede haber varias de envío)
    por_tipo = {}
    for row in data:
        tipo = row.get("tipo") or "desconocido"
        por_tipo.setdefault(tipo, []).append(row)
    return por_tipo


def find_fiscal_similar(
    direcciones_por_tipo: Dict[str, Any],
    direccion_norm: Optional[str],
    cp: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Busca una dirección fiscal similar por dirección normalizada y/o CP.
    """
    fiscales = direcciones_por_tipo.get("fiscal") or []
    for d in fiscales:
        dir_norm_exist = normalize_basic(d.get("direccion"))
        if direccion_norm and dir_norm_exist and dir_norm_exist == direccion_norm:
            return d
        if cp and d.get("cp") == cp:
            return d
    return None


def upsert_direccion_fiscal(
    supa: Client,
    clienteid: int,
    stg_row: Dict[str, Any],
    provincia_map: Dict[str, Dict[str, Any]],
) -> Tuple[Optional[int], bool, bool]:
    """
    Crea o actualiza la dirección FISCAL del cliente usando el staging.

    Devuelve:
      (cliente_direccionid, creada_nueva, actualizada)
    """
    direcciones_por_tipo = get_cliente_direcciones(supa, clienteid)

    vp = stg_row.get("viapublica")
    dom = stg_row.get("domicilio")
    direccion = build_direccion(vp, dom)
    direccion_norm = normalize_basic(direccion)

    cp = (stg_row.get("codigopostal") or "").strip() or None
    ciudad = tidy_name(stg_row.get("municipio"))
    prov_raw = stg_row.get("provincia")
    provincia_oficial, regionid = resolve_provincia_info(prov_raw, provincia_map)
    provincia = provincia_oficial or tidy_name(prov_raw)

    telefono_main = extract_main_phone(stg_row.get("telefono"))

    # ¿Ya hay alguna fiscal?
    fiscal_existente = find_fiscal_similar(direcciones_por_tipo, direccion_norm, cp)

    # Si hay fiscal existente -> solo rellenamos huecos
    if fiscal_existente:
        cliente_direccionid = fiscal_existente["cliente_direccionid"]
        update_payload: Dict[str, Any] = {}

        if not fiscal_existente.get("cp") and cp:
            update_payload["cp"] = cp
        if not fiscal_existente.get("ciudad") and ciudad:
            update_payload["ciudad"] = ciudad
        if (not fiscal_existente.get("provincia")) and provincia:
            update_payload["provincia"] = provincia
        if (not fiscal_existente.get("regionid")) and regionid:
            update_payload["regionid"] = regionid
        if (not fiscal_existente.get("telefono")) and telefono_main:
            update_payload["telefono"] = telefono_main
        if (not fiscal_existente.get("direccion")) and direccion:
            update_payload["direccion"] = direccion

        if update_payload:
            supa.table("cliente_direccion").update(update_payload).eq(
                "cliente_direccionid", cliente_direccionid
            ).execute()
            return cliente_direccionid, False, True

        return cliente_direccionid, False, False

    # Si no hay fiscal, pero sí otras direcciones:
    fiscales = direcciones_por_tipo.get("fiscal") or []
    if fiscales:
        # Ya hay fiscal pero no coincide -> por ahora NO creamos otra
        # (regla: solo una fiscal por cliente desde este Excel)
        return fiscales[0]["cliente_direccionid"], False, False

    # No hay fiscal -> crear
    nombre_comercial = (
        (stg_row.get("nombre_comercial") or stg_row.get("razonsocial") or "").strip()
        or None
    )

    payload = {
        "clienteid": clienteid,
        "tipo": "fiscal",
        "nombre_comercial": nombre_comercial,
        "cif": (stg_row.get("cifdni") or "").strip() or None,
        "direccion": direccion,
        "pais": "ESPAÑA",
        "cp": cp,
        "ciudad": ciudad,
        "provincia": provincia,
        "telefono": telefono_main,
        "fax": (stg_row.get("fax") or "").strip() or None,
        "documentacion_impresa": "valorado",
        "regionid": regionid,
        # postallocid lo resolverán los triggers por cp+ciudad
    }

    res = supa.table("cliente_direccion").insert(payload).execute()
    data = res.data or []
    if not data:
        raise RuntimeError("No se pudo crear cliente_direccion (fiscal)")
    return data[0]["cliente_direccionid"], True, False


# ============================================================
# 💶 cliente_cuenta
# ============================================================
def upsert_cliente_cuenta(supa: Client, clienteid: int, stg_row: Dict[str, Any]) -> Tuple[Optional[int], bool]:
    """
    Crea o actualiza cliente_cuenta para el cliente.
    Si ya existe, solo rellena campos vacíos.
    """
    res = (
        supa.table("cliente_cuenta")
        .select("cliente_cuentaid,cuenta_contable,cuenta_efecto,cuenta_impagado")
        .eq("clienteid", clienteid)
        .limit(1)
        .execute()
    )
    data = res.data or []

    cuenta = (stg_row.get("codigocuenta") or "").strip() or None
    cuenta_efecto = (stg_row.get("codigocuentaefecto") or "").strip() or None
    cuenta_impagado = (stg_row.get("codigocuentaimpagado") or "").strip() or None

    if data:
        row = data[0]
        cliente_cuentaid = row["cliente_cuentaid"]
        update_payload: Dict[str, Any] = {}
        if not row.get("cuenta_contable") and cuenta:
            update_payload["cuenta_contable"] = cuenta
        if not row.get("cuenta_efecto") and cuenta_efecto:
            update_payload["cuenta_efecto"] = cuenta_efecto
        if not row.get("cuenta_impagado") and cuenta_impagado:
            update_payload["cuenta_impagado"] = cuenta_impagado

        if update_payload:
            supa.table("cliente_cuenta").update(update_payload).eq(
                "cliente_cuentaid", cliente_cuentaid
            ).execute()
            return cliente_cuentaid, False
        return cliente_cuentaid, False

    # Crear nueva
    payload = {
        "clienteid": clienteid,
        "cuenta_contable": cuenta,
        "cuenta_efecto": cuenta_efecto,
        "cuenta_impagado": cuenta_impagado,
    }
    res = supa.table("cliente_cuenta").insert(payload).execute()
    data = res.data or []
    if not data:
        raise RuntimeError("No se pudo crear cliente_cuenta")
    return data[0]["cliente_cuentaid"], True


# ============================================================
# 👤 cliente_contacto (principal)
# ============================================================
def ensure_contacto_principal(
    supa: Client, clienteid: int, stg_row: Dict[str, Any]
) -> Tuple[Optional[int], bool]:
    """
    Asegura que haya un contacto principal para el cliente.
    Si ya existe, no crea otro.
    """
    res = (
        supa.table("cliente_contacto")
        .select("cliente_contactoid")
        .eq("clienteid", clienteid)
        .eq("es_principal", True)
        .limit(1)
        .execute()
    )
    data = res.data or []
    if data:
        return data[0]["cliente_contactoid"], False

    nombre = (
        (stg_row.get("nombre_comercial") or stg_row.get("razonsocial") or "").strip()
        or "Contacto principal"
    )
    telefono = extract_main_phone(stg_row.get("telefono"))

    payload = {
        "clienteid": clienteid,
        "nombre": nombre,
        "telefono": telefono,
        "email": None,
        "rol": None,
        "cargo": None,
        "direccion": None,
        "ciudad": None,
        "provincia": None,
        "pais": None,
        "observaciones": None,
        "es_principal": True,
    }
    res = supa.table("cliente_contacto").insert(payload).execute()
    data = res.data or []
    if not data:
        raise RuntimeError("No se pudo crear cliente_contacto principal")
    return data[0]["cliente_contactoid"], True


# ============================================================
# 🔁 Proceso principal
# ============================================================
def process_staging_rows():
    supa = get_supa()
    provincia_map = load_provincia_map(supa)

    # Solo filas pendientes o con error
    res = (
        supa.table(TABLE_STG)
        .select("*")
        .in_("load_status", ["pendiente", "error"])
        .order("stg_id", desc=False)
        .execute()
    )
    rows = res.data or []
    total = len(rows)
    print(f"🔄 Filas en staging a procesar: {total}")

    stats = {
        "clientes_creados": 0,
        "clientes_existentes_ident": 0,
        "clientes_existentes_razon": 0,
        "direcciones_creadas": 0,
        "direcciones_actualizadas": 0,
        "cuentas_creadas": 0,
        "cuentas_actualizadas": 0,
        "contactos_creados": 0,
        "ok": 0,
        "errores": 0,
    }

    for stg in rows:
        stg_id = stg["stg_id"]
        input_row = stg.get("input_row_number")
        log_prefix = f"Fila STG {stg_id} (#{input_row})"

        try:
            # 1) Cliente
            clienteid, creado_cliente, modo = ensure_cliente(supa, stg)
            if creado_cliente:
                stats["clientes_creados"] += 1
            elif modo == "identificador":
                stats["clientes_existentes_ident"] += 1
            elif modo == "razon_social_normalizada":
                stats["clientes_existentes_razon"] += 1

            # 2) Dirección fiscal (create/update, sin borrar nada)
            dir_id, creada_dir, actualizada_dir = upsert_direccion_fiscal(
                supa, clienteid, stg, provincia_map
            )
            if creada_dir:
                stats["direcciones_creadas"] += 1
            if actualizada_dir:
                stats["direcciones_actualizadas"] += 1

            # 3) cliente_cuenta
            cuenta_id, cuenta_creada = upsert_cliente_cuenta(supa, clienteid, stg)
            if cuenta_creada:
                stats["cuentas_creadas"] += 1
            else:
                stats["cuentas_actualizadas"] += 1

            # 4) contacto principal
            contacto_id, contacto_creado = ensure_contacto_principal(
                supa, clienteid, stg
            )
            if contacto_creado:
                stats["contactos_creados"] += 1

            # 5) Marcar staging como OK
            supa.table(TABLE_STG).update(
                {
                    "load_status": "ok",
                    "load_errors": None,
                }
            ).eq("stg_id", stg_id).execute()

            stats["ok"] += 1

            print(
                f"{log_prefix} · clienteid={clienteid} ({modo}) · "
                f"dir_fiscal_id={dir_id} "
                f"{'[creada]' if creada_dir else '[existente]'} "
                f"{'[actualizada]' if actualizada_dir else ''} · "
                f"cliente_cuenta_id={cuenta_id} · contacto_id={contacto_id}"
            )

        except Exception as e:
            msg = f"{log_prefix} ❌ ERROR: {e}"
            print(msg)

            # Guardar error en staging
            supa.table(TABLE_STG).update(
                {
                    "load_status": "error",
                    "load_errors": str(e)[:4000],
                }
            ).eq("stg_id", stg_id).execute()

            stats["errores"] += 1

    print("\n✅ RESUMEN:")
    for k, v in stats.items():
        print(f"  - {k}: {v}")


# ============================================================
# 🏁 MAIN
# ============================================================
if __name__ == "__main__":
    process_staging_rows()
