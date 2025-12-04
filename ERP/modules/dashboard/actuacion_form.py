# modules/dashboard/actuacion_form.py

import streamlit as st
from datetime import date
from modules.dashboard.utils import cliente_autocomplete, safe_date


def render_actuacion_form(supabase, act=None, fecha_default=None):
    """
    Formulario profesional de alta/edición de actuación.
    act = dict con datos (modo edición) o None (modo nuevo)
    fecha_default = date para nuevas actuaciones
    """

    st.markdown("---")
    st.markdown(
        """
        <div style="background:#eff6ff;padding:14px 16px;border-radius:12px;
                    border:1px solid #bfdbfe;margin-bottom:12px;">
            <div style="font-size:16px;font-weight:600;color:#1d4ed8;">🧩 Detalle de actuación CRM</div>
            <div style="font-size:12px;color:#4b5563;">Editar o crear una nueva actuación.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    is_edit = act is not None

    with st.form("form_actuacion"):

        col1, col2 = st.columns([2, 1])
        with col1:
            titulo = st.text_input(
                "Título",
                value=act.get("titulo") if is_edit else "",
            )
            descripcion = st.text_area(
                "Descripción",
                value=act.get("descripcion") if is_edit else "",
                height=80,
            )
            resultado = st.text_area(
                "Resultado / Notas",
                value=act.get("resultado") if is_edit else "",
                height=80,
            )

        with col2:
            canal = st.selectbox(
                "Canal",
                ["Teléfono", "Email", "Videollamada", "Visita", "Otro"],
                index=["Teléfono", "Email", "Videollamada", "Visita", "Otro"].index(
                    act["canal"]
                )
                if is_edit and act.get("canal") in [
                    "Teléfono",
                    "Email",
                    "Videollamada",
                    "Visita",
                    "Otro",
                ]
                else 0,
            )

            estado = st.selectbox(
                "Estado",
                ["Pendiente", "En curso", "Completada"],
                index=["Pendiente", "En curso", "Completada"].index(act["estado"])
                if is_edit and act.get("estado") in ["Pendiente", "En curso", "Completada"]
                else 0,
            )

            prioridad = st.selectbox(
                "Prioridad",
                ["Baja", "Media", "Alta"],
                index=["Baja", "Media", "Alta"].index(act["prioridad"])
                if is_edit and act.get("prioridad") in ["Baja", "Media", "Alta"]
                else 1,
            )

        col3, col4 = st.columns(2)
        with col3:
            fecha_venc = st.date_input(
                "Fecha vencimiento",
                value=date.fromisoformat(str(act["fecha_vencimiento"])[:10])
                if is_edit
                else fecha_default or date.today(),
            )

        with col4:
            fecha_accion = st.date_input(
                "Fecha acción",
                value=date.fromisoformat(str(act["fecha_accion"])[:10])
                if is_edit
                else fecha_default or date.today(),
            )

        # Cliente autocomplete
        clienteid = cliente_autocomplete(
            supabase,
            "actform",
            clienteid_inicial=act.get("clienteid") if is_edit else None,
        )

        colb1, colb2 = st.columns(2)
        guardar = colb1.form_submit_button("💾 Guardar")
        cancelar = colb2.form_submit_button("❌ Cerrar")

        if cancelar:
            st.session_state["crm_actuacion_detalle_id"] = None
            st.session_state["crm_new_act_fecha"] = None
            st.rerun()

        if guardar:
            data = {
                "titulo": titulo or None,
                "descripcion": descripcion or None,
                "resultado": resultado or None,
                "canal": canal,
                "estado": estado,
                "prioridad": prioridad,
                "fecha_vencimiento": fecha_venc.isoformat(),
                "fecha_accion": fecha_accion.isoformat(),
                "clienteid": clienteid,
            }

            try:
                if is_edit:
                    supabase.table("crm_actuacion").update(data).eq(
                        "crm_actuacionid", act["crm_actuacionid"]
                    ).execute()
                else:
                    supabase.table("crm_actuacion").insert(data).execute()

                st.success("Guardado correctamente.")
                st.session_state["crm_actuacion_detalle_id"] = None
                st.session_state["crm_new_act_fecha"] = None
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
