# modules/pedido.py
import streamlit as st
import pandas as pd
from .ui import (
    can_edit, fetch_options, render_header
)

TABLE = "pedido"
FIELDS_LIST = ["pedidoid","clienteid","trabajadorid","numpedido","fechapedido","total"]

EDIT_KEY = "editing_ped"
DEL_KEY  = "pending_delete_ped"

def render_pedido(supabase):
    # ✅ Cabecera unificada
    render_header(
        "🧾 Gestión de Pedidos",
        "Alta y administración de pedidos de clientes."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1
    # ---------------------------
    with tab1:
        st.subheader("Añadir Pedido")

        clientes, map_cli     = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")
        trabajadores, map_tra = fetch_options(supabase, "trabajador", "trabajadorid", "nombre")

        with st.form("form_pedido"):
            cliente    = st.selectbox("Cliente *", clientes)
            trabajador = st.selectbox("Trabajador *", trabajadores)
            numpedido  = st.text_input("Número Pedido *", max_chars=50)
            fecha      = st.date_input("Fecha Pedido")
            total      = st.number_input("Total (€)", min_value=0.0, step=0.01)

            if st.form_submit_button("➕ Insertar"):
                if not numpedido:
                    st.error("❌ Número de pedido obligatorio")
                else:
                    nuevo = {
                        "clienteid": map_cli.get(cliente),
                        "trabajadorid": map_tra.get(trabajador),
                        "numpedido": numpedido,
                        "fechapedido": str(fecha),
                        "total": total
                    }
                    supabase.table(TABLE).insert(nuevo).execute()
                    st.success("✅ Pedido insertado")
                    st.rerun()

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar pedidos")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="ped_campo")
                valor = st.text_input("Valor a buscar", key="ped_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"],
                                 horizontal=True, key="ped_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # Mapear IDs → nombres legibles
        clientes_map = {c["clienteid"]: c["nombrefiscal"]
                        for c in supabase.table("cliente").select("clienteid,nombrefiscal").execute().data}
        trabajadores_map = {t["trabajadorid"]: t["nombre"]
                            for t in supabase.table("trabajador").select("trabajadorid,nombre").execute().data}

        df["Cliente"]    = df["clienteid"].map(clientes_map)
        df["Trabajador"] = df["trabajadorid"].map(trabajadores_map)

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Pedidos registrados")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar pedidos (requiere login)"):
            if can_edit():
                for _, row in df.iterrows():
                    pid = int(row["pedidoid"])
                    st.markdown(f"**{row.get('Cliente','')} — {row.get('numpedido','')} ({row.get('total','')} €)**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_ped_{pid}"):
                            st.session_state[EDIT_KEY] = pid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_ped_{pid}"):
                            st.session_state[DEL_KEY] = pid
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar pedido #{did}?")
                    c1,c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="ped_confirm"):
                            supabase.table(TABLE).delete().eq("pedidoid", did).execute()
                            st.success("✅ Pedido eliminado")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="ped_cancel"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["pedidoid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Pedido #{eid}")
                    with st.form(f"edit_ped_{eid}"):
                        numpedido = st.text_input("Número Pedido", cur.get("numpedido",""))
                        total     = st.number_input("Total (€)", value=float(cur.get("total",0)), step=0.01)
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "numpedido": numpedido,
                                "total": total
                            }).eq("pedidoid", eid).execute()
                            st.success("✅ Pedido actualizado")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar pedidos.")

    # ---------------------------
    # TAB 2
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,trabajadorid,numpedido,fechapedido,total")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_pedido")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_ped"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Pedido")
        st.markdown("""
        - **pedidoid** → Identificador único del pedido.  
        - **clienteid** → Cliente asociado (FK).  
        - **trabajadorid** → Trabajador responsable (FK).  
        - **numpedido** → Número de pedido (obligatorio).  
        - **fechapedido** → Fecha de creación.  
        - **total** → Importe total del pedido.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "clienteid,trabajadorid,numpedido,fechapedido,total\n"
            "1,2,PED001,2025-09-23,120.50",
            language="csv"
        )
