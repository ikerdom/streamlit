# modules/cliente_condiciones.py
import streamlit as st
import pandas as pd
from .ui import render_header, can_edit, fetch_options

TABLE = "clientecondiciones"
FIELDS_LIST = [
    "clientecondicionesid","clienteid","formapagoid","formafacturacionid",
    "diaspago","diaspago1","diaspago2","diaspago3",
    "limitecredito","descuentocomercial",
    "observaciones","fechaalta"
]

EDIT_KEY = "editing_cc"
DEL_KEY  = "pending_delete_cc"

# ---------------------------
# Helpers contra NaN
# ---------------------------
def safe_int(val, default=0):
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return default
        return int(val)
    except Exception:
        return default

def safe_float(val, default=0.0):
    try:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return default
        return float(val)
    except Exception:
        return default

# ---------------------------
# Render principal
# ---------------------------
def render_cliente_condiciones(supabase):
    # ✅ Cabecera
    render_header(
        "⚙️ Condiciones de Cliente",
        "Condiciones comerciales aplicadas a clientes."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1
    # ---------------------------
    with tab1:
        st.subheader("Añadir Condición")

        clientes, map_cli   = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")
        formas, map_formas  = fetch_options(supabase, "formapago", "formapagoid", "nombre")
        facts,  map_facts   = fetch_options(supabase, "forma_facturacion", "formafacturacionid", "nombre")

        with st.form("form_cond"):
            cliente = st.selectbox("Cliente *", clientes)
            forma   = st.selectbox("Forma de pago *", formas)
            fact    = st.selectbox("Forma de facturación *", facts)

            # 👉 Días de pago
            col1, col2, col3, col4 = st.columns(4)
            dias  = col1.number_input("Días pago (general)", min_value=0, step=1)
            dias1 = col2.number_input("Días pago 1", min_value=0, step=1)
            dias2 = col3.number_input("Días pago 2", min_value=0, step=1)
            dias3 = col4.number_input("Días pago 3", min_value=0, step=1)

            # 👉 Límite y descuento
            col5, col6 = st.columns(2)
            limite = col5.number_input("Límite crédito (€)", min_value=0.0, step=100.0)
            desc   = col6.number_input("Descuento comercial (%)", min_value=0.0, max_value=100.0, step=0.5)

            obs = st.text_area("Observaciones")

            if st.form_submit_button("➕ Insertar"):
                if not cliente or not forma or not fact:
                    st.error("❌ Cliente, Forma de pago y Forma de facturación son obligatorios")
                else:
                    supabase.table(TABLE).insert({
                        "clienteid":          map_cli.get(cliente),
                        "formapagoid":        map_formas.get(forma),
                        "formafacturacionid": map_facts.get(fact),
                        "diaspago":           dias,
                        "diaspago1":          dias1,
                        "diaspago2":          dias2,
                        "diaspago3":          dias3,
                        "limitecredito":      limite,
                        "descuentocomercial": desc,
                        "observaciones":      obs
                    }).execute()
                    st.success("✅ Condición insertada")
                    st.rerun()

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar condiciones")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="ccampo")
                valor = st.text_input("Valor a buscar", key="cvalor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"], horizontal=True, key="corden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # Mapear IDs a nombres legibles
        df["clienteid"]          = df["clienteid"].map({v: k for k,v in map_cli.items()})
        df["formapagoid"]        = df["formapagoid"].map({v: k for k,v in map_formas.items()})
        df["formafacturacionid"] = df["formafacturacionid"].map({v: k for k,v in map_facts.items()})

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Condiciones registradas")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar condiciones (requiere login)"):
            if can_edit():
                for _, row in df.iterrows():
                    cid = int(row["clientecondicionesid"])
                    st.markdown(f"**{row.get('clienteid','')} — {row.get('formapagoid','')} — {row.get('formafacturacionid','')}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_cc_{cid}"):
                            st.session_state[EDIT_KEY] = cid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_cc_{cid}"):
                            st.session_state[DEL_KEY] = cid
                            st.rerun()
                    st.markdown("---")

                # Confirmar borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar condición #{did}?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="cc_confirm"):
                            supabase.table(TABLE).delete().eq("clientecondicionesid", did).execute()
                            st.success("✅ Condición eliminada")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="cc_cancel"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["clientecondicionesid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Condición #{eid}")
                    with st.form(f"edit_cc_{eid}"):
                        forma_edit = st.selectbox("Forma de pago *", formas,
                                                  index=(formas.index(cur.get("formapagoid")) if cur.get("formapagoid") in formas else 0))
                        fact_edit  = st.selectbox("Forma de facturación *", facts,
                                                  index=(facts.index(cur.get("formafacturacionid")) if cur.get("formafacturacionid") in facts else 0))

                        col1, col2, col3, col4 = st.columns(4)
                        dias  = col1.number_input("Días de pago", value=safe_int(cur.get("diaspago")))
                        dias1 = col2.number_input("Días de pago 1", value=safe_int(cur.get("diaspago1")))
                        dias2 = col3.number_input("Días de pago 2", value=safe_int(cur.get("diaspago2")))
                        dias3 = col4.number_input("Días de pago 3", value=safe_int(cur.get("diaspago3")))

                        col5, col6 = st.columns(2)
                        limite = col5.number_input("Límite crédito (€)", value=safe_float(cur.get("limitecredito")))
                        desc   = col6.number_input("Descuento (%)", value=safe_float(cur.get("descuentocomercial")))

                        obs = st.text_area("Observaciones", value=cur.get("observaciones",""))

                        if st.form_submit_button("💾 Guardar"):
                            supabase.table(TABLE).update({
                                "formapagoid":        map_formas.get(forma_edit),
                                "formafacturacionid": map_facts.get(fact_edit),
                                "diaspago":           dias,
                                "diaspago1":          dias1,
                                "diaspago2":          dias2,
                                "diaspago3":          dias3,
                                "limitecredito":      limite,
                                "descuentocomercial": desc,
                                "observaciones":      obs
                            }).eq("clientecondicionesid", eid).execute()
                            st.success("✅ Condición actualizada")
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar condiciones.")

    # ---------------------------
    # TAB 2
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,formapagoid,formafacturacionid,diaspago,diaspago1,diaspago2,diaspago3,limitecredito,descuentocomercial,observaciones")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_condiciones")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_cc"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Condiciones de Cliente")
        st.markdown("""
        - **clienteid** → referencia al cliente.  
        - **formapagoid** → referencia a forma de pago.  
        - **formafacturacionid** → referencia a forma de facturación.  
        - **diaspago** → días de pago en caso de pago único.  
        - **diaspago1,2,3** → días de vencimiento en caso de pagos fraccionados.  
        - **limitecredito** → límite de crédito asignado (€).  
        - **descuentocomercial** → descuento general (%).  
        - **observaciones** → notas adicionales.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "clienteid,formapagoid,formafacturacionid,diaspago,diaspago1,diaspago2,diaspago3,limitecredito,descuentocomercial,observaciones\n"
            "1,2,1,30,0,0,0,5000,10.5,Cliente preferente\n"
            "2,3,2,0,30,60,90,12000,5.0,Pago en 3 plazos",
            language="csv"
        )
