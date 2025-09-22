# modules/formapago.py
import streamlit as st
import pandas as pd
from .ui import render_header, can_edit, draw_live_df

TABLE = "formapago"
FIELDS_LIST = ["formapagoid", "nombre"]

EDIT_KEY = "editing_formapago"
DEL_KEY  = "pending_delete_formapago"

def render_forma_pago(supabase):
    # ✅ Cabecera corporativa
    render_header(
        "💳 Formas de Pago",
        "Define los métodos de pago disponibles para los pedidos (ej. transferencia, tarjeta, etc.)."
    )



    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # --- TAB 1: Formulario + Tabla
    with tab1:
        st.subheader("Añadir Forma de Pago")
        with st.form("form_pago"):
            nombre = st.text_input("Nombre *", max_chars=50)
            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({"nombre": nombre}).execute()
                    st.success("✅ Forma de pago insertada")
                    st.rerun()

        st.markdown("#### 📑 Formas de Pago actuales con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,3])
            for col, txt in zip(header, ["✏️","🗑️","Nombre"]):
                col.markdown(f"**{txt}**")

            for _, row in df.iterrows():
                fid = int(row["formapagoid"])
                cols = st.columns([0.5,0.5,3])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_pago_{fid}"):
                            st.session_state[EDIT_KEY] = fid
                            st.rerun()
                    else:
                        st.button("✏️", key=f"edit_pago_{fid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"del_pago_{fid}"):
                            st.session_state[DEL_KEY] = fid
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"del_pago_{fid}", disabled=True)

                # Nombre
                cols[2].write(row.get("nombre",""))

            # Confirmar borrado
            if st.session_state.get(DEL_KEY):
                did = st.session_state[DEL_KEY]
                st.markdown("---")
                st.error(f"⚠️ ¿Eliminar forma de pago #{did}?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="pago_confirm_del"):
                        supabase.table(TABLE).delete().eq("formapagoid", did).execute()
                        st.success("✅ Forma de pago eliminada")
                        st.session_state[DEL_KEY] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="pago_cancel_del"):
                        st.session_state[DEL_KEY] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get(EDIT_KEY):
                eid = st.session_state[EDIT_KEY]
                cur = df[df["formapagoid"]==eid].iloc[0].to_dict()
                st.markdown("---")
                st.subheader(f"Editar Forma de Pago #{eid}")
                with st.form("edit_formapago"):
                    nombre = st.text_input("Nombre", cur.get("nombre",""))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({"nombre": nombre}).eq("formapagoid", eid).execute()
                            st.success("✅ Forma de pago actualizada")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")
                if st.button("❌ Cancelar", key="pago_cancel_edit"):
                    st.session_state[EDIT_KEY] = None
                    st.rerun()

    # --- TAB 2: CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_pago")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_pago"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # --- TAB 3: Instrucciones
    with tab3:
        st.subheader("📑 Campos de Formas de Pago")
        st.markdown("""
        - **formapagoid** → identificador único de la forma de pago.  
        - **nombre** → nombre de la forma de pago (ej: Transferencia, Tarjeta, SEPA, Contado).  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "nombre\n"
            "Transferencia\n"
            "Tarjeta de crédito\n"
            "Remesa SEPA\n"
            "Contado",
            language="csv"
        )
