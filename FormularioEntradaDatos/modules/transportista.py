# modules/transportista.py
import streamlit as st
import pandas as pd
from .ui import render_header, can_edit

TABLE = "transportista"
FIELDS_LIST = ["transportistaid", "nombre", "observaciones"]

TRANSPORTISTAS_PREDEFINIDOS = [
    "SEUR", "Correos Express", "MRW", "DHL", "UPS", "GLS"
]

EDIT_KEY = "editing_transportista"
DEL_KEY  = "pending_delete_transportista"

def render_transportista(supabase):
    # ✅ Cabecera unificada
    render_header(
        "🚚 Catálogo: Transportistas", 
        "Define las empresas de transporte que gestionan los envíos."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1
    # ---------------------------
    with tab1:
        st.subheader("Añadir Transportista")

        with st.form("form_transportista"):
            nombre = st.selectbox("Nombre *", ["— Introducir manualmente —"] + TRANSPORTISTAS_PREDEFINIDOS)
            if nombre == "— Introducir manualmente —":
                nombre = st.text_input("Otro transportista *", max_chars=100)
            obs = st.text_area("Observaciones", max_chars=300)

            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({
                        "nombre": nombre,
                        "observaciones": obs
                    }).execute()
                    st.success("✅ Transportista insertado")
                    st.rerun()

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar transportistas")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="transp_campo")
                valor = st.text_input("Valor a buscar", key="transp_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"],
                                 horizontal=True, key="transp_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Transportistas registrados")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar transportistas (requiere login)"):
            if can_edit() and not df.empty:
                for _, row in df.iterrows():
                    tid = int(row["transportistaid"])
                    st.markdown(f"**{row.get('nombre','')} → {row.get('observaciones','')}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"tra_edit_{tid}"):
                            st.session_state[EDIT_KEY] = tid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"tra_del_{tid}"):
                            st.session_state[DEL_KEY] = tid
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar transportista #{did}?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="tra_confirm_del"):
                            supabase.table(TABLE).delete().eq("transportistaid", did).execute()
                            st.success("✅ Transportista eliminado")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="tra_cancel_del"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["transportistaid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Transportista #{eid}")
                    with st.form(f"edit_transportista_{eid}"):
                        nom = st.text_input("Nombre", cur.get("nombre",""))
                        obs = st.text_area("Observaciones", cur.get("observaciones",""))
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "nombre": nom,
                                "observaciones": obs
                            }).eq("transportistaid", eid).execute()
                            st.success("✅ Transportista actualizado")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar transportistas.")

    # ---------------------------
    # TAB 2
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: nombre,observaciones")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_transportista")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_transportista"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Transportistas")
        st.markdown("""
        - **transportistaid** → Identificador único del transportista.  
        - **nombre** → Nombre de la empresa de transporte (ej: SEUR, MRW, DHL).  
        - **observaciones** → Notas adicionales (ej: cobertura nacional, internacional).  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "nombre,observaciones\n"
            "SEUR,Mensajería urgente\n"
            "Correos Express,Servicio nacional",
            language="csv"
        )
