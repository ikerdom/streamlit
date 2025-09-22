import streamlit as st
import pandas as pd
from .ui import render_header, draw_live_df, can_edit

TABLE = "estadopedido"
FIELDS_LIST = ["estadopedidoid", "nombre", "descripcion"]

ESTADOS_PREDEFINIDOS = ["Pendiente", "Confirmado", "Enviado", "Facturado", "Cancelado"]

EDIT_KEY = "editing_estado"
DEL_KEY  = "pending_delete_estado"

def render_estado_pedido(supabase):
    # ✅ Cabecera corporativa con logo
    render_header(
        "📌 Estados de Pedido",
        "Catálogo de estados posibles de un pedido."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # --- TAB 1: Formulario + Tabla
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

        st.markdown("#### 📑 Estados registrados con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            header = st.columns([0.5,0.5,2,3])
            for col, txt in zip(header, ["✏️","🗑️","Nombre","Descripción"]):
                col.markdown(f"**{txt}**")

            for _, row in df.iterrows():
                eid = int(row["estadopedidoid"])
                cols = st.columns([0.5,0.5,2,3])

                cols[2].write(row.get("nombre",""))
                cols[3].write(row.get("descripcion",""))

                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_estado_{eid}"):
                            st.session_state[EDIT_KEY] = eid; st.rerun()
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"del_estado_{eid}"):
                            st.session_state[DEL_KEY] = eid; st.rerun()

            # Confirmación de borrado
            if st.session_state.get(DEL_KEY):
                did = st.session_state[DEL_KEY]
                st.markdown("---")
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
                st.markdown("---")
                st.subheader(f"Editar Estado #{eid}")
                with st.form("edit_estado"):
                    nombre = st.selectbox(
                        "Estado", ESTADOS_PREDEFINIDOS,
                        index=ESTADOS_PREDEFINIDOS.index(cur.get("nombre"))
                        if cur.get("nombre") in ESTADOS_PREDEFINIDOS else 0
                    )
                    descripcion = st.text_area("Descripción", cur.get("descripcion",""))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "nombre": nombre,
                                "descripcion": descripcion
                            }).eq("estadopedidoid", eid).execute()
                            st.success("✅ Estado actualizado")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
                if st.button("❌ Cancelar", key="estado_cancel_edit"):
                    st.session_state[EDIT_KEY] = None
                    st.rerun()

    # --- TAB 2: CSV
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

    # --- TAB 3: Instrucciones
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
