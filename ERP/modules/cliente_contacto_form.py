import streamlit as st

# =========================================================
# 👥 FORM · Contactos del cliente (ERP style)
# =========================================================

def _parse_pg_array(val):
    """Convierte arrays Postgres a lista limpia."""
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val).strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1].strip()
        if not s:
            return []
        parts = [p.strip().strip('"').strip("'") for p in s.split(",")]
        return [p for p in parts if p]
    return [s] if s else []


# =========================================================
# 🧾 Render principal
# =========================================================
def render_contacto_form(supabase, clienteid: int):

    # =========================
    # CABECERA
    # =========================
    st.markdown(
        """
        <div style="
            padding:10px;
            background:#f8fafc;
            border:1px solid #e5e7eb;
            border-radius:10px;
            margin-bottom:10px;">
            <div style="font-size:1.15rem; font-weight:600; color:#111827;">
                👥 Contactos del cliente
            </div>
            <div style="font-size:0.9rem; color:#6b7280;">
                Personas de contacto asociadas al cliente.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================
    # Cargar contactos
    # =========================
    try:
        contactos = (
            supabase.table("cliente_contacto")
            .select("*")
            .eq("clienteid", int(clienteid))
            .order("es_principal", desc=True)
            .order("nombre")
            .execute()
            .data
            or []
        )
    except Exception as e:
        st.error(f"❌ No se pudieron cargar los contactos: {e}")
        return

    # =========================
    # ➕ Nuevo contacto
    # =========================
    with st.expander("➕ Añadir nuevo contacto"):
        _contacto_editor(supabase, clienteid, None)

    # =========================
    # Listado
    # =========================
    if not contactos:
        st.info("📭 Este cliente no tiene contactos registrados.")
        return

    st.markdown("---")

    for c in contactos:
        cid = c["cliente_contactoid"]
        nombre = c.get("nombre", "(Sin nombre)")
        cargo = c.get("cargo") or "—"
        rol = c.get("rol") or "—"
        emails = ", ".join(_parse_pg_array(c.get("email"))) or "—"
        telefonos = ", ".join(_parse_pg_array(c.get("telefono"))) or "—"
        obs = c.get("observaciones") or "—"
        es_principal = bool(c.get("es_principal"))

        bg = "#f0f9ff" if es_principal else "#ffffff"
        border = "#38bdf8" if es_principal else "#e5e7eb"

        st.markdown(
            f"""
            <div style="
                background:{bg};
                border:1px solid {border};
                border-left:5px solid {border};
                border-radius:10px;
                padding:12px 14px;
                margin-bottom:10px;">

                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-size:1.05rem;font-weight:600;">
                        {nombre}
                        <span style="color:#6b7280;font-size:0.9rem;">
                            — {cargo}
                        </span>
                    </div>
                    {"<span style='padding:3px 8px;background:#dbeafe;color:#1e3a8a;border-radius:999px;font-size:0.75rem;'>⭐ Principal</span>" if es_principal else ""}
                </div>

                <div style="margin-top:6px;font-size:0.9rem;color:#374151;">
                    📧 <b>Email:</b> {emails}<br>
                    📞 <b>Teléfono:</b> {telefonos}<br>
                    🧩 <b>Rol:</b> {rol}<br>
                    📝 <b>Notas:</b> {obs}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # -------------------------
        # BOTONES
        # -------------------------
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Editar", key=f"edit_contact_{cid}", use_container_width=True):
                st.session_state[f"edit_contact_{cid}"] = not st.session_state.get(
                    f"edit_contact_{cid}", False
                )

        with col2:
            if st.button("Eliminar", key=f"delete_contact_{cid}", use_container_width=True):
                try:
                    supabase.table("cliente_contacto").delete().eq(
                        "cliente_contactoid", cid
                    ).execute()
                    st.toast("Contacto eliminado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al eliminar contacto: {e}")

        with col3:
            if not es_principal:
                if st.button("Hacer principal", key=f"main_contact_{cid}", use_container_width=True):
                    try:
                        supabase.table("cliente_contacto").update(
                            {"es_principal": False}
                        ).eq("clienteid", clienteid).execute()

                        supabase.table("cliente_contacto").update(
                            {"es_principal": True}
                        ).eq("cliente_contactoid", cid).execute()

                        st.toast("Contacto marcado como principal.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al marcar principal: {e}")

        # -------------------------
        # EDITOR
        # -------------------------
        if st.session_state.get(f"edit_contact_{cid}"):
            with st.expander(f"Editar contacto — {nombre}", expanded=True):
                _contacto_editor(supabase, clienteid, c)


# =========================================================
# ✏️ Editor de contacto (alta / edición)
# =========================================================
def _contacto_editor(supabase, clienteid, c=None):
    is_new = c is None
    cid = (c or {}).get("cliente_contactoid")
    prefix = f"contact_{cid or 'new'}"

    def field(key, label, default=""):
        k = f"{prefix}_{key}"
        st.session_state.setdefault(k, (c or {}).get(key, default))
        return st.text_input(label, key=k)

    nombre = field("nombre", "Nombre *")
    cargo = field("cargo", "Cargo")
    rol = field("rol", "Rol")
    email = field("email", "Email (separar por comas)")
    telefono = field("telefono", "Teléfono (separar por comas)")
    direccion = field("direccion", "Dirección")
    ciudad = field("ciudad", "Ciudad")
    provincia = field("provincia", "Provincia")
    pais = field("pais", "País", "España")
    observaciones = st.text_area("Observaciones", value=(c or {}).get("observaciones", ""), key=f"{prefix}_obs")

    def normalize_multi(txt):
        if not txt:
            return None
        parts = [p.strip() for p in str(txt).split(",") if p.strip()]
        return ", ".join(parts) if parts else None

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Guardar", key=f"{prefix}_save", use_container_width=True):
            if not nombre.strip():
                st.warning("El nombre es obligatorio.")
                return

            data = {
                "clienteid": int(clienteid),
                "nombre": nombre.strip(),
                "cargo": cargo.strip() or None,
                "rol": rol.strip() or None,
                "email": normalize_multi(email),
                "telefono": normalize_multi(telefono),
                "direccion": direccion.strip() or None,
                "ciudad": ciudad.strip() or None,
                "provincia": provincia.strip() or None,
                "pais": pais.strip() or None,
                "observaciones": observaciones.strip() or None,
            }

            try:
                if is_new:
                    supabase.table("cliente_contacto").insert(data).execute()
                    st.toast("Contacto añadido.")
                else:
                    supabase.table("cliente_contacto").update(data).eq(
                        "cliente_contactoid", cid
                    ).execute()
                    st.toast("Contacto actualizado.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar contacto: {e}")

    with col2:
        if not is_new:
            if st.button("Eliminar", key=f"{prefix}_delete", use_container_width=True):
                try:
                    supabase.table("cliente_contacto").delete().eq(
                        "cliente_contactoid", cid
                    ).execute()
                    st.toast("Contacto eliminado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al eliminar contacto: {e}")
