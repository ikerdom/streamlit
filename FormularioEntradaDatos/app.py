import streamlit as st
from modules.supa import get_client
from modules.ui import (
    set_page_config, ensure_session_keys,
    login_sidebar, menu_sidebar, render_global_feed,
    apply_custom_css
)

# Importa tus módulos
from modules.inicio import render_inicio
from modules.grupo import render_grupo
from modules.cliente import render_cliente
from modules.trabajador import render_trabajador
from modules.producto import render_producto
from modules.pedido import render_pedido
from modules.pedido_detalle import render_pedido_detalle
from modules.pedido_envio import render_pedido_envio
from modules.catalogos import (
    render_estado_pedido, render_forma_pago,
    render_transportista, render_metodo_envio
)
from modules.cliente_condiciones import render_cliente_condiciones
from modules.cliente_banco import render_cliente_banco
from modules.cliente_direccion import render_cliente_direccion


# -------------------------------
# Configuración inicial
# -------------------------------
set_page_config()
apply_custom_css()     # 🔹 SOLO UNA VEZ
supabase = get_client()
ensure_session_keys()

# -------------------------------
# Sidebar
# -------------------------------
login_sidebar(supabase)
module_key = menu_sidebar()
render_global_feed(supabase)

# -------------------------------
# Router principal
# -------------------------------
if module_key == "inicio":
    render_inicio(supabase)
elif module_key == "grupo":
    render_grupo(supabase)
elif module_key == "cliente":
    render_cliente(supabase)
elif module_key == "cliente_condiciones":
    render_cliente_condiciones(supabase)
elif module_key == "cliente_banco":
    render_cliente_banco(supabase)
elif module_key == "cliente_direccion":
    render_cliente_direccion(supabase)
elif module_key == "trabajador":
    render_trabajador(supabase)
elif module_key == "producto":
    render_producto(supabase)
elif module_key == "pedido":
    render_pedido(supabase)
elif module_key == "pedido_detalle":
    render_pedido_detalle(supabase)
elif module_key == "pedido_envio":
    render_pedido_envio(supabase)
elif module_key == "estadopedido":
    render_estado_pedido(supabase)
elif module_key == "formapago":
    render_forma_pago(supabase)
elif module_key == "transportista":
    render_transportista(supabase)
elif module_key == "metodoenvio":
    render_metodo_envio(supabase)
