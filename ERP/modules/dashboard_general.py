import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from modules.diagramas import render_diagramas
from modules.orbe_palette import PRIMARY, SUCCESS, WARNING, DANGER, SECONDARY

# ======================================================
# 🔧 Helpers visuales
# ======================================================
def _kpi_card(title: str, value: str, subtitle: str = "", color: str = PRIMARY):
    st.markdown(
        f"""
        <div style="
            border-radius: 14px;
            padding: 12px 14px;
            background: #ffffff;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 4px rgba(15,23,42,.06);
            display:flex;
            flex-direction:column;
            gap:4px;
            height:100%;
        ">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#6b7280;">
            {title}
          </div>
          <div style="font-size:26px;font-weight:700;color:#111827;">
            {value}
          </div>
          <div style="font-size:12px;color:#6b7280;">
            {subtitle}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section_title(icon: str, title: str, caption: str | None = None):
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:8px;margin-top:4px;margin-bottom:2px;">
          <div style="font-size:18px;font-weight:600;color:#111827;">{icon} {title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if caption:
        st.caption(caption)


def _safe_date(d):
    if not d:
        return "-"
    if isinstance(d, (date, datetime)):
        return d.strftime("%d/%m/%Y")
    try:
        return date.fromisoformat(str(d)).strftime("%d/%m/%Y")
    except Exception:
        return str(d)


# ======================================================
# 📊 DASHBOARD PRINCIPAL COMERCIAL · EnteNova Gnosis · Orbe
# ======================================================
def render_dashboard(supabase):
    # ------------------------------------------------------
    # 🌙 MODO OSCURO (opcional, pero por defecto blanco corporativo)
    # ------------------------------------------------------
    if "modo_oscuro" not in st.session_state:
        st.session_state["modo_oscuro"] = False

    dark_mode = st.toggle("🌙 Modo oscuro", value=st.session_state["modo_oscuro"], help="Activa una vista nocturna más cómoda.")
    st.session_state["modo_oscuro"] = dark_mode

    if dark_mode:
        st.markdown(
            """
        <style>
        body, .stApp { background-color: #0f172a !important; color: #f1f5f9 !important; }
        div[data-testid="stMarkdownContainer"] p { color: #f8fafc !important; }
        div[data-testid="stMetricValue"] { color: #facc15 !important; }
        .stDataFrame { background-color: #1e293b !important; color: #e2e8f0 !important; }
        </style>
        """,
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------
    # 🧱 ENCABEZADO PRINCIPAL
    # ------------------------------------------------------
    st.markdown(
        f"""
    <div style='background:#ecfdf5;padding:18px 20px;border-radius:12px;border-left:6px solid {PRIMARY};
                margin-bottom:18px;box-shadow:0 1px 3px rgba(0,0,0,0.05);'>
        <h2 style='margin:0;color:#065f46;'>📊 Panel General — EnteNova Gnosis · Orbe</h2>
        <p style='color:#166534;margin-top:4px;'>Resumen comercial, CRM, actividad y servicio.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    trabajadorid = st.session_state.get("trabajadorid")
    user = st.session_state.get("user_nombre", "Usuario")

    ver_todo = st.toggle("👀 Ver todo el equipo", value=False, help="Activa para mostrar los datos globales del equipo.")
    st.caption(f"Bienvenido, **{user}** — mostrando datos de {'todo el equipo' if ver_todo else 'tu actividad personal'}.")

    hoy = date.today()
    fecha_inicio_30 = (datetime.now() - timedelta(days=30)).date()
    fecha_inicio_7 = (datetime.now() - timedelta(days=7)).date()

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
            res = q.execute()
            return getattr(res, "count", 0) or 0
        except Exception:
            return 0

    # pedidos activos = estado_pedidoid 2? (ajustable si cambias el mapping)
    presupuestos_tot = contar("presupuesto")
    pedidos_activos = contar("pedido", {"estado_pedidoid": 2})
    acciones_pend = contar("crm_actuacion", {"estado": "Pendiente"})
    incidencias_abiertas = contar("incidencia", {"estado": "Abierta"})

    with col1:
        _kpi_card("Presupuestos", str(presupuestos_tot), "Total presupuestos registrados.")
    with col2:
        _kpi_card("Pedidos activos", str(pedidos_activos), "Pedidos en estado abierto.", color=SUCCESS)
    with col3:
        _kpi_card("Acciones CRM pendientes", str(acciones_pend), "Actuaciones aún por completar.", color=WARNING)
    with col4:
        _kpi_card("Incidencias abiertas", str(incidencias_abiertas), "Pendientes de resolución.", color=DANGER)

    st.markdown("---")

    # ------------------------------------------------------
    # 2️⃣ CALENDARIO SEMANAL CRM (crm_actuacion)
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

    # Semana actual según offset
    start_week = datetime.combine(hoy, datetime.min.time()) - timedelta(days=hoy.weekday())
    start_week = start_week + timedelta(weeks=st.session_state["dash_week_offset"])
    days = [start_week + timedelta(days=i) for i in range(7)]
    st.caption(f"Semana: **{days[0].date().strftime('%d/%m')} — {days[-1].date().strftime('%d/%m')}**")

    # Cargar actuaciones de la semana
    try:
        q = (
            supabase.table("crm_actuacion")
            .select(
                "crm_actuacionid, descripcion, canal, estado, fecha_vencimiento, fecha_accion, "
                "clienteid, trabajadorid, trabajador_asignadoid"
            )
            .gte("fecha_vencimiento", days[0].date().isoformat())
            .lte("fecha_vencimiento", days[-1].date().isoformat())
            .order("fecha_vencimiento")  # ❗ sin 'asc=True', que es lo que te estaba rompiendo
        )
        acts_data = q.execute().data or []
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar las actuaciones: {e}")
        acts_data = []

    # Filtro por trabajador (si no está activo "ver todo el equipo")
    if not ver_todo and trabajadorid:
        def _visible_for_user(a):
            asignado = a.get("trabajador_asignadoid")
            creador = a.get("trabajadorid")
            return (asignado == trabajadorid) or (asignado is None and creador == trabajadorid)

        acts = [a for a in acts_data if _visible_for_user(a)]
    else:
        acts = acts_data

    # Mapa de clientes
    clientes_map = {}
    try:
        ids = list({a["clienteid"] for a in acts if a.get("clienteid")})
        if ids:
            res = supabase.table("cliente").select("clienteid, razon_social").in_("clienteid", ids).execute()
            clientes_map = {r["clienteid"]: r["razon_social"] for r in res.data}
    except Exception:
        clientes_map = {}

    cols = st.columns(7)
    wd = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    for i, d in enumerate(days):
        with cols[i]:
            st.markdown(f"### {wd[i]} {d.strftime('%d/%m')}")
            daily = [
                a
                for a in acts
                if (a.get("fecha_vencimiento") or "")[:10] == d.date().isoformat()
            ]
            if not daily:
                st.caption("Sin acciones.")
            for a in daily:
                cliente = clientes_map.get(a.get("clienteid"), "Sin cliente")
                color = {
                    "Pendiente": WARNING,
                    "En curso": SECONDARY,
                    "Completada": SUCCESS,
                }.get(a.get("estado"), "#6b7280")
                desc = a.get("descripcion") or a.get("titulo") or "Actuación CRM"
                canal = a.get("canal") or "-"
                estado = a.get("estado") or "-"
                st.markdown(
                    f"<div style='border-left:5px solid {color};padding:6px 8px;margin:6px 0;"
                    f"border-radius:6px;background:#f9fafb;'>"
                    f"<b>{desc}</b><br><small>{cliente} · {canal} · {estado}</small></div>",
                    unsafe_allow_html=True,
                )

            # Formulario rápida "nueva acción" en ese día
            with st.expander("➕ Nueva acción"):
                with st.form(f"form_add_{i}"):
                    desc = st.text_input("Descripción", key=f"desc_{i}")
                    canal = st.selectbox(
                        "Canal",
                        ["Teléfono", "Email", "Videollamada", "Visita", "Otro"],
                        key=f"canal_{i}",
                    )
                    estado = st.selectbox(
                        "Estado",
                        ["Pendiente", "En curso", "Completada"],
                        key=f"estado_{i}",
                    )
                    clienteid_txt = st.text_input("Cliente ID (opcional)", key=f"cli_{i}")
                    submit = st.form_submit_button("Guardar acción")
                    if submit and desc:
                        try:
                            supabase.table("crm_actuacion").insert(
                                {
                                    "descripcion": desc,
                                    "canal": canal,
                                    "estado": estado,
                                    "fecha_vencimiento": d.date().isoformat(),
                                    "fecha_accion": d.date().isoformat(),
                                    "clienteid": int(clienteid_txt) if clienteid_txt else None,
                                    "trabajadorid": trabajadorid,
                                }
                            ).execute()
                            st.success("✅ Acción creada correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

    st.markdown("---")

    # ------------------------------------------------------
    # 3️⃣ ACTIVIDAD: PEDIDOS + PRESUPUESTOS (últimos 30 días)
    # ------------------------------------------------------
    st.subheader("📈 Actividad comercial (últimos 30 días)")
    colA, colB = st.columns(2)

    with colA:
        st.markdown("### 📈 Actividad comercial (últimos 30 días)")

        try:
            # --- Cargar pedidos ---
            ped = (
                supabase.table("pedido")
                .select("fecha_pedido")
                .gte("fecha_pedido", fecha_inicio_30.isoformat())
                .execute()
                .data or []
            )
            df_ped = pd.DataFrame(ped)

            if "fecha_pedido" in df_ped.columns:
                df_ped["fecha"] = pd.to_datetime(df_ped["fecha_pedido"], errors="coerce").dt.date
                df_ped["tipo"] = "Pedidos"
            else:
                df_ped = pd.DataFrame(columns=["fecha", "tipo"])

            # --- Cargar presupuestos ---
            pres = (
                supabase.table("presupuesto")
                .select("fecha_presupuesto")
                .gte("fecha_presupuesto", fecha_inicio_30.isoformat())
                .execute()
                .data or []
            )
            df_pres = pd.DataFrame(pres)

            if "fecha_presupuesto" in df_pres.columns:
                df_pres["fecha"] = pd.to_datetime(df_pres["fecha_presupuesto"], errors="coerce").dt.date
                df_pres["tipo"] = "Presupuestos"
            else:
                df_pres = pd.DataFrame(columns=["fecha", "tipo"])

            # --- Unimos ambos ---
            df_all = pd.concat([df_pres[["fecha", "tipo"]], df_ped[["fecha", "tipo"]]], ignore_index=True)

            # --- Si no hay nada, mensaje profesional ---
            if df_all.empty:
                st.info("No hay actividad de pedidos o presupuestos en los últimos 30 días.")
            else:
                # --- Agrupamos ---
                df_chart = df_all.groupby(["fecha", "tipo"]).size().unstack(fill_value=0)

                # --- Dibujamos ---
                st.line_chart(df_chart, use_container_width=True)

        except Exception as e:
            st.warning(f"⚠️ Error cargando la gráfica: {e}")


        # ---- Presupuestos → Pedidos ----
        st.markdown("### 🔁 Presupuestos convertidos en pedidos")
        try:
            # Pedidos con presupuesto_origenid en los últimos 30 días
            ped_conv = (
                supabase.table("pedido")
                .select("pedidoid, numero, fecha_pedido, presupuesto_origenid, clienteid")
                .gte("fecha_pedido", fecha_inicio_30.isoformat())
                .execute()
                .data
                or []
            )
            ped_conv = [p for p in ped_conv if p.get("presupuesto_origenid")]

            if not ped_conv:
                st.caption("No hay presupuestos convertidos en pedidos en los últimos 30 días.")
            else:
                # Cargar los presupuestos origen para mostrar su número
                pres_ids = list({p["presupuesto_origenid"] for p in ped_conv if p.get("presupuesto_origenid")})
                pres_map_num = {}
                if pres_ids:
                    pres_rows = (
                        supabase.table("presupuesto")
                        .select("presupuestoid, numero, clienteid")
                        .in_("presupuestoid", pres_ids)
                        .execute()
                        .data
                        or []
                    )
                    pres_map_num = {r["presupuestoid"]: r.get("numero") for r in pres_rows}

                # Cargar nombres de cliente
                cli_ids = list({p["clienteid"] for p in ped_conv if p.get("clienteid")})
                cli_map = {}
                if cli_ids:
                    cli_rows = (
                        supabase.table("cliente")
                        .select("clienteid, razon_social")
                        .in_("clienteid", cli_ids)
                        .execute()
                        .data
                        or []
                    )
                    cli_map = {c["clienteid"]: c["razon_social"] for c in cli_rows}

                for p in ped_conv[:5]:
                    num_ped = p.get("numero") or f"PED-{p['pedidoid']}"
                    num_pres = pres_map_num.get(p["presupuesto_origenid"], f"Presupuesto {p['presupuesto_origenid']}")
                    cli = cli_map.get(p.get("clienteid"), "Cliente sin nombre")
                    fecha_ped = _safe_date(p.get("fecha_pedido"))
                    st.markdown(
                        f"• 📦 Pedido **{num_ped}** ({fecha_ped}) — desde **{num_pres}** · {cli}"
                    )
        except Exception as e:
            st.warning(f"⚠️ Error revisando conversión de presupuestos: {e}")

    with colB:
        st.subheader("🚨 Incidencias abiertas")
        try:
            inc = (
                supabase.table("incidencia")
                .select("tipo, descripcion, fecha_creacion, estado")
                .eq("estado", "Abierta")
                .order("fecha_creacion", desc=True)
                .limit(10)
                .execute()
                .data
                or []
            )
            if not inc:
                st.success("🎉 No hay incidencias abiertas.")
            else:
                for i_row in inc:
                    tipo = i_row.get("tipo") or "Incidencia"
                    desc = i_row.get("descripcion") or ""
                    fecha_c = _safe_date(i_row.get("fecha_creacion"))
                    st.markdown(f"**{tipo}** — {desc}  \n📅 {fecha_c}")
        except Exception:
            st.warning("⚠️ No se pudieron cargar incidencias.")

    st.markdown("---")

    # ------------------------------------------------------
    # 4️⃣ TOP CLIENTES ACTIVOS (últimos 30 días)
    # ------------------------------------------------------
    st.subheader("🏆 Clientes más activos (últimos 30 días)")
    try:
        ped = (
            supabase.table("pedido")
            .select("clienteid, fecha_pedido")
            .gte("fecha_pedido", fecha_inicio_30.isoformat())
            .execute()
            .data
            or []
        )
        pres = (
            supabase.table("presupuesto")
            .select("clienteid, fecha_presupuesto")
            .gte("fecha_presupuesto", fecha_inicio_30.isoformat())
            .execute()
            .data
            or []
        )
        inc = (
            supabase.table("incidencia")
            .select("clienteid, fecha_creacion")
            .gte("fecha_creacion", fecha_inicio_30.isoformat())
            .execute()
            .data
            or []
        )

        df_all = pd.concat(
            [pd.DataFrame(ped), pd.DataFrame(pres), pd.DataFrame(inc)], ignore_index=True
        )
        if "clienteid" not in df_all or df_all["clienteid"].isna().all():
            st.info("Sin actividad reciente de clientes.")
        else:
            df_all = df_all[df_all["clienteid"].notna()]
            top = df_all["clienteid"].value_counts().head(5)

            clientes = (
                supabase.table("cliente")
                .select("clienteid, razon_social")
                .in_("clienteid", list(top.index))
                .execute()
                .data
                or []
            )
            cmap = {c["clienteid"]: c["razon_social"] for c in clientes}

            for cid, val in top.items():
                nombre = cmap.get(cid, f"Cliente {cid}")
                bar_len = max(1, int((val / top.max()) * 20))
                bar = "█" * bar_len
                st.markdown(
                    f"**{nombre}** — {val} interacciones  \n"
                    f"<span style='color:{SECONDARY};font-size:12px;'>{bar}</span>",
                    unsafe_allow_html=True,
                )
    except Exception as e:
        st.warning(f"⚠️ Error cargando clientes activos: {e}")

    st.markdown("---")

    # ------------------------------------------------------
    # 5️⃣ DIAGRAMAS · Arquitectura ERP
    # ------------------------------------------------------
    st.subheader("🧭 Arquitectura y relaciones ERP")
    render_diagramas(embed=True)

    st.markdown("---")
    st.caption("© 2025 EnteNova Gnosis · Orbe · Dashboard comercial y CRM.")
