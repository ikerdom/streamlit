# modules/ui.py
import os
import streamlit as st
import pandas as pd
import base64

# -----------------------------
# Config / Constantes
# -----------------------------
ALLOWED_EDITORS = {"hola@entenova.com", "idi1001@alu.ubu.es"}

# Ruta logos
LOGO_PATH = os.path.join("images", "logo_orbe.png")         # logo Orbe
ENTENOVA_LOGO = os.path.join("images", "logo-tree.png")     # logo EnteNova

# -----------------------------
# Configuración de página
# -----------------------------
def set_page_config():
    try:
        st.set_page_config(page_title="ERP Orbe", layout="wide")
    except Exception:
        pass

def ensure_session_keys():
    defaults = {
        "user_email": None,
        "editing": None,
        "pending_delete": None,
        "module_key": "inicio",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def can_edit():
    email = st.session_state.get("user_email")
    return bool(email and email in ALLOWED_EDITORS)

# -----------------------------
# CSS (marca de agua y estilos)
# -----------------------------
def apply_custom_css():
    if not os.path.exists(LOGO_PATH):
        return
    try:
        with open(LOGO_PATH, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
    except Exception:
        return

    css = f"""
    <style>
    [data-testid="stApp"] {{
        position: relative;
        overflow: visible;
    }}
    [data-testid="stApp"]::before {{
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        width: 320px;
        height: 320px;
        background: url('data:image/png;base64,{encoded}') no-repeat center center;
        background-size: contain;
        opacity: 0.07;
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 0;
    }}
    .appview-container, .main, [data-testid="stApp"] .block-container {{
        position: relative;
        z-index: 1;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def safe_image(relative_path, **kwargs):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(base_dir, "..", "images", relative_path)
    if os.path.exists(img_path):
        try:
            st.image(img_path, **kwargs)
        except Exception:
            try:
                with open(img_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                st.markdown(f"![img](data:image/png;base64,{encoded})")
            except:
                st.warning(f"⚠️ No se pudo cargar la imagen {relative_path}")
    else:
        st.warning(f"⚠️ Imagen no encontrada: {relative_path}")

# -----------------------------
# Sidebar helpers
# -----------------------------
def sidebar_logo_top():
    if os.path.exists(LOGO_PATH):
        try:
            st.sidebar.image(LOGO_PATH, width=120)
        except Exception:
            pass

def login_sidebar(supabase):
    sidebar_logo_top()
    st.sidebar.title("🔐 Acceso")
    if st.session_state.get("user_email") is None:
        with st.sidebar.form("login_form"):
            email_login = st.text_input("Correo")
            password_login = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Iniciar Sesión"):
                try:
                    res = supabase.auth.sign_in_with_password(
                        {"email": email_login, "password": password_login}
                    )
                    if getattr(res, "user", None) and getattr(res.user, "email", None):
                        st.session_state["user_email"] = res.user.email
                        st.sidebar.success(f"✅ {res.user.email}")
                        st.experimental_rerun()
                    else:
                        st.sidebar.error("❌ Credenciales incorrectas")
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")
    else:
        st.sidebar.success(f"Conectado: {st.session_state['user_email']}")
        if st.sidebar.button("Cerrar sesión"):
            st.session_state["user_email"] = None
            st.session_state["editing"] = None
            st.session_state["pending_delete"] = None
            st.experimental_rerun()

# -----------------------------
# Header con logo Orbe + EnteNova
# -----------------------------
def render_header(title: str, description: str = "", logo="logo_orbe.png"):
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(title)
        if description:
            # Logo EnteNova inline con texto
            if os.path.exists(ENTENOVA_LOGO):
                with open(ENTENOVA_LOGO, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                st.caption(
                    f"""{description}  
                    Aplicación desarrollada para EnteNova Gnosis 
                    <img src="data:image/png;base64,{encoded}" width="50">""",
                    unsafe_allow_html=True
                )
            else:
                st.caption(f"{description}  \nAplicación desarrollada para EnteNova Gnosis")
    with col2:
        safe_image(logo, width=160)
    st.markdown("---")

# -----------------------------
# (resto del código se queda igual: menú, feeds, draw_live_df, etc.)
# -----------------------------
