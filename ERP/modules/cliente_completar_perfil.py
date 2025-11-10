import streamlit as st
from modules.cliente_direccion_form import render_direccion_form
from modules.cliente_facturacion_form import render_facturacion_form
from modules.cliente_documento_form import render_documento_form
from modules.historial import render_historial  # 🆕 NUEVO: integración CRM


def render_cliente_completar_perfil(supabase):
    st.header("👤 Completar perfil del cliente")
    st.caption("Añade información detallada: direcciones, facturación, documentos, observaciones y comunicaciones.")

    # ==================================================
    # 🔍 Detección automática del cliente activo
    # ==================================================
    clienteid = (
        st.session_state.get("cliente_creado")
        or st.session_state.get("cliente_actual")
    )

    if not clienteid:
        # Si no hay cliente cargado, mostrar formulario de búsqueda
        st.subheader("🔑 Seleccionar cliente manualmente")
        cols = st.columns([2, 1])
        with cols[0]:
            cliente_input = st.text_input(
                "ID o identificador del cliente",
                key="buscar_cliente",
                placeholder="Ej: 123 o LIB-libreria-san-marcos",
            )
        with cols[1]:
            cargar = st.button("Cargar cliente existente", key="btn_cargar_cliente")

        if cargar and cliente_input:
            try:
                query = supabase.table("cliente").select("clienteid, identificador")
                if cliente_input.isdigit():
                    res = query.or_(
                        f"clienteid.eq.{cliente_input},identificador.eq.{cliente_input}"
                    ).limit(1).execute()
                else:
                    res = query.eq("identificador", cliente_input).limit(1).execute()

                if res.data:
                    clienteid = res.data[0]["clienteid"]
                    st.session_state["cliente_creado"] = clienteid
                    st.success(
                        f"✅ Cliente cargado: {res.data[0]['identificador']} (ID {clienteid})"
                    )
                    st.rerun()
                else:
                    st.warning("⚠️ No se encontró ningún cliente con ese ID o identificador.")
            except Exception as e:
                st.error(f"❌ Error al buscar cliente: {e}")
            return

        st.info("ℹ️ Introduce un ID o identificador, o crea un cliente básico antes de completar su perfil.")
        return

    # ==================================================
    # 📋 Pestañas principales (ahora con HISTORIAL)
    # ==================================================
    tabs = st.tabs(
        [
            "🏠 Dirección",
            "🏦 Facturación y banco",
            "📎 Documentos",
            "🗒️ Observaciones",
            "💬 Historial / CRM"  # 🆕 Nueva pestaña
        ]
    )

    # ==================================================
    # 🏠 DIRECCIÓN
    # ==================================================
    with tabs[0]:
        st.subheader("🏠 Dirección fiscal y de envío")
        st.info("Añade al menos una dirección fiscal. Puedes añadir también direcciones de envío.")
        render_direccion_form(supabase, clienteid)

    # ==================================================
    # 🏦 FACTURACIÓN Y BANCO
    # ==================================================
    with tabs[1]:
        st.subheader("🏦 Datos bancarios y facturación")
        st.info("Selecciona la forma de pago y configura opciones de facturación. Banco solo si aplica (transferencia / domiciliación).")
        render_facturacion_form(supabase, clienteid)

    # ==================================================
    # 📎 DOCUMENTOS
    # ==================================================
    with tabs[2]:
        st.subheader("📎 Documentos del cliente")
        st.info("Sube contratos, autorizaciones SEPA, FACE u otros anexos.")
        render_documento_form(supabase, clienteid)

    # ==================================================
    # 🗒️ OBSERVACIONES
    # ==================================================
    with tabs[3]:
        st.subheader("🗒️ Observaciones adicionales")
        st.info("Guarda comentarios generales o específicos. Se almacenan como parámetros del cliente.")

        tema_obs = st.selectbox(
            "¿Sobre qué trata la observación?",
            ["General", "Dirección", "Forma de pago", "Facturación", "Documentos"],
            key="select_obs_tipo",
        )
        obs = st.text_area(
            "Escribe tus observaciones",
            key="textarea_obs_general",
            placeholder="Ej: prefiere facturas agrupadas a fin de mes.",
        )

        if st.button("💾 Guardar observación", key="btn_guardar_obs"):
            if obs.strip():
                try:
                    supabase.table("cliente_parametro").upsert(
                        {
                            "clienteid": clienteid,
                            "clave": f"observacion_{tema_obs.lower()}",
                            "valor": obs.strip(),
                        },
                        on_conflict="clienteid,clave",
                    ).execute()
                    st.success("✅ Observación guardada correctamente.")
                except Exception as e:
                    st.error(f"❌ Error al guardar la observación: {e}")
            else:
                st.warning("⚠️ No se ha introducido ninguna observación.")

    # ==================================================
    # 💬 HISTORIAL / CRM
    # ==================================================
    with tabs[4]:
        st.subheader("💬 Historial y comunicaciones del cliente")
        st.info("Consulta y registra las interacciones mantenidas con el cliente. Puedes convertir cada comunicación en una acción CRM.")
        
        # Forzamos el cliente activo en sesión para que render_historial lo use directamente
        st.session_state["cliente_actual"] = clienteid
        render_historial(supabase)
