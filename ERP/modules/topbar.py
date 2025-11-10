import streamlit as st
from datetime import datetime, timedelta

def render_topbar(supabase):
    """
    🎨 Barra superior moderna con alertas CRM y mensajería integrada.
    - Botones: ➕ acción rápida, 🔔 acciones próximas, 📨 mensajes, 🚪 logout.
    - Indicadores rojos si hay pendientes o mensajes sin leer.
    - Popups interactivos con refresco local y marcado de lectura.
    """

    trabajadorid = st.session_state.get("trabajadorid")
    user = st.session_state.get("user_nombre", "Usuario")
    tipo = st.session_state.get("tipo_usuario", "Invitado").capitalize()

    # ------------------------------------------------------
    # 💅 ESTILOS
    # ------------------------------------------------------
    st.markdown("""
    <style>
    .topbar {
        position: sticky;
        top: 0;
        z-index: 100;
        background: linear-gradient(90deg, #0066cc, #0088ff);
        color: white;
        padding: 0.7rem 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 0 0 12px 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.25);
        font-family: 'Inter', sans-serif;
    }
    .topbar .left { font-weight: 600; font-size: 1.05rem; letter-spacing: 0.3px; }
    .topbar .right { display: flex; align-items: center; gap: 0.6rem; }
    .notif-popup {
        position: fixed;
        top: 65px;
        right: 30px;
        width: 360px;
        background: rgba(255,255,255,0.98);
        color: #111;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        padding: 1rem;
        backdrop-filter: blur(8px);
        animation: fadeIn 0.25s ease-in-out;
    }
    .notif-item { padding: 6px 0; border-bottom: 1px solid #eee; }
    .notif-item:hover { background: #f7faff; border-radius: 6px; }
    .btn-close { background: #ccc; color: #111; border: none; padding: 0.3rem 0.6rem; border-radius: 6px; cursor: pointer; }
    .btn-close:hover { background: #999; color: white; }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------
    # 🔔 Acciones próximas (7 días)
    # ------------------------------------------------------
    hay_alertas = False
    try:
        hoy = datetime.now().date()
        limite = hoy + timedelta(days=7)
        query = (
            supabase.table("crm_actuacion")
            .select("crm_actuacionid")
            .gte("fecha_vencimiento", hoy.isoformat())
            .lte("fecha_vencimiento", limite.isoformat())
            .neq("estado", "Completada")
        )
        if trabajadorid:
            query = query.eq("trabajadorid", trabajadorid)
        acciones = query.execute()
        hay_alertas = bool(acciones.data)
    except Exception:
        pass

    # ------------------------------------------------------
    # 📨 Mensajes no leídos
    # ------------------------------------------------------
    mensajes_no_leidos = 0
    try:
        if trabajadorid:
            mensajes = (
                supabase.table("mensaje_contacto")
                .select("mensajeid")
                .eq("trabajadorid", trabajadorid)
                .eq("leido", False)
                .execute()
            )
            mensajes_no_leidos = len(mensajes.data or [])
    except Exception:
        pass

    # ------------------------------------------------------
    # 🧭 TOPBAR
    # ------------------------------------------------------
    st.markdown('<div class="topbar">', unsafe_allow_html=True)
    col1, col2 = st.columns([4, 2])

    with col1:
        st.markdown('<div class="left">🧱 ERP EnteNova Gnosis</div>', unsafe_allow_html=True)

    with col2:
        c1, c2, c3, c4 = st.columns([0.18, 0.18, 0.18, 0.46])

        with c1:
            if st.button("➕", key="btn_add_action", help="Nueva acción CRM"):
                st.session_state["crear_accion_crm"] = True

        with c2:
            notif_label = "🔔"
            if hay_alertas:
                notif_label += " ●"
            if st.button(notif_label, key="btn_notif_topbar", help="Ver próximas acciones"):
                st.session_state["mostrar_acciones_crm"] = not st.session_state.get("mostrar_acciones_crm", False)

        with c3:
            msg_label = "📨"
            if mensajes_no_leidos > 0:
                msg_label += " ●"
            if st.button(msg_label, key="btn_msg_topbar", help=f"Tienes {mensajes_no_leidos} mensajes sin leer"):
                st.session_state["mostrar_mensajes_popup"] = not st.session_state.get("mostrar_mensajes_popup", False)

        with c4:
            st.markdown(f"<div class='right'><span>{user} ({tipo})</span></div>", unsafe_allow_html=True)
            if st.button("Cerrar sesión", key="btn_logout_topbar", use_container_width=True):
                for key in ["cliente_actual", "cliente_creado", "user_email", "user_nombre", "tipo_usuario", "trabajadorid"]:
                    st.session_state.pop(key, None)
                st.success("Sesión cerrada correctamente.")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------------
    # 🔔 POPUP: Acciones próximas
    # ------------------------------------------------------
    if st.session_state.get("mostrar_acciones_crm", False):
        st.markdown("<div class='notif-popup'>", unsafe_allow_html=True)
        st.markdown("### 🔔 Acciones próximas (7 días)")
        try:
            hoy = datetime.now().date()
            limite = hoy + timedelta(days=7)
            query = (
                supabase.table("crm_actuacion")
                .select("crm_actuacionid, descripcion, canal, estado, fecha_vencimiento")
                .gte("fecha_vencimiento", hoy.isoformat())
                .lte("fecha_vencimiento", limite.isoformat())
                .neq("estado", "Completada")
                .order("fecha_vencimiento", desc=False)
            )
            if trabajadorid:
                query = query.eq("trabajadorid", trabajadorid)
            acciones = query.execute()
            if acciones.data:
                for a in acciones.data:
                    fecha_acc = datetime.fromisoformat(a["fecha_vencimiento"]).strftime("%d/%m/%Y")
                    st.markdown(
                        f"<div class='notif-item'><b>{a['descripcion']}</b><br>"
                        f"📅 {fecha_acc} | 💬 {a.get('canal','-')} | 🏷️ {a.get('estado','Pendiente')}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No hay acciones programadas.")
        except Exception as e:
            st.error(f"❌ Error al cargar acciones: {e}")

        colb1, colb2 = st.columns([0.5, 0.5])
        with colb1:
            if st.button("🔄 Actualizar", key="btn_refresh_acc"):
                st.rerun()
        with colb2:
            if st.button("Cerrar 🔕", key="btn_close_acc"):
                st.session_state["mostrar_acciones_crm"] = False

        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------------------------------------------
    # 📨 POPUP: Bandeja de entrada + nuevo mensaje
    # ------------------------------------------------------
    if st.session_state.get("mostrar_mensajes_popup", False):
        st.markdown("<div class='notif-popup'>", unsafe_allow_html=True)
        st.markdown("### 📨 Mensajes recientes")

        try:
            mensajes = (
                supabase.table("mensaje_contacto")
                .select("mensajeid, remitente, contenido, fecha_envio, leido, canal")
                .eq("trabajadorid", trabajadorid)
                .order("fecha_envio", desc=True)
                .limit(5)
                .execute()
            )
            if mensajes.data:
                for m in mensajes.data:
                    fecha = datetime.fromisoformat(m["fecha_envio"]).strftime("%d/%m %H:%M") if m.get("fecha_envio") else "-"
                    leido = "✅" if m.get("leido") else "🔴"
                    canal = m.get("canal", "interno")
                    contenido = m.get("contenido", "(sin texto)")
                    resumen = contenido[:80] + ("..." if len(contenido) > 80 else "")

                    st.markdown(f"**{leido} {m['remitente']}** ({canal}) — {fecha}")
                    if st.button(f"🕓 Ver mensaje {m['mensajeid']}", key=f"ver_{m['mensajeid']}"):
                        st.info(f"📩 {contenido}")
                        # ✅ Marcar como leído
                        supabase.table("mensaje_contacto").update({"leido": True}).eq("mensajeid", m["mensajeid"]).execute()
                        st.rerun()
                    st.caption(f"{resumen}")
                    st.markdown("---")
            else:
                st.info("No hay mensajes registrados.")
        except Exception as e:
            st.error(f"❌ Error al cargar mensajes: {e}")

        # ✉️ Enviar mensaje nuevo
        st.markdown("#### ✉️ Enviar nuevo mensaje")
        try:
            clienteid = st.session_state.get("cliente_actual")
            trabajador_nombre = st.session_state.get("user_nombre", "Desconocido")

            if clienteid:
                contactos = (
                    supabase.table("cliente_contacto")
                    .select("cliente_contactoid, nombre, email")
                    .eq("clienteid", clienteid)
                    .execute()
                )
            else:
                contactos = (
                    supabase.table("cliente_contacto")
                    .select("cliente_contactoid, nombre, email")
                    .limit(50)
                    .execute()
                )

            if not contactos.data:
                st.warning("⚠️ No hay contactos disponibles.")
            else:
                nombres_contactos = {
                    f"{c['nombre']} ({c.get('email','-')})": c["cliente_contactoid"]
                    for c in contactos.data
                }
                with st.form("form_msg_popup"):
                    destinatario = st.selectbox("Destinatario", list(nombres_contactos.keys()))
                    canal = st.selectbox("Canal", ["interno", "email", "teléfono", "otro"])
                    mensaje = st.text_area("Mensaje", placeholder="Escribe tu mensaje...", height=100)
                    enviar = st.form_submit_button("📤 Enviar")
                if enviar and mensaje.strip():
                    supabase.table("mensaje_contacto").insert({
                        "contacto_id": nombres_contactos[destinatario],
                        "trabajadorid": trabajadorid,
                        "remitente": trabajador_nombre,
                        "contenido": mensaje.strip(),
                        "fecha_envio": datetime.now().isoformat(),
                        "leido": False,
                        "canal": canal,
                    }).execute()
                    st.success("✅ Mensaje enviado correctamente.")
                    st.session_state["mostrar_mensajes_popup"] = False
                    st.rerun()
        except Exception as e:
            st.error(f"❌ Error al enviar mensaje: {e}")

        colc1, colc2 = st.columns([0.5, 0.5])
        with colc1:
            if st.button("🔄 Actualizar", key="btn_refresh_msg"):
                st.rerun()
        with colc2:
            if st.button("Cerrar 📴", key="btn_close_msg"):
                st.session_state["mostrar_mensajes_popup"] = False

        st.markdown("</div>", unsafe_allow_html=True)
