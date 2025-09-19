import streamlit as st
import pandas as pd
from .ui import (
    draw_live_df, can_edit, show_form_images, show_csv_images,
    section_header
)

TABLE = "formapago"
FIELDS_LIST = ["formapagoid", "nombre"]

def render_forma_pago(supabase):
    section_header("💳 Catálogo: Formas de Pago", 
                   "Define los métodos de pago disponibles para los pedidos (ej. transferencia, tarjeta, etc.).")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- Formulario
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

        st.markdown("#### 📑 Tabla en vivo con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,4,1])
            header[0].markdown("**✏️**")
            header[1].markdown("**🗑️**")
            header[2].markdown("**Nombre**")
            header[3].markdown("**ID**")

            for _, row in df.iterrows():
                fid = int(row["formapagoid"])
                cols = st.columns([0.5,0.5,4,1])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"fp_edit_{fid}"):
                            st.session_state["editing"] = fid
                            st.session_state["editing_table"] = TABLE
                            st.rerun()
                    else:
                        st.button("✏️", key=f"fp_edit_{fid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"fp_delask_{fid}"):
                            st.session_state["pending_delete"] = fid
                            st.session_state["pending_table"] = TABLE
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"fp_delask_{fid}", disabled=True)

                cols[2].write(row.get("nombre",""))
                cols[3].write(fid)

            # Confirmar borrado
            if (st.session_state.get("pending_delete") 
                and st.session_state.get("pending_table") == TABLE):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Seguro que quieres eliminar la forma de pago #{did}?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="fp_confirm_del"):
                        supabase.table(TABLE).delete().eq("formapagoid", did).execute()
                        st.success("✅ Forma de pago eliminada")
                        st.session_state["pending_delete"] = None
                        st.session_state["pending_table"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="fp_cancel_del"):
                        st.session_state["pending_delete"] = None
                        st.session_state["pending_table"] = None
                        st.rerun()

            # Edición inline
            if (st.session_state.get("editing") 
                and st.session_state.get("editing_table") == TABLE):
                eid = st.session_state["editing"]
                cur = df[df["formapagoid"]==eid].iloc[0].to_dict()
                st.markdown("---")
                st.subheader(f"Editar Forma de Pago #{eid}")
                with st.form("edit_formapago"):
                    nom = st.text_input("Nombre", cur.get("nombre",""))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({"nombre": nom}).eq("formapagoid", eid).execute()
                            st.success("✅ Forma de pago actualizada")
                            st.session_state["editing"] = None
                            st.session_state["editing_table"] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- CSV
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

        st.markdown("#### 📑 Tabla en vivo")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- Instrucciones
    with tab3:
        st.subheader("📖 Ejemplos e Instrucciones")
        st.code("Transferencia\nTarjeta de crédito\nRemesa SEPA\nContado", language="csv")
        show_form_images()
        show_csv_images()
