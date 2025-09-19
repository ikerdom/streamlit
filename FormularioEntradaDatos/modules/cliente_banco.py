import streamlit as st
import pandas as pd
from .ui import (
    draw_live_df, can_edit, section_header,
    fetch_options, show_form_images, show_csv_images
)

TABLE = "clientebanco"
FIELDS_LIST = ["clientebancoid","clienteid","iban","bic","titular","banco","predeterminado"]

def render_cliente_banco(supabase):
    section_header("🏦 Bancos Cliente",
                   "Gestión de cuentas bancarias asociadas a cada cliente.")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- Formulario
    with tab1:
        clientes, map_clientes = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")

        with st.form("form_clientebanco"):
            cliente = st.selectbox("Cliente *", clientes)
            iban = st.text_input("IBAN *", max_chars=34)
            bic = st.text_input("BIC", max_chars=11)
            titular = st.text_input("Titular")
            banco = st.text_input("Banco")
            predeterminado = st.checkbox("Predeterminado", value=False)

            if st.form_submit_button("➕ Insertar"):
                if not cliente or not iban:
                    st.error("❌ Cliente e IBAN obligatorios")
                else:
                    nuevo = {
                        "clienteid": map_clientes.get(cliente),
                        "iban": iban,
                        "bic": bic,
                        "titular": titular,
                        "banco": banco,
                        "predeterminado": predeterminado
                    }
                    supabase.table(TABLE).insert(nuevo).execute()
                    st.success("✅ Cuenta añadida")
                    st.rerun()

        st.markdown("#### 📑 Cuentas actuales con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,2,2,2,2])
            header[0].markdown("**✏️**")
            header[1].markdown("**🗑️**")
            header[2].markdown("**IBAN**")
            header[3].markdown("**Titular**")
            header[4].markdown("**Banco**")
            header[5].markdown("**Predeterminado**")

            for _, row in df.iterrows():
                bid = int(row["clientebancoid"])
                cols = st.columns([0.5,0.5,2,2,2,2])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_{bid}"):
                            st.session_state["editing"] = bid; st.rerun()
                    else:
                        st.button("✏️", key=f"edit_{bid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"ask_del_{bid}"):
                            st.session_state["pending_delete"] = bid; st.rerun()
                    else:
                        st.button("🗑️", key=f"ask_del_{bid}", disabled=True)

                cols[2].write(row.get("iban",""))
                cols[3].write(row.get("titular",""))
                cols[4].write(row.get("banco",""))
                cols[5].write("✅" if row.get("predeterminado") else "—")

            # Confirmar borrado
            if st.session_state.get("pending_delete"):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Seguro que quieres eliminar la cuenta #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del"):
                        supabase.table(TABLE).delete().eq("clientebancoid", did).execute()
                        st.success("✅ Eliminada")
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del"):
                        st.session_state["pending_delete"] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get("editing"):
                eid = st.session_state["editing"]
                cur = df[df["clientebancoid"]==eid].iloc[0].to_dict()
                st.markdown("---"); st.subheader(f"Editar Cuenta #{eid}")
                with st.form("edit_banco"):
                    iban = st.text_input("IBAN", cur.get("iban",""))
                    titular = st.text_input("Titular", cur.get("titular",""))
                    banco = st.text_input("Banco", cur.get("banco",""))
                    pred = st.checkbox("Predeterminado", value=cur.get("predeterminado",False))
                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "iban": iban,
                                "titular": titular,
                                "banco": banco,
                                "predeterminado": pred
                            }).eq("clientebancoid", eid).execute()
                            st.success("✅ Cuenta actualizada")
                            st.session_state["editing"] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,iban,bic,titular,banco,predeterminado")

        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_banco")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_banco"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.rerun()

    # --- Instrucciones
    with tab3:
        st.subheader("📖 Ejemplos CSV")
        st.code("clienteid,iban,bic,titular,banco,predeterminado\n1,ES9820385778983000760236,BKTRSESMM,Juan Pérez,Banco Santander,true", language="csv")
        show_form_images()
        show_csv_images()
