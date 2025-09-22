import streamlit as st
import pandas as pd
from .ui import render_header, can_edit, fetch_options

TABLE = "crm_actuacion"
FIELDS_LIST = [
    "actuacionid","clienteid","trabajadorid","fecha",
    "canal","descripcion","estado"
]

CANAL_OPCIONES = ["Teléfono","Email","Visita","Otro"]
ESTADO_OPCIONES = ["Pendiente","En curso","Cerrado"]

EDIT_KEY = "editing_crm"
DEL_KEY  = "pending_delete_crm"

def render_crm_actuacion(supabase):
    # ✅ Cabecera corporativa con logo
    render_header(
        "📞 CRM Actuaciones",
        "Registro de llamadas, emails, visitas o incidencias con clientes o trabajadores."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # =========================
    # TAB 1 - FORMULARIO + TABLA
    # =========================
    with tab1:
        st.subheader("Añadir Actuación")

        modo = st.radio("Registrar actuación para:", ["Cliente", "Trabajador"], horizontal=True)

        clientes, map_clientes = fetch_options(supabase, "cliente", "clienteid", "nombrefiscal")
        trabajadores, map_trab = fetch_options(supabase, "trabajador", "trabajadorid", "nombre")

        with st.form("form_crm"):
            clienteid, trabajadorid = None, None

            if modo == "Cliente":
                cliente_sel = st.selectbox("Cliente *", clientes)
                clienteid = map_clientes.get(cliente_sel)

            elif modo == "Trabajador":
                trab_sel = st.selectbox("Trabajador *", trabajadores)
                trabajadorid = map_trab.get(trab_sel)

            fecha = st.date_input("Fecha")
            canal = st.selectbox("Canal", CANAL_OPCIONES)
            descripcion = st.text_area("Descripción *")
            estado = st.selectbox("Estado", ESTADO_OPCIONES)

            if st.form_submit_button("➕ Insertar"):
                if modo == "Cliente" and not clienteid:
                    st.error("❌ Debes seleccionar un cliente")
                elif modo == "Trabajador" and not trabajadorid:
                    st.error("❌ Debes seleccionar un trabajador")
                elif not descripcion.strip():
                    st.error("❌ La descripción es obligatoria")
                else:
                    nuevo = {
                        "clienteid": clienteid,
                        "trabajadorid": trabajadorid,
                        "fecha": str(fecha),
                        "canal": canal.lower(),
                        "descripcion": descripcion.strip(),
                        "estado": estado.lower()
                    }
                    supabase.table(TABLE).insert(nuevo).execute()
                    st.success("✅ Actuación registrada")
                    st.rerun()

        st.markdown("#### 📑 Actuaciones registradas")

        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            # Mapear nombres
            clientes_map = {c["clienteid"]: c["nombrefiscal"]
                            for c in supabase.table("cliente").select("clienteid,nombrefiscal").execute().data}
            trabajadores_map = {t["trabajadorid"]: t["nombre"]
                                for t in supabase.table("trabajador").select("trabajadorid,nombre").execute().data}

            df["Entidad"] = df.apply(
                lambda r: clientes_map.get(r["clienteid"]) if pd.notna(r["clienteid"]) else trabajadores_map.get(r["trabajadorid"], "—"),
                axis=1
            )
            df["Tipo"] = df.apply(
                lambda r: "Cliente" if pd.notna(r["clienteid"]) else "Trabajador",
                axis=1
            )

            # Cabecera tabla
            header = st.columns([0.5,0.5,2,2,2,2,3,2])
            for col, txt in zip(header, ["✏️","🗑️","Tipo","Entidad","Fecha","Canal","Descripción","Estado"]):
                col.markdown(f"**{txt}**")

            for _, row in df.iterrows():
                if pd.isna(row["actuacionid"]):
                    continue
                aid = int(row["actuacionid"])
                cols = st.columns([0.5,0.5,2,2,2,2,3,2])

                cols[2].write(row.get("Tipo",""))
                cols[3].write(row.get("Entidad",""))
                cols[4].write(str(row.get("fecha",""))[:10])
                cols[5].write(row.get("canal",""))
                cols[6].write(row.get("descripcion",""))
                cols[7].write(row.get("estado",""))

                # Botones editar/borrar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"edit_{aid}"):
                            st.session_state[EDIT_KEY] = aid; st.rerun()
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"del_{aid}"):
                            st.session_state[DEL_KEY] = aid; st.rerun()

            # Confirmación de borrado
            if st.session_state.get(DEL_KEY):
                did = st.session_state[DEL_KEY]
                st.markdown("---")
                st.error(f"⚠️ ¿Eliminar actuación #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="confirm_del"):
                        supabase.table(TABLE).delete().eq("actuacionid", did).execute()
                        st.success("✅ Actuación eliminada")
                        st.session_state[DEL_KEY] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="cancel_del"):
                        st.session_state[DEL_KEY] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get(EDIT_KEY):
                eid = st.session_state[EDIT_KEY]
                cur = df[df["actuacionid"]==eid].iloc[0].to_dict()
                st.markdown("---")
                st.subheader(f"Editar Actuación #{eid}")
                with st.form("edit_crm"):
                    descripcion = st.text_area("Descripción", cur.get("descripcion",""))
                    estado = st.selectbox(
                        "Estado", ESTADO_OPCIONES,
                        index=ESTADO_OPCIONES.index(cur.get("estado").capitalize())
                        if cur.get("estado") else 0
                    )
                    if st.form_submit_button("💾 Guardar"):
                        supabase.table(TABLE).update({
                            "descripcion": descripcion,
                            "estado": estado.lower()
                        }).eq("actuacionid", eid).execute()
                        st.success("✅ Actuación actualizada")
                        st.session_state[EDIT_KEY] = None
                        st.rerun()
