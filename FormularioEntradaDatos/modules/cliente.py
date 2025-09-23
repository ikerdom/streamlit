# modules/cliente.py
import streamlit as st
import pandas as pd
from .ui import (
    render_header, can_edit, fetch_options,
    show_form_images, show_csv_images
)
from .ui_queries import QueryHelper

TABLE = "cliente"
FIELDS_LIST = [
    "clienteid","grupoid","nombrefiscal","nombrecomercial","cif_nif","tipocliente",
    "email","telefono","ciudad","provincia","pais","fechaalta"
]

def render_cliente(supabase):
    # ✅ Cabecera corporativa
    render_header(
        "👥 Gestión de Clientes",
        "Módulo para dar de alta, administrar y editar clientes."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # -------------------------------
    # TAB 1: Formulario + Tabla + Filtros
    # -------------------------------
    with tab1:
        st.subheader("Alta de Cliente")

        grupos, map_grupos = fetch_options(supabase, "grupo", "grupoid", "nombre")

        with st.form("form_cliente"):
            grupo_label     = st.selectbox("Grupo", ["— Ninguno —"] + grupos)
            nombrefiscal    = st.text_input("Nombre Fiscal *", max_chars=200)
            nombrecomercial = st.text_input("Nombre Comercial", max_chars=200)
            cif_nif         = st.text_input("CIF/NIF", max_chars=20)
            tipo_cliente    = st.selectbox(
                "Tipo de Cliente",
                ["Centro de formación","Empresa","Distribuidor","Particular","Otro"]
            )
            email           = st.text_input("Email")
            telefono        = st.text_input("Teléfono", max_chars=50)

            col1, col2 = st.columns(2)
            with col1:
                ciudad = st.text_input("Ciudad", max_chars=100)
            with col2:
                provincia = st.text_input("Provincia", max_chars=100)

            pais = st.selectbox("País", ["España","Portugal","Francia","Alemania"])

            if st.form_submit_button("➕ Insertar"):
                if not nombrefiscal:
                    st.error("❌ Nombre Fiscal es obligatorio")
                else:
                    nuevo = {
                        "grupoid": map_grupos.get(grupo_label),
                        "nombrefiscal": nombrefiscal,
                        "nombrecomercial": nombrecomercial,
                        "cif_nif": cif_nif,
                        "tipocliente": tipo_cliente,
                        "email": email,
                        "telefono": telefono,
                        "ciudad": ciudad,
                        "provincia": provincia,
                        "pais": pais
                    }
                    supabase.table(TABLE).insert(nuevo).execute()
                    st.success("✅ Cliente insertado")
                    st.rerun()

        # -------------------------------
        # 🔎 Herramientas de búsqueda y filtrado
        # -------------------------------
        st.markdown("### 🔎 Herramientas de búsqueda y filtrado")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Buscar / Filtrar clientes"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="cliente_campo")
                valor = st.text_input("Valor a buscar", key="cliente_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"], horizontal=True, key="cliente_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]

                if orden == "Ascendente":
                    df = df.sort_values(by=campo, ascending=True)
                else:
                    df = df.sort_values(by=campo, ascending=False)

        # -------------------------------
        # 📑 Tabla en vivo
        # -------------------------------
        st.markdown("### 📑 Tabla en vivo")
        st.dataframe(df, use_container_width=True)

        # -------------------------------
        # ⚙️ Acciones avanzadas (requiere login)
        # -------------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar clientes (requiere login)"):
            if can_edit():
                for _, row in df.iterrows():
                    cid = int(row["clienteid"])
                    st.markdown(f"**{row.get('nombrefiscal','')} — {row.get('email','')}**")
                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button("✏️ Editar", key=f"cliente_edit_{cid}"):
                            st.session_state["editing_cliente"] = cid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"cliente_del_{cid}"):
                            st.session_state["pending_delete_cliente"] = cid
                            st.rerun()

                    st.markdown("---")

                # Confirmación de borrado
                if st.session_state.get("pending_delete_cliente"):
                    did = st.session_state["pending_delete_cliente"]
                    st.error(f"⚠️ ¿Seguro que quieres eliminar el cliente #{did}?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="cliente_confirm_del"):
                            supabase.table(TABLE).delete().eq("clienteid", did).execute()
                            st.success(f"✅ Cliente {did} eliminado")
                            st.session_state["pending_delete_cliente"] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="cliente_cancel_del"):
                            st.info("Operación cancelada.")
                            st.session_state["pending_delete_cliente"] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get("editing_cliente"):
                    eid = st.session_state["editing_cliente"]
                    cur = df[df["clienteid"] == eid].iloc[0].to_dict()
                    st.subheader(f"Editar Cliente #{eid}")
                    with st.form("edit_cliente"):
                        nf = st.text_input("Nombre Fiscal", cur.get("nombrefiscal",""))
                        nc = st.text_input("Nombre Comercial", cur.get("nombrecomercial",""))
                        em = st.text_input("Email", cur.get("email",""))
                        te = st.text_input("Teléfono", cur.get("telefono",""))

                        col1, col2 = st.columns(2)
                        with col1:
                            ci = st.text_input("Ciudad", cur.get("ciudad",""))
                        with col2:
                            pr = st.text_input("Provincia", cur.get("provincia",""))

                        pa = st.selectbox("País", ["España","Portugal","Francia","Alemania"], index=0)

                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "nombrefiscal": nf,
                                "nombrecomercial": nc,
                                "email": em,
                                "telefono": te,
                                "ciudad": ci,
                                "provincia": pr,
                                "pais": pa
                            }).eq("clienteid", eid).execute()
                            st.success("✅ Cliente actualizado")
                            st.session_state["editing_cliente"] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para acceder a editar/borrar clientes.")

    # -------------------------------
    # TAB 2: CSV
    # -------------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombrefiscal,nombrecomercial,cif_nif,tipocliente,email,telefono,ciudad,provincia,pais")

        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_cliente")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_cliente"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # -------------------------------
    # TAB 3: Instrucciones
    # -------------------------------
    with tab3:
        st.subheader("📑 Campos de Cliente")
        st.markdown("""
        - **clienteid**: identificador único (autonumérico).  
        - **grupoid**: referencia al grupo empresarial (FK).  
        - **nombrefiscal**: razón social del cliente (obligatorio).  
        - **nombrecomercial**: nombre usado públicamente (opcional).  
        - **cif_nif**: identificación fiscal.  
        - **tipocliente**: categoría (Centro de formación, Empresa, Distribuidor, Particular, Otro).  
        - **email**, **telefono**: datos de contacto.  
        - **ciudad**, **provincia**, **pais**: localización del cliente.  
        - **fechaalta**: fecha de alta automática.  
        """)
        st.subheader("📖 Ejemplos e Instrucciones")
        show_form_images()
        show_csv_images()
