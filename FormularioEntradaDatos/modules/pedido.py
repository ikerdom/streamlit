import streamlit as st
import pandas as pd
from .ui import (
    section_header, draw_live_df, can_edit, fetch_options
)

TABLE = "pedido"
FIELDS_LIST = ["pedidoid","clienteid","trabajadorid","numpedido","fechapedido","total"]

def render_pedido(supabase):
    section_header("🧾 Gestión de Pedidos", "Alta y administración de pedidos de clientes.")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- Formulario
    with tab1:
        st.subheader("Añadir Pedido")

        clientes, map_cli = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")
        trabajadores, map_tra = fetch_options(supabase, "trabajador", "trabajadorid", "nombre")

        with st.form("form_pedido"):
            cliente = st.selectbox("Cliente *", clientes)
            trabajador = st.selectbox("Trabajador *", trabajadores)
            numpedido = st.text_input("Número Pedido *", max_chars=50)
            fecha = st.date_input("Fecha Pedido")
            total = st.number_input("Total (€)", min_value=0.0, step=0.01)

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

        st.markdown("#### 📑 Pedidos (en vivo) con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,2,2,2,1,1])
            header[0].markdown("**✏️**")
            header[1].markdown("**🗑️**")
            header[2].markdown("**ClienteID**")
            header[3].markdown("**TrabajadorID**")
            header[4].markdown("**NumPedido**")
            header[5].markdown("**Fecha**")
            header[6].markdown("**Total**")

            for _, row in df.iterrows():
                pid = int(row["pedidoid"])
                cols = st.columns([0.5,0.5,2,2,2,1,1])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_{pid}"):
                            st.session_state["editing"] = pid
                            st.rerun()
                    else:
                        st.button("✏️", key=f"edit_{pid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"ask_del_{pid}"):
                            st.session_state["pending_delete"] = pid
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"ask_del_{pid}", disabled=True)

                cols[2].write(row.get("clienteid",""))
                cols[3].write(row.get("trabajadorid",""))
                cols[4].write(row.get("numpedido",""))
                cols[5].write(row.get("fechapedido",""))
                cols[6].write(row.get("total",""))

            # Confirmación de borrado
            if st.session_state.get("pending_delete"):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Eliminar pedido #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del"):
                        supabase.table(TABLE).delete().eq("pedidoid", did).execute()
                        st.success("✅ Pedido eliminado")
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del"):
                        st.session_state["pending_delete"] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get("editing"):
                eid = st.session_state["editing"]
                cur = df[df["pedidoid"]==eid].iloc[0].to_dict()
                st.markdown("---"); st.subheader(f"Editar Pedido #{eid}")
                with st.form("edit_pedido"):
                    numpedido = st.text_input("Número Pedido", cur.get("numpedido",""))
                    total     = st.number_input("Total (€)", value=float(cur.get("total",0)), step=0.01)
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "numpedido": numpedido,
                                "total": total
                            }).eq("pedidoid", eid).execute()
                            st.success("✅ Pedido actualizado")
                            st.session_state["editing"] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,trabajadorid,numpedido,fechapedido,total")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_pedido")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_pedido"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()
        st.markdown("#### 📑 Pedidos (en vivo)")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- Instrucciones
    with tab3:
        st.subheader("📖 Instrucciones")
        st.markdown("- **Número de pedido** es obligatorio.\n"
                    "- **Cliente** y **Trabajador** deben existir previamente.\n"
                    "- **Fecha** debe tener formato válido.\n"
                    "- **Total** debe ser numérico.")
