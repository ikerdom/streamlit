# modules/ui.py
import os
import base64
import pandas as pd
import streamlit as st

# =========================================
# Config / Constantes
# =========================================
ALLOWED_EDITORS = {"hola@entenova.com", "idi1001@alu.ubu.es"}

# Rutas absolutas a /images (para que funcione igual en local y en cloud)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR  = os.path.abspath(os.path.join(BASE_DIR, "..", "images"))

# Logos
LOGO_WATERMARK = os.path.join(IMG_DIR, "entenova1.png")   # marca de agua (opcional)
LOGO_ORBE_PATH = os.path.join(IMG_DIR, "logo_orbe.png")   # logo Orbe (sidebar/top)
LOGO_ENTENOVA_PATH = os.path.join(IMG_DIR, "logo-tree.png")  # logo EnteNova (en caption)

# Imágenes de ayuda (opcionales)
IMG_FORM_1 = os.path.join(IMG_DIR, "Captura.PNG")
IMG_FORM_2 = os.path.join(IMG_DIR, "aceptado.PNG")
IMG_CSV_1  = os.path.join(IMG_DIR, "ejemplo.PNG")
IMG_CSV_2  = os.path.join(IMG_DIR, "1decsv.PNG")


# =========================================
# Configuración de página / sesión
# =========================================
def set_page_config():
    try:
        st.set_page_config(page_title="ERP Orbe", layout="wide")
    except Exception:
        # Streamlit solo permite set_page_config una vez
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


# =========================================
# CSS (marca de agua y estilos)
# =========================================
def apply_custom_css():
    """
    Inyecta una marca de agua suave usando LOGO_WATERMARK.
    No bloquea clicks (pointer-events:none) y queda por detrás (z-index:0).
    """
    if not os.path.exists(LOGO_WATERMARK):
        return

    try:
        with open(LOGO_WATERMARK, "rb") as f:
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


# =========================================
# Utilidades de imagen
# =========================================
def safe_image(relative_path, use_container_width=True, caption=None, width=None):
    """
    Muestra una imagen de /images de forma robusta.
    - Construye ruta absoluta a partir de modules/../images
    - Si falla st.image, hace fallback a base64
    - Si no existe, muestra warning
    """
    img_path = os.path.join(IMG_DIR, relative_path)
    if os.path.exists(img_path):
        try:
            st.image(img_path, use_container_width=use_container_width, caption=caption, width=width)
        except Exception as e:
            try:
                with open(img_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                st.markdown(f"![img](data:image/png;base64,{encoded})")
            except Exception:
                st.warning(f"⚠️ No se pudo cargar la imagen {relative_path} ({e})")
    else:
        st.warning(f"⚠️ Imagen no encontrada: {relative_path}")


# =========================================
# Sidebar (logo + login + menú)
# =========================================
def sidebar_logo_top():
    """
    Logo Orbe arriba del bloque de Acceso.
    """
    if os.path.exists(LOGO_ORBE_PATH):
        try:
            st.sidebar.image(LOGO_ORBE_PATH, width=120)
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
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Credenciales incorrectas")
                except Exception as e:
                    st.sidebar.error(f"Error: {e}")
    else:
        st.sidebar.success(f"Conectado: {st.session_state['user_email']}")
        if st.sidebar.button("Cerrar sesión", use_container_width=True):
            st.session_state["user_email"] = None
            st.session_state["editing"] = None
            st.session_state["pending_delete"] = None
            st.rerun()

def menu_sidebar():
    st.sidebar.markdown("## 📂 Navegación")

    # Inicio
    if st.sidebar.button("🏠 Inicio", key="menu_inicio", use_container_width=True):
        st.session_state["module_key"] = "inicio"

    # Grupo
    if st.sidebar.button("👥 Grupo", key="menu_grupo", use_container_width=True):
        st.session_state["module_key"] = "grupo"

    # Clientes
    if st.sidebar.button("👤 Clientes", key="menu_cliente", use_container_width=True):
        st.session_state["module_key"] = "cliente"

    if st.session_state["module_key"] in [
        "cliente", "cliente_condiciones", "cliente_banco",
        "cliente_direccion", "cliente_familia_descuento"
    ]:
        with st.sidebar.expander("📂 Opciones de Clientes", expanded=True):
            sub = st.radio(
                "Submenú Clientes",
                [
                    "📋 Datos principales",
                    "⚖️ Condiciones",
                    "🏦 Bancos",
                    "🏠 Direcciones",
                    "🏷️ Descuentos por Familia"
                ],
                index=[
                    "cliente",
                    "cliente_condiciones",
                    "cliente_banco",
                    "cliente_direccion",
                    "cliente_familia_descuento"
                ].index(st.session_state["module_key"]),
                label_visibility="collapsed"
            )
            mapping = {
                "📋 Datos principales": "cliente",
                "⚖️ Condiciones": "cliente_condiciones",
                "🏦 Bancos": "cliente_banco",
                "🏠 Direcciones": "cliente_direccion",
                "🏷️ Descuentos por Familia": "cliente_familia_descuento",
            }
            st.session_state["module_key"] = mapping[sub]

    # Trabajador
    if st.sidebar.button("🧑‍💼 Trabajadores", key="menu_trabajador", use_container_width=True):
        st.session_state["module_key"] = "trabajador"

    # Productos (con submenú)
    if st.sidebar.button("📦 Productos", key="menu_producto", use_container_width=True):
        st.session_state["module_key"] = "producto"

    if st.session_state["module_key"] in ["producto", "producto_familia"]:
        with st.sidebar.expander("📂 Opciones de Productos", expanded=True):
            sub = st.radio(
                "Submenú Productos",
                ["📋 Datos principales", "📚 Familias de Producto"],
                index=["producto", "producto_familia"].index(st.session_state["module_key"]),
                label_visibility="collapsed"
            )
            mapping = {
                "📋 Datos principales": "producto",
                "📚 Familias de Producto": "producto_familia",
            }
            st.session_state["module_key"] = mapping[sub]

    # Pedidos (con submenú)
    if st.sidebar.button("🧾 Pedidos", key="menu_pedido", use_container_width=True):
        st.session_state["module_key"] = "pedido"

    if st.session_state["module_key"] in [
        "pedido", "pedido_detalle", "pedido_envio",
        "estadopedido", "transportista", "metodoenvio"
    ]:
        with st.sidebar.expander("📂 Opciones de Pedidos", expanded=True):
            sub = st.radio(
                "Submenú Pedidos",
                [
                    "📋 Datos principales",
                    "📑 Detalle",
                    "🚚 Envío",
                    "📌 Estado Pedido",
                    "🚚 Transportista",
                    "📦 Método de Envío"
                ],
                index=[
                    "pedido",
                    "pedido_detalle",
                    "pedido_envio",
                    "estadopedido",
                    "transportista",
                    "metodoenvio"
                ].index(st.session_state["module_key"]),
                label_visibility="collapsed"
            )
            mapping = {
                "📋 Datos principales": "pedido",
                "📑 Detalle": "pedido_detalle",
                "🚚 Envío": "pedido_envio",
                "📌 Estado Pedido": "estadopedido",
                "🚚 Transportista": "transportista",
                "📦 Método de Envío": "metodoenvio",
            }
            st.session_state["module_key"] = mapping[sub]

    # Configuración
        # Configuración
       # Formas de Pago
    if st.sidebar.button("💳 Formas de Pago", key="menu_formapago", use_container_width=True):
        st.session_state["module_key"] = "formapago"



    # CRM
    if st.sidebar.button("📞 CRM", key="menu_crm", use_container_width=True):
        st.session_state["module_key"] = "crm_actuacion"

    return st.session_state["module_key"]


# =========================================
# Feeds de novedades
# =========================================
def draw_feed_generic(supabase, tabla, campo_nombre, campo_fecha, campo_id, limit=2):
    try:
        order_field = campo_fecha if campo_fecha else campo_id
        r = supabase.table(tabla).select("*").order(order_field, desc=True).limit(limit).execute()
        rows = r.data or []
        if not rows:
            return []
        cards = []
        for row in rows:
            nombre = row.get(campo_nombre, f"{tabla} #{row.get(campo_id,'?')}")
            fecha  = row.get(campo_fecha, row.get(campo_id, ""))
            cards.append(f"📰 **{tabla.capitalize()}** → {nombre} ({fecha})")
        return cards
    except Exception as e:
        return [f"⚠️ Error en {tabla}: {e}"]

def render_global_feed(supabase, in_sidebar=True, limit=2):
    items = [
        ("grupo", "nombre", "fechaalta", "grupoid"),
        ("trabajador", "nombre", "fechaalta", "trabajadorid"),
        ("cliente", "nombrefiscal", "fechaalta", "clienteid"),
        ("producto", "titulo", "fechaalta", "productoid"),
        ("pedido", "numpedido", "fechapedido", "pedidoid"),
        # módulos sin fecha clara → fallback a id para orden
        ("producto_familia", "nombre", "familiaid", "familiaid"),
        ("cliente_familia_descuento", "clienteid", "clienteid", "cliente_familia_descuentoid"),
        ("crm_actuacion", "descripcion", "fecha", "crm_actuacionid"),
    ]

    if in_sidebar:
        with st.sidebar:
            st.markdown("### 📰 Últimas novedades")
            for tabla, campo, fecha, tid in items:
                cards = draw_feed_generic(supabase, tabla, campo, fecha, tid, limit)
                for c in cards:
                    st.info(c)
    else:
        cols = st.columns(3)
        i = 0
        for tabla, campo, fecha, tid in items:
            cards = draw_feed_generic(supabase, tabla, campo, fecha, tid, limit)
            for c in cards:
                with cols[i % 3]:
                    st.info(c)
                i += 1


# =========================================
# Helpers de datos/tablas
# =========================================
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


# =========================================
# Cabeceras e imágenes de ayuda
# =========================================
def render_header(title: str, description: str = "", logo="logo_orbe.png"):
    """
    Header unificado:
    - Título a la izquierda
    - Debajo: descripción (y opcionalmente el texto fijo de EnteNova, si quieres)
    - Logo Orbe a la derecha
    """
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title(title)

        if description:
            # Mostramos la descripción tal cual
            st.caption(description)

            # Si quieres SIEMPRE la coletilla de EnteNova debajo (sin logo):
            if "entenova" not in description.lower():
                st.caption("Aplicación desarrollada para EnteNova Gnosis")

    with col2:
        safe_image(logo, width=160)

    st.markdown("---")


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


# =========================================
# Debug opcional
# =========================================
def debug_table(supabase, tabla):
    try:
        res = supabase.table(tabla).select("*").execute()
        st.code({
            "data": res.data,
            "count": getattr(res, "count", None)
        }, language="json")
    except Exception as e:
        st.error(f"Debug {tabla}: {e}")
