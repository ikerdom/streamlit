import streamlit as st
from datetime import date, datetime

from modules.pedido_models import load_clientes, load_trabajadores
from modules.presupuesto_detalle import recalcular_lineas_presupuesto  # (usado en otros flujos)


# ==============================
# 🔹 Helpers de catálogos
# ==============================
def _load_estados_presupuesto(supabase) -> dict:
    """Devuelve {nombre: estado_presupuestoid}."""
    try:
        rows = (
            supabase.table("estado_presupuesto")
            .select("estado_presupuestoid, nombre")
            .order("estado_presupuestoid")
            .execute()
            .data
            or []
        )
        return {r["nombre"]: r["estado_presupuestoid"] for r in rows}
    except Exception:
        return {}

def _load_direcciones_envio_cliente(supabase, clienteid: int):
    """
    Devuelve:
      - dict {label: cliente_direccionid} SOLO para tipo='envio'
      - dict {cliente_direccionid: row}
    """
    if not clienteid:
        return {}, {}

    try:
        rows = (
            supabase.table("cliente_direccion")
            .select(
                "cliente_direccionid, tipo, direccion, cp, ciudad, provincia, pais, region(nombre)"
            )
            .eq("clienteid", clienteid)
            .eq("tipo", "envio")
            .order("cliente_direccionid")
            .execute()
            .data
            or []
        )

        labels = {}
        by_id = {}

        for r in rows:
            region_name = "-"
            if isinstance(r.get("region"), dict):
                region_name = r["region"].get("nombre") or "-"

            label = (
                f"{r.get('direccion','(sin dirección)')} — "
                f"{r.get('cp','')} {r.get('ciudad','')} "
                f"({region_name})"
            )
            labels[label] = r["cliente_direccionid"]
            by_id[r["cliente_direccionid"]] = r

        return labels, by_id
    except Exception:
        return {}, {}


def _load_direccion_fiscal_cliente(supabase, clienteid: int):
    """
    Devuelve la dirección fiscal (tipo='fiscal') si existe, o None.
    """
    if not clienteid:
        return None

    try:
        row = (
            supabase.table("cliente_direccion")
            .select(
                "cliente_direccionid, tipo, direccion, cp, ciudad, provincia, pais, region(nombre)"
            )
            .eq("clienteid", clienteid)
            .eq("tipo", "fiscal")
            .maybe_single()
            .execute()
            .data
        )
        return row or None
    except Exception:
        return None


def _load_formas_pago(supabase) -> dict:
    """Devuelve {nombre: formapagoid}."""
    try:
        rows = (
            supabase.table("forma_pago")
            .select("formapagoid, nombre")
            .order("orden", desc=False)
            .order("nombre", desc=False)
            .execute()
            .data
            or []
        )
        return {r["nombre"]: r["formapagoid"] for r in rows}
    except Exception:
        return {}


def _load_cliente_basico(supabase, clienteid: int):
    """
    Devuelve info básica del cliente (razón social, cif, teléfono, email).
    No rompe si no existe.
    """
    if not clienteid:
        return {}

    try:
        row = (
            supabase.table("cliente")
            .select("clienteid, razon_social, nombre_comercial, cif_nif, cif, telefono, email")
            .eq("clienteid", clienteid)
            .maybe_single()
            .execute()
            .data
        )
        return row or {}
    except Exception:
        return {}


# ==============================
# 🔹 Helper de índices para selectbox
# ==============================
def _index(d: dict, val):
    """Devuelve el índice del valor en un dict (para selectboxes)."""
    if not d or val is None:
        return 0
    keys = list(d.keys())
    for i, k in enumerate(keys):
        if d[k] == val:
            return i + 1  # +1 por el "(sin ...)" inicial
    return 0

def render_presupuesto_form(supabase, presupuestoid=None, bloqueado=False, on_saved_rerun=True):
    """
    Formulario profesional de presupuesto:
      - Cliente bloqueado si ya existe el presupuesto
      - Dirección fiscal visible (solo lectura)
      - Dirección de envío seleccionable
      - Contacto ATT / Teléfono
      - Forma de pago
      - Fechas, estado, observaciones
      - Guarda regionid automáticamente
    """
    st.subheader("🧾 Datos del presupuesto")

    # --- Catálogos
    clientes = load_clientes(supabase)
    trabajadores = load_trabajadores(supabase)
    estados = _load_estados_presupuesto(supabase)
    formas_pago = _load_formas_pago(supabase)

    # --- Cargar presupuesto
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
        except:
            st.error("❌ No se pudo cargar el presupuesto")

    # Cliente del presupuesto
    clienteid = presupuesto.get("clienteid")
    cliente_info = _load_cliente_basico(supabase, clienteid) if clienteid else {}

    # Direcciones
    direcciones_env_labels, direcciones_env_by_id = _load_direcciones_envio_cliente(
        supabase, clienteid
    ) if clienteid else ({}, {})
    direccion_fiscal = _load_direccion_fiscal_cliente(supabase, clienteid) if clienteid else None

    # Forma de pago
    formapagoid = presupuesto.get("formapagoid")

    # =====================================================
    # 👇 FORMULARIO
    # =====================================================
    with st.form(f"form_presupuesto_{presupuestoid or 'new'}"):
        # ========= CLIENTE + COMERCIAL =========
        c1, c2 = st.columns(2)
        with c1:
            cliente_sel = st.selectbox(
                "Cliente",
                ["(sin cliente)"] + list(clientes.keys()),
                index=_index(clientes, presupuesto.get("clienteid")),
                disabled=bool(presupuestoid),           # 🔒 Bloqueado si existe
            )

        with c2:
            trab_sel = st.selectbox(
                "Comercial",
                ["(sin comercial)"] + list(trabajadores.keys()),
                index=_index(trabajadores, presupuesto.get("trabajadorid")),
                disabled=bloqueado,
            )

        # Si es nuevo, recargar cliente info y direcciones
        if not presupuestoid:
            clienteid = clientes.get(cliente_sel)
            cliente_info = _load_cliente_basico(supabase, clienteid)
            direcciones_env_labels, direcciones_env_by_id = _load_direcciones_envio_cliente(supabase, clienteid)
            direccion_fiscal = _load_direccion_fiscal_cliente(supabase, clienteid)

        # ========= BLOQUE FISCAL =========
        with st.expander("📌 Datos fiscales del cliente", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.text_input(
                    "Razón social",
                    value=cliente_info.get("razon_social") or cliente_info.get("nombre_comercial") or "",
                    disabled=True,
                )
            with col_b:
                st.text_input(
                    "CIF/NIF",
                    value=cliente_info.get("cif_nif") or cliente_info.get("cif") or "",
                    disabled=True,
                )

            if direccion_fiscal:
                st.markdown("**Dirección fiscal**")
                st.write(
                    f"{direccion_fiscal.get('direccion','')}\n\n"
                    f"{direccion_fiscal.get('cp','')} "
                    f"{direccion_fiscal.get('ciudad','')} "
                    f"({direccion_fiscal.get('provincia','')}) "
                    f"{direccion_fiscal.get('pais','ESPAÑA')}"
                )
            else:
                st.info("ℹ️ Este cliente no tiene dirección fiscal definida.")

        # ========= ENVÍO =========
        with st.expander("📦 Dirección de envío", expanded=True):
            if direcciones_env_labels:
                direccion_sel = st.selectbox(
                    "Dirección de envío",
                    list(direcciones_env_labels.keys()),
                    index=_index(direcciones_env_labels, presupuesto.get("direccion_envioid")),
                    disabled=bloqueado,
                )
            else:
                direccion_sel = None
                st.info("ℹ️ No hay direcciones de envío. Se usará la fiscal.")

            # Vista previa
            if direccion_sel:
                env_id = direcciones_env_labels.get(direccion_sel)
                env = direcciones_env_by_id.get(env_id, {})
                st.markdown("**Resumen dirección de envío**")
                st.write(
                    f"{env.get('direccion','')}\n\n"
                    f"{env.get('cp','')} {env.get('ciudad','')} "
                    f"({env.get('provincia','')}) {env.get('pais','ESPAÑA')}"
                )

        # ========= DATOS BÁSICOS =========
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

        # ========= CONTACTO + FP =========
        c5, c6 = st.columns(2)
        with c5:
            contacto_att = st.text_input(
                "Persona de contacto (ATT.)",
                presupuesto.get("contacto_att", ""),
                disabled=bloqueado,
            )
        with c6:
            telefono_contacto = st.text_input(
                "Teléfono contacto",
                presupuesto.get("telefono_contacto", ""),
                disabled=bloqueado,
            )

        formapago_sel = st.selectbox(
            "Forma de pago",
            ["(sin forma de pago)"] + list(formas_pago.keys()),
            index=_index(formas_pago, formapagoid),
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

        guardar = st.form_submit_button("💾 Guardar presupuesto", disabled=bloqueado, use_container_width=True)

    # ====== GUARDAR ======
    if guardar:
        try:
            payload = {
                "numero": numero or None,
                "clienteid": clienteid,
                "trabajadorid": trabajadores.get(trab_sel),
                "referencia_cliente": referencia or None,
                "fecha_presupuesto": fecha.isoformat(),
                "fecha_validez": fecha_validez.isoformat(),
                "observaciones": observaciones or None,
                "facturar_individual": facturar,
                "contacto_att": contacto_att or None,
                "telefono_contacto": telefono_contacto or None,
                "direccion_envioid": direcciones_env_labels.get(direccion_sel)
                if direccion_sel else None,
            }

            # Región automática
            if payload["direccion_envioid"]:
                reg = (
                    supabase.table("cliente_direccion")
                    .select("regionid")
                    .eq("cliente_direccionid", payload["direccion_envioid"])
                    .maybe_single()
                    .execute()
                    .data
                )
                if reg and reg.get("regionid"):
                    payload["regionid"] = reg["regionid"]

            # Forma pago
            payload["formapagoid"] = formas_pago.get(formapago_sel) if formapago_sel in formas_pago else None

            # Estado
            if estado_sel in estados:
                payload["estado_presupuestoid"] = estados[estado_sel]

            # Guardar
            if presupuestoid:
                supabase.table("presupuesto").update(payload).eq("presupuestoid", presupuestoid).execute()
                st.toast("✅ Presupuesto actualizado.", icon="✅")
            else:
                supabase.table("presupuesto").insert(payload).execute()
                st.toast("✅ Presupuesto creado.", icon="✅")

            if on_saved_rerun:
                st.rerun()

        except Exception as e:
            st.error(f"❌ Error al guardar el presupuesto: {e}")

# ===========================================
# 🔁 CONVERTIR PRESUPUESTO → PEDIDO (igual que tenías)
# ===========================================
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
            supabase.table("pedido_detalle").insert(
                {
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
                }
            ).execute()

        # Actualizar presupuesto → Convertido
        supabase.table("presupuesto").update(
            {
                "estado_presupuestoid": 6,
                "pedidoid_relacionado": pedidoid,
            }
        ).eq("presupuestoid", presupuestoid).execute()

        st.success(f"✅ Presupuesto #{presupuestoid} convertido a pedido {numero_pedido}")
        return pedidoid

    except Exception as e:
        st.error(f"❌ Error al convertir presupuesto: {e}")
        return None
