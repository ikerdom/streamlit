# modules/producto_familia.py
import streamlit as st
import pandas as pd
from .ui import render_header, can_edit

TABLE = "producto_familia"
FIELDS_LIST = ["familiaid", "nombre"]

EDIT_KEY = "editing_pf"
DEL_KEY  = "pending_delete_pf"

def render_producto_familia(supabase):
    # ✅ Cabecera
    render_header(
        "📚 Familias de Producto",
        "Catálogo de familias de productos para organizar el inventario."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # -------------------------------
    # TAB 1
    # -------------------------------
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

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar familias")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="pf_campo")
                valor = st.text_input("Valor a buscar", key="pf_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"],
                                 horizontal=True, key="pf_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Familias registradas")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar familias (requiere login)"):
            if can_edit():
                for _, row in df.iterrows():
                    fid = int(row["familiaid"])
                    st.markdown(f"**#{fid} — {row.get('nombre','')}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_pf_{fid}"):
                            st.session_state[EDIT_KEY] = fid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_pf_{fid}"):
                            st.session_state[DEL_KEY] = fid
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar familia #{did}?")
                    c1,c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="pf_confirm"):
                            supabase.table(TABLE).delete().eq("familiaid", did).execute()
                            st.success("✅ Familia eliminada")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="pf_cancel"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["familiaid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Familia #{eid}")
                    with st.form(f"edit_pf_{eid}"):
                        nombre = st.text_input("Nombre", cur.get("nombre",""))
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "nombre": nombre
                            }).eq("familiaid", eid).execute()
                            st.success("✅ Familia actualizada")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar familias.")

    # -------------------------------
    # TAB 2: CSV
    # -------------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_producto_familia")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_pf"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # -------------------------------
    # TAB 3: Instrucciones
    # -------------------------------
    with tab3:
        st.subheader("📑 Campos de Familias de Producto")
        st.markdown("""
        - **familiaid** → Identificador único de la familia.  
        - **nombre** → Nombre de la familia (ej: Libros ESO, Idiomas).  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code("nombre\nLibros ESO\nIdiomas", language="csv")
