import streamlit as st
import pandas as pd
from datetime import date


# ======================================================
# 📈 PROGRESO DE CAMPAÑA
# ======================================================

def render():
    # Cabecera principal
    st.title("📈 Progreso de campaña")

    if st.button("⬅️ Volver al listado"):
        st.session_state["campania_view"] = "lista"
        st.rerun()


    # Datos de campaña
    supa = st.session_state["supa"]

    if "campaniaid" not in st.session_state:
        st.error("No se ha seleccionado ninguna campaña.")
        return

    campaniaid = st.session_state["campaniaid"]

    campania = (
        supa.table("campania")
        .select("nombre, descripcion, fecha_inicio, fecha_fin, estado")
        .eq("campaniaid", campaniaid)
        .single()
        .execute()
        .data
    )

    if not campania:
        st.error("Campaña no encontrada.")
        return

    # Cabecera compacta estilo ERP
    st.header(f"📣 {campania['nombre']}")
    st.markdown(f"🗓️ **{campania['fecha_inicio']} → {campania['fecha_fin']}**")
    st.markdown(_badge_estado(campania["estado"]), unsafe_allow_html=True)
    st.markdown(campania["descripcion"] or "—")
    st.divider()

    # -----------------------------------------
    # Acciones CRM vinculadas REALMENTE
    # -----------------------------------------
    acciones = _fetch_acciones(supa, campaniaid)

    if not acciones:
        st.warning("La campaña aún no tiene actuaciones generadas.")
        return

    df = pd.DataFrame(acciones)
    # -----------------------------------------
    # Filtros
    # -----------------------------------------
    st.subheader("🔍 Filtros")

    f1, f2, f3, f4 = st.columns([2, 2, 2, 1])

    with f1:
        estado_sel = st.selectbox(
            "Estado",
            ["Todos"] + sorted(df["estado"].unique().tolist())
        )

    with f2:
        comercial_sel = st.selectbox(
            "Comercial",
            ["Todos"] + sorted(df["trabajador"].unique().tolist())
        )

    with f3:
        cliente_sel = st.selectbox(
            "Cliente",
            ["Todos"] + sorted(df["cliente"].unique().tolist())
        )

    with f4:
        st.write("")  # Espaciado
        st.write("")  # Espaciado
        if st.button("🔄 Limpiar filtros"):
            st.rerun()

    df_view = df.copy()

    if estado_sel != "Todos":
        df_view = df_view[df_view["estado"] == estado_sel]

    if comercial_sel != "Todos":
        df_view = df_view[df_view["trabajador"] == comercial_sel]

    if cliente_sel != "Todos":
        df_view = df_view[df_view["cliente"] == cliente_sel]
    # -----------------------------------------
    # Métricas globales
    # -----------------------------------------
    st.subheader("📊 Métricas globales")

    total = len(df)
    comp = (df["estado"] == "Completada").sum()
    pend = (df["estado"] == "Pendiente").sum()
    canc = (df["estado"] == "Cancelada").sum()
    avance = round((comp / total) * 100, 1) if total else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total", total)
    m2.metric("Completadas", comp)
    m3.metric("Pendientes", pend)
    m4.metric("Canceladas", canc)
    m5.metric("% Avance", f"{avance}%")

    st.progress(comp / total if total else 0)


    # ------------------------
    # TABLA
    # ------------------------
    st.subheader("📋 Actuaciones filtradas")

    st.dataframe(
        df_view,
        use_container_width=True,
        hide_index=True
    )
    st.caption(f"Mostrando {len(df_view)} de {total} actuaciones")

    # ======================================================
    # 🛠 Acciones masivas
    # ======================================================
    st.divider()
    st.subheader("🛠 Acciones masivas sobre actuaciones")

    ids_disponibles = df_view["crm_actuacionid"].tolist()

    seleccion = st.multiselect(
        "Selecciona actuaciones a modificar",
        ids_disponibles
    )

    if not seleccion:
        st.info("Selecciona tareas para aplicar acciones.")
        return

    st.success(f"{len(seleccion)} actuaciones seleccionadas.")

    # ---- Acciones por columnas ----
    ac1, ac2 = st.columns(2)

    with ac1:
        if st.button("✔ Marcar como completadas"):
            _bulk_update_estado(supa, seleccion, "Completada")
            st.rerun()

        if st.button("❌ Cancelar actuaciones seleccionadas"):
            _bulk_update_estado(supa, seleccion, "Cancelada")
            st.rerun()

    with ac2:
        trabajadores = st.session_state.get("all_trabajadores", [])
        mapa_trab = {
            f"{t['nombre']} {t['apellidos']}": t["trabajadorid"]
            for t in trabajadores
        }

        nuevo = st.selectbox("Reasignar comercial a:", ["—"] + list(mapa_trab.keys()))

        if nuevo != "—" and st.button("🔄 Reasignar"):
            _bulk_update_comercial(supa, seleccion, mapa_trab[nuevo])
            st.rerun()

    st.divider()

    # ---- Reprogramación ----
    st.subheader("📅 Reprogramar fecha")

    ac3, ac4 = st.columns([2, 1])

    with ac3:
        nueva_f = st.date_input("Nueva fecha", date.today())

    with ac4:
        if st.button("Aplicar fecha"):
            _bulk_update_fecha(supa, seleccion, str(nueva_f))
            st.rerun()

    st.divider()

    # ---- Resultado ----
    st.subheader("📝 Añadir resultado")

    resultado = st.text_input("Texto del resultado")

    if resultado and st.button("Guardar resultado"):
        _bulk_update_resultado(supa, seleccion, resultado)
        st.rerun()



# ======================================================
# 🔧 HELPERS — RELACIÓN REAL campania → campania_actuacion → crm_actuacion
# ======================================================

def _fetch_acciones(supa, campaniaid: int):
    """
    1. Saco ID de actuaciones desde campania_actuacion
    2. Cargo info completa desde crm_actuacion
    """

    rel = (
        supa.table("campania_actuacion")
        .select("actuacionid")
        .eq("campaniaid", campaniaid)
        .execute()
        .data
    )

    if not rel:
        return []

    ids = [r["actuacionid"] for r in rel]

    q = (
        supa.table("crm_actuacion")
        .select("""
            crm_actuacionid,
            estado,
            fecha_accion,
            resultado,
            prioridad,
            cliente (clienteid, razon_social),
            trabajador!crm_actuacion_trabajadorid_fkey (trabajadorid, nombre, apellidos)

        """)
        .in_("crm_actuacionid", ids)
        .order("fecha_accion")
        .execute()
        .data
    )

    rows = []
    for a in q:
        rows.append({
            "crm_actuacionid": a["crm_actuacionid"],
            "estado": a["estado"],
            "fecha_accion": a["fecha_accion"],
            "resultado": a["resultado"],
            "prioridad": a["prioridad"],
            "cliente": a["cliente"]["razon_social"] if a["cliente"] else "—",
            "trabajador": (
                f"{a['trabajador']['nombre']} {a['trabajador']['apellidos']}"
                if a["trabajador"] else "—"
            )
        })

    # Orden final por fecha
    rows = sorted(rows, key=lambda r: r["fecha_accion"])
    return rows


# ======================================================
# 🔧 UPDATES MASIVOS
# ======================================================

def _bulk_update_estado(supa, ids, estado):
    supa.table("crm_actuacion").update({"estado": estado}).in_("crm_actuacionid", ids).execute()

def _bulk_update_comercial(supa, ids, trabajadorid):
    supa.table("crm_actuacion").update({"trabajadorid": trabajadorid}).in_("crm_actuacionid", ids).execute()

def _bulk_update_fecha(supa, ids, fecha):
    supa.table("crm_actuacion").update({"fecha_accion": fecha}).in_("crm_actuacionid", ids).execute()

def _bulk_update_resultado(supa, ids, texto):
    supa.table("crm_actuacion").update({"resultado": texto}).in_("crm_actuacionid", ids).execute()


# ======================================================
# 🔧 BADGE DE ESTADO
# ======================================================

def _badge_estado(estado):
    colores = {
        "borrador": "🟡 Borrador",
        "activa": "🟢 Activa",
        "pausada": "🟠 Pausada",
        "finalizada": "🔵 Finalizada",
        "cancelada": "🔴 Cancelada",
    }
    txt = colores.get(estado, estado)
    return f"""<div style="padding:6px 12px;background:#eee;border-radius:8px;display:inline-block;">{txt}</div>"""
