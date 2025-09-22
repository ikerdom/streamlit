# modules/cliente_familia_descuento.py
import streamlit as st
import pandas as pd
from .ui import safe_image
from .ui import (
    section_header, can_edit, fetch_options
)

TABLE = "cliente_familia_descuento"
FIELDS_LIST = [
    "cliente_familia_descuentoid","clienteid","familiaid","descuentopct","fechaalta"
]

EDIT_KEY = "editing_cfd"
DEL_KEY  = "pending_delete_cfd"

def render_cliente_familia_descuento(supabase):
    # Cabecera con logo
    col1, col2 = st.columns([4,1])
    with col1:
        section_header("🏷️ Descuentos por Familia",
                       "Gestión de descuentos aplicados a clientes por familia de productos.")
    with col2:
        safe_image("logo_orbe_sinfondo-1536x479.png")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # --- TAB 1: Formulario + Tabla
    with tab1:
        st.subheader("Añadir Descuento por Familia")

        # Catálogos
        clientes, map_clientes = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")
        familias, map_familias = fetch_options(supabase, "producto_familia", "familiaid", "nombre")

        with st.form("form_cliente_familia_desc"):
            cliente = st.selectbox("Cliente *", clientes)
            familia = st.selectbox("Familia de Producto *", familias)
            desc = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, step=0.5)

            if st.form_submit_button("➕ Insertar"):
                if not cliente or not familia:
                    st.error("❌ Cliente y Familia obligatorios")
                else:
                    nuevo = {
                        "clienteid": map_clientes.get(cliente),
                        "familiaid": map_familias.get(familia),
                        "descuentopct": desc
                    }
                    supabase.table(TABLE).insert(nuevo).execute()
                    st.success("✅ Descuento asignado")
                    st.rerun()

        st.markdown("#### 📑 Descuentos actuales")
        df = supabase.table(TABLE).select("*").execute().data
        df = pd.DataFrame(df)

        if not df.empty:
            # Mapear IDs → nombres legibles
            clientes_map = {c["clienteid"]: c["nombrefiscal"]
                            for c in supabase.table("cliente").select("clienteid,nombrefiscal").execute().data}
            familias_map = {f["familiaid"]: f["nombre"]
                            for f in supabase.table("producto_familia").select("familiaid,nombre").execute().data}

            df["Cliente"] = df["clienteid"].map(clientes_map)
            df["Familia"] = df["familiaid"].map(familias_map)

            # Header
            header = st.columns([0.5,0.5,2,2,1.5,2])
            for col, txt in zip(header, ["✏️","🗑️","Cliente","Familia","Descuento","Fecha Alta"]):
                col.markdown(f"**{txt}**")

            for _, row in df.iterrows():
                if pd.isna(row["cliente_familia_descuentoid"]):
                    continue
                did = int(row["cliente_familia_descuentoid"])
                cols = st.columns([0.5,0.5,2,2,1.5,2])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_cfd_{did}"):
                            st.session_state[EDIT_KEY] = did
                            st.rerun()
                    else:
                        st.button("✏️", key=f"edit_cfd_{did}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"del_cfd_{did}"):
                            st.session_state[DEL_KEY] = did
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"del_cfd_{did}", disabled=True)

                cols[2].write(row.get("Cliente",""))
                cols[3].write(row.get("Familia",""))
                cols[4].write(f"{row.get('descuentopct','')} %")
                cols[5].write(row.get("fechaalta",""))

            # Confirmar borrado
            if st.session_state.get(DEL_KEY):
                did = st.session_state[DEL_KEY]
                st.error(f"⚠️ ¿Eliminar descuento #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del_cfd"):
                        supabase.table(TABLE).delete().eq("cliente_familia_descuentoid", did).execute()
                        st.success("✅ Eliminado")
                        st.session_state[DEL_KEY] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del_cfd"):
                        st.session_state[DEL_KEY] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get(EDIT_KEY):
                eid = st.session_state[EDIT_KEY]
                cur = df[df["cliente_familia_descuentoid"]==eid].iloc[0].to_dict()
                st.markdown("---"); st.subheader(f"Editar Descuento #{eid}")
                with st.form(f"edit_cfd_{eid}"):
                    desc = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0,
                                           value=float(cur.get("descuentopct",0)), step=0.5)
                    if st.form_submit_button("💾 Guardar"):
                        supabase.table(TABLE).update({
                            "descuentopct": desc
                        }).eq("cliente_familia_descuentoid", eid).execute()
                        st.success("✅ Descuento actualizado")
                        st.session_state[EDIT_KEY] = None
                        st.rerun()

    # --- TAB 2: CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,familiaid,descuentopct")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_cliente_familia_desc")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_cliente_familia_desc"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # --- TAB 3: Instrucciones
    with tab3:
        st.subheader("📑 Campos de Descuentos por Familia")
        st.markdown("""
        - **cliente_familia_descuentoid** → Identificador único del descuento.  
        - **clienteid** → Cliente al que se aplica el descuento.  
        - **familiaid** → Familia de productos afectada.  
        - **descuentopct** → Porcentaje de descuento (%) sobre esa familia.  
        - **fechaalta** → Fecha de creación del registro.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code("clienteid,familiaid,descuentopct\n1,2,10.5", language="csv")
