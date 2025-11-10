import streamlit as st

# =========================================================
# 👥 FORM · Contactos del cliente (tarjetas + editor)
# =========================================================

def _parse_pg_array(val):
    """
    Convierte un string tipo Postgres array: "{a@b.com,c@d.com}" -> ["a@b.com","c@d.com"]
    Si ya viene como lista/None u otro tipo, lo devuelve razonablemente.
    """
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val).strip()
    # PostgREST suele serializar arrays como {"x","y"} o {x,y}
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1].strip()
        if not s:
            return []
        # split por comas no escapadas, y quita comillas
        parts = [p.strip().strip('"').strip("'") for p in s.split(",")]
        return [p for p in parts if p]
    return [s] if s else []


def render_contacto_form(supabase, clienteid: int):
    """Gestión de contactos asociados a un cliente (lista + alta + edición)."""
    st.markdown("### 👥 Contactos del cliente")
    st.caption("Consulta, añade o edita los contactos asociados a este cliente.")

    # =====================================================
    # 📦 Cargar contactos
    # =====================================================
    try:
        res = (
            supabase.table("cliente_contacto")
            .select("*")
            .eq("clienteid", int(clienteid))
            .order("es_principal", desc=True)
            .order("nombre")
            .execute()
        )
        contactos = res.data or []

    except Exception as e:
        st.error(f"❌ No se pudieron cargar los contactos: {e}")
        return

    # =====================================================
    # ➕ Añadir nuevo contacto
    # =====================================================
    with st.expander("➕ Añadir nuevo contacto", expanded=False):
        _contacto_editor(supabase, clienteid, None)

    # =====================================================
    # 📇 Listado de contactos existentes
    # =====================================================
    if not contactos:
        st.info("📭 Este cliente no tiene contactos registrados.")
        return

    st.divider()
    for c in contactos:
        nombre = c.get("nombre", "(Sin nombre)")
        cargo = c.get("cargo") or ""
        emails = _parse_pg_array(c.get("email"))
        telefonos = _parse_pg_array(c.get("telefono"))
        rol = c.get("rol") or "-"
        obs = c.get("observaciones") or "-"
        es_principal = bool(c.get("es_principal"))

        color_fondo = "#f0f9ff" if es_principal else "#f9fafb"
        borde = "#38bdf8" if es_principal else "#e5e7eb"

        email_html = ", ".join(emails) if emails else "-"
        tlf_html = ", ".join(telefonos) if telefonos else "-"

        with st.container():
            st.markdown(
                f"""
                <div style="border:1px solid {borde};
                            border-radius:12px;
                            padding:14px;
                            margin-bottom:12px;
                            background:{color_fondo};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-size:1.05rem;">
                                <b>{nombre}</b> <span style='color:#6b7280;'>({cargo or "Sin cargo"})</span>
                            </div>
                            <div>📧 <b>Email:</b> {email_html}</div>
                            <div>📞 <b>Teléfono:</b> {tlf_html}</div>
                            <div>🧩 <b>Rol:</b> {rol}</div>
                            <div>📝 <b>Notas:</b> {obs}</div>
                        </div>
                        <div>
                            {"<span style='padding:4px 8px; background:#dbeafe; color:#1e3a8a; border-radius:999px; font-size:0.8rem;'>⭐ Principal</span>" if es_principal else ""}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("✏️ Editar", key=f"edit_contact_{c['cliente_contactoid']}", use_container_width=True):
                    st.session_state[f"edit_contact_{c['cliente_contactoid']}"] = not st.session_state.get(
                        f"edit_contact_{c['cliente_contactoid']}", False
                    )

            with col2:
                if st.button("🗑️ Eliminar", key=f"delete_contact_{c['cliente_contactoid']}", use_container_width=True):
                    try:
                        supabase.table("cliente_contacto").delete().eq("cliente_contactoid", c["cliente_contactoid"]).execute()
                        st.toast("🗑️ Contacto eliminado correctamente.", icon="🗑️")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al eliminar contacto: {e}")

            with col3:
                if not es_principal:
                    if st.button("⭐ Hacer principal", key=f"main_contact_{c['cliente_contactoid']}", use_container_width=True):
                        try:
                            supabase.table("cliente_contacto").update({"es_principal": False}).eq("clienteid", clienteid).execute()
                            supabase.table("cliente_contacto").update({"es_principal": True}).eq("cliente_contactoid", c["cliente_contactoid"]).execute()
                            st.toast("⭐ Contacto marcado como principal.", icon="⭐")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al marcar contacto principal: {e}")

            # -------------------------------------------------
            # ✏️ Expander edición (relleno con datos del contacto)
            # -------------------------------------------------
            if st.session_state.get(f"edit_contact_{c['cliente_contactoid']}"):
                with st.expander(f"✏️ Editar contacto — {nombre}", expanded=True):
                    _contacto_editor(supabase, clienteid, c)

# =========================================================
# 🔧 Editor interno de contacto (alta / edición) — versión pro
# =========================================================
def _contacto_editor(supabase, clienteid, c=None):
    """Formulario de creación o edición de contacto con validación antidual y mejor UI."""
    is_new = c is None
    cid = (c or {}).get("cliente_contactoid")
    prefix = f"contact_{cid or 'new'}"

    def _field(key, label, default=""):
        full_key = f"{prefix}_{key}"
        st.session_state.setdefault(full_key, (c or {}).get(key, default))
        return st.text_input(label, value=st.session_state[full_key], key=full_key)

    nombre = _field("nombre", "👤 Nombre completo *")
    cargo = _field("cargo", "Cargo / Puesto")
    rol = _field("rol", "Rol interno o comercial")
    email = _field("email", "📧 Email (uno o varios, separados por comas)")
    telefono = _field("telefono", "📞 Teléfono (uno o varios, separados por comas)")
    direccion = _field("direccion", "Dirección")
    ciudad = _field("ciudad", "Ciudad")
    provincia = _field("provincia", "Provincia")
    pais = _field("pais", "País", "España")
    observaciones = st.text_area("📝 Observaciones", value=(c or {}).get("observaciones", ""), key=f"{prefix}_obs")

    # =============================
    # ✅ Validación anti-duplicados
    # =============================
    def _ya_existe(email_val, nombre_val):
        try:
            if not email_val and not nombre_val:
                return False
            conds = []
            if email_val:
                conds.append(f"email.ilike.%{email_val.strip()}%")
            if nombre_val:
                conds.append(f"nombre.ilike.%{nombre_val.strip()}%")
            query = ",".join(conds)
            dup = (
                supabase.table("cliente_contacto")
                .select("cliente_contactoid, nombre, email")
                .eq("clienteid", int(clienteid))
                .or_(query)
                .execute()
                .data
            )
            if not dup:
                return False
            # Evita confundir el mismo registro si estamos editando
            if not is_new:
                dup = [d for d in dup if d["cliente_contactoid"] != cid]
            return bool(dup)
        except Exception:
            return False

    def _normalize_multi(txt):
        if not txt:
            return None
        parts = [p.strip() for p in str(txt).split(",")]
        parts = [p for p in parts if p]
        if not parts:
            return None
        return ", ".join(parts)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("💾 Guardar", key=f"{prefix}_save", use_container_width=True):
            if not nombre.strip():
                st.warning("⚠️ El nombre es obligatorio.")
                return

            # Validación anti duplicado
            if _ya_existe(email, nombre):
                st.warning("⚠️ Ya existe un contacto con el mismo nombre o correo electrónico.")
                return

            data = {
                "clienteid": int(clienteid),
                "nombre": nombre.strip(),
                "cargo": cargo.strip() or None,
                "rol": rol.strip() or None,
                "email": _normalize_multi(email),
                "telefono": _normalize_multi(telefono),
                "direccion": direccion.strip() or None,
                "ciudad": ciudad.strip() or None,
                "provincia": provincia.strip() or None,
                "pais": pais.strip() or None,
                "observaciones": (observaciones or "").strip() or None,
            }

            try:
                if is_new:
                    supabase.table("cliente_contacto").insert(data).execute()
                    st.toast("✅ Contacto añadido correctamente.", icon="✅")
                else:
                    supabase.table("cliente_contacto").update(data).eq("cliente_contactoid", cid).execute()
                    st.toast("✅ Contacto actualizado correctamente.", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar contacto: {e}")

    with col2:
        if not is_new:
            if st.button("🗑️ Eliminar", key=f"{prefix}_delete", use_container_width=True):
                try:
                    supabase.table("cliente_contacto").delete().eq("cliente_contactoid", cid).execute()
                    st.toast("🗑️ Contacto eliminado correctamente.", icon="🗑️")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al eliminar contacto: {e}")
