import streamlit as st
import pandas as pd
from .ui import section_header, draw_live_df, can_edit, fetch_options, show_form_images, show_csv_images

TABLE = "clientecondiciones"
FIELDS_LIST = [
    "clientecondicionesid","clienteid","formapagoid",
    "diaspago","limitecredito","descuentocomercial",
    "observaciones","fechaalta"
]

def render_cliente_condiciones(supabase):
    section_header("⚙️ Condiciones de Cliente", "Condiciones comerciales aplicadas a clientes.")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- Formulario
    with tab1:
        st.subheader("Añadir Condición")
        clientes, map_cli = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")
        formas, map_formas = fetch_options(supabase, "formapago", "formapagoid", "nombre")

        with st.form("form_cond"):
            cliente = st.selectbox("Cliente *", clientes)
            forma   = st.selectbox("Forma de pago", ["— Ninguna —"] + formas)
            dias    = st.number_input("Días de pago", min_value=0, step=1)
            limite  = st.number_input("Límite crédito (€)", min_value=0.0, step=100.0)
            desc    = st.number_input("Descuento comercial (%)", min_value=0.0, max_value=100.0, step=0.5)
            obs     = st.text_area("Observaciones")

            if st.form_submit_button("➕ Insertar"):
                if not cliente:
                    st.error("❌ Cliente es obligatorio")
                else:
                    supabase.table(TABLE).insert({
                        "clienteid": map_cli.get(cliente),
                        "formapagoid": map_formas.get(forma),
                        "diaspago": dias,
                        "limitecredito": limite,
                        "descuentocomercial": desc,
                        "observaciones": obs
                    }).execute()
                    st.success("✅ Condición insertada")
                    st.rerun()

        st.markdown("#### 📑 Condiciones (en vivo)")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,1.5,1.5,1.5,1.5,2])
            for c,t in zip(header, ["✏️","🗑️","Cliente","FormaPago","Días","Límite","Descuento"]):
                c.markdown(f"**{t}**")

            for _, row in df.iterrows():
                cid = int(row["clientecondicionesid"])
                cols = st.columns([0.5,0.5,1.5,1.5,1.5,1.5,2])

                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_{cid}"):
                            st.session_state["editing"] = cid
                            st.rerun()
                    else:
                        st.button("✏️", key=f"edit_{cid}", disabled=True)

                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"ask_del_{cid}"):
                            st.session_state["pending_delete"] = cid
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"ask_del_{cid}", disabled=True)

                cols[2].write(row.get("clienteid",""))
                cols[3].write(row.get("formapagoid",""))
                cols[4].write(row.get("diaspago",""))
                cols[5].write(row.get("limitecredito",""))
                cols[6].write(row.get("descuentocomercial",""))

            # Confirmar borrado
            if st.session_state.get("pending_delete"):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Eliminar condición #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del"):
                        supabase.table(TABLE).delete().eq("clientecondicionesid", did).execute()
                        st.success("✅ Condición eliminada")
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del"):
                        st.session_state["pending_delete"] = None
                        st.rerun()

            # Editar inline
            if st.session_state.get("editing"):
                eid = st.session_state["editing"]
                cur = df[df["clientecondicionesid"]==eid].iloc[0].to_dict()
                st.markdown("---")
                st.subheader(f"Editar Condición #{eid}")
                with st.form("edit_cond"):
                    dias = st.number_input("Días de pago", value=int(cur.get("diaspago",0)))
                    limite = st.number_input("Límite crédito (€)", value=float(cur.get("limitecredito",0)))
                    desc = st.number_input("Descuento (%)", value=float(cur.get("descuentocomercial",0)))
                    obs  = st.text_area("Observaciones", value=cur.get("observaciones",""))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "diaspago": dias,
                                "limitecredito": limite,
                                "descuentocomercial": desc,
                                "observaciones": obs
                            }).eq("clientecondicionesid", eid).execute()
                            st.success("✅ Condición actualizada")
                            st.session_state["editing"] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,formapagoid,diaspago,limitecredito,descuentocomercial,observaciones")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_condiciones")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_condiciones"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.rerun()
        st.markdown("#### 📑 Condiciones (en vivo)")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- Instrucciones
    with tab3:
        st.subheader("📖 Ejemplos e Instrucciones")
        st.markdown("Puedes cargar condiciones vía formulario o CSV. Ejemplo de CSV:")
        st.code("clienteid,formapagoid,diaspago,limitecredito,descuentocomercial,observaciones\n1,2,30,5000,10.5,Cliente preferente", language="csv")
        show_form_images()
        show_csv_images()
