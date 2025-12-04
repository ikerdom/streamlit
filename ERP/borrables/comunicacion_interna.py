import streamlit as st
from datetime import datetime

def render_comunicacion_interna(supabase):
    """
    💬 Comunicación interna entre trabajadores y contactos.
    - Filtra por trabajador logueado (solo sus mensajes).
    - Permite enviar mensajes a contactos o revisar conversaciones previas.
    """

    st.header("💬 Comunicación interna")
    st.caption("Envía y revisa mensajes entre trabajadores y contactos. Ideal para seguimiento de clientes o coordinación interna.")

    # ======================================================
    # 🔐 Contexto de sesión
    # ======================================================
    trabajadorid = st.session_state.get("trabajadorid")
    trabajador_nombre = st.session_state.get("user_nombre", "Desconocido")

    if not trabajadorid:
        st.warning("⚠️ No hay sesión activa de trabajador.")
        st.stop()

    # ======================================================
    # 🔍 FILTROS DE BÚSQUEDA
    # ======================================================
    col1, col2 = st.columns([2, 1])
    with col1:
        filtro_texto = st.text_input("Buscar por palabra o contacto", key="buscar_mensaje")
    with col2:
        try:
            contactos_data = (
                supabase.table("cliente_contacto")
                .select("cliente_contactoid, nombre")
                .order("nombre")
                .limit(100)
                .execute()
            )
            lista_contactos = ["Todos"] + [c["nombre"] for c in contactos_data.data]
        except Exception:
            lista_contactos = ["Todos"]
        filtro_contacto = st.selectbox("Filtrar por contacto", lista_contactos, key="filtro_contacto")

    st.markdown("---")
    st.subheader("📥 Últimos mensajes")

    # ======================================================
    # 📋 CARGAR MENSAJES DEL TRABAJADOR
    # ======================================================
    try:
        query = (
            supabase.table("mensaje_contacto")
            .select("mensajeid, contacto_id, remitente, contenido, fecha_envio, leido, canal, trabajadorid")
            .eq("trabajadorid", trabajadorid)  # 🔥 solo mensajes del trabajador
            .order("fecha_envio", desc=True)
            .limit(100)
        )

        # Filtrar por contacto
        if filtro_contacto != "Todos":
            res = (
                supabase.table("cliente_contacto")
                .select("cliente_contactoid")
                .eq("nombre", filtro_contacto)
                .limit(1)
                .execute()
            )
            if res.data:
                contacto_id = res.data[0]["cliente_contactoid"]
                query = query.eq("contacto_id", contacto_id)

        mensajes = query.execute()

        if mensajes.data:
            for m in mensajes.data:
                contacto = (
                    supabase.table("cliente_contacto")
                    .select("nombre, email")
                    .eq("cliente_contactoid", m["contacto_id"])
                    .limit(1)
                    .execute()
                )
                nombre_contacto = (
                    contacto.data[0]["nombre"]
                    if contacto.data else "Desconocido"
                )
                email_contacto = (
                    contacto.data[0].get("email", "-")
                    if contacto.data else "-"
                )

                fecha = (
                    datetime.fromisoformat(m["fecha_envio"]).strftime("%d/%m/%Y %H:%M")
                    if m.get("fecha_envio") else "Sin fecha"
                )
                canal = m.get("canal", "interno")
                leido = "✅ Sí" if m.get("leido") else "❌ No"

                st.markdown(f"""
                **🧾 De:** {m['remitente']}  
                **📨 Para:** {nombre_contacto} ({email_contacto})  
                **🕒 Fecha:** {fecha}  
                **📡 Canal:** {canal}  
                **👁️ Leído:** {leido}  
                > {m['contenido']}
                """)
                st.markdown("---")
        else:
            st.info("No hay mensajes registrados todavía.")
    except Exception as e:
        st.error(f"❌ Error al cargar mensajes: {e}")

    # ======================================================
    # ✉️ ENVIAR NUEVO MENSAJE
    # ======================================================
    st.subheader("✉️ Enviar nuevo mensaje")

    try:
        contactos = (
            supabase.table("cliente_contacto")
            .select("cliente_contactoid, nombre, email")
            .order("nombre")
            .limit(100)
            .execute()
        )
    except Exception as e:
        st.error(f"❌ Error al cargar contactos: {e}")
        return

    if not contactos.data:
        st.warning("⚠️ No hay contactos disponibles para enviar mensajes.")
        return

    nombres_contactos = {
        f"{c['nombre']} ({c.get('email','-')})": c["cliente_contactoid"]
        for c in contactos.data
    }

    with st.form("form_nuevo_mensaje"):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input(
                "Remitente (trabajador)",
                value=trabajador_nombre,
                disabled=True,
                key="msg_remitente_display",
            )
        with col2:
            destinatario = st.selectbox(
                "Destinatario (contacto)",
                list(nombres_contactos.keys()),
                key="msg_destinatario",
            )

        canal = st.selectbox(
            "Canal",
            ["interno", "email", "teléfono", "otro"],
            index=0,
            key="msg_canal",
        )
        mensaje = st.text_area(
            "Mensaje",
            placeholder="Escribe aquí tu mensaje...",
            height=100,
            key="msg_contenido",
        )

        enviar = st.form_submit_button("📤 Enviar mensaje")

    if enviar and mensaje.strip():
        try:
            supabase.table("mensaje_contacto").insert({
                "contacto_id": nombres_contactos[destinatario],
                "trabajadorid": trabajadorid,  # 🔥 vínculo directo
                "remitente": trabajador_nombre,
                "contenido": mensaje.strip(),
                "fecha_envio": datetime.now().isoformat(),
                "leido": False,
                "canal": canal,
            }).execute()
            st.success(f"✅ Mensaje enviado correctamente a {destinatario}.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error al enviar el mensaje: {e}")

    st.markdown("---")
    st.caption("Comunicación interna de trabajadores · EnteNova Gnosis · Orbe")
