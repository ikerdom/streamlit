import streamlit as st
from datetime import date, datetime, timedelta, time

# ======================================================
# 📣 CREAR / EDITAR CAMPAÑA COMERCIAL
# ======================================================

def render(supabase):
    # --------------------------------------------------
    # Contexto / estado base
    # --------------------------------------------------
    campaniaid = st.session_state.get("campaniaid")
    campania = None

    # Breadcrumb para topbar (si lo usas allí)
    st.session_state["menu_campanias"] = (
        "Nueva campaña" if campaniaid is None else "Editar campaña"
    )

    st.title("📣 Crear / Editar campaña comercial")

    # Botón global para volver al listado
    if st.button("⬅️ Cancelar y volver al listado", use_container_width=True):
        st.session_state["campania_view"] = "lista"
        st.session_state["campania_step"] = 1
        st.session_state["campaniaid"] = None
        st.rerun()

    # ---------------------------
    # Identificar campaña actual
    # ---------------------------
    if campaniaid:
        try:
            res = (
                supabase.table("campania")
                .select("*")
                .eq("campaniaid", campaniaid)
                .single()
                .execute()
            )
            campania = res.data
        except Exception as e:
            st.error(f"Error cargando campaña: {e}")
            campania = None
    else:
        campania = None

    # Si la campaña está cerrada, no se edita aquí
    if campania and campania.get("estado") in ["finalizada", "cancelada"]:
        st.info("Esta campaña está cerrada. Solo puedes consultar detalle / informes.")
        return

    # ---------------------------
    # Control de pasos del wizard
    # ---------------------------
    step = st.session_state.get("campania_step", 1)
    if step not in (1, 2, 3):
        step = 1
        st.session_state["campania_step"] = 1

    st.sidebar.title("Pasos campaña")
    st.sidebar.write("1️⃣ Datos generales")
    st.sidebar.write("2️⃣ Segmentación")
    st.sidebar.write("3️⃣ Confirmación")

    if step == 1:
        step1_datos_generales(supabase, campania, campaniaid)
    elif step == 2:
        step2_segmentacion(supabase, campania, campaniaid)
    elif step == 3:
        step3_confirmacion(supabase, campania, campaniaid)


# ======================================================
# 🧩 PASO 1 · DATOS GENERALES
# ======================================================

def step1_datos_generales(supabase, campania, campaniaid):
    st.header("1️⃣ Datos generales de la campaña")

    nombre = st.text_input(
        "Nombre de la campaña",
        value=(campania.get("nombre") if campania else "") or "",
    )

    descripcion = st.text_area(
        "Descripción",
        value=(campania.get("descripcion") if campania else "") or "",
        placeholder="Ejemplo: Campaña de llamadas a centros de formación…",
    )

    col1, col2 = st.columns(2)

    with col1:
        fi_default = date.today()
        if campania and campania.get("fecha_inicio"):
            try:
                fi_default = date.fromisoformat(str(campania["fecha_inicio"]))
            except Exception:
                pass

        fecha_inicio = st.date_input("Fecha inicio", value=fi_default)

    with col2:
        ff_default = fi_default
        if campania and campania.get("fecha_fin"):
            try:
                ff_default = date.fromisoformat(str(campania["fecha_fin"]))
            except Exception:
                pass

        fecha_fin = st.date_input("Fecha fin", value=ff_default)

    tipos = ["llamada", "email", "whatsapp", "visita"]
    if campania and campania.get("tipo_accion") in tipos:
        idx = tipos.index(campania["tipo_accion"])
    else:
        idx = 0

    tipo_accion = st.selectbox(
        "Tipo de acción principal",
        tipos,
        index=idx,
    )

    objetivo_total = st.number_input(
        "Número total de acciones objetivo (opcional)",
        min_value=0,
        value=int(campania.get("objetivo_total") or 0) if campania else 0,
    )

    notas = st.text_area(
        "Notas internas",
        value=(campania.get("notas") if campania else "") or "",
    )

    st.divider()

    colA, colB, colC = st.columns(3)

    # Volver al listado
    with colA:
        if st.button("⬅️ Volver al listado"):
            st.session_state["campania_step"] = 1
            st.session_state["campaniaid"] = None
            st.session_state["campania_view"] = "lista"
            st.session_state["menu_campanias"] = None
            st.rerun()

    # Guardar y seguir
    with colB:
        if st.button("➡️ Siguiente: segmentación"):
            ok, msg = _validar_fechas(fecha_inicio, fecha_fin)
            if not ok:
                st.error(msg)
                return

            payload = {
                "nombre": nombre.strip(),
                "descripcion": descripcion.strip() or None,
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
                "tipo_accion": tipo_accion,
                "objetivo_total": objetivo_total or None,
                "notas": notas.strip() or None,
            }

            # Crear o actualizar
            if campaniaid:
                supabase.table("campania").update(payload).eq(
                    "campaniaid", campaniaid
                ).execute()
            else:
                payload.setdefault("estado", "borrador")
                res = supabase.table("campania").insert(payload).execute()
                if res.data:
                    campaniaid = res.data[0]["campaniaid"]
                    st.session_state["campaniaid"] = campaniaid

            st.session_state["campania_step"] = 2
            st.rerun()

    # Guardar y quedarse
    with colC:
        if st.button("💾 Guardar borrador"):
            ok, msg = _validar_fechas(fecha_inicio, fecha_fin)
            if not ok:
                st.error(msg)
                return

            payload = {
                "nombre": nombre.strip(),
                "descripcion": descripcion.strip() or None,
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
                "tipo_accion": tipo_accion,
                "objetivo_total": objetivo_total or None,
                "notas": notas.strip() or None,
                "estado": (campania.get("estado") if campania else "borrador") or "borrador",
            }

            if campaniaid:
                supabase.table("campania").update(payload).eq(
                    "campaniaid", campaniaid
                ).execute()
                st.success("Campaña actualizada.")
            else:
                res = supabase.table("campania").insert(payload).execute()
                if res.data:
                    st.session_state["campaniaid"] = res.data[0]["campaniaid"]
                st.success("Campaña creada como borrador.")

            st.rerun()


# ======================================================
# 🧩 PASO 2 · SEGMENTACIÓN
# ======================================================

def step2_segmentacion(supabase, campania, campaniaid):
    st.header("2️⃣ Segmentación de la campaña")

    if not campaniaid:
        st.error("Primero guarda los datos generales de la campaña (Paso 1).")
        if st.button("⬅️ Ir a datos generales"):
            st.session_state["campania_step"] = 1
            st.rerun()
        return

    st.info(
        "Añade clientes a la campaña manualmente o por grupo. "
        "Estos clientes recibirán las acciones comerciales."
    )

    # -------------------------
    # 1. Clientes actuales
    # -------------------------
    st.subheader("Clientes incluidos en la campaña")

    clientes_campania = _fetch_campania_clientes(supabase, campaniaid)

    if not clientes_campania:
        st.info("La campaña aún no tiene clientes.")
    else:
        for c in clientes_campania:
            cli = c.get("cliente") or {}
            with st.container(border=True):
                col1, col2, col3 = st.columns([6, 3, 1])

                with col1:
                    st.markdown(f"**👤 {cli.get('razon_social', '(sin nombre)')}**")

                with col2:
                    st.caption(f"ID Cliente: {cli.get('clienteid')}")

                with col3:
                    if st.button("❌", key=f"del_cli_{c['campania_clienteid']}"):
                        supabase.table("campania_cliente").delete().eq(
                            "campania_clienteid", c["campania_clienteid"]
                        ).execute()
                        st.rerun()

    st.divider()

    # -------------------------
    # 2. Buscar y añadir manual
    # -------------------------
    st.subheader("➕ Añadir cliente manualmente")

    texto = st.text_input("Buscar cliente por razón social o ID", key="busq_cli")

    if texto and len(texto) >= 2:
        try:
            q = (
                supabase.table("cliente")
                .select("clienteid, razon_social, identificador, trabajadorid")
                .or_(
                    f"razon_social.ilike.%{texto}%,identificador.ilike.%{texto}%,clienteid.eq.{texto}"
                )
                .limit(40)
            )
            res = q.execute()
            candidatos = res.data or []
        except Exception as e:
            st.error(f"Error buscando clientes: {e}")
            candidatos = []

        for cli in candidatos:
            with st.container(border=True):
                col1, col2 = st.columns([7, 1])

                with col1:
                    st.write(
                        f"**{cli.get('razon_social','(sin nombre)')}** "
                        f"· ID: {cli.get('clienteid')} · Ref: {cli.get('identificador')}"
                    )

                with col2:
                    if st.button("Añadir", key=f"add_cli_{cli['clienteid']}"):
                        _add_cliente_to_campania(supabase, campaniaid, cli["clienteid"])
                        st.rerun()

    st.divider()

    # -------------------------
    # 3. Segmentación por grupo
    # -------------------------
    st.subheader("🎯 Segmentación por grupo de cliente")

    try:
        res_g = supabase.table("grupo").select("grupoid, nombre").order("nombre").execute()
        grupos = res_g.data or []
    except Exception:
        grupos = []

    if grupos:
        nombres_grupos = ["-- Selecciona grupo --"] + [g["nombre"] for g in grupos]
        grupo_sel = st.selectbox("Filtrar clientes por grupo:", nombres_grupos)

        if grupo_sel != "-- Selecciona grupo --":
            grupo_obj = next(g for g in grupos if g["nombre"] == grupo_sel)

            res_cli = (
                supabase.table("cliente")
                .select("clienteid, razon_social, identificador")
                .eq("grupoid", grupo_obj["grupoid"])
                .execute()
            )
            clientes_grupo = res_cli.data or []

            st.write(f"Clientes en grupo **{grupo_sel}**: {len(clientes_grupo)}")

            for cli in clientes_grupo:
                with st.container(border=True):
                    col1, col2 = st.columns([7, 1])

                    with col1:
                        st.write(f"{cli['razon_social']} · ID {cli['clienteid']}")

                    with col2:
                        if st.button("Añadir", key=f"add_grp_{cli['clienteid']}"):
                            _add_cliente_to_campania(supabase, campaniaid, cli["clienteid"])
                            st.rerun()

    st.divider()

    # -------------------------
    # 4. Navegación
    # -------------------------
    colA, colB = st.columns(2)
    with colA:
        if st.button("⬅️ Volver a datos generales"):
            st.session_state["campania_step"] = 1
            st.rerun()

    with colB:
        if st.button("➡️ Ir a confirmación"):
            st.session_state["campania_step"] = 3
            st.rerun()


# ======================================================
# 🧩 PASO 3 · CONFIRMACIÓN Y GENERACIÓN
# ======================================================

def step3_confirmacion(supabase, campania, campaniaid):
    st.header("3️⃣ Confirmación de la campaña")

    if not campaniaid:
        st.error("No hay campaña seleccionada.")
        if st.button("⬅️ Volver a datos generales"):
            st.session_state["campania_step"] = 1
            st.rerun()
        return

    # Recargar campaña
    try:
        res = (
            supabase.table("campania")
            .select("*")
            .eq("campaniaid", campaniaid)
            .single()
            .execute()
        )
        campania = res.data
        if not campania:
            st.error("No se encontró la campaña.")
            return
    except Exception as e:
        st.error(f"No se pudo cargar la campaña: {e}")
        return

    clientes = _fetch_campania_clientes(supabase, campaniaid)
    total_clientes = len(clientes)

    if total_clientes == 0:
        st.error("La campaña no tiene clientes. Añade alguno antes de continuar.")
        if st.button("⬅️ Volver a segmentación"):
            st.session_state["campania_step"] = 2
            st.rerun()
        return

    st.subheader("📄 Resumen general")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Nombre:** {campania.get('nombre')}")
        st.markdown(f"**Acción principal:** {campania.get('tipo_accion')}")
        st.markdown(f"**Objetivo total:** {campania.get('objetivo_total') or '—'}")

    with col2:
        st.markdown(f"**Fecha inicio:** {campania.get('fecha_inicio')}")
        st.markdown(f"**Fecha fin:** {campania.get('fecha_fin')}")
        st.markdown(f"**Estado:** `{campania.get('estado')}`")

    st.markdown("**Descripción:**")
    st.info(campania.get("descripcion") or "—")

    st.subheader("👥 Clientes asignados")
    st.write(f"Total: **{total_clientes}**")

    with st.expander("Ver lista de clientes"):
        import pandas as pd

        df_cli = pd.DataFrame([
            {
                "Cliente": (c.get("cliente") or {}).get("razon_social", "(sin nombre)"),
                "ID": (c.get("cliente") or {}).get("clienteid")
            }
            for c in clientes
        ])

        st.dataframe(df_cli, hide_index=True, use_container_width=True)

    st.divider()

    st.subheader("⚙️ Generación de acciones CRM")

    st.info(
        "Se crearán actuaciones CRM para cada cliente y la campaña pasará a estado **activa**. "
        "Las actuaciones aparecerán en el Calendario CRM con fechas distribuidas entre inicio y fin."
    )

    generar = st.button("🚀 Generar acciones y activar campaña")

    if generar:
        ok, msg = _validar_activacion(campania, clientes)
        if not ok:
            st.error(msg)
            return

        with st.spinner("Generando actuaciones..."):
            creadas = _generar_acciones_campania(supabase, campania, clientes)

        if creadas == 0:
            st.warning("No se crearon actuaciones. Puede que ya existan para esta campaña.")
        else:
            st.success(f"Actuaciones generadas: **{creadas}**. La campaña ahora está activa.")
            st.balloons()

        st.session_state["campania_step"] = 1
        st.session_state["campaniaid"] = campaniaid
        st.rerun()

    if st.button("⬅️ Volver a segmentación"):
        st.session_state["campania_step"] = 2
        st.session_state["menu_campanias"] = "Segmentación"
        st.rerun()


# ======================================================
# 🔧 HELPERS INTERNOS
# ======================================================

def _validar_fechas(fecha_inicio: date, fecha_fin: date):
    if not fecha_inicio or not fecha_fin:
        return False, "Debes indicar fecha de inicio y fin."
    if fecha_fin < fecha_inicio:
        return False, "La fecha fin no puede ser anterior a la fecha inicio."
    return True, None


def _validar_segmentacion(clientes):
    if not clientes or len(clientes) == 0:
        return False, "La campaña no tiene clientes asignados."
    return True, None


def _validar_activacion(campania, clientes):
    try:
        fi = date.fromisoformat(str(campania["fecha_inicio"]))
        ff = date.fromisoformat(str(campania["fecha_fin"]))
    except Exception:
        return False, "Fechas de campaña no válidas."

    ok, msg = _validar_fechas(fi, ff)
    if not ok:
        return False, msg

    ok, msg = _validar_segmentacion(clientes)
    if not ok:
        return False, msg

    return True, None


def _fetch_campania_clientes(supabase, campaniaid: int):
    """
    Devuelve registros de campania_cliente + cliente embebido.
    """
    try:
        res = (
            supabase.table("campania_cliente")
            .select("campania_clienteid, clienteid, cliente (clienteid, razon_social, trabajadorid)")
            .eq("campaniaid", campaniaid)
            .execute()
        )
        return res.data or []
    except Exception:
        return []


def _add_cliente_to_campania(supabase, campaniaid: int, clienteid: int):
    """
    Añade cliente respetando el UNIQUE (campaniaid, clienteid).
    """
    try:
        supabase.table("campania_cliente").insert(
            {"campaniaid": campaniaid, "clienteid": clienteid}
        ).execute()
    except Exception as e:
        st.warning(f"No se pudo añadir el cliente (puede que ya esté en la campaña). Detalle: {e}")


def _campania_tiene_actuaciones(supabase, campaniaid: int) -> bool:
    """
    Comprueba si existen registros en campania_actuacion para esta campaña.
    """
    try:
        res = (
            supabase.table("campania_actuacion")
            .select("actuacionid", count="exact")
            .eq("campaniaid", campaniaid)
            .limit(1)
            .execute()
        )
        data = res.data or []
        return len(data) > 0
    except Exception:
        return False


def _generar_acciones_campania(supabase, campania, clientes):
    """
    Genera registros en crm_actuacion y en campania_actuacion.

    NO usa columna campaniaid en crm_actuacion (porque no existe),
    la relación se guarda en campania_actuacion.
    """
    campaniaid = campania["campaniaid"]

    # Evitar duplicar tareas si ya existen vinculadas
    if _campania_tiene_actuaciones(supabase, campaniaid):
        st.warning("Las actuaciones de esta campaña ya existen. No se crearán duplicados.")
        return 0

    try:
        fi = date.fromisoformat(str(campania["fecha_inicio"]))
        ff = date.fromisoformat(str(campania["fecha_fin"]))
    except Exception:
        fi = date.today()
        ff = fi

    dias = max((ff - fi).days + 1, 1)

    tipo_accion = campania.get("tipo_accion") or "llamada"
    trabajador_por_defecto = st.session_state.get("trabajadorid")

    creadas = 0

    for idx, c in enumerate(clientes):
        cli = c.get("cliente") or {}
        clienteid = cli.get("clienteid")

        if not clienteid:
            continue

        # Fecha distribuida en el rango de la campaña
        offset = idx % dias
        fecha_venc = fi + timedelta(days=offset)
        fecha_accion = datetime.combine(fecha_venc, time(9, 0))

        trabajadorid = cli.get("trabajadorid") or trabajador_por_defecto

        actuacion_payload = {
            "clienteid": clienteid,
            "trabajadorid": trabajadorid,
            "trabajador_asignadoid": trabajadorid,
            "canal": tipo_accion,
            "descripcion": campania.get("descripcion") or "",
            "estado": "Pendiente",  # respeta el CHECK de crm_actuacion
            "fecha_accion": fecha_accion.isoformat(),
            "fecha_vencimiento": fecha_venc.isoformat(),
            "prioridad": "Media",
            "titulo": f"Campaña: {campania.get('nombre')}",
        }

        try:
            res_act = supabase.table("crm_actuacion").insert(actuacion_payload).execute()
            if not res_act.data:
                continue
            act_id = res_act.data[0]["crm_actuacionid"]

            supabase.table("campania_actuacion").insert(
                {
                    "campaniaid": campaniaid,
                    "actuacionid": act_id,
                    "clienteid": clienteid,
                }
            ).execute()

            creadas += 1
        except Exception as e:
            st.error(f"Error creando actuación para cliente {clienteid}: {e}")

    # Cambiar estado a activa si se ha creado algo
    if creadas > 0:
        try:
            supabase.table("campania").update({"estado": "activa"}).eq(
                "campaniaid", campaniaid
            ).execute()
        except Exception as e:
            st.error(f"Error actualizando estado de campaña: {e}")

    return creadas
