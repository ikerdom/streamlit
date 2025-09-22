# modules/inicio.py
import streamlit as st
from .ui import render_global_feed, render_header

def render_inicio(supabase):
    # ✅ Cabecera unificada (con logos)
    render_header(
        "🏠 ERP Orbe - Inicio",
        "Aplicación corporativa desarrollada para EnteNova Gnosis"
    )

    # Descripción general
    st.markdown("""
    Bienvenido al **ERP Orbe**.  
    Esta aplicación centraliza la gestión de las principales áreas de la empresa, 
    facilitando el control de datos, procesos y relaciones comerciales.

    ### 📑 Módulos principales
    - 📂 **Grupos** → entidades, fundaciones u organizaciones vinculadas.
    - 👥 **Clientes** → academias, empresas o particulares registrados.
        - 📝 **Condiciones**: formas de pago, facturación y límites de crédito.
        - 🏦 **Bancos**: cuentas bancarias asociadas a cada cliente.
        - 📍 **Direcciones**: sedes, envíos y contactos.
        - 🎯 **Familias de Descuento**: condiciones especiales por familias de productos.
    - 👨‍💼 **Trabajadores** → empleados con sus datos y roles en el sistema.
    - 📚 **Productos** → catálogo de libros, materiales y referencias disponibles.
        - 📚 **Familias de Producto**: categorías para organizar inventario.
    - 🧾 **Pedidos** → registro y control de ventas.
        - 📑 **Detalle del pedido**: líneas de productos en cada pedido.
        - 🚚 **Envíos**: gestión logística y estado.
        - 🚚 **Transportistas**: empresas de transporte asociadas.
        - 📦 **Métodos de envío**: opciones definidas para entregas.
        - 📌 **Estado Pedido**: fases y seguimiento del pedido.
    - 💬 **CRM Actuaciones** → registro de interacciones con **clientes** y **trabajadores** 
      (llamadas, emails, visitas, incidencias).
    - ⚙️ **Configuración**
        - 💳 **Formas de Pago**: métodos de pago admitidos.

    ### ⚙️ Funcionalidades clave
    - Formularios de alta y edición de datos.
    - Importación de datos mediante CSV.
    - Tablas en vivo con edición y borrado inline.
    - Autenticación de usuarios y control de permisos (RLS en Supabase).
    - Menú lateral jerárquico y feed de novedades.
    - Personalización visual con logos, iconos y marca de agua.

    Usa el menú lateral para acceder a cada módulo y comenzar a trabajar con el ERP.
    """)

    st.markdown("---")

    # Feed de novedades (versión en página)
    st.subheader("📰 Últimas novedades")
    render_global_feed(supabase, in_sidebar=False, limit=6)
