import streamlit as st
import pandas as pd


# ======================================================
# 🔎 DETALLE DE CAMPAÑA
# ======================================================

def render(campaniaid: int):
    st.title("🔎 Detalle de la Campaña")

    if st.button("⬅️ Cancelar y volver"):
        st.session_state["campania_view"] = "lista"
        st.rerun()


    supa = st.session_state["supa"]

    # --------------------------------------------------
    # Cargar campaña
    # --------------------------------------------------
    campania = (
        supa.table("campania")
        .select("*")
        .eq("campaniaid", campaniaid)
        .single()
        .execute()
        .data
    )

    if not campania:
        st.error("No se encontró la campaña.")
        return

    # Cabecera limpia + estado
    col1, col2 = st.columns([4, 1])

    with col1:
        st.header(f"📣 {campania['nombre']}")

    with col2:
        st.markdown(_badge_estado(campania["estado"]), unsafe_allow_html=True)

    # Resumen general rápido
    st.markdown("### 🧾 Resumen")
    colA, colB, colC = st.columns(3)

    with colA:
        st.markdown(f"**Inicio:** {campania['fecha_inicio']}")
        st.markdown(f"**Fin:** {campania['fecha_fin']}")

    with colB:
        st.markdown(f"**Acción:** {campania['tipo_accion']}")
        st.markdown(f"**Objetivo:** {campania.get('objetivo_total') or '—'}")

    with colC:
        st.markdown(f"**Estado:** `{campania['estado']}`")

    st.divider()


    acciones = _fetch_actuaciones_campania(supa, campaniaid)
    df = pd.DataFrame(acciones)

    if df.empty:
        st.warning("Esta campaña aún no tiene actuaciones generadas.")
        return

    # Normalizar fechas
    df["fecha_accion"] = pd.to_datetime(df["fecha_accion"])

    # KPIs rápidos
    total = len(df)
    comp = (df["estado"] == "Completada").sum()
    pend = (df["estado"] == "Pendiente").sum()
    canc = (df["estado"] == "Cancelada").sum()

    st.markdown("### 📊 KPIs generales")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total", total)
    k2.metric("Completadas", comp)
    k3.metric("Pendientes", pend)
    k4.metric("Canceladas", canc)

    st.progress(comp / total if total else 0)
    st.divider()


    # ======================================================
    # TABS
    # ======================================================
    tab1, tab2, tab3 = st.tabs([
        "👤 Por Comercial",
        "🏢 Por Cliente",
        "🕒 Timeline"
    ])

    # ======================================================
    # TAB 1 - POR COMERCIAL
    # ======================================================
    with tab1:
        st.subheader("👤 Actividad por comercial")

        df_trab = df.groupby("trabajadorid").agg(
            nombre=("trabajador_nombre", "first"),
            apellidos=("trabajador_apellidos", "first"),
            total=("crm_actuacionid", "count"),
            completadas=("estado", lambda x: (x == "Completada").sum()),
            pendientes=("estado", lambda x: (x == "Pendiente").sum()),
            canceladas=("estado", lambda x: (x == "Cancelada").sum()),
        ).reset_index()

        df_trab["avance"] = (df_trab["completadas"] / df_trab["total"] * 100).round(1)

        st.dataframe(
            df_trab[["nombre", "apellidos", "total", "completadas", "pendientes", "avance"]],
            hide_index=True,
            use_container_width=True
        )

        st.markdown("#### % Avance por comercial")
        st.bar_chart(df_trab.set_index("nombre")["avance"])


    # ======================================================
    # TAB 2 - POR CLIENTE
    # ======================================================
    with tab2:
        st.subheader("🏢 Actividad por cliente")

        df_cli = df.groupby("clienteid").agg(
            cliente=("cliente_razon_social", "first"),
            total=("crm_actuacionid", "count"),
            completadas=("estado", lambda x: (x == "Completada").sum()),
            pendientes=("estado", lambda x: (x == "Pendiente").sum()),
            canceladas=("estado", lambda x: (x == "Cancelada").sum()),
        ).reset_index()

        df_cli["% avance"] = (
            df_cli["completadas"] / df_cli["total"] * 100
        ).round(2)

        st.dataframe(df_cli)

        st.markdown("### Detalle por cliente")
        cliente_sel = st.selectbox("Selecciona cliente:", df_cli["cliente"].tolist())

        df_det = df[df["cliente_razon_social"] == cliente_sel].sort_values("fecha_accion")

        st.dataframe(
            df_det[[
                "fecha_accion", "estado", "prioridad",
                "trabajador_nombre", "trabajador_apellidos", "resultado"
            ]],
            hide_index=True,
            use_container_width=True
        )

    # ======================================================
    # TAB 3 - TIMELINE
    # ======================================================
    with tab3:
        st.subheader("🕒 Timeline de la campaña")

        df_sorted = df.sort_values("fecha_accion")

        st.markdown("### 🕒 Timeline ordenado")

        for _, row in df_sorted.iterrows():
            st.markdown(f"""
            <div style="padding:10px; border-left:4px solid #4a90e2; margin-bottom:10px; background:#fafafa;">
                <b>{row['fecha_accion'].strftime('%d/%m/%Y %H:%M')}</b> — {row['cliente_razon_social']}<br>
                <span style="color:gray">Comercial:</span> {row['trabajador_nombre']} {row['trabajador_apellidos']}<br>
                <span style="color:gray">Estado:</span> <b>{row['estado']}</b> ·
                <span style="color:gray">Prioridad:</span> <b>{row['prioridad']}</b><br>
                <span style="color:gray">Resultado:</span> {row['resultado'] or '—'}
            </div>
            """, unsafe_allow_html=True)


# ======================================================
# 🔧 HELPERS INTERNOS CORRECTOS
# ======================================================

def _fetch_actuaciones_campania(supa, campaniaid: int):
    """
    Obtiene TODAS las actuaciones de la campaña usando campania_actuacion
    (NO existe columna campaniaid en crm_actuacion).
    """

    # 1. Obtener IDs de actuaciones vinculadas
    rel = (
        supa.table("campania_actuacion")
        .select("actuacionid, clienteid")
        .eq("campaniaid", campaniaid)
        .execute()
    ).data or []

    if not rel:
        return []

    act_ids = [r["actuacionid"] for r in rel]

    # 2. Cargar actuaciones reales
    res = (
        supa.table("crm_actuacion")
        .select(
            """
            crm_actuacionid,
            clienteid,
            trabajadorid,
            estado,
            prioridad,
            fecha_accion,
            resultado,
            cliente (clienteid, razon_social),
            trabajador!crm_actuacion_trabajadorid_fkey (trabajadorid, nombre, apellidos)

            """
        )
        .in_("crm_actuacionid", act_ids)
        .order("fecha_accion")
        .execute()
    )
    data = res.data or []

    # Aplanar
    rows = []
    for a in data:
        rows.append({
            "crm_actuacionid": a["crm_actuacionid"],
            "clienteid": a["clienteid"],
            "cliente_razon_social": a["cliente"]["razon_social"] if a["cliente"] else "",
            "trabajadorid": a["trabajadorid"],
            "trabajador_nombre": a["trabajador"]["nombre"] if a["trabajador"] else "",
            "trabajador_apellidos": a["trabajador"]["apellidos"] if a["trabajador"] else "",
            "estado": a["estado"],
            "prioridad": a["prioridad"],
            "fecha_accion": a["fecha_accion"],  # será convertido a datetime arriba
            "resultado": a.get("resultado"),
        })

    # Ordenamos por fecha antes de devolver
    rows = sorted(rows, key=lambda r: r["fecha_accion"])
    return rows


def _badge_estado(estado: str):
    colores = {
        "borrador": "🟡 Borrador",
        "activa": "🟢 Activa",
        "finalizada": "🔵 Finalizada",
        "cancelada": "🔴 Cancelada",
    }
    txt = colores.get(estado, estado)
    return f"""
    <div style="
        padding:6px 10px;
        background:#f2f2f2;
        border-radius:8px;
        display:inline-block;
        font-weight:600;
    ">
        {txt}
    </div>
    """
