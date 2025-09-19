import streamlit as st
import pandas as pd
from .ui import section_header, draw_live_df, can_edit

TABLE = "estadopedido"
FIELDS_LIST = ["estadoid","nombre","descripcion"]

def render_estado_pedido(supabase):
    section_header("📌 Estados de Pedido", "Catálogo de estados posibles de un pedido.")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "✏️/🗑️ Editar/Borrar"])

    # --- Formulario
    with tab1:
        st.subheader("Añadir Estado")
        with st.form("form_estado"):
            nombre = st.text_input("Nombre *", max_chars=100)
            descripcion = st.text_area("Descripción", max_chars=300)
            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({
                        "nombre": nombre,
                        "descripcion": descripcion
                    }).execute()
                    st.success("✅ Estado insertado")
                    st.rerun()
        st.markdown("#### 📑 Estados (en vivo)")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre,descripcion")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_estado")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_estado"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.rerun()
        st.markdown("#### 📑 Estados (en vivo)")
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
            eid = int(row["estadoid"])
            cols = st.columns([0.5,0.5,2,3])

            with cols[0]:
                if can_edit():
                    if st.button("✏️", key=f"edit_{eid}"):
                        st.session_state["editing"] = eid; st.rerun()
                else:
                    st.button("✏️", key=f"edit_{eid}", disabled=True)

            with cols[1]:
                if can_edit():
                    if st.button("🗑️", key=f"ask_del_{eid}"):
                        st.session_state["pending_delete"] = eid; st.rerun()
                else:
                    st.button("🗑️", key=f"ask_del_{eid}", disabled=True)

            cols[2].write(row.get("nombre",""))
            cols[3].write(row.get("descripcion",""))

        # Confirmación de borrado
        if st.session_state.get("pending_delete"):
            did = st.session_state["pending_delete"]
            st.markdown("---")
            st.error(f"⚠️ ¿Eliminar estado #{did}?")
            c1,c2 = st.columns(2)
            with c1:
                if st.button("✅ Confirmar", key="confirm_del"):
                    supabase.table(TABLE).delete().eq("estadoid", did).execute()
                    st.success("✅ Estado eliminado")
                    st.session_state["pending_delete"] = None
                    st.rerun()
            with c2:
                if st.button("❌ Cancelar", key="cancel_del"):
                    st.session_state["pending_delete"] = None
                    st.rerun()

        # Edición inline
        if st.session_state.get("editing"):
            eid = st.session_state["editing"]
            cur = df[df["estadoid"]==eid].iloc[0].to_dict()
            st.markdown("---"); st.subheader(f"Editar Estado #{eid}")
            with st.form("edit_estado"):
                nombre = st.text_input("Nombre", cur.get("nombre",""))
                descripcion = st.text_area("Descripción", cur.get("descripcion",""))
                if st.form_submit_button("💾 Guardar"):
                    if can_edit():
                        supabase.table(TABLE).update({
                            "nombre": nombre,
                            "descripcion": descripcion
                        }).eq("estadoid", eid).execute()
                        st.success("✅ Estado actualizado")
                        st.session_state["editing"] = None
                        st.rerun()
                    else:
                        st.error("⚠️ Inicia sesión para editar registros.")
