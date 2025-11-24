# ======================================================
# 📦 Catálogo de productos — EnteNova Gnosis · ERP Orbe
# ======================================================
import io
import math
import pandas as pd
import streamlit as st
from datetime import date

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
from modules.producto_form import render_producto_form
from modules.producto_arbol_ui import render_arbol_productos


# ======================================================
# ⚙️ UTILIDADES
# ======================================================
def _safe(val, default="-"):
    return val if val not in (None, "", "null") else default


def _range(page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size - 1
    return start, end


def _build_search_or(s, fields=("nombre", "titulo", "referencia", "isbn", "ean")):
    s = (s or "").strip()
    if not s:
        return None
    return ",".join([f"{f}.ilike.%{s}%" for f in fields])

def _safe_catalog(loader, supabase):
    try:
        data = loader(supabase)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        st.warning(f"⚠️ Catálogo no disponible: {e}")
        return {}


# ======================================================
# 🧱 VISTA PRINCIPAL — CATÁLOGO DE PRODUCTOS
# ======================================================
def render_producto_lista(supabase):
    from modules.orbe_theme import apply_orbe_theme
    apply_orbe_theme()

    st.header("📦 Catálogo de productos")
    st.caption("Busca, filtra y gestiona el catálogo. Cambia a vista en árbol para navegar por familias y productos.")

    # Guardamos supabase para helpers
    st.session_state["_supabase_for_helpers"] = supabase

    # ---- Estado de sesión
    st.session_state.setdefault("prod_page", 1)
    st.session_state.setdefault("prod_view", "Tarjetas")
    st.session_state.setdefault("prod_sort", "nombre ASC")
    st.session_state.setdefault("producto_show_form", False)
    st.session_state.setdefault("producto_editar_id", None)
    st.session_state.setdefault("show_producto_modal", False)
    st.session_state.setdefault("producto_modal_id", None)
    st.session_state.setdefault("confirm_delete_producto", False)
    st.session_state.setdefault("modo_producto", "Catálogo")

    # Volver al catálogo desde otras vistas
    if st.session_state.get("_go_catalog"):
        st.session_state["modo_producto"] = "Catálogo"
        st.session_state["_go_catalog"] = False
        st.rerun()

    # ---- Selector de modo
    modo = st.radio("Modo", ["Catálogo", "Árbol"], horizontal=True, key="modo_producto")

    # =====================================================
    # 🌳 MODO ÁRBOL
    # =====================================================
    if modo == "Árbol":
        render_arbol_productos(supabase)
        st.markdown("---")
        if st.button("⬅️ Volver al catálogo", key="volver_catalogo_lista", use_container_width=True):
            st.session_state["modo_producto"] = "Catálogo"
            st.rerun()

        return

    # =====================================================
    # 🛒 MODO CATÁLOGO
    # =====================================================
    familias, tipos, impuestos, estados = {}, {}, {}, {}
    familias = _safe_catalog(load_familias, supabase)
    tipos = _safe_catalog(load_tipos_producto, supabase)
    impuestos = _safe_catalog(load_impuestos, supabase)
    estados = _safe_catalog(load_estados_producto, supabase)


    # Filtro heredado del árbol
    if st.session_state.get("_pending_filter_from_tree"):
        target = st.session_state["_pending_filter_from_tree"]
        if target in familias:
            st.session_state["prod_familia"] = target
        st.session_state["_pending_filter_from_tree"] = None

    # ------------------------------
    # 🎛️ FILTROS
    # ------------------------------
    # 🔍 Primera fila: búsqueda, familia, tipo
    c1, c2, c3 = st.columns([2.5, 2, 2])
    with c1:
        q = st.text_input("🔎 Buscar", placeholder="Nombre, título, referencia, ISBN, EAN…", key="prod_q")
    with c2:
        familia_sel = st.selectbox("📂 Familia", ["Todas"] + list(familias.keys()), key="prod_familia")
    with c3:
        tipo_sel = st.selectbox("🏷️ Tipo", ["Todos"] + list(tipos.keys()), key="prod_tipo")
    # ❌ Eliminamos completamente el expander de filtros avanzados
    # (ya no lo necesitamos y no aporta nada)
    # ❌ Eliminamos completamente el expander de filtros avanzados
    # (ya no lo necesitamos y no aporta nada)

    st.divider()

    # 🔄 Nueva fila para usar 'c4' y evitar errores
    c4, _ = st.columns([1, 5])
    with c4:
        view = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, key="prod_view")

    # ------------------------------
    # 🎛️ Filtros principales (limpios)
    # ------------------------------
    c5, c6, c7 = st.columns([2, 2, 2])

    with c5:
        estado_sel = st.selectbox("Estado", ["Todos"] + list(estados.keys()), key="prod_estado")

    with c6:
        ordenar = st.selectbox(
            "Ordenar por",
            [
                "nombre ASC", "nombre DESC",
                "fecha_publicacion DESC", "fecha_publicacion ASC",
                "precio_generico DESC", "precio_generico ASC",
            ],
            key="prod_sort",
        )

    with c7:
        # Eliminado el botón de nuevo producto
        st.write("")

    st.markdown("---")

    # ------------------------------
    # 📊 QUERY PRINCIPAL
    # ------------------------------
    total, productos = 0, []
    page_size_cards, page_size_table = 12, 30

    try:
        base_count = supabase.table("producto").select("productoid", count="exact")

        or_filter = _build_search_or(q)
        if or_filter:
            base_count = base_count.or_(or_filter)

        if familia_sel != "Todas" and familia_sel in familias:
            base_count = base_count.eq("familia_productoid", familias[familia_sel])
        if tipo_sel != "Todos" and tipo_sel in tipos:
            base_count = base_count.eq("producto_tipoid", tipos[tipo_sel])
        if estado_sel != "Todos" and estado_sel in estados:
            base_count = base_count.eq("estado_productoid", estados[estado_sel])

        cres = base_count.execute()
        total = getattr(cres, "count", None) or len(cres.data or [])

        per_page = page_size_cards if view == "Tarjetas" else page_size_table
        start, end = _range(st.session_state.prod_page, per_page)

        base = supabase.table("producto").select("*")
        if or_filter:
            base = base.or_(or_filter)
        if familia_sel != "Todas" and familia_sel in familias:
            base = base.eq("familia_productoid", familias[familia_sel])
        if tipo_sel != "Todos" and tipo_sel in tipos:
            base = base.eq("producto_tipoid", tipos[tipo_sel])
        if estado_sel != "Todos" and estado_sel in estados:
            base = base.eq("estado_productoid", estados[estado_sel])

        if " " in ordenar:
            f, d = ordenar.split(" ")
            base = base.order(f, desc=(d.upper() == "DESC"))

        productos = (base.range(start, end).execute().data or [])

    except Exception as e:
        st.error(f"❌ Error cargando productos: {e}")

    # ------------------------------
    # 📑 PAGINACIÓN
    # ------------------------------
    total_pages = max(1, math.ceil(total / (page_size_cards if view == "Tarjetas" else page_size_table)))
    st.caption(f"Mostrando página {st.session_state.prod_page} de {total_pages} — Total: {total} productos")

    p1, p2, p3, _ = st.columns([1, 1, 1, 5])
    if p1.button("⏮️", disabled=st.session_state.prod_page <= 1):
        st.session_state.prod_page = 1
        st.rerun()
    if p2.button("◀️", disabled=st.session_state.prod_page <= 1):
        st.session_state.prod_page -= 1
        st.rerun()
    if p3.button("▶️", disabled=st.session_state.prod_page >= total_pages):
        st.session_state.prod_page += 1
        st.rerun()

    st.markdown("---")

    # ------------------------------
    # 🧾 RENDER RESULTADOS
    # ------------------------------
    if not productos:
        st.info("📭 No hay productos que coincidan con los filtros.")
        return

    if view == "Tarjetas":
        cols = st.columns(3)
        for i, p in enumerate(productos):
            with cols[i % 3]:
                _render_card_producto(p, supabase)
    else:
        _render_tabla_productos(productos)

    # ------------------------------
    # 🧩 MODAL FICHA / EDICIÓN
    # ------------------------------
    if st.session_state.get("show_producto_modal"):
        render_producto_modal(supabase)

def _render_card_producto(p, supabase):
    from modules.producto_models import get_tipo_label, get_familia_label, get_estado_label

    nombre, titulo = _safe(p.get("nombre")), _safe(p.get("titulo"))
    precio = p.get("precio_generico")
    precio_str = f"{float(precio):.2f} €" if isinstance(precio, (int, float)) else "-"
    tipo_lbl = get_tipo_label(p.get("producto_tipoid"), supabase)
    familia_lbl = get_familia_label(p.get("familia_productoid"), supabase)
    estado_lbl = get_estado_label(p.get("estado_productoid"), supabase)
    portada = p.get("portada_url") or ""

    st.markdown(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:14px;padding:10px;background:#fafafa;">
            <div style="display:flex;gap:10px;">
                <div style="width:90px;height:120px;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
                    {'<img src="'+portada+'" style="width:100%;height:100%;object-fit:cover;" />' if portada else '📘'}
                </div>
                <div style="flex:1;">
                    <div style="font-weight:600;font-size:1.1rem;">{nombre}</div>
                    <div style="color:#666;">{titulo}</div>
                    <div style="margin-top:4px;">
                        💶 <b>{precio_str}</b> |
                        🏷️ {tipo_lbl} · {familia_lbl} |
                        ⚙️ {estado_lbl}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Botón único ancho: Ver ficha
    if st.button(
        "📄 Ver ficha",
        key=f"ficha_prod_{p['productoid']}",
        use_container_width=True
    ):
        st.session_state["producto_modal_id"] = p["productoid"]
        st.session_state["show_producto_modal"] = True
        st.rerun()


def _render_tabla_productos(productos):
    if not productos:
        st.info("No hay productos.")
        return

    supabase = st.session_state.get("_supabase_for_helpers")

    fam_map = load_familias(supabase) if supabase else {}
    tipo_map = load_tipos_producto(supabase) if supabase else {}
    imp_map = load_impuestos(supabase) if supabase else {}
    est_map = load_estados_producto(supabase) if supabase else {}

    def rev_lookup(d, vid):
        return next((k for k, v in d.items() if v == vid), "-")

    rows = []
    for p in productos:
        rows.append({
            "ID": p.get("productoid"),
            "Nombre": p.get("nombre"),
            "Título": p.get("titulo"),
            "Referencia": p.get("referencia"),
            "Precio (€)": p.get("precio_generico"),
            "Familia": rev_lookup(fam_map, p.get("familia_productoid")),
            "Tipo": rev_lookup(tipo_map, p.get("producto_tipoid")),
            "Estado": rev_lookup(est_map, p.get("estado_productoid")),
            "Impuesto": rev_lookup(imp_map, p.get("impuestoid")),
            "Público": p.get("publico"),
            "Fecha publicación": p.get("fecha_publicacion"),
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

def render_producto_modal(supabase):
    pid = st.session_state.get("producto_modal_id")
    if not pid:
        return

    st.markdown("---")
    st.markdown("### 📘 Ficha del producto")

    # Botón superior: solo cerrar ficha (sin eliminar)
    if st.button("⬅️ Cerrar ficha", key=f"close_modal_{pid}", use_container_width=True):
        st.session_state["show_producto_modal"] = False
        st.rerun()


    # Cargar datos
    try:
        p = supabase.table("producto").select("*").eq("productoid", pid).single().execute().data
    except Exception as e:
        st.error(f"❌ Error cargando producto: {e}")
        return

    tipo_lbl = get_tipo_label(p.get("producto_tipoid"), supabase)
    familia_lbl = get_familia_label(p.get("familia_productoid"), supabase)
    impuesto_lbl = get_impuesto_label(p.get("impuestoid"), supabase)
    estado_lbl = get_estado_label(p.get("estado_productoid"), supabase)

    # 🔎 Detalle (solo lectura mejorado)
    with st.expander("🔎 Detalle del producto", expanded=True):

        def field(label, value):
            """Renderiza un campo SOLO si tiene contenido."""
            if value not in (None, "", "null"):
                st.write(f"**{label}:** {value}")

        cols = st.columns([1, 2])

        # ------------------------
        # 📘 Columna izquierda
        # ------------------------
        with cols[0]:
            portada = p.get("portada_url")
            if portada:
                st.image(portada, use_container_width=True)

            # Precio
            if p.get("precio_generico") not in (None, "", 0):
                st.write("**💶 Precio:**", f"{float(p['precio_generico']):.2f} €")

            # Estado
            estado_lbl = get_estado_label(p.get("estado_productoid"), supabase)
            if estado_lbl and estado_lbl != "-":
                st.write("**⚙️ Estado:**", estado_lbl)

            # Fecha publicación
            if p.get("fecha_publicacion"):
                st.write("**📅 Publicación:**", p["fecha_publicacion"])

            # Público
            if p.get("publico") is not None:
                st.write("**👁️ Público:**", "Sí" if p["publico"] else "No")

        # ------------------------
        # 📄 Columna derecha
        # ------------------------
        with cols[1]:
            field("Nombre", p.get("nombre"))
            field("Título", p.get("titulo"))
            field("Referencia", p.get("referencia"))
            field("ISBN", p.get("isbn"))
            field("EAN", p.get("ean"))
            field("Familia", familia_lbl)
            field("Tipo", tipo_lbl)
            field("Cuerpo certificado", p.get("cuerpo_certificado"))

            # Autor(es)
            autores = p.get("autores")
            autores = autores if autores not in (None, "", "null") else "Sin autor"
            st.write(f"**Autor:** {autores}")

            field("Versatilidad", p.get("versatilidad"))

            # SINOPSIS → solo si existe
            if p.get("sinopsis") not in (None, "", "null"):
                st.markdown("**📝 Sinopsis:**")
                st.info(p["sinopsis"])

    # ⚙️ Ajustes rápidos (solo campos permitidos)
    st.markdown("---")
    st.subheader("⚙️ Ajustes rápidos")

    try:
        estados = load_estados_producto(supabase)  # {"Activo":1, ...}
    except Exception:
        estados = {}

    # Valor por defecto para el select de estado
    def _default_idx(d, val):
        if not d:
            return 0
        items = list(d.items())
        for i, (_, vid) in enumerate(items, start=1):
            if vid == val:
                return i
        return 0

    cA, cB = st.columns([2, 1])
    with cA:
        estado_sel = st.selectbox(
            "Estado",
            ["(sin estado)"] + list(estados.keys()),
            index=_default_idx(estados, p.get("estado_productoid")),
            key=f"estado_sel_{pid}"
        )
    with cB:
        publico_sel = st.checkbox("Visible al público", value=bool(p.get("publico", True)), key=f"publico_sel_{pid}")

    if st.button("💾 Guardar ajustes", key=f"quick_save_{pid}", use_container_width=True):
        payload = {
            "estado_productoid": estados.get(estado_sel),
            "publico": publico_sel
        }
        try:
            supabase.table("producto").update(payload).eq("productoid", pid).execute()
            st.toast("✅ Ajustes guardados.", icon="✅")
            # refrescar la ficha
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error guardando cambios: {e}")
