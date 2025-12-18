from datetime import datetime, date, time
import streamlit as st

# =========================================================
# 💬 CRM · Acciones y seguimiento de clientes
# =========================================================

def render_crm_form(supabase, clienteid: int):

    # =========================
    # CABECERA
    # =========================
    st.markdown(
        """
        <div style="
            padding:10px;
            background:#f8fafc;
            border:1px solid #e5e7eb;
            border-radius:10px;
            margin-bottom:10px;">
            <div style="font-size:1.15rem; font-weight:600; color:#111827;">
                💬 Seguimiento CRM
            </div>
            <div style="font-size:0.9rem; color:#6b7280;">
                Acciones comerciales o administrativas asociadas al cliente.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    trabajadorid = st.session_state.get("trabajadorid")
    if not trabajadorid:
        st.warning("⚠️ No hay sesión de trabajador activa.")
        return

    # =====================================================
    # 👥 Cargar trabajadores
    # =====================================================
    try:
        trabajadores = (
            supabase.table("trabajador")
            .select("trabajadorid, nombre, apellidos")
            .order("nombre")
            .execute()
            .data or []
        )
        trabajadores_map = {
            f"{t['nombre']} {t['apellidos']}": t["trabajadorid"] for t in trabajadores
        }
        trabajadores_rev = {v: k for k, v in trabajadores_map.items()}
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar los trabajadores: {e}")
        trabajadores_map, trabajadores_rev = {}, {}

    # =====================================================
    # ➕ NUEVA ACCIÓN
    # =====================================================
    with st.expander("➕ Registrar nueva acción"):
        with st.form(f"crm_new_{clienteid}"):

            c1, c2 = st.columns(2)

            with c1:
                titulo = st.text_input("Título *")
                canal = st.selectbox("Canal", ["Teléfono", "Email", "Reunión", "WhatsApp", "Otro"])
                prioridad = st.selectbox("Prioridad", ["Alta", "Media", "Baja"], index=1)

            with c2:
                fecha_venc = st.date_input("Fecha límite", value=date.today())
                hora = st.time_input("Hora (opcional)", value=time(9, 0))
                descripcion = st.text_area(
                    "Descripción / recordatorio",
                    placeholder="Detalles de la acción…",
                    height=80,
                )

            st.markdown("**Asignar responsable**")

            nombre_logueado = st.session_state.get("user_nombre", "").lower()
            idx_default = 0
            for i, n in enumerate(trabajadores_map.keys()):
                if nombre_logueado and nombre_logueado in n.lower():
                    idx_default = i
                    break

            trab_sel = st.selectbox(
                "Trabajador",
                list(trabajadores_map.keys()) if trabajadores_map else ["—"],
                index=idx_default if trabajadores_map else 0,
            )

            trabajador_asignado = trabajadores_map.get(trab_sel, trabajadorid)

            submitted = st.form_submit_button("Guardar acción", use_container_width=True)

        if submitted:
            if not titulo.strip():
                st.warning("⚠️ El título es obligatorio.")
                return

            payload = {
                "clienteid": clienteid,
                "titulo": titulo.strip(),
                "descripcion": descripcion.strip() or None,
                "canal": canal,
                "estado": "Pendiente",
                "prioridad": prioridad,
                "fecha_vencimiento": fecha_venc.isoformat(),
                "trabajadorid": trabajadorid,
                "trabajador_asignadoid": trabajador_asignado,
            }

            if hora:
                payload["fecha_accion"] = datetime.combine(
                    fecha_venc, hora
                ).replace(microsecond=0).isoformat()

            try:
                supabase.table("crm_actuacion").insert(payload).execute()
                st.toast(f"Acción creada y asignada a {trab_sel}.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar acción: {e}")

    # =====================================================
    # 📋 LISTADO DE ACCIONES
    # =====================================================
    st.markdown("---")
    st.markdown("#### Acciones registradas")

    try:
        acciones = (
            supabase.table("crm_actuacion")
            .select(
                "crm_actuacionid, titulo, estado, canal, fecha_vencimiento, prioridad, trabajador_asignadoid, descripcion"
            )
            .eq("clienteid", clienteid)
            .order("fecha_vencimiento")
            .execute()
            .data or []
        )

        if not acciones:
            st.info("📭 Este cliente no tiene acciones registradas.")
            return

        for a in acciones:
            estado = a.get("estado", "Pendiente")
            prioridad = a.get("prioridad", "Media")
            titulo = a.get("titulo", "—")
            canal = a.get("canal", "—")
            descripcion = a.get("descripcion") or "—"
            fecha_venc = a.get("fecha_vencimiento", "—")

            trabajador_asignado = trabajadores_rev.get(
                a.get("trabajador_asignadoid"), "—"
            )

            color_estado = {
                "Pendiente": "#f59e0b",
                "Completada": "#16a34a",
                "Cancelada": "#6b7280",
            }.get(estado, "#f59e0b")

            color_prioridad = {
                "Alta": "#dc2626",
                "Media": "#f59e0b",
                "Baja": "#22c55e",
            }.get(prioridad, "#6b7280")

            st.markdown(
                f"""
                <div style="
                    border:1px solid #e5e7eb;
                    border-left:5px solid {color_estado};
                    background:#ffffff;
                    border-radius:10px;
                    padding:12px 14px;
                    margin-bottom:10px;">

                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="font-size:1rem;font-weight:600;">
                            {titulo}
                            <span style="color:{color_prioridad};font-size:0.85rem;">
                                ({prioridad})
                            </span>
                        </div>
                        <div style="font-size:0.85rem;font-weight:600;color:{color_estado};">
                            {estado}
                        </div>
                    </div>

                    <div style="margin-top:4px;font-size:0.85rem;color:#374151;">
                        📡 {canal} &nbsp;·&nbsp; 👤 {trabajador_asignado} &nbsp;·&nbsp; ⏰ {fecha_venc}
                    </div>

                    <div style="margin-top:6px;font-size:0.9rem;color:#374151;">
                        {descripcion}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar las acciones: {e}")
