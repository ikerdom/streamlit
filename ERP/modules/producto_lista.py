import io
import math
from datetime import date

import pandas as pd
import streamlit as st

from modules.orbe_theme import apply_orbe_theme
from modules.ui.page import page
from modules.ui.section import section
from modules.ui.card import card
from modules.ui.empty import empty_state

from modules.producto_arbol_ui import render_arbol_productos
from modules.producto_models import (
    load_familias,
    load_tipos_producto,
    load_impuestos,
    load_estados_producto,
    get_familia_label,
    get_tipo_label,
    get_impuesto_label,
    get_estado_label,
)

# ======================================================
# ⚙️ UTILIDADES
# ======================================================
def _safe(v, d="-"):
    return v if v not in (None, "", "null") else d


def _format_precio(v):
    if isinstance(v, (int, float)):
        return f"{float(v):.2f} €"
    return "-"


def _range(page_num: int, page_size: int):
    s = (page_num - 1) * page_size
    return s, s + page_size - 1


def _build_search_or(s, fields=("nombre", "titulo", "referencia", "isbn", "ean")):
    s = (s or "").strip()
    if not s:
        return None
    return ",".join(f"{f}.ilike.%{s}%" for f in fields)


def _safe_catalog(loader, supabase):
    try:
        data = loader(supabase)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        st.warning(f"⚠️ Catálogo no disponible: {e}")
        return {}


def _idx_from_catalog(cat: dict, val):
    if not cat:
        return 0
    for i, (_, v) in enumerate(cat.items()):
        if v == val:
            return i + 1
    return 0


def _render_fixed_lines(text: str, max_lines: int = 2, line_len: int = 44):
    """
    Renderiza SIEMPRE el mismo nº de líneas (Streamlit puro) para que
    nombre/título largos no cambien la altura de la card.
    """
    words = (text or "").strip().split()
    lines = []
    cur = ""

    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= line_len:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
            if len(lines) >= max_lines:
                break

    if len(lines) < max_lines and cur:
        lines.append(cur)

    while len(lines) < max_lines:
        lines.append(" ")

    for l in lines[:max_lines]:
        st.caption(l)


def _render_cover_box(portada_url: str | None):
    """
    Portada con tamaño estable + marco bonito.
    Si no hay portada, placeholder decente.
    """
    portada = (portada_url or "").strip()
    if portada and not portada.startswith("http"):
        portada = ""

    # Tamaño “catálogo” (no gigantes): parecido a tu idea inicial
    W, H = 105, 145

    if portada:
        st.markdown(
            f"""
            <div style="
                width:{W}px;height:{H}px;
                border:1px solid #e5e7eb;
                border-radius:10px;
                background:#ffffff;
                overflow:hidden;
                box-shadow:0 1px 2px rgba(0,0,0,0.06);
            ">
                <img src="{portada}" style="width:100%;height:100%;object-fit:cover;display:block;" />
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Placeholder bonito (sin depender de URLs externas)
        st.markdown(
            f"""
            <div style="
                width:{W}px;height:{H}px;
                border:1px dashed #cbd5e1;
                border-radius:10px;
                background:linear-gradient(180deg,#ffffff,#f8fafc);
                display:flex;
                flex-direction:column;
                align-items:center;
                justify-content:center;
                box-shadow:0 1px 2px rgba(0,0,0,0.04);
                color:#334155;
                font-weight:600;
            ">
                <div style="font-size:26px;line-height:1;">📘</div>
                <div style="font-size:11px;font-weight:500;margin-top:6px;color:#64748b;">
                    Sin portada
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ======================================================
# 🟦 CARD PRODUCTO (altura estable + portada grande)
# ======================================================
def _render_card_producto(p: dict, supabase):
    pid = p.get("productoid")

    nombre = _safe(p.get("nombre"))
    titulo = _safe(p.get("titulo"), "")
    precio_str = _format_precio(p.get("precio_generico"))

    tipo_lbl = _safe(get_tipo_label(p.get("producto_tipoid"), supabase), "Sin tipo")
    familia_lbl = _safe(get_familia_label(p.get("familia_productoid"), supabase), "Sin familia")
    estado_lbl = _safe(get_estado_label(p.get("estado_productoid"), supabase), "Activo")

    portada_url = p.get("portada_url")

    with card():
        # Layout compacto, pero bonito
        c_img, c_info = st.columns([1, 2], gap="small")

        with c_img:
            _render_cover_box(portada_url)

        with c_info:
            # Nombre → siempre 2 líneas
            _render_fixed_lines(nombre, max_lines=2, line_len=44)

            # Título → siempre 2 líneas (aunque no exista)
            _render_fixed_lines(titulo or "", max_lines=2, line_len=44)

            st.caption(f"🏷️ {tipo_lbl}")
            st.caption(f"📂 {familia_lbl}")
            st.caption(f"⚙️ {estado_lbl}")

            st.write(f"💶 **{precio_str}**")


        if st.button("📄 Ficha", key=f"prod_ficha_{pid}", use_container_width=True):
            st.session_state["producto_modal_id"] = pid
            st.session_state["show_producto_modal"] = True
            st.rerun()



# ======================================================
# 🟩 FICHA / MODAL ARRIBA (estilo Orbe)
# ======================================================
def render_producto_modal(supabase):
    if not st.session_state.get("show_producto_modal"):
        return

    pid = st.session_state.get("producto_modal_id")
    if not pid:
        st.session_state["show_producto_modal"] = False
        return

    try:
        p = (
            supabase.table("producto")
            .select("*")
            .eq("productoid", int(pid))
            .single()
            .execute()
            .data
        )
    except Exception as e:
        st.error(f"❌ Error cargando producto: {e}")
        return

    nombre = p.get("nombre") or "(Sin nombre)"
    titulo = p.get("titulo") or ""
    precio = _format_precio(p.get("precio_generico"))

    tipo_lbl = get_tipo_label(p.get("producto_tipoid"), supabase)
    familia_lbl = get_familia_label(p.get("familia_productoid"), supabase)
    impuesto_lbl = get_impuesto_label(p.get("impuestoid"), supabase)
    estado_lbl = get_estado_label(p.get("estado_productoid"), supabase)

    with page(title="Ficha de producto", subtitle=None, icon="📘"):
        # Cabecera compacta
        c_close, c_head = st.columns([1, 5], gap="small")

        with c_close:
            if st.button("⬅️ Volver", key=f"close_prod_{pid}", use_container_width=True):
                st.session_state["show_producto_modal"] = False
                st.session_state["producto_modal_id"] = None
                st.rerun()

        with c_head:
            with card():
                st.markdown(f"### 📘 {nombre}")
                meta = f"**ID:** {pid}"
                if titulo:
                    meta += f" · **Título:** {titulo}"
                st.caption(meta)

        tab_general, tab_desc = st.tabs(["📌 General", "📝 Descripción"])

        with tab_general:
            c1, c2 = st.columns([1, 2], gap="large")

            with c1:
                portada = (p.get("portada_url") or "").strip()
                if portada and portada.startswith("http"):
                    try:
                        st.image(portada, use_container_width=True)
                    except Exception:
                        pass
                else:
                    # Placeholder en ficha también, por consistencia
                    _render_cover_box(None)

            with c2:
                def f(lbl, val):
                    if val not in (None, "", "null"):
                        st.write(f"**{lbl}:** {val}")

                f("Precio", precio)
                f("Estado", estado_lbl or "-")
                f("Publicación", p.get("fecha_publicacion") or "-")
                f("Público", "Sí" if p.get("publico") else "No")

                st.markdown("---")

                f("Referencia", p.get("referencia"))
                f("ISBN", p.get("isbn"))
                f("EAN", p.get("ean"))
                f("Tipo", tipo_lbl)
                f("Familia", familia_lbl)
                f("Impuesto", impuesto_lbl)
                f("Cuerpo certificado", p.get("cuerpo_certificado"))
                f("Versatilidad", p.get("versatilidad"))
                f("Autores", p.get("autores"))

        with tab_desc:
            st.markdown("### 📝 Sinopsis")
            if p.get("sinopsis"):
                st.info(p["sinopsis"])
            else:
                st.caption("No hay sinopsis registrada.")

        # Ajustes rápidos (estado + público)
        with section("Ajustes rápidos", icon="⚙️"):
            estados = _safe_catalog(load_estados_producto, supabase)

            cA, cB = st.columns([2, 1])
            with cA:
                estado_sel = st.selectbox(
                    "Estado",
                    ["(sin estado)"] + list(estados.keys()),
                    index=_idx_from_catalog(estados, p.get("estado_productoid")),
                    key=f"prod_modal_estado_{pid}",
                )
            with cB:
                publico_sel = st.checkbox(
                    "Visible al público",
                    value=bool(p.get("publico", True)),
                    key=f"prod_modal_publico_{pid}",
                )

            if st.button("💾 Guardar cambios", key=f"prod_modal_save_{pid}", use_container_width=True):
                try:
                    supabase.table("producto").update(
                        {
                            "estado_productoid": estados.get(estado_sel),
                            "publico": publico_sel,
                        }
                    ).eq("productoid", int(pid)).execute()
                    st.toast("Cambios guardados", icon="💾")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error guardando cambios: {e}")


# ======================================================
# 🟪 TABLA PRODUCTOS (selector columnas + campos reales)
# ======================================================
def _render_tabla_productos(productos: list, supabase):
    rows = []
    for p in productos:
        rows.append(
            {
                "ID": p.get("productoid"),
                "Nombre": p.get("nombre"),
                "Título": p.get("titulo"),
                "Ref/SKU": p.get("referencia"),
                "EAN": p.get("ean"),
                "ISBN": p.get("isbn"),
                "Tipo": get_tipo_label(p.get("producto_tipoid"), supabase),
                "Familia": get_familia_label(p.get("familia_productoid"), supabase),
                "Estado": get_estado_label(p.get("estado_productoid"), supabase),
                "Impuesto": get_impuesto_label(p.get("impuestoid"), supabase),
                "Precio": p.get("precio_generico"),
                "Público": p.get("publico"),
                "Fecha alta": p.get("fecha_alta"),
                "Fecha publicación": p.get("fecha_publicacion"),
                "Páginas": p.get("paginas_totales"),
                "Autores": p.get("autores"),
                "Cuerpo certificado": p.get("cuerpo_certificado"),
                "URL portada": p.get("portada_url"),
                "URL producto": p.get("url_producto"),
                "Depósito legal": p.get("deposito_legal"),
                "Versatilidad": p.get("versatilidad"),
                "ProveedorID": p.get("proveedorid"),
                "CategoríaID": p.get("categoriaid"),
                "OrigenID": p.get("id_origen"),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        st.info("📭 No hay productos para mostrar en tabla.")
        return

    all_cols = list(df.columns)

    # ✅ FIX WARNING: no usar default + session_state a la vez
    if "prod_table_cols" not in st.session_state:
        st.session_state["prod_table_cols"] = [
            "ID",
            "Nombre",
            "Ref/SKU",
            "Tipo",
            "Familia",
            "Estado",
            "Precio",
            "Público",
        ]

    st.multiselect(
        "Columnas visibles",
        options=all_cols,
        key="prod_table_cols",
    )

    cols_sel = st.session_state.get("prod_table_cols", [])
    if not cols_sel:
        st.warning("Selecciona al menos una columna para mostrar la tabla.")
        return

    st.dataframe(df[cols_sel], use_container_width=True, hide_index=True)

    buff = io.StringIO()
    df.to_csv(buff, index=False)
    st.download_button(
        "⬇️ Exportar CSV",
        buff.getvalue(),
        file_name=f"productos_{date.today()}.csv",
        mime="text/csv",
        use_container_width=True,
    )
def render_producto_lista(supabase):
    apply_orbe_theme()

    defaults = {
        "prod_page": 1,
        "prod_view": "Tarjetas",
        "prod_sort_dir": "ASC",   # ✅ ASC por defecto
        "prod_q": "",
        "prod_last_q": "",
        "prod_familia": "Todas",
        "prod_tipo": "Todos",
        "show_producto_modal": False,
        "producto_modal_id": None,
        "modo_producto": "Catálogo",
        "prod_result_count": 0,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # Si hay ficha abierta → solo ficha
    if st.session_state.get("show_producto_modal") and st.session_state.get("producto_modal_id"):
        render_producto_modal(supabase)
        return

    with page(
        title="Catálogo de productos",
        subtitle="Consulta, filtra y accede a la ficha profesional de cada producto.",
        icon="📦",
    ):
        # -----------------------------
        # Barra superior compacta
        # -----------------------------
        top1, top2, top3 = st.columns([1.2, 1.2, 3.6], gap="small")

        with top1:
            st.radio(
                "Modo",
                ["Catálogo", "Árbol"],
                horizontal=True,
                key="modo_producto",
                label_visibility="collapsed",
            )

        with top2:
            st.radio(
                "Vista",
                ["Tarjetas", "Tabla"],
                horizontal=True,
                key="prod_view",
                label_visibility="collapsed",
            )

        with top3:
            st.write("")
            st.caption(f"Total: **{st.session_state.get('prod_result_count', 0)}**")

        # -----------------------------
        # Árbol
        # -----------------------------
        if st.session_state["modo_producto"] == "Árbol":
            with section("Árbol de productos", icon="🌳"):
                render_arbol_productos(supabase)
            return

        # -----------------------------
        # Catálogos
        # -----------------------------
        familias = _safe_catalog(load_familias, supabase)
        tipos = _safe_catalog(load_tipos_producto, supabase)
        _safe_catalog(load_impuestos, supabase)

        # -----------------------------
        # Búsqueda
        # -----------------------------
        c1, c2 = st.columns([3, 1], gap="small")
        with c1:
            q = st.text_input(
                "Buscar producto",
                placeholder="Nombre, título, referencia, ISBN, EAN…",
                key="prod_q",
                label_visibility="collapsed",
            )
            if q != st.session_state.get("prod_last_q", ""):
                st.session_state["prod_page"] = 1
                st.session_state["prod_last_q"] = q

        # -----------------------------
        # Filtros
        # -----------------------------
        with st.expander("⚙️ Filtros avanzados", expanded=False):
            cA, cB = st.columns(2)
            with cA:
                st.selectbox("📂 Familia", ["Todas"] + list(familias.keys()), key="prod_familia")
            with cB:
                st.selectbox("🏷️ Tipo", ["Todos"] + list(tipos.keys()), key="prod_tipo")

            st.markdown("### ↕️ Orden")
            st.radio("Dirección", ["ASC", "DESC"], horizontal=True, key="prod_sort_dir")

        # -----------------------------
        # QUERY
        # -----------------------------
        productos = []
        total = 0

        page_size = 12 if st.session_state["prod_view"] == "Tarjetas" else 30

        familia_sel = st.session_state["prod_familia"]
        tipo_sel = st.session_state["prod_tipo"]
        sort_dir = st.session_state.get("prod_sort_dir", "ASC")
        q = st.session_state.get("prod_q", "")

        try:
            # COUNT
            base_count = supabase.table("producto").select("productoid", count="exact")

            or_filter = _build_search_or(q)
            if or_filter:
                base_count = base_count.or_(or_filter)

            if familia_sel != "Todas" and familia_sel in familias:
                base_count = base_count.eq("familia_productoid", familias[familia_sel])

            if tipo_sel != "Todos" and tipo_sel in tipos:
                base_count = base_count.eq("producto_tipoid", tipos[tipo_sel])

            cres = base_count.execute()
            total = cres.count or 0
            st.session_state["prod_result_count"] = total

            total_pages = max(1, math.ceil(total / page_size))
            if st.session_state["prod_page"] > total_pages:
                st.session_state["prod_page"] = total_pages

            start, end = _range(st.session_state["prod_page"], page_size)

            # DATA
            base = supabase.table("producto").select("*")

            if or_filter:
                base = base.or_(or_filter)

            if familia_sel != "Todas" and familia_sel in familias:
                base = base.eq("familia_productoid", familias[familia_sel])

            if tipo_sel != "Todos" and tipo_sel in tipos:
                base = base.eq("producto_tipoid", tipos[tipo_sel])

            base = base.order("nombre", desc=(sort_dir == "DESC"))
            productos = base.range(start, end).execute().data or []

        except Exception as e:
            st.error(f"❌ Error cargando productos: {e}")
            return

        # -----------------------------
        # Paginación
        # -----------------------------
        total_pages = max(1, math.ceil(total / page_size))
        st.caption(f"Página {st.session_state['prod_page']}/{total_pages} · Total: {total}")

        p1, _, p3 = st.columns(3)
        with p1:
            if st.button("⬅️ Anterior", disabled=st.session_state["prod_page"] <= 1):
                st.session_state["prod_page"] -= 1
                st.rerun()
        with p3:
            if st.button("Siguiente ➡️", disabled=st.session_state["prod_page"] >= total_pages):
                st.session_state["prod_page"] += 1
                st.rerun()

        st.markdown("---")

        if not productos:
            empty_state("No hay productos que coincidan con los filtros.", icon="📭")
            return

        # -----------------------------
        # Render
        # -----------------------------
        if st.session_state["prod_view"] == "Tarjetas":
            cols = st.columns(3)
            for i, p in enumerate(productos):
                with cols[i % 3]:
                    _render_card_producto(p, supabase)
        else:
            _render_tabla_productos(productos, supabase)
