# =========================================================
# 💬 CRM — Acciones y seguimiento de clientes (versión pro)
# =========================================================
from datetime import datetime, date, time
import streamlit as st

def render_crm_form(supabase, clienteid: int):
    """Gestión de acciones y seguimiento CRM asociadas a un cliente."""
    st.markdown("### 💬 Seguimiento CRM")
    st.caption("Crea, asigna y consulta las actuaciones comerciales o administrativas asociadas al cliente.")

    trabajadorid = st.session_state.get("trabajadorid")
    if not trabajadorid:
        st.warning("⚠️ No hay sesión de trabajador activa.")
        return

    # =====================================================
    # 📥 Cargar catálogo de trabajadores
    # =====================================================
    try:
        trabajadores = (
            supabase.table("trabajador")
            .select("trabajadorid, nombre, apellidos")
            .order("nombre")
            .execute()
            .data or []
        )
        trabajadores_map = {f"{t['nombre']} {t['apellidos']}": t["trabajadorid"] for t in trabajadores}
        trabajadores_rev = {v: k for k, v in trabajadores_map.items()}
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar los trabajadores: {e}")
        trabajadores_map, trabajadores_rev = {}, {}

    # =====================================================
    # ➕ Añadir nueva acción CRM
    # =====================================================
    with st.expander("➕ Registrar nueva acción", expanded=False):
        with st.form(f"form_accion_cli_{clienteid}"):
            c1, c2 = st.columns(2)
            with c1:
                titulo = st.text_input("📝 Título de la acción *", key=f"titulo_cli_{clienteid}")
                canal = st.selectbox("📡 Canal", ["Teléfono", "Email", "Reunión", "WhatsApp", "Otro"], key=f"canal_cli_{clienteid}")
                prioridad = st.selectbox("🔥 Prioridad", ["Alta", "Media", "Baja"], index=1, key=f"prio_cli_{clienteid}")
            with c2:
                fecha_venc = st.date_input("📅 Fecha límite", value=date.today(), key=f"fecha_cli_{clienteid}")
                hora = st.time_input("⏰ Hora (opcional)", value=time(9, 0), key=f"hora_cli_{clienteid}")
                descripcion = st.text_area("💬 Descripción o recordatorio", placeholder="Detalles de la acción…", key=f"desc_cli_{clienteid}")

            st.markdown("#### 👥 Asignar trabajador responsable")
            nombre_logueado = st.session_state.get("user_nombre", "").strip().lower()
            idx_default = 0
            for i, (n, _) in enumerate(trabajadores_map.items()):
                if nombre_logueado and nombre_logueado in n.lower():
                    idx_default = i
                    break

            trab_sel = st.selectbox(
                "Asignar a:",
                list(trabajadores_map.keys()) if trabajadores_map else ["(sin trabajadores disponibles)"],
                index=idx_default if trabajadores_map else 0,
                help="Selecciona el trabajador responsable de esta acción.",
            )
            trabajador_asignado = trabajadores_map.get(trab_sel, trabajadorid)

            enviado = st.form_submit_button("💾 Guardar acción", use_container_width=True)

        if enviado:
            if not titulo.strip():
                st.warning("⚠️ El título es obligatorio.")
                return
            payload = {
                "titulo": titulo.strip(),
                "descripcion": descripcion or None,
                "canal": canal,
                "estado": "Pendiente",
                "fecha_vencimiento": fecha_venc.isoformat(),
                "prioridad": prioridad,
                "trabajadorid": trabajadorid,
                "trabajador_asignadoid": trabajador_asignado,
                "clienteid": clienteid,
            }
            if hora:
                payload["fecha_accion"] = datetime.combine(fecha_venc, hora).replace(microsecond=0).isoformat()

            try:
                supabase.table("crm_actuacion").insert(payload).execute()
                st.toast(f"✅ Acción creada y asignada a {trab_sel}.", icon="✅")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar acción: {e}")

    # =====================================================
    # 📋 Listado de acciones existentes
    # =====================================================
    st.markdown("---")
    st.markdown("#### 🧾 Acciones registradas")

    try:
        acciones = (
            supabase.table("crm_actuacion")
            .select("crm_actuacionid, titulo, estado, canal, fecha_vencimiento, prioridad, trabajador_asignadoid, descripcion")
            .eq("clienteid", clienteid)
            .order("fecha_vencimiento", desc=False)
            .execute()
            .data or []
        )

        if not acciones:
            st.info("📭 Este cliente no tiene acciones registradas aún.")
            return

        for a in acciones:
            estado = a.get("estado", "Pendiente")
            prioridad = a.get("prioridad", "Media")
            canal = a.get("canal", "-")
            titulo = a.get("titulo", "(Sin título)")
            descripcion = a.get("descripcion") or "-"
            fecha_venc = a.get("fecha_vencimiento", "-")

            # Colores por estado
            color_estado = {
                "Pendiente": "#f59e0b",
                "Completada": "#16a34a",
                "Cancelada": "#6b7280",
            }.get(estado, "#f59e0b")

            # Colores por prioridad
            color_prioridad = {
                "Alta": "#dc2626",
                "Media": "#f59e0b",
                "Baja": "#22c55e",
            }.get(prioridad, "#6b7280")

            trabajador_asignado = trabajadores_rev.get(a.get("trabajador_asignadoid"), "—")

            st.markdown(
                f"""
                <div style='border:1px solid #e5e7eb;border-left:5px solid {color_estado};
                            background:#f9fafb;border-radius:10px;padding:10px 14px;margin-bottom:10px;'>
                    <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <div>
                            <b style='font-size:1rem;'>{titulo}</b> <span style='color:{color_prioridad};'>({prioridad})</span><br>
                            <span style='font-size:0.85rem;color:#374151;'>📡 {canal} — 🧑 {trabajador_asignado}</span><br>
                            <span style='font-size:0.85rem;color:#6b7280;'>⏰ {fecha_venc}</span>
                        </div>
                        <div style='font-weight:600;color:{color_estado};font-size:0.9rem;'>
                            {estado}
                        </div>
                    </div>
                    <div style='margin-top:6px;font-size:0.9rem;color:#374151;'>
                        {descripcion}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar las acciones: {e}")
