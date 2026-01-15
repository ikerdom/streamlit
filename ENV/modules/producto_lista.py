import math
import os
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
from streamlit.components.v1 import html as st_html

from modules.orbe_theme import apply_orbe_theme
from modules.producto_arbol_ui import render_arbol_productos
from modules.producto_form import render_producto_form


def _api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return (
            os.getenv("ORBE_API_URL")
            or st.session_state.get("ORBE_API_URL")
            or "http://127.0.0.1:8000"
        )


def _api_get(path: str, params: Optional[dict] = None) -> dict:
    try:
        r = requests.get(f"{_api_base()}{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Error API: {e}")
        return {}


def _safe(v, d="-"):
    return v if v not in (None, "", "null") else d


def _price(v: Any):
    try:
        return f"{float(v):.2f} €"
    except Exception:
        return "-"


# ======================================================
# LISTA DE PRODUCTOS (UI -> FastAPI)
# ======================================================
def render_producto_lista(supabase=None):
    apply_orbe_theme()

    st.header("Gestión de productos")
    st.caption("Listado, filtros y acceso rápido a la ficha del producto.")

    st.session_state.setdefault("prod_show_form", False)
    # Modo catálogo / árbol
    st.session_state.setdefault("modo_producto", "Catálogo")
    st.session_state["modo_producto"] = st.selectbox(
        "Vista de productos",
        ["Catálogo", "Árbol"],
        index=0 if st.session_state.get("modo_producto") == "Catálogo" else 1,
        key="modo_prod_selector",
    )

    # Alta producto (solo catálogo)
    if st.session_state.get("modo_producto") == "Catálogo":
        if st.button("Nuevo producto", key="btn_nuevo_prod", width="stretch"):
            st.session_state["prod_show_form"] = True
            st.rerun()

    if st.session_state.get("prod_show_form"):
        supa = supabase or st.session_state.get("supa")
        if not supa:
            st.error("Necesito Supabase para usar el formulario de producto.")
            return
        render_producto_form(supa)
        return

    # Vista árbol
    if st.session_state.get("modo_producto") == "Árbol":
        supa = supabase or st.session_state.get("supa")
        if not supa:
            st.error("Necesito el cliente supabase para mostrar el árbol de productos.")
            return
        render_arbol_productos(supa)
        return

    # estado UI
    defaults = {
        "prod_page": 1,
        "prod_sort_field": "nombre",
        "prod_sort_dir": "ASC",
        "prod_view": "Tarjetas",
        "prod_result_count": 0,
        "prod_table_cols": ["productoid", "nombre", "referencia", "familia", "tipo", "precio"],
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # Catálogos
    cats = _api_get("/api/productos/catalogos")
    familias = {c["label"]: c["id"] for c in cats.get("familias", [])}
    tipos = {c["label"]: c["id"] for c in cats.get("tipos", [])}

    # Filtros
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input("Buscar", placeholder="Nombre, referencia, ISBN, EAN...", key="prod_q")
        if st.session_state.get("prod_last_q") != q:
            st.session_state["prod_page"] = 1
            st.session_state["prod_last_q"] = q
    with c2:
        st.metric("Resultados", st.session_state["prod_result_count"])

    with st.expander("Opciones y filtros", expanded=False):
        f1, f2 = st.columns(2)
        with f1:
            st.session_state["prod_view"] = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True)
            st.session_state["prod_sort_field"] = st.selectbox("Ordenar por", ["nombre", "titulo", "referencia"])
            st.session_state["prod_sort_dir"] = st.radio("Dirección", ["ASC", "DESC"], horizontal=True)
        with f2:
            fam_labels = ["Todas"] + list(familias.keys())
            tipo_labels = ["Todos"] + list(tipos.keys())
            st.session_state["prod_familia"] = st.selectbox(
                "Familia",
                fam_labels,
                index=fam_labels.index(st.session_state.get("prod_familia", "Todas"))
                if st.session_state.get("prod_familia") in fam_labels
                else 0,
            )
            st.session_state["prod_tipo"] = st.selectbox("Tipo", tipo_labels)
        if st.session_state["prod_view"] == "Tabla":
            all_cols = [
                "productoid",
                "nombre",
                "titulo",
                "referencia",
                "familia",
                "tipo",
                "impuesto",
                "estado",
                "precio",
            ]
            st.session_state["prod_table_cols"] = st.multiselect(
                "Columnas a mostrar",
                options=all_cols,
                default=st.session_state.get("prod_table_cols", defaults["prod_table_cols"]),
            )
            st.session_state["prod_sort_field"] = st.selectbox(
                "Ordenar tabla por",
                options=st.session_state["prod_table_cols"] or all_cols,
                key="prod_sort_field_table",
            )
            st.session_state["prod_sort_dir"] = st.radio(
                "Dirección",
                ["ASC", "DESC"],
                horizontal=True,
                key="prod_sort_dir_table",
            )

    # Params API
    page = st.session_state["prod_page"]
    page_size = 30
    params = {
        "q": q or None,
        "page": page,
        "page_size": page_size,
        "sort_field": st.session_state["prod_sort_field"],
        "sort_dir": st.session_state["prod_sort_dir"],
    }
    fam_sel = st.session_state.get("prod_familia")
    if fam_sel and fam_sel != "Todas":
        params["familiaid"] = familias.get(fam_sel)
    tipo_sel = st.session_state.get("prod_tipo")
    if tipo_sel and tipo_sel != "Todos":
        params["tipoid"] = tipos.get(tipo_sel)

    payload = _api_get("/api/productos", params=params)
    productos: List[Dict[str, Any]] = payload.get("data", [])
    total = payload.get("total", 0)
    total_pages = payload.get("total_pages", 1)
    st.session_state["prod_result_count"] = len(productos)

    # Ficha prioritaria si seleccionada
    sel = st.session_state.get("prod_detalle_id")
    if sel:
        _render_modal_producto(sel)
        st.markdown("---")

    if not productos:
        st.info("No hay productos con esos filtros.")
        return

    if st.session_state["prod_view"] == "Tarjetas":
        cols = st.columns(3)
        for i, p in enumerate(productos):
            with cols[i % 3]:
                _render_card_producto(p)
    else:
        _render_tabla_productos(productos)

    # paginación
    st.markdown("---")
    total_pages = max(1, math.ceil(total / page_size))
    p1, _, p3 = st.columns(3)
    with p1:
        if st.button("Anterior", disabled=page <= 1):
            st.session_state["prod_page"] = page - 1
            st.rerun()
    with p3:
        if st.button("Siguiente", disabled=page >= total_pages):
            st.session_state["prod_page"] = page + 1
            st.rerun()
    st.caption(f"Página {page}/{total_pages} · Total: {total}")


def _render_card_producto(p: dict):
    nombre = _safe(p.get("nombre")) or _safe(p.get("titulo"))
    ref = _safe(p.get("referencia"))
    familia = _safe(p.get("familia"))
    tipo = _safe(p.get("tipo"))
    precio = _price(p.get("precio"))
    portada = (p.get("portada_url") or "").strip()
    if portada and not portada.startswith("http"):
        portada = ""

    W, H = 105, 145
    portada_html = (
        f"<img src='{portada}' style='width:100%;height:100%;object-fit:cover;display:block;' />"
        if portada
        else "<div style='display:flex;align-items:center;justify-content:center;width:100%;height:100%;color:#94a3b8;'>Sin portada</div>"
    )

    st_html(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;
                    background:#f9fafb;padding:12px;margin-bottom:14px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="display:flex;gap:12px;">
                <div style="width:{W}px;height:{H}px;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;background:#fff;">
                    {portada_html}
                </div>
                <div style="flex:1;min-width:0;">
                    <div style="font-size:1.05rem;font-weight:700;">{nombre}</div>
                    <div style="color:#6b7280;font-size:.9rem;">Ref: {ref}</div>
                    <div style="margin-top:6px;font-size:.9rem;">
                        <b>Familia:</b> {familia}<br>
                        <b>Tipo:</b> {tipo}<br>
                        <b>Precio:</b> {precio}
                    </div>
                </div>
            </div>
        </div>
        """,
        height=200,
    )
    pid = p.get("productoid")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("Ficha", key=f"prod_ficha_{pid}", width="stretch"):
            st.session_state["prod_detalle_id"] = pid
            st.rerun()


def _render_tabla_productos(productos: list):
    cols_sel = st.session_state.get("prod_table_cols") or []
    if not cols_sel:
        st.info("Selecciona al menos una columna para mostrar.")
        return
    rows = []
    for p in productos:
        row = {}
        for col in cols_sel:
            row[col] = p.get(col)
        rows.append(row)
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # Selector rÃ¡pido para abrir ficha desde la tabla
    opciones = [
        (f"{p.get('productoid')} - {p.get('nombre')}", p.get("productoid"))
        for p in productos
        if p.get("productoid") is not None
    ]
    if opciones:
        label_map = {label: pid for label, pid in opciones}
        elegido = st.selectbox(
            "Abrir ficha de producto",
            options=list(label_map.keys()),
            index=0,
            key="prod_sel_ficha",
        )
        if st.button("Ver ficha seleccionada", key="prod_sel_btn", width="stretch"):
            st.session_state["prod_detalle_id"] = label_map[elegido]
            st.rerun()


def _render_modal_producto(productoid: int):
    try:
        res = requests.get(f"{_api_base()}/api/productos/{productoid}", timeout=15)
        res.raise_for_status()
        data = res.json() or {}
    except Exception as e:
        st.error(f"Error cargando ficha de producto: {e}")
        if st.button("Cerrar", key=f"cerrar_prod_err_{productoid}", width="stretch"):
            st.session_state["prod_detalle_id"] = None
            st.rerun()
        return

    p = data.get("producto", data)

    st.markdown("---")
    st.subheader(f"Ficha producto {productoid}")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.write(f"**Nombre:** {p.get('nombre') or '-'}")
        st.write(f"**Título:** {p.get('titulo') or '-'}")
        st.write(f"**Referencia:** {p.get('referencia') or '-'}")
        st.write(f"**ISBN / EAN:** {p.get('isbn') or '-'} / {p.get('ean') or '-'}")
        st.write(f"**Familia / Tipo:** {p.get('familia') or '-'} / {p.get('tipo') or '-'}")
        st.write(f"**Impuesto / Estado:** {p.get('impuesto') or '-'} / {p.get('estado') or '-'}")
        st.write(f"**Precio:** {_price(p.get('precio'))}")
        st.write(f"**Versatilidad:** {p.get('versatilidad') or '-'}")
        st.write(f"**Publico:** {p.get('publico')}")
        st.write(f"**Fecha publicación:** {p.get('fecha_publicacion') or '-'}")
    with c2:
        portada = p.get("portada_url") or ""
        if portada and portada.startswith("http"):
            st.image(portada, use_container_width=True)
        else:
            st.info("Sin portada")
    st.markdown("**Sinopsis / descripción**")
    st.write(p.get("sinopsis") or "—")

    if st.button("Cerrar ficha", key=f"cerrar_prod_{productoid}", width="stretch"):
        st.session_state["prod_detalle_id"] = None
        st.rerun()
