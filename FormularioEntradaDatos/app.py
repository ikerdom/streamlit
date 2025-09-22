import streamlit as st
from modules.supa import get_client


from modules.ui import (
    set_page_config, ensure_session_keys, login_sidebar,
    menu_sidebar, render_header, render_global_feed,
    draw_live_df, can_edit, fetch_options, safe_image,
    apply_custom_css
)


# Importa tus módulos
from modules.inicio import render_inicio
from modules.crm_actuacion import render_crm_actuacion

from modules.grupo import render_grupo
from modules.cliente import render_cliente
from modules.trabajador import render_trabajador
from modules.producto import render_producto
from modules.producto_familia import render_producto_familia

from modules.pedido import render_pedido
from modules.pedido_detalle import render_pedido_detalle
from modules.pedido_envio import render_pedido_envio

from modules.estado_pedido import render_estado_pedido
from modules.formapago import render_forma_pago
from modules.metodoenvio import render_metodo_envio
from modules.transportista import render_transportista

from modules.cliente_condiciones import render_cliente_condiciones
from modules.cliente_banco import render_cliente_banco
from modules.cliente_direccion import render_cliente_direccion
from modules.cliente_familia_descuento import render_cliente_familia_descuento

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
elif module_key == "cliente_familia_descuento":
    render_cliente_familia_descuento(supabase)
elif module_key == "trabajador":
    render_trabajador(supabase)
elif module_key == "producto":
    render_producto(supabase)
elif module_key == "producto_familia":
    render_producto_familia(supabase)
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
elif module_key == "crm_actuacion":
    render_crm_actuacion(supabase)
