import streamlit as st

from modules.campania import campania_lista
from modules.campania import campania_form
from modules.campania import campania_progreso
from modules.campania import campania_detalle
from modules.campania import campania_informes


def render_campania_router(supabase):
    """
    Router interno de campañas.
    Controla las vistas:
    - lista
    - form
    - progreso
    - detalle
    - informes

    usando:
    - st.session_state["campania_view"]
    - st.session_state["campaniaid"]
    """
    st.session_state.setdefault("campania_view", "lista")
    st.session_state.setdefault("campania_step", 1)
    st.session_state.setdefault("campaniaid", None)

    view = st.session_state["campania_view"]
    campaniaid = st.session_state.get("campaniaid")

    # ===========================
    # LISTADO
    # ===========================
    if view == "lista":
        campania_lista.render(supabase)

    # ===========================
    # FORMULARIO (wizard 1–3)
    # ===========================
    elif view == "form":
        campania_form.render(supabase)

    # ===========================
    # PROGRESO (edición masiva)
    # ===========================
    elif view == "progreso":
        if not campaniaid:
            st.error("No hay campaña seleccionada.")
            if st.button("⬅️ Volver al listado"):
                st.session_state["campania_view"] = "lista"
                st.rerun()
            return
        campania_progreso.render()

    # ===========================
    # DETALLE (análisis por comercial / cliente / timeline)
    # ===========================
    elif view == "detalle":
        if not campaniaid:
            st.error("No hay campaña seleccionada.")
            if st.button("⬅️ Volver al listado"):
                st.session_state["campania_view"] = "lista"
                st.rerun()
            return
        campania_detalle.render(campaniaid)

    # ===========================
    # INFORMES (KPIs y export)
    # ===========================
    elif view == "informes":
        if not campaniaid:
            st.error("No hay campaña seleccionada.")
            if st.button("⬅️ Volver al listado"):
                st.session_state["campania_view"] = "lista"
                st.rerun()
            return

        campania_informes.render(supabase, campaniaid)
