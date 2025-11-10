# modules/crm_accion_detalle.py
import streamlit as st
from datetime import datetime, date, time, timedelta
from dateutil.parser import parse as parse_date
from modules.pedido_models import load_trabajadores

def render_crm_accion_detalle(supabase, accionid: int):
    """
    🧭 Panel de detalle interactivo de una acción CRM.
    Permite ver, posponer, reasignar, duplicar o completar una acción.
    """
    if not accionid:
        st.warning("⚠️ No se ha seleccionado ninguna acción.")
        return

    trabajadorid = st.session_state.get("trabajadorid")

    # ----------------------------
    # Cargar acción actual
    # ----------------------------
    try:
        accion = (
            supabase.table("crm_actuacion")
            .select("*")
            .eq("crm_actuacionid", accionid)
            .single()
            .execute()
            .data
        )
    except Exception as e:
        st.error(f"❌ Error cargando acción: {e}")
        return

    if not accion:
        st.error("No se encontró la acción seleccionada.")
        return

    # ----------------------------
    # Cabecera de la acción
    # ----------------------------
    st.markdown(f"### 📌 {accion.get('titulo', '(Sin título)')}")
    st.caption(
        f"Canal: {accion.get('canal', '-')},  Prioridad: {accion.get('prioridad', '-')},  Estado: {accion.get('estado', '-')}"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Descripción:** {accion.get('descripcion') or '—'}")
    with col2:
        if accion.get("fecha_vencimiento"):
            fecha_venc = parse_date(str(accion["fecha_vencimiento"])).date()
            st.markdown(f"**Fecha límite:** {fecha_venc.strftime('%d/%m/%Y')}")
        else:
            fecha_venc = date.today()
            st.markdown("**Fecha límite:** —")

    st.divider()

    # =======================================================
    # ⏰ POSPONER ACCIÓN (actualiza calendario real)
    # =======================================================
    with st.expander("⏰ Posponer acción"):
        col1, col2 = st.columns(2)

        default_date = max(date.today(), fecha_venc)
        default_time = (
            parse_date(str(accion["fecha_accion"])).time()
            if accion.get("fecha_accion")
            else time(9, 0)
        )

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
                    "fecha_modificacion": datetime.now().isoformat(),
                    "modificado_porid": trabajadorid,
                }
                supabase.table("crm_actuacion").update(payload).eq("crm_actuacionid", accionid).execute()
                st.success("✅ Acción pospuesta correctamente.")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al posponer: {e}")

    # =======================================================
    # 👥 REASIGNAR TRABAJADOR
    # =======================================================
    with st.expander("👥 Reasignar trabajador responsable"):
        trabajadores = load_trabajadores(supabase)
        trabajador_sel = st.selectbox(
            "Seleccionar nuevo responsable",
            list(trabajadores.keys()),
            index=0,
            key=f"reasignar_sel_{accionid}",
        )
        if st.button("🔄 Reasignar acción", key=f"reasignar_btn_{accionid}"):
            try:
                payload = {
                    "trabajador_asignadoid": trabajadores[trabajador_sel],
                    "fecha_modificacion": datetime.now().isoformat(),
                    "modificado_porid": trabajadorid,
                }
                supabase.table("crm_actuacion").update(payload).eq("crm_actuacionid", accionid).execute()
                st.success(f"✅ Acción reasignada a {trabajador_sel}.")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al reasignar: {e}")

    # =======================================================
    # 📋 DUPLICAR ACCIÓN
    # =======================================================
    with st.expander("📋 Duplicar acción"):
        col1, col2 = st.columns(2)
        with col1:
            fecha_copia = st.date_input(
                "Fecha de la nueva acción",
                value=date.today() + timedelta(days=1),
                min_value=date.today(),
                key=f"dup_fecha_{accionid}",
            )
        with col2:
            hora_copia = st.time_input("Hora de la nueva acción", value=time(9, 0), key=f"dup_hora_{accionid}")

        trabajadores = load_trabajadores(supabase)
        trab_copia = st.selectbox("Asignar a", list(trabajadores.keys()), index=0, key=f"dup_trab_{accionid}")

        if st.button("📄 Crear copia", key=f"dup_btn_{accionid}"):
            try:
                payload = {**accion}
                payload.pop("crm_actuacionid", None)
                payload["trabajadorid"] = trabajadores[trab_copia]
                payload["trabajador_asignadoid"] = trabajadores[trab_copia]
                payload["fecha_accion"] = datetime.combine(fecha_copia, hora_copia).replace(microsecond=0).isoformat()
                payload["fecha_vencimiento"] = fecha_copia.isoformat()
                payload["fecha_modificacion"] = datetime.now().isoformat()
                payload["modificado_porid"] = trabajadorid
                payload["estado"] = "Pendiente"
                supabase.table("crm_actuacion").insert(payload).execute()
                st.success(f"✅ Copia creada y asignada a {trab_copia}.")
                st.session_state["force_reload"] = True
            except Exception as e:
                st.error(f"Error al duplicar: {e}")

    # =======================================================
    # ✅ COMPLETAR O ❌ CANCELAR
    # =======================================================
    st.divider()
    colA, colB = st.columns(2)
    with colA:
        if st.button("✅ Marcar completada", key=f"comp_{accionid}"):
            supabase.table("crm_actuacion").update(
                {
                    "estado": "Completada",
                    "fecha_modificacion": datetime.now().isoformat(),
                    "modificado_porid": trabajadorid,
                }
            ).eq("crm_actuacionid", accionid).execute()
            st.success("✅ Acción completada.")
            st.session_state["force_reload"] = True
            st.rerun()

    with colB:
        if st.button("❌ Cancelar acción", key=f"cancel_{accionid}"):
            supabase.table("crm_actuacion").update(
                {
                    "estado": "Cancelada",
                    "fecha_modificacion": datetime.now().isoformat(),
                    "modificado_porid": trabajadorid,
                }
            ).eq("crm_actuacionid", accionid).execute()
            st.warning("⚠️ Acción cancelada.")
            st.session_state["force_reload"] = True
            st.rerun()

    st.markdown("---")
    st.caption("CRM Acción Detalle · EnteNova Gnosis · Orbe")
