import streamlit as st
from modules.supa_client import get_supabase_client

def render_login():
    """
    🔐 Inicio de sesión para trabajadores del ERP EnteNova Gnosis.
    - Autentica por correo (sin contraseña).
    - Carga automáticamente el trabajador, su ID y rol (si lo tiene).
    """

    st.title("🧱 ERP EnteNova Gnosis")
    st.caption("Sistema interno Orbe · módulo de trabajadores")

    supabase = get_supabase_client()

    # -------------------------------------------------------
    # 🧍 FORMULARIO DE INICIO
    # -------------------------------------------------------
    st.subheader("🔐 Iniciar sesión como trabajador")

    with st.form("form_login_trabajador"):
        email = st.text_input("📧 Correo corporativo *", placeholder="Ej: iker@entenova.com")
        submitted = st.form_submit_button("Entrar ➜")

    if submitted:
        if not email.strip():
            st.error("⚠️ El correo es obligatorio.")
            return

        try:
            # Buscar trabajador por correo
            trab = (
                supabase.table("trabajador")
                .select("trabajadorid, nombre, apellidos, telefono, email, rol")
                .eq("email", email.strip())
                .limit(1)
                .execute()
            )

            if trab.data:
                t = trab.data[0]

                # Limpiar posible sesión previa
                for key in ["cliente_actual", "cliente_creado"]:
                    st.session_state.pop(key, None)

                # Guardar sesión
                st.session_state["user_email"] = email.strip()
                st.session_state["user_nombre"] = f"{t['nombre']} {t['apellidos']}"
                st.session_state["tipo_usuario"] = "trabajador"
                st.session_state["trabajadorid"] = t["trabajadorid"]
                st.session_state["rol_usuario"] = t.get("rol", "Editor")

                st.success(f"✅ Bienvenido {t['nombre']} ({email})")
                st.info("Acceso habilitado a gestión de clientes, CRM y comunicación interna.")
                st.rerun()
                return

            else:
                st.error("❌ No se encontró ningún trabajador con ese correo.")

        except Exception as e:
            st.error(f"❌ Error al iniciar sesión: {e}")

    # -------------------------------------------------------
    # 🚪 CIERRE DE SESIÓN
    # -------------------------------------------------------
    if "user_email" in st.session_state:
        st.markdown("---")
        st.subheader("🚪 Cerrar sesión")
        if st.button("Cerrar sesión"):
            for key in [
                "cliente_actual",
                "cliente_creado",
                "user_email",
                "user_nombre",
                "tipo_usuario",
                "rol_usuario",
                "trabajadorid",
            ]:
                st.session_state.pop(key, None)
            st.success("✅ Sesión cerrada correctamente.")
            st.rerun()

    # -------------------------------------------------------
    # 👣 PIE DE PÁGINA
    # -------------------------------------------------------
    st.markdown("---")
    st.caption("© 2025 EnteNova Gnosis · Orbe · Desarrollado por Iker Domínguez Ibáñez")
