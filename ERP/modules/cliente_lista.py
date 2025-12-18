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
from modules.cliente_contacto_form import render_contacto_form
from modules.cliente_observacion_form import render_observaciones_form
from modules.cliente_crm_form import render_crm_form


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
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


# =========================================================
# 📄 LISTADO DE CLIENTES
# =========================================================
def render_cliente_lista(supabase):
    apply_orbe_theme()

    st.header("🏢 Gestión de clientes")
    st.caption("Consulta, filtra y accede a la ficha completa de tus clientes.")

    # ---------------------------
    # Estado inicial
    # ---------------------------
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

    # ---------------------------
    # Ficha cliente
    # ---------------------------
    if st.session_state.get("show_cliente_modal") and st.session_state.get("cliente_modal_id"):
        render_cliente_modal(supabase)
        st.markdown("---")

    # ---------------------------
    # Catálogos
    # ---------------------------
    estados = load_estados_cliente(supabase)
    grupos = load_grupos(supabase)
    trabajadores = load_trabajadores(supabase)
    load_formas_pago(supabase)

    # =================================================
    # 🔍 Buscador
    # =================================================
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input(
            "Buscar cliente",
            placeholder="Razón social o identificador…",
            key="cli_q",
        )

        if "last_q" not in st.session_state:
            st.session_state["last_q"] = ""

        if q != st.session_state["last_q"]:
            st.session_state["cli_page"] = 1
            st.session_state["last_q"] = q

    with c2:
        st.metric("Resultados", st.session_state.get("cli_result_count", 0))

    st.markdown("---")

    # =================================================
    # 🎛 Filtros
    # =================================================
    with st.expander("⚙️ Filtros avanzados", expanded=False):
        f1, f2 = st.columns(2)
        with f1:
            estado_sel = st.selectbox("Estado", ["Todos"] + list(estados.keys()), key="cli_estado")
        with f2:
            grupo_sel = st.selectbox("Grupo", ["Todos"] + list(grupos.keys()), key="cli_grupo")

        f3, f4 = st.columns(2)
        with f3:
            trab_sel = st.selectbox(
                "Comercial asignado",
                ["Todos"] + list(trabajadores.keys()),
                key="cli_trab",
            )
        with f4:
            view = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, key="cli_view")

        st.markdown("### ↕️ Ordenar")
        o1, o2 = st.columns(2)
        with o1:
            st.session_state["cli_sort_field"] = st.selectbox(
                "Campo",
                ["razon_social", "identificador", "estadoid", "grupoid"],
            )
        with o2:
            st.session_state["cli_sort_dir"] = st.radio(
                "Dirección",
                ["ASC", "DESC"],
                horizontal=True,
            )

    # =================================================
    # 📥 Carga de clientes
    # =================================================
    try:
        base = (
            supabase.table("cliente")
            .select(
                "clienteid, razon_social, identificador, estadoid, "
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

        if estado_sel != "Todos":
            base = base.eq("estadoid", estados[estado_sel])
            count_q = count_q.eq("estadoid", estados[estado_sel])

        if grupo_sel != "Todos":
            base = base.eq("grupoid", grupos[grupo_sel])
            count_q = count_q.eq("grupoid", grupos[grupo_sel])

        if trab_sel != "Todos":
            base = base.eq("trabajadorid", trabajadores[trab_sel])
            count_q = count_q.eq("trabajadorid", trabajadores[trab_sel])

        total_clientes = count_q.execute().count or 0

        page_size = 30
        page = st.session_state["cli_page"]
        total_paginas = max(1, math.ceil(total_clientes / page_size))

        start = (page - 1) * page_size
        end = start + page_size - 1

        clientes = (
            base.order(
                st.session_state["cli_sort_field"],
                desc=st.session_state["cli_sort_dir"] == "DESC",
            )
            .range(start, end)
            .execute()
            .data
            or []
        )

        st.session_state["cli_result_count"] = len(clientes)

    except Exception as e:
        st.error(f"❌ Error cargando clientes: {e}")
        return

    if not clientes:
        st.info("📭 No se encontraron clientes.")
        return

    # =================================================
    # 🔄 Presupuesto más reciente
    # =================================================
    presupuestos: Dict[int, Dict[str, Any]] = {}
    ids = [c["clienteid"] for c in clientes]

    if ids:
        try:
            rows = (
                supabase.table("presupuesto")
                .select("clienteid, estado_presupuestoid, fecha_presupuesto")
                .in_("clienteid", ids)
                .order("fecha_presupuesto", desc=True)
                .execute()
                .data
                or []
            )
            for r in rows:
                if r["clienteid"] not in presupuestos:
                    presupuestos[r["clienteid"]] = r
        except Exception:
            pass

    # =================================================
    # 📊 TABLA / TARJETAS
    # =================================================
    if view == "Tabla":
        ALL_COLS = [
            "ID cliente",
            "Razón social",
            "Identificador",
            "Estado",
            "Grupo",
            "Comercial",
            "Forma de pago",
        ]

        st.session_state.setdefault(
            "cli_table_cols",
            ["ID cliente", "Razón social", "Identificador", "Estado"],
        )

        cols_sel = st.multiselect(
            "Columnas visibles",
            options=ALL_COLS,
            default=st.session_state["cli_table_cols"],
            key="cli_table_cols",
        )

        rows = []
        for c in clientes:
            rows.append(
                {
                    "ID cliente": c["clienteid"],
                    "Razón social": c["razon_social"],
                    "Identificador": c["identificador"],
                    "Estado": get_estado_label(c["estadoid"], supabase),
                    "Grupo": get_grupo_label(c["grupoid"], supabase),
                    "Comercial": get_trabajador_label(c["trabajadorid"], supabase),
                    "Forma de pago": get_formapago_label(
                        _normalize_id(c["formapagoid"]), supabase
                    ),
                }
            )

        df = pd.DataFrame(rows)
        st.dataframe(df[cols_sel], use_container_width=True, hide_index=True)

    else:
        cols = st.columns(3)
        for i, c in enumerate(clientes):
            c["presupuesto_info"] = presupuestos.get(c["clienteid"])
            with cols[i % 3]:
                _render_card(c, supabase)

    # =================================================
    # 🔢 Paginación
    # =================================================
    st.markdown("---")
    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button("⬅️ Anterior", disabled=page <= 1):
            st.session_state["cli_page"] = page - 1
            st.rerun()
    with p2:
        st.write(f"Página {page} / {total_paginas} · Total: {total_clientes}")
    with p3:
        if st.button("Siguiente ➡️", disabled=page >= total_paginas):
            st.session_state["cli_page"] = page + 1
            st.rerun()
# =========================================================
# 🧾 Tarjeta de cliente (CARD)
# =========================================================
def _render_card(c: Dict[str, Any], supabase):
    apply_orbe_theme()

    razon = _safe(c.get("razon_social"))
    ident = _safe(c.get("identificador"))

    estado = get_estado_label(c.get("estadoid"), supabase) or "-"
    grupo = get_grupo_label(c.get("grupoid"), supabase) or "Sin grupo"
    trab = get_trabajador_label(c.get("trabajadorid"), supabase) or "Sin comercial"

    forma_pago = get_formapago_label(
        _normalize_id(c.get("formapagoid")), supabase
    ) or "-"

    pres = c.get("presupuesto_info")
    pres_estado = "Sin presupuesto"
    pres_fecha = None

    if pres:
        pres_estado = {1: "Pendiente", 2: "Aceptado", 3: "Rechazado"}.get(
            pres.get("estado_presupuestoid"), "Sin presupuesto"
        )
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
        f"<div style='font-size:0.8rem;color:#475569;'>🗓️ {pres_fecha}</div>"
        if pres_fecha
        else ""
    )

    st_html(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;
                    background:#f9fafb;padding:14px;margin-bottom:12px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);">

            <div style="display:flex;justify-content:space-between;">
                <div>
                    <div style="font-size:1.05rem;font-weight:600;">
                        🏢 {razon}
                    </div>
                    <div style="font-size:0.9rem;color:#6b7280;">
                        {ident}
                    </div>
                </div>
                <div style="color:{color_estado};font-weight:600;">
                    {estado}
                </div>
            </div>

            <div style="margin-top:8px;font-size:0.9rem;">
                👥 <b>Grupo:</b> {grupo}<br>
                🧑 <b>Comercial:</b> {trab}<br>
                💳 <b>Forma pago:</b> {forma_pago}<br>
                <span style="color:{color_pres};font-weight:600;">
                    📦 {pres_estado}
                </span>
                {fecha_html}
            </div>
        </div>
        """,
        height=210,
    )

    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("📄 Ficha", key=f"cli_ficha_{c['clienteid']}", use_container_width=True):
            st.session_state.update(
                {
                    "cliente_modal_id": c["clienteid"],
                    "show_cliente_modal": True,
                    "confirm_delete": False,
                }
            )
            st.rerun()

    with b2:
        if st.button("📨 Presupuesto", key=f"cli_pres_{c['clienteid']}", use_container_width=True):
            supabase.table("presupuesto").insert(
                {
                    "numero": f"PRES-{date.today().year}-{c['clienteid']}",
                    "clienteid": c["clienteid"],
                    "estado_presupuestoid": 1,
                    "fecha_presupuesto": date.today().isoformat(),
                    "editable": True,
                }
            ).execute()
            st.toast("📨 Presupuesto creado", icon="📨")

    with b3:
        if st.button("🛑 Baja", key=f"cli_del_{c['clienteid']}", use_container_width=True):
            st.session_state.update(
                {
                    "cliente_modal_id": c["clienteid"],
                    "show_cliente_modal": True,
                    "confirm_delete": True,
                }
            )
            st.rerun()


# =========================================================
# 📄 FICHA COMPLETA DEL CLIENTE
# =========================================================
def render_cliente_modal(supabase):
    clienteid = st.session_state.get("cliente_modal_id")
    if not clienteid:
        return

    cli = (
        supabase.table("cliente")
        .select("*")
        .eq("clienteid", int(clienteid))
        .single()
        .execute()
        .data
    )
    # Estado paginación facturas
    st.session_state.setdefault("fact_page", 1)
    st.session_state.setdefault("fact_page_size", 15)

    razon = cli.get("razon_social", "(Sin nombre)")
    identificador = cli.get("identificador", "-")
    tipo_cliente = cli.get("tipo_cliente", "-")

    estado = get_estado_label(cli.get("estadoid"), supabase)
    grupo = get_grupo_label(cli.get("grupoid"), supabase)
    comercial = get_trabajador_label(cli.get("trabajadorid"), supabase)
    forma_pago = get_formapago_label(cli.get("formapagoid"), supabase)

    # ---------------------------
    # Cabecera
    # ---------------------------
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("⬅️ Volver", use_container_width=True):
            st.session_state["show_cliente_modal"] = False
            st.session_state["cliente_modal_id"] = None
            st.rerun()

    with c2:
        st_html(
            f"""
            <div style="padding:14px;border-radius:12px;
                        background:#f9fafb;border:1px solid #e5e7eb;">
                <h3>🏢 {razon}</h3>
                <p style="color:#475569;font-size:0.9rem;">
                    ID: {clienteid} · {identificador} · {tipo_cliente}
                </p>
            </div>
            """,
            height=120,
        )

    # ---------------------------
    # Tabs
    # ---------------------------
    (
        tab_general,
        tab_dir,
        tab_contactos,
        tab_obs,
        tab_crm,
        tab_pres,
        tab_ped,
        tab_fac,
    ) = st.tabs([
        "📌 General",
        "🏠 Direcciones",
        "👥 Contactos",
        "🗒️ Observaciones",
        "💬 CRM",
        "🧾 Presupuestos",
        "📦 Pedidos",
        "🧾 Facturas",
    ])


    # ---------------------------
    # GENERAL
    # ---------------------------
    with tab_general:
        st.write(f"**Estado:** {estado}")
        st.write(f"**Grupo:** {grupo}")
        st.write(f"**Comercial:** {comercial}")
        st.write(f"**Forma de pago:** {forma_pago}")

    # ---------------------------
    # DIRECCIONES
    # ---------------------------
    with tab_dir:
        render_direccion_form(supabase, clienteid, modo="cliente")

    # ---------------------------
    # CONTACTOS
    # ---------------------------
    with tab_contactos:
        render_contacto_form(supabase, clienteid)

    # ---------------------------
    # OBSERVACIONES
    # ---------------------------
    with tab_obs:
        render_observaciones_form(supabase, clienteid)

    # ---------------------------
    # CRM
    # ---------------------------
    with tab_crm:
        render_crm_form(supabase, clienteid)

    # ---------------------------
    # PRESUPUESTOS
    # ---------------------------
    with tab_pres:
        presupuestos = (
            supabase.table("presupuesto")
            .select("*")
            .eq("clienteid", clienteid)
            .order("fecha_presupuesto", desc=True)
            .execute()
            .data
            or []
        )

        if not presupuestos:
            st.info("📭 No hay presupuestos")
        else:
            for p in presupuestos:
                st_html(
                    f"""
                    <div style="border-left:5px solid #16a34a;
                                background:#f9fafb;padding:10px;margin:6px 0;">
                        <b>{p.get("numero")}</b> — {p.get("fecha_presupuesto")}  
                        💰 {p.get("total_estimada","-")} €
                    </div>
                    """,
                    height=90,
                )

    # ============================
    # 🧾 TAB · FACTURAS (PAGINADAS)
    # ============================
    with tab_fac:
        page_size = st.session_state["fact_page_size"]
        page = st.session_state["fact_page"]

        try:
            # 🔢 Total facturas (para paginación)
            count_res = (
                supabase.table("factura")
                .select("facturaid", count="exact")
                .eq("clienteid", int(clienteid))
                .execute()
            )
            total_facturas = count_res.count or 0

            total_pages = max(1, math.ceil(total_facturas / page_size))
            if page > total_pages:
                page = total_pages
                st.session_state["fact_page"] = page

            start = (page - 1) * page_size
            end = start + page_size - 1

            # 📥 Carga paginada
            facturas = (
                supabase.table("factura")
                .select(
                    "facturaid, factura_serie, factura_numero, "
                    "fecha_emision, fecha_vencimiento, "
                    "factura_estado, forma_pago, "
                    "base_imponible, impuestos, total_calculado"
                )
                .eq("clienteid", int(clienteid))
                .order("fecha_emision", desc=True)
                .range(start, end)
                .execute()
                .data
                or []
            )

        except Exception as e:
            st.error(f"❌ Error cargando facturas: {e}")
            facturas = []
            total_facturas = 0
            total_pages = 1

        if not facturas:
            st.info("📭 Este cliente no tiene facturas registradas.")
        else:
            for f in facturas:
                estado = f.get("factura_estado", "-")
                color_estado = {
                    "Exportada": "#16a34a",
                    "Borrador": "#f59e0b",
                    "Anulada": "#dc2626",
                }.get(estado, "#6b7280")

                numero = f"{f.get('factura_serie','')}-{f.get('factura_numero','')}"

                st_html(
                    f"""
                    <div style="
                        border:1px solid #e5e7eb;
                        border-left:5px solid {color_estado};
                        background:#f9fafb;
                        padding:12px;
                        margin:8px 0;
                        border-radius:8px;
                    ">
                        <b>🧾 {numero}</b><br>
                        🗓️ <b>Emisión:</b> {f.get('fecha_emision','-')}<br>
                        ⏳ <b>Vencimiento:</b> {f.get('fecha_vencimiento','-')}<br>
                        💳 <b>Forma de pago:</b> {f.get('forma_pago','-')}<br>
                        💰 <b>Base:</b> {f.get('base_imponible','-')} €<br>
                        🧮 <b>Impuestos:</b> {f.get('impuestos','-')} €<br>
                        <span style="font-weight:700;">
                            💶 Total: {f.get('total_calculado','-')} €
                        </span><br>
                        <span style="color:{color_estado};font-weight:600;">
                            Estado: {estado}
                        </span>
                    </div>
                    """,
                    height=190,
                )

        # 🔢 Controles de paginación
        st.markdown("---")
        p1, p2, p3 = st.columns(3)

        with p1:
            if st.button("⬅️ Anterior", disabled=page <= 1, key="fact_prev"):
                st.session_state["fact_page"] = page - 1
                st.rerun()

        with p2:
            st.write(f"Página {page} / {total_pages} · Total facturas: {total_facturas}")

        with p3:
            if st.button("Siguiente ➡️", disabled=page >= total_pages, key="fact_next"):
                st.session_state["fact_page"] = page + 1
                st.rerun()


    # ---------------------------
    # PEDIDOS
    # ---------------------------
    with tab_ped:
        pedidos = (
            supabase.table("pedido")
            .select("*")
            .eq("clienteid", clienteid)
            .order("fecha_pedido", desc=True)
            .execute()
            .data
            or []
        )

        if not pedidos:
            st.info("📭 No hay pedidos")
        else:
            for p in pedidos:
                st_html(
                    f"""
                    <div style="border-left:5px solid #3b82f6;
                                background:#f9fafb;padding:10px;margin:6px 0;">
                        <b>{p.get("numero","PED-"+str(p.get("pedidoid")))}</b>  
                        🗓️ {p.get("fecha_pedido","-")}  
                        💰 {p.get("total","-")} €
                    </div>
                    """,
                    height=90,
                )
