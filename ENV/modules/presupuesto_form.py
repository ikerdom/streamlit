import streamlit as st
from datetime import date
import requests

from modules.presupuesto_api import (
    get_presupuesto,
    actualizar_presupuesto,
    crear_presupuesto,
    get_catalogos,
    cliente_basico,
)
from modules.presupuesto_api import _base_url


def _load_direcciones(clienteid: int):
    """Devuelve (envio_options, env_by_id, fiscal_row)."""
    try:
        r = requests.get(f"{_base_url()}/api/clientes/{clienteid}/direcciones", timeout=20)
        r.raise_for_status()
        rows = r.json() or []
    except Exception:
        return {}, {}, None

    envio_labels = {}
    envio_by_id = {}
    fiscal = None

    for r in rows:
        if r.get("tipo") == "envio":
            label = f"{r.get('direccion','(sin dirección)')} · {r.get('cp','')} {r.get('ciudad','')} ({r.get('provincia','')})"
            envio_labels[label] = r["cliente_direccionid"]
            envio_by_id[r["cliente_direccionid"]] = r
        if r.get("tipo") == "fiscal":
            fiscal = r

    return envio_labels, envio_by_id, fiscal


def _index(d: dict, val):
    """Índice para selectbox con opción vacía inicial."""
    if not d or val is None:
        return 0
    keys = list(d.keys())
    for i, k in enumerate(keys):
        if d[k] == val:
            return i + 1
    return 0


def render_presupuesto_form(presupuestoid=None, bloqueado=False, on_saved_rerun=True):
    """
    Formulario de cabecera del presupuesto (consumiendo API FastAPI).
    - Si presupuestoid es None, crea; si existe, actualiza.
    """
    st.subheader("🧾 Datos del presupuesto")

    # Catálogos
    catalogos = get_catalogos()
    estados = {c["label"]: c["id"] for c in catalogos.get("estados", [])}
    formas_pago = {c["label"]: c["id"] for c in catalogos.get("formas_pago", [])}
    clientes_cat = {c["label"]: c["id"] for c in catalogos.get("clientes", [])}
    trabajadores = {c["label"]: c["id"] for c in catalogos.get("trabajadores", [])}

    # Presupuesto (si existe)
    presupuesto = {}
    if presupuestoid:
        try:
            presupuesto = get_presupuesto(presupuestoid)
        except Exception as e:
            st.error(f"❌ No se pudo cargar el presupuesto: {e}")
            return

    # Cliente info
    clienteid = presupuesto.get("clienteid")
    cliente_info = cliente_basico(clienteid) if clienteid else {}
    direcciones_env_labels, direcciones_env_by_id, direccion_fiscal = _load_direcciones(clienteid) if clienteid else ({}, {}, None)

    with st.form(f"form_presupuesto_{presupuestoid or 'new'}"):
        c1, c2 = st.columns(2)
        with c1:
            cliente_sel = st.selectbox(
                "Cliente",
                ["(sin cliente)"] + list(clientes_cat.keys()),
                index=_index(clientes_cat, presupuesto.get("clienteid")),
                disabled=bool(presupuestoid),
            )
        with c2:
            trab_sel = st.selectbox(
                "Comercial",
                ["(sin comercial)"] + list(trabajadores.keys()),
                index=_index(trabajadores, presupuesto.get("trabajadorid")),
                disabled=bloqueado,
            )

        if not presupuestoid and cliente_sel != "(sin cliente)":
            clienteid = clientes_cat.get(cliente_sel)
            cliente_info = cliente_basico(clienteid) if clienteid else {}
            direcciones_env_labels, direcciones_env_by_id, direccion_fiscal = _load_direcciones(clienteid)

        with st.expander("🏢 Datos fiscales del cliente", expanded=True):
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

        with st.expander("🚚 Dirección de envío", expanded=True):
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

            if direccion_sel:
                env_id = direcciones_env_labels.get(direccion_sel)
                env = direcciones_env_by_id.get(env_id, {})
                st.markdown("**Resumen dirección de envío**")
                st.write(
                    f"{env.get('direccion','')}\n\n"
                    f"{env.get('cp','')} {env.get('ciudad','')} "
                    f"({env.get('provincia','')}) {env.get('pais','ESPAÑA')}"
                )

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
            index=_index(formas_pago, presupuesto.get("formapagoid")),
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
                "direccion_envioid": direcciones_env_labels.get(direccion_sel) if direccion_sel else None,
            }

            payload["formapagoid"] = formas_pago.get(formapago_sel) if formapago_sel in formas_pago else None
            if estado_sel in estados:
                payload["estado_presupuestoid"] = estados[estado_sel]

            if presupuestoid:
                actualizar_presupuesto(presupuestoid, payload)
                st.toast("✅ Presupuesto actualizado.", icon="✅")
            else:
                creado = crear_presupuesto(payload)
                presupuestoid = creado.get("presupuestoid")
                st.toast("✅ Presupuesto creado.", icon="✅")

            if on_saved_rerun:
                st.rerun()

        except Exception as e:
            st.error(f"❌ Error al guardar el presupuesto: {e}")
