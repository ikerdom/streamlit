# ======================================================
# 🌳 VISTA JERÁRQUICA DE PRODUCTOS — EnteNova Gnosis · ERP Orbe
# ======================================================
import streamlit as st
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from modules.orbe_theme import apply_orbe_theme


# ======================================================
# 📦 MODELO DEL NODO DE CATEGORÍA
# ======================================================
@dataclass
class NodoCategoria:
    id: int
    nombre: str
    tipo: str
    nivel: int
    refid: Optional[int] = None
    padreid: Optional[int] = None
    hijos: List["NodoCategoria"] = field(default_factory=list)


# ======================================================
# 📥 CARGA DEL ÁRBOL DE CATEGORÍAS  (FIX: _supabase)
# ======================================================
@st.cache_data(ttl=300)
def load_arbol_productos(_supabase) -> List[NodoCategoria]:
    """
    Carga la jerarquía de producto_categoria_arbol y devuelve una lista
    de nodos raíz con hijos conectados.
    """
    try:
        res = (
            _supabase.table("producto_categoria_arbol")
            .select("categoria_arbolid, nombre, tipo, nivel, padreid, refid, habilitado")
            .eq("habilitado", True)
            .order("nivel, nombre")
            .execute()
        )
        rows = res.data or []
        if not rows:
            return []

        nodos: Dict[int, NodoCategoria] = {
            r["categoria_arbolid"]: NodoCategoria(
                id=r["categoria_arbolid"],
                nombre=r["nombre"],
                tipo=r.get("tipo") or "",
                nivel=r.get("nivel") or 1,
                padreid=r.get("padreid"),
                refid=r.get("refid"),
            )
            for r in rows
        }

        # Conectar padres ↔ hijos
        for nodo in nodos.values():
            if nodo.padreid and nodo.padreid in nodos:
                nodos[nodo.padreid].hijos.append(nodo)

        return [n for n in nodos.values() if not n.padreid]

    except Exception as e:
        st.error(f"❌ Error cargando árbol de categorías: {e}")
        return []


# ======================================================
# 💳 TARJETA DE PRODUCTO (compacta)
# ======================================================
def _render_producto_card(p: Dict[str, Any]):
    nombre = p.get("nombre", "(Producto)")
    portada = p.get("portada_url") or ""
    precio = p.get("precio_generico")
    precio_str = f"{float(precio):.2f} €" if isinstance(precio, (int, float)) else "-"
    pid = p.get("productoid")

    st.markdown(
        f"""
        <div style="border:1px solid #e5e7eb;background:#f9fafb;border-radius:8px;
                    padding:6px 10px;margin-bottom:4px;display:flex;align-items:center;gap:10px;">
            <div style="width:46px;height:60px;border:1px solid #ddd;border-radius:6px;overflow:hidden;">
                {'<img src="'+portada+'" style="width:100%;height:100%;object-fit:cover;" />' if portada else '📘'}
            </div>
            <div style="flex:1;min-width:0;">
                <div style="font-weight:600;color:#064e3b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    {nombre}
                </div>
                <div style="opacity:.7;font-size:0.9rem;">💶 {precio_str}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("📄 Ficha", key=f"arbol_ficha_{pid}", use_container_width=True):
        st.session_state["producto_modal_id"] = pid
        st.session_state["show_producto_modal"] = True
        st.session_state["_go_catalog"] = True
        st.rerun()


# ======================================================
# 🌳 FUNCIÓN PRINCIPAL — VISTA ÁRBOL
# ======================================================
def render_arbol_productos(supabase):
    apply_orbe_theme()

    st.subheader("🌳 Catálogo de productos — Vista Árbol")
    st.caption("Navega por CATEGORÍAS, luego por FAMILIAS y finalmente por PRODUCTOS.")

    q_global = st.text_input(
        "🔎 Buscar categoría o producto",
        placeholder="Ej: Hosteleria y Turismo, Comercio y Marketing, Celador…"
    ).strip().lower()

    # -----------------------------
    # CARGA DE DATOS
    # -----------------------------
    try:
        raices = load_arbol_productos(supabase)

        productos = (
            supabase.table("producto")
            .select(
                "productoid, nombre, categoriaid, familia_productoid, "
                "precio_generico, portada_url, publico"
            )
            .eq("publico", True)
            .order("nombre")
            .execute()
            .data or []
        )

        familias_rows = (
            supabase.table("producto_familia")
            .select("familia_productoid, nombre, habilitado")
            .eq("habilitado", True)
            .order("nombre")
            .execute()
            .data or []
        )
        familias_map = {f["familia_productoid"]: f["nombre"] for f in familias_rows}

    except Exception as e:
        st.error(f"❌ Error cargando datos del árbol: {e}")
        return

    if not raices:
        st.info("📭 No hay categorías registradas.")
        return

    # -----------------------------
    # HELPERS
    # -----------------------------
    def productos_de_categoria(cat_id: int):
        return [p for p in productos if p.get("categoriaid") == cat_id]

    def nodo_tiene_match(nodo: NodoCategoria) -> bool:
        if not q_global:
            return True

        if q_global in nodo.nombre.lower():
            return True

        for p in productos_de_categoria(nodo.id):
            if q_global in p.get("nombre", "").lower():
                return True

        return any(nodo_tiene_match(h) for h in nodo.hijos)

    # -----------------------------
    # RENDER RECURSIVO
    # -----------------------------
    def render_nodo(nodo: NodoCategoria):
        if not nodo_tiene_match(nodo):
            return

        prods_cat = productos_de_categoria(nodo.id)

        fam_contador = {}
        for p in prods_cat:
            fid = p.get("familia_productoid")
            if fid:
                fam_contador[fid] = fam_contador.get(fid, 0) + 1

        titulo = f"📂 {nodo.nombre}"
        if prods_cat:
            titulo += f" — {len(prods_cat)} producto(s)"

        with st.expander(titulo, expanded=False):

            # ================================
            # FAMILIAS
            # ================================
            if fam_contador:
                st.markdown("### 📁 Familias en esta categoría")

                for fid, count in sorted(
                    fam_contador.items(),
                    key=lambda x: (familias_map.get(x[0], "") or "").lower()
                ):
                    fam_nombre = familias_map.get(fid, f"Familia {fid}")

                    c1, c2 = st.columns([3, 2])
                    with c1:
                        st.write(f"• **{fam_nombre}** ({count} producto(s))")

                    # 🎯 Ver catálogo filtrado por esta familia
                    with c2:
                        if st.button(
                            "🎯 Ver catálogo",
                            key=f"ver_cat_{nodo.id}_{fid}",
                            use_container_width=True,
                        ):
                            st.session_state["_pending_filter_from_tree"] = fam_nombre
                            st.session_state["_go_catalog"] = True
                            st.rerun()

                st.markdown("---")

            # ================================
            # PRODUCTOS DE LA CATEGORÍA
            # ================================
            if prods_cat:
                q_local = st.text_input(
                    "Buscar productos en esta categoría",
                    key=f"q_cat_{nodo.id}"
                ).strip().lower()

                for p in prods_cat:
                    if q_local and q_local not in p.get("nombre", "").lower():
                        continue
                    _render_producto_card(p)

            # ================================
            # SUBCATEGORÍAS
            # ================================
            if nodo.hijos:
                st.markdown("### 🌿 Subcategorías")
                for h in nodo.hijos:
                    render_nodo(h)

    # -----------------------------
    # RENDER DE RAÍCES
    # -----------------------------
    for raiz in raices:
        render_nodo(raiz)

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("⬅️ Volver al catálogo", key="volver_catalogo_arbol", use_container_width=True):
        st.session_state["modo_producto"] = "Catálogo"
        st.rerun()
