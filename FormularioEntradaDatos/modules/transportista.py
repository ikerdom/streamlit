# modules/transportista.py
import streamlit as st
import pandas as pd
from .ui import section_header, draw_live_df, can_edit
from .ui import safe_image

TABLE = "transportista"
FIELDS_LIST = ["transportistaid", "nombre", "observaciones"]

EDIT_KEY = "editing_transportista"
DEL_KEY  = "pending_delete_transportista"

def render_transportista(supabase):
    # Cabecera con logo
    col1, col2 = st.columns([4,1])
    with col1:
        section_header("🚚 Catálogo: Transportistas", 
                       "Define las empresas de transporte que gestionan los envíos.")
    with col2:
        safe_image("logo_orbe_sinfondo-1536x479.png")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # --- TAB 1: Formulario + Tabla
    with tab1:
        st.subheader("Añadir Transportista")
        with st.form("form_transportista"):
            nombre = st.text_input("Nombre *", max_chars=100)
            obs    = st.text_area("Observaciones", max_chars=300)
            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({"nombre": nombre, "observaciones": obs}).execute()
                    st.success("✅ Transportista insertado")
                    st.rerun()

        st.markdown("#### 📑 Transportistas actuales con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            # Cabecera
            header = st.columns([0.5,0.5,2,3])
            for col, txt in zip(header, ["✏️","🗑️","Nombre","Observaciones"]):
                col.markdown(f"**{txt}**")

            for _, row in df.iterrows():
                tid = int(row["transportistaid"])
                cols = st.columns([0.5,0.5,2,3])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"tra_edit_{tid}"):
                            st.session_state[EDIT_KEY] = tid
                            st.rerun()
                    else:
                        st.button("✏️", key=f"tra_edit_{tid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"tra_del_{tid}"):
                            st.session_state[DEL_KEY] = tid
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"tra_del_{tid}", disabled=True)

                cols[2].write(row.get("nombre",""))
                cols[3].write(row.get("observaciones",""))

            # Confirmación de borrado
            if st.session_state.get(DEL_KEY):
                did = st.session_state[DEL_KEY]
                st.markdown("---")
                st.error(f"⚠️ ¿Eliminar transportista #{did}?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="tra_confirm_del"):
                        supabase.table(TABLE).delete().eq("transportistaid", did).execute()
                        st.success("✅ Transportista eliminado")
                        st.session_state[DEL_KEY] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="tra_cancel_del"):
                        st.session_state[DEL_KEY] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get(EDIT_KEY):
                eid = st.session_state[EDIT_KEY]
                cur = df[df["transportistaid"]==eid].iloc[0].to_dict()
                st.markdown("---")
                st.subheader(f"Editar Transportista #{eid}")
                with st.form("edit_transportista"):
                    nom = st.text_input("Nombre", cur.get("nombre",""))
                    obs = st.text_area("Observaciones", cur.get("observaciones",""))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "nombre": nom,
                                "observaciones": obs
                            }).eq("transportistaid", eid).execute()
                            st.success("✅ Transportista actualizado")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")
                if st.button("❌ Cancelar", key="tra_cancel_edit"):
                    st.session_state[EDIT_KEY] = None
                    st.rerun()

    # --- TAB 2: CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre,observaciones")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_transportista")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_transportista"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # --- TAB 3: Instrucciones
    with tab3:
        st.subheader("📑 Campos de Transportistas")
        st.markdown("""
        - **transportistaid** → Identificador único del transportista.  
        - **nombre** → Nombre de la empresa de transporte (obligatorio).  
        - **observaciones** → Notas adicionales (ej: cobertura nacional, internacional).  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "nombre,observaciones\n"
            "SEUR,Mensajería urgente\n"
            "Correos Express,Servicio nacional",
            language="csv"
        )
