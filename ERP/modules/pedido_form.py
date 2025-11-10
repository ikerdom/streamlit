# ======================================================
# 📦 FORMULARIO DE PEDIDO — Alta y edición
# ======================================================
import streamlit as st
from datetime import date
from modules.pedido_models import (
    load_clientes,
    load_trabajadores,
    load_tipos_pedido,
    load_procedencias_pedido,
    load_estados_pedido,
    load_formas_pago,
    load_transportistas,
)

def render_pedido_form(supabase, pedidoid: int | None = None, on_saved_rerun: bool = True):
    """Formulario de alta o edición de pedidos."""
    modo = "✏️ Editar pedido" if pedidoid else "➕ Nuevo pedido"
    st.subheader(modo)

    # ======================================================
    # 🔹 Cargar catálogos
    # ======================================================
    clientes = load_clientes(supabase)
    trabajadores = load_trabajadores(supabase)
    tipos = load_tipos_pedido(supabase)
    procedencias = load_procedencias_pedido(supabase)
    estados = load_estados_pedido(supabase)
    formas_pago = load_formas_pago(supabase)
    transportistas = load_transportistas(supabase)

    pedido = {}
    if pedidoid:
        try:
            r = supabase.table("pedido").select("*").eq("pedidoid", pedidoid).single().execute()
            if r.data:
                pedido = r.data
            else:
                st.warning("⚠️ Pedido no encontrado.")
                return
        except Exception as e:
            st.error(f"❌ Error cargando pedido: {e}")
            return

    # ======================================================
    # 🧾 Formulario principal
    # ======================================================
    with st.expander("📋 Datos generales", expanded=True):
        with st.form(f"form_pedido_{pedidoid or 'new'}"):
            c1, c2, c3 = st.columns(3)
            with c1:
                cliente_sel = st.selectbox("Cliente", ["(sin cliente)"] + list(clientes.keys()),
                                           index=_sel_index(clientes, pedido.get("clienteid")))
            with c2:
                trabajador_sel = st.selectbox("Vendedor", ["(sin vendedor)"] + list(trabajadores.keys()),
                                              index=_sel_index(trabajadores, pedido.get("trabajadorid")))
            with c3:
                numero = st.text_input("Número de pedido", pedido.get("numero", ""))

            cA, cB, cC = st.columns(3)
            with cA:
                tipo_sel = st.selectbox("Tipo de pedido", ["(sin tipo)"] + list(tipos.keys()),
                                        index=_sel_index(tipos, pedido.get("tipo_pedidoid")))
                pedido_origen = st.text_input("Pedido origen (si es devolución)", str(pedido.get("pedido_origenid") or ""))
            with cB:
                proc_sel = st.selectbox("Procedencia", ["(sin procedencia)"] + list(procedencias.keys()),
                                        index=_sel_index(procedencias, pedido.get("procedencia_pedidoid")))
            with cC:
                est_sel = st.selectbox("Estado", ["(sin estado)"] + list(estados.keys()),
                                       index=_sel_index(estados, pedido.get("estado_pedidoid")))

            cD, cE, cF = st.columns(3)
            with cD:
                pago_sel = st.selectbox("Forma de pago", ["(sin forma de pago)"] + list(formas_pago.keys()),
                                        index=_sel_index(formas_pago, pedido.get("formapagoid")))
            with cE:
                transp_sel = st.selectbox("Transportista", ["(sin transportista)"] + list(transportistas.keys()),
                                          index=_sel_index(transportistas, pedido.get("transportistaid")))
            with cF:
                fecha_pedido = st.date_input("Fecha pedido",
                                             value=date.fromisoformat(pedido["fecha_pedido"])
                                             if pedido.get("fecha_pedido") else date.today())

            referencia = st.text_input("Referencia cliente", pedido.get("referencia_cliente", ""))
            justificante = st.text_input("URL justificante de pago", pedido.get("justificante_pago_url", ""))
            facturar = st.checkbox("Facturar individualmente", value=bool(pedido.get("facturar_individual", False)))

            enviar = st.form_submit_button("💾 Guardar pedido", use_container_width=True)

        if enviar:
            if not numero.strip():
                st.warning("⚠️ El número de pedido es obligatorio.")
                return

            payload = {
                "numero": numero.strip(),
                "referencia_cliente": referencia.strip() or None,
                "fecha_pedido": fecha_pedido.isoformat(),
                "justificante_pago_url": justificante.strip() or None,
                "facturar_individual": facturar,
                "clienteid": clientes.get(cliente_sel) if cliente_sel != "(sin cliente)" else None,
                "trabajadorid": trabajadores.get(trabajador_sel) if trabajador_sel != "(sin vendedor)" else None,
                "tipo_pedidoid": tipos.get(tipo_sel) if tipo_sel != "(sin tipo)" else None,
                "procedencia_pedidoid": procedencias.get(proc_sel) if proc_sel != "(sin procedencia)" else None,
                "estado_pedidoid": estados.get(est_sel) if est_sel != "(sin estado)" else None,
                "formapagoid": formas_pago.get(pago_sel) if pago_sel != "(sin forma de pago)" else None,
                "transportistaid": transportistas.get(transp_sel) if transp_sel != "(sin transportista)" else None,
                "pedido_origenid": int(pedido_origen) if pedido_origen.strip().isdigit() else None,
            }

            try:
                if pedidoid:
                    supabase.table("pedido").update(payload).eq("pedidoid", pedidoid).execute()
                    st.toast("✅ Pedido actualizado correctamente.", icon="✅")
                else:
                    res = supabase.table("pedido").insert(payload).execute()
                    nuevo_id = res.data[0]["pedidoid"] if res.data else None
                    st.toast(f"✅ Pedido creado (ID {nuevo_id}).", icon="✅")
                if on_saved_rerun:
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error guardando pedido: {e}")


# ======================================================
# 🔧 Helper para índices dinámicos en selects
# ======================================================
def _sel_index(diccionario, id_actual):
    """Devuelve el índice correcto del elemento seleccionado."""
    if not id_actual:
        return 0
    for i, (k, v) in enumerate(diccionario.items()):
        if v == id_actual:
            return i + 1
    return 0
