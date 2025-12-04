# modules/dashboard/actuacion_card.py

import streamlit as st
from modules.dashboard.utils import safe_time

def _can_complete(a):
    """
    Una actuación puede completarse si:
    - NO tiene hora_inicio/hora_fin (bloque horario)
    - estado != 'Completada'
    """
    if a.get("estado") == "Completada":
        return False
    if a.get("hora_inicio") or a.get("hora_fin"):
        return False
    return True


def render_actuacion_card(a, cliente_nombre=""):
    """
    Renderiza una tarjeta compacta de actuación en el calendario.
    Devuelve (clicked_view, clicked_complete)
    """
    clicked_view = False
    clicked_complete = False

    desc = a.get("descripcion") or a.get("titulo") or "Actuación CRM"
    canal = a.get("canal") or "-"
    estado = a.get("estado") or "-"
    prioridad = a.get("prioridad") or "-"

    hora_ini = safe_time(a.get("hora_inicio"))
    hora_fin = safe_time(a.get("hora_fin"))

    franja = ""
    if hora_ini and hora_fin:
        franja = f"{hora_ini}–{hora_fin}"
    elif hora_ini:
        franja = f"desde {hora_ini}"

    color = {
        "Pendiente": "#f59e0b",
        "En curso": "#6366f1",
        "Completada": "#10b981"
    }.get(a.get("estado"), "#6b7280")

    st.markdown(
        f"""
        <div style='border-left:5px solid {color}; padding:6px 8px;
                    margin:6px 0; border-radius:6px; background:#f9fafb;'>
            <b>{desc}</b><br>
            <small>{cliente_nombre} · {canal} · {estado} · Prioridad: {prioridad}"""
        +
        (f" · {franja}" if franja else "") +
        "</small></div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Ver / editar", key=f"v_{a['crm_actuacionid']}"):
            clicked_view = True

    if _can_complete(a):
        with col2:
            if st.button("✅ Completar", key=f"c_{a['crm_actuacionid']}"):
                clicked_complete = True

    return clicked_view, clicked_complete
