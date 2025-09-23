# modules/metodoenvio.py
import streamlit as st
import pandas as pd
from .ui import render_header, can_edit

TABLE = "metodoenvio"
FIELDS_LIST = ["metodoenvioid", "nombre", "descripcion"]

METODOS_PREDEFINIDOS = [
    "Urgente (24h)", "Estándar (3-5 días)", "Económico",
    "Recogida en tienda", "Internacional"
]

EDIT_KEY = "editing_metodo"
DEL_KEY  = "pending_delete_metodo"

def render_metodo_envio(supabase):
    # ✅ Cabecera unificada
    render_header(
        "📦 Catálogo: Métodos de Envío",
        "Define los métodos de envío disponibles (urgente, estándar, etc.)."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1: Formulario + Tabla
    # ---------------------------
    with tab1:
        st.subheader("Añadir Método de Envío")

        with st.form("form_metodo"):
            nombre = st.selectbox("Nombre *", ["— Introducir manualmente —"] + METODOS_PREDEFINIDOS)
            if nombre == "— Introducir manualmente —":
                nombre = st.text_input("Otro método *", max_chars=150)
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

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar métodos")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="metodo_campo")
                valor = st.text_input("Valor a buscar", key="metodo_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"],
                                 horizontal=True, key="metodo_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Métodos registrados")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar métodos (requiere login)"):
            if can_edit() and not df.empty:
                for _, row in df.iterrows():
                    mid = int(row["metodoenvioid"])
                    st.markdown(f"**{row.get('nombre','')} → {row.get('descripcion','')}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"metodo_edit_{mid}"):
                            st.session_state[EDIT_KEY] = mid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"metodo_del_{mid}"):
                            st.session_state[DEL_KEY] = mid
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar método #{did}?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="metodo_confirm_del"):
                            supabase.table(TABLE).delete().eq("metodoenvioid", did).execute()
                            st.success("✅ Método eliminado")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="metodo_cancel_del"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["metodoenvioid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Método #{eid}")
                    with st.form(f"edit_metodo_{eid}"):
                        nombre = st.text_input("Nombre", cur.get("nombre",""))
                        descripcion = st.text_area("Descripción", cur.get("descripcion",""))
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "nombre": nombre,
                                "descripcion": descripcion
                            }).eq("metodoenvioid", eid).execute()
                            st.success("✅ Método actualizado")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar métodos.")

    # ---------------------------
    # TAB 2: CSV
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre,descripcion")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_metodoenvio")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_metodoenvio"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3: Instrucciones
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Métodos de Envío")
        st.markdown("""
        - **metodoenvioid** → Identificador único del método.  
        - **nombre** → Nombre del método de envío (ej: Urgente, Estándar, Económico).  
        - **descripcion** → Detalle adicional sobre el método.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "nombre,descripcion\n"
            "Urgente (24h),Entrega en 24h\n"
            "Estándar (3-5 días),Entrega en 3-5 días",
            language="csv"
        )
