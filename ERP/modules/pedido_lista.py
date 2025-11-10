import io
import math
import pandas as pd
import streamlit as st
from datetime import date, datetime
from modules.pedido_form import render_pedido_form


from modules.pedido_models import (
    load_clientes,
    load_trabajadores,
    load_estados_pedido,
    load_tipos_pedido,
    load_procedencias_pedido,
    load_formas_pago,
    load_transportistas,
)
from modules.pedido_form import render_pedido_form
from modules.precio_engine import calcular_precio_linea  # ⬅️ arriba del archivo


# ======================================================
# 🔄 Forward declarations (para evitar warnings de Pylance)
# ======================================================
def _render_table(pedidos: list[dict]):
    pass

def _render_pedido_modal(
    supabase,
    pedidoid: int,
    estados: dict,
    clientes: dict,
    trabajadores: dict,
    formas_pago: dict,
    transportistas: dict,
):
    pass



# ======================================================
# 💡 Utilidades
# ======================================================
def _safe(val, default="-"):
    return val if val not in (None, "", "null") else default


def _range(page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size - 1
    return start, end


def _label_from(catalog: dict, id_val) -> str:
    if not id_val:
        return "-"
    for k, v in (catalog or {}).items():
        if v == id_val:
            return k
    return "-"


def _color_estado(nombre_estado: str) -> str:
    if not nombre_estado:
        return "#9ca3af"
    n = (nombre_estado or "").lower()
    if "pend" in n:
        return "#f59e0b"
    if "confir" in n or "curso" in n:
        return "#3b82f6"
    if "enviado" in n:
        return "#6366f1"
    if "entreg" in n or "factur" in n:
        return "#10b981"
    if "cancel" in n or "devol" in n:
        return "#ef4444"
    return "#6b7280"


def _money(v):
    try:
        return f"{float(v):.2f} €"
    except Exception:
        return "-"


def _abrir_edicion(pedidoid: int):
    st.session_state["pedido_editar_id"] = pedidoid
    st.session_state["pedido_show_form"] = True
    st.session_state["show_pedido_modal"] = False
    st.rerun()


# ======================================================
# 📦 VISTA PRINCIPAL — PEDIDOS
# ======================================================
def render_pedido_lista(supabase):
    """Vista general de pedidos, devoluciones e incidencias."""
    modo_inci = st.session_state.get("modo_incidencias", False)
    tipo_filtro = st.session_state.get("pedido_tipo_filtro")

    if modo_inci:
        st.header("⚠️ Gestión de incidencias")
        st.caption("Listado de pedidos que tienen incidencias registradas (pendientes o solucionadas).")
    elif tipo_filtro == "Devolución":
        st.header("🔁 Gestión de devoluciones")
        st.caption("Pedidos de devolución — generan impacto negativo en stock y facturación.")
    else:
        st.header("📦 Gestión de pedidos")
        st.caption("Gestiona tus pedidos desde una sola vista: cabecera, líneas, totales y observaciones.")

    # ----------------------------
    # Estado de sesión
    # ----------------------------
    session = st.session_state
    defaults = {
        "pedido_page": 1,
        "pedido_view": "Tarjetas",
        "pedido_show_form": False,
        "pedido_editar_id": None,
        "show_pedido_modal": False,
        "pedido_modal_id": None,
    }
    for k, v in defaults.items():
        session.setdefault(k, v)

    page_size_cards, page_size_table = 12, 30

    # ----------------------------
    # Catálogos
    # ----------------------------
    clientes = load_clientes(supabase)
    trabajadores = load_trabajadores(supabase)
    estados = load_estados_pedido(supabase)
    tipos = load_tipos_pedido(supabase)
    procedencias = load_procedencias_pedido(supabase)
    formas_pago = load_formas_pago(supabase)
    transportistas = load_transportistas(supabase)

    # ----------------------------
    # Filtros
    # ----------------------------
    colf1, colf2, colf3, colf4, colf5 = st.columns([2, 2, 2, 2, 1])
    with colf1:
        q = st.text_input("🔍 Buscar (nº pedido / referencia / cliente)", key="pedido_q")
    with colf2:
        estado_sel = st.selectbox("Estado", ["Todos"] + list(estados.keys()), key="pedido_estado")
    with colf3:
        tipo_sel = st.selectbox("Tipo", ["Todos"] + list(tipos.keys()), key="pedido_tipo")
    with colf4:
        proc_sel = st.selectbox("Procedencia", ["Todas"] + list(procedencias.keys()), key="pedido_proc")
    with colf5:
        view = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, key="pedido_view")

    colf6, colf7, colf8 = st.columns([2, 2, 2])
    with colf6:
        trabajador_sel = st.selectbox("Trabajador", ["Todos"] + list(trabajadores.keys()), key="pedido_trab")
    with colf7:
        fecha_desde = st.date_input("Desde", value=None, key="pedido_from")
    with colf8:
        fecha_hasta = st.date_input("Hasta", value=None, key="pedido_to")

    if st.button("➕ Nuevo pedido", use_container_width=True):
        session["pedido_show_form"] = True
        session["pedido_editar_id"] = None
        session["show_pedido_modal"] = False

    st.markdown("---")

    # ----------------------------
    # Query principal
    # ----------------------------
    pedidos, total = [], 0
    try:
        base = supabase.table("pedido").select("*")

        # 🔁 Filtro modo devoluciones
        if tipo_filtro == "Devolución":
            try:
                tipo_dev = (
                    supabase.table("pedido_tipo")
                    .select("tipo_pedidoid")
                    .eq("nombre", "Devolución")
                    .single()
                    .execute()
                    .data
                )
                if tipo_dev:
                    base = base.eq("tipo_pedidoid", tipo_dev["tipo_pedidoid"])
            except Exception as e:
                st.warning(f"⚠️ No se pudo aplicar filtro de tipo 'Devolución': {e}")

        # Filtros normales
        if q:
            base = base.or_(f"numero.ilike.%{q}%,referencia_cliente.ilike.%{q}%")
        if estado_sel != "Todos":
            base = base.eq("estado_pedidoid", estados[estado_sel])
        if tipo_sel != "Todos":
            base = base.eq("tipo_pedidoid", tipos[tipo_sel])
        if proc_sel != "Todas":
            base = base.eq("procedencia_pedidoid", procedencias[proc_sel])
        if trabajador_sel != "Todos":
            base = base.eq("trabajadorid", trabajadores[trabajador_sel])
        if fecha_desde:
            base = base.gte("fecha_pedido", fecha_desde.isoformat())
        if fecha_hasta:
            base = base.lte("fecha_pedido", fecha_hasta.isoformat())

        # Ejecutar consulta paginada
        page = session.pedido_page
        per_page = page_size_cards if view == "Tarjetas" else page_size_table
        start, end = _range(page, per_page)
        data = base.order("fecha_pedido", desc=True).range(start, end).execute()
        pedidos = data.data or []

        # ⚠️ Filtrar incidencias si aplica
        if modo_inci:
            incidencias = supabase.table("incidencia").select("pedidoid, estado").execute().data or []
            ids = {i["pedidoid"] for i in incidencias}
            pedidos = [p for p in pedidos if p["pedidoid"] in ids]
            estados_inci = {i["pedidoid"]: i["estado"] for i in incidencias}
            for p in pedidos:
                p["estado_incidencia"] = estados_inci.get(p["pedidoid"], "Sin estado")

        total = len(pedidos)
    except Exception as e:
        st.error(f"❌ Error cargando pedidos: {e}")

    # ----------------------------
    # Formulario de edición inline
    # ----------------------------
    if session.get("pedido_show_form"):
        with st.expander("✏️ Editor de pedido (cabecera)", expanded=True):
            try:
                render_pedido_form(supabase, pedidoid=session.get("pedido_editar_id"), on_saved_rerun=True)
            except Exception as e:
                st.error(f"❌ Error abriendo formulario: {e}")

    # ----------------------------
    # Paginación
    # ----------------------------
    total_pages = max(1, math.ceil(max(1, total) / (page_size_cards if view == "Tarjetas" else page_size_table)))
    st.caption(f"Página {session.pedido_page} de {total_pages} — Total aprox. página: {total}")

    colp1, colp2, colp3, _ = st.columns([1, 1, 1, 5])
    if colp1.button("⏮️", disabled=session.pedido_page <= 1):
        session.pedido_page = 1
        st.rerun()
    if colp2.button("◀️", disabled=session.pedido_page <= 1):
        session.pedido_page -= 1
        st.rerun()
    if colp3.button("▶️", disabled=session.pedido_page >= total_pages):
        session.pedido_page += 1
        st.rerun()

    st.markdown("---")

    # ----------------------------
    # KPIs de la página
    # ----------------------------
    e_pend = estados.get("Pendiente")
    e_curso = estados.get("En curso") or estados.get("Confirmado")
    e_env = estados.get("Enviado")
    e_entr = estados.get("Entregado")
    e_fact = estados.get("Facturado")

    k_total = len(pedidos)
    k_pend = sum(1 for p in pedidos if p.get("estado_pedidoid") == e_pend)
    k_curso = sum(1 for p in pedidos if p.get("estado_pedidoid") == e_curso)
    k_env = sum(1 for p in pedidos if p.get("estado_pedidoid") == e_env)
    k_ok = sum(1 for p in pedidos if p.get("estado_pedidoid") in (e_entr, e_fact))

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📦 Pedidos (página)", k_total)
    m2.metric("🕓 Pendientes", k_pend)
    m3.metric("🔵 En curso", k_curso)
    m4.metric("🚚 Enviados", k_env)
    m5.metric("✅ Cerrados", k_ok)

    # ----------------------------
    # Render listado
    # ----------------------------
    if not pedidos:
        st.info("📭 No hay pedidos que coincidan con los filtros.")
        return

    if view == "Tarjetas":
        cols = st.columns(3)
        for idx, p in enumerate(pedidos):
            with cols[idx % 3]:
                _render_pedido_card(p, supabase, estados, clientes)
    else:
        _render_table(pedidos)

    if session.get("show_pedido_modal"):
        _render_pedido_modal(
            supabase,
            session.get("pedido_modal_id"),
            estados,
            clientes,
            trabajadores,
            formas_pago,
            transportistas,
        )


# ======================================================
# 💳 Tarjetas
# ======================================================
def _render_pedido_card(p, supabase, estados, clientes):
    cliente_nombre = _label_from(clientes, p.get("clienteid"))
    estado_nombre = _label_from(estados, p.get("estado_pedidoid"))
    color_estado = _color_estado(estado_nombre)

    if "devol" in (estado_nombre or "").lower():
        color_estado = "#ef4444"
    if "estado_incidencia" in p:
        estado_inci = p["estado_incidencia"].lower()
        if "solucion" in estado_inci:
            color_estado = "#10b981"
        elif "pend" in estado_inci:
            color_estado = "#f59e0b"

    bloqueado = any(b in (estado_nombre or "").lower() for b in ["facturado", "enviado", "confirmado"])

    st.markdown(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin-bottom:10px;
                    background:#fff;box-shadow:0 1px 2px rgba(0,0,0,0.05);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div><b>#{_safe(p.get('numero'))}</b> — {_safe(cliente_nombre)}</div>
                <span style="background:{color_estado};color:#fff;padding:3px 8px;border-radius:8px;font-size:0.8rem;">
                    {estado_nombre or '-'}
                </span>
            </div>
            <div style="margin-top:4px;color:#555;font-size:0.9rem;">
                📅 {_safe(p.get("fecha_pedido"))}
            </div>
            <div style="color:#777;font-size:0.85rem;margin-top:4px;">
                Ref. cliente: {_safe(p.get("referencia_cliente"))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- AÑADIR DESDE AQUÍ ---
    if p.get("presupuesto_origenid"):
        st.markdown(
            f"🧾 **Origen:** Presupuesto #{p['presupuesto_origenid']}"
        )
    # --- HASTA AQUÍ ---

    colA, colB, colC = st.columns(3)
    with colA:

        if st.button("📄 Ficha", key=f"ficha_{p['pedidoid']}", use_container_width=True):
            st.session_state["pedido_modal_id"] = p["pedidoid"]
            st.session_state["show_pedido_modal"] = True
            st.session_state["pedido_show_form"] = False
            st.rerun()
    with colB:
        st.button(
            "✏️ Editar",
            key=f"edit_{p['pedidoid']}",
            use_container_width=True,
            disabled=bloqueado,
            on_click=(lambda pid=p["pedidoid"]: _abrir_edicion(pid)) if not bloqueado else None,
        )
    with colC:
        st.button("🧾 Duplicar", key=f"dup_{p['pedidoid']}", use_container_width=True, disabled=True)
# ======================================================
# 🧩 Modal DETALLE / EDICIÓN / DEVOLUCIÓN
# ======================================================
def _render_pedido_modal(
    supabase,
    pedidoid: int,
    estados: dict,
    clientes: dict,
    trabajadores: dict,
    formas_pago: dict,
    transportistas: dict,
):
    if not pedidoid:
        return

    st.markdown("---")
    st.markdown("### 📋 Ficha del pedido")

    # --------------------------------------------
    # Cargar datos principales
    # --------------------------------------------
    try:
        p = supabase.table("pedido").select("*").eq("pedidoid", pedidoid).single().execute().data
    except Exception as e:
        st.error(f"❌ Error cargando pedido: {e}")
        return

    estado_lbl = _label_from(estados, p.get("estado_pedidoid"))
    cliente_lbl = _label_from(clientes, p.get("clienteid"))
    color_estado = _color_estado(estado_lbl)
    bloqueado = any(b in (estado_lbl or "").lower() for b in ["facturado", "enviado", "confirmado"])

    # --------------------------------------------
    # Botonera superior
    # --------------------------------------------
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        if st.button("⬅️ Cerrar ficha", use_container_width=True):
            st.session_state["show_pedido_modal"] = False
            st.session_state["pedido_modal_id"] = None
            st.rerun()
    with c2:
        st.button("🗑️ Eliminar pedido", use_container_width=True, disabled=bloqueado)
    with c3:
        st.button("📑 Duplicar", use_container_width=True, disabled=True)
    with c4:
        st.button("↩️ Crear devolución", use_container_width=True,
                  on_click=lambda pid=pedidoid: _crear_devolucion_desde_pedido(supabase, pid))

    if bloqueado:
        st.warning(f"🚫 Este pedido está en estado **{estado_lbl}** y no puede modificarse.")
    else:
        st.info(f"✏️ Pedido editable (estado: {estado_lbl}).")

    # --------------------------------------------
    # Detalle general
    # --------------------------------------------
    with st.expander("🔎 Detalle general del pedido", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Cliente:** {cliente_lbl}")
            st.markdown(f"**Estado:** <span style='color:{color_estado};font-weight:700'>{estado_lbl}</span>",
                        unsafe_allow_html=True)
        with col2:
            st.text(f"Fecha pedido: {_safe(p.get('fecha_pedido'))}")
            st.text(f"Confirmada: {_safe(p.get('fecha_confirmada'))}")
        with col3:
            st.text(f"Entrega prevista: {_safe(p.get('fecha_entrega_prevista'))}")
            st.text(f"Ref. cliente: {_safe(p.get('referencia_cliente'))}")

    # --- AÑADIR DESDE AQUÍ ---
    if p.get("presupuesto_origenid"):
        st.markdown(f"🧾 **Origen:** Presupuesto #{p['presupuesto_origenid']}")
    # --- OPCIONAL: abrir presupuesto origen desde el modal ---
    if p.get("presupuesto_origenid"):
        if st.button("🧾 Abrir presupuesto origen", use_container_width=True):
            st.session_state["show_presupuesto_modal"] = True
            st.session_state["presupuesto_modal_id"] = p["presupuesto_origenid"]
            # Si usas router/menu:
            # st.session_state["menu_actual"] = "Presupuestos"
            st.rerun()

    # --- HASTA AQUÍ ---

    # --------------------------------------------
    # Edición cabecera
    # --------------------------------------------
    st.markdown("---")
    st.subheader("✏️ Cabecera del pedido")
    if bloqueado:
        st.info("🔒 Edición deshabilitada para pedidos Facturados, Enviados o Confirmados.")
    else:
        try:
            render_pedido_form(supabase, pedidoid=pedidoid, on_saved_rerun=True)
        except Exception as e:
            st.error(f"❌ Error al abrir el formulario de cabecera: {e}")

    # --------------------------------------------
    # Líneas del pedido
    # --------------------------------------------
    st.markdown("---")
    st.subheader("🧾 Líneas del pedido")
    try:
        res_lin = (
            supabase.table("pedido_detalle")
            .select("pedido_detalleid, nombre_producto, cantidad, precio_unitario, descuento_pct, importe_total_linea")
            .eq("pedidoid", pedidoid)
            .order("pedido_detalleid")
            .execute()
        )
        lineas = res_lin.data or []
    except Exception as e:
        st.error(f"❌ Error cargando líneas: {e}")
        lineas = []

    if not lineas:
        st.info("📭 No hay líneas registradas para este pedido.")
    else:
        df = pd.DataFrame(lineas)
        df["importe_total_linea"] = df.apply(
            lambda r: r["importe_total_linea"]
            if r.get("importe_total_linea") not in (None, "")
            else float(r.get("cantidad", 0))
                 * float(r.get("precio_unitario", 0))
                 * (1 - float(r.get("descuento_pct", 0)) / 100.0),
            axis=1,
        )
        st.dataframe(df, use_container_width=True)

    # ======================================================
    # ➕ Añadir / eliminar línea (con motor de precios)
    # ======================================================
    if not bloqueado:
        with st.expander("➕ Añadir línea rápida", expanded=False):
            with st.form(f"form_add_linea_{pedidoid}"):
                st.caption("Calcula automáticamente el descuento y el IVA según las tarifas activas.")

                productoid = st.number_input("🆔 ID del producto (opcional)", min_value=0, value=0, step=1)
                nombre_prod = st.text_input("📦 Descripción / nombre del producto")
                cantidad = st.number_input("🔢 Cantidad", min_value=1.0, value=1.0)
                precio = st.number_input("💶 Precio base unitario (sin IVA)", min_value=0.0, value=0.0, step=0.01)
                desc_manual = st.number_input("🎯 Descuento adicional manual (%)",
                                              min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                add_ok = st.form_submit_button("💾 Añadir línea")

            if add_ok:
                try:
                    from modules.precio_engine import calcular_precio_linea

                    engine = calcular_precio_linea(
                        supabase,
                        clienteid=p.get("clienteid"),
                        productoid=(productoid or None),
                        precio_base_unit=precio,
                        cantidad=cantidad,
                    )

                    desc_total = engine["descuento_pct"] + desc_manual
                    subtotal_sin_iva = float(engine["unit_bruto"]) * cantidad * (1 - desc_total / 100.0)
                    iva_importe = subtotal_sin_iva * (engine["iva_pct"] / 100.0)
                    total_con_iva = subtotal_sin_iva + iva_importe

                    st.info(f"""
                    💰 **Resumen de cálculo**
                    - Precio base: {engine['unit_bruto']} €
                    - Descuento tarifa: {engine['descuento_pct']}%
                    - Descuento manual: {desc_manual}%
                    - Subtotal sin IVA: {subtotal_sin_iva:.2f} €
                    - IVA aplicado: {engine['iva_pct']}% → {iva_importe:.2f} €
                    - Total con IVA: {total_con_iva:.2f} €
                    - Tarifa aplicada: {engine['tarifa_aplicada'] or 'Ninguna'}
                    """)

                    payload = {
                        "pedidoid": pedidoid,
                        "productoid": (productoid or None),
                        "nombre_producto": (nombre_prod.strip() or None),
                        "cantidad": float(cantidad),
                        "precio_unitario": round(engine["unit_neto_sin_iva"], 2),
                        "descuento_pct": round(desc_total, 2),
                        "importe_total_linea": round(subtotal_sin_iva, 2),
                    }
                    supabase.table("pedido_detalle").insert(payload).execute()
                    st.success("✅ Línea añadida correctamente con descuentos e IVA aplicados.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error añadiendo línea: {e}")

        if lineas:
            with st.expander("🗑️ Eliminar línea existente", expanded=False):
                opciones = {f"{l['pedido_detalleid']} · {l['nombre_producto']}": l["pedido_detalleid"] for l in lineas}
                sel = st.selectbox("Selecciona línea a eliminar", list(opciones.keys()))
                if st.button("Eliminar línea seleccionada"):
                    try:
                        supabase.table("pedido_detalle").delete().eq("pedido_detalleid", opciones[sel]).execute()
                        st.success("🗑️ Línea eliminada.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error eliminando línea: {e}")
    else:
        st.info("🔒 No se pueden modificar líneas en pedidos bloqueados.")

    # ======================================================
    # 💰 Totales del pedido (motor de precios integrado)
    # ======================================================
    st.markdown("---")
    st.subheader("💰 Totales del pedido")

    try:
        tot = supabase.table("pedido_totales").select("*").eq("pedidoid", pedidoid).single().execute().data
    except Exception:
        tot = None

    colT1, colT2, colT3, colT4, colT5 = st.columns(5)
    if tot:
        colT1.metric("Base imponible", _money(tot.get("base_imponible")))
        colT2.metric("IVA", _money(tot.get("iva_importe")))
        colT3.metric("Total", _money(tot.get("total_importe")))
        colT4.metric("Gastos envío", _money(tot.get("gastos_envio")))
        colT5.metric("Env. sin cargo", "Sí" if tot.get("envio_sin_cargo") else "No")
    else:
        st.warning("⚠️ No hay totales calculados aún para este pedido.")

    # 🔄 Recalcular totales usando el motor de precios
    with st.expander("🔄 Recalcular totales", expanded=False):
        st.caption("Recalcula los importes con tarifas, descuentos e impuestos reales por producto.")

        use_iva = st.checkbox("Aplicar IVA (según producto o tarifa)", value=True)
        gastos = st.number_input(
            "Gastos de envío (€)",
            min_value=0.0,
            value=float(tot.get("gastos_envio", 0.0)) if tot else 0.0,
            step=0.01,
        )
        envio_sin_cargo = st.checkbox("Envío sin cargo",
                                      value=bool(tot.get("envio_sin_cargo")) if tot else False)

        if st.button("🔁 Recalcular ahora"):
            try:
                from modules.precio_engine import calcular_precio_linea

                res_lin = supabase.table("pedido_detalle").select(
                    "pedido_detalleid, productoid, cantidad, precio_unitario"
                ).eq("pedidoid", pedidoid).execute()
                lineas = res_lin.data or []

                if not lineas:
                    st.warning("No hay líneas registradas en este pedido.")
                    st.stop()

                base_total = 0.0
                iva_total = 0.0

                for l in lineas:
                    pid = l.get("productoid")
                    cant = float(l.get("cantidad") or 0)
                    precio_base = float(l.get("precio_unitario") or 0)

                    engine = calcular_precio_linea(
                        supabase,
                        clienteid=p.get("clienteid"),
                        productoid=pid,
                        precio_base_unit=precio_base,
                        cantidad=cant,
                    )

                    subtotal_sin_iva = engine["unit_neto_sin_iva"] * cant
                    base_total += subtotal_sin_iva

                    iva_pct = engine["iva_pct"] if use_iva else 0.0
                    iva_total += subtotal_sin_iva * (iva_pct / 100.0)

                total_importe = base_total + iva_total + gastos

                payload = {
                    "pedidoid": pedidoid,
                    "base_imponible": round(base_total, 2),
                    "iva_importe": round(iva_total, 2),
                    "total_importe": round(total_importe, 2),
                    "gastos_envio": round(gastos, 2),
                    "envio_sin_cargo": bool(envio_sin_cargo),
                }

                if tot:
                    supabase.table("pedido_totales").update(payload).eq("pedidoid", pedidoid).execute()
                else:
                    supabase.table("pedido_totales").insert(payload).execute()

                st.success("✅ Totales recalculados con motor de precios e IVA reales.")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error recalculando totales: {e}")

    # --------------------------------------------
    # Observaciones
    # --------------------------------------------
    st.markdown("---")
    st.subheader("🗒️ Observaciones")

    try:
        obs = supabase.table("pedido_observacion").select(
            "comentario, tipo, fecha, usuario"
        ).eq("pedidoid", pedidoid).order("fecha", desc=True).execute().data
        if not obs:
            st.info("No hay observaciones registradas.")
        else:
            for o in obs:
                st.markdown(f"**{o['tipo']}** — {o['fecha']} · {o.get('usuario','-')}\n\n> {o['comentario']}")
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar observaciones: {e}")

    with st.expander("➕ Añadir observación", expanded=False):
        tipo_obs = st.selectbox("Tipo", ["pedido", "factura"])
        comentario = st.text_area("Comentario")
        user = st.session_state.get("user_nombre") or st.session_state.get("user_email") or "sistema"
        if st.button("💾 Guardar observación"):
            try:
                supabase.table("pedido_observacion").insert({
                    "pedidoid": pedidoid,
                    "tipo": tipo_obs,
                    "comentario": comentario.strip(),
                    "usuario": user,
                    "fecha": datetime.now().isoformat(timespec="seconds"),
                }).execute()
                st.success("✅ Observación registrada.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error guardando observación: {e}")


# ======================================================
# ↩️ FUNCIÓN: CREAR DEVOLUCIÓN DESDE PEDIDO
# ======================================================
def _crear_devolucion_desde_pedido(supabase, pedidoid: int):
    """Duplica un pedido como 'Devolución' con cantidades negativas."""
    try:
        pedido = supabase.table("pedido").select("*").eq("pedidoid", pedidoid).single().execute().data
        if not pedido:
            st.error("No se encontró el pedido original.")
            return

        # Obtener tipo 'Devolución'
        tipo_dev = (
            supabase.table("pedido_tipo")
            .select("tipo_pedidoid")
            .eq("nombre", "Devolución")
            .single()
            .execute()
            .data
        )
        if not tipo_dev:
            st.error("⚠️ No se encontró el tipo de pedido 'Devolución'.")
            return

        # Insertar cabecera devolución
        payload_ped = {
            "numero": f"DEV-{pedido['numero']}",
            "clienteid": pedido.get("clienteid"),
            "tipo_pedidoid": tipo_dev["tipo_pedidoid"],
            "estado_pedidoid": pedido.get("estado_pedidoid"),
            "fecha_pedido": date.today().isoformat(),
            "referencia_cliente": pedido.get("referencia_cliente"),
            "facturar_individual": False,
            "pedido_origenid": pedidoid,
        }
        new_ped = supabase.table("pedido").insert(payload_ped).execute().data[0]
        new_id = new_ped["pedidoid"]

        # Duplicar líneas negativas
        lineas = supabase.table("pedido_detalle").select("*").eq("pedidoid", pedidoid).execute().data or []
        for l in lineas:
            supabase.table("pedido_detalle").insert({
                "pedidoid": new_id,
                "nombre_producto": l.get("nombre_producto"),
                "cantidad": -abs(l.get("cantidad", 0)),
                "precio_unitario": l.get("precio_unitario"),
                "descuento_pct": l.get("descuento_pct"),
                "importe_total_linea": -abs(l.get("importe_total_linea", 0)),
            }).execute()

        st.success(f"✅ Devolución creada correctamente (pedido #{new_id}).")
        st.rerun()

    except Exception as e:
        st.error(f"❌ Error creando devolución: {e}")
