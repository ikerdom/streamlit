# modules/cliente_contactos_lista.py
import streamlit as st

def render_contactos_lista(supabase):
    st.header("👥 Contactos de cliente")
    st.caption("Busca y gestiona contactos asociados a tus clientes.")

    c1, c2 = st.columns([2, 1])
    with c1:
        q = st.text_input("🔎 Buscar (nombre, email, teléfono, cliente)…", key="ctos_q")
    with c2:
        solo_principales = st.toggle("⭐ Solo principales", value=False, key="ctos_principales")

    st.markdown("---")

    try:
        base = (
            supabase.table("cliente_contacto")
            .select("cliente_contactoid, nombre, telefono, email, rol, cargo, clienteid, es_principal")
        )
        if q:
            q = q.strip()
            base = base.or_(
                f"nombre.ilike.%{q}%,email.ilike.%{q}%,telefono.ilike.%{q}%"
            )

        if solo_principales:
            base = base.eq("es_principal", True)

        # Trae clientes para mostrar la razón social
        contactos = base.order("nombre").execute().data or []
        if not contactos:
            st.info("📭 No hay contactos que coincidan.")
            return

        # cache simple de clientes
        ids = sorted({c["clienteid"] for c in contactos if c.get("clienteid")})
        cliente_map = {}
        if ids:
            rows = (
                supabase.table("cliente")
                .select("clienteid, razon_social")
                .in_("clienteid", ids)
                .execute()
                .data or []
            )
            cliente_map = {r["clienteid"]: r.get("razon_social","-") for r in rows}

        for cto in contactos:
            razon = cliente_map.get(cto.get("clienteid"), "-")
            estrella = "⭐" if cto.get("es_principal") else ""
            st.markdown(
                f"""
                <div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin-bottom:10px;background:#f9fafb;">
                  <div style="display:flex;justify-content:space-between;gap:10px;">
                    <div>
                      <b>{cto.get('nombre','(Sin nombre)')}</b> {estrella}<br>
                      <span style="color:#6b7280;">{cto.get('cargo','-')} · {cto.get('rol','-')}</span><br>
                      📧 {", ".join(cto.get('email') or []) or "-"}<br>
                      📞 {", ".join(cto.get('telefono') or []) or "-"}
                    </div>
                    <div style="text-align:right;color:#6b7280;">
                      🏢 {razon}
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    except Exception as e:
        st.error(f"❌ Error cargando contactos: {e}")
