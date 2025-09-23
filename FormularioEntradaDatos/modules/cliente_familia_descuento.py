# modules/cliente_familia_descuento.py
import streamlit as st
import pandas as pd
from .ui import (
    render_header, can_edit, fetch_options
)

TABLE = "cliente_familia_descuento"
FIELDS_LIST = [
    "clientefamdescuentoid", "clienteid", "familiaid", "descuento", "vigencia"
]

EDIT_KEY = "editing_cfd"
DEL_KEY  = "pending_delete_cfd"

def render_cliente_familia_descuento(supabase):
    # ✅ Cabecera
    render_header(
        "🏷️ Descuentos por Familia",
        "Gestión de descuentos aplicados a clientes por familia de productos."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1
    # ---------------------------
    with tab1:
        st.subheader("Añadir Descuento por Familia")

        clientes, map_clientes = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")
        familias, map_familias = fetch_options(supabase, "producto_familia", "familiaid", "nombre")

        with st.form("form_cliente_familia_desc"):
            cliente = st.selectbox("Cliente *", clientes)
            familia = st.selectbox("Familia de Producto *", familias)
            desc = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, step=0.5)

            # Vigencia → dos fechas
            col1, col2 = st.columns(2)
            desde = col1.date_input("Desde")
            hasta = col2.date_input("Hasta", value=None)

            if st.form_submit_button("➕ Insertar"):
                if not cliente or not familia:
                    st.error("❌ Cliente y Familia obligatorios")
                else:
                    supabase.table(TABLE).insert({
                        "clienteid": map_clientes.get(cliente),
                        "familiaid": map_familias.get(familia),
                        "descuento": desc,
                        "vigencia": f"[{desde},{hasta})" if hasta else f"[{desde},)"
                    }).execute()
                    st.success("✅ Descuento asignado")
                    st.rerun()

        # ---------------------------
        # 🔎 Buscar / Filtrar
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar descuentos")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="cfd_campo")
                valor = st.text_input("Valor a buscar", key="cfd_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"], horizontal=True, key="cfd_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # Mapear IDs
        clientes_map = {c["clienteid"]: c["nombrefiscal"] for c in supabase.table("cliente").select("clienteid,nombrefiscal").execute().data}
        familias_map = {f["familiaid"]: f["nombre"] for f in supabase.table("producto_familia").select("familiaid,nombre").execute().data}

        if not df.empty:
            df["Cliente"] = df["clienteid"].map(clientes_map)
            df["Familia"] = df["familiaid"].map(familias_map)

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Descuentos registrados")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar descuentos (requiere login)"):
            if can_edit() and not df.empty:
                for _, row in df.iterrows():
                    did = int(row["clientefamdescuentoid"])
                    st.markdown(f"**{row.get('Cliente','')} — {row.get('Familia','')} ({row.get('descuento','')}%)**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_cfd_{did}"):
                            st.session_state[EDIT_KEY] = did
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_cfd_{did}"):
                            st.session_state[DEL_KEY] = did
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar descuento #{did}?")
                    c1,c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="cfd_confirm"):
                            supabase.table(TABLE).delete().eq("clientefamdescuentoid", did).execute()
                            st.success("✅ Descuento eliminado")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="cfd_cancel"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["clientefamdescuentoid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Descuento #{eid}")
                    with st.form(f"edit_cfd_{eid}"):
                        desc = st.number_input(
                            "Descuento (%)", min_value=0.0, max_value=100.0,
                            value=float(cur.get("descuento",0)), step=0.5
                        )
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "descuento": desc
                            }).eq("clientefamdescuentoid", eid).execute()
                            st.success("✅ Descuento actualizado")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar descuentos.")

    # ---------------------------
    # TAB 2
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,familiaid,descuento,vigencia")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_cliente_familia_desc")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_cfd"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Descuentos por Familia")
        st.markdown("""
        - **clientefamdescuentoid** → Identificador único del descuento.  
        - **clienteid** → Cliente al que se aplica el descuento.  
        - **familiaid** → Familia de productos afectada.  
        - **descuento** → Porcentaje de descuento (%) sobre esa familia.  
        - **vigencia** → Rango de fechas de validez del descuento.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code("clienteid,familiaid,descuento,vigencia\n1,9,10.5,[2025-01-01,2025-12-31)", language="csv")
