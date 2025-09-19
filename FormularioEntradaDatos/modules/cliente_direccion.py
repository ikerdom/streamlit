import streamlit as st
import pandas as pd
from .ui import (
    draw_live_df, can_edit, section_header,
    fetch_options, show_form_images, show_csv_images
)

TABLE = "clientedireccion"
FIELDS_LIST = [
    "clientedireccionid","clienteid","tipo","alias","nombredestinatario",
    "email","telefono","direccion1","direccion2","cp","ciudad",
    "provincia","pais","predeterminada","fechaalta"
]

def render_cliente_direccion(supabase):
    section_header("📍 Direcciones Cliente",
                   "Gestión de direcciones asociadas a cada cliente (facturación, envío, etc.).")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- Formulario
    with tab1:
        clientes, map_clientes = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")

        with st.form("form_clientedireccion"):
            cliente = st.selectbox("Cliente *", clientes)
            tipo = st.selectbox("Tipo *", ["Facturación", "Envío", "Otro"])
            alias = st.text_input("Alias")
            nombre = st.text_input("Nombre Destinatario")
            email = st.text_input("Email")
            telefono = st.text_input("Teléfono")
            direccion1 = st.text_input("Dirección 1 *")
            direccion2 = st.text_input("Dirección 2")
            cp = st.text_input("Código Postal *", max_chars=10)
            ciudad = st.text_input("Ciudad *")
            provincia = st.text_input("Provincia")
            pais = st.text_input("País", value="España")
            predeterminado = st.checkbox("Predeterminada", value=False)

            if st.form_submit_button("➕ Insertar"):
                if not cliente or not direccion1 or not cp or not ciudad:
                    st.error("❌ Cliente, Dirección, CP y Ciudad obligatorios")
                else:
                    nuevo = {
                        "clienteid": map_clientes.get(cliente),
                        "tipo": tipo,
                        "alias": alias,
                        "nombredestinatario": nombre,
                        "email": email,
                        "telefono": telefono,
                        "direccion1": direccion1,
                        "direccion2": direccion2,
                        "cp": cp,
                        "ciudad": ciudad,
                        "provincia": provincia,
                        "pais": pais,
                        "predeterminada": predeterminado
                    }
                    supabase.table(TABLE).insert(nuevo).execute()
                    st.success("✅ Dirección añadida")
                    st.rerun()

        st.markdown("#### 📑 Direcciones actuales con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,2,2,2,2])
            header[0].markdown("**✏️**")
            header[1].markdown("**🗑️**")
            header[2].markdown("**Alias**")
            header[3].markdown("**Dirección1**")
            header[4].markdown("**Ciudad**")
            header[5].markdown("**Predet.**")

            for _, row in df.iterrows():
                did = int(row["clientedireccionid"])
                cols = st.columns([0.5,0.5,2,2,2,2])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_{did}"):
                            st.session_state["editing"] = did; st.rerun()
                    else:
                        st.button("✏️", key=f"edit_{did}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"ask_del_{did}"):
                            st.session_state["pending_delete"] = did; st.rerun()
                    else:
                        st.button("🗑️", key=f"ask_del_{did}", disabled=True)

                cols[2].write(row.get("alias",""))
                cols[3].write(row.get("direccion1",""))
                cols[4].write(row.get("ciudad",""))
                cols[5].write("✅" if row.get("predeterminada") else "—")

            # Confirmar borrado
            if st.session_state.get("pending_delete"):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Eliminar dirección #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del"):
                        supabase.table(TABLE).delete().eq("clientedireccionid", did).execute()
                        st.success("✅ Dirección eliminada")
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del"):
                        st.session_state["pending_delete"] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get("editing"):
                eid = st.session_state["editing"]
                cur = df[df["clientedireccionid"]==eid].iloc[0].to_dict()
                st.markdown("---"); st.subheader(f"Editar Dirección #{eid}")
                with st.form("edit_direccion"):
                    alias = st.text_input("Alias", cur.get("alias",""))
                    direccion1 = st.text_input("Dirección 1", cur.get("direccion1",""))
                    ciudad = st.text_input("Ciudad", cur.get("ciudad",""))
                    provincia = st.text_input("Provincia", cur.get("provincia",""))
                    pred = st.checkbox("Predeterminada", value=cur.get("predeterminada",False))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "alias": alias,
                                "direccion1": direccion1,
                                "ciudad": ciudad,
                                "provincia": provincia,
                                "predeterminada": pred
                            }).eq("clientedireccionid", eid).execute()
                            st.success("✅ Dirección actualizada")
                            st.session_state["editing"] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,tipo,alias,nombredestinatario,email,telefono,direccion1,direccion2,cp,ciudad,provincia,pais,predeterminada")

        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_direccion")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_direccion"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.rerun()

    # --- Instrucciones
    with tab3:
        st.subheader("📖 Ejemplos CSV")
        st.code("clienteid,tipo,alias,nombredestinatario,email,telefono,direccion1,direccion2,cp,ciudad,provincia,pais,predeterminada\n1,Envío,Principal,María López,ml@example.com,600123456,Calle Mayor 1,,28001,Madrid,Madrid,España,true", language="csv")
        show_form_images()
        show_csv_images()
