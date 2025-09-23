# modules/crm_actuacion.py
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
    # ✅ Cabecera
    render_header(
        "📞 CRM Actuaciones",
        "Registro de llamadas, emails, visitas o incidencias con clientes o trabajadores."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # ---------------------------
    # TAB 1: Formulario + Tabla
    # ---------------------------
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

        # ---------------------------
        # 📑 Actuaciones con filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar actuaciones")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            clientes_map = {c["clienteid"]: c["nombrefiscal"]
                            for c in supabase.table("cliente").select("clienteid,nombrefiscal").execute().data}
            trabajadores_map = {t["trabajadorid"]: t["nombre"]
                                for t in supabase.table("trabajador").select("trabajadorid,nombre").execute().data}

            df["Entidad"] = df.apply(
                lambda r: clientes_map.get(r["clienteid"]) if pd.notna(r["clienteid"]) else trabajadores_map.get(r["trabajadorid"], "—"),
                axis=1
            )
            df["Tipo"] = df.apply(lambda r: "Cliente" if pd.notna(r["clienteid"]) else "Trabajador", axis=1)

            # 🔎 Filtros
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Campo", ["Entidad","Tipo","canal","estado","fecha","descripcion"])
                valor = st.text_input("Valor a buscar")
                orden = st.radio("Ordenar por", ["Ascendente","Descendente"], horizontal=True)

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

            # Tabla
            st.markdown("### 📑 Actuaciones registradas")
            st.dataframe(df[["Tipo","Entidad","fecha","canal","descripcion","estado"]], use_container_width=True)

            # ---------------------------
            # ⚙️ Acciones avanzadas
            # ---------------------------
            st.markdown("### ⚙️ Acciones avanzadas")
            with st.expander("⚙️ Editar / Borrar actuaciones (requiere login)"):
                if can_edit():
                    for _, row in df.iterrows():
                        aid = int(row["actuacionid"])
                        st.markdown(f"**{row['Tipo']} → {row['Entidad']}** | {row['fecha']} | {row['canal'].capitalize()}")
                        st.caption(f"{row['descripcion']} ({row['estado'].capitalize()})")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✏️ Editar", key=f"edit_crm_{aid}"):
                                st.session_state[EDIT_KEY] = aid; st.rerun()
                        with c2:
                            if st.button("🗑️ Borrar", key=f"del_crm_{aid}"):
                                st.session_state[DEL_KEY] = aid; st.rerun()
                        st.markdown("---")

                    # Confirmar borrado
                    if st.session_state.get(DEL_KEY):
                        did = st.session_state[DEL_KEY]
                        st.error(f"⚠️ ¿Eliminar actuación #{did}?")
                        c1,c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Confirmar", key="crm_confirm_del"):
                                supabase.table(TABLE).delete().eq("actuacionid", did).execute()
                                st.success("✅ Actuación eliminada")
                                st.session_state[DEL_KEY] = None
                                st.rerun()
                        with c2:
                            if st.button("❌ Cancelar", key="crm_cancel_del"):
                                st.session_state[DEL_KEY] = None
                                st.rerun()

                    # Edición inline
                    if st.session_state.get(EDIT_KEY):
                        eid = st.session_state[EDIT_KEY]
                        cur = df[df["actuacionid"]==eid].iloc[0].to_dict()
                        st.subheader(f"Editar Actuación #{eid}")
                        with st.form(f"edit_crm_{eid}"):
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
                else:
                    st.warning("⚠️ Debes iniciar sesión para editar o borrar registros.")

    # ---------------------------
    # TAB 2: CSV
    # ---------------------------
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: clienteid,trabajadorid,fecha,canal,descripcion,estado")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_crm")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_crm"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

    # ---------------------------
    # TAB 3: Instrucciones
    # ---------------------------
    with tab3:
        st.subheader("📑 Campos de Actuaciones CRM")
        st.markdown("""
        - **actuacionid** → identificador único de la actuación.  
        - **clienteid / trabajadorid** → referencia a la entidad asociada.  
        - **fecha** → fecha de la actuación (YYYY-MM-DD).  
        - **canal** → medio de comunicación (Teléfono, Email, Visita, Otro).  
        - **descripcion** → detalle de la interacción.  
        - **estado** → estado de la actuación (Pendiente, En curso, Cerrado).  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "clienteid,trabajadorid,fecha,canal,descripcion,estado\n"
            "1,,2025-09-22,Teléfono,Llamada de seguimiento,pendiente\n"
            ",2,2025-09-21,Email,Revisión de contrato,cerrado",
            language="csv"
        )
