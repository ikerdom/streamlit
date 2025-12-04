import io
import math
import pandas as pd
import streamlit as st
from datetime import date
from streamlit.components.v1 import html as st_html

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
from modules.producto_arbol_ui import render_arbol_productos
from modules.orbe_theme import apply_orbe_theme


# ======================================================
# ⚙️ UTILIDADES
# ======================================================
def _safe(v, d="-"):
    return v if v not in (None, "", "null") else d


def _format_precio(v):
    if isinstance(v, (int, float)):
        return f"{float(v):.2f} €"
    return "-"


def _range(page, page_size):
    s = (page - 1) * page_size
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


# ======================================================
# 🟦 CARD PROFESIONAL (estilo cliente)
# ======================================================
def _render_card_producto(p, supabase):
    apply_orbe_theme()

    nombre = _safe(p.get("nombre"))
    titulo = _safe(p.get("titulo"))
    precio_str = _format_precio(p.get("precio_generico"))
    tipo_lbl = get_tipo_label(p.get("producto_tipoid"), supabase)
    familia_lbl = get_familia_label(p.get("familia_productoid"), supabase)
    estado_lbl = get_estado_label(p.get("estado_productoid"), supabase) or "Activo"

    portada = p.get("portada_url") or ""
    pid = p.get("productoid")

    if portada and not portada.startswith("http"):
        portada = ""

    # Colores
    estado_color = {
        "Activo": "#10b981",
        "Descatalogado": "#dc2626",
        "Pendiente": "#f59e0b",
    }.get(estado_lbl, "#6b7280")

    html = f"""
    <div style="
        border:1px solid #e5e7eb;
        border-radius:12px;
        background:#f9fafb;
        padding:12px;
        margin-bottom:14px;
        box-shadow:0 1px 3px rgba(0,0,0,0.08);
    ">

        <div style="display:flex;gap:12px;">

            <div style="
                width:80px;height:110px;
                border:1px solid #ddd;
                border-radius:8px;
                overflow:hidden;
                background:#fff;
                display:flex;align-items:center;justify-content:center;
            ">
                {"<img src='"+portada+"' style='width:100%;height:100%;object-fit:cover;' />" if portada else "📘"}
            </div>

            <div style="flex:1;min-width:0;">
                <div style="
                    font-size:1rem;font-weight:600;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                ">{nombre}</div>

                <div style="
                    color:#6b7280;font-size:0.85rem;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                ">{titulo}</div>

                <div style="display:flex;flex-wrap:wrap;gap:6px;margin:6px 0;">
                    <span style="background:#fef3c7;color:#92400e;padding:2px 6px;border-radius:6px;font-size:0.72rem;">
                        {tipo_lbl}
                    </span>
                    <span style="background:#ecfdf5;color:#065f46;padding:2px 6px;border-radius:6px;font-size:0.72rem;">
                        {familia_lbl}
                    </span>
                    <span style="background:#e0f2fe;color:{estado_color};padding:2px 6px;border-radius:6px;font-size:0.72rem;">
                        {estado_lbl}
                    </span>
                </div>

                <div>💶 <b>{precio_str}</b></div>
            </div>
        </div>
    </div>
    """
    st_html(html, height=210)

    if st.button("📄 Ficha", key=f"prod_ficha_{pid}", use_container_width=True):
        st.session_state["producto_modal_id"] = pid
        st.session_state["show_producto_modal"] = True
        st.rerun()


# ======================================================
# 🟩 MODAL PROFESIONAL (arriba, estilo cliente)
# ======================================================
def render_producto_modal(supabase):
    if not st.session_state.get("show_producto_modal"):
        return

    pid = st.session_state["producto_modal_id"]

    try:
        p = (
            supabase.table("producto")
            .select("*")
            .eq("productoid", pid)
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

    # ===========================================
    # CABECERA SUPERIOR
    # ===========================================
    col_close, col_title = st.columns([1, 4])

    with col_close:
        if st.button("⬅️ Cerrar ficha", key=f"close_prod_{pid}", use_container_width=True):
            st.session_state["show_producto_modal"] = False
            st.rerun()

    with col_title:
        st.markdown(
            f"""
            <div style='padding:14px;border-radius:12px;background:#f9fafb;border:1px solid #e5e7eb;'>
                <h3 style='margin:0;'>📘 {nombre}</h3>
                <p style='margin:4px 0 0 0;color:#4b5563;font-size:0.9rem;'>
                    <b>ID:</b> {pid} · 
                    <b>Título:</b> {titulo}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ===========================================
    # TABS
    # ===========================================
    tab_general, tab_detalles = st.tabs(["📌 General", "📝 Descripción"])

    # ---------------------------
    # TAB GENERAL
    # ---------------------------
    with tab_general:
        c1, c2 = st.columns([1, 2])

        with c1:
            portada = p.get("portada_url")
            if portada:
                st.image(portada, use_container_width=True)

            st.write("**💶 Precio:**", precio)
            st.write("**⚙️ Estado:**", estado_lbl)
            st.write("**📅 Publicación:**", p.get("fecha_publicacion") or "-")
            st.write("**👁 Público:**", "Sí" if p.get("publico") else "No")

        with c2:
            def f(lbl, val):
                if val not in (None, "", "null"):
                    st.write(f"**{lbl}:** {val}")

            f("Referencia", p.get("referencia"))
            f("ISBN", p.get("isbn"))
            f("EAN", p.get("ean"))
            f("Tipo", tipo_lbl)
            f("Familia", familia_lbl)
            f("Impuesto", impuesto_lbl)
            f("Cuerpo certificado", p.get("cuerpo_certificado"))
            f("Versatilidad", p.get("versatilidad"))
            f("Autores", p.get("autores") or "Sin autor")

    # ---------------------------
    # TAB DESCRIPCIÓN
    # ---------------------------
    with tab_detalles:
        st.markdown("### 📝 Sinopsis")
        if p.get("sinopsis"):
            st.info(p["sinopsis"])
        else:
            st.caption("No hay sinopsis registrada.")

    # ===========================
    # AJUSTES RÁPIDOS
    # ===========================
    st.markdown("---")
    st.subheader("⚙️ Ajustes rápidos")

    estados = load_estados_producto(supabase)

    def idx(d, val):
        keys = list(d.keys())
        for i, k in enumerate(keys):
            if d[k] == val:
                return i + 1
        return 0

    cA, cB = st.columns([2, 1])
    with cA:
        estado_sel = st.selectbox(
            "Estado",
            ["(sin estado)"] + list(estados.keys()),
            index=idx(estados, p.get("estado_productoid")),
        )
    with cB:
        publico_sel = st.checkbox("Visible al público", value=bool(p.get("publico", True)))

    if st.button("💾 Guardar", use_container_width=True):
        supabase.table("producto").update({
            "estado_productoid": estados.get(estado_sel),
            "publico": publico_sel,
        }).eq("productoid", pid).execute()
        st.toast("Cambios guardados", icon="💾")
        st.rerun()

# ======================================================
# 🧱 VISTA PRINCIPAL — CATÁLOGO DE PRODUCTOS (PRO)
# ======================================================
def render_producto_lista(supabase):
    from modules.orbe_theme import apply_orbe_theme
    apply_orbe_theme()

    # ======================================================
    # 📌 MODAL ARRIBA DEL TODO (igual que CLIENTES)
    # ======================================================
    if st.session_state.get("show_producto_modal") and st.session_state.get("producto_modal_id"):
        try:
            st.session_state.pop("_dialog_state", None)
        except Exception:
            pass

        render_producto_modal(supabase)
        st.markdown("## ")  # separación visual

    # ======================================================
    # 🔧 ESTADO INICIAL
    # ======================================================
    st.session_state.setdefault("prod_page", 1)
    st.session_state.setdefault("prod_view", "Tarjetas")
    st.session_state.setdefault("prod_sort", "nombre ASC")
    st.session_state.setdefault("producto_show_form", False)
    st.session_state.setdefault("producto_editar_id", None)
    st.session_state.setdefault("show_producto_modal", False)
    st.session_state.setdefault("producto_modal_id", None)
    st.session_state.setdefault("confirm_delete_producto", False)
    st.session_state.setdefault("modo_producto", "Catálogo")

    # ======================================================
    # 🧭 CABECERA
    # ======================================================
    st.header("📦 Catálogo de productos")
    st.caption("Consulta, filtra y accede a la ficha profesional de cada producto.")

    # Guardamos supabase en sesión para helpers
    st.session_state["_supabase_for_helpers"] = supabase

    # Volver desde ficha
    if st.session_state.get("_go_catalog"):
        st.session_state["modo_producto"] = "Catálogo"
        st.session_state["_go_catalog"] = False
        st.rerun()

    # ======================================================
    # 🔀 Selector de modo
    # ======================================================
    modo = st.radio("Modo", ["Catálogo", "Árbol"], horizontal=True, key="modo_producto")

    if modo == "Árbol":
        render_arbol_productos(supabase)
        st.markdown("---")
        if st.button("⬅️ Volver al catálogo", use_container_width=True):
            st.session_state["modo_producto"] = "Catálogo"
            st.rerun()
        return



    # ======================================================
    # 📁 CATÁLOGOS
    # ======================================================
    familias = _safe_catalog(load_familias, supabase)
    tipos = _safe_catalog(load_tipos_producto, supabase)
    impuestos = _safe_catalog(load_impuestos, supabase)
    # estados ELIMINADOS — no se usan más

    # Filtro heredado del árbol
    if st.session_state.get("_pending_filter_from_tree"):
        target = st.session_state["_pending_filter_from_tree"]
        if target in familias:
            st.session_state["prod_familia"] = target
        st.session_state["_pending_filter_from_tree"] = None

    # ======================================================
    # 🔍 BUSCADOR PRINCIPAL (fuera del expander)
    # ======================================================
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input(
            "🔎 Buscar producto",
            placeholder="Nombre, título, referencia, ISBN, EAN…",
            key="prod_q",
        )

        # Evitar cierre al escribir (igual que clientes)
        if "prod_last_q" not in st.session_state:
            st.session_state["prod_last_q"] = ""

        if q != st.session_state["prod_last_q"]:
            st.session_state["prod_page"] = 1
            st.session_state["prod_last_q"] = q

    with c2:
        st.metric("📦 Resultados", st.session_state.get("prod_result_count", 0))

    st.markdown("---")

    # ======================================================
    # ⚙️ FILTROS AVANZADOS — estilo clientes
    # ======================================================
    with st.expander("⚙️ Filtros avanzados", expanded=False):

        # --------------------------
        # 📂 Familia y Tipo
        # --------------------------
        cA, cB = st.columns(2)
        with cA:
            familia_sel = st.selectbox(
                "📂 Familia",
                ["Todas"] + list(familias.keys()),
                key="prod_familia"
            )
        with cB:
            tipo_sel = st.selectbox(
                "🏷️ Tipo de producto",
                ["Todos"] + list(tipos.keys()),
                key="prod_tipo"
            )

        st.markdown("### ↕️ Ordenar")

        # --------------------------
        # ↕️ Orden (solo nombre)
        # --------------------------
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            st.selectbox(
                "Campo",
                ["nombre"],
                index=0,
                key="prod_sort_field_disabled",
                disabled=True,
            )
        with col_o2:
            sort_dir = st.radio(
                "Dirección",
                ["ASC", "DESC"],
                index=0 if "ASC" in st.session_state.get("prod_sort", "nombre ASC") else 1,
                horizontal=True,
                key="prod_sort_dir"
            )

        # Set final sort
        st.session_state["prod_sort"] = f"nombre {sort_dir}"

        st.markdown("### 👁️ Vista")

        st.radio(
            "Mostrar como",
            ["Tarjetas", "Tabla"],
            horizontal=True,
            key="prod_view"
        )

    st.markdown("---")

    # ======================================================
    # 📊 QUERY PRINCIPAL
    # ======================================================
    total, productos = 0, []
    page_size_cards = 12
    page_size_table = 30

    try:
        # 1) Count
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

        # 2) Pagination
        per_page = page_size_cards if st.session_state["prod_view"] == "Tarjetas" else page_size_table
        start, end = _range(st.session_state.prod_page, per_page)

        # 3) Main query
        base = supabase.table("producto").select("*")

        if or_filter:
            base = base.or_(or_filter)

        if familia_sel != "Todas" and familia_sel in familias:
            base = base.eq("familia_productoid", familias[familia_sel])

        if tipo_sel != "Todos" and tipo_sel in tipos:
            base = base.eq("producto_tipoid", tipos[tipo_sel])

        # Orden único
        f, d = st.session_state["prod_sort"].split(" ")
        base = base.order(f, desc=(d.upper() == "DESC"))

        productos = base.range(start, end).execute().data or []

    except Exception as e:
        st.error(f"❌ Error cargando productos: {e}")
        return

    # ======================================================
    # 🔢 PAGINACIÓN
    # ======================================================
    total_pages = max(1, math.ceil(total / per_page))
    st.caption(f"Página {st.session_state.prod_page}/{total_pages} · Total: {total}")

    p1, p2, p3 = st.columns(3)
    with p1:
        if st.button("⬅️ Anterior", disabled=st.session_state.prod_page <= 1):
            st.session_state.prod_page -= 1
            st.rerun()
    with p2:
        st.write(" ")
    with p3:
        if st.button("Siguiente ➡️", disabled=st.session_state.prod_page >= total_pages):
            st.session_state.prod_page += 1
            st.rerun()

    st.markdown("---")

    # ======================================================
    # 🧾 RENDER RESULTADOS
    # ======================================================
    if not productos:
        st.info("📭 No hay productos que coincidan con los filtros.")
        return

    if st.session_state.get("prod_view") == "Tarjetas":
        cols = st.columns(3)
        for i, p in enumerate(productos):
            with cols[i % 3]:
                _render_card_producto(p, supabase)
    else:
        _render_tabla_productos(productos)

    # ======================================================
    # (EL MODAL YA ESTÁ ARRIBA — NO SE RENDERIZA AQUÍ)
    # ======================================================

# ======================================================
# 🟪 TABLA (vista alternativa)
# ======================================================
def _render_tabla_productos(productos):
    rows = []
    for p in productos:
        rows.append({
            "ID": p.get("productoid"),
            "Nombre": p.get("nombre"),
            "Título": p.get("titulo"),
            "Referencia": p.get("referencia"),
            "Precio": p.get("precio_generico"),
            "Fecha publicación": p.get("fecha_publicacion"),
            "Publico": p.get("publico"),
            "Portada": p.get("portada_url"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    buff = io.StringIO()
    df.to_csv(buff, index=False)
    st.download_button(
        "⬇️ Exportar CSV",
        buff.getvalue(),
        file_name=f"productos_{date.today()}.csv",
        mime="text/csv",
    )
