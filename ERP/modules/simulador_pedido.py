# ======================================================
# 🧮 SIMULADOR DE PRECIOS — EnteNova Gnosis
# ======================================================

import streamlit as st
import pandas as pd
from datetime import date
from modules.precio_engine import calcular_precio_linea


def render_simulador_pedido(supabase):
    st.header("🧮 Simulador de precios, tarifas e impuestos")
    st.caption("Comprueba cómo aplican las tarifas, jerarquías y el IVA según la combinación de cliente, grupo y producto.")

    st.markdown("---")

    # ======================================================
    # 🧾 Selección de cliente y producto
    # ======================================================
    col1, col2 = st.columns(2)

    with col1:
        try:
            clientes = (
                supabase.table("cliente")
                .select("clienteid, razon_social, grupoid")
                .order("razon_social")
                .execute()
                .data or []
            )
        except Exception as e:
            st.error(f"No se pudieron cargar clientes: {e}")
            clientes = []

        cli_map = {c["razon_social"]: c for c in clientes}
        cli_sel = st.selectbox("👤 Cliente", list(cli_map.keys()) or ["(sin clientes disponibles)"])
        cliente = cli_map.get(cli_sel)
        clienteid = cliente["clienteid"] if cliente else None

    with col2:
        try:
            productos = (
                supabase.table("producto")
                .select("productoid, nombre, precio_generico, familia_productoid, producto_tipoid")
                .order("nombre")
                .execute()
                .data or []
            )
        except Exception as e:
            st.error(f"No se pudieron cargar productos: {e}")
            productos = []

        prod_map = {p["nombre"]: p for p in productos}
        prod_sel = st.selectbox("📦 Producto", list(prod_map.keys()) or ["(sin productos disponibles)"])
        producto = prod_map.get(prod_sel)
        productoid = producto["productoid"] if producto else None
        precio_base = float(producto["precio_generico"] or 0.0) if producto else 0.0

    st.markdown("---")

    # ======================================================
    # ⚙️ Parámetros de simulación
    # ======================================================
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
    with col2:
        fecha_sel = st.date_input("Fecha simulada", value=date.today())
    with col3:
        st.write("")
        calcular = st.button(
            "💡 Calcular precio final",
            use_container_width=True,
            disabled=not (clienteid and productoid),
        )

    # ======================================================
    # 💰 Resultado principal
    # ======================================================
    if calcular:
        try:
            engine = calcular_precio_linea(
                supabase,
                clienteid=clienteid,
                productoid=productoid,
                precio_base_unit=precio_base,
                cantidad=cantidad,
                fecha=fecha_sel,
            )

            nivel = engine.get("nivel_tarifa")
            color = {
                "producto+cliente": "#22c55e",  # verde
                "familia+cliente": "#3b82f6",   # azul
                "producto+grupo": "#f59e0b",    # ámbar
                "familia+grupo": "#eab308",     # mostaza
                "cliente_tarifa": "#8b5cf6",    # violeta
                "fallback_general": "#6b7280",  # gris
                None: "#9ca3af"
            }.get(nivel)

            st.markdown("### 💰 Resultado del cálculo")

            st.markdown(
                f"""
                <div style="border-left:6px solid {color};padding:15px 18px;background:#f9fafb;border-radius:10px;line-height:1.7;">
                <b>Precio bruto unitario:</b> {engine["unit_bruto"]:.2f} €<br>
                <b>Descuento aplicado:</b> {engine["descuento_pct"]:.2f}%<br>
                <b>→ Neto sin IVA:</b> {engine["unit_neto_sin_iva"]:.2f} €<br>
                <b>IVA:</b> {engine["iva_pct"]:.2f}% ({engine["iva_nombre"] or "No definido"})<br>
                <b>Total con IVA:</b> <span style="font-size:1.2em;color:#16a34a;font-weight:600;">{engine["total_con_iva"]:.2f} €</span>
                <hr>
                <b>Tarifa aplicada:</b> {engine["tarifa_aplicada"] or "Ninguna"}<br>
                <b>Nivel jerárquico:</b> {nivel or "Sin coincidencia"}<br>
                <b>Regla ID:</b> {engine["regla_id"] or "-"}<br>
                <b>IVA origen:</b> {engine["iva_origen"] or "-"}<br>
                <b>Región:</b> {engine["region"] or "-"} ({engine["region_origen"] or "-"})
                </div>
                """,
                unsafe_allow_html=True,
            )

            # ======================================================
            # 🧩 Jerarquía visual
            # ======================================================
            st.markdown("### Jerarquía evaluada")
            niveles = [
                ("producto+cliente", "Producto + Cliente"),
                ("familia+cliente", "Familia + Cliente"),
                ("producto+grupo", "Producto + Grupo"),
                ("familia+grupo", "Familia + Grupo"),
                ("cliente_tarifa", "Cliente – Tarifa asignada"),
                ("fallback_general", "Tarifa General (fallback)"),
            ]
            for clave, etiqueta in niveles:
                icon = "✅" if nivel == clave else "⚪"
                st.write(f"{icon} {etiqueta}")

            # ======================================================
            # 🧠 Detalle técnico del motor
            # ======================================================
            with st.expander("🔍 Desglose completo del cálculo"):
                st.markdown("**📋 Datos base:**")
                st.json({
                    "Cliente": cliente["razon_social"],
                    "Grupo": cliente.get("grupoid"),
                    "Producto": producto["nombre"],
                    "Familia": producto.get("familia_productoid"),
                    "Tipo Producto": producto.get("producto_tipoid"),
                    "Cantidad": cantidad,
                    "Fecha simulada": str(fecha_sel)
                })

                st.markdown("**🧮 Resultado del motor:**")
                st.json(engine)

                # Mostrar posibles reglas activas relacionadas (vigentes hoy)
                try:
                    fecha_iso = date.today().isoformat()
                    reglas = (
                        supabase.table("tarifa_regla")
                        .select("tarifa_reglaid, tarifaid, clienteid, grupoid, productoid, familia_productoid, producto_tipoid, fecha_inicio, fecha_fin, prioridad")
                        .gte("fecha_fin", fecha_iso)
                        .lte("fecha_inicio", fecha_iso)
                        .execute()
                        .data or []
                    )
                    reglas_rel = [
                        r for r in reglas
                        if (
                            (r.get("clienteid") == clienteid or r.get("grupoid") == cliente.get("grupoid"))
                            and (r.get("productoid") == productoid or r.get("familia_productoid") == producto.get("familia_productoid"))
                        )
                    ]
                    if reglas_rel:
                        st.markdown("**📜 Reglas encontradas relacionadas:**")
                        st.dataframe(pd.DataFrame(reglas_rel), use_container_width=True)
                except Exception:
                    pass

        except Exception as e:
            st.error(f"❌ Error durante la simulación: {e}")
