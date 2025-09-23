# modules/formapago.py
import streamlit as st
import pandas as pd
from .ui import render_header, can_edit

TABLE = "formapago"
FIELDS_LIST = ["formapagoid", "nombre"]

FORMAS_PREDEFINIDAS = [
    "Transferencia bancaria", "Tarjeta de crédito", "Tarjeta de débito",
    "Domiciliación SEPA", "Paypal", "Bizum", "Contado"
]

EDIT_KEY = "editing_formapago"
DEL_KEY  = "pending_delete_formapago"

def render_forma_pago(supabase):
    # ✅ Cabecera corporativa
    render_header(
        "💳 Formas de Pago",
        "Define los métodos de pago disponibles para los pedidos."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1: Formulario + Tabla
    # ---------------------------
    with tab1:
        st.subheader("Añadir Forma de Pago")
        with st.form("form_pago"):
            nombre = st.selectbox("Nombre *", ["— Introducir manualmente —"] + FORMAS_PREDEFINIDAS)
            if nombre == "— Introducir manualmente —":
                nombre = st.text_input("Otro método *", max_chars=50)

            if st.form_submit_button("➕ Insertar"):
                if not nombre:
                    st.error("❌ El nombre es obligatorio")
                else:
                    supabase.table(TABLE).insert({"nombre": nombre}).execute()
                    st.success("✅ Forma de pago insertada")
                    st.rerun()

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar formas de pago")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="pago_campo")
                valor = st.text_input("Valor a buscar", key="pago_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"],
                                 horizontal=True, key="pago_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Formas de Pago registradas")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar formas de pago (requiere login)"):
            if can_edit() and not df.empty:
                for _, row in df.iterrows():
                    fid = int(row["formapagoid"])
                    st.markdown(f"**{row.get('nombre','')}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"pago_edit_{fid}"):
                            st.session_state[EDIT_KEY] = fid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"pago_del_{fid}"):
                            st.session_state[DEL_KEY] = fid
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
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
                    st.subheader(f"Editar Forma de Pago #{eid}")
                    with st.form(f"edit_formapago_{eid}"):
                        nombre = st.text_input("Nombre", cur.get("nombre",""))
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({"nombre": nombre}).eq("formapagoid", eid).execute()
                            st.success("✅ Forma de pago actualizada")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar registros.")

    # ---------------------------
    # TAB 2: CSV
    # ---------------------------
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

    # ---------------------------
    # TAB 3: Instrucciones
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Formas de Pago")
        st.markdown("""
        - **formapagoid** → Identificador único de la forma de pago.  
        - **nombre** → Nombre de la forma de pago (ej: Transferencia, Tarjeta, SEPA, Bizum, Contado).  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "nombre\n"
            "Transferencia bancaria\n"
            "Tarjeta de crédito\n"
            "Bizum\n"
            "Contado",
            language="csv"
        )
