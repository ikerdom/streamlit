import streamlit as st
import pandas as pd
from .ui import (
    draw_live_df, can_edit, show_form_images, show_csv_images,
    section_header
)

TABLE = "grupo"
FIELDS_LIST = ["grupoid","nombre","cif","notas","fechaalta"]

def render_grupo(supabase):
    section_header("📂 Gestión de Grupos", "Sección para organizar clientes por grupos empresariales.")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📑 Instrucciones"])

    # --- Formulario
    with tab1:
        st.subheader("Añadir Grupo")
        with st.form("form_grupo"):
            nombre = st.text_input("Nombre *", max_chars=200)
            cif    = st.text_input("CIF", max_chars=20)
            notas  = st.text_area("Notas", max_chars=500)
            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({
                        "nombre": nombre,
                        "cif": cif,
                        "notas": notas
                    }).execute()
                    st.success("✅ Grupo insertado")
                    st.rerun()

        st.markdown("#### 📑 Tabla en vivo con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,2,2,2])
            header[0].markdown("**✏️**")
            header[1].markdown("**🗑️**")
            header[2].markdown("**Nombre**")
            header[3].markdown("**CIF**")
            header[4].markdown("**Notas**")

            for _, row in df.iterrows():
                gid = int(row["grupoid"])
                cols = st.columns([0.5,0.5,2,2,2])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_{gid}"):
                            st.session_state["editing"] = gid
                            st.rerun()
                    else:
                        st.button("✏️", key=f"edit_{gid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"ask_del_{gid}"):
                            st.session_state["pending_delete"] = gid
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"ask_del_{gid}", disabled=True)

                cols[2].write(row.get("nombre",""))
                cols[3].write(row.get("cif",""))
                cols[4].write(row.get("notas",""))

            # Confirmación borrado
            if st.session_state.get("pending_delete"):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Seguro que quieres eliminar el grupo #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del"):
                        supabase.table(TABLE).delete().eq("grupoid", did).execute()
                        st.success(f"✅ Grupo {did} eliminado")
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del"):
                        st.info("Operación cancelada.")
                        st.session_state["pending_delete"] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get("editing"):
                eid = st.session_state["editing"]
                cur = df[df["grupoid"]==eid].iloc[0].to_dict()
                st.markdown("---")
                st.subheader(f"Editar Grupo #{eid}")
                with st.form("edit_grupo"):
                    nombre = st.text_input("Nombre", cur.get("nombre",""))
                    cif    = st.text_input("CIF", cur.get("cif",""))
                    notas  = st.text_area("Notas", cur.get("notas",""))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "nombre": nombre,
                                "cif": cif,
                                "notas": notas
                            }).eq("grupoid", eid).execute()
                            st.success("✅ Grupo actualizado")
                            st.session_state["editing"] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre,cif,notas")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_grupo")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_grupo"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.rerun()
        st.markdown("#### 📑 Tabla en vivo")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- Instrucciones
    with tab3:
        st.subheader("📖 Ejemplos e Instrucciones")
        st.markdown("Aquí puedes ver ejemplos de formularios y cargas CSV.")
        show_form_images()
        show_csv_images()
