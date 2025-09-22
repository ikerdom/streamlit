import streamlit as st
import pandas as pd
from .ui import (
    draw_live_df, can_edit, show_form_images, show_csv_images,
    fetch_options, section_header
)

TABLE = "cliente"
FIELDS_LIST = [
    "clienteid","grupoid","nombrefiscal","nombrecomercial","cif_nif","tipocliente",
    "email","telefono","ciudad","provincia","pais","fechaalta"
]

def render_cliente(supabase):
    section_header("👥 Gestión de Clientes", "Módulo para dar de alta, administrar y editar clientes.")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- Formulario
    with tab1:
        st.subheader("Añadir Cliente")

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
                        "nombrefiscal":nombrefiscal,
                        "nombrecomercial":nombrecomercial,
                        "cif_nif":cif_nif,
                        "tipocliente":tipo_cliente,
                        "email":email,
                        "telefono":telefono,
                        "ciudad":ciudad,
                        "provincia":provincia,
                        "pais":pais
                    }
                    supabase.table(TABLE).insert(nuevo).execute()
                    st.success("✅ Cliente insertado")
                    st.rerun()

        st.markdown("#### 📑 Tabla en vivo con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,2,2,2,2])
            header[0].markdown("**✏️**")
            header[1].markdown("**🗑️**")
            header[2].markdown("**Nombre Fiscal**")
            header[3].markdown("**Nombre Comercial**")
            header[4].markdown("**Email**")
            header[5].markdown("**Ciudad**")

            for _, row in df.iterrows():
                cid = int(row["clienteid"])
                cols = st.columns([0.5,0.5,2,2,2,2])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_{cid}"):
                            st.session_state["editing"] = cid
                            st.rerun()
                    else:
                        st.button("✏️", key=f"edit_{cid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"ask_del_{cid}"):
                            st.session_state["pending_delete"] = cid
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"ask_del_{cid}", disabled=True)

                cols[2].write(row.get("nombrefiscal",""))
                cols[3].write(row.get("nombrecomercial",""))
                cols[4].write(row.get("email",""))
                cols[5].write(row.get("ciudad",""))

            # Confirmar borrado
            if st.session_state.get("pending_delete"):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Seguro que quieres eliminar el cliente #{did}?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del"):
                        supabase.table(TABLE).delete().eq("clienteid", did).execute()
                        st.success(f"✅ Cliente {did} eliminado")
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del"):
                        st.info("Operación cancelada.")
                        st.session_state["pending_delete"] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get("editing"):
                eid = st.session_state["editing"]
                cur = df[df["clienteid"]==eid].iloc[0].to_dict()
                st.markdown("---")
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
                        if can_edit():
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
                            st.session_state["editing"] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombrefiscal,nombrecomercial,cif_nif,tipocliente,email,telefono,ciudad,provincia,pais")

        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_cliente")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_cliente"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.rerun()

        st.markdown("#### 📑 Tabla en vivo")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- Instrucciones
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
