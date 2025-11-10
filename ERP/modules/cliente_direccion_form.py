# =========================================================
# 🏠 FORM · Direcciones del cliente (versión profesional)
# =========================================================
import streamlit as st

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


def _guardar_direccion(supabase, clienteid, data):
    try:
        data["clienteid"] = clienteid
        supabase.table("cliente_direccion").upsert(data, on_conflict="cliente_direccionid").execute()
        st.toast("✅ Dirección guardada correctamente.", icon="✅")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error guardando dirección: {e}")


def render_direccion_form(supabase, clienteid, modo="cliente"):
    st.markdown("### 🏠 Direcciones")
    st.caption("Gestiona las direcciones fiscales y de envío del cliente.")

    direcciones = _load_direcciones(supabase, clienteid)
    if not direcciones:
        st.info("📭 No hay direcciones registradas aún.")

    # -------------------------------------------------
    # 🗂️ Mostrar direcciones existentes
    # -------------------------------------------------
    for d in direcciones:
        tipo = d.get("tipo", "envio").capitalize()
        direccion = d.get("direccion", "-")
        ciudad = d.get("ciudad", "-")
        cp = d.get("cp", "-")
        provincia = d.get("provincia", "-")
        pais = d.get("pais", "-")
        email = d.get("email", "-")
        es_principal = bool(d.get("es_principal", False))

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
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <b style="font-size:1.05rem;">📦 {tipo}</b> {'⭐' if es_principal else ''}<br>
                            <span style="color:#4b5563;">
                                {direccion}, {cp} {ciudad} ({provincia}) — {pais}<br>
                                📧 {email or '-'}
                            </span>
                        </div>
                        <div style="text-align:right;">
                            {"<span style='background:#dbeafe;color:#1e3a8a;padding:4px 8px;border-radius:8px;font-size:0.8rem;'>Principal</span>" if es_principal else ""}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                if st.button("✏️ Editar", key=f"edit_dir_{d['cliente_direccionid']}", use_container_width=True):
                    st.session_state[f"edit_dir_{d['cliente_direccionid']}"] = not st.session_state.get(
                        f"edit_dir_{d['cliente_direccionid']}", False
                    )

            with c2:
                if st.button("🗑️ Eliminar", key=f"del_dir_{d['cliente_direccionid']}", use_container_width=True):
                    try:
                        supabase.table("cliente_direccion").delete().eq("cliente_direccionid", d["cliente_direccionid"]).execute()
                        st.toast("🗑️ Dirección eliminada.", icon="🗑️")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error eliminando dirección: {e}")

            with c3:
                if not es_principal:
                    if st.button("⭐ Hacer principal", key=f"main_dir_{d['cliente_direccionid']}", use_container_width=True):
                        try:
                            supabase.table("cliente_direccion").update({"es_principal": False}).eq("clienteid", clienteid).execute()
                            supabase.table("cliente_direccion").update({"es_principal": True}).eq("cliente_direccionid", d["cliente_direccionid"]).execute()
                            st.toast("⭐ Dirección marcada como principal.", icon="⭐")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al marcar dirección principal: {e}")

        # -------------------------------------------------
        # ✏️ Expander de edición inline
        # -------------------------------------------------
        if st.session_state.get(f"edit_dir_{d['cliente_direccionid']}"):
            with st.expander(f"✏️ Editar dirección — {tipo}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    direccion_n = st.text_input("Dirección", value=direccion)
                    ciudad_n = st.text_input("Ciudad", value=ciudad)
                    cp_n = st.text_input("Código postal", value=cp)
                    provincia_n = st.text_input("Provincia", value=provincia)
                with c2:
                    pais_n = st.text_input("País", value=pais)
                    email_n = st.text_input("Email", value=email)
                    tipo_n = st.selectbox("Tipo", ["fiscal", "envio"], index=(0 if tipo.lower() == "fiscal" else 1))
                    principal_n = st.checkbox("⭐ Principal", value=es_principal)

                if st.button("💾 Guardar cambios", key=f"save_dir_{d['cliente_direccionid']}", use_container_width=True):
                    _guardar_direccion(supabase, clienteid, {
                        "cliente_direccionid": d["cliente_direccionid"],
                        "direccion": direccion_n,
                        "ciudad": ciudad_n,
                        "cp": cp_n,
                        "provincia": provincia_n,
                        "pais": pais_n,
                        "email": email_n,
                        "tipo": tipo_n,
                        "es_principal": principal_n
                    })

    # -------------------------------------------------
    # ➕ Nueva dirección
    # -------------------------------------------------
    st.markdown("---")
    with st.expander("➕ Añadir nueva dirección", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            direccion_n = st.text_input("Dirección")
            ciudad_n = st.text_input("Ciudad")
            cp_n = st.text_input("Código postal")
            provincia_n = st.text_input("Provincia")
        with c2:
            pais_n = st.text_input("País", value="España")
            email_n = st.text_input("Email")
            tipo_n = st.selectbox("Tipo", ["fiscal", "envio"])
            principal_n = st.checkbox("⭐ Marcar como principal", value=False)

        if st.button("💾 Guardar nueva dirección", use_container_width=True):
            _guardar_direccion(supabase, clienteid, {
                "direccion": direccion_n.strip(),
                "ciudad": ciudad_n.strip(),
                "cp": cp_n.strip(),
                "provincia": provincia_n.strip(),
                "pais": pais_n.strip(),
                "email": email_n.strip(),
                "tipo": tipo_n,
                "es_principal": principal_n,
            })
