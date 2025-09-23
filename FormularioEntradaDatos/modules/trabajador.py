# modules/trabajador.py
import streamlit as st
import pandas as pd
from .ui import (
    render_header, can_edit
)

TABLE = "trabajador"
FIELDS_LIST = ["trabajadorid","codigoempleado","nombre","email","telefono","activo","fechaalta"]

EDIT_KEY = "editing_trab"
DEL_KEY  = "pending_delete_trab"

def render_trabajador(supabase):
    # ✅ Cabecera corporativa
    render_header(
        "👨‍💼 Gestión de Trabajadores",
        "Altas y gestión de empleados."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # -------------------------------
    # TAB 1
    # -------------------------------
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

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar trabajadores")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="trab_campo")
                valor = st.text_input("Valor a buscar", key="trab_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"],
                                 horizontal=True, key="trab_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Trabajadores registrados")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar trabajadores (requiere login)"):
            if can_edit():
                for _, row in df.iterrows():
                    tid = int(row["trabajadorid"])
                    st.markdown(f"**{row.get('codigoempleado','')} — {row.get('nombre','')}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_trab_{tid}"):
                            st.session_state[EDIT_KEY] = tid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_trab_{tid}"):
                            st.session_state[DEL_KEY] = tid
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar trabajador #{did}?")
                    c1,c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="trab_confirm"):
                            supabase.table(TABLE).delete().eq("trabajadorid", did).execute()
                            st.success("✅ Trabajador eliminado")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="trab_cancel"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["trabajadorid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Trabajador #{eid}")
                    with st.form(f"edit_trab_{eid}"):
                        cod = st.text_input("Código", cur.get("codigoempleado",""))
                        nom = st.text_input("Nombre", cur.get("nombre",""))
                        em  = st.text_input("Email", cur.get("email",""))
                        te  = st.text_input("Teléfono", cur.get("telefono",""))
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "codigoempleado": cod,
                                "nombre": nom,
                                "email": em,
                                "telefono": te
                            }).eq("trabajadorid", eid).execute()
                            st.success("✅ Trabajador actualizado")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar trabajadores.")

    # -------------------------------
    # TAB 2: CSV
    # -------------------------------
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

    # -------------------------------
    # TAB 3: Instrucciones
    # -------------------------------
    with tab3:
        st.subheader("📑 Campos de Trabajador")
        st.markdown("""
        - **trabajadorid** → Identificador único.  
        - **codigoempleado** → Identificador interno del trabajador.  
        - **nombre** → Nombre completo.  
        - **email** → Correo de contacto.  
        - **telefono** → Teléfono de contacto.  
        - **activo** → Si el trabajador sigue en la empresa.  
        - **fechaalta** → Fecha de alta en el sistema.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "codigoempleado,nombre,email,telefono\n"
            "EMP001,María López,maria@example.com,600123456\n"
            "EMP002,Carlos García,carlos@example.com,600654321",
            language="csv"
        )
