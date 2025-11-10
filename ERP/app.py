# ======================================================
# 🧱 ERP EnteNova Gnosis · Orbe
# ======================================================

import streamlit as st
from datetime import date

# ======================================================
# 🎨 TEMA CORPORATIVO ORBE
# ======================================================
from modules.orbe_theme import apply_orbe_theme
apply_orbe_theme()

# ======================================================
# 🔗 CONEXIÓN A SUPABASE
# ======================================================
from modules.supa_client import get_supabase_client

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
# 🧩 CONEXIÓN A BASE DE DATOS
# ======================================================
supabase = get_supabase_client()
try:
    supabase.table("cliente").select("clienteid").limit(1).execute()
    st.sidebar.success("✅ Conectado a Supabase")
except Exception as e:
    st.sidebar.error("❌ Error de conexión con Supabase")
    st.sidebar.caption(str(e))

# ======================================================
# 🧩 CONTROL DE SESIÓN
# ======================================================
if "user_email" not in st.session_state:
    st.sidebar.warning("🔒 Inicia sesión para continuar")
    render_login()
    st.stop()

# Variables base
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
# 🧩 MENÚ DINÁMICO (por rol)
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
        "💬 Historial / Comunicación",
        "⚠️ Incidencias",
        "📈 Diagramas y métricas",
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

# 🔐 LOGIN
if opcion == "🔐 Iniciar sesión":
    render_login()

# 🚪 CERRAR SESIÓN
elif opcion == "🚪 Cerrar sesión":
    for key in [
        "cliente_actual",
        "cliente_creado",
        "user_email",
        "user_nombre",
        "tipo_usuario",
        "rol_usuario",
        "trabajadorid",
        "pedido_tipo_filtro",
        "modo_incidencias",
    ]:
        st.session_state.pop(key, None)
    st.success("✅ Sesión cerrada correctamente.")
    st.rerun()

# 📊 PANEL GENERAL
elif opcion == "📊 Panel general":
    try:
        from modules.dashboard_general import render_dashboard
        render_dashboard(supabase)
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar el dashboard general: {e}")

# 👥 CLIENTES
elif opcion == "👥 Gestión de clientes":
    st.sidebar.subheader("👥 Gestión de clientes")
    render_cliente_lista(supabase)

# 🧾 POTENCIALES
elif opcion == "🧾 Gestión de potenciales":
    st.sidebar.subheader("🧾 Clientes potenciales / Leads")
    render_cliente_potencial_lista(supabase)

# 📦 PRODUCTOS
elif opcion == "📦 Gestión de productos":
    st.sidebar.subheader("📦 Catálogo de productos")
    render_producto_lista(supabase)

# 💼 PRESUPUESTOS
elif opcion == "💼 Gestión de presupuestos":
    st.sidebar.subheader("💼 Presupuestos")
    render_presupuesto_lista(supabase)

# 🧮 PEDIDOS
elif opcion == "🧮 Gestión de pedidos":
    st.sidebar.subheader("🧮 Pedidos y facturación")
    st.session_state["pedido_tipo_filtro"] = None
    st.session_state["modo_incidencias"] = False
    render_pedido_lista(supabase)

# 🔁 DEVOLUCIONES
elif opcion == "🔁 Devoluciones":
    st.sidebar.subheader("🔁 Pedidos de devolución")
    st.session_state["pedido_tipo_filtro"] = "Devolución"
    st.session_state["modo_incidencias"] = False
    render_pedido_lista(supabase)
    st.session_state["pedido_tipo_filtro"] = None  # limpiar

# 🧾 IMPUESTOS
elif opcion == "🧾 Impuestos":
    st.sidebar.subheader("🧾 Gestión de impuestos")
    render_impuesto_lista(supabase)

# 🏷️ TARIFAS
elif opcion == "🏷️ Gestión de tarifas":
    st.sidebar.subheader("🏷️ Administración de tarifas")
    render_tarifa_admin(supabase)

# 🧮 SIMULADOR DE TARIFAS
elif opcion == "🧮 Simulador de tarifas":
    st.sidebar.subheader("🧮 Simulador de precios y tarifas")
    render_simulador_pedido(supabase)

# 🗓️ CRM
elif opcion == "🗓️ Calendario CRM":
    st.sidebar.subheader("🗓️ Acciones y calendario")
    render_crm_acciones(supabase)

# 💬 HISTORIAL
elif opcion == "💬 Historial / Comunicación":
    st.sidebar.subheader("💬 Historial de mensajes")
    render_historial(supabase)

# ⚠️ INCIDENCIAS
elif opcion == "⚠️ Incidencias":
    st.sidebar.subheader("⚠️ Gestión de incidencias")
    try:
        render_incidencia_lista(supabase)
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar el módulo de incidencias: {e}")

# 📈 DIAGRAMAS
elif opcion == "📈 Diagramas y métricas":
    render_diagramas()

# NUEVO LEAD
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
