# =========================================================
# 🔄 Conversión de Presupuestos a Pedidos
# =========================================================
import streamlit as st
from datetime import date, datetime
def convertir_presupuesto_a_pedido(supabase, presupuestoid: int):
    """
    Convierte un presupuesto aceptado en un pedido (una sola vez).
    Si ya existe un pedido para ese presupuesto, no crea otro.
    """
    try:
        # 1️⃣ Verificar si ya existe pedido con este presupuesto de origen
        existing = (
            supabase.table("pedido")
            .select("pedidoid, numero, estado_pedidoid")
            .eq("presupuesto_origenid", presupuestoid)
            .execute()
            .data
        )

        if existing:
            st.warning(f"⚠️ Ya existe un pedido asociado a este presupuesto (#{existing[0]['numero']}).")
            return

        # 2️⃣ Cargar datos del presupuesto
        pres = (
            supabase.table("presupuesto")
            .select("*")
            .eq("presupuestoid", presupuestoid)
            .single()
            .execute()
            .data
        )
        if not pres:
            st.error("❌ Presupuesto no encontrado.")
            return

        # 3️⃣ Crear número nuevo de pedido
        import datetime
        fecha = datetime.date.today()
        anio = fecha.year
        numero_pedido = f"PED-{anio}-{9000 + presupuestoid:04d}"

        # 4️⃣ Insertar el pedido nuevo
        pedido_data = {
            "numero": numero_pedido,
            "clienteid": pres["clienteid"],
            "tipo_pedidoid": 1,
            "procedencia_pedidoid": 2,
            "estado_pedidoid": 1,  # Borrador
            "fecha_pedido": fecha.isoformat(),
            "trabajadorid": pres.get("trabajadorid"),
            "presupuesto_origenid": presupuestoid,
        }

        pedido_resp = supabase.table("pedido").insert(pedido_data).execute().data
        if not pedido_resp:
            st.error("❌ Error creando el pedido.")
            return

        pedidoid = pedido_resp[0]["pedidoid"]

        # 5️⃣ Copiar líneas del presupuesto
        lineas = (
            supabase.table("presupuesto_detalle")
            .select("*")
            .eq("presupuestoid", presupuestoid)
            .execute()
            .data
            or []
        )

        for l in lineas:
            supabase.table("pedido_detalle").insert({
                "pedidoid": pedidoid,
                "productoid": l.get("productoid"),
                "nombre_producto": l.get("descripcion"),
                "cantidad": l.get("cantidad"),
                "precio_unitario": l.get("precio_unitario"),
                "descuento_pct": l.get("descuento_pct") or 0,
                "iva_pct": l.get("iva_pct") or 21,
                "importe_base": l.get("importe_base") or 0,
                "importe_total_linea": l.get("importe_total_linea") or 0,
            }).execute()

        # 6️⃣ Actualizar presupuesto a “Convertido”
        supabase.table("presupuesto").update({"estado_presupuestoid": 6}).eq("presupuestoid", presupuestoid).execute()

        st.success(f"✅ Presupuesto #{presupuestoid} convertido a pedido {numero_pedido}")

    except Exception as e:
        st.error(f"❌ Error convirtiendo presupuesto a pedido: {e}")
