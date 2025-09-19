import streamlit as st
import pandas as pd
from .ui import (
    draw_live_df, can_edit, section_header,
    fetch_options, show_form_images, show_csv_images
)

TABLE = "pedidodetalle"
FIELDS_LIST = [
    "pedidodetalleid","pedidoid","linea","productoid","cantidad",
    "preciounitario","descuentopct","tipoivalinea",
    "importelineabase","importelineaiva","importelineatotal"
]

def render_pedido_detalle(supabase):
    section_header("📦 Detalle Pedido",
                   "Gestión de líneas de detalle asociadas a cada pedido.")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- Formulario
    with tab1:
        pedidos, map_pedidos = fetch_options(supabase, "pedido", "pedidoid", "numpedido")
        productos, map_productos = fetch_options(supabase, "producto", "productoid", "titulo")

        with st.form("form_pedidodetalle"):
            pedido = st.selectbox("Pedido *", pedidos)
            producto = st.selectbox("Producto *", productos)
            linea = st.number_input("Línea", min_value=1, step=1)
            cantidad = st.number_input("Cantidad", min_value=1, step=1)
            precio = st.number_input("Precio Unitario", min_value=0.0, step=0.5)
            descuento = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, step=0.5)
            tipoiva = st.number_input("Tipo IVA (%)", min_value=0.0, step=0.5)

            if st.form_submit_button("➕ Insertar"):
                if not pedido or not producto:
                    st.error("❌ Pedido y Producto obligatorios")
                else:
                    base = cantidad * precio * (1 - descuento/100)
                    iva = base * (tipoiva/100)
                    total = base + iva
                    nuevo = {
                        "pedidoid": map_pedidos.get(pedido),
                        "linea": linea,
                        "productoid": map_productos.get(producto),
                        "cantidad": cantidad,
                        "preciounitario": precio,
                        "descuentopct": descuento,
                        "tipoivalinea": tipoiva,
                        "importelineabase": base,
                        "importelineaiva": iva,
                        "importelineatotal": total
                    }
                    supabase.table(TABLE).insert(nuevo).execute()
                    st.success("✅ Línea añadida")
                    st.rerun()

        st.markdown("#### 📑 Detalles actuales con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,2,2,1,1])
            header[0].markdown("**✏️**")
            header[1].markdown("**🗑️**")
            header[2].markdown("**PedidoID**")
            header[3].markdown("**ProductoID**")
            header[4].markdown("**Cantidad**")
            header[5].markdown("**Total**")

            for _, row in df.iterrows():
                did = int(row["pedidodetalleid"])
                cols = st.columns([0.5,0.5,2,2,1,1])

                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_{did}"):
                            st.session_state["editing"] = did; st.rerun()
                    else:
                        st.button("✏️", key=f"edit_{did}", disabled=True)

                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"ask_del_{did}"):
                            st.session_state["pending_delete"] = did; st.rerun()
                    else:
                        st.button("🗑️", key=f"ask_del_{did}", disabled=True)

                cols[2].write(row.get("pedidoid",""))
                cols[3].write(row.get("productoid",""))
                cols[4].write(row.get("cantidad",""))
                cols[5].write(row.get("importelineatotal",""))

            # Borrar
            if st.session_state.get("pending_delete"):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Eliminar línea #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del"):
                        supabase.table(TABLE).delete().eq("pedidodetalleid", did).execute()
                        st.success("✅ Eliminada")
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del"):
                        st.session_state["pending_delete"] = None
                        st.rerun()

            # Editar
            if st.session_state.get("editing"):
                eid = st.session_state["editing"]
                cur = df[df["pedidodetalleid"]==eid].iloc[0].to_dict()
                st.markdown("---"); st.subheader(f"Editar Detalle #{eid}")
                with st.form("edit_detalle"):
                    cantidad = st.number_input("Cantidad", value=int(cur.get("cantidad",1)), min_value=1)
                    precio   = st.number_input("Precio Unitario", value=float(cur.get("preciounitario",0)), min_value=0.0)
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "cantidad": cantidad,
                                "preciounitario": precio
                            }).eq("pedidodetalleid", eid).execute()
                            st.success("✅ Actualizado")
                            st.session_state["editing"] = None
                            st.rerun()

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: pedidoid,linea,productoid,cantidad,preciounitario,...")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_pedidodetalle")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_pedidodetalle"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.rerun()

    # --- Instrucciones
    with tab3:
        st.subheader("📖 Ejemplo CSV")
        st.code("pedidoid,linea,productoid,cantidad,preciounitario,descuentopct,...", language="csv")
        show_form_images()
        show_csv_images()
