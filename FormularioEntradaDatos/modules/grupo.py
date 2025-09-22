import streamlit as st
import pandas as pd
from .ui import render_header, draw_live_df, can_edit, fetch_options

TABLE = "grupo"
FIELDS_LIST = ["grupoid","nombre","cif","notas","fechaalta"]

def render_grupo(supabase):
    # ✅ Cabecera corporativa
    render_header(
        "📂 Gestión de Grupos",
        "Sección para organizar clientes por grupos empresariales."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📑 Instrucciones"])

    # -------------------------------
    # TAB 1: Formulario
    # -------------------------------
    with tab1:
        st.subheader("Alta o edición de Grupo")

        modo = st.radio("Selecciona modo:", ["➖ Grupo existente", "➕ Nuevo grupo"])
        grupos, map_grupos = fetch_options(supabase, TABLE, "grupoid", "nombre")

        nombre, cif, notas, grupo_id = "", "", "", None
        if modo == "➖ Grupo existente" and grupos:
            grupo_sel = st.selectbox("Grupo existente", grupos)
            grupo_id = map_grupos.get(grupo_sel)
            if grupo_id:
                cur = supabase.table(TABLE).select("*").eq("grupoid", grupo_id).execute()
                if cur.data:
                    row = cur.data[0]
                    nombre = row.get("nombre","")
                    cif = row.get("cif","")
                    notas = row.get("notas","")

        with st.form("form_grupo"):
            nombre = st.text_input("Nombre *", value=nombre, max_chars=200)
            cif    = st.text_input("CIF", value=cif, max_chars=20)
            notas  = st.text_area("Notas", value=notas, max_chars=500)

            if st.form_submit_button("💾 Guardar"):
                if not nombre.strip():
                    st.error("❌ El nombre es obligatorio")
                else:
                    if modo == "➕ Nuevo grupo":
                        supabase.table(TABLE).insert({
                            "nombre": nombre.strip(),
                            "cif": cif.strip(),
                            "notas": notas.strip()
                        }).execute()
                        st.success(f"✅ Grupo '{nombre}' creado")
                    else:
                        supabase.table(TABLE).update({
                            "nombre": nombre.strip(),
                            "cif": cif.strip(),
                            "notas": notas.strip()
                        }).eq("grupoid", grupo_id).execute()
                        st.success(f"✅ Grupo '{nombre}' actualizado")
                    st.rerun()

        st.markdown("#### 📑 Tabla en vivo con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        # --- Acciones de edición/borrado ---
        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")
            header = st.columns([0.5,0.5,3,2,3,2])
            for c, t in zip(header, ["✏️","🗑️","Nombre","CIF","Notas","Fecha Alta"]):
                c.markdown(f"**{t}**")

            for _, row in df.iterrows():
                gid = int(row["grupoid"])
                cols = st.columns([0.5,0.5,3,2,3,2])

                cols[2].write(row.get("nombre",""))
                cols[3].write(row.get("cif",""))
                cols[4].write(row.get("notas",""))
                cols[5].write(str(row.get("fechaalta","")))

                with cols[0]:
                    if can_edit() and st.button("✏️", key=f"grupo_edit_{gid}"):
                        st.session_state["editing_grupo"] = gid; st.rerun()
                with cols[1]:
                    if can_edit() and st.button("🗑️", key=f"grupo_delask_{gid}"):
                        st.session_state["pending_delete_grupo"] = gid; st.rerun()

            # Confirmar borrado
            if st.session_state.get("pending_delete_grupo"):
                did = st.session_state["pending_delete_grupo"]
                st.markdown("---")
                st.error(f"⚠️ ¿Seguro que quieres eliminar el grupo #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="grupo_confirm_del"):
                        supabase.table(TABLE).delete().eq("grupoid", did).execute()
                        st.success("✅ Grupo eliminado")
                        st.session_state["pending_delete_grupo"] = None; st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="grupo_cancel_del"):
                        st.session_state["pending_delete_grupo"] = None; st.rerun()

            # Edición inline
            if st.session_state.get("editing_grupo"):
                eid = st.session_state["editing_grupo"]
                cur = df[df["grupoid"]==eid].iloc[0].to_dict()
                st.markdown("---"); st.subheader(f"Editar Grupo #{eid}")
                with st.form("edit_grupo"):
                    nom = st.text_input("Nombre", cur.get("nombre",""))
                    ci  = st.text_input("CIF", cur.get("cif",""))
                    no  = st.text_area("Notas", cur.get("notas",""))
                    if st.form_submit_button("💾 Guardar cambios"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "nombre": nom,
                                "cif": ci,
                                "notas": no
                            }).eq("grupoid", eid).execute()
                            st.success("✅ Grupo actualizado")
                            st.session_state["editing_grupo"] = None; st.rerun()

    # -------------------------------
    # TAB 2: CSV
    # -------------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("El archivo debe tener las columnas: **nombre, cif, notas**")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_grupo")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_grupo"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}"); st.rerun()
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # -------------------------------
    # TAB 3: Instrucciones
    # -------------------------------
    with tab3:
        st.subheader("📑 Campos de Grupo")
        st.markdown("""
        - **grupoid** → identificador único (autonumérico).  
        - **nombre** → nombre del grupo empresarial (obligatorio).  
        - **cif** → código fiscal (opcional).  
        - **notas** → información adicional.  
        - **fechaalta** → fecha de creación (automática).  

        ### Ejemplo CSV
        ```
        nombre,cif,notas
        Grupo Alfa,B12345678,Notas de ejemplo
        Grupo Beta,C87654321,"Observaciones adicionales"
        ```
        """)
