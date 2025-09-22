import streamlit as st
import pandas as pd
from .ui import (
    render_header, draw_live_df, can_edit, fetch_options
)

TABLE = "clientedireccion"
FIELDS_LIST = [
    "clientedireccionid","clienteid","tipo","alias","nombredestinatario",
    "email","telefono","direccion1","direccion2","cp","ciudad",
    "provincia","pais","predeterminada","fechaalta"
]

EDIT_KEY = "editing_dir"
DEL_KEY  = "pending_delete_dir"

def render_cliente_direccion(supabase):
    # ✅ Cabecera corporativa con logo
    render_header(
        "📍 Direcciones Cliente",
        "Gestión de direcciones asociadas a cada cliente (facturación, envío, etc.)."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- TAB 1: Formulario
    with tab1:
        clientes, map_clientes = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")

        with st.form("form_clientedireccion"):
            cliente = st.selectbox("Cliente *", clientes)
            tipo = st.selectbox("Tipo *", ["Facturación", "Envío", "Otro"])
            alias = st.text_input("Alias")
            nombre = st.text_input("Nombre Destinatario")

            col1, col2 = st.columns(2)
            email    = col1.text_input("Email")
            telefono = col2.text_input("Teléfono")

            col3, col4 = st.columns(2)
            direccion1 = col3.text_input("Dirección 1 *")
            direccion2 = col4.text_input("Dirección 2")

            col5, col6 = st.columns(2)
            cp     = col5.text_input("Código Postal *", max_chars=10)
            ciudad = col6.text_input("Ciudad *")

            col7, col8 = st.columns(2)
            provincia = col7.text_input("Provincia")
            pais      = col8.text_input("País", value="España")

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
            clientes_map = {c["clienteid"]: c["nombrefiscal"]
                            for c in supabase.table("cliente")
                            .select("clienteid,nombrefiscal").execute().data}
            df["cliente"] = df["clienteid"].map(clientes_map)

            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,2,2,2,2,2,2])
            for col, text in zip(header, ["✏️","🗑️","Cliente","Tipo","Alias","Destinatario","Ciudad","Predet."]):
                col.markdown(f"**{text}**")

            for _, row in df.iterrows():
                did = int(row["clientedireccionid"])
                cols = st.columns([0.5,0.5,2,2,2,2,2,2])

                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_dir_{did}"):
                            st.session_state[EDIT_KEY] = did; st.rerun()
                    else:
                        st.button("✏️", key=f"edit_dir_{did}", disabled=True)

                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"del_dir_{did}"):
                            st.session_state[DEL_KEY] = did; st.rerun()
                    else:
                        st.button("🗑️", key=f"del_dir_{did}", disabled=True)

                cols[2].write(row.get("cliente",""))
                cols[3].write(row.get("tipo",""))
                cols[4].write(row.get("alias",""))
                cols[5].write(row.get("nombredestinatario",""))
                cols[6].write(row.get("ciudad",""))
                cols[7].write("✅" if row.get("predeterminada") else "—")

            # Confirmar borrado
            if st.session_state.get(DEL_KEY):
                did = st.session_state[DEL_KEY]
                st.markdown("---")
                st.error(f"⚠️ ¿Eliminar dirección #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del_dir"):
                        supabase.table(TABLE).delete().eq("clientedireccionid", did).execute()
                        st.success("✅ Dirección eliminada")
                        st.session_state[DEL_KEY] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del_dir"):
                        st.session_state[DEL_KEY] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get(EDIT_KEY):
                eid = st.session_state[EDIT_KEY]
                cur = df[df["clientedireccionid"]==eid].iloc[0].to_dict()
                st.markdown("---"); st.subheader(f"Editar Dirección #{eid}")
                with st.form(f"edit_dir_{eid}"):
                    tipo  = st.selectbox("Tipo", ["Facturación","Envío","Otro"],
                                         index=(["Facturación","Envío","Otro"].index(cur.get("tipo")) if cur.get("tipo") in ["Facturación","Envío","Otro"] else 0))
                    alias = st.text_input("Alias", cur.get("alias",""))
                    nombre = st.text_input("Nombre Destinatario", cur.get("nombredestinatario",""))

                    col1, col2 = st.columns(2)
                    email    = col1.text_input("Email", cur.get("email",""))
                    telefono = col2.text_input("Teléfono", cur.get("telefono",""))

                    col3, col4 = st.columns(2)
                    direccion1 = col3.text_input("Dirección 1", cur.get("direccion1",""))
                    direccion2 = col4.text_input("Dirección 2", cur.get("direccion2",""))

                    col5, col6 = st.columns(2)
                    cp     = col5.text_input("Código Postal", cur.get("cp",""))
                    ciudad = col6.text_input("Ciudad", cur.get("ciudad",""))

                    col7, col8 = st.columns(2)
                    provincia = col7.text_input("Provincia", cur.get("provincia",""))
                    pais      = col8.text_input("País", cur.get("pais","España"))

                    pred = st.checkbox("Predeterminada", value=cur.get("predeterminada",False))

                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
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
                                "predeterminada": pred
                            }).eq("clientedireccionid", eid).execute()
                            st.success("✅ Dirección actualizada")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- TAB 2: CSV
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

    # --- TAB 3: Instrucciones
    with tab3:
        st.subheader("📑 Campos de Direcciones de Cliente")
        st.markdown("""
        - **clientedireccionid** → Identificador único de la dirección.  
        - **clienteid** → Cliente al que pertenece.  
        - **tipo** → Tipo de dirección (Facturación, Envío, Otro).  
        - **alias** → Nombre corto o referencia (ej: "Oficina Madrid").  
        - **nombredestinatario** → Persona o entidad que recibirá la correspondencia.  
        - **email / teléfono** → Datos de contacto.  
        - **direccion1 / direccion2** → Dirección completa (línea 1 obligatoria).  
        - **cp, ciudad, provincia, pais** → Localización detallada.  
        - **predeterminada** → Indica si es la dirección principal del cliente.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "clienteid,tipo,alias,nombredestinatario,email,telefono,direccion1,direccion2,cp,ciudad,provincia,pais,predeterminada\n"
            "1,Envío,Principal,María López,ml@example.com,600123456,Calle Mayor 1,,28001,Madrid,Madrid,España,true",
            language="csv"
        )
