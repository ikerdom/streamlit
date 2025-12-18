import streamlit as st
from streamlit.components.v1 import html as st_html


def buscar_por_cp(supabase, cp: str):
    cp_raw = (cp or "").strip()

    if not cp_raw or not cp_raw.isdigit():
        return []

    # Normalizaciones
    cp_variants = {cp_raw}

    # Quitar ceros a la izquierda → "09003" -> "9003"
    cp_no_zeros = cp_raw.lstrip("0")
    if cp_no_zeros:
        cp_variants.add(cp_no_zeros)

    resultados = []

    try:
        for cp_val in cp_variants:
            filas = (
                supabase.table("postal_localidad")
                .select("*")
                .eq("cp", cp_val)
                .order("localidad")
                .execute()
                .data
                or []
            )
            resultados.extend(filas)
    except Exception:
        pass

    # Eliminar duplicados por postallocid
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
            .eq("clienteid", int(clienteid))
            .order("tipo", desc=True)
            .execute()
            .data
            or []
        )
    except Exception as e:
        st.error(f"❌ Error cargando direcciones: {e}")
        return []


# =========================================================
# 💾 Guardar dirección
# =========================================================
def _guardar_direccion(supabase, clienteid, data):
    try:
        data["clienteid"] = int(clienteid)
        supabase.table("cliente_direccion").upsert(
            data, on_conflict="cliente_direccionid"
        ).execute()

        st.session_state[f"page_dir_{clienteid}"] = 0
        st.toast("✅ Dirección guardada correctamente.")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error guardando dirección: {e}")


# =========================================================
# 🔍 Autocompletar CP (edición)
# =========================================================
def _cp_busqueda_por_boton(
    supabase,
    cp_key,
    loc_key,
    prov_key,
    prov_id_key,
    region_id_key,
):
    cp = str(st.session_state.get(cp_key, "") or "").strip()

    if st.button("Rellenar desde CP", key=f"{cp_key}_btn"):
        if len(cp) < 4 or not cp.isdigit():
            st.warning("CP no válido.")
            return

        filas = buscar_por_cp(supabase, cp)


        if not filas:
            st.warning("No hay localidades para ese CP.")
            return

        if len(filas) == 1:
            r = filas[0]
            st.session_state[loc_key] = r.get("localidad", "")
            st.session_state[prov_key] = r.get("provincia_nombre_raw", "")
            st.session_state[prov_id_key] = r.get("provinciaid")
            st.session_state[region_id_key] = r.get("regionid")
        else:
            labels = [f"{r['localidad']} ({r['provincia_nombre_raw']})" for r in filas]
            sel = st.selectbox("Localidades", labels, key=f"{cp_key}_sel")
            r = filas[labels.index(sel)]
            st.session_state[loc_key] = r["localidad"]
            st.session_state[prov_key] = r["provincia_nombre_raw"]
            st.session_state[prov_id_key] = r["provinciaid"]
            st.session_state[region_id_key] = r["regionid"]


# =========================================================
# 🧱 Card HTML (emojis SOLO aquí)
# =========================================================
def _render_dir_card(tipo, direccion, cp, ciudad, provincia):
    tipo = (tipo or "envio").lower()
    titulo = f"📦 {tipo.capitalize()} {'⭐' if tipo == 'fiscal' else ''}"

    st_html(
        f"""
        <div style="border:1px solid #d1d5db;background:#ffffff;
                    border-radius:8px;padding:12px 14px;margin-bottom:6px;">
            <div style="font-size:1rem;font-weight:600;color:#065f46;">
                {titulo}
            </div>
            <div style="font-size:0.88rem;color:#475569;margin-top:4px;">
                {direccion} — {cp} {ciudad} ({provincia})
            </div>
        </div>
        """,
        height=90,
    )


# =========================================================
# 🏠 FORMULARIO PRINCIPAL
# =========================================================
def render_direccion_form(supabase, clienteid, modo="cliente"):
    clienteid = int(clienteid)

    st.markdown("### 🏠 Direcciones del cliente")
    st.caption("Direcciones fiscales y de envío. Solo puede haber una fiscal.")

    direcciones = _load_direcciones(supabase, clienteid)

    # ===============================
    # BUSCADOR
    # ===============================
    search = st.text_input("Buscar dirección", key=f"buscar_dir_{clienteid}")
    if search:
        s = search.lower()
        direcciones = [
            d
            for d in direcciones
            if s
            in (
                (d.get("direccion", "") + d.get("ciudad", "") + d.get("cp", "") + d.get("provincia", "")).lower()
            )
        ]

    # ===============================
    # FILTRO TIPO
    # ===============================
    filtro = st.selectbox("Tipo", ["Todos", "Fiscales", "Envío"])
    if filtro == "Fiscales":
        direcciones = [d for d in direcciones if d.get("tipo") == "fiscal"]
    elif filtro == "Envío":
        direcciones = [d for d in direcciones if d.get("tipo") == "envio"]

    # ===============================
    # PAGINACIÓN
    # ===============================
    PAGE_SIZE = 10
    st.session_state.setdefault(f"page_dir_{clienteid}", 0)
    page = st.session_state[f"page_dir_{clienteid}"]
    max_page = max((len(direcciones) - 1) // PAGE_SIZE, 0)

    if page > max_page:
        st.session_state[f"page_dir_{clienteid}"] = max_page
        page = max_page

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_dirs = direcciones[start:end]

    # ===============================
    # TARJETAS
    # ===============================
    for d in page_dirs:
        dir_id = d["cliente_direccionid"]
        flag_key = f"edit_{dir_id}"
        confirm_key = f"confirm_{dir_id}"

        st.session_state.setdefault(flag_key, False)
        st.session_state.setdefault(confirm_key, False)

        _render_dir_card(
            d.get("tipo"),
            d.get("direccion", "-"),
            d.get("cp", "-"),
            d.get("ciudad", "-"),
            d.get("provincia", "-"),
        )

        c1, c2, c3 = st.columns([1, 1, 2])

        with c1:
            if st.button("Editar", key=f"btn_edit_{dir_id}"):
                st.session_state[flag_key] = not st.session_state[flag_key]

        with c2:
            if st.button("Borrar", key=f"btn_del_{dir_id}"):
                supabase.table("cliente_direccion").delete().eq(
                    "cliente_direccionid", dir_id
                ).execute()
                st.toast("Dirección eliminada")
                st.rerun()

        with c3:
            if d.get("tipo") != "fiscal":
                if st.button("Hacer fiscal", key=f"btn_fiscal_{dir_id}"):
                    st.session_state[confirm_key] = True

        # CONFIRMAR FISCAL
        if st.session_state[confirm_key]:
            st.warning("¿Marcar esta dirección como fiscal?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Confirmar", key=f"ok_{dir_id}"):
                    supabase.table("cliente_direccion").update({"tipo": "envio"}).eq(
                        "clienteid", clienteid
                    ).eq("tipo", "fiscal").execute()

                    supabase.table("cliente_direccion").update({"tipo": "fiscal"}).eq(
                        "cliente_direccionid", dir_id
                    ).execute()

                    st.toast("Dirección fiscal actualizada")
                    st.rerun()
            with cc2:
                if st.button("Cancelar", key=f"cancel_{dir_id}"):
                    st.session_state[confirm_key] = False

        # FORM EDITAR
        if st.session_state[flag_key]:
            with st.expander("Editar dirección", expanded=True):
                cp_key = f"cp_{dir_id}"
                loc_key = f"loc_{dir_id}"
                prov_key = f"prov_{dir_id}"
                prov_id_key = f"proid_{dir_id}"
                reg_id_key = f"regid_{dir_id}"

                st.session_state.setdefault(cp_key, d.get("cp", ""))
                st.session_state.setdefault(loc_key, d.get("ciudad", ""))
                st.session_state.setdefault(prov_key, d.get("provincia", ""))

                cp = st.text_input("CP", key=cp_key)
                _cp_busqueda_por_boton(
                    supabase, cp_key, loc_key, prov_key, prov_id_key, reg_id_key
                )

                ciudad = st.text_input("Localidad", key=loc_key)
                provincia = st.text_input("Provincia", key=prov_key)
                direccion = st.text_input("Dirección", value=d.get("direccion", ""))
                pais = st.text_input("País", value=d.get("pais", "España"))
                email = st.text_input("Email", value=d.get("email", ""))

                if st.button("Guardar cambios", key=f"save_{dir_id}"):
                    payload = {
                        "cliente_direccionid": dir_id,
                        "direccion": direccion.strip(),
                        "ciudad": ciudad.strip(),
                        "cp": cp.strip(),
                        "provincia": provincia.strip(),
                        "provinciaid": st.session_state.get(prov_id_key),
                        "regionid": st.session_state.get(reg_id_key),
                        "pais": pais.strip(),
                        "email": email.strip(),
                        "tipo": d.get("tipo"),
                    }
                    _guardar_direccion(supabase, clienteid, payload)

    # ===============================
    # NUEVA DIRECCIÓN (con Rellenar desde CP ✅)
    # ===============================
    st.markdown("---")
    with st.expander("➕ Añadir nueva dirección"):
        fiscal_exist = any(d.get("tipo") == "fiscal" for d in _load_direcciones(supabase, clienteid))

        cp_key = f"cp_new_{clienteid}"
        loc_key = f"loc_new_{clienteid}"
        prov_key = f"prov_new_{clienteid}"
        prov_id_key = f"proid_new_{clienteid}"
        reg_id_key = f"regid_new_{clienteid}"

        st.session_state.setdefault(cp_key, "")
        st.session_state.setdefault(loc_key, "")
        st.session_state.setdefault(prov_key, "")
        st.session_state.setdefault(prov_id_key, None)
        st.session_state.setdefault(reg_id_key, None)

        cp = st.text_input("CP", key=cp_key)

        # Botón rellenar desde CP + selector si hay varias localidades
        _cp_busqueda_por_boton(supabase, cp_key, loc_key, prov_key, prov_id_key, reg_id_key)

        ciudad = st.text_input("Localidad", key=loc_key)
        provincia = st.text_input("Provincia", key=prov_key)
        direccion = st.text_input("Dirección", key=f"dir_new_{clienteid}")
        pais = st.text_input("País", "España", key=f"pais_new_{clienteid}")
        email = st.text_input("Email", key=f"email_new_{clienteid}")

        tipo = "envio"
        if not fiscal_exist:
            tipo = st.selectbox("Tipo", ["fiscal", "envio"], key=f"tipo_new_{clienteid}")

        if st.button("Guardar nueva dirección", key=f"save_new_{clienteid}"):
            payload = {
                "direccion": direccion.strip(),
                "ciudad": ciudad.strip(),
                "cp": cp.strip(),
                "provincia": provincia.strip(),
                "provinciaid": st.session_state.get(prov_id_key),
                "regionid": st.session_state.get(reg_id_key),
                "pais": pais.strip(),
                "email": email.strip(),
                "tipo": tipo,
            }
            _guardar_direccion(supabase, clienteid, payload)
