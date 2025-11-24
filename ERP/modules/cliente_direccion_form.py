# =========================================================
# 🏠 FORM · Direcciones del cliente (versión profesional + CP auto)
# =========================================================
import streamlit as st


def buscar_por_cp(supabase, cp: str):

    cp = cp.strip()

    resultados = []

    # 1) Buscar CP exactamente como lo escribió el usuario
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

    # 2) Si empieza por 0 → buscar también sin los 0
    if cp.startswith("0"):
        cp_sin_ceros = cp.lstrip("0")

        try:
            alt = (
                supabase.table("postal_localidad")
                .select("*")
                .eq("cp", cp_sin_ceros)
                .order("localidad")
                .execute()
                .data or []
            )
            resultados.extend(alt)
        except:
            pass

    # Eliminar duplicados por postallocid
    finales = {r["postallocid"]: r for r in resultados}

    return list(finales.values())


# =========================================================
# 🔧 Cargar direcciones
# =========================================================
def _load_direcciones(supabase, clienteid):
    try:
        data = (
            supabase.table("cliente_direccion")
            .select("*")
            .eq("clienteid", clienteid)
            .order("tipo", desc=True)
            .execute()
            .data or []
        )
        return data
    except Exception as e:
        st.error(f"❌ Error cargando direcciones: {e}")
        return []


# =========================================================
# 💾 Guardar / actualizar dirección
# =========================================================
def _guardar_direccion(supabase, clienteid, data):
    try:
        data["clienteid"] = clienteid
        supabase.table("cliente_direccion").upsert(
            data,
            on_conflict="cliente_direccionid"
        ).execute()
        st.toast("✅ Dirección guardada correctamente.", icon="✅")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error guardando dirección: {e}")


# =========================================================
# 🔍 BOTÓN · Buscar datos por código postal
# =========================================================
def _cp_busqueda_por_boton(
    supabase,
    cp_key: str,
    loc_key: str,
    prov_key: str,
    prov_id_key: str,
    region_id_key: str,
):
    """
    Botón que, usando el CP escrito en el campo principal, intenta rellenar
    LOCALIDAD y PROVINCIA.

    - No crea inputs nuevos.
    - Solo usa/actualiza los mismos text_input de localidad y provincia
      a través de session_state.
    """

    cp = str(st.session_state.get(cp_key, "") or "").strip()

    # Botón bajo el campo de CP
    if st.button("🔍 Rellenar desde código postal", key=f"{cp_key}_buscar", use_container_width=False):
        if len(cp) < 4 or not cp.isdigit():
            st.warning("⚠️ Introduce al menos 4 dígitos numéricos de código postal.")
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
            st.error(f"❌ Error buscando el código postal: {e}")
            return

        if not filas:
            st.warning("⚠️ No se encontraron localidades para ese código postal.")
            st.session_state.pop(f"{cp_key}_options", None)
            return

        # Guardamos las opciones por si hay varias
        st.session_state[f"{cp_key}_options"] = filas

        # Si solo hay una, la aplicamos directamente
        if len(filas) == 1:
            row = filas[0]
            st.session_state[loc_key] = row.get("localidad", "")
            st.session_state[prov_key] = row.get("provincia_nombre_raw", "") or ""
            st.session_state[prov_id_key] = row.get("provinciaid")
            st.session_state[region_id_key] = row.get("regionid")
            st.success(f"📍 Aplicado: {row.get('localidad','')} ({row.get('provincia_nombre_raw','')})")

    # Si en una búsqueda previa había varias localidades, mostramos el selector
    opciones = st.session_state.get(f"{cp_key}_options")
    if opciones and len(opciones) > 1:
        labels = [
            f"{r['localidad']} ({r.get('provincia_nombre_raw','')})"
            for r in opciones
        ]
        label_sel = st.selectbox(
            "Localidades disponibles para este CP",
            labels,
            key=f"{cp_key}_opt_label",
        )
        row = opciones[labels.index(label_sel)]
        st.session_state[loc_key] = row.get("localidad", "")
        st.session_state[prov_key] = row.get("provincia_nombre_raw", "") or ""
        st.session_state[prov_id_key] = row.get("provinciaid")
        st.session_state[region_id_key] = row.get("regionid")
        st.caption(f"✅ Localidad aplicada: {row.get('localidad','')} ({row.get('provincia_nombre_raw','')})")


# =========================================================
# 🏠 FORMULARIO PRINCIPAL · Direcciones
# =========================================================
def render_direccion_form(supabase, clienteid, modo="cliente"):
    st.markdown("### 🏠 Direcciones")
    st.caption("Gestiona las direcciones fiscales y de envío del cliente.")

    # Mapa provinciaid → nombre para mostrar en las tarjetas
    try:
        prov_rows = (
            supabase.table("provincia")
            .select("provinciaid, nombre")
            .execute()
            .data or []
        )
        prov_map = {p["provinciaid"]: p["nombre"] for p in prov_rows}
    except Exception:
        prov_map = {}

    direcciones = _load_direcciones(supabase, clienteid)
    if not direcciones:
        st.info("📭 No hay direcciones registradas aún.")

    # =====================================================
    # 🗂️ Tarjetas de direcciones existentes
    # =====================================================
    for d in direcciones:
        tipo = d.get("tipo", "envio").capitalize()
        es_principal = bool(d.get("es_principal", False))

        provincia_nombre_tarjeta = prov_map.get(
            d.get("provinciaid"),
            d.get("provincia", "-"),
        )

        borde = "#38bdf8" if es_principal else "#e5e7eb"
        fondo = "#f0f9ff" if es_principal else "#f9fafb"

        with st.container():
            st.markdown(
                f"""
                <div style="border:1px solid {borde};
                            border-radius:12px;
                            padding:14px;
                            margin-bottom:10px;
                            background:{fondo};">
                    <b style="font-size:1.05rem;">📦 {tipo}</b> {'⭐' if es_principal else ''}<br>
                    <span style="color:#4b5563;">
                        {d.get('direccion','-')}, {d.get('cp','-')} {d.get('ciudad','-')}
                        ({provincia_nombre_tarjeta}) — {d.get('pais','-')}<br>
                        📧 {d.get('email','-') or '-'}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns(3)

            # Editar
            with col1:
                if st.button("✏️ Editar", key=f"edit_dir_{d['cliente_direccionid']}", use_container_width=True):
                    st.session_state[f"edit_dir_{d['cliente_direccionid']}"] = not st.session_state.get(
                        f"edit_dir_{d['cliente_direccionid']}", False
                    )

            # Eliminar
            with col2:
                if st.button("🗑️ Eliminar", key=f"del_dir_{d['cliente_direccionid']}", use_container_width=True):
                    try:
                        supabase.table("cliente_direccion").delete()\
                            .eq("cliente_direccionid", d["cliente_direccionid"]).execute()
                        st.toast("🗑️ Dirección eliminada.", icon="🗑️")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error eliminando dirección: {e}")

            # Hacer principal
            with col3:
                if not es_principal:
                    if st.button("⭐ Hacer principal", key=f"main_dir_{d['cliente_direccionid']}", use_container_width=True):
                        try:
                            supabase.table("cliente_direccion").update({"es_principal": False}).eq("clienteid", clienteid).execute()
                            supabase.table("cliente_direccion").update({"es_principal": True}).eq("cliente_direccionid", d["cliente_direccionid"]).execute()
                            st.toast("⭐ Dirección marcada como principal.", icon="⭐")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al marcar dirección principal: {e}")

        # ---------- Formulario de edición ----------
        if st.session_state.get(f"edit_dir_{d['cliente_direccionid']}"):
            with st.expander(f"✏️ Editar dirección — {tipo}", expanded=True):

                cid = d["cliente_direccionid"]
                cp_key = f"cp_edit_{cid}"
                loc_key = f"loc_edit_{cid}"
                prov_key = f"prov_edit_{cid}"
                prov_id_key = f"prov_id_edit_{cid}"
                region_id_key = f"reg_id_edit_{cid}"

                # CP
                cp_val = st.text_input(
                    "Código Postal",
                    value=str(d.get("cp", "") or ""),
                    key=cp_key,
                )

                # Botón de búsqueda por CP (rellena localidad/provincia)
                _cp_busqueda_por_boton(
                    supabase,
                    cp_key=cp_key,
                    loc_key=loc_key,
                    prov_key=prov_key,
                    prov_id_key=prov_id_key,
                    region_id_key=region_id_key,
                )

                # Localidad
                loc_val = st.text_input(
                    "Localidad",
                    value=d.get("ciudad", "") or d.get("localidad", "") or "",
                    key=loc_key,
                )

                # Provincia (texto, editable, pero sincronizada con CP si se usa el botón)
                prov_nombre_ini = prov_map.get(d.get("provinciaid"), d.get("provincia", "") or "")
                prov_val = st.text_input(
                    "Provincia",
                    value=prov_nombre_ini,
                    key=prov_key,
                )

                # Calle
                dir_val = st.text_input(
                    "Dirección",
                    value=d.get("direccion", "") or "",
                    key=f"dir_edit_{cid}",
                )

                pais_val = st.text_input("País", value=d.get("pais", "España") or "España", key=f"pais_edit_{cid}")
                email_val = st.text_input("Email", value=d.get("email", "") or "", key=f"email_edit_{cid}")
                tipo_val = st.selectbox(
                    "Tipo",
                    ["fiscal", "envio"],
                    index=(0 if d.get("tipo", "envio").lower() == "fiscal" else 1),
                    key=f"tipo_edit_{cid}",
                )
                principal_val = st.checkbox("⭐ Principal", value=es_principal, key=f"principal_edit_{cid}")

                if st.button("💾 Guardar cambios", key=f"save_dir_{cid}", use_container_width=True):
                    _guardar_direccion(supabase, clienteid, {
                        "cliente_direccionid": cid,
                        "direccion": dir_val.strip(),
                        "ciudad": st.session_state.get(loc_key, loc_val).strip(),
                        "cp": cp_val.strip(),
                        "provincia": st.session_state.get(prov_key, prov_val).strip(),
                        "provinciaid": st.session_state.get(prov_id_key, d.get("provinciaid")),
                        "regionid": st.session_state.get(region_id_key, d.get("regionid")),
                        "pais": pais_val.strip(),
                        "email": email_val.strip(),
                        "tipo": tipo_val,
                        "es_principal": principal_val,
                    })

    # =========================================================
    # ➕ AÑADIR NUEVA DIRECCIÓN (versión correcta)
    # =========================================================
    st.markdown("---")
    with st.expander("➕ Añadir nueva dirección", expanded=False):

        # ------ CAMPOS PRINCIPALES -------
        cp_key = "cp_new"
        loc_key = "loc_new"
        prov_id_key = "prov_id_new"
        prov_nombre_key = "prov_nombre_new"

        cp = st.text_input("Código Postal", key=cp_key, placeholder="Ej. 28013")

        # ------ BOTÓN QUE HACE LA MAGIA -------
        if st.button("🔍 Buscar CP", key="buscar_cp_new"):

            filas = buscar_por_cp(supabase, cp)

            if not filas:
                st.warning("⚠️ No existe ese código postal.")
            elif len(filas) == 1:
                row = filas[0]
                st.session_state[loc_key] = row["localidad"]
                st.session_state[prov_id_key] = row["provinciaid"]
                st.session_state[prov_nombre_key] = row.get("provincia_nombre_raw", "")
                st.success(f"📍 Detectado: {row['localidad']} ({row.get('provincia_nombre_raw', '-')})")
            else:
                # VARIAS LOCALIDADES PARA EL MISMO CP
                opciones = [f"{r['localidad']} ({r.get('provincia_nombre_raw','')})" for r in filas]
                sel = st.selectbox("Selecciona localidad", opciones, key="sel_loc_new")

                row = filas[opciones.index(sel)]
                st.session_state[loc_key] = row["localidad"]
                st.session_state[prov_id_key] = row["provinciaid"]
                st.session_state[prov_nombre_key] = row.get("provincia_nombre_raw", "")

                st.success(f"📍 Localidad seleccionada: {row['localidad']}")

        # ------ CAMPOS QUE SE AUTOCOMPLETAN -------
        localidad = st.text_input("Localidad", key=loc_key)
        provincia_nombre = st.text_input("Provincia", key=prov_nombre_key)

        # ------ CAMPOS RESTANTES -------
        direccion = st.text_input("Dirección", key="dir_new")
        pais = st.text_input("País", value="España", key="pais_new")
        email = st.text_input("Email", key="email_new")
        tipo = st.selectbox("Tipo", ["fiscal","envio"], key="tipo_new")
        principal = st.checkbox("⭐ Marcar como principal", key="principal_new")

        # ------ GUARDAR -------
        if st.button("💾 Guardar nueva dirección", key="save_new_dir"):

            _guardar_direccion(
                supabase,
                clienteid,
                {
                    "direccion": direccion.strip(),
                    "ciudad": st.session_state.get(loc_key, "").strip(),
                    "cp": cp.strip(),
                    "provincia": st.session_state.get(prov_nombre_key, "").strip(),
                    "provinciaid": st.session_state.get(prov_id_key),
                    "regionid": None,  # si lo quieres, lo añadimos
                    "pais": pais.strip(),
                    "email": email.strip(),
                    "tipo": tipo,
                    "es_principal": principal
                }
            )
