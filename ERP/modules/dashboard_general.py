# modules/dashboard_general.py

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date

from modules.orbe_palette import PRIMARY, SUCCESS, WARNING, DANGER, SECONDARY

# ==== Importaciones nuevas y correctas ====
from modules.dashboard.utils import (
    safe_date,
    contar_registros,
)
from modules.dashboard.actuacion_card import render_actuacion_card
from modules.dashboard.actuacion_form import render_actuacion_form
from modules.dashboard.campaign_strip import render_campaign_strip
from modules.dashboard.incidencias_block import render_incidencias_blocks


# ======================================================
# 🔧 KPI CARD
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


# ======================================================
# 📊 DASHBOARD PRINCIPAL
# ======================================================
def render_dashboard(supabase):

    # ------------------------------------------------------
    # 🌙 MODO OSCURO
    # ------------------------------------------------------
    st.session_state.setdefault("modo_oscuro", False)

    dark_mode = st.toggle("🌙 Modo oscuro", st.session_state["modo_oscuro"])
    st.session_state["modo_oscuro"] = dark_mode

    if dark_mode:
        st.markdown(
            """<style>
                body, .stApp { background-color: #0f172a !important; color:#f1f5f9 !important; }
                div[data-testid="stMarkdownContainer"] p { color:#f8fafc !important; }
            </style>""",
            unsafe_allow_html=True,
        )

    # ------------------------------------------------------
    # 🧱 ENCABEZADO
    # ------------------------------------------------------
    st.markdown(
        f"""
        <div style='background:#ecfdf5;padding:18px 20px;border-radius:12px;
                    border-left:6px solid {PRIMARY};margin-bottom:18px;'>
            <h2 style='margin:0;color:#065f46;'>📊 Panel General — EnteNova Gnosis · Orbe</h2>
            <p style='color:#166534;margin-top:4px;'>Resumen comercial, CRM y actividad.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    trabajadorid = st.session_state.get("trabajadorid")
    user = st.session_state.get("user_nombre", "Usuario")

    ver_todo = st.toggle("👀 Ver todo el equipo", False)
    st.caption(
        f"Bienvenido, **{user}** — "
        f"mostrando datos de {'todo el equipo' if ver_todo else 'tu actividad personal'}."
    )

    hoy = date.today()
    fecha_inicio_30 = (datetime.now() - timedelta(days=30)).date()

    # ------------------------------------------------------
    # ESTADO UI
    # ------------------------------------------------------
    st.session_state.setdefault("dash_week_offset", 0)
    st.session_state.setdefault("crm_actuacion_detalle_id", None)
    st.session_state.setdefault("crm_new_act_fecha", None)

    st.markdown("---")

    # ------------------------------------------------------
    # 1️⃣ KPIs
    # ------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        _kpi_card("Presupuestos", contar_registros(supabase, "presupuesto"))
    with c2:
        _kpi_card("Pedidos activos", contar_registros(supabase, "pedido", {"estado_pedidoid": 2}), color=SUCCESS)
    with c3:
        _kpi_card("Acciones CRM pendientes", contar_registros(supabase, "crm_actuacion", {"estado": "Pendiente"}), color=WARNING)
    with c4:
        _kpi_card("Incidencias abiertas", contar_registros(supabase, "incidencia", {"estado": "Abierta"}), color=DANGER)

    st.markdown("---")

    # ------------------------------------------------------
    # 1️⃣ BIS — TIRA DE CAMPAÑAS
    # ------------------------------------------------------
    semana_ini = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=st.session_state["dash_week_offset"])
    semana_fin = semana_ini + timedelta(days=6)

    render_campaign_strip(
        supabase,
        semana_ini=semana_ini,
        semana_fin=semana_fin,
        trabajadorid=trabajadorid,
        ver_todo=ver_todo,
    )

    st.markdown("---")

    # ------------------------------------------------------
    # 2️⃣ CALENDARIO CRM
    # ------------------------------------------------------
    st.subheader("🗓️ Calendario semanal CRM")

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("◀️ Semana anterior"):
            st.session_state["dash_week_offset"] -= 1
            st.session_state["crm_actuacion_detalle_id"] = None
            st.session_state["crm_new_act_fecha"] = None
    with nav3:
        if st.button("Semana siguiente ▶️"):
            st.session_state["dash_week_offset"] += 1
            st.session_state["crm_actuacion_detalle_id"] = None
            st.session_state["crm_new_act_fecha"] = None
    with nav2:
        if st.button("🔄 Semana actual"):
            st.session_state["dash_week_offset"] = 0
            st.session_state["crm_actuacion_detalle_id"] = None
            st.session_state["crm_new_act_fecha"] = None

    # Fechas reales de la semana
    semana_ini = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=st.session_state["dash_week_offset"])
    semana_fin = semana_ini + timedelta(days=6)
    days = [semana_ini + timedelta(days=i) for i in range(7)]

    st.caption(f"Semana: **{semana_ini.strftime('%d/%m')} — {semana_fin.strftime('%d/%m')}**")

    # ------------------------------------------------------
    # Cargar actuaciones
    # ------------------------------------------------------
    try:
        q = (
            supabase.table("crm_actuacion")
            .select(
                "crm_actuacionid, descripcion, canal, estado, fecha_vencimiento, fecha_accion, "
                "clienteid, trabajadorid, trabajador_asignadoid, prioridad, titulo, hora_inicio, "
                "hora_fin, duracion_segundos, campaniaid"
            )
            .gte("fecha_vencimiento", semana_ini.isoformat())
            .lte("fecha_vencimiento", semana_fin.isoformat())
            .order("fecha_vencimiento")
        )
        acts_data = q.execute().data or []
    except Exception as e:
        st.error(f"No se pudieron cargar las actuaciones: {e}")
        acts_data = []

    # Filtro por trabajador
    if not ver_todo and trabajadorid:
        def visible(a):
            return (
                a.get("trabajador_asignadoid") == trabajadorid
                or (a.get("trabajador_asignadoid") is None and a.get("trabajadorid") == trabajadorid)
            )

        acts = [a for a in acts_data if visible(a)]
    else:
        acts = acts_data

    # ------------------------------------------------------
    # Cargar nombres de clientes
    # ------------------------------------------------------
    clientes_map = {}
    try:
        ids = {a["clienteid"] for a in acts if a.get("clienteid")}
        if ids:
            rows = (
                supabase.table("cliente")
                .select("clienteid, razon_social")
                .in_("clienteid", list(ids))
                .execute()
                .data
            )
            clientes_map = {r["clienteid"]: r["razon_social"] for r in rows}
    except:
        clientes_map = {}

    # ------------------------------------------------------
    # Diseño: calendario + panel lateral
    # ------------------------------------------------------
    col_cal, col_side = st.columns([4, 1])

    # -------- LATERAL --------
    with col_side:
        st.markdown("### 👤 Resumen semanal")
        if not acts:
            st.caption("Sin actuaciones.")
        else:
            total = len(acts)
            por_estado = {}
            for a in acts:
                est = a.get("estado", "-")
                por_estado[est] = por_estado.get(est, 0) + 1

            st.write(f"**Total:** {total}")
            for est, n in por_estado.items():
                st.write(f"- **{est}**: {n}")

    # -------- CALENDARIO --------
    with col_cal:
        wd = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        cols = st.columns(7)

        for i, d in enumerate(days):
            with cols[i]:
                st.markdown(f"### {wd[i]} {d.strftime('%d/%m')}")
                daily = [a for a in acts if (a.get("fecha_vencimiento") or "")[:10] == d.isoformat()]

                if not daily:
                    st.caption("Sin acciones.")

                for a in daily:
                    cliente = clientes_map.get(a.get("clienteid"), "Sin cliente")
                    clicked_view, clicked_complete = render_actuacion_card(a, cliente)

                    if clicked_view:
                        st.session_state["crm_actuacion_detalle_id"] = a["crm_actuacionid"]
                        st.session_state["crm_new_act_fecha"] = None
                        st.rerun()

                    if clicked_complete:
                        try:
                            supabase.table("crm_actuacion").update(
                                {"estado": "Completada", "fecha_accion": date.today().isoformat()}
                            ).eq("crm_actuacionid", a["crm_actuacionid"]).execute()
                            st.success("Actuación completada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al completar: {e}")

                # Crear nueva actuación
                if st.button("➕ Nueva acción", key=f"new_{i}"):
                    st.session_state["crm_new_act_fecha"] = d.isoformat()
                    st.session_state["crm_actuacion_detalle_id"] = None
                    st.rerun()

    # ------------------------------------------------------
    # PANEL DE DETALLE/ALTA (parte inferior)
    # ------------------------------------------------------
    act_det = None
    if st.session_state["crm_actuacion_detalle_id"]:
        act_det = next(
            (x for x in acts if x["crm_actuacionid"] == st.session_state["crm_actuacion_detalle_id"]),
            None,
        )

    fecha_default = None
    if st.session_state["crm_new_act_fecha"]:
        try:
            fecha_default = date.fromisoformat(st.session_state["crm_new_act_fecha"])
        except:
            fecha_default = date.today()

    if act_det or fecha_default:
        render_actuacion_form(supabase, act_det, fecha_default)

    st.markdown("---")

    # ------------------------------------------------------
    # 3️⃣ ACTIVIDAD · GRÁFICAS
    # ------------------------------------------------------
    st.subheader("📈 Actividad comercial (últimos 30 días)")
    colA, colB = st.columns(2)

    # -------- Gráficas principales --------
    with colA:
        try:
            ped = supabase.table("pedido").select("fecha_pedido").gte("fecha_pedido", fecha_inicio_30.isoformat()).execute().data or []
            pres = supabase.table("presupuesto").select("fecha_presupuesto").gte("fecha_presupuesto", fecha_inicio_30.isoformat()).execute().data or []
            acts30 = supabase.table("crm_actuacion").select("fecha_accion, estado").gte("fecha_accion", fecha_inicio_30.isoformat()).eq("estado", "Completada").execute().data or []

            df_ped = pd.DataFrame(ped)
            df_pres = pd.DataFrame(pres)
            df_acts = pd.DataFrame(acts30)

            if not df_ped.empty:
                df_ped["fecha"] = pd.to_datetime(df_ped["fecha_pedido"]).dt.date
                df_ped["tipo"] = "Pedidos"

            if not df_pres.empty:
                df_pres["fecha"] = pd.to_datetime(df_pres["fecha_presupuesto"]).dt.date
                df_pres["tipo"] = "Presupuestos"

            if not df_acts.empty:
                df_acts["fecha"] = pd.to_datetime(df_acts["fecha_accion"]).dt.date
                df_acts["tipo"] = "Acciones CRM"

            df_all = pd.concat(
                [
                    df_ped[["fecha", "tipo"]],
                    df_pres[["fecha", "tipo"]],
                    df_acts[["fecha", "tipo"]],
                ],
                ignore_index=True,
            )

            if df_all.empty:
                st.info("No hay actividad reciente.")
            else:
                df_chart = df_all.groupby(["fecha", "tipo"]).size().unstack(fill_value=0)
                st.line_chart(df_chart, use_container_width=True)

        except Exception as e:
            st.error(f"Error gráfico: {e}")

        # Gráfico estados CRM
        st.markdown("### 🎯 Estado de acciones CRM (últimos 30 días)")
        try:
            rows = (
                supabase.table("crm_actuacion")
                .select("estado")
                .gte("fecha_accion", fecha_inicio_30.isoformat())
                .execute()
                .data
            )
            df_est = pd.DataFrame(rows)
            if df_est.empty:
                st.caption("Sin acciones CRM.")
            else:
                df_cnt = df_est["estado"].value_counts()
                st.bar_chart(df_cnt)
        except:
            st.caption("Error cargando datos.")

        # ---- Presupuestos → Pedidos ----
        st.markdown("### 🔁 Presupuestos convertidos en pedidos")
        try:
            ped_conv = (
                supabase.table("pedido")
                .select("pedidoid, numero, fecha_pedido, presupuesto_origenid, clienteid")
                .gte("fecha_pedido", fecha_inicio_30.isoformat())
                .execute()
                .data
            )

            ped_conv = [p for p in ped_conv if p.get("presupuesto_origenid")]

            if not ped_conv:
                st.caption("Sin conversiones.")
            else:
                pres_ids = list({p["presupuesto_origenid"] for p in ped_conv})
                pres_rows = (
                    supabase.table("presupuesto")
                    .select("presupuestoid, numero, clienteid")
                    .in_("presupuestoid", pres_ids)
                    .execute()
                    .data
                )
                pres_map = {r["presupuestoid"]: r["numero"] for r in pres_rows}

                cli_ids = list({p["clienteid"] for p in ped_conv})
                cli_rows = (
                    supabase.table("cliente")
                    .select("clienteid, razon_social")
                    .in_("clienteid", cli_ids)
                    .execute()
                    .data
                )
                cli_map = {c["clienteid"]: c["razon_social"] for c in cli_rows}

                for p in ped_conv[:5]:
                    st.markdown(
                        f"• **Pedido {p['numero']}** → presupuesto {pres_map.get(p['presupuesto_origenid'],'-')} · {cli_map.get(p['clienteid'],'-')}"
                    )

        except Exception as e:
            st.error(f"Error en conversiones: {e}")

    # -------- INCIDENCIAS --------
    with colB:
        render_incidencias_blocks(supabase, trabajadorid)

    st.markdown("---")
    st.caption("© 2025 EnteNova Gnosis · Orbe — Dashboard comercial y CRM")
