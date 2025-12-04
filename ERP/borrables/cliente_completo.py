import streamlit as st
from supabase import create_client

# ======================================================
# 🔌 CONFIGURACIÓN SUPABASE
# ======================================================
SUPABASE_URL = "https://gqhrbvusvcaytcbnusdx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxaHJidnVzdmNheXRjYm51c2R4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MzM3MDQsImV4cCI6MjA3NTAwOTcwNH0.y3018JLs9A08sSZKHLXeMsITZ3oc4s2NDhNLxWqM9Ag"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ======================================================
# 🧾 FORMULARIO CLIENTE PRINCIPAL
# ======================================================
def render_cliente_completo():
    st.title("🧾 Alta de cliente")
    st.caption("Formulario para crear un nuevo cliente en el sistema. Los datos adicionales (dirección, contacto, banco...) se añaden más adelante.")

    st.divider()

    # ------------------------------------------------
    # FUNCIONES AUXILIARES
    # ------------------------------------------------
    def get_options(tabla, campo="nombre", value_field=None):
        try:
            data = supabase.table(tabla).select("*").eq("habilitado", True).execute().data
            if not data:
                return {}
            value_field = value_field or f"{tabla}id"
            return {d[campo]: d[value_field] for d in data}
        except Exception:
            return {}

    def get_estado_activo():
        estado = supabase.table("cliente_estado").select("estadoid").eq("nombre", "Activo").execute().data
        return estado[0]["estadoid"] if estado else None

    # ------------------------------------------------
    # CAMPOS PRINCIPALES DE CLIENTE
    # ------------------------------------------------
    col1, col2 = st.columns(2)
    with col1:
        razon_social = st.text_input("Razón social *", placeholder="Ej: Librería San Marcos")
        identificador = st.text_input("Identificador único *", placeholder="Ej: libreria-san-marcos")
        observaciones = st.text_area("Observaciones", placeholder="Notas internas...")

    with col2:
        categorias = get_options("cliente_categoria")
        grupos = get_options("grupo", "nombre", "grupoid")
        trabajadores = get_options("trabajador", "nombre", "trabajadorid")
        formas_pago = get_options("forma_pago", "nombre", "formapagoid")

        categoria_nombre = st.selectbox("Categoría", list(categorias.keys()) if categorias else [])
        grupo_nombre = st.selectbox("Grupo (opcional)", ["(Sin grupo)"] + list(grupos.keys()) if grupos else ["(Sin grupo)"])
        trabajador_nombre = st.selectbox("Trabajador asignado", ["(Ninguno)"] + list(trabajadores.keys()))
        formapago_nombre = st.selectbox("Forma de pago", list(formas_pago.keys()) if formas_pago else [])

    st.divider()

    st.info(
        """
        ⚙️ **Campos que se completarán más adelante:**
        - Direcciones (fiscal y envío)
        - Contactos asociados
        - Cuentas bancarias
        - Condiciones personalizadas
        - Configuración de facturación
        """,
        icon="ℹ️"
    )

    st.divider()

    # ------------------------------------------------
    # BOTÓN DE CREACIÓN
    # ------------------------------------------------
    if st.button("💾 Crear cliente", use_container_width=True):
        if not razon_social or not identificador:
            st.error("⚠️ Debes rellenar al menos Razón social e Identificador.")
            st.stop()

        try:
            with st.spinner("Guardando cliente en Supabase..."):
                estadoid = get_estado_activo()
                categoriaid = categorias.get(categoria_nombre)
                grupoid = grupos.get(grupo_nombre) if grupo_nombre != "(Sin grupo)" else None
                trabajadorid = trabajadores.get(trabajador_nombre) if trabajador_nombre != "(Ninguno)" else None
                formapagoid = formas_pago.get(formapago_nombre)

                cliente_data = {
                    "razon_social": razon_social,
                    "identificador": identificador,
                    "estadoid": estadoid,
                    "categoriaid": categoriaid,
                    "grupoid": grupoid,
                    "trabajadorid": trabajadorid,
                    "formapagoid": formapagoid,
                    "observaciones": observaciones
                }

                res = supabase.table("cliente").insert(cliente_data).execute()
                clienteid = res.data[0]["clienteid"]

                st.success(f"✅ Cliente '{razon_social}' creado correctamente con ID {clienteid}.")
                st.info("➡️ Puedes añadir direcciones, contactos o facturación desde el panel de cliente.")
                st.balloons()

        except Exception as e:
            st.error(f"❌ Error al crear el cliente: {e}")
