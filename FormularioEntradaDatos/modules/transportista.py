import streamlit as st
import pandas as pd
from .ui import (
    draw_live_df, can_edit, show_form_images, show_csv_images,
    section_header
)

TABLE = "transportista"
FIELDS_LIST = ["transportistaid", "nombre", "observaciones"]

def render_transportista(supabase):
    section_header("🚚 Catálogo: Transportistas", 
                   "Define las empresas de transporte que gestionan los envíos.")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- Formulario
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

        st.markdown("#### 📑 Tabla en vivo con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,3,4,1])
            header[0].markdown("**✏️**")
            header[1].markdown("**🗑️**")
            header[2].markdown("**Nombre**")
            header[3].markdown("**Observaciones**")
            header[4].markdown("**ID**")

            for _, row in df.iterrows():
                tid = int(row["transportistaid"])
                cols = st.columns([0.5,0.5,3,4,1])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"tra_edit_{tid}"):
                            st.session_state["editing"] = tid
                            st.session_state["editing_table"] = TABLE
                            st.rerun()
                    else:
                        st.button("✏️", key=f"tra_edit_{tid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"tra_delask_{tid}"):
                            st.session_state["pending_delete"] = tid
                            st.session_state["pending_table"] = TABLE
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"tra_delask_{tid}", disabled=True)

                cols[2].write(row.get("nombre",""))
                cols[3].write(row.get("observaciones",""))
                cols[4].write(tid)

            # Confirmar borrado
            if (st.session_state.get("pending_delete") 
                and st.session_state.get("pending_table") == TABLE):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Seguro que quieres eliminar el transportista #{did}?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="tra_confirm_del"):
                        supabase.table(TABLE).delete().eq("transportistaid", did).execute()
                        st.success("✅ Transportista eliminado")
                        st.session_state["pending_delete"] = None
                        st.session_state["pending_table"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="tra_cancel_del"):
                        st.session_state["pending_delete"] = None
                        st.session_state["pending_table"] = None
                        st.rerun()

            # Edición inline
            if (st.session_state.get("editing") 
                and st.session_state.get("editing_table") == TABLE):
                eid = st.session_state["editing"]
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
                            st.session_state["editing"] = None
                            st.session_state["editing_table"] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- CSV
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

        st.markdown("#### 📑 Tabla en vivo")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- Instrucciones
    with tab3:
        st.subheader("📖 Ejemplos e Instrucciones")
        st.code("SEUR,Mensajería urgente\nCorreos Express,Servicio nacional", language="csv")
        show_form_images()
        show_csv_images()
