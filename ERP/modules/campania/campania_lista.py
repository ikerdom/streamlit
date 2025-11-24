import streamlit as st
from datetime import date


# ======================================================
# 📣 LISTADO DE CAMPAÑAS — modo real sin utils
# ======================================================

def render(supabase):

    st.title("📣 Campañas comerciales")
    st.caption("Gestiona campañas, consulta su progreso y accede a informes.")
    st.divider()

    # ======================================================
    # ➕ NUEVA CAMPAÑA
    # ======================================================
    if st.button("➕ Crear nueva campaña", use_container_width=True):
        st.session_state["campaniaid"] = None
        st.session_state["campania_step"] = 1
        st.session_state["campania_view"] = "form"
        st.rerun()

    # ======================================================
    # 🎛️ FILTROS AVANZADOS
    # ======================================================
    with st.expander("🎛️ Filtros avanzados", expanded=False):

        c1, c2 = st.columns(2)
        with c1:
            estados = ["Todos", "borrador", "activa", "pausada", "finalizada", "cancelada"]
            estado_sel = st.selectbox("Estado", estados)

        with c2:
            tipos = ["Todos", "llamada", "email", "whatsapp", "visita"]
            tipo_sel = st.selectbox("Tipo de acción", tipos)

        nombre_busqueda = st.text_input("Buscar por nombre o descripción", "")

        c3, c4 = st.columns(2)
        with c3:
            fecha_min = st.date_input("Fecha inicio mínima", value=None)
        with c4:
            fecha_max = st.date_input("Fecha fin máxima", value=None)

        progreso_min = st.slider(
            "Progreso mínimo (%)",
            0, 100, 0
        )

        if st.button("🔄 Limpiar filtros"):
            st.session_state.pop("filtros", None)
            st.rerun()

    # ======================================================
    # 🔄 CARGA DE CAMPAÑAS
    # ======================================================
    try:
        resp = (
            supabase.table("campania")
            .select("*")
            .order("fecha_inicio", desc=True)
            .execute()
        )
        campanias = resp.data or []
    except Exception as e:
        st.error(f"❌ Error cargando campañas: {e}")
        return

    # ======================================================
    # 🧹 APLICAR FILTROS
    # ======================================================

    def aplicar_filtros(c):
        # Estado
        if estado_sel != "Todos" and c["estado"] != estado_sel:
            return False

        # Tipo
        if tipo_sel != "Todos" and c["tipo_accion"] != tipo_sel:
            return False

        # Búsqueda
        if nombre_busqueda:
            txt = f"{c['nombre']} {c.get('descripcion','')}".lower()
            if nombre_busqueda.lower() not in txt:
                return False

        # Fechas
        if fecha_min and c["fecha_inicio"] < fecha_min.isoformat():
            return False

        if fecha_max and c["fecha_fin"] > fecha_max.isoformat():
            return False

        return True

    campanias = [c for c in campanias if aplicar_filtros(c)]

    if not campanias:
        st.info("📭 No hay campañas que coincidan con los filtros.")
        return

    # ======================================================
    # BADGES
    # ======================================================
    BADGE = {
        "borrador": "🟡 Borrador",
        "activa": "🟢 Activa",
        "pausada": "⏸️ Pausada",
        "finalizada": "🔵 Finalizada",
        "cancelada": "🔴 Cancelada",
    }

    st.subheader("📋 Listado de campañas")
    st.write("")

    # ======================================================
    # 🧱 RENDER DEL LISTADO
    # ======================================================
    for camp in campanias:

        with st.container(border=True):

            col1, col2, col3, col4 = st.columns([4, 2, 2, 2])

            # --------------------------------------------------
            # 📝 Columna 1 — Datos generales
            # --------------------------------------------------
            with col1:
                st.markdown(f"### {camp['nombre']}")
                st.write(camp.get("descripcion") or "—")

                st.write(f"📅 *{camp['fecha_inicio']} → {camp['fecha_fin']}*")
                st.write(f"🏷️ Tipo: **{camp['tipo_accion']}**")

            # --------------------------------------------------
            # 🔖 Columna 2 — Estado + Acciones administrativas
            # --------------------------------------------------
            with col2:
                st.write("### Estado")
                estado = camp["estado"]
                st.markdown(f"**{BADGE.get(estado, estado)}**")

                # 🎛 Acciones de estado
                if estado in ["borrador", "activa", "pausada"]:
                    if st.button("🔵 Finalizar", key=f"fin_{camp['campaniaid']}"):
                        supabase.table("campania").update({"estado": "finalizada"}) \
                            .eq("campaniaid", camp["campaniaid"]).execute()
                        st.rerun()

                    if st.button("🔴 Cancelar", key=f"can_{camp['campaniaid']}"):
                        supabase.table("campania").update({"estado": "cancelada"}) \
                            .eq("campaniaid", camp["campaniaid"]).execute()
                        st.rerun()

                # Reabrir si está cerrada
                if estado in ["cancelada", "finalizada"]:
                    if st.button("♻️ Reabrir", key=f"open_{camp['campaniaid']}"):
                        nuevo_estado = "activa" if estado == "finalizada" else "pausada"
                        supabase.table("campania").update({"estado": nuevo_estado}) \
                            .eq("campaniaid", camp["campaniaid"]).execute()
                        st.rerun()

            # --------------------------------------------------
            # 📊 Columna 3 — Progreso CRM real
            # --------------------------------------------------
            with col3:
                try:
                    rel = (
                        supabase.table("campania_actuacion")
                        .select("actuacionid")
                        .eq("campaniaid", camp["campaniaid"])
                        .execute()
                    ).data or []

                    act_ids = [r["actuacionid"] for r in rel]

                    if act_ids:
                        acc = (
                            supabase.table("crm_actuacion")
                            .select("estado")
                            .in_("crm_actuacionid", act_ids)
                            .execute()
                        ).data or []
                    else:
                        acc = []

                except:
                    acc = []

                total = len(acc)
                completadas = sum(1 for a in acc if a["estado"] == "Completada")
                pct = int((completadas / total) * 100) if total else 0

                st.write("### 📊 Progreso")
                st.write(f"Total: **{total}**")
                st.write(f"Completadas: **{completadas}**")
                st.progress(pct / 100 if total else 0)
                st.caption(f"{pct}% completado")

            # --------------------------------------------------
            # ⚙️ Columna 4 — Acciones de navegación
            # --------------------------------------------------
            with col4:
                st.write("### Opciones")

                if st.button("📄 Detalle", key=f"detalle_{camp['campaniaid']}"):
                    st.session_state["campaniaid"] = camp["campaniaid"]
                    st.session_state["campania_view"] = "detalle"
                    st.rerun()

                if st.button("✏️ Editar", key=f"edit_{camp['campaniaid']}"):
                    st.session_state["campaniaid"] = camp["campaniaid"]
                    st.session_state["campania_step"] = 1
                    st.session_state["campania_view"] = "form"
                    st.rerun()

                if st.button("📈 Progreso", key=f"prog_{camp['campaniaid']}"):
                    st.session_state["campaniaid"] = camp["campaniaid"]
                    st.session_state["campania_view"] = "progreso"
                    st.rerun()

                if st.button("📊 Informes", key=f"inf_{camp['campaniaid']}"):
                    st.session_state["campaniaid"] = camp["campaniaid"]
                    st.session_state["campania_view"] = "informes"
                    st.rerun()

                # 📑 Clonar campaña
                if st.button("📑 Clonar", key=f"clone_{camp['campaniaid']}"):

                    clone = {
                        "nombre": camp["nombre"] + " (copia)",
                        "descripcion": camp["descripcion"],
                        "tipo_accion": camp["tipo_accion"],
                        "fecha_inicio": camp["fecha_inicio"],
                        "fecha_fin": camp["fecha_fin"],
                        "estado": "borrador",
                    }

                    try:
                        new = supabase.table("campania").insert(clone).execute()

                        if new.data:
                            new_id = new.data[0]["campaniaid"]

                            supabase.rpc(
                                "clonar_campania_segmentacion",
                                {"old_id": camp["campaniaid"], "new_id": new_id}
                            ).execute()

                            st.success("Campaña clonada correctamente.")
                            st.session_state["campaniaid"] = new_id
                            st.session_state["campania_view"] = "form"
                            st.rerun()

                    except Exception as e:
                        st.error(f"❌ Error al clonar: {e}")

        st.write("")  # separación visual
