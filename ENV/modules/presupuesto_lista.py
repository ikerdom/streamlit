import io
import math
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

from modules.orbe_theme import apply_orbe_theme
from modules.presupuesto_api import (
    list_presupuestos,
    get_presupuesto,
    crear_presupuesto,
    get_catalogos,
    agregar_linea,
    borrar_presupuesto,
)
from modules.presupuesto_detalle import render_presupuesto_detalle, recalcular_lineas_presupuesto
from modules.presupuesto_form import render_presupuesto_form
from modules.presupuesto_convert import convertir_presupuesto_a_pedido
from modules.presupuesto_api import _base_url
from modules.ui.page import page
from modules.ui.section import section
from modules.ui.card import card
from modules.ui.empty import empty_state


def _safe(val, default="-"):
    return val if val not in (None, "", "null") else default


def _api_products():
    try:
        r = requests.get(
            f"{_base_url()}/api/productos",
            params={"page": 1, "page_size": 200, "sort_field": "nombre"},
            timeout=20,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar productos: {e}")
        return []


def _render_nuevo_presupuesto_inline():
    """Constructor rápido usando API (crea cabecera + primera línea opcional)."""
    st.markdown("### 🆕 Nuevo presupuesto")

    catalogos = get_catalogos()
    clientes = {c["label"]: c["id"] for c in catalogos.get("clientes", [])}
    trabajadores = {c["label"]: c["id"] for c in catalogos.get("trabajadores", [])}
    productos = _api_products()

    col1, col2 = st.columns(2)
    with col1:
        cliente_sel = st.selectbox("🧑‍🤝‍🧑 Cliente", ["(selecciona)"] + list(clientes.keys()))
    with col2:
        trabajador_sel = st.selectbox("👤 Comercial", ["(sin comercial)"] + list(trabajadores.keys()))

    col3, col4 = st.columns(2)
    with col3:
        fecha_pres = st.date_input("📅 Fecha del presupuesto", value=date.today())
    with col4:
        fecha_validez = st.date_input("⏱️ Validez hasta", value=date.today() + timedelta(days=30))

    col5, col6 = st.columns(2)
    with col5:
        producto_sel = st.selectbox(
            "📦 Producto inicial",
            ["(selecciona)"] + [p.get("nombre") for p in productos],
        )
    with col6:
        cantidad = st.number_input("Cantidad", min_value=1, step=1, value=1)

    if st.button("💾 Crear presupuesto", type="primary", use_container_width=True):
        if cliente_sel == "(selecciona)" or producto_sel == "(selecciona)":
            st.warning("Selecciona un cliente y un producto para crear el presupuesto.")
            return

        clienteid = clientes.get(cliente_sel)
        trabajadorid = trabajadores.get(trabajador_sel) if trabajador_sel != "(sin comercial)" else None
        payload = {
            "clienteid": clienteid,
            "trabajadorid": trabajadorid,
            "fecha_presupuesto": fecha_pres.isoformat(),
            "fecha_validez": fecha_validez.isoformat(),
            "observaciones": None,
            "facturar_individual": False,
        }
        try:
            pres = crear_presupuesto(payload)
            pid = pres.get("presupuestoid")
            prod = next((p for p in productos if p.get("nombre") == producto_sel), None)
            if pid and prod:
                try:
                    agregar_linea(
                        pid,
                        {"productoid": prod.get("productoid"), "cantidad": float(cantidad), "descripcion": prod.get("nombre")},
                    )
                except Exception as e:
                    st.warning(f"⚠️ Presupuesto creado sin línea inicial: {e}")

            st.session_state["presupuesto_modal_id"] = pid
            st.session_state["show_presupuesto_modal"] = True
            st.session_state["show_creator"] = False
            st.success(f"✅ Presupuesto creado correctamente: {pres.get('numero')}")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error creando presupuesto: {e}")


def _render_card(r, estados_map: dict):
    cli = _safe(r.get("clienteid"))
    est_nombre = estados_map.get(r.get("estado_presupuestoid"))

    e = (est_nombre or "").lower()
    if "acept" in e:
        color_estado = "#10b981"
    elif "rechaz" in e:
        color_estado = "#ef4444"
    elif "convert" in e:
        color_estado = "#6b7280"
    else:
        color_estado = "#3b82f6"

    pres_id = r.get("presupuestoid")
    numero = _safe(r.get("numero"))
    fecha = _safe(r.get("fecha_presupuesto"))
    total = _safe(r.get("total_estimada"))

    with card():
        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <span style="background:#111827;color:#fff;padding:2px 8px;border-radius:999px;font-size:0.75rem;">
                  #{pres_id}
                </span>
                <div style="font-weight:700;">{numero}</div>
              </div>
              <span style="background:{color_estado};color:#fff;padding:3px 10px;border-radius:999px;font-size:0.8rem;font-weight:600;">
                {est_nombre or '-'}
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(f"👤 {cli}  ·  📅 {fecha}")
        st.caption(f"💰 {total}")

        if st.button("🗂️ Ficha", key=f"pres_ficha_{pres_id}", use_container_width=True):
            st.session_state["presupuesto_modal_id"] = pres_id
            st.session_state["show_presupuesto_modal"] = True
            st.rerun()


def _render_table(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No hay presupuestos.")
        return
    cols = [
        "presupuestoid",
        "numero",
        "clienteid",
        "estado_presupuestoid",
        "fecha_presupuesto",
        "fecha_validez",
        "total_estimada",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    st.dataframe(df[cols], use_container_width=True, hide_index=True)
    buff = io.StringIO()
    df[cols].to_csv(buff, index=False)
    st.download_button(
        "⬇️ Exportar CSV",
        buff.getvalue(),
        file_name=f"presupuestos_{date.today()}.csv",
        mime="text/csv",
    )


def _render_presupuesto_modal(estados_map: dict):
    pid = st.session_state.get("presupuesto_modal_id")
    if not pid:
        return

    try:
        pres = get_presupuesto(pid)
    except Exception as e:
        empty_state(f"No se encontró el presupuesto. {e}", icon="⚠️")
        return

    est_nombre = estados_map.get(pres.get("estado_presupuestoid"))
    est_lower = (est_nombre or "").lower()
    bloqueado = (pres.get("editable") is False) or ("acept" in est_lower) or ("convert" in est_lower)

    if "acept" in est_lower:
        color_estado = "#10b981"
    elif "rechaz" in est_lower:
        color_estado = "#ef4444"
    elif "convert" in est_lower:
        color_estado = "#6b7280"
    else:
        color_estado = "#3b82f6"

    numero = pres.get("numero") or "N/A"
    total = pres.get("total_estimada")

    with card():
        top1, top2 = st.columns([3, 2])
        with top1:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                  <div style="font-size:1.15rem;font-weight:800;">📄 Presupuesto {numero}</div>
                  <span style="background:#111827;color:#fff;padding:2px 10px;border-radius:999px;font-size:0.8rem;">
                    ID #{pid}
                  </span>
                  <span style="background:{color_estado};color:#fff;padding:2px 10px;border-radius:999px;font-size:0.8rem;font-weight:700;">
                    {est_nombre or "Sin estado"}
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(f"📅 {_safe(pres.get('fecha_presupuesto'))} · ⏱️ Validez: {_safe(pres.get('fecha_validez'))}")

        with top2:
            colm1, colm2 = st.columns(2)
            with colm1:
                try:
                    st.metric("Total", f"{float(total or 0):,.2f} €")
                except Exception:
                    st.metric("Total", _safe(total))
            with colm2:
                st.metric("ClienteID", _safe(pres.get("clienteid")))

        a1, a2, a3 = st.columns([1, 1, 1])
        with a1:
            if st.button("↩️ Volver", use_container_width=True):
                st.session_state["show_presupuesto_modal"] = False
                st.session_state["presupuesto_modal_id"] = None
                st.rerun()
        with a2:
            if st.button("🗑️ Eliminar", use_container_width=True, disabled=bloqueado):
                try:
                    borrar_presupuesto(pid)
                    st.success("✅ Presupuesto eliminado.")
                    st.session_state["show_presupuesto_modal"] = False
                    st.session_state["presupuesto_modal_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al eliminar: {e}")
        with a3:
            if "acept" in est_lower:
                if st.button("🔄 Convertir", use_container_width=True):
                    convertir_presupuesto_a_pedido(pid)
                    st.rerun()
            else:
                st.button("🔄 Convertir", use_container_width=True, disabled=True)

    if bloqueado:
        st.warning("🔒 Este presupuesto está Aceptado/Convertido y no se puede editar.")
    else:
        st.info("✅ Presupuesto editable.")

    tab1, tab2 = st.tabs(["🧾 Cabecera", "📦 Líneas"])

    with tab1:
        with section("Datos del presupuesto", icon="🧾"):
            render_presupuesto_form(presupuestoid=pid, bloqueado=bloqueado)

        with section("Recalcular líneas por tarifas", icon="🔄"):
            fecha_validez = pres.get("fecha_validez")
            if isinstance(fecha_validez, str):
                try:
                    fecha_validez = date.fromisoformat(fecha_validez)
                except Exception:
                    fecha_validez = None

            fecha_manual = st.date_input(
                "Fecha de cálculo",
                value=fecha_validez or date.today(),
                key=f"recalc_fecha_{pid}",
                help="Usa esta fecha para recalcular tarifas (puedes ajustarla).",
                disabled=bloqueado,
            )

            if st.button("🔄 Recalcular líneas", use_container_width=True, disabled=bloqueado):
                recalcular_lineas_presupuesto(pid, fecha_manual)
                st.rerun()

    with tab2:
        with section("Detalle de líneas", icon="📦"):
            render_presupuesto_detalle(pid, bloqueado=bloqueado)


def render_presupuesto_lista(api_base: Optional[str] = None):
    apply_orbe_theme()

    defaults = {
        "pres_page": 1,
        "pres_view": "Tarjetas",
        "show_presupuesto_modal": False,
        "presupuesto_modal_id": None,
        "show_creator": False,
        "pres_q": "",
        "pres_estado": "Todos",
        "pres_cliente_filtro": "Todos",
        "pres_orden": "Últimos creados",
        "pres_result_count": 0,
        "pres_last_fingerprint": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    page_size_cards, page_size_table = 12, 30

    catalogos = get_catalogos()
    estados_map = {c["id"]: c["label"] for c in catalogos.get("estados", [])}
    clientes_map = {c["label"]: c["id"] for c in catalogos.get("clientes", [])}

    if st.session_state.get("show_presupuesto_modal") and st.session_state.get("presupuesto_modal_id"):
        _render_presupuesto_modal(estados_map)
        return

    with page(
        "Gestión de presupuestos",
        "Visualiza, filtra, edita y genera presupuestos.",
        icon="🧾",
    ):
        c1, c2 = st.columns([3, 1])
        with c1:
            q = st.text_input(
                "Buscar presupuesto",
                placeholder="Número o referencia cliente…",
                key="pres_q",
            )
        with c2:
            st.metric("Resultados (página)", st.session_state.get("pres_result_count", 0))

        with st.expander("⚙️ Filtros avanzados", expanded=False):
            f1, f2, f3 = st.columns(3)
            with f1:
                estado_sel = st.selectbox(
                    "Estado",
                    ["Todos"] + list(estados_map.values()),
                    key="pres_estado",
                )
            with f2:
                cliente_filtro = st.selectbox(
                    "Cliente",
                    ["Todos"] + list(clientes_map.keys()),
                    key="pres_cliente_filtro",
                )
            with f3:
                orden_sel = st.selectbox(
                    "Ordenar por",
                    ["Últimos creados", "Fecha de presupuesto"],
                    key="pres_orden",
                )

            f4, f5 = st.columns([1, 1])
            with f4:
                st.radio(
                    "Vista",
                    ["Tarjetas", "Tabla"],
                    horizontal=True,
                    key="pres_view",
                )
            with f5:
                if st.button("🆕 Nuevo presupuesto", use_container_width=True):
                    st.session_state["show_creator"] = True
                    st.rerun()

        fingerprint = (
            (q or "").strip(),
            estado_sel,
            cliente_filtro,
            orden_sel,
            st.session_state.get("pres_view"),
        )
        if st.session_state.get("pres_last_fingerprint") != fingerprint:
            st.session_state["pres_page"] = 1
            st.session_state["pres_last_fingerprint"] = fingerprint

        st.markdown("---")

        if st.session_state.get("show_creator"):
            with section("Nuevo presupuesto", icon="🆕"):
                _render_nuevo_presupuesto_inline()
            st.markdown("")

        total, rows = 0, []
        try:
            per_page = page_size_cards if st.session_state["pres_view"] == "Tarjetas" else page_size_table
            params = {
                "q": q or None,
                "page": st.session_state["pres_page"],
                "page_size": per_page,
                "ordenar_por": "creado_en" if orden_sel == "Últimos creados" else "fecha_presupuesto",
            }
            if estado_sel != "Todos":
                params["estadoid"] = next((k for k, v in estados_map.items() if v == estado_sel), None)
            if cliente_filtro != "Todos":
                params["clienteid"] = clientes_map.get(cliente_filtro)

            payload = list_presupuestos(params)
            rows = payload.get("data", [])
            total = payload.get("total", 0)
            st.session_state["pres_result_count"] = len(rows)
        except Exception as e:
            st.error(f"❌ Error cargando presupuestos: {e}")
            rows = []
            total = 0

        if not rows:
            empty_state("No hay presupuestos que coincidan con los filtros.", icon="🗒️")
            return

        per_page = page_size_cards if st.session_state["pres_view"] == "Tarjetas" else page_size_table
        total_pages = max(1, math.ceil((total or 0) / per_page))

        st.caption(f"Página {st.session_state['pres_page']} / {total_pages} · Total: {total}")

        p1, p2, p3 = st.columns(3)
        with p1:
            if st.button("⬅️ Anterior", disabled=st.session_state["pres_page"] <= 1):
                st.session_state["pres_page"] -= 1
                st.rerun()
        with p2:
            st.write("")
        with p3:
            if st.button("Siguiente ➡️", disabled=st.session_state["pres_page"] >= total_pages):
                st.session_state["pres_page"] += 1
                st.rerun()

        st.markdown("---")

        if st.session_state["pres_view"] == "Tarjetas":
            cols = st.columns(3)
            for i, r in enumerate(rows):
                with cols[i % 3]:
                    _render_card(r, estados_map)
        else:
            _render_table(rows)
