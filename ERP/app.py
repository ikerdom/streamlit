# ======================================================
# 🧱 ERP EnteNova Gnosis · Orbe
# ======================================================

import streamlit as st
import subprocess
import webbrowser
import os
import sys
from datetime import date

# ======================================================
# ⚙️ CONFIGURACIÓN GLOBAL
# ======================================================
st.set_page_config(
    page_title="ERP EnteNova Gnosis",
    page_icon="🧱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ======================================================
# 📌 FUNCIÓN LAUNCHER DEL DATAQUERYBOT
# ======================================================
def launch_dataquerybot():
    ruta_bot = os.path.join(os.getcwd(), "dataquerybot")

    env = os.environ.copy()

    env["SUPABASE_URL"] = (
        "postgresql://postgres:EnteNova2025@"
        "db.gqhrbvusvcaytcbnusdx.supabase.co:5432/postgres?sslmode=require"
    )

    env["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

    subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py"],
        cwd=ruta_bot,
        env=env,
        shell=True
    )

    webbrowser.open_new_tab("http://localhost:8501")

# ======================================================
# 🎨 TEMA CORPORATIVO ORBE
# ======================================================
from modules.orbe_theme import apply_orbe_theme
apply_orbe_theme()

# ======================================================
# 🔗 CONEXIÓN A SUPABASE
# ======================================================
from modules.supa_client import get_supabase_client
supabase = get_supabase_client()

try:
    supabase.table("cliente").select("clienteid").limit(1).execute()
    st.sidebar.success("✅ Conectado a Supabase")
    st.session_state["supa"] = supabase
except Exception as e:
    st.sidebar.error("❌ Error de conexión con Supabase")
    st.sidebar.caption(str(e))

# ======================================================
# 🌐 CORE UI / NAVEGACIÓN
# ======================================================
from modules.topbar import render_topbar
from modules.login import render_login
from modules.diagramas import render_diagramas

# ======================================================
# 📦 MÓDULOS PRINCIPALES
# ======================================================
from modules.cliente_lista import render_cliente_lista
from modules.cliente_potencial_lista import render_cliente_potencial_lista
from modules.producto_lista import render_producto_lista
from modules.pedido_lista import render_pedido_lista
from modules.presupuesto_lista import render_presupuesto_lista
from modules.crm_acciones import render_crm_acciones
from modules.historial import render_historial
from modules.lead_form import render_lead_form
from modules.impuesto_lista import render_impuesto_lista
from modules.tarifa_admin import render_tarifa_admin
from modules.incidencia_lista import render_incidencia_lista
from modules.simulador_pedido import render_simulador_pedido

# Campañas
from modules.campania.campania_lista import render as render_campania_lista
from modules.campania.campania_form import render as render_campania_form
from modules.campania.campania_progreso import render as render_campania_progreso
from modules.campania.campania_detalle import render as render_campania_detalle
from modules.campania.campania_informes import render as render_campania_informes
from modules.campania.campania_router import render_campania_router

# ======================================================
# 🧩 CONTROL DE SESIÓN
# ======================================================
if "user_email" not in st.session_state:
    st.sidebar.warning("🔒 Inicia sesión para continuar")
    render_login()
    st.stop()

st.session_state.setdefault("menu_principal", "📊 Panel general")
st.session_state.setdefault("rol_usuario", "Editor")
st.session_state.setdefault("tipo_usuario", "trabajador")

# ======================================================
# 🎨 TOPBAR GLOBAL
# ======================================================
render_topbar(supabase)

# ======================================================
# 🧭 MENÚ LATERAL
# ======================================================
st.sidebar.title("📂 Menú principal")

if "user_email" in st.session_state:
    tipo = st.session_state.get("tipo_usuario", "Trabajador").capitalize()
    rol = st.session_state.get("rol_usuario", "Editor").capitalize()
    st.sidebar.markdown(
        f"**👤 Sesión:** {st.session_state['user_email']}  \n"
        f"**Rol:** {rol} ({tipo})"
    )
    st.sidebar.markdown("---")
else:
    st.sidebar.markdown("**No hay sesión iniciada.**")
    st.sidebar.markdown("---")

tipo_usuario = st.session_state.get("tipo_usuario")

# ======================================================
# 🧩 MENÚ DINÁMICO
# ======================================================
if tipo_usuario == "trabajador":
    menu_principal = [
        "📊 Panel general",
        "👥 Gestión de clientes",
        "🧾 Gestión de potenciales",
        "📦 Gestión de productos",
        "💼 Gestión de presupuestos",
        "🧮 Gestión de pedidos",
        "🔁 Devoluciones",
        "🧾 Impuestos",
        "🏷️ Gestión de tarifas",
        "🧮 Simulador de tarifas",
        "🗓️ Calendario CRM",
        "📣 Campañas",
        "💬 Historial / Comunicación",
        "⚠️ Incidencias",
        "📈 Diagramas y métricas",
        "🤖 IA · Consultas inteligentes",
        "🧪 Feedback IA",
        "🚪 Cerrar sesión",
    ]

elif tipo_usuario == "cliente":
    menu_principal = [
        "👥 Mis datos / Clientes",
        "💬 Historial de contacto",
        "🗓️ Acciones / Calendario",
        "🚪 Cerrar sesión",
    ]

else:
    menu_principal = ["🔐 Iniciar sesión"]

opcion = st.sidebar.radio("Selecciona módulo:", menu_principal, key="menu_principal")

# ======================================================
# 📦 ROUTER PRINCIPAL
# ======================================================
if opcion == "🔐 Iniciar sesión":
    render_login()

elif opcion == "🚪 Cerrar sesión":
    for key in [
        "cliente_actual", "cliente_creado", "user_email", "user_nombre",
        "tipo_usuario", "rol_usuario", "trabajadorid",
        "pedido_tipo_filtro", "modo_incidencias"
    ]:
        st.session_state.pop(key, None)

    st.success("✅ Sesión cerrada correctamente.")
    st.rerun()

elif opcion == "📊 Panel general":
    try:
        from modules.dashboard_general import render_dashboard
        render_dashboard(supabase)
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar el dashboard general: {e}")

elif opcion == "👥 Gestión de clientes":
    st.sidebar.subheader("👥 Gestión de clientes")
    render_cliente_lista(supabase)

elif opcion == "🧾 Gestión de potenciales":
    st.sidebar.subheader("🧾 Clientes potenciales / Leads")
    render_cliente_potencial_lista(supabase)

elif opcion == "📦 Gestión de productos":
    st.sidebar.subheader("📦 Catálogo de productos")
    render_producto_lista(supabase)

elif opcion == "💼 Gestión de presupuestos":
    st.sidebar.subheader("💼 Gestión de presupuestos")
    render_presupuesto_lista(supabase)

elif opcion == "🧮 Gestión de pedidos":
    st.sidebar.subheader("🧮 Pedidos y facturación")
    st.session_state["pedido_tipo_filtro"] = None
    st.session_state["modo_incidencias"] = False
    render_pedido_lista(supabase)

elif opcion == "🔁 Devoluciones":
    st.sidebar.subheader("🔁 Pedidos de devolución")
    st.session_state["pedido_tipo_filtro"] = "Devolución"
    st.session_state["modo_incidencias"] = False
    render_pedido_lista(supabase)
    st.session_state["pedido_tipo_filtro"] = None

elif opcion == "🧾 Impuestos":
    st.sidebar.subheader("🧾 Gestión de impuestos")
    render_impuesto_lista(supabase)

elif opcion == "🏷️ Gestión de tarifas":
    st.sidebar.subheader("🏷️ Administración de tarifas")
    render_tarifa_admin(supabase)

elif opcion == "🧮 Simulador de tarifas":
    st.sidebar.subheader("🧮 Simulador de precios y tarifas")
    render_simulador_pedido(supabase)

elif opcion == "🤖 IA · Consultas Inteligentes":
    st.subheader("🤖 IA · Consultas Inteligentes")
    st.info("Haz clic para abrir el DataQueryBot completo en una nueva ventana.")
    
    if st.button("🔗 Abrir DataQueryBot Completo"):
        launch_dataquerybot()

elif opcion == "🗓️ Calendario CRM":
    st.sidebar.subheader("🗓️ Acciones y calendario")
    render_crm_acciones(supabase)

elif opcion == "📣 Campañas":
    st.sidebar.subheader("📣 Campañas comerciales")
    render_campania_router(supabase)

elif opcion == "💬 Historial / Comunicación":
    st.sidebar.subheader("💬 Historial de mensajes")
    render_historial(supabase)

elif opcion == "⚠️ Incidencias":
    st.sidebar.subheader("⚠️ Gestión de incidencias")
    try:
        render_incidencia_lista(supabase)
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar el módulo de incidencias: {e}")

elif opcion == "📈 Diagramas y métricas":
    render_diagramas()

elif opcion == "Nuevo lead":
    render_lead_form()

# ======================================================
# 📋 PIE DE PÁGINA
# ======================================================
st.markdown("---")
st.caption(
    "© 2025 **EnteNova Gnosis · Orbe**  |  "
    "Desarrollado por *Iker Domínguez Ibáñez*  |  "
    "Versión interna de desarrollo · build 1.0.0"
)
