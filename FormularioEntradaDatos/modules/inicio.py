import streamlit as st
from .ui import render_global_feed

def render_inicio(supabase):
    # Cabecera
    st.title("🏠 ERP Orbe - Inicio")
    st.markdown("---")

    # Descripción general
    st.markdown("""
    Bienvenido al **ERP Orbe**.  
    Esta aplicación permite gestionar de forma centralizada los principales datos de la empresa:

    - 📂 **Grupos**: entidades o fundaciones vinculadas.  
    - 👥 **Clientes**: academias, empresas o particulares.  
    - 👨‍💼 **Trabajadores**: empleados registrados en el sistema.  
    - 📚 **Productos**: libros y materiales disponibles en el catálogo.  
    - 🧾 **Pedidos**: registro de ventas y operaciones comerciales.  

    Usa el menú lateral para acceder a cada módulo.  
    """)

    # Espacio para separar
    st.markdown("---")

    # Feed global al lado derecho
    st.subheader("📰 Últimas novedades")
    render_global_feed(supabase, in_sidebar=False, limit=6)  # hasta 6 tarjetas en columnas
