import streamlit as st
from datetime import datetime, timedelta


# ======================================================
# 📞 WORKFLOW PROFESIONAL DE LLAMADA (CRM)
# ======================================================
def render_llamada_workflow(supabase, crm_actuacionid: int):

    # ==================================================
    # 1) Cargar actuación completa
    # ==================================================
    res = (
        supabase.table("crm_actuacion")
        .select(
            """
            crm_actuacionid,
            clienteid,
            trabajadorid,
            canal,
            estado,
            fecha_accion,
            fecha_vencimiento,
            hora_inicio,
            hora_fin,
            duracion_segundos,
            resultado,
            titulo,
            descripcion,
            requiere_seguimiento,
            fecha_recordatorio,
            cliente (clienteid, razon_social),
            trabajador!crm_actuacion_trabajadorid_fkey (trabajadorid, nombre, apellidos)
        """
        )
        .eq("crm_actuacionid", crm_actuacionid)
        .single()
        .execute()
        .data
    )

    if not res:
        st.error("❌ No se encontró la actuación.")
        return

    act = res

    # ==================================================
    # 2) Datos visuales
    # ==================================================
    cliente_nombre = act.get("cliente", {}).get("razon_social", "—")
    trabajador_nombre = (
        f"{act['trabajador']['nombre']} {act['trabajador']['apellidos']}"
        if act.get("trabajador")
        else "—"
    )

    st.markdown(
        f"### 📞 Llamada — <b>{cliente_nombre}</b>",
        unsafe_allow_html=True
    )
    st.caption(f"👤 Comercial: {trabajador_nombre} · Estado: **{act['estado']}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"📅 Acción: {act.get('fecha_accion')}")
    with col2:
        st.write(f"🎯 Vence: {act.get('fecha_vencimiento')}")
    with col3:
        if act.get("duracion_segundos"):
            m = act["duracion_segundos"] // 60
            s = act["duracion_segundos"] % 60
            st.write(f"⏱️ Duración: {m}m {s}s")

    if act.get("descripcion"):
        st.markdown("**Descripción:**")
        st.write(act["descripcion"])

    st.divider()

    hora_inicio = act.get("hora_inicio")
    hora_fin = act.get("hora_fin")

    # Normalizar hora ISO
    def _parse_fecha(x):
        if not x:
            return None
        return datetime.fromisoformat(x.replace("Z", "+00:00"))

    # ======================================================
    # 3) INICIAR LLAMADA
    # ======================================================
    if not hora_inicio:
        if st.button("▶️ Iniciar llamada", use_container_width=True):
            ahora = datetime.utcnow().isoformat()

            supabase.table("crm_actuacion") \
                .update({"hora_inicio": ahora}) \
                .eq("crm_actuacionid", crm_actuacionid) \
                .execute()

            _registrar_historial(
                supabase,
                act["clienteid"],
                f"📞 Inicio de llamada (Actuación #{crm_actuacionid})."
            )

            st.success("Llamada iniciada.")
            st.rerun()

        return

    else:
        st.info(f"📍 Llamada iniciada: {hora_inicio}")

    # ======================================================
    # 4) FINALIZAR LLAMADA
    # ======================================================
    if hora_inicio and not hora_fin:

        st.markdown("### 🟢 Finalizar llamada")

        resultado_principal = st.selectbox(
            "Resultado",
            [
                "Contactado - Interesado",
                "Contactado - No interesado",
                "No contesta",
                "Número incorrecto",
                "Buzón de voz",
                "Otro",
            ],
        )

        notas = st.text_area(
            "Notas / detalles",
            value=act.get("resultado") or "",
        )

        # Seguimiento automático
        crear_seguimiento = st.checkbox(
            "📅 Crear actuación de seguimiento automática",
            value=(resultado_principal in ["Contactado - Interesado", "No contesta"]),
        )

        if crear_seguimiento:
            dias_seg = st.number_input("Días hasta el seguimiento", 1, 60, 3)

        if st.button("✅ Guardar y finalizar", use_container_width=True):

            ahora = datetime.utcnow()
            inicio_dt = _parse_fecha(hora_inicio)
            duracion = int((ahora - inicio_dt).total_seconds())

            # --------------------------------------------
            # Actualizar actuación actual
            # --------------------------------------------
            supabase.table("crm_actuacion").update(
                {
                    "hora_fin": ahora.isoformat(),
                    "duracion_segundos": duracion,
                    "estado": "Completada",
                    "resultado": notas or resultado_principal,
                }
            ).eq("crm_actuacionid", crm_actuacionid).execute()

            # --------------------------------------------
            # Crear seguimiento automático
            # --------------------------------------------
            if crear_seguimiento:
                fecha_seg = (ahora + timedelta(days=int(dias_seg))).replace(
                    hour=10, minute=0, second=0, microsecond=0
                )

                payload_seg = {
                    "clienteid": act["clienteid"],
                    "trabajadorid": act["trabajadorid"],
                    "canal": act.get("canal") or "llamada",
                    "descripcion": f"Seguimiento automático: {resultado_principal}",
                    "estado": "Pendiente",
                    "fecha_accion": fecha_seg.isoformat(),
                    "fecha_vencimiento": fecha_seg.date().isoformat(),
                    "prioridad": "Media",
                    "titulo": "Seguimiento de llamada",
                    "resultado": None,
                    "requiere_seguimiento": True,
                    "fecha_recordatorio": fecha_seg.date().isoformat(),
                }

                supabase.table("crm_actuacion").insert(payload_seg).execute()

                _registrar_historial(
                    supabase,
                    act["clienteid"],
                    f"📅 Programado seguimiento automático para el {fecha_seg.date()}."
                )

            # --------------------------------------------
            # Registrar fin de llamada
            # --------------------------------------------
            _registrar_historial(
                supabase,
                act["clienteid"],
                f"📞 Llamada finalizada. Resultado: {resultado_principal}."
            )

            st.success("Llamada finalizada correctamente.")
            st.rerun()

    # ======================================================
    # 5) LLAMADA YA FINALIZADA
    # ======================================================
    if hora_fin:
        st.success("✔ La llamada ya está finalizada.")
        st.write(f"⏱ Inicio: {hora_inicio}")
        st.write(f"⏱ Fin: {hora_fin}")

        if act.get("resultado"):
            st.markdown("**Notas registradas:**")
            st.write(act["resultado"])


# ======================================================
# 📝 REGISTRO DE HISTORIAL CRM (mensajes / actividad)
# ======================================================
def _registrar_historial(supa, clienteid: int, mensaje: str):
    try:
        supa.table("mensaje_contacto").insert({
            "clienteid": clienteid,
            "mensaje": mensaje,
            "fecha": datetime.utcnow().isoformat()
        }).execute()
    except Exception:
        pass
