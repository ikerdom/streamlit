import streamlit as st
import pandas as pd
from .ui import (
    section_header, draw_live_df, can_edit,
    fetch_options
)
from .ui import safe_image
from .ui import render_header


TABLE = "clientecondiciones"
FIELDS_LIST = [
    "clientecondicionesid","clienteid","formapagoid","formafacturacionid",
    "diaspago","diaspago1","diaspago2","diaspago3",
    "limitecredito","descuentocomercial",
    "observaciones","fechaalta"
]

EDIT_KEY = "editing_cc"
DEL_KEY  = "pending_delete_cc"
FACT_OPTIONS = ["Un solo pago", "Pagos fraccionados"]

# Helpers seguros contra NaN
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

def render_cliente_condiciones(supabase):
    # Cabecera con logo

    render_header(
        "⚙️ Condiciones de Cliente", "Condiciones comerciales aplicadas a clientes."
    )
    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])



    # ---------------------------
    # TAB 1: Formulario + tabla
    # ---------------------------
    with tab1:
        st.subheader("Añadir Condición")

        clientes, map_cli  = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")
        formas, map_formas = fetch_options(supabase, "formapago", "formapagoid", "nombre")

        with st.form("form_cond"):
            cliente = st.selectbox("Cliente *", clientes)
            forma   = st.selectbox("Forma de pago *", formas)
            fact    = st.selectbox("Forma de facturación *", FACT_OPTIONS, index=0)

            # 👉 Días tabulados
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                dias = st.number_input("Días pago (general)", min_value=0, step=1)
            with col2:
                dias1 = st.number_input("Días pago 1", min_value=0, step=1)
            with col3:
                dias2 = st.number_input("Días pago 2", min_value=0, step=1)
            with col4:
                dias3 = st.number_input("Días pago 3", min_value=0, step=1)

            # 👉 Límite y descuento juntos
            col5, col6 = st.columns(2)
            with col5:
                limite = st.number_input("Límite crédito (€)", min_value=0.0, step=100.0)
            with col6:
                desc = st.number_input("Descuento comercial (%)", min_value=0.0, max_value=100.0, step=0.5)

            obs = st.text_area("Observaciones")

            if st.form_submit_button("➕ Insertar"):
                if not cliente or not forma or not fact:
                    st.error("❌ Cliente, Forma de pago y Forma de facturación son obligatorios")
                else:
                    supabase.table(TABLE).insert({
                        "clienteid":          map_cli.get(cliente),
                        "formapagoid":        map_formas.get(forma),
                        "formafacturacionid": fact,
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

        st.markdown("#### 📑 Condiciones (en vivo)")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            # 🔹 Mapear IDs a nombres legibles
            clientes, map_cli  = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")
            formas, map_formas = fetch_options(supabase, "formapago", "formapagoid", "nombre")

            df["clienteid"]   = df["clienteid"].map({v: k for k,v in map_cli.items()})
            df["formapagoid"] = df["formapagoid"].map({v: k for k,v in map_formas.items()})

            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            for _, row in df.iterrows():
                cid = int(row["clientecondicionesid"])
                cols = st.columns([0.5,0.5,3,3,2,2])
                with cols[0]:
                    if can_edit() and st.button("✏️", key=f"edit_cc_{cid}"):
                        st.session_state[EDIT_KEY] = cid
                        st.rerun()
                with cols[1]:
                    if can_edit() and st.button("🗑️", key=f"del_cc_{cid}"):
                        st.session_state[DEL_KEY] = cid
                        st.rerun()
                cols[2].write(row.get("clienteid",""))
                cols[3].write(row.get("formapagoid",""))
                cols[4].write(row.get("formafacturacionid",""))
                cols[5].write(f"{row.get('limitecredito','')} €")

            # Confirmar borrado
            if st.session_state.get(DEL_KEY):
                did = st.session_state[DEL_KEY]
                st.error(f"⚠️ ¿Eliminar condición #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del_cc"):
                        supabase.table(TABLE).delete().eq("clientecondicionesid", did).execute()
                        st.success("✅ Condición eliminada")
                        st.session_state[DEL_KEY] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del_cc"):
                        st.session_state[DEL_KEY] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get(EDIT_KEY):
                eid = st.session_state[EDIT_KEY]
                cur = df[df["clientecondicionesid"]==eid].iloc[0].to_dict()
                st.markdown("---")
                st.subheader(f"Editar Condición #{eid}")
                with st.form(f"edit_cc_{eid}"):
                    forma_edit = st.selectbox(
                        "Forma de pago *", formas,
                        index=(formas.index(cur.get("formapagoid")) if cur.get("formapagoid") in formas else 0)
                    )
                    fact_edit = st.selectbox(
                        "Forma de facturación *", FACT_OPTIONS,
                        index=(FACT_OPTIONS.index(cur.get("formafacturacionid"))
                               if cur.get("formafacturacionid") in FACT_OPTIONS else 0)
                    )

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        dias  = st.number_input("Días de pago", value=safe_int(cur.get("diaspago")))
                    with col2:
                        dias1 = st.number_input("Días de pago 1", value=safe_int(cur.get("diaspago1")))
                    with col3:
                        dias2 = st.number_input("Días de pago 2", value=safe_int(cur.get("diaspago2")))
                    with col4:
                        dias3 = st.number_input("Días de pago 3", value=safe_int(cur.get("diaspago3")))

                    col5, col6 = st.columns(2)
                    with col5:
                        limite = st.number_input("Límite crédito (€)", value=safe_float(cur.get("limitecredito")))
                    with col6:
                        desc   = st.number_input("Descuento (%)", value=safe_float(cur.get("descuentocomercial")))

                    obs = st.text_area("Observaciones", value=cur.get("observaciones",""))

                    if st.form_submit_button("💾 Guardar"):
                        supabase.table(TABLE).update({
                            "formapagoid":        map_formas.get(forma_edit),
                            "formafacturacionid": fact_edit,
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

                if st.button("❌ Cancelar", key=f"cancel_cc_{eid}"):
                    st.session_state[EDIT_KEY] = None
                    st.rerun()

    # ---------------------------
    # TAB 2: CSV
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,formapagoid,formafacturacionid,diaspago,diaspago1,diaspago2,diaspago3,limitecredito,descuentocomercial,observaciones")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_condiciones")
        if up:
            df = pd.read_csv(up)
            st.dataframe(df, use_container_width=True)
            if st.button("➕ Insertar todos"):
                supabase.table(TABLE).insert(df.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df)}")
                st.rerun()
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # ---------------------------
    # TAB 3: Instrucciones
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Condiciones de Cliente")
        st.markdown("""
        - **clienteid** → referencia al cliente.  
        - **formapagoid** → referencia a forma de pago.  
        - **formafacturacionid** → solo puede ser: *Un solo pago* o *Pagos fraccionados*.  
        - **diaspago** → días de pago en caso de pago único.  
        - **diaspago1,2,3** → días de vencimiento en caso de pagos fraccionados.  
        - **limitecredito** → límite de crédito asignado (€).  
        - **descuentocomercial** → descuento general (%).  
        - **observaciones** → notas adicionales.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "clienteid,formapagoid,formafacturacionid,diaspago,diaspago1,diaspago2,diaspago3,limitecredito,descuentocomercial,observaciones\n"
            "1,2,Un solo pago,30,0,0,0,5000,10.5,Cliente preferente\n"
            "2,3,Pagos fraccionados,0,30,60,90,12000,5.0,Pago en 3 plazos",
            language="csv"
        )
