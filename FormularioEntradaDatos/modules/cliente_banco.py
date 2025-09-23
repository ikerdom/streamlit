# modules/cliente_banco.py
import streamlit as st
import pandas as pd
from .ui import render_header, can_edit, fetch_options

TABLE = "clientebanco"
FIELDS_LIST = [
    "clientebancoid","clienteid","iban","bic",
    "titular","banco","predeterminado"
]

EDIT_KEY = "editing_banco"
DEL_KEY  = "pending_delete_banco"

def render_cliente_banco(supabase):
    # ✅ Cabecera
    render_header(
        "🏦 Bancos Cliente",
        "Gestión de cuentas bancarias asociadas a cada cliente."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1
    # ---------------------------
    with tab1:
        st.subheader("Añadir Cuenta Bancaria")

        clientes, map_clientes = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")

        with st.form("form_clientebanco"):
            cliente = st.selectbox("Cliente *", clientes)
            iban = st.text_input("IBAN *", max_chars=34, placeholder="ES9820385778983000760236")
            bic = st.text_input("BIC", max_chars=11, placeholder="BANKESMMXXX")
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

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar cuentas")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            # Mapear clienteid → nombre fiscal
            clientes_map = {
                c["clienteid"]: c["nombrefiscal"]
                for c in supabase.table("cliente").select("clienteid,nombrefiscal").execute().data
            }
            df["clienteid"] = df["clienteid"].map(clientes_map)

            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="banco_campo")
                valor = st.text_input("Valor a buscar", key="banco_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"], horizontal=True, key="banco_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden == "Ascendente"))

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Cuentas registradas")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar cuentas (requiere login)"):
            if can_edit():
                for _, row in df.iterrows():
                    bid = int(row["clientebancoid"])
                    st.markdown(f"**{row.get('clienteid','')} — {row.get('iban','')}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_banco_{bid}"):
                            st.session_state[EDIT_KEY] = bid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_banco_{bid}"):
                            st.session_state[DEL_KEY] = bid
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar cuenta bancaria #{did}?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="banco_confirm"):
                            supabase.table(TABLE).delete().eq("clientebancoid", did).execute()
                            st.success("✅ Cuenta eliminada")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="banco_cancel"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["clientebancoid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Cuenta #{eid}")
                    with st.form(f"edit_banco_{eid}"):
                        iban = st.text_input("IBAN", cur.get("iban",""))
                        bic = st.text_input("BIC", cur.get("bic",""))
                        titular = st.text_input("Titular", cur.get("titular",""))
                        banco = st.text_input("Banco", cur.get("banco",""))
                        pred = st.checkbox("Predeterminado", value=cur.get("predeterminado",False))
                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "iban": iban,
                                "bic": bic,
                                "titular": titular,
                                "banco": banco,
                                "predeterminado": pred
                            }).eq("clientebancoid", eid).execute()
                            st.success("✅ Cuenta actualizada")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar cuentas.")

    # ---------------------------
    # TAB 2
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,iban,bic,titular,banco,predeterminado")

        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_banco")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_banco"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Bancos Cliente")
        st.markdown("""
        - **clientebancoid** → Identificador único del registro.  
        - **clienteid** → Cliente al que pertenece la cuenta bancaria.  
        - **iban** → Número IBAN (obligatorio).  
        - **bic** → Código BIC/SWIFT de la entidad.  
        - **titular** → Nombre del titular de la cuenta.  
        - **banco** → Nombre de la entidad bancaria.  
        - **predeterminado** → Si es la cuenta principal de ese cliente (true/false).  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "clienteid,iban,bic,titular,banco,predeterminado\n"
            "1,ES9820385778983000760236,BKTRSESMM,Juan Pérez,Banco Santander,true",
            language="csv"
        )
