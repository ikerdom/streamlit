import streamlit as st
from datetime import datetime

def render_contacto_form(supabase):
    st.header("📇 Alta de contacto")
    st.caption("Registra un nuevo contacto. Puedes asociarlo a un cliente existente o dejarlo libre para vincularlo más adelante.")

    with st.form("form_contacto"):
        col1, col2 = st.columns(2)

        with col1:
            nombre = st.text_input("👤 Nombre completo *", placeholder="Ej: María López Ruiz", key="contacto_nombre")
            telefono = st.text_input("📞 Teléfono", placeholder="+34 600 123 456", key="contacto_telefono")
            cargo = st.text_input("🏢 Cargo o puesto", placeholder="Ej: Responsable de compras", key="contacto_cargo")

        with col2:
            email = st.text_input("📧 Correo electrónico", placeholder="Ej: maria@empresa.com", key="contacto_email")
            rol = st.text_input("🎯 Rol en la empresa", placeholder="Ej: Compras, Contabilidad, Dirección...", key="contacto_rol")

            # Buscar clientes existentes (opcional)
            clientes = supabase.table("cliente").select("clienteid, razon_social").execute()
            lista_clientes = {c["razon_social"]: c["clienteid"] for c in clientes.data} if clientes.data else {}
            cliente_asociado = st.selectbox(
                "🧱 Asociar a cliente (opcional)",
                ["(Sin cliente)"] + list(lista_clientes.keys()),
                key="contacto_cliente"
            )

        obs = st.text_area(
            "🗒️ Observaciones",
            placeholder="Ej: contacto preferente en horario de mañana.",
            key="contacto_observaciones"
        )

        submitted = st.form_submit_button("💾 Guardar contacto")

    if submitted:
        if not nombre.strip():
            st.warning("⚠️ El campo *Nombre completo* es obligatorio.")
            return

        try:
            clienteid = None if cliente_asociado == "(Sin cliente)" else lista_clientes[cliente_asociado]

            data = {
                "nombre": nombre.strip(),
                "telefono": telefono.strip() or None,
                "email": email.strip() or None,
                "rol": rol.strip() or None,
                "cargo": cargo.strip() or None,
                "clienteid": clienteid,
                "observaciones": obs.strip() or None,
            }

            res = supabase.table("cliente_contacto").insert(data).execute()

            if res.data:
                nuevo_id = res.data[0]["cliente_contactoid"]
                st.success(f"✅ Contacto creado correctamente (ID {nuevo_id}).")

                if clienteid:
                    st.info(f"🔗 Asociado automáticamente al cliente **{cliente_asociado}**.")
                else:
                    st.caption("💡 Puedes vincular este contacto más adelante desde el perfil del cliente.")
            else:
                st.error("❌ No se pudo insertar el contacto. Verifica los datos.")

        except Exception as e:
            st.error(f"❌ Error al guardar el contacto: {e}")
