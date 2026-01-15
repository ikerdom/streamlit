# modules/crm_accion_detalle.py
# Panel de detalle de acción CRM vía API.

import streamlit as st
from datetime import datetime, date, time, timedelta
from dateutil.parser import parse as parse_date

from modules.crm_api import detalle as api_detalle, actualizar as api_actualizar
from modules.pedido_api import catalogos as pedido_catalogos  # para listar trabajadores


def render_crm_accion_detalle(_supabase_unused, accionid: int):
    if not accionid:
        st.warning("⚠️ No se ha seleccionado ninguna acción.")
        return

    trabajadorid = st.session_state.get("trabajadorid")

    try:
        accion = api_detalle(accionid)
    except Exception as e:
        st.error(f"❌ Error cargando acción: {e}")
        return

    if not accion:
        st.error("No se encontró la acción seleccionada.")
        return

    st.markdown(f"### 📌 {accion.get('titulo', '(Sin título)')}")
    st.caption(
        f"Canal: {accion.get('canal', '-')},  Prioridad: {accion.get('prioridad', '-')},  Estado: {accion.get('estado', '-')}"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Descripción:** {accion.get('descripcion') or '–'}")
    with col2:
        if accion.get("fecha_vencimiento"):
            fecha_venc = parse_date(str(accion["fecha_vencimiento"])).date()
            st.markdown(f"**Fecha límite:** {fecha_venc.strftime('%d/%m/%Y')}")
        else:
            fecha_venc = date.today()
            st.markdown("**Fecha límite:** –")

    st.divider()

    # POSPONER
    with st.expander("⏰ Posponer acción"):
        col1, col2 = st.columns(2)
        default_date = max(date.today(), fecha_venc)
        default_time = parse_date(str(accion["fecha_accion"])).time() if accion.get("fecha_accion") else time(9, 0)
        with col1:
            nueva_fecha = st.date_input(
                "Nueva fecha",
                value=default_date,
                min_value=date.today(),
                max_value=date.today() + timedelta(days=365 * 10),
                key=f"posp_fecha_{accionid}",
            )
        with col2:
            nueva_hora = st.time_input("Nueva hora", value=default_time, key=f"posp_hora_{accionid}")

        if st.button("💾 Guardar nueva fecha/hora", key=f"save_fecha_{accionid}"):
            try:
                nueva_fecha_accion = datetime.combine(nueva_fecha, nueva_hora).replace(microsecond=0)
                payload = {
                    "fecha_vencimiento": nueva_fecha.isoformat(),
                    "fecha_accion": nueva_fecha_accion.isoformat(),
                }
                api_actualizar(accionid, payload)
                st.success("✅ Acción pospuesta correctamente.")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al posponer: {e}")

    # REASIGNAR
    with st.expander("👤 Reasignar trabajador responsable"):
        try:
            cats = pedido_catalogos()
            trabajadores = {t["label"]: t["id"] for t in cats.get("trabajadores", [])}
        except Exception:
            trabajadores = {}
        trab_sel = st.selectbox("Seleccionar nuevo responsable", list(trabajadores.keys()) or ["(ninguno)"], index=0, key=f"reasignar_sel_{accionid}")
        if st.button("🔁 Reasignar acción", key=f"reasignar_btn_{accionid}"):
            try:
                payload = {
                    "trabajador_asignadoid": trabajadores.get(trab_sel),
                }
                api_actualizar(accionid, payload)
                st.success(f"✅ Acción reasignada a {trab_sel}.")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al reasignar: {e}")

    # COMPLETAR / CANCELAR
    st.divider()
    colA, colB = st.columns(2)
    with colA:
        if st.button("✅ Marcar completada", key=f"comp_{accionid}"):
            api_actualizar(accionid, {"estado": "Completada"})
            st.success("✅ Acción completada.")
            st.session_state["force_reload"] = True
            st.rerun()

    with colB:
        if st.button("🚫 Cancelar acción", key=f"cancel_{accionid}"):
            api_actualizar(accionid, {"estado": "Cancelada"})
            st.warning("⚠️ Acción cancelada.")
            st.session_state["force_reload"] = True
            st.rerun()

    st.markdown("---")
    st.caption("CRM Acción Detalle · EnteNova Gnosis · Orbe")
