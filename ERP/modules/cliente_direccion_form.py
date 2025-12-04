import streamlit as st

# =========================================================
# 🔍 Buscar por Código Postal
# =========================================================
def buscar_por_cp(supabase, cp: str):
    cp = cp.strip()
    resultados = []

    try:
        exact = (
            supabase.table("postal_localidad")
            .select("*")
            .eq("cp", cp)
            .order("localidad")
            .execute()
            .data or []
        )
        resultados.extend(exact)
    except:
        pass

    if cp.startswith("0"):
        try:
            alt = (
                supabase.table("postal_localidad")
                .select("*")
                .eq("cp", cp.llstrip("0"))
                .order("localidad")
                .execute()
                .data or []
            )
            resultados.extend(alt)
        except:
            pass

    finales = {r["postallocid"]: r for r in resultados if r.get("postallocid")}
    return list(finales.values())


# =========================================================
# 🔧 Cargar direcciones
# =========================================================
def _load_direcciones(supabase, clienteid):
    try:
        return (
            supabase.table("cliente_direccion")
            .select("*")
            .eq("clienteid", clienteid)
            .order("tipo", desc=True)
            .execute()
            .data or []
        )
    except Exception as e:
        st.error(f"❌ Error cargando direcciones: {e}")
        return []


# =========================================================
# 💾 Guardar dirección
# =========================================================
def _guardar_direccion(supabase, clienteid, data):
    try:
        data["clienteid"] = clienteid
        supabase.table("cliente_direccion").upsert(
            data, on_conflict="cliente_direccionid"
        ).execute()

        # Reset paginación para que se vea arriba
        st.session_state[f"page_dir_{clienteid}"] = 0

        st.toast("✅ Dirección guardada correctamente.")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error guardando dirección: {e}")


# =========================================================
# 🔍 Autocompletar CP
# =========================================================
def _cp_busqueda_por_boton(
    supabase,
    cp_key,
    loc_key,
    prov_key,
    prov_id_key,
    region_id_key,
):
    cp = str(st.session_state.get(cp_key, "")).strip()
    btn_key = f"{cp_key}_btn_fill"

    if st.button("🔍 Rellenar desde CP", key=btn_key):
        if len(cp) < 4 or not cp.isdigit():
            st.warning("⚠️ CP no válido (mínimo 4 dígitos).")
            return

        try:
            filas = (
                supabase.table("postal_localidad")
                .select("*")
                .eq("cp", cp)
                .order("localidad")
                .execute()
                .data or []
            )
        except Exception as e:
            st.error(f"❌ Error buscando CP: {e}")
            return

        if not filas:
            st.warning("⚠️ No hay localidades para ese CP.")
            st.session_state.pop(f"{cp_key}_opt", None)
            return

        st.session_state[f"{cp_key}_opt"] = filas

        if len(filas) == 1:
            r = filas[0]
            st.session_state[loc_key] = r.get("localidad", "")
            st.session_state[prov_key] = r.get("provincia_nombre_raw", "")
            st.session_state[prov_id_key] = r.get("provinciaid")
            st.session_state[region_id_key] = r.get("regionid")
            st.success(f"📍 {r.get('localidad','')} ({r.get('provincia_nombre_raw','')})")

    opciones = st.session_state.get(f"{cp_key}_opt")
    if opciones and len(opciones) > 1:
        labels = [
            f"{r.get('localidad','-')} ({r.get('provincia_nombre_raw','-')})"
            for r in opciones
        ]

        sel_key = f"{cp_key}_opts_select"
        sel = st.selectbox("Localidades disponibles", labels, key=sel_key)

        r = opciones[labels.index(sel)]
        st.session_state[loc_key] = r.get("localidad", "")
        st.session_state[prov_key] = r.get("provincia_nombre_raw", "")
        st.session_state[prov_id_key] = r.get("provinciaid")
        st.session_state[region_id_key] = r.get("regionid")


# =========================================================
# 🏠 FORMULARIO PRINCIPAL — con buscador, filtros y paginación
# =========================================================
def render_direccion_form(supabase, clienteid, modo="cliente"):

    # CABECERA
    st.markdown(
        """
        <div style="
            padding:10px;
            background:#ecfdf5;
            border:1px solid #bbf7d0;
            border-radius:10px;
            margin-bottom:10px;">
            <div style="font-size:1.25rem; font-weight:650; color:#065f46;">
                🏠 Direcciones del cliente
            </div>
            <div style="font-size:0.9rem; color:#047857;">
                Fiscales y de envío. Solo puede haber una fiscal.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Provincias MAP
    prov_map = {}
    try:
        provs = supabase.table("provincia").select("provinciaid,nombre").execute().data
        if provs:
            prov_map = {p["provinciaid"]: p["nombre"] for p in provs}
    except:
        pass

    # Load direcciones
    direcciones = _load_direcciones(supabase, clienteid)

    fiscal_actual = next((d for d in direcciones if d.get("tipo") == "fiscal"), None)

    # =====================================================
    # 🔎 BUSCADOR
    # =====================================================
    search = st.text_input("🔍 Buscar dirección…", key=f"buscar_dir_{clienteid}")

    if search.strip():
        s = search.lower()
        direcciones = [
            d for d in direcciones
            if s in (d.get("direccion","") + d.get("ciudad","") + d.get("cp","") + d.get("provincia","")).lower()
        ]

    # =====================================================
    # FILTRO POR TIPO
    # =====================================================
    filtro_tipo = st.selectbox(
        "Filtrar por tipo",
        ["Todos", "Fiscales", "Envío"],
        key=f"filtro_tipo_{clienteid}"
    )

    if filtro_tipo == "Fiscales":
        direcciones = [d for d in direcciones if d.get("tipo") == "fiscal"]
    elif filtro_tipo == "Envío":
        direcciones = [d for d in direcciones if d.get("tipo") == "envio"]

    # =====================================================
    # PAGINACIÓN
    # =====================================================
    PAGE_SIZE = 10

    st.session_state.setdefault(f"page_dir_{clienteid}", 0)

    total = len(direcciones)
    max_page = max((total - 1) // PAGE_SIZE, 0)

    page = st.session_state[f"page_dir_{clienteid}"]

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_dirs = direcciones[start:end]

    # PREINICIALIZAR session_state
    for d in page_dirs:
        dir_id_tmp = d.get("cliente_direccionid")
        if dir_id_tmp is None:
            continue
        st.session_state.setdefault(f"flag_edit_{dir_id_tmp}", False)
        st.session_state.setdefault(f"confirm_fiscal_{dir_id_tmp}", False)

    # =====================================================
    # TARJETAS — DISEÑO EXACTO SOLICITADO + BOTONES COMPACTOS
    # =====================================================
    for d in page_dirs:

        dir_id = d["cliente_direccionid"]
        tipo = d.get("tipo", "envio").lower()
        provincia_nombre = prov_map.get(d.get("provinciaid"), d.get("provincia", "-"))

        flag_key = f"flag_edit_{dir_id}"
        st.session_state.setdefault(flag_key, False)
        st.session_state.setdefault(f"confirm_fiscal_{dir_id}", False)

        # -----------------------------------------------------
        # CARD EXACTO — TU DISEÑO ORIGINAL
        # -----------------------------------------------------
        st.markdown(
            f"""
            <div style="
                border:1px solid #d1d5db;
                background:#ffffff;
                border-radius:8px;
                padding:12px 14px;
                margin-bottom:6px;">

                <!-- Título -->
                <div style="font-size:1rem; font-weight:600; color:#065f46;">
                    📦 {tipo.capitalize()} {"⭐" if tipo == "fiscal" else ""}
                </div>

                <!-- Dirección -->
                <div style="font-size:0.88rem; color:#475569; margin-top:4px;">
                    {d.get('direccion', '-')} —
                    {d.get('cp', '-')} {d.get('ciudad', '-')} ({provincia_nombre})
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        # -----------------------------------------------------
        # BOTONES (compactos, debajo del card)
        # -----------------------------------------------------
        colA, colB, colC = st.columns([1, 1, 2])

        # EDITAR
        with colA:
            if st.button("✏ Editar", key=f"edit_{dir_id}", use_container_width=True):
                st.session_state[flag_key] = not st.session_state.get(flag_key, False)

        # BORRAR
        with colB:
            if st.button("🗑 Borrar", key=f"del_{dir_id}", use_container_width=True):
                try:
                    supabase.table("cliente_direccion").delete().eq(
                        "cliente_direccionid", dir_id
                    ).execute()
                    st.session_state[f"page_dir_{clienteid}"] = 0
                    st.toast("🗑 Dirección eliminada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error eliminando dirección: {e}")

        # HACER FISCAL
        with colC:
            if tipo != "fiscal":
                if st.button("⭐ Fiscal", key=f"mkf_{dir_id}", use_container_width=True):
                    st.session_state[f"confirm_fiscal_{dir_id}"] = True

        # -----------------------------------------------------
        # CONFIRMAR FISCAL — versión compacta y elegante
        # -----------------------------------------------------
        if st.session_state.get(f"confirm_fiscal_{dir_id}", False):

            st.markdown(
                """
                <div style="
                    border:1px solid #facc15;
                    background:#fefce8;
                    padding:10px;
                    border-radius:6px;
                    margin-bottom:8px;">
                    <strong>¿Hacer fiscal esta dirección?</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

            cc1, cc2 = st.columns(2)

            # Confirmar
            with cc1:
                if st.button("✔ Sí", key=f"cfy_{dir_id}"):
                    try:
                        # Quitar fiscal anterior
                        supabase.table("cliente_direccion").update(
                            {"tipo": "envio"}
                        ).eq("clienteid", clienteid).eq("tipo", "fiscal").execute()

                        # Asignar nueva fiscal
                        supabase.table("cliente_direccion").update(
                            {"tipo": "fiscal"}
                        ).eq("cliente_direccionid", dir_id).execute()

                        st.session_state[f"confirm_fiscal_{dir_id}"] = False
                        st.session_state[f"page_dir_{clienteid}"] = 0

                        st.toast("⭐ Dirección fiscal actualizada.")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Error convirtiendo en fiscal: {e}")

            # Cancelar
            with cc2:
                if st.button("Cancelar", key=f"cfn_{dir_id}"):
                    st.session_state[f"confirm_fiscal_{dir_id}"] = False

        # -----------------------------------------------------
        # FORMULARIO EDICIÓN — Expander
        # -----------------------------------------------------
        if st.session_state.get(flag_key, False):

            with st.expander("✏ Editar dirección", expanded=True):

                cp_key = f"cp_{dir_id}"
                loc_key = f"loc_{dir_id}"
                prov_key = f"prov_{dir_id}"
                prov_id_key = f"proid_{dir_id}"
                reg_id_key = f"regid_{dir_id}"

                st.session_state.setdefault(cp_key, d.get("cp", ""))
                st.session_state.setdefault(loc_key, d.get("ciudad", ""))
                st.session_state.setdefault(prov_key, provincia_nombre)

                cp = st.text_input("CP", st.session_state.get(cp_key, ""), key=cp_key)

                _cp_busqueda_por_boton(
                    supabase, cp_key, loc_key, prov_key, prov_id_key, reg_id_key
                )

                ciudad = st.text_input("Localidad", st.session_state.get(loc_key, d.get("ciudad", "")), key=loc_key)
                provincia = st.text_input("Provincia", st.session_state.get(prov_key, provincia_nombre), key=prov_key)
                direccion = st.text_input("Dirección", d.get("direccion", ""), key=f"dir_txt_{dir_id}")
                pais = st.text_input("País", d.get("pais", "España"), key=f"pais_{dir_id}")
                email = st.text_input("Email", d.get("email", ""), key=f"mail_{dir_id}")

                tipo_val = "fiscal" if tipo == "fiscal" else "envio"

                if st.button("💾 Guardar", key=f"save_{dir_id}"):
                    payload = {
                        "cliente_direccionid": dir_id,
                        "direccion": direccion.strip(),
                        "ciudad": st.session_state.get(loc_key, ciudad).strip(),
                        "cp": cp.strip(),
                        "provincia": st.session_state.get(prov_key, provincia).strip(),
                        "provinciaid": st.session_state.get(prov_id_key, d.get("provinciaid")),
                        "regionid": st.session_state.get(reg_id_key, d.get("regionid")),
                        "pais": pais.strip(),
                        "email": email.strip(),
                        "tipo": tipo_val,
                    }
                    _guardar_direccion(supabase, clienteid, payload)




    # =====================================================
    # PAGINACIÓN — BOTONES
    # =====================================================
    st.markdown("")

    colP1, colP2, colP3 = st.columns([1,1,4])

    with colP1:
        if page > 0:
            if st.button("⬅️ Anterior", key=f"prev_{clienteid}"):
                st.session_state[f"page_dir_{clienteid}"] -= 1
                st.rerun()

    with colP2:
        if page < max_page:
            if st.button("Siguiente ➡️", key=f"next_{clienteid}"):
                st.session_state[f"page_dir_{clienteid}"] += 1
                st.rerun()

    # =====================================================
    # ➕ NUEVA DIRECCIÓN
    # =====================================================
    st.markdown("---")

    with st.expander("➕ Añadir nueva dirección"):

        fiscal_exist = any(d.get("tipo")=="fiscal" for d in direcciones)

        cp_key = f"cp_new_{clienteid}"
        loc_key = f"loc_new_{clienteid}"
        prov_id_key = f"proid_new_{clienteid}"
        prov_nombre_key = f"prov_new_{clienteid}"

        st.session_state.setdefault(cp_key,"")
        st.session_state.setdefault(loc_key,"")
        st.session_state.setdefault(prov_nombre_key,"")

        cp = st.text_input("CP", key=cp_key)

        if st.button("🔍 Buscar CP", key=f"buscar_new_{clienteid}"):
            filas = buscar_por_cp(supabase, cp)
            if not filas:
                st.warning("⚠️ No existe ese CP.")
            elif len(filas) == 1:
                r = filas[0]
                st.session_state[loc_key] = r.get("localidad","")
                st.session_state[prov_id_key] = r.get("provinciaid")
                st.session_state[prov_nombre_key] = r.get("provincia_nombre_raw","")
                st.success(f"📍 {r.get('localidad','')}")
            else:
                labels = [f"{r['localidad']} ({r['provincia_nombre_raw']})" for r in filas]
                sel_key = f"sel_new_{clienteid}"
                sel = st.selectbox("Localidades", labels, key=sel_key)
                r = filas[labels.index(sel)]
                st.session_state[loc_key] = r["localidad"]
                st.session_state[prov_id_key] = r["provinciaid"]
                st.session_state[prov_nombre_key] = r["provincia_nombre_raw"]

        localidad = st.text_input("Localidad", key=loc_key)
        provincia = st.text_input("Provincia", key=prov_nombre_key)
        direccion = st.text_input("Dirección", key=f"dir_new_{clienteid}")
        pais = st.text_input("País", "España", key=f"pais_new_{clienteid}")
        email = st.text_input("Email", key=f"email_new_{clienteid}")

        tipo = "envio"
        if not fiscal_exist:
            tipo = st.selectbox("Tipo", ["fiscal","envio"], key=f"tipo_new_{clienteid}")

        if st.button("💾 Guardar nueva", key=f"save_new_{clienteid}"):
            payload = {
                "direccion": direccion.strip(),
                "ciudad": localidad.strip(),
                "cp": cp.strip(),
                "provincia": provincia.strip(),
                "provinciaid": st.session_state.get(prov_id_key),
                "regionid": None,
                "pais": pais.strip(),
                "email": email.strip(),
                "tipo": tipo,
            }
            _guardar_direccion(supabase, clienteid, payload)
