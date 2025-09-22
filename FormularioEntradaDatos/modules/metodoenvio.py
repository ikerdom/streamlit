# modules/metodoenvio.py
import streamlit as st
import pandas as pd
from .ui import render_header, draw_live_df, can_edit

TABLE = "metodoenvio"
FIELDS_LIST = ["metodoenvioid", "nombre", "descripcion"]

EDIT_KEY = "editing_metodo"
DEL_KEY  = "pending_delete_metodo"

def render_metodo_envio(supabase):
    # ✅ Cabecera unificada
    render_header(
        "📦 Catálogo: Métodos de Envío",
        "Define los métodos de envío disponibles (urgente, estándar, etc.)."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # --- TAB 1: Formulario + Tabla
    with tab1:
        st.subheader("Añadir Método de Envío")
        with st.form("form_metodo"):
            nombre = st.text_input("Nombre *", max_chars=150)
            descripcion = st.text_area("Descripción", max_chars=300)
            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({
                        "nombre": nombre,
                        "descripcion": descripcion
                    }).execute()
                    st.success("✅ Método insertado")
                    st.rerun()

        st.markdown("#### 📑 Métodos actuales con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,2,3])
            for col, txt in zip(header, ["✏️","🗑️","Nombre","Descripción"]):
                col.markdown(f"**{txt}**")

            for _, row in df.iterrows():
                mid = int(row["metodoenvioid"])
                cols = st.columns([0.5,0.5,2,3])

                cols[2].write(row.get("nombre",""))
                cols[3].write(row.get("descripcion",""))

                # Editar
                with cols[0]:
                    if can_edit() and st.button("✏️", key=f"edit_metodo_{mid}"):
                        st.session_state[EDIT_KEY] = mid; st.rerun()
                # Borrar
                with cols[1]:
                    if can_edit() and st.button("🗑️", key=f"del_metodo_{mid}"):
                        st.session_state[DEL_KEY] = mid; st.rerun()

            # Confirmar borrado
            if st.session_state.get(DEL_KEY):
                did = st.session_state[DEL_KEY]
                st.markdown("---")
                st.error(f"⚠️ ¿Eliminar método de envío #{did}?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="metodo_confirm_del"):
                        supabase.table(TABLE).delete().eq("metodoenvioid", did).execute()
                        st.success("✅ Método eliminado")
                        st.session_state[DEL_KEY] = None; st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="metodo_cancel_del"):
                        st.session_state[DEL_KEY] = None; st.rerun()

            # Edición inline
            if st.session_state.get(EDIT_KEY):
                eid = st.session_state[EDIT_KEY]
                cur = df[df["metodoenvioid"]==eid].iloc[0].to_dict()
                st.markdown("---"); st.subheader(f"Editar Método #{eid}")
                with st.form("edit_metodo"):
                    nombre = st.text_input("Nombre", cur.get("nombre",""))
                    descripcion = st.text_area("Descripción", cur.get("descripcion",""))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "nombre": nombre,
                                "descripcion": descripcion
                            }).eq("metodoenvioid", eid).execute()
                            st.success("✅ Método actualizado")
                            st.session_state[EDIT_KEY] = None; st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")
                if st.button("❌ Cancelar", key="metodo_cancel_edit"):
                    st.session_state[EDIT_KEY] = None; st.rerun()

    # --- TAB 2: CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre,descripcion")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_metodoenvio")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_metodoenvio"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}"); st.rerun()

    # --- TAB 3: Instrucciones
    with tab3:
        st.subheader("📑 Campos de Métodos de Envío")
        st.markdown("""
        - **metodoenvioid** → identificador único del método.  
        - **nombre** → nombre del método de envío (ej: Urgente, Estándar).  
        - **descripcion** → detalle adicional sobre el método.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "nombre,descripcion\nUrgente,Entrega en 24h\nEstándar,Entrega en 3-5 días",
            language="csv"
        )
