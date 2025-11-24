import streamlit as st
from modules.supa_client import supabase


# ---------------------------------------------------------
# CAMPANIA (cabecera)
# ---------------------------------------------------------

def fetch_campanias():
    """Devuelve todas las campañas con metadatos básicos."""
    resp = supabase.table("campania").select("*").order("campaniaid", desc=True).execute()
    return resp.data or []


def fetch_campania(campaniaid: int):
    """Devuelve una campaña concreta."""
    resp = supabase.table("campania").select("*").eq("campaniaid", campaniaid).single().execute()
    return resp.data


def insert_campania(payload: dict):
    """Inserta una nueva campaña."""
    resp = supabase.table("campania").insert(payload).execute()
    return resp.data


def update_campania(campaniaid: int, payload: dict):
    """Actualiza una campaña existente."""
    resp = (
        supabase.table("campania")
        .update(payload)
        .eq("campaniaid", campaniaid)
        .execute()
    )
    return resp.data


# ---------------------------------------------------------
# SEGMENTACIÓN (clientes asignados a campaña)
# ---------------------------------------------------------

def fetch_campania_clientes(campaniaid: int):
    resp = (
        supabase.table("campania_cliente")
        .select("*, cliente(*)")
        .eq("campaniaid", campaniaid)
        .execute()
    )
    return resp.data or []


def add_cliente_to_campania(campaniaid: int, clienteid: int):
    """Añade un cliente manualmente a la campaña."""
    payload = {"campaniaid": campaniaid, "clienteid": clienteid}
    resp = supabase.table("campania_cliente").insert(payload).execute()
    return resp.data


def remove_cliente_from_campania(campania_clienteid: int):
    """Elimina cliente de la campaña (si aún no hay tareas generadas)."""
    resp = (
        supabase.table("campania_cliente")
        .delete()
        .eq("campania_clienteid", campania_clienteid)
        .execute()
    )
    return resp.data


# ---------------------------------------------------------
# ACCIONES (tareas generadas en CRM)
# ---------------------------------------------------------

def fetch_campania_acciones(campaniaid: int):
    """Devuelve las tareas generadas por la campaña."""
    resp = (
        supabase.table("campania_actuacion")
        .select("*, crm_actuacion(*)")
        .eq("campaniaid", campaniaid)
        .execute()
    )
    return resp.data or []


def link_accion_to_campania(campaniaid: int, actuacionid: int):
    """Registra la relación entre campaña y una acción CRM existente."""
    payload = {"campaniaid": campaniaid, "actuacionid": actuacionid}
    resp = supabase.table("campania_actuacion").insert(payload).execute()
    return resp.data
def bulk_update_acciones_estado(client, accion_ids: list[int], nuevo_estado: str):
    data, error = client.table("crm_actuacion") \
        .update({"estado": nuevo_estado}) \
        .in_("crm_actuacionid", accion_ids) \
        .execute()

    return error is None


def bulk_update_acciones_comercial(client, accion_ids: list[int], trabajadorid: int):
    data, error = client.table("crm_actuacion") \
        .update({"trabajador_asignadoid": trabajadorid}) \
        .in_("crm_actuacionid", accion_ids) \
        .execute()

    return error is None


def bulk_update_acciones_fecha(client, accion_ids: list[int], nueva_fecha: str):
    data, error = client.table("crm_actuacion") \
        .update({"fecha_accion": nueva_fecha}) \
        .in_("crm_actuacionid", accion_ids) \
        .execute()

    return error is None


def bulk_update_acciones_resultado(client, accion_ids: list[int], resultado: str):
    data, error = client.table("crm_actuacion") \
        .update({"resultado": resultado}) \
        .in_("crm_actuacionid", accion_ids) \
        .execute()

    return error is None
def get_campania_acciones(client, campaniaid: int):
    data, error = client.rpc("get_campania_acciones", {
        "p_campaniaid": campaniaid
    }).execute()
    return data or []
def get_campania_detalle(client, campaniaid: int):
    data, error = client.rpc("get_campania_detalle", {
        "p_campaniaid": campaniaid
    }).execute()
    return data or []
def update_campania_estado(client, campaniaid: int, nuevo_estado: str):
    data, error = client.table("campania") \
        .update({"estado": nuevo_estado}) \
        .eq("campaniaid", campaniaid) \
        .execute()
    return error is None


def campania_tiene_actuaciones(client, campaniaid: int):
    data, error = client.table("campania_actuacion") \
        .select("actuacionid") \
        .eq("campaniaid", campaniaid) \
        .limit(1) \
        .execute()
    return len(data or []) > 0
def distribuir_clientes(clientes, comerciales):
    asignacion = {t: [] for t in comerciales}
    idx = 0

    for c in clientes:
        trabajador = comerciales[idx % len(comerciales)]
        asignacion[trabajador].append(c)
        idx += 1

    return asignacion
def crear_actuaciones_campania(supa, campaniaid, clientes, comerciales, tipo_accion):
    asign = distribuir_clientes(clientes, comerciales)
    actuaciones_creadas = 0

    for trabajadorid, lista_cli in asign.items():
        for clienteid in lista_cli:
            payload = {
                "trabajadorid": trabajadorid,
                "clienteid": clienteid,
                "accion_tipoid": tipo_accion,
                "estado": "Pendiente",
                "titulo": "Acción campaña",
                "descripcion": f"Acción asignada por campaña {campaniaid}",
                "campaniaid": campaniaid
            }

            supa.table("crm_actuacion").insert(payload).execute()
            actuaciones_creadas += 1

    return actuaciones_creadas
def badge_estado(estado):
    colores = {
        "borrador": "gray",
        "activa": "green",
        "pausada": "orange",
        "finalizada": "blue",
        "cancelada": "red"
    }
    color = colores.get(estado, "gray")

    return f"<span style='padding:4px 8px; border-radius:6px; background:{color}; color:white;'>{estado}</span>"
iconos = {
    "borrador": "📝",
    "activa": "🚀",
    "pausada": "⏸️",
    "finalizada": "🏁",
    "cancelada": "❌"
}

def icono_estado(est):
    return iconos.get(est, "❔")
def actuaciones_existentes(supa, campaniaid):
    data = supa.table("crm_actuacion").select("crm_actuacionid").eq("campaniaid", campaniaid).execute()
    if data and data.data:
        return True
    return False
