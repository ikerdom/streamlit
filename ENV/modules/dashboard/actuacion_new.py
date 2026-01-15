# modules/dashboard/actuacion_new.py

import streamlit as st
from datetime import datetime

from modules.dashboard.utils import cliente_autocomplete
from modules.crm_api import crear as api_crear


# ======================================================
# ➕ FORMULARIO NUEVA ACTUACIÓN (DÍA CONCRETO)
# ======================================================
def render_nueva_actuacion_form(supabase, fecha, day_index):
    with st.form(f"form_new_act_{day_index}"):

        descripcion = st.text_input("Descripción")
        canal = st.selectbox(
            "Canal",
            ["Teléfono", "Email", "Videollamada", "Visita", "Otro"],
        )
        estado = st.selectbox(
            "Estado",
            ["Pendiente", "En curso", "Completada"],
        )
        prioridad = st.selectbox(
            "Prioridad",
            ["Baja", "Media", "Alta"],
            index=1,
        )

        clienteid = cliente_autocomplete(
            supabase,
            key_prefix=f"new_act_cli_{day_index}",
            label="Cliente (opcional)",
        )

        crear = st.form_submit_button("💾 Crear acción")

        if crear:
            if not descripcion:
                st.error("La descripción es obligatoria.")
                return

            try:
                payload = {
                    "titulo": descripcion,
                    "descripcion": descripcion,
                    "canal": canal,
                    "estado": estado,
                    "fecha_vencimiento": fecha.date().isoformat(),
                    "fecha_accion": fecha.date().isoformat(),
                    "clienteid": clienteid,
                    "trabajadorid": st.session_state.get("trabajadorid"),
                    "prioridad": prioridad,
                }
                if supabase:
                    supabase.table("crm_actuacion").insert(payload).execute()
                else:
                    payload["fecha_accion"] = f"{fecha.date().isoformat()}T00:00:00"
                    api_crear({k: v for k, v in payload.items() if k != "descripcion"})

                st.success("✅ Acción creada correctamente.")
                st.session_state["crm_open_day"] = day_index
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error creando la acción: {e}")
