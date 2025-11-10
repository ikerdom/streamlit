import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from modules.diagramas import render_diagramas
from modules.orbe_palette import PRIMARY, SUCCESS, WARNING, DANGER, SECONDARY

# ======================================================
# 📊 DASHBOARD PRINCIPAL COMERCIAL · EnteNova Gnosis · Orbe
# ======================================================
def render_dashboard(supabase):
    # ------------------------------------------------------
    # 🌙 MODO OSCURO (persistente en sesión)
    # ------------------------------------------------------
    if "modo_oscuro" not in st.session_state:
        st.session_state["modo_oscuro"] = False

    dark_mode = st.toggle("🌙 Modo oscuro", value=st.session_state["modo_oscuro"], help="Activa una vista nocturna más cómoda.")
    st.session_state["modo_oscuro"] = dark_mode

    if dark_mode:
        st.markdown("""
        <style>
        body, .stApp { background-color: #0f172a !important; color: #f1f5f9 !important; }
        div[data-testid="stMarkdownContainer"] p { color: #f8fafc !important; }
        div[data-testid="stMetricValue"] { color: #facc15 !important; }
        .stDataFrame { background-color: #1e293b !important; color: #e2e8f0 !important; }
        </style>
        """, unsafe_allow_html=True)

    # ------------------------------------------------------
    # 🧱 ENCABEZADO PRINCIPAL
    # ------------------------------------------------------
    st.markdown(f"""
    <div style='background:#ecfdf5;padding:18px 20px;border-radius:12px;border-left:6px solid {PRIMARY};
                margin-bottom:18px;box-shadow:0 1px 3px rgba(0,0,0,0.05);'>
        <h2 style='margin:0;color:#065f46;'>📊 Panel General — EnteNova Gnosis · Orbe</h2>
        <p style='color:#166534;margin-top:4px;'>Resumen comercial, CRM, actividad y rendimiento del equipo.</p>
    </div>
    """, unsafe_allow_html=True)

    trabajadorid = st.session_state.get("trabajadorid")
    user = st.session_state.get("user_nombre", "Usuario")

    ver_todo = st.toggle("👀 Ver todo el equipo", value=False, help="Activa para mostrar los datos globales del equipo.")
    filtro_trabajador = None if ver_todo else trabajadorid
    st.caption(f"Bienvenido, **{user}** — mostrando datos de {'todo el equipo' if ver_todo else 'tu actividad personal'}.")

    hoy = date.today()
    semana = hoy + timedelta(days=7)
    st.markdown("---")

    # ------------------------------------------------------
    # 1️⃣ KPIs GENERALES
    # ------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)

    def contar(tabla, filtros=None):
        try:
            q = supabase.table(tabla).select("*", count="exact")
            if filtros:
                for k, v in filtros.items():
                    q = q.eq(k, v)
            return getattr(q.execute(), "count", 0) or 0
        except Exception:
            return 0

    presup = contar("presupuesto")
    pedidos = contar("pedido", {"estado_pedidoid": 2})
    acciones = contar("crm_actuacion", {"estado": "Pendiente"})
    incidencias = contar("incidencia", {"estado": "Abierta"})

    col1.metric("💼 Presupuestos", presup)
    col2.metric("📦 Pedidos activos", pedidos)
    col3.metric("🗓️ Acciones pendientes", acciones)
    col4.metric("🚨 Incidencias abiertas", incidencias)
    st.markdown("---")

    # ------------------------------------------------------
    # 2️⃣ CALENDARIO SEMANAL CRM
    # ------------------------------------------------------
    st.subheader("🗓️ Calendario semanal CRM")

    if "dash_week_offset" not in st.session_state:
        st.session_state["dash_week_offset"] = 0

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("◀️ Semana anterior"):
            st.session_state["dash_week_offset"] -= 1
    with nav3:
        if st.button("Semana siguiente ▶️"):
            st.session_state["dash_week_offset"] += 1
    with nav2:
        if st.button("🔄 Semana actual"):
            st.session_state["dash_week_offset"] = 0

    start_week = (datetime.combine(hoy, datetime.min.time()) - timedelta(days=hoy.weekday())) + timedelta(weeks=st.session_state["dash_week_offset"])
    days = [start_week + timedelta(days=i) for i in range(7)]
    st.caption(f"Semana: **{days[0].date().strftime('%d/%m')} — {days[-1].date().strftime('%d/%m')}**")

    try:
        q = supabase.table("crm_actuacion").select(
            "crm_actuacionid, descripcion, canal, estado, fecha_vencimiento, clienteid"
        ).gte("fecha_vencimiento", days[0].date().isoformat()).lte("fecha_vencimiento", days[-1].date().isoformat())
        if not ver_todo and trabajadorid:
            q = q.eq("trabajadorid", trabajadorid)
        acts = q.order("fecha_vencimiento", asc=True).execute().data or []
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar las actuaciones: {e}")
        acts = []

    clientes_map = {}
    try:
        ids = list({a["clienteid"] for a in acts if a.get("clienteid")})
        if ids:
            res = supabase.table("cliente").select("clienteid, razon_social").in_("clienteid", ids).execute()
            clientes_map = {r["clienteid"]: r["razon_social"] for r in res.data}
    except Exception:
        pass

    cols = st.columns(7)
    wd = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    for i, d in enumerate(days):
        with cols[i]:
            st.markdown(f"### {wd[i]} {d.strftime('%d/%m')}")
            daily = [a for a in acts if a.get("fecha_vencimiento", "")[:10] == d.date().isoformat()]
            for a in daily or []:
                cliente = clientes_map.get(a.get("clienteid"), "Sin cliente")
                color = {
                    "Pendiente": WARNING,
                    "En curso": SECONDARY,
                    "Completada": SUCCESS
                }.get(a.get("estado"), "#6b7280")
                st.markdown(
                    f"<div style='border-left:5px solid {color};padding:6px 8px;margin:6px 0;border-radius:6px;background:#f9fafb;'>"
                    f"<b>{a['descripcion']}</b><br><small>{cliente} · {a.get('canal','-')} · {a.get('estado','-')}</small></div>",
                    unsafe_allow_html=True,
                )
            with st.expander("➕ Nueva acción"):
                with st.form(f"form_add_{i}"):
                    desc = st.text_input("Descripción", key=f"desc_{i}")
                    canal = st.selectbox("Canal", ["Teléfono", "Email", "Visita", "Otro"], key=f"canal_{i}")
                    estado = st.selectbox("Estado", ["Pendiente", "En curso", "Completada"], key=f"estado_{i}")
                    clienteid = st.text_input("Cliente ID (opcional)", key=f"cli_{i}")
                    submit = st.form_submit_button("Guardar acción")
                    if submit and desc:
                        try:
                            supabase.table("crm_actuacion").insert({
                                "descripcion": desc,
                                "canal": canal,
                                "estado": estado,
                                "fecha_vencimiento": d.date().isoformat(),
                                "clienteid": int(clienteid) if clienteid else None,
                                "trabajadorid": trabajadorid
                            }).execute()
                            st.success("✅ Acción creada correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

    st.markdown("---")

    # ------------------------------------------------------
    # 3️⃣ ACTIVIDAD + PEDIDOS + INCIDENCIAS
    # ------------------------------------------------------
    st.subheader("📈 Actividad y seguimiento")
    colA, colB = st.columns(2)
    fecha_inicio = (datetime.now() - timedelta(days=30)).date().isoformat()

    with colA:
        try:
            ped = supabase.table("pedido").select("fecha_pedido").gte("fecha_pedido", fecha_inicio).execute().data or []
            pres = supabase.table("presupuesto").select("fecha_presupuesto").gte("fecha_presupuesto", fecha_inicio).execute().data or []
            df_ped, df_pres = pd.DataFrame(ped), pd.DataFrame(pres)
            if not df_ped.empty:
                df_ped["fecha"] = pd.to_datetime(df_ped["fecha_pedido"]).dt.date
            if not df_pres.empty:
                df_pres["fecha"] = pd.to_datetime(df_pres["fecha_presupuesto"]).dt.date
            df = pd.concat([
                df_pres.groupby("fecha").size().rename("Presupuestos"),
                df_ped.groupby("fecha").size().rename("Pedidos")
            ], axis=1).fillna(0).reset_index()
            st.line_chart(df.set_index("fecha"), use_container_width=True)
        except Exception as e:
            st.warning(f"⚠️ Error cargando la gráfica: {e}")

    with colB:
        st.subheader("🚨 Incidencias abiertas")
        try:
            inc = supabase.table("incidencia").select("tipo, descripcion, fecha_creacion").eq("estado", "Abierta").execute().data or []
            if not inc:
                st.success("🎉 No hay incidencias abiertas.")
            else:
                for i in inc[:5]:
                    st.markdown(f"**{i['tipo']}** — {i['descripcion']}  \n📅 {i['fecha_creacion']}")
        except Exception:
            st.warning("⚠️ No se pudieron cargar incidencias.")

    st.markdown("---")

    # ------------------------------------------------------
    # 4️⃣ TOP CLIENTES ACTIVOS
    # ------------------------------------------------------
    st.subheader("🏆 Clientes más activos (últimos 30 días)")
    try:
        ped = supabase.table("pedido").select("clienteid").gte("fecha_pedido", fecha_inicio).execute().data or []
        pres = supabase.table("presupuesto").select("clienteid").gte("fecha_presupuesto", fecha_inicio).execute().data or []
        inc = supabase.table("incidencia").select("clienteid").gte("fecha_creacion", fecha_inicio).execute().data or []
        df_all = pd.concat([pd.DataFrame(ped), pd.DataFrame(pres), pd.DataFrame(inc)], ignore_index=True)
        top = df_all["clienteid"].value_counts().head(5)
        if not top.empty:
            clientes = supabase.table("cliente").select("clienteid, razon_social").in_("clienteid", list(top.index)).execute().data or []
            cmap = {c["clienteid"]: c["razon_social"] for c in clientes}
            for cid, val in top.items():
                nombre = cmap.get(cid, f"Cliente {cid}")
                bar = "█" * int((val / top.max()) * 20)
                st.markdown(f"**{nombre}** — {val} interacciones  \n<span style='color:{SECONDARY}'>{bar}</span>", unsafe_allow_html=True)
        else:
            st.info("Sin actividad reciente de clientes.")
    except Exception as e:
        st.warning(f"⚠️ Error cargando clientes activos: {e}")

    st.markdown("---")

    # ------------------------------------------------------
    # 5️⃣ RANKING DEL EQUIPO
    # ------------------------------------------------------
    st.subheader("🏅 Rendimiento del equipo comercial")
    try:
        pres = supabase.table("presupuesto").select("trabajadorid").execute().data or []
        ped = supabase.table("pedido").select("trabajadorid").execute().data or []
        inc = supabase.table("incidencia").select("responsableid").execute().data or []
        df_pres, df_ped, df_inc = pd.DataFrame(pres), pd.DataFrame(ped), pd.DataFrame(inc)
        ranking = pd.DataFrame({"trabajadorid": []})
        if not df_pres.empty:
            pres_count = df_pres.groupby("trabajadorid").size().rename("Presupuestos").reset_index()
            ranking = pres_count
        if not df_ped.empty:
            ped_count = df_ped.groupby("trabajadorid").size().rename("Pedidos").reset_index()
            ranking = ranking.merge(ped_count, on="trabajadorid", how="outer") if not ranking.empty else ped_count
        if not df_inc.empty:
            inc_count = df_inc.groupby("responsableid").size().rename("Incidencias resueltas").reset_index()
            inc_count = inc_count.rename(columns={"responsableid": "trabajadorid"})
            ranking = ranking.merge(inc_count, on="trabajadorid", how="outer") if not ranking.empty else inc_count

        ranking.fillna(0, inplace=True)
        ranking["Total"] = ranking.sum(axis=1, numeric_only=True)
        trabajadores = supabase.table("trabajador").select("trabajadorid, nombre, apellidos").execute().data or []
        tmap = {t["trabajadorid"]: f"{t['nombre']} {t.get('apellidos','')}" for t in trabajadores}
        ranking["Nombre"] = ranking["trabajadorid"].map(tmap).fillna("—")
        ranking = ranking[["Nombre", "Presupuestos", "Pedidos", "Incidencias resueltas", "Total"]].sort_values("Total", ascending=False)
        st.bar_chart(ranking.set_index("Nombre")[["Presupuestos", "Pedidos", "Incidencias resueltas"]], use_container_width=True)
        st.dataframe(ranking, use_container_width=True)
    except Exception as e:
        st.warning(f"⚠️ No se pudo generar el ranking: {e}")

    # ------------------------------------------------------
    # 6️⃣ DIAGRAMAS
    # ------------------------------------------------------
    st.markdown("---")
    st.subheader("🧭 Arquitectura y relaciones ERP")
    render_diagramas(embed=True)

    st.markdown("---")
    st.caption("© 2025 EnteNova Gnosis · Orbe · Dashboard con modo oscuro, calendario y ranking CRM.")
