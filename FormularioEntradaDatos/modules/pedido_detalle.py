# modules/pedido_detalle.py
import streamlit as st
import pandas as pd
from .ui import (
    can_edit, fetch_options, render_header
)

TABLE = "pedidodetalle"
FIELDS_LIST = [
    "pedidodetalleid","pedidoid","linea","productoid","cantidad",
    "preciounitario","descuentopct","tipoivalinea",
    "importelineabase","importelineaiva","importelineatotal"
]

EDIT_KEY = "editing_det"
DEL_KEY  = "pending_delete_det"

def render_pedido_detalle(supabase):
    # ✅ Cabecera unificada
    render_header(
        "📦 Detalle de Pedido",
        "Gestión de líneas de detalle asociadas a cada pedido con importes calculados."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1
    # ---------------------------
    with tab1:
        st.subheader("Añadir línea de Pedido")

        pedidos, map_pedidos   = fetch_options(supabase, "pedido", "pedidoid", "numpedido")
        productos, map_productos = fetch_options(supabase, "producto", "productoid", "titulo")

        with st.form("form_pedidodetalle"):
            pedido   = st.selectbox("Pedido *", pedidos)
            producto = st.selectbox("Producto *", productos)

            c1, c2 = st.columns(2)
            linea    = c1.number_input("Línea", min_value=1, step=1)
            cantidad = c2.number_input("Cantidad", min_value=1, step=1)

            c3, c4 = st.columns(2)
            precio    = c3.number_input("Precio Unitario (€)", min_value=0.0, step=0.5)
            descuento = c4.number_input("Descuento (%)", min_value=0.0, max_value=100.0, step=0.5)

            tipoiva = st.number_input("Tipo IVA (%)", min_value=0.0, step=0.5)

            if st.form_submit_button("➕ Insertar"):
                if not pedido or not producto:
                    st.error("❌ Pedido y Producto obligatorios")
                else:
                    base  = cantidad * precio * (1 - descuento/100)
                    iva   = base * (tipoiva/100)
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

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar líneas")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="det_campo")
                valor = st.text_input("Valor a buscar", key="det_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"],
                                 horizontal=True, key="det_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # Mapear IDs a nombres legibles
        pedidos_map   = {p["pedidoid"]: p["numpedido"] for p in supabase.table("pedido").select("pedidoid,numpedido").execute().data}
        productos_map = {p["productoid"]: p["titulo"] for p in supabase.table("producto").select("productoid,titulo").execute().data}
        df["Pedido"]   = df["pedidoid"].map(pedidos_map)
        df["Producto"] = df["productoid"].map(productos_map)

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Detalles registrados")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar detalles (requiere login)"):
            if can_edit():
                for _, row in df.iterrows():
                    did = int(row["pedidodetalleid"])
                    st.markdown(f"**Pedido {row.get('Pedido','')} — {row.get('Producto','')} ({row.get('cantidad','')} ud.)**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_det_{did}"):
                            st.session_state[EDIT_KEY] = did
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_det_{did}"):
                            st.session_state[DEL_KEY] = did
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar línea #{did}?")
                    c1,c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="det_confirm"):
                            supabase.table(TABLE).delete().eq("pedidodetalleid", did).execute()
                            st.success("✅ Línea eliminada")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="det_cancel"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["pedidodetalleid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Detalle #{eid}")
                    with st.form(f"edit_det_{eid}"):
                        cantidad  = st.number_input("Cantidad", value=int(cur.get("cantidad",1)), min_value=1)
                        precio    = st.number_input("Precio Unitario (€)", value=float(cur.get("preciounitario",0)), min_value=0.0)
                        descuento = st.number_input("Descuento (%)", value=float(cur.get("descuentopct",0)), min_value=0.0, max_value=100.0, step=0.5)
                        tipoiva   = st.number_input("Tipo IVA (%)", value=float(cur.get("tipoivalinea",0)), min_value=0.0, step=0.5)

                        if st.form_submit_button("💾 Guardar"):
                            base  = cantidad * precio * (1 - descuento/100)
                            iva   = base * (tipoiva/100)
                            total = base + iva
                            supabase.table(TABLE).update({
                                "cantidad": cantidad,
                                "preciounitario": precio,
                                "descuentopct": descuento,
                                "tipoivalinea": tipoiva,
                                "importelineabase": base,
                                "importelineaiva": iva,
                                "importelineatotal": total
                            }).eq("pedidodetalleid", eid).execute()
                            st.success("✅ Detalle actualizado")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar detalles.")

    # ---------------------------
    # TAB 2
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: pedidoid,linea,productoid,cantidad,preciounitario,descuentopct,tipoivalinea")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_pedidodetalle")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_det"):
                df_csv["importelineabase"] = df_csv["cantidad"] * df_csv["preciounitario"] * (1 - df_csv["descuentopct"]/100)
                df_csv["importelineaiva"]  = df_csv["importelineabase"] * (df_csv["tipoivalinea"]/100)
                df_csv["importelineatotal"]= df_csv["importelineabase"] + df_csv["importelineaiva"]
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Detalle de Pedido")
        st.markdown("""
        - **pedidoid** → referencia al pedido.  
        - **linea** → número de línea dentro del pedido.  
        - **productoid** → referencia al producto.  
        - **cantidad** → unidades pedidas.  
        - **preciounitario** → importe por unidad.  
        - **descuentopct** → descuento aplicado (%).  
        - **tipoivalinea** → tipo de IVA (%) aplicado a la línea.  
        - **importelineabase** → subtotal antes de impuestos.  
        - **importelineaiva** → importe de IVA.  
        - **importelineatotal** → total final de la línea.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "pedidoid,linea,productoid,cantidad,preciounitario,descuentopct,tipoivalinea\n"
            "1,1,2,3,28.5,5,4.0",
            language="csv"
        )
