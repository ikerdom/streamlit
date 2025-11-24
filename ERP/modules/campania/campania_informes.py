import streamlit as st
import pandas as pd


# ======================================================
# 📊 INFORMES DE CAMPAÑA
# ======================================================

def render(supa, campaniaid):
    st.title("📊 Informes de campaña")

    # Botón volver
    if st.button("⬅️ Volver al listado"):
        st.session_state["campania_view"] = "lista"
        st.rerun()

    # --------------------------------------------------
    # Cargar información básica de campaña
    # --------------------------------------------------
    campania = (
        supa.table("campania")
        .select("nombre, fecha_inicio, fecha_fin, tipo_accion, estado")
        .eq("campaniaid", campaniaid)
        .single()
        .execute()
        .data
    )

    if campania:
        st.markdown(f"### 📣 {campania['nombre']}")
        st.markdown(
            f"🗓️ **{campania['fecha_inicio']} → {campania['fecha_fin']}** · `{campania['estado']}`"
        )
    else:
        st.warning("No se pudo cargar información de la campaña.")

    st.divider()

    # --------------------------------------------------
    # Cargar actuaciones reales
    # --------------------------------------------------
    acciones = _fetch_actuaciones_campania(supa, campaniaid)

    if not acciones:
        st.warning("Esta campaña aún no tiene actuaciones generadas.")
        return

    df = pd.DataFrame(acciones)

    # ======================================================
    # KPIs GENERALES
    # ======================================================
    st.header("📌 Resumen general")

    total = len(df)
    completadas = (df["estado"] == "Completada").sum()
    pendientes = (df["estado"] == "Pendiente").sum()
    canceladas = (df["estado"] == "Cancelada").sum()

    avance_pct = round((completadas / total) * 100, 1) if total else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total", total)
    k2.metric("Completadas", completadas)
    k3.metric("Pendientes", pendientes)
    k4.metric("Canceladas", canceladas)
    k5.metric("% Avance", f"{avance_pct}%")

    st.progress(avance_pct / 100 if total else 0)

    st.divider()

    # ======================================================
    # RENDIMIENTO POR COMERCIAL
    # ======================================================
    st.subheader("👤 Rendimiento por comercial")

    df_trab = df.groupby("trabajadorid").agg(
        nombre=("trabajador_nombre", "first"),
        apellidos=("trabajador_apellidos", "first"),
        total=("crm_actuacionid", "count"),
        completadas=("estado", lambda x: (x == "Completada").sum()),
        pendientes=("estado", lambda x: (x == "Pendiente").sum()),
    ).reset_index()

    df_trab["avance"] = (
        df_trab["completadas"] / df_trab["total"] * 100
    ).round(1)

    st.dataframe(
        df_trab[["nombre", "apellidos", "total", "completadas", "pendientes", "avance"]],
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "📥 Exportar CSV (Comerciales)",
        df_trab.to_csv(index=False).encode("utf-8"),
        "campania_por_comercial.csv",
        "text/csv",
    )

    st.bar_chart(df_trab.set_index("nombre")["avance"])
    st.divider()

    # ======================================================
    # RENDIMIENTO POR CLIENTE
    # ======================================================
    st.subheader("🏢 Rendimiento por cliente")

    df_cli = df.groupby("clienteid").agg(
        cliente=("cliente_razon_social", "first"),
        total=("crm_actuacionid", "count"),
        completadas=("estado", lambda x: (x == "Completada").sum()),
        pendientes=("estado", lambda x: (x == "Pendiente").sum()),
    ).reset_index()

    df_cli["avance"] = (
        df_cli["completadas"] / df_cli["total"] * 100
    ).round(1)

    st.dataframe(
        df_cli[["cliente", "total", "completadas", "pendientes", "avance"]],
        hide_index=True,
        use_container_width=True,
    )

    st.download_button(
        "📥 Exportar CSV (Clientes)",
        df_cli.to_csv(index=False).encode("utf-8"),
        "campania_por_cliente.csv",
        "text/csv",
    )

    st.divider()

    # ======================================================
    # EVOLUCIÓN TEMPORAL
    # ======================================================
    st.subheader("🗓️ Evolución temporal de actuaciones")

    df["fecha_accion"] = pd.to_datetime(df["fecha_accion"]).dt.date

    df_fecha = df.groupby("fecha_accion").agg(
        total=("crm_actuacionid", "count"),
        completadas=("estado", lambda x: (x == "Completada").sum()),
    ).reset_index()

    st.line_chart(df_fecha.set_index("fecha_accion")[["total", "completadas"]])
    st.divider()

    # ======================================================
    # EMBUDO
    # ======================================================
    st.subheader("🧪 Embudo de conversión")

    funnel = pd.DataFrame({
        "Etapa": ["Generadas", "Pendientes", "Completadas"],
        "Valor": [total, pendientes, completadas],
    }).set_index("Etapa")

    st.bar_chart(funnel)

    st.markdown("""
    **Interpretación:**
    - **Generadas** → Tareas creadas por la campaña  
    - **Pendientes** → Aún no atendidas  
    - **Completadas** → Ejecutadas  
    """)

    st.divider()

    # ======================================================
    # GRUPOS
    # ======================================================
    st.subheader("📚 Actuaciones por grupo de cliente")

    df_grupo = _fetch_por_grupo(supa, campaniaid)

    st.dataframe(df_grupo.sort_values("total", ascending=False), hide_index=True)

    st.download_button(
        "📥 Exportar CSV (Grupos)",
        df_grupo.to_csv(index=False).encode("utf-8"),
        "campania_por_grupo.csv",
        "text/csv",
    )

    st.divider()

    # ======================================================
    # EXPORTACIÓN COMPLETA
    # ======================================================
    st.subheader("📦 Exportación completa del dataset")

    st.download_button(
        "📥 Exportar todo (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        "campania_completa.csv",
        "text/csv",
    )



# ======================================================
# 🔧 HELPERS
# ======================================================

def _fetch_actuaciones_campania(supa, campaniaid: int):
    """
    Carga actuaciones haciendo:
    campania → campania_actuacion → crm_actuacion
    """

    rel = (
        supa.table("campania_actuacion")
        .select("actuacionid, clienteid")
        .eq("campaniaid", campaniaid)
        .execute()
    ).data or []

    if not rel:
        return []

    act_ids = [r["actuacionid"] for r in rel]

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
            "fecha_accion": a["fecha_accion"],
            "resultado": a.get("resultado"),
        })

    rows = sorted(rows, key=lambda r: r["fecha_accion"])
    return rows


def _fetch_por_grupo(supa, campaniaid: int):
    """
    Obtiene total de actuaciones por GRUPO del cliente.
    Requiere la función Postgres: execute_sql(query text)
    """

    sql = f"""
        SELECT 
            COALESCE(g.nombre, 'Sin grupo') AS grupo,
            COUNT(a.crm_actuacionid) AS total
        FROM crm_actuacion a
        JOIN cliente c ON c.clienteid = a.clienteid
        JOIN campania_actuacion ca ON ca.actuacionid = a.crm_actuacionid
        LEFT JOIN grupo g ON g.grupoid = c.grupoid
        WHERE ca.campaniaid = {campaniaid}
        GROUP BY g.nombre
        ORDER BY total DESC;
    """

    try:
        res = supa.rpc("execute_sql", {"query": sql}).execute()
        return pd.DataFrame(res.data or [])
    except Exception as e:
        st.error(f"Error cargando datos por grupo: {e}")
        return pd.DataFrame([])
