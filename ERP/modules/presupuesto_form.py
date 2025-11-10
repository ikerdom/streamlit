# modules/presupuesto_form.py
import streamlit as st
from datetime import date, datetime
from modules.pedido_models import load_clientes, load_trabajadores
from modules.presupuesto_detalle import recalcular_lineas_presupuesto

# ==============================
# 🔹 Cargar estados del presupuesto
# ==============================
def _load_estados_presupuesto(supabase) -> dict:
    try:
        rows = supabase.table("estado_presupuesto").select("estado_presupuestoid, nombre").order("estado_presupuestoid").execute().data or []
        return {r["nombre"]: r["estado_presupuestoid"] for r in rows}
    except Exception:
        return {}
def _load_direcciones_cliente(supabase, clienteid: int) -> dict:
    """Devuelve un dict {label: cliente_direccionid} solo para direcciones de envío."""
    if not clienteid:
        return {}

    try:
        rows = (
            supabase.table("cliente_direccion")
            .select("cliente_direccionid, direccion, ciudad, provincia, region(nombre)")
            .eq("clienteid", clienteid)
            .eq("tipo", "envio")
            .execute()
            .data
            or []
        )
        direcciones = {}
        for r in rows:
            region_name = "-"
            if isinstance(r.get("region"), dict):
                region_name = r["region"].get("nombre") or "-"
            label = f"{r.get('direccion','(sin dirección)')} — {r.get('ciudad','')} ({region_name})"
            direcciones[label] = r["cliente_direccionid"]
        return direcciones
    except Exception:
        return {}

def render_presupuesto_form(supabase, presupuestoid=None, bloqueado=False, on_saved_rerun=True):
    """Formulario limpio de edición/creación de presupuesto (sin PDF ni conversión)."""
    st.subheader("🧾 Datos del presupuesto")

    clientes = load_clientes(supabase)
    trabajadores = load_trabajadores(supabase)
    estados = _load_estados_presupuesto(supabase)

    presupuesto = {}
    if presupuestoid:
        try:
            res = (
                supabase.table("presupuesto")
                .select("*")
                .eq("presupuestoid", presupuestoid)
                .single()
                .execute()
            )
            presupuesto = res.data or {}
        except Exception as e:
            st.error(f"❌ Error cargando presupuesto: {e}")

    def _index(d, val):
        """Devuelve el índice del valor en un dict (para selectboxes)."""
        keys = list(d.keys())
        for i, k in enumerate(keys):
            if d[k] == val:
                return i + 1
        return 0

    with st.form(f"form_presupuesto_{presupuestoid or 'new'}"):
        # === Cliente / Comercial ===
        c1, c2 = st.columns(2)
        with c1:
            cliente_sel = st.selectbox(
                "Cliente",
                ["(sin cliente)"] + list(clientes.keys()),
                index=_index(clientes, presupuesto.get("clienteid")),
                disabled=bloqueado,
            )
        with c2:
            trab_sel = st.selectbox(
                "Comercial",
                ["(sin comercial)"] + list(trabajadores.keys()),
                index=_index(trabajadores, presupuesto.get("trabajadorid")),
                disabled=bloqueado,
            )

        clienteid = clientes.get(cliente_sel)
        direcciones = _load_direcciones_cliente(supabase, clienteid) if clienteid else {}

        if direcciones:
            direccion_sel = st.selectbox(
                "Dirección de envío",
                list(direcciones.keys()),
                index=_index(direcciones, presupuesto.get("direccion_envioid")),
                disabled=bloqueado,
            )
        else:
            direccion_sel = None
            st.info("ℹ️ Selecciona un cliente con direcciones de envío para completar datos fiscales.")

        # === Datos básicos ===
        numero = st.text_input("Número de presupuesto", presupuesto.get("numero", ""), disabled=bloqueado)
        referencia = st.text_input("Referencia cliente", presupuesto.get("referencia_cliente", ""), disabled=bloqueado)

        c3, c4 = st.columns(2)
        with c3:
            fecha = st.date_input(
                "Fecha del presupuesto",
                value=(
                    date.fromisoformat(presupuesto["fecha_presupuesto"])
                    if presupuesto.get("fecha_presupuesto")
                    else date.today()
                ),
                disabled=bloqueado,
            )
        with c4:
            fecha_validez = st.date_input(
                "Validez hasta",
                value=(
                    date.fromisoformat(presupuesto["fecha_validez"])
                    if presupuesto.get("fecha_validez")
                    else date.today()
                ),
                disabled=bloqueado,
            )

        observaciones = st.text_area(
            "Observaciones",
            presupuesto.get("observaciones", ""),
            height=100,
            disabled=bloqueado,
        )

        estado_sel = st.selectbox(
            "Estado del presupuesto",
            ["(sin estado)"] + list(estados.keys()),
            index=_index(estados, presupuesto.get("estado_presupuestoid")),
            disabled=bloqueado,
        )

        facturar = st.checkbox(
            "Facturar individualmente",
            value=bool(presupuesto.get("facturar_individual", False)),
            disabled=bloqueado,
        )

        st.caption("💡 El total del presupuesto se calcula automáticamente con las líneas.")

        guardar = st.form_submit_button("💾 Guardar presupuesto", disabled=bloqueado, use_container_width=True)

    # === Guardar cambios ===
    if guardar:
        try:
            payload = {
                "numero": numero.strip() if numero else None,
                "clienteid": clienteid,
                "trabajadorid": trabajadores.get(trab_sel),
                "referencia_cliente": referencia.strip() or None,
                "fecha_presupuesto": fecha.isoformat(),
                "fecha_validez": fecha_validez.isoformat(),
                "observaciones": observaciones.strip() or None,
                "facturar_individual": facturar,
                "direccion_envioid": direcciones.get(direccion_sel) if direccion_sel else None,
            }

            # Añadir región si existe
            if payload.get("direccion_envioid"):
                reg = (
                    supabase.table("cliente_direccion")
                    .select("regionid")
                    .eq("cliente_direccionid", payload["direccion_envioid"])
                    .single()
                    .execute()
                    .data
                )
                if reg and reg.get("regionid"):
                    payload["regionid"] = reg["regionid"]

            # Estado
            if estado_sel and estado_sel in estados:
                payload["estado_presupuestoid"] = estados[estado_sel]

            # Guardar / actualizar
            if presupuestoid:
                supabase.table("presupuesto").update(payload).eq("presupuestoid", presupuestoid).execute()
                st.toast("✅ Presupuesto actualizado correctamente.", icon="✅")
            else:
                supabase.table("presupuesto").insert(payload).execute()
                st.toast("✅ Nuevo presupuesto creado.", icon="✅")

            if on_saved_rerun:
                st.rerun()

        except Exception as e:
            st.error(f"❌ Error al guardar el presupuesto: {e}")

def convertir_presupuesto_a_pedido(supabase, presupuestoid: int):
    """Convierte un presupuesto Aceptado en un pedido, con control de duplicado."""
    try:
        # Ya convertido
        existing = (
            supabase.table("pedido")
            .select("pedidoid, numero")
            .eq("presupuesto_origenid", presupuestoid)
            .execute()
            .data
        )
        if existing:
            st.info(f"ℹ️ Ya existe un pedido asociado: #{existing[0]['numero']}")
            return

        # Cargar presupuesto
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

        # Crear pedido
        fecha = datetime.now().date()
        numero_pedido = f"PED-{fecha.year}-{9000 + presupuestoid:04d}"

        pedido = {
            "numero": numero_pedido,
            "clienteid": pres.get("clienteid"),
            "trabajadorid": pres.get("trabajadorid"),
            "fecha_pedido": fecha.isoformat(),
            "estado_pedidoid": 1,  # Borrador
            "presupuesto_origenid": presupuestoid,
        }
        pedido_resp = supabase.table("pedido").insert(pedido).execute().data
        if not pedido_resp:
            st.error("❌ Error creando pedido.")
            return
        pedidoid = pedido_resp[0]["pedidoid"]

        # Copiar líneas
        lineas = (
            supabase.table("presupuesto_detalle")
            .select("*")
            .eq("presupuestoid", presupuestoid)
            .execute()
            .data
            or []
        )
        for ln in lineas:
            supabase.table("pedido_detalle").insert({
                "pedidoid": pedidoid,
                "productoid": ln.get("productoid"),
                "descripcion": ln.get("descripcion"),
                "cantidad": ln.get("cantidad"),
                "precio_unitario": ln.get("precio_unitario"),
                "descuento_pct": ln.get("descuento_pct") or 0,
                "iva_pct": ln.get("iva_pct") or 21,
                "importe_base": ln.get("importe_base") or 0,
                "importe_total_linea": ln.get("importe_total_linea") or 0,
                "tarifa_aplicada": ln.get("tarifa_aplicada"),
                "nivel_tarifa": ln.get("nivel_tarifa"),
            }).execute()

        # Actualizar presupuesto → Convertido
        supabase.table("presupuesto").update({
            "estado_presupuestoid": 6,
            "pedidoid_relacionado": pedidoid,
        }).eq("presupuestoid", presupuestoid).execute()

        st.success(f"✅ Presupuesto #{presupuestoid} convertido a pedido {numero_pedido}")
        return pedidoid

    except Exception as e:
        st.error(f"❌ Error al convertir presupuesto: {e}")
        return None
