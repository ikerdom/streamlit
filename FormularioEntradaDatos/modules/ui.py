# modules/ui.py
import os
import streamlit as st
import pandas as pd
import base64

# -----------------------------
# Config / Constantes
# -----------------------------
ALLOWED_EDITORS = {"hola@entenova.com", "idi1001@alu.ubu.es"}

# Ruta al logo dentro del proyecto (asegúrate de que existe images/entenova1.png)
LOGO_PATH = os.path.join("images", "entenova1.png")

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
# Marca de agua y CSS seguro
# -----------------------------
def apply_custom_css():
    """
    Añade la marca de agua como imagen base64 de forma NO invasiva:
    - la marca queda en z-index:0
    - los contenedores principales quedan en z-index:1 para que no bloquee interacción
    """
    # Si no existe, no hacemos nada (no rompe la app)
    if not os.path.exists(LOGO_PATH):
        return

    try:
        with open(LOGO_PATH, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
    except Exception:
        return

    # CSS pensado para que la marca esté DETRÁS y no opaque ni bloquee
    css = f"""
    <style>
    /* Marca de agua centrada y sutil */
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
        opacity: 0.07;               /* ajusta visibilidad */
        transform: translate(-50%, -50%);
        pointer-events: none;        /* no interfiere con clicks */
        z-index: 0;                  /* DETRÁS del contenido principal */
    }}

    /* Forzamos que los principales contenedores se muestren ENCIMA */
    /* Selectores funcionan con la estructura actual de Streamlit */
    .appview-container, .main, [data-testid="stApp"] .block-container, .css-1lcbmhc {{
        position: relative;
        z-index: 1;
    }}

    /* Ajustes estéticos sidebar (botones ocupen todo ancho) */
    section[data-testid="stSidebar"] .stButton>button {{
        width: 100%;
        text-align: left;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# -----------------------------
# Sidebar helpers (logo + login + menu)
# -----------------------------
def sidebar_logo_top():
    """
    Muestra el logo (pequeño) arriba del login en sidebar si existe.
    """
    if os.path.exists(LOGO_PATH):
        try:
            st.sidebar.markdown(
                """
                <div style="text-align:center; padding:10px 0 8px 0;">
                    <img src="data:image/png;base64,{}" style="width:110px; height:auto; border-radius:50%;">
                </div>
                """.format(base64.b64encode(open(LOGO_PATH, "rb").read()).decode()),
                unsafe_allow_html=True,
            )
        except Exception:
            # si por alguna razón falla la inyección base64, fallback a st.image
            try:
                st.sidebar.image(LOGO_PATH, width=110)
            except Exception:
                pass

def login_sidebar(supabase):
    # Logo arriba del login
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
# Menú lateral (enlaces)
# -----------------------------
def menu_sidebar():
    st.sidebar.markdown("## 📂 Navegación")

    opciones = {
        # Principales
        "🏠 Inicio": "inicio",
        "👥 Grupo": "grupo",
        "🧑‍💼 Trabajador": "trabajador",
        "📦 Producto": "producto",

        # Clientes y dependencias
        "👥 Clientes": "cliente",
        "↳ Condiciones": "cliente_condiciones",
        "↳ Bancos": "cliente_banco",
        "↳ Direcciones": "cliente_direccion",

        # Pedido y dependencias
        "🧾 Pedido": "pedido",
        "↳ Detalle": "pedido_detalle",
        "↳ Envío": "pedido_envio",
        "↳ Estado Pedido": "estadopedido",
        "↳ Transportista": "transportista",
        "↳ Método de Envío": "metodoenvio",

        # Otro principal
        "💳 Forma de Pago": "formapago",
    }

    if "module_key" not in st.session_state:
        st.session_state["module_key"] = "inicio"

    # Usamos botones para que el estilo sea consistente y no haya radios múltiples seleccionadas
    for label, key in opciones.items():
        if st.sidebar.button(label, key=f"menu_{key}", use_container_width=True):
            st.session_state["module_key"] = key

    return st.session_state["module_key"]

# -----------------------------
# Feed lateral de novedades / feed interno
# -----------------------------
def draw_feed_generic(supabase, tabla, campo_nombre, campo_fecha, campo_id, limit=2):
    try:
        r = supabase.table(tabla).select("*").order(campo_fecha, desc=True).limit(limit).execute()
        rows = r.data or []
        if not rows:
            return []
        cards = []
        for row in rows:
            nombre = row.get(campo_nombre, "N/D")
            fecha  = row.get(campo_fecha, "sin fecha")
            cards.append(f"📰 **{tabla.capitalize()}** → {nombre} ({fecha})")
        return cards
    except Exception as e:
        return [f"⚠️ Error en {tabla}: {e}"]

def render_global_feed(supabase, in_sidebar=True, limit=2):
    """
    - in_sidebar=True -> pinta en el sidebar (con título)
    - in_sidebar=False -> pinta en columnas dentro de la página (sin título)
    """
    items = [
        ("grupo", "nombre", "fechaalta", "grupoid"),
        ("trabajador", "nombre", "fechaalta", "trabajadorid"),
        ("cliente", "nombrefiscal", "fechaalta", "clienteid"),
        ("producto", "titulo", "fechaalta", "productoid"),
        ("pedido", "numpedido", "fechapedido", "pedidoid"),
    ]

    if in_sidebar:
        with st.sidebar:
            st.markdown("### 📰 Últimas novedades")
            for tabla, campo, fecha, tid in items:
                cards = draw_feed_generic(supabase, tabla, campo, fecha, tid, limit)
                for c in cards:
                    st.info(c)
    else:
        # pintar tarjetas en columnas; NO ponemos el título aquí (inicio.py lo controla)
        cols = st.columns(3)
        i = 0
        for tabla, campo, fecha, tid in items:
            cards = draw_feed_generic(supabase, tabla, campo, fecha, tid, limit)
            for c in cards:
                with cols[i % 3]:
                    st.info(c)
                i += 1

# -----------------------------
# Helpers de datos/tablas
# -----------------------------
def draw_live_df(supabase, tabla, columns=None, caption=None, height=360):
    try:
        res = supabase.table(tabla).select("*").execute()
        data = res.data or []
        if not data:
            st.info(f"ℹ️ No hay registros en **{tabla}**.")
            return pd.DataFrame()
        df = pd.DataFrame(data)
        if columns:
            cols = [c for c in columns if c in df.columns]
            if cols:
                df = df[cols]
        st.dataframe(df, use_container_width=True, height=height)
        if caption:
            st.caption(caption)
        return df
    except Exception as e:
        st.error(f"Error cargando {tabla}: {e}")
        return pd.DataFrame()

def fetch_options(supabase, table, id_field, label_field):
    try:
        res = supabase.table(table).select(f"{id_field},{label_field}").order(label_field, desc=False).execute()
        rows = res.data or []
        labels = [r.get(label_field) for r in rows if r.get(label_field) is not None]
        mapping = {r.get(label_field): r.get(id_field) for r in rows if r.get(label_field) is not None}
        return labels, mapping
    except Exception as e:
        st.error(f"⚠️ Error cargando opciones de {table}: {e}")
        return [], {}

# -----------------------------
# Imágenes / Instrucciones
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "images"))
IMG_FORM_1 = os.path.join(IMG_DIR, "Captura.PNG")
IMG_FORM_2 = os.path.join(IMG_DIR, "aceptado.PNG")
IMG_CSV_1  = os.path.join(IMG_DIR, "ejemplo.PNG")
IMG_CSV_2  = os.path.join(IMG_DIR, "1decsv.PNG")

def show_form_images():
    cols = st.columns(2)
    if os.path.exists(IMG_FORM_1):
        with cols[0]:
            st.image(IMG_FORM_1, caption="Formulario (ejemplo)", use_container_width=True)
    if os.path.exists(IMG_FORM_2):
        with cols[1]:
            st.image(IMG_FORM_2, caption="Registro aceptado (ejemplo)", use_container_width=True)

def show_csv_images():
    cols = st.columns(2)
    if os.path.exists(IMG_CSV_1):
        with cols[0]:
            st.image(IMG_CSV_1, caption="CSV (ejemplo)", use_container_width=True)
    if os.path.exists(IMG_CSV_2):
        with cols[1]:
            st.image(IMG_CSV_2, caption="CSV (ejemplo 2)", use_container_width=True)

def section_header(title: str, description: str = ""):
    st.title(title)
    if description:
        st.caption(description)

def instructions_block(title="📖 Ejemplos e Instrucciones"):
    st.subheader(title)
    st.markdown("Aquí puedes ver ejemplos de formularios y cargas CSV.")
    show_form_images()
    show_csv_images()

# -----------------------------
# Debug opcional
# -----------------------------
def debug_table(supabase, tabla):
    try:
        res = supabase.table(tabla).select("*").execute()
        st.code({
            "data": res.data,
            "count": getattr(res, "count", None)
        }, language="json")
    except Exception as e:
        st.error(f"Debug {tabla}: {e}")
