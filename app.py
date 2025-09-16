import streamlit as st
import pandas as pd
from supabase import create_client

# -----------------------
# CONFIGURACIÓN SUPABASE
# -----------------------
url = "https://iwtapkspwdogppxhnhes.supabase.co"
anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml3dGFwa3Nwd2RvZ3BweGhuaGVzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc5MTk3NjAsImV4cCI6MjA3MzQ5NTc2MH0.6L7vNDpX336FFEuywSIFTVuB2vKb-LgSAVYgKP6hXUk"
supabase = create_client(url, anon_key)

# Usuarios autorizados para editar/delete
ALLOWED_EDITORS = {"hola@entenova.com", "idi1001@alu.ubu.es"}

# -----------------------
# AJUSTES PÁGINA
# -----------------------
st.set_page_config(page_title="Gestión de Clientes - ERP", layout="wide")

# -----------------------
# UTILS
# -----------------------
def fetch_clientes():
    res = supabase.table("cliente").select("*").order("clienteid", desc=False).execute()
    return res.data or []

def draw_readonly_table():
    data = fetch_clientes()
    if data:
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    else:
        st.info("ℹ️ No hay clientes en la base de datos.")

def get_logged_email():
    return st.session_state.get("user_email")

def can_edit():
    email = get_logged_email()
    return email in ALLOWED_EDITORS if email else False

# -----------------------
# SIDEBAR: LOGIN
# -----------------------
st.sidebar.title("🔐 Acceso")
if "user_email" not in st.session_state:
    st.session_state["user_email"] = None
if "pending_delete" not in st.session_state:
    st.session_state["pending_delete"] = None
if "editing_id" not in st.session_state:
    st.session_state["editing_id"] = None

if st.session_state["user_email"] is None:
    with st.sidebar.form("login_form"):
        email_login = st.text_input("Correo")
        password_login = st.text_input("Contraseña", type="password")
        login_btn = st.form_submit_button("Iniciar Sesión")

    if login_btn:
        try:
            res = supabase.auth.sign_in_with_password({"email": email_login, "password": password_login})
            user_obj = getattr(res, "user", None)
            if user_obj and getattr(user_obj, "email", None):
                st.session_state["user_email"] = user_obj.email
                st.sidebar.success(f"✅ Sesión iniciada: {user_obj.email}")
                st.rerun()
            else:
                st.sidebar.error("❌ Credenciales incorrectas")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")
else:
    st.sidebar.success(f"Conectado: {st.session_state['user_email']}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["user_email"] = None
        st.session_state["pending_delete"] = None
        st.session_state["editing_id"] = None
        st.rerun()

# -----------------------
# INTRO
# -----------------------
st.title("📋 ERP - Gestión de Clientes")
st.markdown("""
Bienvenido al **ERP Orbe**.  
- 📝 Añade clientes con el formulario.  
- 📂 Importa varios clientes desde CSV.  
- ✏️ / 🗑️ Edita o borra en la pestaña dedicada (solo usuarios autorizados).  
""")

# -----------------------
# PESTAÑAS
# -----------------------
tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "✏️/🗑️ Editar o Borrar"])

# =======================
# TAB 1: FORMULARIO
# =======================
with tab1:
    st.subheader("Añadir cliente - Formulario")

    with st.form("form_cliente"):
        nombrefiscal = st.text_input("Nombre Fiscal (obligatorio)", max_chars=100)
        nombrecomercial = st.text_input("Nombre Comercial", max_chars=100)
        cif_nif = st.text_input("CIF / NIF", max_chars=15)
        email = st.text_input("Email")
        telefono = st.text_input("Teléfono", max_chars=15)
        ciudad = st.text_input("Ciudad", max_chars=50)
        provincia = st.text_input("Provincia", max_chars=50)
        pais = st.text_input("País", value="España", max_chars=50)
        submitted = st.form_submit_button("➕ Insertar Cliente")

    if submitted:
        if not nombrefiscal:
            st.error("❌ Nombre Fiscal obligatorio")
        elif email and "@" not in email:
            st.error("❌ Email no válido")
        elif telefono and not telefono.isdigit():
            st.error("❌ Teléfono solo números")
        else:
            nuevo_cliente = {
                "nombrefiscal": nombrefiscal,
                "nombrecomercial": nombrecomercial,
                "cif_nif": cif_nif,
                "email": email,
                "telefono": telefono,
                "ciudad": ciudad,
                "provincia": provincia,
                "pais": pais,
            }
            try:
                supabase.table("cliente").insert(nuevo_cliente).execute()
                st.success("✅ Cliente insertado")
                st.rerun()
            except Exception as e:
                st.error(f"Error insertando: {e}")

    st.markdown("#### 📷 Ejemplos (formulario)")
    c1, c2 = st.columns(2)
    with c1:
        st.image("captura.png", caption="Formulario (ejemplo)", use_container_width=True)
    with c2:
        st.image("aceptado.png", caption="Cliente aceptado (ejemplo)", use_container_width=True)

    st.markdown("#### 📑 Tabla en vivo")
    draw_readonly_table()

# =======================
# TAB 2: CSV
# =======================
with tab2:
    st.subheader("Importar clientes desde CSV")
    st.markdown("CSV con columnas: `nombrefiscal,nombrecomercial,cif_nif,email,telefono,ciudad,provincia,pais`")

    uploaded_file = st.file_uploader("Selecciona CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos los clientes del CSV"):
                data = df.to_dict(orient="records")
                supabase.table("cliente").insert(data).execute()
                st.success(f"✅ Insertados {len(data)} clientes")
                st.rerun()
        except Exception as e:
            st.error(f"Error leyendo CSV: {e}")

    st.markdown("#### 📷 Ejemplos (CSV)")
    c3, c4 = st.columns(2)
    with c3:
        st.image("ejemplo.png", caption="Formulario ejemplo", use_container_width=True)
    with c4:
        st.image("1decsv.png", caption="Ejemplo CSV", use_container_width=True)

    st.markdown("#### 📑 Tabla en vivo")
    draw_readonly_table()

# =======================
# TAB 3: EDITAR / BORRAR
# =======================
with tab3:
    st.subheader("Clientes (acciones por fila)")
    data = fetch_clientes()
    if not data:
        st.info("ℹ️ No hay clientes en la base de datos.")
    else:
        df = pd.DataFrame(data)

        # Aviso permisos
        if not can_edit():
            st.warning("Solo lectura. Inicia sesión con un usuario autorizado para ✏️/🗑️.")
        
        # Mostrar encabezados manuales (con columnas para iconos a la izquierda)
        header_cols = st.columns([0.6, 0.6, 1.8, 1.8, 1.8, 1.2, 1.2, 1.2, 1.2])
        header_cols[0].markdown("**✏️**")
        header_cols[1].markdown("**🗑️**")
        header_cols[2].markdown("**Nombre Fiscal**")
        header_cols[3].markdown("**Nombre Comercial**")
        header_cols[4].markdown("**Email**")
        header_cols[5].markdown("**Teléfono**")
        header_cols[6].markdown("**Ciudad**")
        header_cols[7].markdown("**Provincia**")
        header_cols[8].markdown("**ID**")

        # Render por fila
        for _, row in df.iterrows():
            cols = st.columns([0.6, 0.6, 1.8, 1.8, 1.8, 1.2, 1.2, 1.2, 1.2])
            cliente_id = int(row["clienteid"])

            # ✏️ EDITAR
            with cols[0]:
                if can_edit():
                    if st.button("✏️", key=f"edit_{cliente_id}"):
                        st.session_state["editing_id"] = cliente_id
                        st.rerun()
                else:
                    st.write("-")

            # 🗑️ BORRAR (con confirmación global)
            with cols[1]:
                if can_edit():
                    if st.button("🗑️", key=f"del_{cliente_id}"):
                        st.session_state["pending_delete"] = cliente_id
                        st.rerun()
                else:
                    st.write("-")

            # Celdas de datos
            cols[2].write(row.get("nombrefiscal", ""))
            cols[3].write(row.get("nombrecomercial", ""))
            cols[4].write(row.get("email", ""))
            cols[5].write(row.get("telefono", ""))
            cols[6].write(row.get("ciudad", ""))
            cols[7].write(row.get("provincia", ""))
            cols[8].write(cliente_id)

        # FORMULARIO DE EDICIÓN (debajo de la tabla, cuando se pulsa ✏️)
        if st.session_state["editing_id"] is not None:
            eid = st.session_state["editing_id"]
            st.markdown("---")
            st.markdown(f"### ✏️ Editar cliente #{eid}")
            current = next((c for c in data if c["clienteid"] == eid), None)
            if current:
                with st.form(f"edit_form_{eid}"):
                    nf = st.text_input("Nombre Fiscal", value=current.get("nombrefiscal", ""))
                    nc = st.text_input("Nombre Comercial", value=current.get("nombrecomercial", ""))
                    em = st.text_input("Email", value=current.get("email", ""))
                    tel = st.text_input("Teléfono", value=current.get("telefono", ""))
                    ciu = st.text_input("Ciudad", value=current.get("ciudad", ""))
                    prov = st.text_input("Provincia", value=current.get("provincia", ""))
                    pais = st.text_input("País", value=current.get("pais", ""))
                    save = st.form_submit_button("💾 Guardar cambios")
                    if save:
                        if not can_edit():
                            st.error("No tienes permisos para editar.")
                        else:
                            supabase.table("cliente").update({
                                "nombrefiscal": nf,
                                "nombrecomercial": nc,
                                "email": em,
                                "telefono": tel,
                                "ciudad": ciu,
                                "provincia": prov,
                                "pais": pais
                            }).eq("clienteid", eid).execute()
                            st.success("✅ Cliente actualizado")
                            st.session_state["editing_id"] = None
                            st.rerun()

        # CONFIRMACIÓN DE BORRADO (global, bajo la tabla)
        if st.session_state["pending_delete"] is not None:
            did = st.session_state["pending_delete"]
            st.markdown("---")
            st.error(f"¿Seguro que quieres eliminar el cliente #{did}? Esta acción es irreversible.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Confirmar eliminación"):
                    if not can_edit():
                        st.error("No tienes permisos para borrar.")
                    else:
                        supabase.table("cliente").delete().eq("clienteid", did).execute()
                        st.success(f"✅ Cliente {did} eliminado")
                        st.session_state["pending_delete"] = None
                        st.rerun()
            with c2:
                if st.button("❌ Cancelar"):
                    st.session_state["pending_delete"] = None
                    st.rerun()
