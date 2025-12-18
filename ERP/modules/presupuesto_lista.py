import io
import math
import base64
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from modules.orbe_theme import apply_orbe_theme
from modules.pedido_models import load_clientes, load_trabajadores
from modules.presupuesto_form import render_presupuesto_form
from modules.presupuesto_detalle import render_presupuesto_detalle

# UI unificada (como cliente_lista)
from modules.ui.page import page
from modules.ui.section import section
from modules.ui.card import card
from modules.ui.empty import empty_state


# ======================
# Helpers
# ======================

def _safe(val, default="-"):
    return val if val not in (None, "", "null") else default


def _range(page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size - 1
    return start, end


def _load_estados_presupuesto(supabase) -> dict:
    """Devuelve {nombre_estado: estado_presupuestoid}."""
    try:
        res = (
            supabase.table("estado_presupuesto")
            .select("estado_presupuestoid, nombre")
            .order("estado_presupuestoid")
            .execute()
        )
        rows = getattr(res, "data", None) or []
        return {r["nombre"]: r["estado_presupuestoid"] for r in rows}
    except Exception:
        return {}


def _label_from(catalog: dict, id_val) -> str:
    if not id_val:
        return "-"
    for k, v in (catalog or {}).items():
        if v == id_val:
            return k
    return "-"


def _is_bloqueado(estado_nombre: str) -> bool:
    """BLOQUEA si el estado es Aceptado / Convertido."""
    if not estado_nombre:
        return False
    e = estado_nombre.lower()
    return ("acept" in e) or ("convert" in e)


# ======================
# Constructor rápido (inline)
# ======================

def _render_nuevo_presupuesto_inline(supabase):
    """Constructor de presupuesto rápido con fecha y validez automáticas."""
    st.markdown("### 🆕 Nuevo presupuesto")

    clientes = load_clientes(supabase)
    productos_res = (
        supabase.table("producto")
        .select("productoid, nombre, precio_generico, familia_productoid, impuestoid")
        .order("nombre")
        .execute()
    )
    productos = getattr(productos_res, "data", None) or []

    col1, col2 = st.columns(2)
    with col1:
        cliente_sel = st.selectbox(
            "👤 Cliente",
            ["(selecciona)"] + list(clientes.keys()),
            key="nuevo_pres_cliente",
        )
    with col2:
        fecha_pres = st.date_input(
            "📅 Fecha del presupuesto",
            value=date.today(),
            key="nuevo_pres_fecha",
        )

    col3, col4 = st.columns(2)
    with col3:
        fecha_validez = st.date_input(
            "⏳ Validez hasta",
            value=date.today() + timedelta(days=30),
            key="nuevo_pres_validez",
        )
    with col4:
        producto_sel = st.selectbox(
            "📦 Producto inicial",
            ["(selecciona)"] + [p["nombre"] for p in productos],
            key="nuevo_pres_producto",
        )

    cantidad = st.number_input(
        "Cantidad", min_value=1, step=1, value=1, key="nuevo_pres_cantidad"
    )

    crear = st.button(
        "💾 Crear presupuesto",
        type="primary",
        use_container_width=True,
        key="nuevo_pres_crear",
    )
    if not crear:
        return

    if cliente_sel == "(selecciona)" or producto_sel == "(selecciona)":
        st.warning("Selecciona un cliente y un producto para crear el presupuesto.")
        return

    clienteid = clientes.get(cliente_sel)
    producto = next((p for p in productos if p["nombre"] == producto_sel), None)
    if not producto:
        st.error("❌ Producto no encontrado.")
        return

    # Región por dirección de envío (fallback fiscal si no hay envío)
    regionid = None
    try:
        r_res = (
            supabase.table("cliente_direccion")
            .select("regionid, tipo")
            .eq("clienteid", clienteid)
            .order("CASE WHEN tipo = 'envio' THEN 1 WHEN tipo = 'fiscal' THEN 2 ELSE 3 END")
            .limit(1)
            .execute()
        )
        r = getattr(r_res, "data", None) or []
        if r:
            regionid = r[0].get("regionid")
    except Exception:
        pass

    # Número correlativo
    prefijo = f"PRES-{fecha_pres.year}-"
    existentes_res = (
        supabase.table("presupuesto")
        .select("numero")
        .ilike("numero", f"{prefijo}%")
        .execute()
    )
    existentes = getattr(existentes_res, "data", None) or []
    usados = [
        int(x["numero"].split("-")[-1])
        for x in existentes
        if x.get("numero") and x["numero"].split("-")[-1].isdigit()
    ]
    nuevo_num = max(usados) + 1 if usados else 1
    numero = f"{prefijo}{nuevo_num:04d}"

    # Estado = Borrador (si existe)
    estadoid = None
    try:
        e_res = (
            supabase.table("estado_presupuesto")
            .select("estado_presupuestoid")
            .eq("nombre", "Borrador")
            .maybe_single()
            .execute()
        )
        e = getattr(e_res, "data", None)
        if e:
            estadoid = e.get("estado_presupuestoid")
    except Exception:
        pass

    insert_pres = {
        "numero": numero,
        "clienteid": clienteid,
        "fecha_presupuesto": fecha_pres.isoformat(),
        "fecha_validez": fecha_validez.isoformat(),
        "observaciones": None,
        "facturar_individual": False,
        "total_estimada": 0.0,
        "editable": True,
        "regionid": regionid,
        "estado_presupuestoid": estadoid,
        "creado_en": datetime.now().isoformat(),
    }

    try:
        pres_res = supabase.table("presupuesto").insert(insert_pres).execute()
        pres = (getattr(pres_res, "data", None) or [None])[0]
        if not pres:
            st.error("❌ No se ha podido crear el presupuesto.")
            return
    except Exception as e:
        st.error(f"❌ Error creando el presupuesto: {e}")
        return

    presupuestoid = pres["presupuestoid"]

    # Línea inicial con motor de tarifas — fecha de cálculo = validez (o la de presupuesto)
    try:
        from modules.precio_engine import calcular_precio_linea
        from modules.presupuesto_detalle import actualizar_total_presupuesto

        fecha_calc = fecha_validez or fecha_pres  # date

        precio_linea = calcular_precio_linea(
            supabase=supabase,
            clienteid=clienteid,
            productoid=producto["productoid"],
            cantidad=float(cantidad),
            fecha=fecha_calc,
        )
        # st.warning(precio_linea)  # DEBUG (si quieres ver el dict del motor)

        unit_bruto = float(
            precio_linea.get("unit_bruto", producto.get("precio_generico", 0.0))
        )
        dto_pct = float(precio_linea.get("descuento_pct", 0.0))
        iva_pct = float(precio_linea.get("iva_pct", 21.0))

        subtotal = float(
            precio_linea.get(
                "subtotal_sin_iva",
                float(cantidad) * unit_bruto * (1 - dto_pct / 100.0),
            )
        )
        total = float(
            precio_linea.get("total_con_iva", subtotal * (1 + iva_pct / 100.0))
        )

        linea = {
            "presupuestoid": presupuestoid,
            "productoid": producto["productoid"],
            "descripcion": producto["nombre"],
            "cantidad": float(cantidad),
            "precio_unitario": unit_bruto,
            "descuento_pct": dto_pct,
            "iva_pct": iva_pct,
            "importe_base": subtotal,
            "importe_total_linea": total,
            "fecha_alta": datetime.now().isoformat(),
            "tarifa_aplicada": precio_linea.get("tarifa_aplicada"),
            "nivel_tarifa": precio_linea.get("nivel_tarifa"),
            "iva_origen": precio_linea.get("iva_origen"),
        }
        supabase.table("presupuesto_detalle").insert(linea).execute()

        # Recalcular totales
        actualizar_total_presupuesto(supabase, presupuestoid)

    except Exception as e:
        st.warning(
            f"⚠️ Presupuesto creado, pero error en cálculo de la primera línea: {e}"
        )

    st.session_state["presupuesto_modal_id"] = presupuestoid
    st.session_state["show_presupuesto_modal"] = True
    st.success(f"✅ Presupuesto creado correctamente: {numero}")
    st.rerun()


# ======================================================
# 📄 Emitir presupuesto (PDF unificado + marcar Enviado)
# ======================================================

from modules.presupuesto_pdf import (
    _build_data_real,
    build_pdf_bytes,
    upload_pdf_to_storage,
)


def emitir_presupuesto(supabase, presupuestoid: int, estados: dict):
    """
    Genera el PDF final usando el motor unificado,
    lo muestra, permite descargarlo, subirlo a Storage
    y marca el presupuesto como 'Enviado'.
    """
    try:
        # 1️⃣ Validaciones iniciales
        pres_res = (
            supabase.table("presupuesto")
            .select("presupuestoid")
            .eq("presupuestoid", presupuestoid)
            .maybe_single()
            .execute()
        )
        pres = getattr(pres_res, "data", None)
        if not pres:
            st.error("❌ Presupuesto no encontrado.")
            return

        # 2️⃣ Construir data_real (motor oficial unificado)
        data_real = _build_data_real(supabase, presupuestoid)

        # 3️⃣ Generar PDF final
        pdf_bytes, file_name = build_pdf_bytes(data_real)

        # 4️⃣ Mostrar PDF en pantalla
        st.markdown("### 🧾 Documento PDF generado")
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{pdf_b64}" '
            f'width="100%" height="720px"></iframe>',
            unsafe_allow_html=True,
        )

        # 5️⃣ Botón de descarga
        st.download_button(
            "⬇️ Descargar PDF",
            pdf_bytes,
            file_name=file_name,
            mime="application/pdf",
            use_container_width=True,
        )

        # 6️⃣ Subida a Supabase Storage
        if st.button("☁️ Subir PDF a Supabase Storage", use_container_width=True):
            try:
                url = upload_pdf_to_storage(
                    supabase, pdf_bytes, file_name, bucket="presupuestos"
                )
                st.success("📤 PDF guardado correctamente en Supabase Storage.")
                if url:
                    st.markdown(f"🔗 [Abrir PDF en Supabase Storage]({url})")
            except Exception as e:
                st.error(f"❌ Error subiendo PDF: {e}")

        st.markdown("---")

        # 7️⃣ Marcar como ENVIADO
        enviado_id = None
        for nombre, eid in estados.items():
            if "envi" in (nombre or "").lower():
                enviado_id = eid
                break

        if enviado_id:
            supabase.table("presupuesto").update(
                {
                    "estado_presupuestoid": enviado_id,
                    "editable": False,
                    "fecha_envio": datetime.now().isoformat(),
                }
            ).eq("presupuestoid", presupuestoid).execute()
            st.success("📨 Presupuesto marcado como 'Enviado'.")
        else:
            st.warning(
                "⚠️ No se encontró el estado 'Enviado' en la tabla 'estado_presupuesto'."
            )

    except Exception as e:
        st.error(f"❌ Error al emitir presupuesto: {e}")

def _render_card(r, supabase, clientes, trabajadores, estados):
    cli = _label_from(clientes, r.get("clienteid"))
    tra = _label_from(trabajadores, r.get("trabajadorid"))
    est_nombre = _label_from(estados, r.get("estado_presupuestoid"))

    # Color estado
    e = (est_nombre or "").lower()
    if "acept" in e:
        color_estado = "#10b981"
    elif "rechaz" in e:
        color_estado = "#ef4444"
    elif "convert" in e:
        color_estado = "#6b7280"
    else:
        color_estado = "#3b82f6"

    pres_id = r.get("presupuestoid")
    numero = _safe(r.get("numero"))
    fecha = _safe(r.get("fecha_presupuesto"))
    total = _safe(r.get("total_estimada"))

    with card():
        # Header card
        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <span style="background:#111827;color:#fff;padding:2px 8px;border-radius:999px;font-size:0.75rem;">
                  #{pres_id}
                </span>
                <div style="font-weight:700;">{numero}</div>
              </div>
              <span style="background:{color_estado};color:#fff;padding:3px 10px;border-radius:999px;font-size:0.8rem;font-weight:600;">
                {est_nombre or '-'}
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(f"👤 {_safe(cli)}  ·  🧑 {_safe(tra)}")
        st.caption(f"📅 {fecha}  ·  💶 {total} €")

        st.markdown("")

        if st.button("📄 Ficha", key=f"pres_ficha_{pres_id}", use_container_width=True):
            st.session_state["presupuesto_modal_id"] = pres_id
            st.session_state["show_presupuesto_modal"] = True
            st.rerun()


def _render_table(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No hay presupuestos.")
        return
    cols = [
        "presupuestoid",
        "numero",
        "clienteid",
        "estado_presupuestoid",
        "fecha_presupuesto",
        "fecha_validez",
        "total_estimada",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None

    st.dataframe(df[cols], use_container_width=True, hide_index=True)
    buff = io.StringIO()
    df[cols].to_csv(buff, index=False)
    st.download_button(
        "⬇️ Exportar CSV",
        buff.getvalue(),
        file_name=f"presupuestos_{date.today()}.csv",
        mime="text/csv",
    )

def _render_presupuesto_modal(supabase, clientes, trabajadores, estados):
    from modules.presupuesto_detalle import recalcular_lineas_presupuesto
    from modules.presupuesto_convert import convertir_presupuesto_a_pedido
    from modules.presupuesto_pdf import _build_data_real, build_pdf_bytes, upload_pdf_to_storage

    pid = st.session_state.get("presupuesto_modal_id")
    if not pid:
        return

    # ================= CARGAR PRESUPUESTO =================
    try:
        pres_res = (
            supabase.table("presupuesto")
            .select("*")
            .eq("presupuestoid", pid)
            .single()
            .execute()
        )
        pres = getattr(pres_res, "data", None) or {}
        if not pres:
            empty_state("No se encontró el presupuesto.", icon="⚠️")
            return
    except Exception as e:
        st.error(f"❌ Error cargando presupuesto: {e}")
        return

    est_nombre = _label_from(estados, pres.get("estado_presupuestoid"))
    est_lower = (est_nombre or "").lower()
    bloqueado = _is_bloqueado(est_nombre)

    # Badge color (igual idea que cards)
    if "acept" in est_lower:
        color_estado = "#10b981"
    elif "rechaz" in est_lower:
        color_estado = "#ef4444"
    elif "convert" in est_lower:
        color_estado = "#6b7280"
    else:
        color_estado = "#3b82f6"

    numero = pres.get("numero") or "—"
    total = pres.get("total_estimada")

    # ================= CABECERA (card) =================
    with card():
        top1, top2 = st.columns([3, 2])
        with top1:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                  <div style="font-size:1.15rem;font-weight:800;">📄 Presupuesto {numero}</div>
                  <span style="background:#111827;color:#fff;padding:2px 10px;border-radius:999px;font-size:0.8rem;">
                    ID #{pid}
                  </span>
                  <span style="background:{color_estado};color:#fff;padding:2px 10px;border-radius:999px;font-size:0.8rem;font-weight:700;">
                    {est_nombre or "Sin estado"}
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(
                f"📅 {_safe(pres.get('fecha_presupuesto'))} · ⏳ Validez: {_safe(pres.get('fecha_validez'))}"
            )

        with top2:
            colm1, colm2 = st.columns(2)
            with colm1:
                try:
                    st.metric("Total", f"{float(total or 0):,.2f} €")
                except Exception:
                    st.metric("Total", _safe(total))
            with colm2:
                st.metric("ClienteID", _safe(pres.get("clienteid")))

        # acciones rápidas
        a1, a2, a3, a4 = st.columns([1, 1, 1, 1])
        with a1:
            if st.button("⬅️ Volver", use_container_width=True):
                st.session_state["show_presupuesto_modal"] = False
                st.session_state["presupuesto_modal_id"] = None
                st.rerun()
        with a2:
            st.button("🖨️ Imprimir", use_container_width=True, disabled=True)
        with a3:
            if st.button("🗑️ Eliminar", use_container_width=True, disabled=bloqueado):
                try:
                    supabase.table("presupuesto_detalle").delete().eq("presupuestoid", pid).execute()
                    supabase.table("presupuesto").delete().eq("presupuestoid", pid).execute()
                    st.success("🗑️ Presupuesto eliminado correctamente.")
                    st.session_state["show_presupuesto_modal"] = False
                    st.session_state["presupuesto_modal_id"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al eliminar: {e}")
        with a4:
            if "acept" in est_lower:
                if st.button("🧾 Convertir", use_container_width=True):
                    convertir_presupuesto_a_pedido(supabase, pid)
                    st.rerun()
            else:
                st.button("🧾 Convertir", use_container_width=True, disabled=True)

    # ================= BLOQUEO =================
    if bloqueado:
        st.warning("🔒 Este presupuesto está **Aceptado o Convertido** y no se puede editar.")
    else:
        st.info("✏️ Presupuesto editable (estado: Borrador o Enviado).")

    # ================= TABS =================
    tab1, tab2, tab3 = st.tabs(["🧾 Cabecera", "📦 Líneas", "📄 PDF"])

    # -------------------------------------------------
    # TAB 1 — Cabecera
    # -------------------------------------------------
    with tab1:
        with section("Datos del presupuesto", icon="🧾"):
            render_presupuesto_form(
                supabase,
                presupuestoid=pid,
                bloqueado=bloqueado,
            )

        # Recalcular (sección aparte)
        with section("Recalcular líneas por tarifas", icon="🔁"):
            fecha_manual = st.date_input(
                "Fecha de cálculo (opcional)",
                value=None,
                key=f"recalc_fecha_{pid}",
                help="Si se indica, se usará esta fecha en lugar de la fecha de validez.",
                disabled=bloqueado,
            )

            if st.button("🔁 Recalcular líneas", use_container_width=True, disabled=bloqueado):
                try:
                    fecha_calculo = fecha_manual or pres.get("fecha_validez")
                    recalcular_lineas_presupuesto(
                        supabase,
                        presupuestoid=pid,
                        clienteid=pres.get("clienteid"),
                        fecha_validez=fecha_calculo,
                    )
                    st.success("✅ Líneas recalculadas.")
                    st.rerun()
                except Exception as _e:
                    st.error(f"❌ No se pudo recalcular: {_e}")

    # -------------------------------------------------
    # TAB 2 — Líneas
    # -------------------------------------------------
    with tab2:
        with section("Detalle de líneas", icon="📦"):
            render_presupuesto_detalle(
                supabase,
                presupuestoid=pid,
                clienteid=pres.get("clienteid"),
                fecha_validez=pres.get("fecha_validez"),
                bloqueado=bloqueado,
            )

    # -------------------------------------------------
    # TAB 3 — PDF
    # -------------------------------------------------
    with tab3:
        with section("Documento del presupuesto (PDF)", icon="📄"):
            try:
                data_real = _build_data_real(supabase, pid)
                pdf_bytes, file_name = build_pdf_bytes(data_real)

                pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
                st.markdown(
                    f'<iframe src="data:application/pdf;base64,{pdf_b64}" width="100%" height="720px"></iframe>',
                    unsafe_allow_html=True,
                )

                d1, d2 = st.columns([2, 1])
                with d1:
                    st.download_button(
                        "⬇️ Descargar PDF",
                        data=pdf_bytes,
                        file_name=file_name,
                        mime="application/pdf",
                        use_container_width=True,
                    )
                with d2:
                    if st.button("☁️ Subir a Storage", use_container_width=True):
                        url = upload_pdf_to_storage(
                            supabase, pdf_bytes, file_name, bucket="presupuestos"
                        )
                        st.success("📤 PDF subido a Supabase Storage.")
                        if url:
                            st.markdown(f"🔗 [Abrir PDF en Storage]({url})")
            except Exception as e:
                st.error(f"❌ Error generando PDF: {e}")

def render_presupuesto_lista(supabase):
    apply_orbe_theme()

    # ---------------------------
    # Estado UI (como cliente_lista)
    # ---------------------------
    defaults = {
        "pres_page": 1,
        "pres_view": "Tarjetas",
        "show_presupuesto_modal": False,
        "presupuesto_modal_id": None,
        "show_creator": False,
        "pres_q": "",
        "pres_estado": "Todos",
        "pres_cliente_filtro": "Todos",
        "pres_orden": "Últimos creados",
        "pres_result_count": 0,
        "pres_last_fingerprint": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    page_size_cards, page_size_table = 12, 30

    # Catálogos
    clientes = load_clientes(supabase)
    trabajadores = load_trabajadores(supabase)
    estados = _load_estados_presupuesto(supabase)

    # ---------------------------
    # MODO FICHA (si está abierto, no pintes listado debajo)
    # ---------------------------
    if st.session_state.get("show_presupuesto_modal") and st.session_state.get("presupuesto_modal_id"):
        _render_presupuesto_modal(supabase, clientes, trabajadores, estados)
        return

    # ---------------------------
    # Página
    # ---------------------------
    with page(
        "Gestión de presupuestos",
        "Visualiza, filtra, edita y genera presupuestos con tarifas y validez.",
        icon="💼",
    ):
        # =================================================
        # 🔎 Buscador + KPI resultados
        # =================================================
        c1, c2 = st.columns([3, 1])
        with c1:
            q = st.text_input(
                "Buscar presupuesto",
                placeholder="Número o referencia cliente…",
                key="pres_q",
            )
        with c2:
            st.metric("Resultados (página)", st.session_state.get("pres_result_count", 0))

        # =================================================
        # 🎛 Filtros
        # =================================================
        with st.expander("⚙️ Filtros avanzados", expanded=False):
            f1, f2, f3 = st.columns(3)
            with f1:
                estado_sel = st.selectbox(
                    "Estado",
                    ["Todos"] + list(estados.keys()),
                    key="pres_estado",
                )
            with f2:
                cliente_filtro = st.selectbox(
                    "Cliente",
                    ["Todos"] + list(clientes.keys()),
                    key="pres_cliente_filtro",
                )
            with f3:
                orden_sel = st.selectbox(
                    "Ordenar por",
                    ["Últimos creados", "Fecha de presupuesto"],
                    key="pres_orden",
                )

            f4, f5 = st.columns([1, 1])
            with f4:
                st.radio(
                    "Vista",
                    ["Tarjetas", "Tabla"],
                    horizontal=True,
                    key="pres_view",
                )
            with f5:
                if st.button("➕ Nuevo presupuesto", use_container_width=True):
                    st.session_state["show_creator"] = True
                    st.rerun()

        # ✅ Reset de página cuando cambien filtros/búsqueda (como cliente_lista)
        fingerprint = (
            (q or "").strip(),
            estado_sel,
            cliente_filtro,
            orden_sel,
            st.session_state.get("pres_view"),
        )
        if st.session_state.get("pres_last_fingerprint") != fingerprint:
            st.session_state["pres_page"] = 1
            st.session_state["pres_last_fingerprint"] = fingerprint

        st.markdown("---")

        # =================================================
        # 🆕 Constructor inline
        # =================================================
        if st.session_state.get("show_creator"):
            with section("Nuevo presupuesto", icon="🆕"):
                _render_nuevo_presupuesto_inline(supabase)
            st.markdown("")

        # =================================================
        # 📥 Consulta paginada
        # =================================================
        total, rows = 0, []
        try:
            # Count
            base_count = supabase.table("presupuesto").select("presupuestoid", count="exact")

            if q:
                base_count = base_count.or_(f"numero.ilike.%{q}%,referencia_cliente.ilike.%{q}%")

            if estado_sel != "Todos":
                base_count = base_count.eq("estado_presupuestoid", estados[estado_sel])

            if cliente_filtro != "Todos":
                base_count = base_count.eq("clienteid", clientes.get(cliente_filtro))

            cres = base_count.execute()
            total = getattr(cres, "count", None) or 0

            # Paginación
            per_page = page_size_cards if st.session_state["pres_view"] == "Tarjetas" else page_size_table
            start, end = _range(st.session_state["pres_page"], per_page)

            # Query base
            base = supabase.table("presupuesto").select("*")

            if q:
                base = base.or_(f"numero.ilike.%{q}%,referencia_cliente.ilike.%{q}%")

            if estado_sel != "Todos":
                base = base.eq("estado_presupuestoid", estados[estado_sel])

            if cliente_filtro != "Todos":
                base = base.eq("clienteid", clientes.get(cliente_filtro))

            # Orden
            if orden_sel == "Últimos creados":
                try:
                    rows_res = base.order("creado_en", desc=True).range(start, end).execute()
                except Exception:
                    rows_res = base.order("fecha_presupuesto", desc=True).range(start, end).execute()
            else:
                rows_res = base.order("fecha_presupuesto", desc=True).range(start, end).execute()

            rows = getattr(rows_res, "data", None) or []
            st.session_state["pres_result_count"] = len(rows)

        except Exception as e:
            st.error(f"❌ Error cargando presupuestos: {e}")
            rows = []
            total = 0

        # =================================================
        # Empty state
        # =================================================
        if not rows:
            empty_state("No hay presupuestos que coincidan con los filtros.", icon="📭")
            return

        # =================================================
        # 🔢 Paginación UI
        # =================================================
        per_page = page_size_cards if st.session_state["pres_view"] == "Tarjetas" else page_size_table
        total_pages = max(1, math.ceil((total or 0) / per_page))

        st.caption(f"Página {st.session_state['pres_page']} / {total_pages} · Total: {total}")

        p1, p2, p3 = st.columns(3)
        with p1:
            if st.button("⬅️ Anterior", disabled=st.session_state["pres_page"] <= 1):
                st.session_state["pres_page"] -= 1
                st.rerun()
        with p2:
            st.write("")
        with p3:
            if st.button("Siguiente ➡️", disabled=st.session_state["pres_page"] >= total_pages):
                st.session_state["pres_page"] += 1
                st.rerun()

        st.markdown("---")

        # =================================================
        # Render
        # =================================================
        if st.session_state["pres_view"] == "Tarjetas":
            cols = st.columns(3)
            for i, r in enumerate(rows):
                with cols[i % 3]:
                    _render_card(r, supabase, clientes, trabajadores, estados)
        else:
            _render_table(rows)
