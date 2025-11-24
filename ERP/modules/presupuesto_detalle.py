# modules/presupuesto_detalle.py
import pandas as pd
from datetime import datetime
import streamlit as st
from modules.precio_engine import calcular_precio_linea

# =========================
# Recalcular total en cabecera (simple)
# =========================
def actualizar_total_presupuesto(supabase, presupuestoid: int):
    """Recalcula total_estimada sumando líneas y actualiza la cabecera (y totales si existen)."""
    try:
        lineas = (
            supabase.table("presupuesto_detalle")
            .select("importe_total_linea")
            .eq("presupuestoid", presupuestoid)
            .execute()
            .data or []
        )
        total = round(sum(float(l["importe_total_linea"] or 0) for l in lineas), 2)
        supabase.table("presupuesto").update({"total_estimada": total}).eq("presupuestoid", presupuestoid).execute()
    except Exception as e:
        st.warning(f"⚠️ No se pudo recalcular el total del presupuesto: {e}")

def añadir_linea_presupuesto(supabase, presupuestoid: int, clienteid: int, fecha_validez: str | None):
    """
    Permite añadir una nueva línea al presupuesto seleccionando producto y cantidad.
    Usa el motor de tarifas con la fecha de validez (si viene; si no, hoy).
    """
    st.subheader("➕ Añadir línea al presupuesto")

    productos = (
        supabase.table("producto")
        .select("productoid, nombre, precio_generico, familia_productoid")
        .order("nombre")
        .execute()
        .data or []
    )

    nombres = [p["nombre"] for p in productos]
    producto_sel = st.selectbox("Producto", ["(selecciona)"] + nombres)
    if producto_sel == "(selecciona)":
        return

    prod = next((p for p in productos if p["nombre"] == producto_sel), None)
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
            # ⚠️ Convertir fecha_validez (str) a date si llega como string
            if isinstance(fecha_validez, str):
                try:
                    from datetime import date as _date
                    fecha_calc = _date.fromisoformat(fecha_validez)
                except Exception:
                    fecha_calc = datetime.now().date()
            else:
                fecha_calc = fecha_validez or datetime.now().date()

            from modules.precio_engine import calcular_precio_linea
            precio_linea = calcular_precio_linea(
                supabase=supabase,
                clienteid=clienteid,
                productoid=prod["productoid"],
                cantidad=float(cantidad),
                fecha=fecha_calc,     # ← date object
            )
            st.warning(precio_linea)  # DEBUG TEMPORAL


            unit_bruto = float(precio_linea.get("unit_bruto", prod.get("precio_generico", 0.0)))
            dto_motor  = float(precio_linea.get("descuento_pct", 0.0))
            iva_pct    = float(precio_linea.get("iva_pct", 21.0))

            # Si el usuario mete dto manual, sustituye al del motor
            dto_final = descuento_manual if descuento_manual > 0 else dto_motor

            # Base/total desde engine (y si hay dto manual, recalculamos base/total respetando IVA del engine)
            if descuento_manual > 0:
                base   = round(float(cantidad) * unit_bruto * (1 - dto_final/100.0), 2)
                total  = round(base * (1 + iva_pct/100.0), 2)
            else:
                base   = float(precio_linea.get("subtotal_sin_iva", float(cantidad) * unit_bruto * (1 - dto_final/100.0)))
                total  = float(precio_linea.get("total_con_iva",   base * (1 + iva_pct/100.0)))

            linea = {
                "presupuestoid": presupuestoid,
                "productoid": prod["productoid"],
                "descripcion": prod["nombre"],
                "cantidad": float(cantidad),
                "precio_unitario": unit_bruto,
                "descuento_pct": dto_final,
                "iva_pct": iva_pct,
                "importe_base": base,
                "importe_total_linea": total,
                "fecha_alta": datetime.now().isoformat(),
                "tarifa_aplicada": precio_linea.get("tarifa_aplicada"),
                "nivel_tarifa": precio_linea.get("nivel_tarifa"),
                "iva_origen": precio_linea.get("iva_origen"),
            }
            supabase.table("presupuesto_detalle").insert(linea).execute()

            actualizar_total_presupuesto(supabase, presupuestoid)

            st.success(f"✅ Línea añadida: {cantidad} × {prod['nombre']}")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error añadiendo línea: {e}")
# =========================
# Detalle (tabla + alta)
# =========================
def render_presupuesto_detalle(supabase, presupuestoid: int, clienteid: int = None, fecha_validez: str | None = None, bloqueado: bool = False):
    """
    📦 Muestra las líneas del presupuesto + permite añadir nuevas con motor de tarifas.
    - Carga las líneas y calcula totales (base + IVA + total).
    - Integra el motor de precios usando la fecha de validez del presupuesto.
    """
    st.subheader("📦 Detalle de productos del presupuesto")

    # Cargar líneas
    try:
        res = (
            supabase.table("presupuesto_detalle")
            .select("presupuesto_detalleid, productoid, descripcion, cantidad, precio_unitario, descuento_pct, iva_pct, importe_base, importe_total_linea, tarifa_aplicada, nivel_tarifa")
            .eq("presupuestoid", presupuestoid)
            .order("presupuesto_detalleid", desc=False)
            .execute()
        )
        lineas = res.data or []
    except Exception as e:
        st.error(f"❌ Error cargando líneas del presupuesto: {e}")
        return

    # Tabla
    if not lineas:
        st.info("📭 No hay líneas en este presupuesto todavía.")
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

        # Totales
        total_base = sum([float(r.get("importe_base") or 0) for r in lineas])
        total_iva = sum([(float(r.get("importe_base") or 0) * float(r.get("iva_pct") or 0) / 100) for r in lineas])
        total_total = total_base + total_iva

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Base imponible (€)", f"{total_base:,.2f}")
        c2.metric("IVA / IGIC (€)", f"{total_iva:,.2f}")
        c3.metric("Total presupuesto (€)", f"{total_total:,.2f}")

        # Guardar total en cabecera
        try:
            supabase.table("presupuesto").update({"total_estimada": total_total}).eq("presupuestoid", presupuestoid).execute()
        except Exception:
            pass

    st.divider()

    # Alta rápida
    if bloqueado:
        st.info("🔒 Este presupuesto está bloqueado y no permite añadir ni modificar líneas.")
        return

    if not clienteid:
        st.info("ℹ️ Asigna un cliente en la cabecera para poder añadir líneas con tarifas.")
        return

    añadir_linea_presupuesto(supabase, presupuestoid, clienteid, fecha_validez)
from datetime import datetime
from modules.precio_engine import calcular_precio_linea

def recalcular_lineas_presupuesto(supabase, presupuestoid: int):
    """
    🔄 Recalcula las líneas del presupuesto aplicando la lógica de precios y tarifas.
    Guarda los nuevos valores (unitario, dto, iva, totales) en presupuesto_detalle y totales globales.
    """
    try:
        pres = (
            supabase.table("presupuesto")
            .select("clienteid, fecha_presupuesto")
            .eq("presupuestoid", presupuestoid)
            .single()
            .execute()
            .data
        )
        if not pres:
            st.error("❌ Presupuesto no encontrado.")
            return

        lineas = (
            supabase.table("presupuesto_detalle")
            .select("presupuesto_detalleid, productoid, cantidad")
            .eq("presupuestoid", presupuestoid)
            .execute()
            .data or []
        )
        if not lineas:
            st.warning("ℹ️ No hay líneas en el presupuesto.")
            return

        clienteid = pres["clienteid"]
        fecha = datetime.fromisoformat(pres.get("fecha_presupuesto") or datetime.now().isoformat()).date()

        total_base = total_iva = total_total = 0.0

        for ln in lineas:
            r = calcular_precio_linea(
                supabase,
                clienteid=clienteid,
                productoid=ln["productoid"],
                cantidad=ln.get("cantidad", 1),
                fecha=fecha,
            )

            base = float(r["subtotal_sin_iva"])
            iva = float(r["iva_importe"])
            total = float(r["total_con_iva"])

            supabase.table("presupuesto_detalle").update({
                "precio_unitario": r["unit_bruto"],
                "descuento_pct": r["descuento_pct"],
                "iva_pct": r["iva_pct"],
                "importe_base": base,
                "importe_total_linea": total,
                "tarifa_aplicada": r.get("tarifa_aplicada"),
                "nivel_tarifa": r.get("nivel_tarifa"),
            }).eq("presupuesto_detalleid", ln["presupuesto_detalleid"]).execute()

            total_base += base
            total_iva += iva
            total_total += total

        supabase.table("presupuesto_totales").upsert({
            "presupuestoid": presupuestoid,
            "base_imponible": round(total_base, 2),
            "iva_total": round(total_iva, 2),
            "total_presupuesto": round(total_total, 2),
            "fecha_recalculo": datetime.now().isoformat(),
        }).execute()

        st.success(f"✅ Líneas recalculadas ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    except Exception as e:
        st.error(f"❌ Error al recalcular líneas: {e}")
