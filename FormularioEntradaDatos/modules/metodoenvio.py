import streamlit as st
import pandas as pd
from .ui import section_header, draw_live_df, can_edit

TABLE = "metodoenvio"
FIELDS_LIST = ["metodoid","nombre","descripcion"]

def render_metodo_envio(supabase):
    section_header("📦 Métodos de Envío", "Catálogo de formas de envío disponibles.")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "✏️/🗑️ Editar/Borrar"])

    # --- Formulario
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

        st.markdown("#### 📑 Métodos de Envío (en vivo)")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre,descripcion")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_metodoenvio")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_metodoenvio"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.rerun()
        st.markdown("#### 📑 Métodos de Envío (en vivo)")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- Editar / Borrar
    with tab3:
        st.subheader("Editar / Borrar")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)
        if df.empty: return

        header = st.columns([0.5,0.5,2,3])
        for c,t in zip(header, ["✏️","🗑️","Nombre","Descripción"]):
            c.markdown(f"**{t}**")

        for _, row in df.iterrows():
            mid = int(row["metodoid"])
            cols = st.columns([0.5,0.5,2,3])

            with cols[0]:
                if can_edit():
                    if st.button("✏️", key=f"edit_{mid}"):
                        st.session_state["editing"] = mid; st.rerun()
                else:
                    st.button("✏️", key=f"edit_{mid}", disabled=True)

            with cols[1]:
                if can_edit():
                    if st.button("🗑️", key=f"ask_del_{mid}"):
                        st.session_state["pending_delete"] = mid; st.rerun()
                else:
                    st.button("🗑️", key=f"ask_del_{mid}", disabled=True)

            cols[2].write(row.get("nombre",""))
            cols[3].write(row.get("descripcion",""))

        # Confirmar borrado
        if st.session_state.get("pending_delete"):
            did = st.session_state["pending_delete"]
            st.markdown("---")
            st.error(f"⚠️ ¿Eliminar método #{did}?")
            c1,c2 = st.columns(2)
            with c1:
                if st.button("✅ Confirmar", key="confirm_del"):
                    supabase.table(TABLE).delete().eq("metodoid", did).execute()
                    st.success("✅ Método eliminado")
                    st.session_state["pending_delete"] = None
                    st.rerun()
            with c2:
                if st.button("❌ Cancelar", key="cancel_del"):
                    st.session_state["pending_delete"] = None
                    st.rerun()

        # Editar inline
        if st.session_state.get("editing"):
            eid = st.session_state["editing"]
            cur = df[df["metodoid"]==eid].iloc[0].to_dict()
            st.markdown("---"); st.subheader(f"Editar Método #{eid}")
            with st.form("edit_metodo"):
                nombre = st.text_input("Nombre", cur.get("nombre",""))
                descripcion = st.text_area("Descripción", cur.get("descripcion",""))
                if st.form_submit_button("💾 Guardar"):
                    if can_edit():
                        supabase.table(TABLE).update({
                            "nombre": nombre,
                            "descripcion": descripcion
                        }).eq("metodoid", eid).execute()
                        st.success("✅ Método actualizado")
                        st.session_state["editing"] = None
                        st.rerun()
                    else:
                        st.error("⚠️ Inicia sesión para editar registros.")
