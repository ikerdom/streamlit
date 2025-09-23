# modules/estadopedido.py
import streamlit as st
import pandas as pd
from .ui import render_header, can_edit

TABLE = "estadopedido"
FIELDS_LIST = ["estadopedidoid", "nombre", "descripcion"]

ESTADOS_PREDEFINIDOS = ["Pendiente", "Confirmado", "Enviado", "Facturado", "Cancelado"]

EDIT_KEY = "editing_estado"
DEL_KEY  = "pending_delete_estado"

def render_estado_pedido(supabase):
    # ✅ Cabecera unificada
    render_header(
        "📌 Estados de Pedido",
        "Catálogo de estados posibles de un pedido."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1
    # ---------------------------
    with tab1:
        st.subheader("Añadir Estado")

        with st.form("form_estado"):
            nombre = st.selectbox("Estado *", ESTADOS_PREDEFINIDOS)
            descripcion = st.text_area("Descripción", max_chars=300)
            if st.form_submit_button("➕ Insertar"):
                supabase.table(TABLE).insert({
                    "nombre": nombre,
                    "descripcion": descripcion
                }).execute()
                st.success("✅ Estado insertado")
                st.rerun()

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar estados")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="estado_campo")
                valor = st.text_input("Valor a buscar", key="estado_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"],
                                 horizontal=True, key="estado_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Estados registrados")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar estados (requiere login)"):
            if can_edit() and not df.empty:
                for _, row in df.iterrows():
                    eid = int(row["estadopedidoid"])
                    st.markdown(f"**{row.get('nombre','')} → {row.get('descripcion','')}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_estado_{eid}"):
                            st.session_state[EDIT_KEY] = eid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_estado_{eid}"):
                            st.session_state[DEL_KEY] = eid
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar estado #{did}?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="estado_confirm_del"):
                            supabase.table(TABLE).delete().eq("estadopedidoid", did).execute()
                            st.success("✅ Estado eliminado")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="estado_cancel_del"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["estadopedidoid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Estado #{eid}")
                    with st.form(f"edit_estado_{eid}"):
                        nombre = st.selectbox(
                            "Estado", ESTADOS_PREDEFINIDOS,
                            index=ESTADOS_PREDEFINIDOS.index(cur.get("nombre"))
                            if cur.get("nombre") in ESTADOS_PREDEFINIDOS else 0
                        )
                        descripcion = st.text_area("Descripción", cur.get("descripcion",""))
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "nombre": nombre,
                                "descripcion": descripcion
                            }).eq("estadopedidoid", eid).execute()
                            st.success("✅ Estado actualizado")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar estados.")

    # ---------------------------
    # TAB 2
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre,descripcion")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_estado")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_estado"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Estados de Pedido")
        st.markdown("""
        - **estadopedidoid** → identificador único del estado.  
        - **nombre** → uno de los valores predefinidos: *Pendiente, Confirmado, Enviado, Facturado, Cancelado*.  
        - **descripcion** → texto explicativo opcional.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "nombre,descripcion\n"
            "Pendiente,El pedido ha sido registrado pero no procesado aún\n"
            "Confirmado,El pedido ha sido confirmado por el sistema\n"
            "Enviado,El pedido ha sido entregado al transportista\n"
            "Facturado,El pedido ya tiene factura emitida\n"
            "Cancelado,El pedido ha sido anulado",
            language="csv"
        )
