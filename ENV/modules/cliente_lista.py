from typing import Any, Dict, Optional, List
import math
import pandas as pd
import requests
import streamlit as st
from streamlit.components.v1 import html as st_html

from modules.orbe_theme import apply_orbe_theme
from modules.cliente_form_api import render_cliente_form
from modules.cliente_direccion import render_direccion_form
from modules.cliente_contacto import render_contacto_form
from modules.cliente_observacion import render_observaciones_form

try:
    from streamlit_modal import Modal  # type: ignore
except Exception:
    # Fallback mínimo para evitar errores si la dependencia no está instalada
    class Modal:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

        def is_open(self):
            return True

        def open(self):
            return None

        def close(self):
            return None


def _safe(v, d: str = "-"):
    return v if v not in (None, "", "null") else d


def _normalize_id(v: Any):
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return st.session_state.get("ORBE_API_URL") or "http://127.0.0.1:8000"


def _api_get(path: str, params: Optional[dict] = None) -> dict:
    try:
        r = requests.get(f"{_api_base()}{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error llamando a API: {e}")
        return {}


def render_cliente_lista(API_URL: str):
    apply_orbe_theme()

    st.header("Gestión de clientes")
    st.caption("Consulta, filtra y accede a la ficha completa de tus clientes.")

    # Lanzar formularios de alta
    ctop1, ctop2 = st.columns(2)
    with ctop1:
        if st.button("➕ Nuevo cliente"):
            st.session_state["cli_show_form"] = "cliente"
            st.rerun()
    with ctop2:
        if st.button("➕ Nuevo potencial"):
            st.session_state["cli_show_form"] = "potencial"
            st.rerun()

    modo_form = st.session_state.get("cli_show_form")
    if modo_form in ("cliente", "potencial"):
        render_cliente_form(modo=modo_form)
        return

    defaults = {
        "cli_page": 1,
        "cli_sort_field": "razon_social",
        "cli_sort_dir": "ASC",
        "cli_view": "Tarjetas",
        "cli_result_count": 0,
        "cli_table_cols": ["clienteid", "razon_social", "identificador"],
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # Buscador
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input(
            "Buscar cliente",
            placeholder="Razón social o identificador",
            key="cli_q",
        )
        if st.session_state.get("last_q") != q:
            st.session_state["cli_page"] = 1
            st.session_state["last_q"] = q
    with c2:
        st.metric("Resultados", st.session_state["cli_result_count"])

    st.markdown("---")

    # Ficha seleccionada arriba
    sel = st.session_state.get("cliente_detalle_id")
    if sel:
        _render_modal_detalle(sel)
        st.markdown("---")

    # Opciones
    with st.expander("Opciones", expanded=False):
        o1, o2 = st.columns(2)
        with o1:
            st.session_state["cli_view"] = st.radio(
                "Vista",
                ["Tarjetas", "Tabla"],
                horizontal=True,
            )
        with o2:
            st.session_state["cli_sort_field"] = st.selectbox(
                "Ordenar por",
                ["razon_social", "identificador", "estadoid", "grupoid"],
            )
            st.session_state["cli_sort_dir"] = st.radio(
                "Dirección",
                ["ASC", "DESC"],
                horizontal=True,
            )
        if st.session_state["cli_view"] == "Tabla":
            all_cols = [
                "clienteid",
                "razon_social",
                "identificador",
                "estadoid",
                "grupoid",
                "trabajadorid",
                "formapagoid",
            ]
            st.session_state["cli_table_cols"] = st.multiselect(
                "Columnas a mostrar",
                options=all_cols,
                default=st.session_state.get("cli_table_cols", defaults["cli_table_cols"]),
            )
            st.session_state["cli_sort_field"] = st.selectbox(
                "Ordenar tabla por",
                options=st.session_state["cli_table_cols"] or all_cols,
                key="cli_sort_field_table",
            )
            st.session_state["cli_sort_dir"] = st.radio(
                "Dirección",
                ["ASC", "DESC"],
                horizontal=True,
                key="cli_sort_dir_table",
            )

    # Carga API
    page = st.session_state["cli_page"]
    page_size = 30
    params = {
        "q": q or None,
        "page": page,
        "page_size": page_size,
        "sort_field": st.session_state["cli_sort_field"],
        "sort_dir": st.session_state["cli_sort_dir"],
    }
    payload = _api_get("/api/clientes", params=params)
    clientes: List[Dict[str, Any]] = payload.get("data", [])
    total = payload.get("total", 0)
    total_pages = payload.get("total_pages", 1)
    st.session_state["cli_result_count"] = len(clientes)

    if not clientes:
        st.info("No se encontraron clientes.")
        return

    # Tabla / Tarjetas
    if st.session_state["cli_view"] == "Tabla":
        cols_sel = st.session_state.get("cli_table_cols") or defaults["cli_table_cols"]
        rows = []
        for c in clientes:
            row = {}
            for col in cols_sel:
                val = c.get(col)
                if col == "formapagoid":
                    val = _normalize_id(val)
                row[col] = val
            rows.append(row)
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        cols = st.columns(3)
        for i, c in enumerate(clientes):
            with cols[i % 3]:
                _render_card(c)

    # Paginación
    st.markdown("---")
    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button("Anterior", disabled=page <= 1):
            st.session_state["cli_page"] = page - 1
            st.rerun()
    with p2:
        st.write(f"Página {page} / {max(1, total_pages)} · Total: {total}")
    with p3:
        if st.button("Siguiente", disabled=page >= total_pages):
            st.session_state["cli_page"] = page + 1
            st.rerun()

    # Detalle modal si seleccionado

def _render_card(c: Dict[str, Any]):
    razon = _safe(c.get("razon_social"))
    ident = _safe(c.get("identificador"))

    estado = c.get("estadoid", "-")
    grupo = c.get("grupoid", "-")
    comercial = c.get("trabajadorid", "-")
    forma_pago = _normalize_id(c.get("formapagoid")) or "-"

    pres = c.get("presupuesto_reciente")
    pres_estado = "Sin presupuesto"
    pres_fecha = None
    if pres:
        pres_estado = {1: "Pendiente", 2: "Aceptado", 3: "Rechazado"}.get(
            pres.get("estado_presupuestoid"), "Sin presupuesto"
        )
        pres_fecha = pres.get("fecha_presupuesto")
    color_pres = {
        "Aceptado": "#16a34a",
        "Pendiente": "#f59e0b",
        "Rechazado": "#dc2626",
        "Sin presupuesto": "#6b7280",
    }.get(pres_estado, "#6b7280")
    fecha_html = (
        f"<div style='font-size:0.8rem;color:#475569;'>Último presupuesto: {pres_fecha}</div>"
        if pres_fecha else ""
    )

    st_html(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:14px;
                    background:#f9fafb;padding:14px;margin-bottom:14px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="font-size:1.05rem;font-weight:700;">{razon}</div>
            <div style="color:#6b7280;font-size:.9rem;">{ident}</div>
            <div style="margin-top:10px;font-size:.9rem;">
                <b>EstadoID:</b> {estado}<br>
                <b>GrupoID:</b> {grupo}<br>
                <b>ComercialID:</b> {comercial}<br>
                <b>Forma pagoID:</b> {forma_pago}<br>
                <span style="color:{color_pres};font-weight:600;">{pres_estado}</span>
                {fecha_html}
            </div>
        </div>
        """,
        height=240,
    )

    cid = c.get("clienteid")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("📄 Ficha", key=f"cli_ficha_{cid}", use_container_width=True):
            st.session_state["cliente_detalle_id"] = cid
            st.rerun()
    with b2:
        if st.button("Presupuesto", key=f"cli_pres_{cid}", use_container_width=True):
            st.toast("Crear presupuesto (pendiente de endpoint)", icon="ℹ️")
    with b3:
        if st.button("Baja", key=f"cli_del_{cid}", use_container_width=True):
            st.warning(f"Solicitud de baja cliente {cid} (pendiente de API)")


def _render_detalle(clienteid: int):
    st.markdown("---")
    st.subheader(f"Ficha cliente {clienteid}")
    base = _api_base()
    try:
        res = requests.get(f"{base}/api/clientes/{clienteid}", timeout=15)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        st.error(f"Error cargando ficha: {e}")
        return

    cli = data.get("cliente", {})
    df = data.get("direccion_fiscal") or {}
    cp = data.get("contacto_principal") or {}
    banco = data.get("banco") or {}

    tabs = st.tabs(["Resumen", "Direcciones", "Contactos", "Observaciones"])

    with tabs[0]:
        st.write(f"**Razón social:** {cli.get('razon_social') or '-'}")
        st.write(f"**Identificador:** {cli.get('identificador') or '-'}")
        st.write(f"**Estado:** {cli.get('estado', {}).get('label') or '-'}")
        st.write(f"**Forma pago ID:** {cli.get('formapagoid') or '-'}")
        with st.expander("Dirección fiscal", expanded=False):
            _render_dir_summary(df)
        with st.expander("Contacto principal", expanded=False):
            st.write(cp or {})
        with st.expander("Banco", expanded=False):
            st.write(banco or {})

    with tabs[1]:
        render_direccion_form(clienteid, key_prefix="inline_")

    with tabs[2]:
        render_contacto_form(clienteid, key_prefix="inline_")

    with tabs[3]:
        render_observaciones_form(clienteid, key_prefix="inline_")

    if st.button("Cerrar ficha", key=f"cerrar_{clienteid}", use_container_width=True):
        st.session_state["cliente_detalle_id"] = None
        st.rerun()


def _render_modal_detalle(clienteid: int):
    modal = Modal(key=f"modal_cliente_{clienteid}", title=f"Ficha cliente {clienteid}", max_width=900)

    if modal.is_open():
        base = _api_base()
        try:
            res = requests.get(f"{base}/api/clientes/{clienteid}", timeout=15)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            st.error(f"Error cargando ficha: {e}")
            if st.button("Cerrar", key=f"cerrar_err_{clienteid}"):
                st.session_state["cliente_detalle_id"] = None
                modal.close()
                st.rerun()
            modal.close()
            return

        cli = data.get("cliente", {})
        df = data.get("direccion_fiscal") or {}
        cp = data.get("contacto_principal") or {}
        banco = data.get("banco") or {}

        tabs = st.tabs(["Resumen", "Direcciones", "Contactos", "Observaciones"])

        with tabs[0]:
            st.write(f"**Razón social:** {cli.get('razon_social') or '-'}")
            st.write(f"**Identificador:** {cli.get('identificador') or '-'}")
            st.write(f"**Estado:** {cli.get('estado', {}).get('label') or '-'}")
            st.write(f"**Forma pago ID:** {cli.get('formapagoid') or '-'}")
            with st.expander("Dirección fiscal", expanded=False):
                _render_dir_summary(df)
            with st.expander("Contacto principal", expanded=False):
                st.write(cp or {})
            with st.expander("Banco", expanded=False):
                st.write(banco or {})

        with tabs[1]:
            render_direccion_form(clienteid, key_prefix="modal_")
        with tabs[2]:
            render_contacto_form(clienteid, key_prefix="modal_")
        with tabs[3]:
            render_observaciones_form(clienteid, key_prefix="modal_")

        if st.button("Cerrar ficha", key=f"cerrar_modal_{clienteid}", use_container_width=True):
            st.session_state["cliente_detalle_id"] = None
            modal.close()
            st.rerun()

    modal.open()


def _render_dir_summary(df: dict):
    if not df:
        st.info("Sin dirección fiscal")
        return
    st.markdown(
        f"""
        **{df.get('direccion','-')}**

        {df.get('cp','-')} {df.get('ciudad','-')} ({df.get('provincia','-')}) · {df.get('pais','-')}

        - Documentación impresa: {df.get('documentacion_impresa','-')}
        - Teléfono: {df.get('telefono') or '-'}
        - Email: {df.get('email') or '-'}
        """
    )
