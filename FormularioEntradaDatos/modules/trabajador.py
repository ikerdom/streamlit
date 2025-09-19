import streamlit as st
import pandas as pd
from .ui import (
    section_header, draw_live_df, can_edit,
    show_form_images, show_csv_images, draw_feed_generic
)

TABLE = "trabajador"
FIELDS_LIST = ["trabajadorid","codigoempleado","nombre","email","telefono","activo","fechaalta"]

def render_trabajador(supabase):
    # Cabecera + descripción + mini feed
    section_header("👨‍💼 Gestión de Trabajadores", "Altas y gestión de empleados.")
    draw_feed_generic(supabase, TABLE, "nombre", "fechaalta", "trabajadorid")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- Formulario
    with tab1:
        st.subheader("Añadir Trabajador")
        with st.form("form_trabajador"):
            codigo = st.text_input("Código Empleado *", max_chars=30)
            nombre = st.text_input("Nombre *", max_chars=150)
            email  = st.text_input("Email", max_chars=150)
            tel    = st.text_input("Teléfono", max_chars=50)
            if st.form_submit_button("➕ Insertar"):
                if not codigo or not nombre:
                    st.error("❌ Código y Nombre obligatorios")
                else:
                    supabase.table(TABLE).insert({
                        "codigoempleado": codigo,
                        "nombre": nombre,
                        "email": email,
                        "telefono": tel
                    }).execute()
                    st.success("✅ Trabajador insertado")
                    st.rerun()

        st.markdown("#### 📑 Tabla en vivo con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,2,2,2,2,1])
            header[0].markdown("**✏️**")
            header[1].markdown("**🗑️**")
            header[2].markdown("**Código**")
            header[3].markdown("**Nombre**")
            header[4].markdown("**Email**")
            header[5].markdown("**Teléfono**")
            header[6].markdown("**Activo**")

            for _, row in df.iterrows():
                tid = int(row["trabajadorid"])
                cols = st.columns([0.5,0.5,2,2,2,2,1])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"tra_edit_{tid}"):
                            st.session_state["editing"] = tid
                            st.rerun()
                    else:
                        st.button("✏️", key=f"tra_edit_{tid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"tra_delask_{tid}"):
                            st.session_state["pending_delete"] = tid
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"tra_delask_{tid}", disabled=True)

                cols[2].write(row.get("codigoempleado",""))
                cols[3].write(row.get("nombre",""))
                cols[4].write(row.get("email",""))
                cols[5].write(row.get("telefono",""))
                cols[6].write("✅" if row.get("activo") else "—")

            # Confirmar borrado
            if st.session_state.get("pending_delete"):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Seguro que quieres eliminar el trabajador #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="tra_confirm_del"):
                        supabase.table(TABLE).delete().eq("trabajadorid", did).execute()
                        st.success("✅ Trabajador eliminado")
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="tra_cancel_del"):
                        st.session_state["pending_delete"] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get("editing"):
                eid = st.session_state["editing"]
                cur = df[df["trabajadorid"]==eid].iloc[0].to_dict()
                st.markdown("---")
                st.subheader(f"Editar Trabajador #{eid}")
                with st.form("edit_trabajador"):
                    cod = st.text_input("Código", cur.get("codigoempleado",""))
                    nom = st.text_input("Nombre", cur.get("nombre",""))
                    em  = st.text_input("Email", cur.get("email",""))
                    te  = st.text_input("Teléfono", cur.get("telefono",""))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "codigoempleado": cod,
                                "nombre": nom,
                                "email": em,
                                "telefono": te
                            }).eq("trabajadorid", eid).execute()
                            st.success("✅ Trabajador actualizado")
                            st.session_state["editing"] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: codigoempleado,nombre,email,telefono")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_trabajador")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_trabajador"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

        st.markdown("#### 📑 Tabla en vivo")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- Instrucciones
    with tab3:
        st.subheader("📖 Ejemplos e Instrucciones")
        show_form_images()
        show_csv_images()
