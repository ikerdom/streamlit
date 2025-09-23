# modules/pedido_envio.py
import streamlit as st
import pandas as pd
from .ui import (
    can_edit, fetch_options, render_header
)

TABLE = "pedidoenvio"
FIELDS_LIST = [
    "pedidoenvioid","pedidoid","clientedireccionid","nombredestinatario",
    "direccion1","cp","ciudad","provincia","pais",
    "transportistaid","metodoenvioid","costeenvio","tracking"
]

EDIT_KEY = "editing_env"
DEL_KEY  = "pending_delete_env"

def render_pedido_envio(supabase):
    # ✅ Cabecera unificada
    render_header(
        "🚚 Envío de Pedido",
        "Gestión de datos de envío asociados a cada pedido."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1
    # ---------------------------
    with tab1:
        st.subheader("Añadir envío")

        pedidos, map_pedidos       = fetch_options(supabase, "pedido", "pedidoid", "numpedido")
        direcciones, map_dirs      = fetch_options(supabase, "clientedireccion", "clientedireccionid", "alias")
        transportistas, map_transp = fetch_options(supabase, "transportista", "transportistaid", "nombre")
        metodos, map_metodos       = fetch_options(supabase, "metodoenvio", "metodoenvioid", "nombre")

        with st.form("form_pedidoenvio"):
            pedido     = st.selectbox("Pedido *", pedidos)
            direccion  = st.selectbox("Dirección Cliente", ["— Ninguna —"] + direcciones)
            nombre     = st.text_input("Nombre Destinatario *")
            direccion1 = st.text_input("Dirección 1 *")
            cp         = st.text_input("Código Postal *", max_chars=10)

            c1, c2 = st.columns(2)
            ciudad    = c1.text_input("Ciudad *")
            provincia = c2.text_input("Provincia")

            pais = st.text_input("País", value="España")

            c3, c4 = st.columns(2)
            transp = c3.selectbox("Transportista", ["— Ninguno —"] + transportistas)
            metodo = c4.selectbox("Método Envío", ["— Ninguno —"] + metodos)

            coste    = st.number_input("Coste Envío (€)", min_value=0.0, step=0.5)
            tracking = st.text_input("Tracking")

            if st.form_submit_button("➕ Insertar"):
                if not pedido or not nombre or not direccion1 or not cp or not ciudad:
                    st.error("❌ Campos obligatorios faltantes")
                else:
                    nuevo = {
                        "pedidoid": map_pedidos.get(pedido),
                        "clientedireccionid": map_dirs.get(direccion),
                        "nombredestinatario": nombre,
                        "direccion1": direccion1,
                        "cp": cp,
                        "ciudad": ciudad,
                        "provincia": provincia,
                        "pais": pais,
                        "transportistaid": map_transp.get(transp),
                        "metodoenvioid": map_metodos.get(metodo),
                        "costeenvio": coste,
                        "tracking": tracking
                    }
                    supabase.table(TABLE).insert(nuevo).execute()
                    st.success("✅ Envío añadido")
                    st.rerun()

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar envíos")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="env_campo")
                valor = st.text_input("Valor a buscar", key="env_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"],
                                 horizontal=True, key="env_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # Mapear IDs → nombres legibles
        pedidos_map        = {p["pedidoid"]: p["numpedido"] for p in supabase.table("pedido").select("pedidoid,numpedido").execute().data}
        direcciones_map    = {d["clientedireccionid"]: d.get("alias","") for d in supabase.table("clientedireccion").select("clientedireccionid,alias").execute().data}
        transportistas_map = {t["transportistaid"]: t["nombre"] for t in supabase.table("transportista").select("transportistaid,nombre").execute().data}
        metodos_map        = {m["metodoenvioid"]: m["nombre"] for m in supabase.table("metodoenvio").select("metodoenvioid,nombre").execute().data}

        df["Pedido"]        = df["pedidoid"].map(pedidos_map)
        df["Dirección"]     = df["clientedireccionid"].map(direcciones_map)
        df["Transportista"] = df["transportistaid"].map(transportistas_map)
        df["Método"]        = df["metodoenvioid"].map(metodos_map)

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Envíos registrados")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar envíos (requiere login)"):
            if can_edit():
                for _, row in df.iterrows():
                    eid = int(row["pedidoenvioid"])
                    st.markdown(f"**Pedido {row.get('Pedido','')} — {row.get('nombredestinatario','')} ({row.get('ciudad','')})**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_env_{eid}"):
                            st.session_state[EDIT_KEY] = eid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_env_{eid}"):
                            st.session_state[DEL_KEY] = eid
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar envío #{did}?")
                    c1,c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="env_confirm"):
                            supabase.table(TABLE).delete().eq("pedidoenvioid", did).execute()
                            st.success("✅ Envío eliminado")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="env_cancel"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["pedidoenvioid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Envío #{eid}")
                    with st.form(f"edit_env_{eid}"):
                        nombre     = st.text_input("Nombre Destinatario", cur.get("nombredestinatario",""))
                        direccion1 = st.text_input("Dirección 1", cur.get("direccion1",""))
                        cp         = st.text_input("Código Postal", cur.get("cp",""))

                        c1, c2 = st.columns(2)
                        ciudad    = c1.text_input("Ciudad", cur.get("ciudad",""))
                        provincia = c2.text_input("Provincia", cur.get("provincia",""))

                        coste    = st.number_input("Coste Envío (€)", value=float(cur.get("costeenvio",0)), step=0.5)
                        tracking = st.text_input("Tracking", cur.get("tracking",""))
                        if st.form_submit_button("💾 Guardar"):
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
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar envíos.")

    # ---------------------------
    # TAB 2
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: pedidoid,clientedireccionid,nombredestinatario,direccion1,cp,ciudad,provincia,pais,transportistaid,metodoenvioid,costeenvio,tracking")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_pedidoenvio")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_env"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3
    # ---------------------------
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
