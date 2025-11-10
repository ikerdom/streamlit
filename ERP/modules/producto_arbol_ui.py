# ======================================================
# 🌳 VISTA JERÁRQUICA DE PRODUCTOS — EnteNova Gnosis · ERP Orbe
# ======================================================
import streamlit as st
from typing import List, Dict, Any
from modules.orbe_theme import apply_orbe_theme

# ======================================================
# 🌳 VISTA JERÁRQUICA DE PRODUCTOS — EnteNova Gnosis · ERP Orbe
# ======================================================
import streamlit as st
from typing import List, Dict, Any
from modules.orbe_theme import apply_orbe_theme


# ======================================================
# 🧩 FUNCIÓN PRINCIPAL
# ======================================================
def render_arbol_productos(supabase):
    apply_orbe_theme()

    st.subheader("🌳 Catálogo de productos (Vista Árbol)")
    st.caption("Explora las familias y subfamilias. Abre, filtra o crea nuevos productos fácilmente.")

    # 🔍 Buscador global
    q_global = st.text_input("🔎 Buscar familia o producto", placeholder="Ej: Libros, Cuadernos, Accesorios…").strip().lower()

    try:
        familias = (
            supabase.table("producto_categoria_arbol")
            .select("categoria_arbolid, nombre, padreid, nivel, tipo, habilitado")
            .eq("habilitado", True)
            .order("nivel, nombre")
            .execute()
            .data or []
        )

        productos: List[Dict[str, Any]] = (
            supabase.table("producto")
            .select("productoid, nombre, familia_productoid, precio_generico, portada_url, publico")
            .eq("publico", True)
            .order("nombre")
            .execute()
            .data or []
        )

    except Exception as e:
        st.error(f"❌ Error cargando datos del árbol: {e}")
        return

    if not familias and not productos:
        st.info("📭 No hay familias ni productos registrados.")
        return

    # Construir jerarquía padre → hijos
    fam_hijos: Dict[int, List[Dict[str, Any]]] = {}
    for f in familias:
        fam_hijos.setdefault(f.get("padreid"), []).append(f)

    # ======================================================
    # 🔁 RENDER RECURSIVO DE FAMILIAS Y SUBFAMILIAS
    # ======================================================
    def render_familia(f: Dict[str, Any]):
        fid = f["categoria_arbolid"]
        nombre = f["nombre"]
        hijos_prod = [p for p in productos if p.get("familia_productoid") == fid]
        subfams = fam_hijos.get(fid, [])

        # Filtrado global (si no coincide, oculta)
        if q_global and q_global not in nombre.lower() and not any(q_global in p.get("nombre", "").lower() for p in hijos_prod):
            return

        with st.expander(f"📂 {nombre} ({len(hijos_prod)} producto(s))", expanded=False):
            # Botones superiores compactos
            cols = st.columns([1, 1])
            with cols[0]:
                if st.button("🎯 Filtrar en catálogo", key=f"filter_{fid}", use_container_width=True):
                    st.session_state["_pending_filter_from_tree"] = nombre
                    st.session_state["_go_catalog"] = True
                    st.rerun()
            with cols[1]:
                if st.button("➕ Nuevo producto", key=f"new_{fid}", use_container_width=True):
                    st.session_state["producto_editar_id"] = None
                    st.session_state["producto_show_form"] = True
                    st.session_state["show_producto_modal"] = False
                    st.session_state["prefill_familia_productoid"] = fid
                    st.session_state["_go_catalog"] = True
                    st.rerun()

            st.markdown("<hr style='margin:8px 0;border-color:#e5e7eb;'>", unsafe_allow_html=True)

            # Buscador local
            if hijos_prod:
                q_local = st.text_input("Buscar en esta familia", key=f"q_{fid}").strip().lower()
            else:
                q_local = ""

            # Productos
            for p in hijos_prod:
                if q_local and q_local not in p.get("nombre", "").lower():
                    continue
                _render_producto_card(p)

            # Subfamilias (recursivo)
            for sub in subfams:
                render_familia(sub)

    # Renderizar solo las familias raíz (padreid=None)
    for raiz in fam_hijos.get(None, []):
        render_familia(raiz)

    st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
    if st.button("⬅️ Volver al catálogo", key="volver_catalogo_btn", use_container_width=True):
        st.session_state["modo_producto"] = "Catálogo"
        st.rerun()


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
            <div style="flex:1;">
                <div style="font-weight:600;color:#064e3b;">{nombre}</div>
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

def _build_arbol(familias: List[Dict[str, Any]], productos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    mapa_fam = {f["familia_productoid"]: {"id": f["familia_productoid"], "nombre": f["nombre"], "productos": []} for f in familias}

    for p in productos:
        fid = p.get("familia_productoid")
        if fid in mapa_fam:
            mapa_fam[fid]["productos"].append(p)
        else:
            mapa_fam.setdefault(0, {"id": 0, "nombre": "Sin familia", "productos": []})["productos"].append(p)

    return list(mapa_fam.values())

