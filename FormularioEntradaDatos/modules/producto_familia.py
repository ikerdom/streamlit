# modules/producto_familia.py
import streamlit as st
import pandas as pd
from .ui import draw_live_df, can_edit, section_header
from .ui import safe_image
TABLE = "producto_familia"
FIELDS_LIST = ["familiaid", "nombre"]

EDIT_KEY = "editing_pf"
DEL_KEY  = "pending_delete_pf"

def render_producto_familia(supabase):
    # Cabecera con logo a la derecha
    col1, col2 = st.columns([4,1])
    with col1:
        section_header("📚 Familias de Producto",
                       "Catálogo de familias de productos para organizar el inventario.")
    with col2:
        safe_image("logo_orbe_sinfondo-1536x479.png")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- TAB 1: Formulario + Tabla
    with tab1:
        st.subheader("Añadir Familia de Producto")

        with st.form("form_producto_familia"):
            nombre = st.text_input("Nombre *", max_chars=150)

            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({"nombre": nombre}).execute()
                    st.success("✅ Familia añadida")
                    st.rerun()

        st.markdown("#### 📑 Familias actuales")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            # Header
            header = st.columns([0.5, 0.5, 3])
            header[0].markdown("**✏️**")
            header[1].markdown("**🗑️**")
            header[2].markdown("**Nombre**")

            for _, row in df.iterrows():
                fid = int(row["familiaid"])
                cols = st.columns([0.5, 0.5, 3])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_pf_{fid}"):
                            st.session_state[EDIT_KEY] = fid
                            st.rerun()
                    else:
                        st.button("✏️", key=f"edit_pf_{fid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"ask_del_pf_{fid}"):
                            st.session_state[DEL_KEY] = fid
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"ask_del_pf_{fid}", disabled=True)

                cols[2].write(row.get("nombre", ""))

            # Confirmar borrado
            if st.session_state.get(DEL_KEY):
                did = st.session_state[DEL_KEY]
                st.markdown("---")
                st.error(f"⚠️ ¿Seguro que quieres eliminar la familia #{did}?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del_pf"):
                        supabase.table(TABLE).delete().eq("familiaid", did).execute()
                        st.success("✅ Familia eliminada")
                        st.session_state[DEL_KEY] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del_pf"):
                        st.info("Operación cancelada.")
                        st.session_state[DEL_KEY] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get(EDIT_KEY):
                eid = st.session_state[EDIT_KEY]
                cur = df[df["familiaid"] == eid].iloc[0].to_dict()
                st.markdown("---")
                st.subheader(f"Editar Familia #{eid}")
                with st.form(f"edit_pf_{eid}"):
                    nombre = st.text_input("Nombre", cur.get("nombre", ""))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "nombre": nombre
                            }).eq("familiaid", eid).execute()
                            st.success("✅ Familia actualizada")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- TAB 2: CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_producto_familia")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_producto_familia"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # --- TAB 3: Instrucciones
    with tab3:
        st.subheader("📑 Campos de Familias de Producto")
        st.markdown("""
        - **familiaid** → Identificador único de la familia.  
        - **nombre** → Nombre de la familia (ej: Libros ESO, Idiomas).  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code("nombre\nLibros ESO\nIdiomas", language="csv")
