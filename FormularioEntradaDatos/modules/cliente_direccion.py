import streamlit as st
import pandas as pd
from .ui import (
    draw_live_df, can_edit, section_header,
    fetch_options
)
from .ui import safe_image

TABLE = "clientedireccion"
FIELDS_LIST = [
    "clientedireccionid","clienteid","tipo","alias","nombredestinatario",
    "email","telefono","direccion1","direccion2","cp","ciudad",
    "provincia","pais","predeterminada","fechaalta"
]

def render_cliente_direccion(supabase):
    # Cabecera con logo
    col1, col2 = st.columns([4,1])
    with col1:
        section_header("📍 Direcciones Cliente",
                       "Gestión de direcciones asociadas a cada cliente (facturación, envío, etc.).")
    with col2:
        safe_image("logo_orbe_sinfondo-1536x479.png")
    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- TAB 1: Formulario
    with tab1:
        clientes, map_clientes = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")

        with st.form("form_clientedireccion"):
            cliente = st.selectbox("Cliente *", clientes)
            tipo = st.selectbox("Tipo *", ["Facturación", "Envío", "Otro"])
            alias = st.text_input("Alias")
            nombre = st.text_input("Nombre Destinatario")

            # 👉 Email y teléfono en la misma fila
            col1, col2 = st.columns(2)
            with col1:
                email = st.text_input("Email")
            with col2:
                telefono = st.text_input("Teléfono")

            # 👉 Direcciones en la misma fila
            col3, col4 = st.columns(2)
            with col3:
                direccion1 = st.text_input("Dirección 1 *")
            with col4:
                direccion2 = st.text_input("Dirección 2")

            # 👉 CP y ciudad/provincia/pais tabulados
            col5, col6 = st.columns(2)
            with col5:
                cp = st.text_input("Código Postal *", max_chars=10)
            with col6:
                ciudad = st.text_input("Ciudad *")

            col7, col8 = st.columns(2)
            with col7:
                provincia = st.text_input("Provincia")
            with col8:
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
                        if st.button("✏️", key=f"edit_{did}"):
                            st.session_state["editing"] = did; st.rerun()
                    else:
                        st.button("✏️", key=f"edit_{did}", disabled=True)

                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"ask_del_{did}"):
                            st.session_state["pending_delete"] = did; st.rerun()
                    else:
                        st.button("🗑️", key=f"ask_del_{did}", disabled=True)

                cols[2].write(row.get("cliente",""))
                cols[3].write(row.get("tipo",""))
                cols[4].write(row.get("alias",""))
                cols[5].write(row.get("nombredestinatario",""))
                cols[6].write(row.get("ciudad",""))
                cols[7].write("✅" if row.get("predeterminada") else "—")

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
                    tipo = st.selectbox("Tipo", ["Facturación","Envío","Otro"], index=0)
                    alias = st.text_input("Alias", cur.get("alias",""))
                    nombre = st.text_input("Nombre Destinatario", cur.get("nombredestinatario",""))

                    col1, col2 = st.columns(2)
                    with col1:
                        email = st.text_input("Email", cur.get("email",""))
                    with col2:
                        telefono = st.text_input("Teléfono", cur.get("telefono",""))

                    col3, col4 = st.columns(2)
                    with col3:
                        direccion1 = st.text_input("Dirección 1", cur.get("direccion1",""))
                    with col4:
                        direccion2 = st.text_input("Dirección 2", cur.get("direccion2",""))

                    col5, col6 = st.columns(2)
                    with col5:
                        cp = st.text_input("Código Postal", cur.get("cp",""))
                    with col6:
                        ciudad = st.text_input("Ciudad", cur.get("ciudad",""))

                    col7, col8 = st.columns(2)
                    with col7:
                        provincia = st.text_input("Provincia", cur.get("provincia",""))
                    with col8:
                        pais = st.text_input("País", cur.get("pais","España"))

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
                            st.session_state["editing"] = None
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
