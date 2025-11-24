import streamlit as st
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

# ======================================================
# 🌳 MODELO DEL ÁRBOL DE PRODUCTOS
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
# 📦 CARGA DE ÁRBOL (corregido: _supabase)
# ======================================================
@st.cache_data(ttl=300)
def load_arbol_productos(_supabase) -> List[NodoCategoria]:
    """Carga la jerarquía desde producto_categoria_arbol."""
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

        nodos = {r["categoria_arbolid"]: NodoCategoria(
            id=r["categoria_arbolid"],
            nombre=r["nombre"],
            tipo=r.get("tipo", ""),
            nivel=r.get("nivel", 1),
            refid=r.get("refid"),
            padreid=r.get("padreid"),
            hijos=[]
        ) for r in rows}

        # Conectar hijos con padres
        for nodo in nodos.values():
            if nodo.padreid and nodo.padreid in nodos:
                nodos[nodo.padreid].hijos.append(nodo)

        # Solo raíces
        return [n for n in nodos.values() if not n.padreid]
    except Exception as e:
        st.error(f"❌ Error cargando árbol: {e}")
        return []


# ======================================================
# 🔍 BUSCAR NODO POR NOMBRE
# ======================================================

def buscar_nodo_por_nombre(nodos: List[NodoCategoria], nombre: str) -> Optional[NodoCategoria]:
    """Busca un nodo en el árbol por nombre."""
    for nodo in nodos:
        if nodo.nombre.lower() == nombre.lower():
            return nodo
        encontrado = buscar_nodo_por_nombre(nodo.hijos, nombre)
        if encontrado:
            return encontrado
    return None
