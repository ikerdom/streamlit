# modules/forma_facturacion.py
import streamlit as st
import pandas as pd
from .ui import render_header, can_edit

TABLE = "forma_facturacion"
FIELDS_LIST = ["formafacturacionid", "nombre"]

EDIT_KEY = "editing_formafacturacion"
DEL_KEY  = "pending_delete_formafacturacion"

def render_forma_facturacion(supabase):
    # ✅ Cabecera corporativa

    render_header(
        "🧾 Formas de Facturación",
        "Define los métodos de facturación disponibles (p. ej., Factura, Resumen de facturación, etc.)."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1: Formulario + Tabla
    # ---------------------------
    with tab1:
        st.subheader("Añadir Forma de Facturación")
        with st.form("form_facturacion"):
            nombre = st.text_input("Nombre *", max_chars=150)
            if st.form_submit_button("➕ Insertar"):
                if not nombre.strip():
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({"nombre": nombre.strip()}).execute()
                    st.success("✅ Forma de facturación insertada")
                    st.rerun()

        # ---------------------------
        # 🔎 Búsqueda / Filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar formas de facturación")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Campo", df.columns, key="ff_campo")
                valor = st.text_input("Valor a buscar", key="ff_valor")
                orden = st.radio("Ordenar por", ["Ascendente","Descendente"], horizontal=True, key="ff_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # ---------------------------
        # 📑 Tabla
        # ---------------------------
        st.markdown("### 📑 Formas de Facturación registradas")
        st.dataframe(df[FIELDS_LIST] if not df.empty else df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar (requiere login)"):
            if can_edit() and not df.empty:
                for _, row in df.iterrows():
                    fid = int(row["formafacturacionid"])
                    st.markdown(f"**{row.get('nombre','(sin nombre)')}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_fact_{fid}"):
                            st.session_state[EDIT_KEY] = fid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_fact_{fid}"):
                            st.session_state[DEL_KEY] = fid
                            st.rerun()
                    st.markdown("---")

                # Confirmación de borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar forma de facturación #{did}?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="fact_confirm_del"):
                            supabase.table(TABLE).delete().eq("formafacturacionid", did).execute()
                            st.success("✅ Forma eliminada")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="fact_cancel_del"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["formafacturacionid"] == eid].iloc[0].to_dict()
                    st.subheader(f"Editar Forma de Facturación #{eid}")
                    with st.form(f"edit_fact_{eid}"):
                        nombre_edit = st.text_input("Nombre", cur.get("nombre",""))
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "nombre": nombre_edit.strip()
                            }).eq("formafacturacionid", eid).execute()
                            st.success("✅ Forma de facturación actualizada")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar registros, o no hay datos que mostrar.")

    # ---------------------------
    # TAB 2: CSV (sin ejemplos)
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_facturacion")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_facturacion"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3: Instrucciones (sin imágenes ni ejemplo CSV)
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Formas de Facturación")
        st.markdown("""
        - **formafacturacionid** → Identificador único de la forma de facturación.  
        - **nombre** → Nombre del tipo de facturación (p. ej., Factura, Resumen de facturación).  
        """)
