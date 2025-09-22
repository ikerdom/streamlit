import streamlit as st
import pandas as pd
from .ui import (
    draw_live_df, can_edit, section_header,
    fetch_options
)

TABLE = "pedidoenvio"
FIELDS_LIST = [
    "pedidoenvioid","pedidoid","clientedireccionid","nombredestinatario",
    "direccion1","cp","ciudad","provincia","pais",
    "transportistaid","metodoenvioid","costeenvio","tracking"
]

def render_pedido_envio(supabase):
    # Cabecera con logo
    col1, col2 = st.columns([4,1])
    with col1:
        section_header("🚚 Envío de Pedido",
                       "Gestión de datos de envío asociados a cada pedido.")
    with col2:
        st.image("images/logo_orbe_sinfondo-1536x479.png", use_container_width=True)

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- Formulario
    with tab1:
        pedidos, map_pedidos = fetch_options(supabase, "pedido", "pedidoid", "numpedido")
        direcciones, map_direcciones = fetch_options(supabase, "clientedireccion", "clientedireccionid", "alias")
        transportistas, map_transportistas = fetch_options(supabase, "transportista", "transportistaid", "nombre")
        metodos, map_metodos = fetch_options(supabase, "metodoenvio", "metodoenvioid", "nombre")

        with st.form("form_pedidoenvio"):
            pedido = st.selectbox("Pedido *", pedidos)
            direccion = st.selectbox("Dirección Cliente", ["— Ninguna —"] + direcciones)
            nombre = st.text_input("Nombre Destinatario *")
            direccion1 = st.text_input("Dirección 1 *")
            cp = st.text_input("Código Postal *", max_chars=10)

            c1, c2 = st.columns(2)
            with c1:
                ciudad = st.text_input("Ciudad *")
            with c2:
                provincia = st.text_input("Provincia")

            pais = st.text_input("País", value="España")

            c3, c4 = st.columns(2)
            with c3:
                transp = st.selectbox("Transportista", ["— Ninguno —"] + transportistas)
            with c4:
                metodo = st.selectbox("Método Envío", ["— Ninguno —"] + metodos)

            coste = st.number_input("Coste Envío (€)", min_value=0.0, step=0.5)
            tracking = st.text_input("Tracking")

            if st.form_submit_button("➕ Insertar"):
                if not pedido or not nombre or not direccion1 or not cp or not ciudad:
                    st.error("❌ Campos obligatorios faltantes")
                else:
                    nuevo = {
                        "pedidoid": map_pedidos.get(pedido),
                        "clientedireccionid": map_direcciones.get(direccion),
                        "nombredestinatario": nombre,
                        "direccion1": direccion1,
                        "cp": cp,
                        "ciudad": ciudad,
                        "provincia": provincia,
                        "pais": pais,
                        "transportistaid": map_transportistas.get(transp),
                        "metodoenvioid": map_metodos.get(metodo),
                        "costeenvio": coste,
                        "tracking": tracking
                    }
                    supabase.table(TABLE).insert(nuevo).execute()
                    st.success("✅ Envío añadido")
                    st.rerun()

        st.markdown("#### 📑 Envíos actuales con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            # Mapear IDs a nombres
            pedidos_map = {p["pedidoid"]: p["numpedido"] for p in supabase.table("pedido").select("pedidoid,numpedido").execute().data}
            direcciones_map = {d["clientedireccionid"]: d.get("alias","") for d in supabase.table("clientedireccion").select("clientedireccionid,alias").execute().data}
            transportistas_map = {t["transportistaid"]: t["nombre"] for t in supabase.table("transportista").select("transportistaid,nombre").execute().data}
            metodos_map = {m["metodoenvioid"]: m["nombre"] for m in supabase.table("metodoenvio").select("metodoenvioid,nombre").execute().data}

            df["pedido"] = df["pedidoid"].map(pedidos_map)
            df["direccion"] = df["clientedireccionid"].map(direcciones_map)
            df["transportista"] = df["transportistaid"].map(transportistas_map)
            df["metodo"] = df["metodoenvioid"].map(metodos_map)

            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,2,2,2,1,1])
            for col, txt in zip(header, ["✏️","🗑️","Pedido","Destinatario","Ciudad","Coste","Tracking"]):
                col.markdown(f"**{txt}**")

            for _, row in df.iterrows():
                eid = int(row["pedidoenvioid"])
                cols = st.columns([0.5,0.5,2,2,2,1,1])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_{eid}"):
                            st.session_state["editing"] = eid; st.rerun()
                    else:
                        st.button("✏️", key=f"edit_{eid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"ask_del_{eid}"):
                            st.session_state["pending_delete"] = eid; st.rerun()
                    else:
                        st.button("🗑️", key=f"ask_del_{eid}", disabled=True)

                cols[2].write(row.get("pedido",""))
                cols[3].write(row.get("nombredestinatario",""))
                cols[4].write(row.get("ciudad",""))
                cols[5].write(row.get("costeenvio",""))
                cols[6].write(row.get("tracking",""))

            # Confirmación de borrado
            if st.session_state.get("pending_delete"):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Eliminar envío #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del"):
                        supabase.table(TABLE).delete().eq("pedidoenvioid", did).execute()
                        st.success("✅ Eliminado")
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del"):
                        st.session_state["pending_delete"] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get("editing"):
                eid = st.session_state["editing"]
                cur = df[df["pedidoenvioid"]==eid].iloc[0].to_dict()
                st.markdown("---"); st.subheader(f"Editar Envío #{eid}")
                with st.form("edit_envio"):
                    nombre = st.text_input("Nombre Destinatario", cur.get("nombredestinatario",""))
                    direccion1 = st.text_input("Dirección 1", cur.get("direccion1",""))
                    cp = st.text_input("Código Postal", cur.get("cp",""))

                    c1, c2 = st.columns(2)
                    with c1:
                        ciudad = st.text_input("Ciudad", cur.get("ciudad",""))
                    with c2:
                        provincia = st.text_input("Provincia", cur.get("provincia",""))

                    coste  = st.number_input("Coste Envío (€)", value=float(cur.get("costeenvio",0)), step=0.5)
                    tracking = st.text_input("Tracking", cur.get("tracking",""))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "nombredestinatario": nombre,
                                "direccion1": direccion1,
                                "cp": cp,
                                "ciudad": ciudad,
                                "provincia": provincia,
                                "costeenvio": coste,
                                "tracking": tracking
                            }).eq("pedidoenvioid", eid).execute()
                            st.success("✅ Envío actualizado")
                            st.session_state["editing"] = None
                            st.rerun()

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: pedidoid,clientedireccionid,nombredestinatario,direccion1,cp,ciudad,provincia,pais,transportistaid,metodoenvioid,costeenvio,tracking")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_pedidoenvio")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_pedidoenvio"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.rerun()

    # --- Instrucciones
    with tab3:
        st.subheader("📑 Campos de Envío de Pedido")
        st.markdown("""
        - **pedidoid** → referencia al pedido.  
        - **clientedireccionid** → dirección de envío del cliente.  
        - **nombredestinatario** → persona o entidad receptora.  
        - **direccion1 / cp / ciudad / provincia / país** → datos completos de la dirección.  
        - **transportistaid** → transportista seleccionado.  
        - **metodoenvioid** → método de envío (ej: estándar, exprés).  
        - **costeenvio** → coste asociado al transporte.  
        - **tracking** → número o código de seguimiento.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "pedidoid,clientedireccionid,nombredestinatario,direccion1,cp,ciudad,provincia,pais,transportistaid,metodoenvioid,costeenvio,tracking\n"
            "1,2,Academia Alfa,Calle Mayor 5,50016,Zaragoza,Zaragoza,España,1,2,7.50,ZX12345",
            language="csv"
        )
