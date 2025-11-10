# ======================================================
# ⚠️ Gestión de incidencias — vista principal (ERP Editorial)
# ======================================================
import streamlit as st
import pandas as pd
from datetime import datetime
from modules.pedido_models import load_clientes, load_trabajadores

# ======================================================
# 🎯 VISTA PRINCIPAL — INCIDENCIAS
# ======================================================
def render_incidencia_lista(supabase):
    st.header("⚠️ Gestión de incidencias")
    st.caption("Monitorea y resuelve incidencias relacionadas con clientes, pedidos o productos, con su workflow completo.")

    session = st.session_state
    session.setdefault("inci_view", "Tarjetas")

    trabajadores = load_trabajadores(supabase)

    # ----------------------------
    # Filtros
    # ----------------------------
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        tipo_sel = st.selectbox("Origen tipo", ["Todos", "cliente", "pedido", "producto"])
    with col2:
        estado_sel = st.selectbox("Estado", ["Todos", "Abierta", "En curso", "Solucionada", "Rechazada"])
    with col3:
        asignado_sel = st.selectbox("Responsable", ["Todos"] + list(trabajadores.keys()))
    with col4:
        view = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, key="inci_view")

    # ----------------------------
    # Query principal
    # ----------------------------
    incidencias = []
    try:
        base = supabase.table("incidencia").select("*")
        if tipo_sel != "Todos":
            base = base.eq("origen_tipo", tipo_sel)
        if estado_sel != "Todos":
            base = base.eq("estado", estado_sel)
        if asignado_sel != "Todos":
            base = base.eq("responsableid", trabajadores[asignado_sel])
        data = base.order("fecha_creacion", desc=True).limit(150).execute()
        incidencias = data.data or []
    except Exception as e:
        st.error(f"❌ Error cargando incidencias: {e}")
        return

    if not incidencias:
        st.info("📭 No hay incidencias con los filtros seleccionados.")
        return

    # ----------------------------
    # KPIs rápidos
    # ----------------------------
    total = len(incidencias)
    abiertas = sum(1 for i in incidencias if "abier" in str(i.get("estado", "")).lower())
    curso = sum(1 for i in incidencias if "curso" in str(i.get("estado", "")).lower())
    solu = sum(1 for i in incidencias if "solu" in str(i.get("estado", "")).lower())
    rech = sum(1 for i in incidencias if "rech" in str(i.get("estado", "")).lower())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🔢 Total", total)
    c2.metric("🟠 Abiertas", abiertas)
    c3.metric("🔵 En curso", curso)
    c4.metric("🟢 Solucionadas", solu)
    c5.metric("🔴 Rechazadas", rech)

    # ----------------------------
    # Render listado
    # ----------------------------
    if view == "Tarjetas":
        cols = st.columns(2)
        for idx, i in enumerate(incidencias):
            with cols[idx % 2]:
                _render_incidencia_card(i, trabajadores)
    else:
        _render_incidencia_table(incidencias, trabajadores)

    # Modal de detalle
    if st.session_state.get("inci_show_modal"):
        render_incidencia_detalle(supabase)

# ======================================================
# 💳 TARJETAS
# ======================================================
def _render_incidencia_card(i, trabajadores):
    estado = i.get("estado", "-")
    trabajador = _label(trabajadores, i.get("responsableid"))
    tipo = i.get("origen_tipo", "-")
    color = "#9ca3af"

    e = estado.lower()
    if "abier" in e: color = "#f59e0b"
    elif "curso" in e: color = "#3b82f6"
    elif "solu" in e: color = "#10b981"
    elif "rech" in e: color = "#ef4444"

    st.markdown(f"""
    <div style='border:1px solid #ddd;border-radius:10px;padding:10px;margin-bottom:10px;background:#fff;'>
        <div style='display:flex;justify-content:space-between;align-items:center;'>
            <b>#{i['incidenciaid']} · {tipo}</b>
            <span style='background:{color};color:#fff;padding:2px 8px;border-radius:8px;font-size:0.8rem;'>{estado}</span>
        </div>
        <p style='margin-top:6px;'><b>{i.get('tipo','-')}</b> — {i.get('descripcion','')}</p>
        <p style='color:#555;font-size:0.85rem;'>👤 {trabajador or '-'} · 📅 {i.get('fecha_creacion','')}</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("📄 Ver workflow", key=f"detalle_{i['incidenciaid']}", use_container_width=True):
        st.session_state["inci_detalle_id"] = i["incidenciaid"]
        st.session_state["inci_show_modal"] = True
        st.rerun()

# ======================================================
# 📋 TABLA
# ======================================================
def _render_incidencia_table(data, trabajadores):
    if not data:
        st.info("📭 No hay incidencias para mostrar.")
        return

    df = pd.DataFrame(data)
    df["Responsable"] = df["responsableid"].apply(lambda rid: _label(trabajadores, rid))

    show_cols = ["incidenciaid", "tipo", "origen_tipo", "descripcion", "estado", "Responsable", "fecha_creacion"]
    show_cols = [c for c in show_cols if c in df.columns]

    st.dataframe(df[show_cols].sort_values("fecha_creacion", ascending=False), use_container_width=True, hide_index=True)

# ======================================================
# 🧾 DETALLE DE INCIDENCIA (con KPIs / SLA)
# ======================================================
def render_incidencia_detalle(supabase):
    incidenciaid = st.session_state.get("inci_detalle_id")
    if not incidenciaid:
        return

    try:
        i = supabase.table("incidencia").select("*").eq("incidenciaid", incidenciaid).single().execute().data
    except Exception as e:
        st.error(f"❌ Error cargando incidencia: {e}")
        return

    trabajadores = load_trabajadores(supabase)
    clientes = load_clientes(supabase)

    estado = i.get("estado", "-")
    origen_tipo = i.get("origen_tipo", "-")
    origen_id = i.get("origen_id")
    cliente_name = "-"
    if str(origen_tipo).lower() == "cliente" and origen_id:
        cliente_name = _label(clientes, origen_id)

    # --- Cabecera
    st.markdown("---")
    st.markdown(f"## 🧾 Incidencia #{incidenciaid} · {estado}")
    st.write(f"**Tipo:** {i.get('tipo','-')} ({origen_tipo})")
    st.write(f"**Descripción:** {i.get('descripcion','_Sin descripción_')}")
    st.write(f"**Responsable:** {_label(trabajadores, i.get('responsableid')) or '-'}")
    if cliente_name != "-":
        st.write(f"**Cliente:** {cliente_name}")
    st.write(f"📅 **Creada:** {i.get('fecha_creacion','-')}")
    if i.get("fecha_resolucion"):
        st.write(f"✅ **Resuelta:** {i.get('fecha_resolucion')}")

    # ======================================================
    # 🎯 KPIs / SLA
    # ======================================================
    from datetime import datetime as _dt
    def _parse_dt(s):
        if not s: return None
        try:
            return _dt.fromisoformat(str(s).replace("Z",""))
        except Exception:
            return None

    creada = _parse_dt(i.get("fecha_creacion"))
    resuelta = _parse_dt(i.get("fecha_resolucion"))
    ahora = _dt.now()
    abierta_horas = None
    tiempo_resolucion_h = None

    if creada:
        if resuelta:
            tiempo_resolucion_h = round((resuelta - creada).total_seconds() / 3600, 1)
        else:
            abierta_horas = round((ahora - creada).total_seconds() / 3600, 1)

    colsl = st.columns(3)
    with colsl[0]:
        st.metric("⏱️ Abierta (h)", abierta_horas if abierta_horas is not None else "—")
    with colsl[1]:
        st.metric("✅ Resolución (h)", tiempo_resolucion_h if tiempo_resolucion_h is not None else "—")
    with colsl[2]:
        sla_ok = None
        if tiempo_resolucion_h is not None:
            sla_ok = tiempo_resolucion_h <= 72
        elif abierta_horas is not None:
            sla_ok = abierta_horas <= 72
        st.metric("🎯 SLA 72h", "OK" if sla_ok else "⚠️" if sla_ok is not None else "—")

    # --- Workflow
    st.markdown("### 💬 Historial / Workflow")
    comentarios = []
    try:
        comentarios = (
            supabase.table("incidencia_comentario")
            .select("incidencia_comentarioid, comentario, usuario, fecha")
            .eq("incidenciaid", incidenciaid)
            .order("fecha", desc=False)
            .execute()
            .data or []
        )
    except Exception as e:
        st.warning(f"No se pudieron cargar los comentarios: {e}")

    for cmt in comentarios:
        st.markdown(
            f"""
            <div style='border-left:4px solid #3b82f6;padding-left:10px;margin:8px 0;'>
                <b>{cmt.get('usuario','')}</b> · {cmt.get('fecha','')}<br>
                <div style='margin-top:4px;white-space:pre-wrap;'>{cmt.get('comentario','')}</div>
            </div>
            """, unsafe_allow_html=True)


    st.markdown("### ✍️ Añadir comentario o avance")
    with st.form(f"form_com_{incidenciaid}", clear_on_submit=True):
        nuevo = st.text_area("Mensaje")
        usuario = st.text_input("Usuario", value=st.session_state.get("user_nombre", "Agente"))
        enviar = st.form_submit_button("💾 Enviar comentario")
        if enviar:
            if not nuevo.strip():
                st.warning("Escribe un comentario antes de enviar.")
            else:
                supabase.table("incidencia_comentario").insert({
                    "incidenciaid": incidenciaid,
                    "comentario": nuevo.strip(),
                    "usuario": usuario,
                    "fecha": datetime.now().isoformat(timespec="seconds")
                }).execute()
                st.success("Comentario añadido.")
                st.rerun()

    # --- Acciones rápidas
    st.markdown("---")
    st.subheader("🛠️ Acciones rápidas")
    col1, col2, col3 = st.columns(3)
    with col1:
        nuevo_estado = st.selectbox("Estado", ["Abierta", "En curso", "Solucionada", "Rechazada"], index=_estado_idx(estado))
    with col2:
        nuevo_resp = st.selectbox("Responsable", ["(Sin asignar)"] + list(trabajadores.keys()))
    with col3:
        prioridad = st.selectbox("Prioridad", ["Baja", "Media", "Alta"], index=_prio_index(i.get("prioridad")))

    resolucion = i.get("resolucion") or ""
    if "solu" in (nuevo_estado or "").lower():
        resolucion = st.text_area("🧩 Resolución (obligatoria)", value=resolucion, key=f"resol_{incidenciaid}")

    ca, cb, cc = st.columns([2, 2, 1])
    with ca:
        if st.button("💾 Guardar cambios", use_container_width=True):
            if "solu" in nuevo_estado.lower() and not (resolucion or "").strip():
                st.warning("⚠️ Debes escribir una resolución antes de marcar la incidencia como solucionada.")
                return
            payload = {
                "estado": nuevo_estado,
                "responsableid": trabajadores.get(nuevo_resp) if nuevo_resp != "(Sin asignar)" else None,
                "prioridad": prioridad,
            }
            if "solu" in nuevo_estado.lower():
                payload["resolucion"] = resolucion.strip()
                payload["fecha_resolucion"] = datetime.now().isoformat(timespec="seconds")
            supabase.table("incidencia").update(payload).eq("incidenciaid", incidenciaid).execute()
            st.success("Cambios guardados.")
            st.rerun()

    with cb:
        if st.button("✅ Marcar como solucionada", use_container_width=True):
            resolucion_input = st.session_state.get(f"resol_{incidenciaid}", "").strip()
            if not resolucion_input:
                st.warning("⚠️ Debes escribir una resolución antes de marcar la incidencia como solucionada.")
                return
            now = datetime.now().isoformat(timespec="seconds")
            supabase.table("incidencia").update({
                "estado": "Solucionada",
                "fecha_resolucion": now,
                "resolucion": resolucion_input
            }).eq("incidenciaid", incidenciaid).execute()
            supabase.table("incidencia_comentario").insert({
                "incidenciaid": incidenciaid,
                "comentario": f"✅ Incidencia marcada como solucionada. Resolución: {resolucion_input}",
                "usuario": "Sistema",
                "fecha": now
            }).execute()
            st.success("Incidencia solucionada.")
            st.rerun()

    with cc:
        if st.button("🚫 Rechazar", use_container_width=True):
            supabase.table("incidencia").update({"estado": "Rechazada"}).eq("incidenciaid", incidenciaid).execute()
            st.info("Incidencia rechazada.")
            st.rerun()

    if st.button("⬅️ Volver al listado", use_container_width=True):
        st.session_state["inci_show_modal"] = False
        st.session_state["inci_detalle_id"] = None
        st.rerun()

# ======================================================
# 🔧 HELPERS
# ======================================================
def _label(d: dict, idv):
    for k, v in (d or {}).items():
        if v == idv:
            return k
    return "-"

def _estado_idx(estado: str):
    e = (estado or "").lower()
    if "abier" in e: return 0
    if "curso" in e: return 1
    if "solu" in e: return 2
    if "rech" in e: return 3
    return 0

def _prio_index(p):
    if not p: return 1
    p = p.lower()
    if "baj" in p: return 0
    if "alt" in p: return 2
    return 1
