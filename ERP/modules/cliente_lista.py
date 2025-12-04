import math
from datetime import date
from typing import Any, Optional, Dict, List

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html

from modules.orbe_theme import apply_orbe_theme
from modules.cliente_models import (
    load_estados_cliente,
    load_grupos,
    load_trabajadores,
    load_formas_pago,
    get_estado_label,
    get_grupo_label,
    get_trabajador_label,
    get_formapago_label,
)

from modules.cliente_direccion_form import render_direccion_form
from modules.cliente_facturacion_form import render_facturacion_form
from modules.cliente_observacion_form import render_observaciones_form
from modules.cliente_crm_form import render_crm_form
from modules.cliente_contacto_form import render_contacto_form


# =========================================================
# 🔧 Utils
# =========================================================
def _safe(v, d: str = "-"):
    return v if v not in (None, "", "null") else d


def _build_search_or(s: Optional[str], fields=("razon_social", "identificador")):
    s = (s or "").strip()
    if not s:
        return None
    return ",".join([f"{f}.ilike.%{s}%" for f in fields])


def _normalize_id(v: Any):
    """Normaliza IDs numéricos que puedan venir como float (1.0 -> 1)."""
    if isinstance(v, float):
        if v.is_integer():
            return int(v)
        return v
    return v


def render_cliente_lista(supabase):
    apply_orbe_theme()

    st.header("🏢 Gestión de clientes")
    st.caption("Consulta, filtra y accede a la ficha completa de tus clientes.")

    # Estado inicial seguro
    defaults = {
        "cli_page": 1,
        "cli_sort_field": "razon_social",
        "cli_sort_dir": "ASC",
        "cli_view": "Tarjetas",
        "show_cliente_modal": False,
        "cliente_modal_id": None,
        "confirm_delete": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # ===============================
    # 📌 FICHA DE CLIENTE – SI HAY
    # ===============================
    if st.session_state.get("show_cliente_modal") and st.session_state.get("cliente_modal_id"):
        try:
            st.session_state.pop("_dialog_state", None)
        except Exception:
            pass

        render_cliente_modal(supabase)
        st.markdown("## ")

    # Catálogos
    estados = load_estados_cliente(supabase)
    grupos = load_grupos(supabase)
    trabajadores = load_trabajadores(supabase)
    _ = load_formas_pago(supabase)

    # ===============================
    # 🔍 Buscador
    # ===============================
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input(
            "Buscar cliente",
            placeholder="Escribe nombre o identificador…",
            key="cli_q",
        )

        # ---------------------------------------------------------
        # FIX: evitar que la pantalla se cierre al escribir
        # ---------------------------------------------------------
        if "last_q" not in st.session_state:
            st.session_state["last_q"] = ""

        if q != st.session_state["last_q"]:
            st.session_state["cli_page"] = 1
            st.session_state["last_q"] = q
        # ---------------------------------------------------------

    with c2:
        st.metric("👥 Resultados (página)", st.session_state.get("cli_result_count", 0))

    st.markdown("---")

    # ===============================
    # 🎛 Filtros + Orden
    # ===============================
    with st.expander("⚙️ Filtros de búsqueda avanzada", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            estado_sel = st.selectbox("Estado", ["Todos"] + list(estados.keys()), key="cli_estado")
        with c2:
            grupo_sel = st.selectbox("Grupo", ["Todos"] + list(grupos.keys()), key="cli_grupo")

        c3, c4 = st.columns(2)
        with c3:
            trab_sel = st.selectbox(
                "Comercial asignado",
                ["Todos"] + list(trabajadores.keys()),
                key="cli_trab",
            )
        with c4:
            view = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, key="cli_view")

        st.markdown("### ↕️ Ordenar")

        col_order1, col_order2 = st.columns(2)
        with col_order1:
            sort_field = st.selectbox(
                "Campo",
                ["razon_social", "identificador", "estadoid", "grupoid"],
                index=["razon_social", "identificador", "estadoid", "grupoid"].index(
                    st.session_state.get("cli_sort_field", "razon_social")
                ),
            )
            st.session_state["cli_sort_field"] = sort_field

        with col_order2:
            sort_dir = st.radio(
                "Dirección",
                ["ASC", "DESC"],
                index=0 if st.session_state.get("cli_sort_dir", "ASC") == "ASC" else 1,
                horizontal=True,
            )
            st.session_state["cli_sort_dir"] = sort_dir

    # ===============================
    # 📥 Carga + filtros
    # ===============================
    try:
        base = (
            supabase.table("cliente")
            .select(
                "clienteid, razon_social, identificador, estadoid, categoriaid, "
                "grupoid, trabajadorid, formapagoid"
            )
            .eq("tipo_cliente", "cliente")
        )

        count_q = (
            supabase.table("cliente")
            .select("clienteid", count="exact")
            .eq("tipo_cliente", "cliente")
        )

        or_filter = _build_search_or(q)
        if or_filter:
            base = base.or_(or_filter)
            count_q = count_q.or_(or_filter)

        if estado_sel != "Todos" and estado_sel in estados:
            eid = estados[estado_sel]
            base = base.eq("estadoid", eid)
            count_q = count_q.eq("estadoid", eid)

        if grupo_sel != "Todos" and grupo_sel in grupos:
            gid = grupos[grupo_sel]
            base = base.eq("grupoid", gid)
            count_q = count_q.eq("grupoid", gid)

        if trab_sel != "Todos" and trab_sel in trabajadores:
            tid = trabajadores[trab_sel]
            base = base.eq("trabajadorid", tid)
            count_q = count_q.eq("trabajadorid", tid)

        count_res = count_q.execute()
        total_clientes = count_res.count or 0

        page_size = 30
        page = st.session_state["cli_page"]
        total_paginas = max(1, math.ceil(total_clientes / page_size))
        if page > total_paginas:
            page = total_paginas
            st.session_state["cli_page"] = page

        start = (page - 1) * page_size
        end = start + page_size - 1

        base = base.order(
            st.session_state["cli_sort_field"],
            desc=(st.session_state["cli_sort_dir"] == "DESC"),
        )

        data = base.range(start, end).execute()
        clientes = data.data or []
        st.session_state["cli_result_count"] = len(clientes)

    except Exception as e:
        st.error(f"❌ Error cargando clientes: {e}")
        return

    st.markdown("---")

    if not clientes:
        st.info("📭 No se encontraron clientes con esos filtros.")
        return

    # ===============================
    # 🔄 Carga de presupuestos
    # ===============================
    ids_clientes = [c["clienteid"] for c in clientes]
    presupuestos: Dict[int, Dict[str, Any]] = {}
    if ids_clientes:
        try:
            pres_rows = (
                supabase.table("presupuesto")
                .select("clienteid, estado_presupuestoid, fecha_presupuesto")
                .in_("clienteid", ids_clientes)
                .order("fecha_presupuesto", desc=True)
                .execute()
                .data
                or []
            )
            for row in pres_rows:
                cid = row["clienteid"]
                if cid not in presupuestos:
                    presupuestos[cid] = row
        except Exception:
            presupuestos = {}

    # ===============================
    # 👁️ Vista TABLA o TARJETAS
    # ===============================
    if view == "Tabla":
        rows: List[Dict[str, Any]] = []
        for c in clientes:
            estado_lbl = get_estado_label(c.get("estadoid"), supabase) or "-"
            grupo_lbl = get_grupo_label(c.get("grupoid"), supabase) or "-"
            if grupo_lbl == "-":
                grupo_lbl = "Sin grupo"

            trab_lbl = get_trabajador_label(c.get("trabajadorid"), supabase) or "-"
            if trab_lbl == "-":
                trab_lbl = "Sin comercial"

            fid = _normalize_id(c.get("formapagoid"))
            forma = get_formapago_label(fid, supabase) if fid else "-"

            rows.append(
                {
                    "ID": c.get("clienteid"),
                    "Razón social": c.get("razon_social"),
                    "Identificador": c.get("identificador"),
                    "Estado": estado_lbl,
                    "Grupo": grupo_lbl,
                    "Comercial": trab_lbl,
                    "Forma de pago": forma,
                }
            )

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

    else:
        cols = st.columns(3)
        for i, c in enumerate(clientes):
            c["presupuesto_info"] = presupuestos.get(c["clienteid"])
            with cols[i % 3]:
                _render_card(c, supabase)

    # ===============================
    # 🔢 Paginación
    # ===============================
    st.markdown("---")
    pag1, pag2, pag3 = st.columns(3)

    with pag1:
        if st.button("⬅️ Anterior", disabled=page <= 1):
            st.session_state["cli_page"] = page - 1
            st.rerun()

    with pag2:
        st.write(f"Página {page} / {total_paginas} · Total clientes: {total_clientes}")

    with pag3:
        if st.button("Siguiente ➡️", disabled=page >= total_paginas):
            st.session_state["cli_page"] = page + 1
            st.rerun()

# =========================================================
# 🧾 Tarjeta de cliente
# =========================================================
def _render_card(c: Dict[str, Any], supabase):
    apply_orbe_theme()

    razon = _safe(c.get("razon_social"))
    ident = _safe(c.get("identificador"))

    estado = get_estado_label(c.get("estadoid"), supabase) or "-"
    grupo = get_grupo_label(c.get("grupoid"), supabase) or "-"
    if grupo == "-":
        grupo = "Sin grupo"

    trab = get_trabajador_label(c.get("trabajadorid"), supabase) or "-"
    if trab == "-":
        trab = "Sin comercial"

    fid = _normalize_id(c.get("formapagoid"))
    forma_pago = get_formapago_label(fid, supabase) if fid else "-"

    pres = c.get("presupuesto_info")
    pres_estado = "Sin presupuesto"
    pres_fecha = None

    if pres:
        estado_map = {1: "Pendiente", 2: "Aceptado", 3: "Rechazado"}
        pres_estado = estado_map.get(pres.get("estado_presupuestoid"), "Sin presupuesto")
        pres_fecha = pres.get("fecha_presupuesto")

    color_estado = {
        "Activo": "#10b981",
        "Potencial": "#3b82f6",
        "Suspendido": "#dc2626",
    }.get(estado, "#6b7280")

    color_pres = {
        "Aceptado": "#16a34a",
        "Pendiente": "#f59e0b",
        "Rechazado": "#dc2626",
        "Sin presupuesto": "#6b7280",
    }.get(pres_estado, "#6b7280")

    fecha_html = (
        f"<div style='color:#4b5563;font-size:0.8rem;'>🗓️ {pres_fecha}</div>"
        if pres_fecha
        else ""
    )

    html = f"""
    <div style="border:1px solid #e5e7eb;border-radius:12px;
                background:#f9fafb;padding:14px;margin-bottom:14px;
                box-shadow:0 1px 3px rgba(0,0,0,0.08);">

        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:1.05rem;font-weight:600;
                            white-space:nowrap;overflow:hidden;
                            text-overflow:ellipsis;max-width:230px;">
                    🏢 {razon}
                </div>
                <div style="color:#6b7280;font-size:0.9rem;
                            white-space:nowrap;overflow:hidden;
                            text-overflow:ellipsis;max-width:230px;">
                    {ident}
                </div>
            </div>
            <div style="color:{color_estado};font-weight:600;
                        white-space:nowrap;margin-left:8px;">
                {estado}
            </div>
        </div>

        <div style="margin-top:8px;font-size:0.9rem;line-height:1.45;">
            👥 <b>Grupo:</b> {grupo}<br>
            💳 <b>Forma de pago:</b> {forma_pago}<br>
            🧑 <b>Comercial:</b> {trab}<br>
            <span style="color:{color_pres};font-weight:600;">📦 {pres_estado}</span>
            {fecha_html}
        </div>
    </div>
    """

    st_html(html, height=220)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📄 Ficha", key=f"ficha_cli_{c['clienteid']}", use_container_width=True):
            st.session_state.update(
                {
                    "cliente_modal_id": c["clienteid"],
                    "show_cliente_modal": True,
                    "confirm_delete": False,
                }
            )
            st.rerun()

    with col2:
        if st.button("📨 Presupuesto", key=f"pres_cli_{c['clienteid']}", use_container_width=True):
            try:
                supabase.table("presupuesto").insert(
                    {
                        "numero": f"PRES-{date.today().year}-{c['clienteid']}",
                        "clienteid": c["clienteid"],
                        "estado_presupuestoid": 1,
                        "fecha_presupuesto": date.today().isoformat(),
                        "editable": True,
                    }
                ).execute()
                st.toast("📨 Presupuesto creado.", icon="📨")
            except Exception as e:
                st.error(f"❌ Error creando presupuesto: {e}")

    with col3:
        if st.button("🛑 Dar de baja", key=f"elim_cli_{c['clienteid']}", use_container_width=True):
            st.session_state["cliente_modal_id"] = c["clienteid"]
            st.session_state["confirm_delete"] = True
            st.session_state["show_cliente_modal"] = True
            st.rerun()

def render_cliente_modal(supabase):
    """
    Ficha completa del cliente, integrada en la parte superior de la página,
    con tabs para General, Direcciones, Contactos, Observaciones, CRM,
    Presupuestos y Pedidos.
    """
    from modules.cliente_direccion_form import render_direccion_form
    from modules.cliente_facturacion_form import render_facturacion_form
    from modules.cliente_contacto_form import render_contacto_form
    from modules.cliente_observacion_form import render_observaciones_form
    from modules.cliente_crm_form import render_crm_form

    if not st.session_state.get("show_cliente_modal"):
        return

    clienteid = st.session_state.get("cliente_modal_id")
    if not clienteid:
        return

    try:
        cli = (
            supabase.table("cliente")
            .select("*")
            .eq("clienteid", int(clienteid))
            .single()
            .execute()
            .data
        )
    except Exception as e:
        st.error(f"❌ Error cargando la ficha del cliente: {e}")
        return

    # ============================
    # 🔎 Datos base del cliente
    # ============================
    razon = cli.get("razon_social") or "(Sin nombre)"
    identificador = cli.get("identificador") or "-"
    tipo_cliente = cli.get("tipo_cliente") or "-"
    cuenta_comision = cli.get("cuenta_comision", 0)
    estado_presupuesto_txt = cli.get("estado_presupuesto") or "pendiente"
    perfil_completo = bool(cli.get("perfil_completo"))

    estado = get_estado_label(cli.get("estadoid"), supabase)
    if not estado or estado == "-":
        estado = "Desconocido"

    grupo = get_grupo_label(cli.get("grupoid"), supabase) or "Sin grupo"
    comercial = get_trabajador_label(cli.get("trabajadorid"), supabase) or "Sin comercial"
    forma_pago = get_formapago_label(cli.get("formapagoid"), supabase) or "-"

    # ============================
    # 📊 KPIs rápidos
    # ============================
    presupuestos_activos = None
    pedidos_activos = None

    try:
        pres_act = (
            supabase.table("presupuesto")
            .select("presupuestoid", count="exact")
            .eq("clienteid", int(clienteid))
            .eq("estado_presupuestoid", 1)  # 1 = Pendiente / activo
            .execute()
        )
        presupuestos_activos = pres_act.count or 0
    except Exception:
        presupuestos_activos = None

    try:
        ped_act = (
            supabase.table("pedido")
            .select("pedidoid", count="exact")
            .eq("clienteid", int(clienteid))
            .execute()
        )
        pedidos_activos = ped_act.count or 0
    except Exception:
        pedidos_activos = None

    # ============================
    # 🧱 CUADRO PRINCIPAL
    # ============================
    st.markdown("## ")  # pequeño espacio visual

    # Botón Cerrar ficha
    col_close, col_title = st.columns([1, 4])
    with col_close:
        if st.button("⬅️ Cerrar ficha", key="close_cliente_modal", use_container_width=True):
            st.session_state["show_cliente_modal"] = False
            st.session_state["cliente_modal_id"] = None
            st.session_state["confirm_delete"] = False
            st.rerun()

    with col_title:
        st.markdown(
            f"""
            <div style='padding:14px;border-radius:12px;
                        background:#f9fafb;border:1px solid #e5e7eb;'>
                <h3 style='margin:0;'>🏢 {razon}</h3>
                <p style='margin:4px 0 0 0;color:#4b5563;font-size:0.9rem;'>
                    <b>ID interno:</b> {clienteid} · 
                    <b>Identificador:</b> {identificador} · 
                    <b>Tipo:</b> {tipo_cliente}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Fila de resumen
    st.markdown(
        f"""
        <div style='margin-top:8px;margin-bottom:8px;
                    padding:12px 14px;border-radius:12px;
                    background:#ffffff;border:1px solid #e5e7eb;'>
            <div style='display:flex;flex-wrap:wrap;gap:18px;font-size:0.9rem;color:#374151;'>
                <div><b>Estado:</b> {estado}</div>
                <div><b>Grupo:</b> {grupo}</div>
                <div><b>Comercial:</b> {comercial}</div>
                <div><b>Forma de pago:</b> {forma_pago}</div>
                <div><b>Cuenta comisión:</b> {cuenta_comision}</div>
                <div><b>Estado presupuesto:</b> {estado_presupuesto_txt}</div>
                <div><b>Perfil completo:</b> {"✅ Sí" if perfil_completo else "⚪ Pendiente"}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPIs: Presupuestos activos / Pedidos activos
    k1, k2 = st.columns(2)
    with k1:
        if presupuestos_activos is not None:
            st.metric("📨 Presupuestos activos", presupuestos_activos)
        else:
            st.metric("📨 Presupuestos activos", "N/D")
    with k2:
        if pedidos_activos is not None:
            st.metric("📦 Pedidos activos", pedidos_activos)
        else:
            st.metric("📦 Pedidos activos", "N/D")

    st.markdown("---")

    # ======================================================
    # 🧷 TABS PRINCIPALES
    # ======================================================
    (
        tab_general,
        tab_dir,
        tab_contactos,
        tab_obs,
        tab_crm,
        tab_pres,
        tab_ped,
    ) = st.tabs([
        "📌 General",
        "🏠 Direcciones",
        "👥 Contactos",
        "🗒️ Observaciones",
        "💬 CRM",
        "🧾 Presupuestos",
        "📦 Pedidos",
    ])

    # ============================
    # 📌 TAB · GENERAL
    # ============================
    with tab_general:
        st.markdown("### 📌 Resumen general del cliente")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### 🧾 Identificación")
            st.write(f"**Razón social:** {razon}")
            st.write(f"**Identificador:** {identificador}")
            st.write(f"**Tipo de cliente:** {tipo_cliente}")
            st.write(f"**Estado:** {estado}")
            st.write(f"**Grupo:** {grupo}")

        with col_g2:
            st.markdown("#### 👥 Comercial & condiciones")
            st.write(f"**Comercial asignado:** {comercial}")
            st.write(f"**Forma de pago:** {forma_pago}")
            st.write(f"**Cuenta comisión:** {cuenta_comision}")
            st.write(f"**Estado presupuesto:** {estado_presupuesto_txt}")
            st.write(f"**Perfil completo:** {'✅ Sí' if perfil_completo else '⚪ Pendiente'}")

        # Observaciones breves (campo observaciones en tabla cliente, si existe)
        obs_breve = cli.get("observaciones")
        st.markdown("---")
        st.markdown("#### 📝 Observaciones breves")
        if obs_breve:
            st.info(obs_breve)
        else:
            st.caption("No hay observaciones breves guardadas en la ficha base del cliente.")

        st.markdown("---")
        st.markdown("#### ⚙️ Acciones rápidas")

        ac1, ac2, ac3 = st.columns(3)
        with ac1:
            if st.button("📨 Crear presupuesto", key=f"btn_pres_desde_general_{clienteid}", use_container_width=True):
                try:
                    supabase.table("presupuesto").insert({
                        "numero": f"PRES-{date.today().year}-{clienteid}",
                        "clienteid": int(clienteid),
                        "trabajadorid": st.session_state.get("trabajadorid", None),
                        "estado_presupuestoid": 1,
                        "fecha_presupuesto": date.today().isoformat(),
                        "observaciones": "Presupuesto creado desde ficha general del cliente.",
                        "editable": True,
                        "facturar_individual": False,
                    }).execute()
                    st.toast("📨 Presupuesto creado correctamente.", icon="📨")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creando presupuesto: {e}")

        with ac2:
            st.button("📦 (Futuro) Crear pedido", disabled=True, use_container_width=True)

        with ac3:
            if st.button("🛑 Dar de baja cliente", key=f"btn_baja_{clienteid}", use_container_width=True):
                try:
                    supabase.table("cliente").delete().eq("clienteid", int(clienteid)).execute()
                    st.toast("🗑 Cliente dado de baja correctamente.", icon="🗑")
                    st.session_state["show_cliente_modal"] = False
                    st.session_state["cliente_modal_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ No se pudo dar de baja el cliente: {e}")

    # ============================
    # 🏠 TAB · DIRECCIONES
    # ============================
    with tab_dir:
        render_direccion_form(supabase, int(clienteid), modo="cliente")

    # ============================
    # 👥 TAB · CONTACTOS
    # ============================
    with tab_contactos:
        render_contacto_form(supabase, int(clienteid))

    # ============================
    # 🗒️ TAB · OBSERVACIONES
    # ============================
    with tab_obs:
        render_observaciones_form(supabase, int(clienteid))

    # ============================
    # 💬 TAB · CRM
    # ============================
    with tab_crm:
        render_crm_form(supabase, int(clienteid))

    # ============================
    # 🧾 TAB · PRESUPUESTOS
    # ============================
    with tab_pres:
        st.markdown("### 🧾 Presupuestos del cliente")

        try:
            presupuestos = (
                supabase.table("presupuesto")
                .select("presupuestoid, numero, fecha_presupuesto, total_estimada, estado_presupuestoid")
                .eq("clienteid", int(clienteid))
                .order("fecha_presupuesto", desc=True)
                .execute()
                .data
                or []
            )
        except Exception as e:
            st.error(f"❌ Error cargando presupuestos: {e}")
            presupuestos = []

        if not presupuestos:
            st.info("📭 Este cliente no tiene presupuestos registrados aún.")
        else:
            estado_map = {1: "Pendiente", 2: "Aceptado", 3: "Rechazado"}
            color_map = {
                "Pendiente": "#f59e0b",
                "Aceptado": "#16a34a",
                "Rechazado": "#dc2626",
            }

            for p in presupuestos:
                est = estado_map.get(p.get("estado_presupuestoid"), "Desconocido")
                color = color_map.get(est, "#6b7280")

                st.markdown(
                    f"""
                    <div style='border:1px solid #e5e7eb;border-left:5px solid {color};
                                background:#f9fafb;padding:10px 12px;margin:6px 0;border-radius:8px;'>
                        <b>{p.get('numero','(Sin número)')}</b> — 🗓️ {p.get('fecha_presupuesto','-')}<br>
                        💰 <b>{p.get('total_estimada','-')} €</b><br>
                        <span style='color:{color};font-weight:600;'>{est}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ============================
    # 📦 TAB · PEDIDOS
    # ============================
    with tab_ped:
        st.markdown("### 📦 Pedidos del cliente")

        try:
            pedidos = (
                supabase.table("pedido")
                .select("*")
                .eq("clienteid", int(clienteid))
                .order("fecha_pedido", desc=True)
                .execute()
                .data
                or []
            )
        except Exception as e:
            st.error(f"❌ Error cargando pedidos: {e}")
            pedidos = []

        if not pedidos:
            st.info("📭 Este cliente todavía no tiene pedidos registrados.")
        else:
            for ped in pedidos:
                numero = ped.get("numero") or f"PED-{ped.get('pedidoid','?')}"
                fecha = ped.get("fecha_pedido", "-")
                estado_pedidoid = ped.get("estado_pedidoid", "-")
                total = ped.get("total_bruto") or ped.get("total_neto") or ped.get("total") or "-"

                st.markdown(
                    f"""
                    <div style='border:1px solid #e5e7eb;border-left:5px solid #3b82f6;
                                background:#f9fafb;padding:10px 12px;margin:6px 0;border-radius:8px;'>
                        <b>{numero}</b> — 🗓️ {fecha}<br>
                        💰 <b>{total} €</b><br>
                        <span style='color:#3b82f6;font-weight:600;'>Estado pedido ID: {estado_pedidoid}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
