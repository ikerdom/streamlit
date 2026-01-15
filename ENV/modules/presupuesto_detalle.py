# modules/presupuesto_detalle.py
import pandas as pd
from datetime import datetime, date
import requests
import streamlit as st

from modules.presupuesto_api import (
    agregar_linea,
    listar_lineas,
    recalcular_lineas as api_recalcular_lineas,
)
from modules.presupuesto_api import _base_url


def _productos_options():
    """Carga productos vía API de productos (paginado amplio)."""
    try:
        r = requests.get(
            f"{_base_url()}/api/productos",
            params={"page": 1, "page_size": 200, "sort_field": "nombre"},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        return data
    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar productos: {e}")
        return []


def añadir_linea_presupuesto(presupuestoid: int):
    """Alta de línea usando la API (pricing en backend)."""
    st.subheader("➕ Añadir línea al presupuesto")

    productos = _productos_options()
    nombres = [p.get("nombre") for p in productos]

    producto_sel = st.selectbox("Producto", ["(selecciona)"] + nombres)
    if producto_sel == "(selecciona)":
        return

    prod = next((p for p in productos if p.get("nombre") == producto_sel), None)
    if not prod:
        st.warning("Producto no encontrado.")
        return

    col1, col2 = st.columns(2)
    with col1:
        cantidad = st.number_input("Cantidad", min_value=1, step=1, value=1)
    with col2:
        descuento_manual = st.number_input("Descuento (%)", min_value=0.0, step=0.5, value=0.0)

    if st.button("💾 Añadir línea", use_container_width=True):
        try:
            payload = {
                "productoid": int(prod["productoid"]),
                "cantidad": float(cantidad),
                "descripcion": prod.get("nombre"),
            }
            if descuento_manual > 0:
                payload["descuento_pct"] = float(descuento_manual)

            agregar_linea(presupuestoid, payload)
            st.success(f"✅ Línea añadida: {cantidad} × {prod['nombre']}")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error añadiendo línea: {e}")


def render_presupuesto_detalle(presupuestoid: int, bloqueado: bool = False):
    """
    📦 Muestra las líneas del presupuesto usando la API y permite altas si está editable.
    """
    st.subheader("📦 Detalle de productos del presupuesto")

    try:
        lineas = listar_lineas(presupuestoid)
    except Exception as e:
        st.error(f"❌ Error cargando líneas del presupuesto: {e}")
        return

    if not lineas:
        st.info("ℹ️ No hay líneas en este presupuesto todavía.")
    else:
        df = pd.DataFrame(lineas)
        df.rename(
            columns={
                "descripcion": "Descripción",
                "cantidad": "Cantidad",
                "precio_unitario": "P. Unit (€)",
                "descuento_pct": "Dto (%)",
                "iva_pct": "IVA (%)",
                "importe_base": "Base (€)",
                "importe_total_linea": "Total línea (€)",
                "tarifa_aplicada": "Tarifa",
                "nivel_tarifa": "Jerarquía",
            },
            inplace=True,
        )
        df["P. Unit (€)"] = df["P. Unit (€)"].map(lambda x: f"{x:,.2f} €" if x is not None else "-")
        df["Base (€)"] = df["Base (€)"].map(lambda x: f"{x:,.2f} €" if x is not None else "-")
        df["Total línea (€)"] = df["Total línea (€)"].map(lambda x: f"{x:,.2f} €" if x is not None else "-")
        st.dataframe(df, use_container_width=True, hide_index=True)

        total_base = sum([float(r.get("importe_base") or 0) for r in lineas])
        total_iva = sum([(float(r.get("importe_base") or 0) * float(r.get("iva_pct") or 0) / 100) for r in lineas])
        total_total = total_base + total_iva

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Base imponible (€)", f"{total_base:,.2f}")
        c2.metric("IVA / IGIC (€)", f"{total_iva:,.2f}")
        c3.metric("Total presupuesto (€)", f"{total_total:,.2f}")

    st.divider()

    if bloqueado:
        st.info("🔒 Este presupuesto está bloqueado y no permite añadir ni modificar líneas.")
        return

    añadir_linea_presupuesto(presupuestoid)


def recalcular_lineas_presupuesto(presupuestoid: int, fecha_calculo: date | None = None):
    """Recalcula todas las líneas vía API backend."""
    try:
        resp = api_recalcular_lineas(presupuestoid, fecha_calculo)
        st.success(f"✅ Líneas recalculadas ({resp.get('fecha_recalculo')})")
    except Exception as e:
        st.error(f"❌ Error al recalcular líneas: {e}")
