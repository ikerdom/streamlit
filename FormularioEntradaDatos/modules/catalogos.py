import streamlit as st
import pandas as pd
from .ui import (
    draw_live_df, can_edit, section_header,
    show_form_images, show_csv_images
)

# ======================
# ESTADO PEDIDO
# ======================
def render_estado_pedido(supabase):
    TABLE = "estadopedido"
    FIELDS_LIST = ["estadopedidoid", "nombre"]

    section_header("📋 Catálogo: Estado Pedido",
                   "Define los distintos estados posibles de un pedido (ej: pendiente, enviado, entregado).")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # Formulario
    with tab1:
        with st.form("form_estadopedido"):
            nombre = st.text_input("Nombre Estado *", max_chars=50)
            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({"nombre": nombre}).execute()
                    st.success("✅ Estado añadido")
                    st.experimental_rerun()
        st.markdown("#### 📑 Estados actuales")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_estadopedido")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_estadopedido"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.experimental_rerun()
        st.markdown("#### 📑 Estados actuales")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # Instrucciones
    with tab3:
        show_form_images()
        show_csv_images()

# ======================
# FORMA PAGO
# ======================
def render_forma_pago(supabase):
    TABLE = "formapago"
    FIELDS_LIST = ["formapagoid", "nombre"]

    section_header("💳 Catálogo: Forma de Pago",
                   "Opciones de pago aceptadas (transferencia, tarjeta, PayPal...).")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    with tab1:
        with st.form("form_formapago"):
            nombre = st.text_input("Nombre Forma Pago *", max_chars=50)
            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({"nombre": nombre}).execute()
                    st.success("✅ Forma de pago añadida")
                    st.experimental_rerun()
        st.markdown("#### 📑 Formas de pago actuales")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_formapago")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_formapago"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.experimental_rerun()
        st.markdown("#### 📑 Formas de pago actuales")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    with tab3:
        show_form_images()
        show_csv_images()

# ======================
# TRANSPORTISTA
# ======================
def render_transportista(supabase):
    TABLE = "transportista"
    FIELDS_LIST = ["transportistaid", "nombre", "observaciones"]

    section_header("🚛 Catálogo: Transportistas",
                   "Lista de empresas de transporte con las que se gestionan los envíos.")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    with tab1:
        with st.form("form_transportista"):
            nombre = st.text_input("Nombre Transportista *", max_chars=100)
            obs = st.text_area("Observaciones", max_chars=300)
            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({"nombre": nombre, "observaciones": obs}).execute()
                    st.success("✅ Transportista añadido")
                    st.experimental_rerun()
        st.markdown("#### 📑 Transportistas actuales")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre,observaciones")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_transportista")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_transportista"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.experimental_rerun()
        st.markdown("#### 📑 Transportistas actuales")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    with tab3:
        show_form_images()
        show_csv_images()

# ======================
# MÉTODO ENVÍO
# ======================
def render_metodo_envio(supabase):
    TABLE = "metodoenvio"
    FIELDS_LIST = ["metodoenvioid", "nombre", "observaciones"]

    section_header("📦 Catálogo: Métodos de Envío",
                   "Modos de entrega disponibles (mensajería, recogida en tienda...).")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    with tab1:
        with st.form("form_metodoenvio"):
            nombre = st.text_input("Nombre Método Envío *", max_chars=100)
            obs = st.text_area("Observaciones", max_chars=300)
            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({"nombre": nombre, "observaciones": obs}).execute()
                    st.success("✅ Método añadido")
                    st.experimental_rerun()
        st.markdown("#### 📑 Métodos actuales")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre,observaciones")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_metodoenvio")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_metodoenvio"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.experimental_rerun()
        st.markdown("#### 📑 Métodos actuales")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    with tab3:
        show_form_images()
        show_csv_images()
