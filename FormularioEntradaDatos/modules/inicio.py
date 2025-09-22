import streamlit as st
from .ui import render_global_feed
from .ui import safe_image

def render_inicio(supabase):
    # Cabecera con título a la izquierda y logo a la derecha
    col1, col2 = st.columns([4, 1])  # texto más ancho, logo más estrecho
    with col1:
        st.title("🏠 ERP Orbe - Inicio")
        st.caption("Aplicación corporativa desarrollada para **EnteNova Gnosis**")
    with col2:
        safe_image("logo_orbe_sinfondo-1536x479.png")

    st.markdown("---")

    # Descripción general de la app
    st.markdown("""
    Bienvenido al **ERP Orbe**.  
    Esta aplicación centraliza la gestión de las principales áreas de la empresa, 
    facilitando el control de datos, procesos y relaciones comerciales.

    ### 📑 Módulos principales
    - 📂 **Grupos** → entidades, fundaciones u organizaciones vinculadas.
    - 👥 **Clientes** → academias, empresas o particulares registrados.
        - 📝 **Condiciones**: formas de pago, facturación y límites de crédito.
        - 🏦 **Banco**: cuentas bancarias asociadas a cada cliente.
        - 📍 **Direcciones**: sedes, envíos y contactos.
        - 🎯 **Familias de Descuento**: condiciones especiales por familias de productos.
    - 👨‍💼 **Trabajadores** → empleados con sus datos y roles en el sistema.
    - 📚 **Productos** → catálogo de libros, materiales y referencias disponibles.
    - 🧾 **Pedidos** → registro y control de ventas.
        - 📦 **Detalle del pedido**: líneas de productos.
        - 🚚 **Envíos**: transportistas, métodos de envío y estado logístico.
    - 💬 **CRM Actuaciones** → registro de interacciones con **clientes** y **trabajadores** 
      (llamadas, emails, visitas, incidencias).

    ### ⚙️ Funcionalidades clave
    - Formularios de alta y edición de datos.
    - Importación de datos mediante CSV.
    - Tablas en vivo con edición y borrado inline.
    - Autenticación de usuarios y control de permisos (RLS en Supabase).
    - Menú lateral jerárquico y feed de novedades.
    - Personalización visual con logo, iconos y marca de agua.

    Usa el menú lateral para acceder a cada módulo y comenzar a trabajar con el ERP.
    """)

    st.markdown("---")

    # Feed de novedades
    st.subheader("📰 Últimas novedades")
    render_global_feed(supabase, in_sidebar=False, limit=6)
