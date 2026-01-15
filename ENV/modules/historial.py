# modules/historial.py
# ================================================================
# 🕓 Historial profesional de comunicaciones — EnteNova Gnosis · Orbe
# ================================================================
# - Muestra comunicaciones del trabajador actual (por defecto)
# - Permite filtrar por trabajador, cliente, contacto y canal
# - Crea acciones CRM desde mensajes
# ================================================================

import streamlit as st
from datetime import datetime, date, time, timedelta
from dateutil.parser import parse as parse_date


def render_historial(supabase):
    st.header("🕓 Historial de comunicaciones")
    st.caption("Consulta y registra tus interacciones con clientes o contactos.")

    trabajadorid = st.session_state.get("trabajadorid")
    trabajador_nombre = st.session_state.get("user_nombre", "Desconocido")
    clienteid = st.session_state.get("cliente_actual")

    if not trabajadorid:
        st.warning("⚠️ No hay sesión de trabajador activa.")
        return

    # ======================================================
    # 🧭 FILTROS
    # ======================================================
    st.markdown("### 🔍 Filtros")

    # Cargar catálogos
    try:
        trabajadores = supabase.table("trabajador").select("trabajadorid,nombre,apellidos").execute().data or []
        clientes = supabase.table("cliente").select("clienteid,razon_social").order("razon_social").execute().data or []
    except Exception:
        trabajadores, clientes = [], []

    trabajadores_map = {f"{t['nombre']} {t['apellidos']}": t["trabajadorid"] for t in trabajadores}
    clientes_map = {c["razon_social"]: c["clienteid"] for c in clientes}

    colf1, colf2, colf3, colf4 = st.columns([2, 2, 2, 2])
    with colf1:
        trab_sel = st.selectbox("👤 Trabajador", ["Yo mismo"] + list(trabajadores_map.keys()))
    with colf2:
        cli_sel = st.selectbox("🏢 Cliente", ["Todos"] + list(clientes_map.keys()))
    with colf3:
        tipo_filtro = st.selectbox(
            "Tipo de comunicación",
            ["Todos", "llamada", "reunion", "email", "whatsapp", "otro"],
            index=0,
        )
    with colf4:
        fecha_desde = st.date_input("Desde", value=date.today() - timedelta(days=60))
        fecha_hasta = st.date_input("Hasta", value=date.today())

    # Determinar trabajadorid filtrado
    trabajador_filtro = trabajadorid if trab_sel == "Yo mismo" else trabajadores_map.get(trab_sel)

    st.markdown("---")

    # ======================================================
    # ➕ NUEVA COMUNICACIÓN
    # ======================================================
    st.subheader("➕ Registrar nueva comunicación")

    # Cargar contactos asociados al cliente actual (si lo hay)
    try:
        q_contactos = supabase.table("cliente_contacto").select("cliente_contactoid,nombre,email,clienteid")
        if clienteid:
            q_contactos = q_contactos.eq("clienteid", clienteid)
        contactos = q_contactos.order("nombre").execute().data or []
    except Exception as e:
        st.error(f"Error cargando contactos: {e}")
        contactos = []

    contactos_map = {f"{c['nombre']} ({c.get('email','-')})": c["cliente_contactoid"] for c in contactos}
    lista_contactos = list(contactos_map.keys()) + ["Otro / no registrado"]

    with st.form("form_comunicacion"):
        c1, c2 = st.columns(2)
        with c1:
            tipo = st.selectbox("Tipo", ["llamada", "reunion", "email", "whatsapp", "otro"])
            contacto_sel = st.selectbox("Contacto", lista_contactos)
        with c2:
            fecha = st.date_input("Fecha", value=date.today())
            hora = st.time_input("Hora", value=datetime.now().time())

        resumen = st.text_input("Resumen breve", placeholder="Ej: llamada con cliente sobre presupuesto")
        detalle = st.text_area("Detalles", placeholder="Describe lo tratado...", height=90)
        crear_accion = st.checkbox("🔁 Crear acción CRM desde esta comunicación")

        if crear_accion:
            colA, colB = st.columns(2)
            with colA:
                fecha_accion = st.date_input("📅 Fecha de acción", value=date.today() + timedelta(days=1))
            with colB:
                hora_accion = st.time_input("🕒 Hora de acción", value=time(9, 0))
            prioridad = st.selectbox("Prioridad", ["Alta", "Media", "Baja"], index=1)
            titulo_accion = st.text_input("Título de la acción", placeholder="Ej: seguimiento de llamada")

        enviado = st.form_submit_button("💾 Registrar")

    if enviado:
        if not resumen.strip():
            st.warning("⚠️ El resumen es obligatorio.")
        else:
            try:
                contacto_id = contactos_map.get(contacto_sel)
                registro = {
                    "cliente_contactoid": contacto_id,
                    "trabajadorid": trabajadorid,
                    "remitente": trabajador_nombre,
                    "contenido": detalle or resumen,
                    "fecha_envio": datetime.combine(fecha, hora).replace(microsecond=0).isoformat(),
                    "canal": tipo,
                    "tipo_comunicacion": tipo,
                    "estado_envio": "enviado",
                    "leido": True,
                }
                supabase.table("mensaje_contacto").insert(registro).execute()
                st.success("✅ Comunicación registrada correctamente.")

                # Crear acción CRM si procede
                if crear_accion and titulo_accion:
                    accion = {
                        "titulo": titulo_accion.strip(),
                        "descripcion": detalle or resumen,
                        "canal": tipo,
                        "estado": "Pendiente",
                        "fecha_accion": datetime.combine(fecha_accion, hora_accion).replace(microsecond=0).isoformat(),
                        "fecha_vencimiento": fecha_accion.isoformat(),
                        "prioridad": prioridad,
                        "trabajadorid": trabajadorid,
                    }
                    supabase.table("crm_actuacion").insert(accion).execute()
                    st.success("🧩 Acción CRM creada correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al registrar comunicación: {e}")

    st.markdown("---")
    # ======================================================
    # 🗂️ HISTORIAL DE COMUNICACIONES
    # ======================================================
    st.subheader("📜 Historial de comunicaciones recientes")

    try:
        query = (
            supabase.table("mensaje_contacto")
            .select("mensajeid, contacto_id, remitente, contenido, fecha_envio, canal, tipo_comunicacion")
            .eq("trabajadorid", trabajador_filtro)
            .order("fecha_envio", desc=True)
            .limit(200)
        )

        # Filtro cliente
        if cli_sel != "Todos":
            cli_id = clientes_map.get(cli_sel)
            if cli_id:
                contactos_ids = (
                    supabase.table("cliente_contacto")
                    .select("cliente_contactoid")
                    .eq("clienteid", cli_id)
                    .execute()
                    .data
                )
                ids = [c["cliente_contactoid"] for c in contactos_ids]
                if ids:
                    query = query.in_("contacto_id", ids)

        # Filtro tipo
        if tipo_filtro != "Todos":
            query = query.eq("tipo_comunicacion", tipo_filtro)

        if fecha_desde:
            query = query.gte("fecha_envio", fecha_desde.isoformat())
        if fecha_hasta:
            query = query.lte("fecha_envio", fecha_hasta.isoformat())

        mensajes = query.execute().data or []
    except Exception as e:
        st.error(f"❌ Error al cargar historial: {e}")
        mensajes = []

    if not mensajes:
        st.info("No hay comunicaciones registradas todavía.")
        # ❗️ NO hacemos return para permitir mostrar el historial de LOG SQL
        st.markdown("---")
        render_log_cambios(supabase)
        return


    # ======================================================
    # 📈 RESUMEN
    # ======================================================
    tipo_counts = {}
    for m in mensajes:
        tipo = m.get("tipo_comunicacion", "otro")
        tipo_counts[tipo] = tipo_counts.get(tipo, 0) + 1

    resumen_texto = " · ".join([f"{icono_tipo(t)} {t.capitalize()}: {n}" for t, n in tipo_counts.items()])
    if resumen_texto:
        st.markdown(f"**📊 Actividad reciente:** {resumen_texto}")
        st.divider()

    # ======================================================
    # 🎨 LISTADO
    # ======================================================
    contacto_ids = [m.get("contacto_id") for m in mensajes if m.get("contacto_id")]
    contacto_map = {}
    if contacto_ids:
        try:
            rows_contacto = (
                supabase.table("cliente_contacto")
                .select("cliente_contactoid, nombre")
                .in_("cliente_contactoid", contacto_ids)
                .execute()
                .data
            ) or []
            contacto_map = {r["cliente_contactoid"]: r.get("nombre") for r in rows_contacto}
        except Exception:
            contacto_map = {}

    for m in mensajes:
        tipo = m.get("tipo_comunicacion", "otro")
        icono = icono_tipo(tipo)
        fecha = parse_date(m["fecha_envio"]).strftime("%d/%m/%Y %H:%M")

        contacto_nombre = contacto_map.get(m.get("contacto_id"), "-")

        with st.expander(f"{icono} {tipo.capitalize()} — {fecha} · {contacto_nombre}"):
            st.markdown(f"**Remitente:** {m.get('remitente','-')}")
            st.markdown(f"**Mensaje:** {m.get('contenido','(sin contenido)')}")

            # Crear acción CRM
            st.divider()
            st.markdown("### 🔁 Crear acción CRM desde esta comunicación")

            col1, col2 = st.columns(2)
            with col1:
                fecha_accion = st.date_input("📅 Fecha", value=date.today(), key=f"fecha_{m['mensajeid']}")
            with col2:
                hora_accion = st.time_input("🕒 Hora", value=time(9, 0), key=f"hora_{m['mensajeid']}")
            titulo = st.text_input(
                "Título",
                value=f"{tipo.capitalize()} con {contacto_nombre}",
                key=f"titulo_{m['mensajeid']}",
            )
            prioridad = st.selectbox(
                "Prioridad", ["Alta", "Media", "Baja"], index=1, key=f"prio_{m['mensajeid']}"
            )

            if st.button("💾 Crear acción CRM", key=f"crear_accion_{m['mensajeid']}"):
                try:
                    accion = {
                        "titulo": titulo,
                        "descripcion": m.get("contenido", ""),
                        "canal": tipo,
                        "estado": "Pendiente",
                        "fecha_accion": datetime.combine(fecha_accion, hora_accion).replace(microsecond=0).isoformat(),
                        "fecha_vencimiento": fecha_accion.isoformat(),
                        "prioridad": prioridad,
                        "trabajadorid": trabajadorid,
                    }
                    supabase.table("crm_actuacion").insert(accion).execute()
                    st.success("✅ Acción CRM creada correctamente.")
                except Exception as e:
                    st.error(f"❌ Error al crear acción CRM: {e}")
# ================================
    # 👁️ VISOR DEL LOG SQL (botón)
    # ================================
    st.subheader("🧾 Cambios en base de datos")

    if st.button("👁️ Ver historial de cambios (LOG SQL)", use_container_width=True):
        st.session_state["mostrar_log_sql"] = True

    if st.session_state.get("mostrar_log_sql"):
        render_log_cambios(supabase)

    st.markdown("---")
    st.caption("📞 Historial de comunicaciones · EnteNova Gnosis · Orbe")

# ======================================================
# 🧾 HISTORIAL DE CAMBIOS (LOG SQL)
# ======================================================

import json
import pandas as pd

def render_log_cambios(supabase):
    st.markdown("### 🧾 Historial de cambios en base de datos")

    with st.expander("🔍 Ver historial de cambios (Log SQL)", expanded=False):

        # =============================
        # FILTROS
        # =============================
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            tabla_sel = st.selectbox(
                "📦 Tabla",
                ["Todas", "producto", "cliente", "pedido", "crm_actuacion", "mensaje_contacto"],
                index=0
            )
        with col2:
            accion_sel = st.selectbox("⚙️ Acción", ["Todas", "INSERT", "UPDATE", "DELETE"], index=0)
        with col3:
            buscar = st.text_input("🔎 Buscar ID, campo o texto")

        st.markdown("---")

        # =============================
        # QUERY BASE
        # =============================
        try:
            q = (
                supabase.table("log_cambio")
                .select("logid, tabla, registro_id, accion, tipo_log, usuario, trabajadorid, fecha, detalle")
                .order("fecha", desc=True)
                .limit(300)
            )

            if tabla_sel != "Todas":
                q = q.eq("tabla", tabla_sel)

            if accion_sel != "Todas":
                q = q.eq("accion", accion_sel)

            logs = q.execute().data or []

            # Filtro manual por texto (por si se busca ean, productoid, etc.)
            if buscar:
                buscar_low = buscar.lower()
                logs = [
                    l for l in logs
                    if buscar_low in json.dumps(l, default=str).lower()
                ]

        except Exception as e:
            st.error(f"❌ Error cargando historial de cambios: {e}")
            return

        if not logs:
            st.info("No hay cambios registrados con esos filtros.")
            return

        # =============================
        # LISTADO
        # =============================
        for log in logs:
            lid = log.get("logid")
            tabla = log.get("tabla", "-")
            accion = log.get("accion", "-")
            rid = log.get("registro_id", "-")
            fecha = log.get("fecha", "-")
            detalle = log.get("detalle")

            # Título del expander
            titulo = f"📌 [{tabla.upper()}] {accion} — ID {rid} — {fecha}"

            with st.expander(titulo, expanded=False):

                # --------------------------------------
                # Mostrar JSON old/new
                # --------------------------------------
                try:
                    parsed = detalle if isinstance(detalle, dict) else json.loads(detalle)
                except:
                    parsed = {"detalle": detalle}

                colA, colB = st.columns(2)
                with colA:
                    st.markdown("#### 📥 Nuevo valor")
                    if "new" in parsed and parsed["new"]:
                        st.json(parsed["new"])
                    else:
                        st.write("-")

                with colB:
                    st.markdown("#### 📤 Valor anterior")
                    if "old" in parsed and parsed["old"]:
                        st.json(parsed["old"])
                    else:
                        st.write("-")

                st.caption(f"🆔 Log #{lid} — Usuario: {log.get('usuario') or '-'} — Trabajador {log.get('trabajadorid') or '-'}")


def _build_resumen_cambios(new_data, old_data, campos_clave=None):
    """
    Devuelve dos listas de strings:
    - cambios en campos clave
    - cambios en el resto de campos
    usando la estructura detalle = {"new": {...}, "old": {...}}
    """
    if campos_clave is None:
        campos_clave = []

    resumen_clave = []
    resumen_otros = []

    if not isinstance(new_data, dict):
        return resumen_clave, resumen_otros

    # old_data puede ser None (INSERT)
    old_data = old_data or {}

    # Conjunto de todas las claves
    keys = set(new_data.keys()) | set(old_data.keys())

    for k in sorted(keys):
        nuevo = new_data.get(k)
        viejo = old_data.get(k)

        # Normalizar representación para comparar
        if isinstance(nuevo, float) and isinstance(viejo, float):
            iguales = abs(nuevo - viejo) < 1e-9
        else:
            iguales = (str(nuevo) == str(viejo))

        if iguales:
            continue  # no ha cambiado

        # Formateo bonico
        def fmt(v):
            if v is None:
                return "∅"
            if isinstance(v, bool):
                return "Sí" if v else "No"
            return str(v)

        linea = f"**{k}**: `{fmt(viejo)}` → `{fmt(nuevo)}`"

        if k in campos_clave:
            resumen_clave.append(linea)
        else:
            resumen_otros.append(linea)

    return resumen_clave, resumen_otros

# ======================================================
# 🔧 Helper para iconos
# ======================================================
def icono_tipo(tipo: str) -> str:
    iconos = {
        "llamada": "📞",
        "reunion": "🤝",
        "email": "✉️",
        "whatsapp": "💬",
        "otro": "🗒️",
    }
    return iconos.get(tipo, "🗒️")


