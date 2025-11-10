# modules/presupuesto_lista.py
import io
import math
import pandas as pd
import streamlit as st
from datetime import date, datetime, timedelta

from modules.pedido_models import load_clientes, load_trabajadores
from modules.presupuesto_form import render_presupuesto_form
from modules.presupuesto_detalle import render_presupuesto_detalle

# ======================================================
# PDF panel (import seguro con fallback)
# ======================================================
_PDF_PANEL_OK = True
try:
    from modules.pdf_templates import render_presupuesto_pdf_panel
except Exception as _pdf_err:
    _PDF_PANEL_OK = False
    _PDF_IMPORT_ERROR = _pdf_err

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
    try:
        rows = supabase.table("estado_presupuesto").select("*").order("estado_presupuestoid").execute().data or []
        # Aseguramos nombres estándar (Borrador, Enviado, Aceptado, Rechazado, Caducado)
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
    if not estado_nombre:
        return False
    e = estado_nombre.lower()
    # Bloquea edición si aceptado o convertido
    return ("acept" in e) or ("convert" in e)
def _render_nuevo_presupuesto_inline(supabase):
    """Constructor de presupuesto rápido con fecha y validez automáticas."""
    st.markdown("### 🆕 Nuevo presupuesto")

    clientes = load_clientes(supabase)
    productos = (
        supabase.table("producto")
        .select("productoid, nombre, precio_generico, familia_productoid, impuestoid")
        .order("nombre")
        .execute()
        .data
        or []
    )
    col1, col2 = st.columns(2)
    with col1:
        cliente_sel = st.selectbox(
            "👤 Cliente",
            ["(selecciona)"] + list(clientes.keys()),
            key="nuevo_pres_cliente"
        )
    with col2:
        fecha_pres = st.date_input(
            "📅 Fecha del presupuesto",
            value=date.today(),
            key="nuevo_pres_fecha"
        )

    col3, col4 = st.columns(2)
    with col3:
        fecha_validez = st.date_input(
            "⏳ Validez hasta",
            value=date.today() + timedelta(days=30),
            key="nuevo_pres_validez"
        )
    with col4:
        producto_sel = st.selectbox(
            "📦 Producto inicial",
            ["(selecciona)"] + [p["nombre"] for p in productos],
            key="nuevo_pres_producto"
        )

    cantidad = st.number_input(
        "Cantidad", min_value=1, step=1, value=1, key="nuevo_pres_cantidad"
    )

    crear = st.button("💾 Crear presupuesto", type="primary", use_container_width=True, key="nuevo_pres_crear")
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

    # Región por dirección de envío (fallback fiscal)
    regionid = None
    try:
        r = (
            supabase.table("cliente_direccion")
            .select("regionid, tipo")
            .eq("clienteid", clienteid)
            .order("CASE WHEN tipo = 'envio' THEN 1 WHEN tipo = 'fiscal' THEN 2 ELSE 3 END")
            .limit(1)
            .execute()
            .data
        )
        if r:
            regionid = r[0].get("regionid")
    except Exception:
        pass

    # Número correlativo
    prefijo = f"PRES-{fecha_pres.year}-"
    existentes = (
        supabase.table("presupuesto")
        .select("numero")
        .ilike("numero", f"{prefijo}%")
        .execute()
        .data
        or []
    )
    usados = [int(x["numero"].split("-")[-1]) for x in existentes if x["numero"].split("-")[-1].isdigit()]
    nuevo_num = max(usados) + 1 if usados else 1
    numero = f"{prefijo}{nuevo_num:04d}"

    # Estado = Borrador (si existe)
    estadoid = None
    try:
        e = (
            supabase.table("estado_presupuesto")
            .select("estado_presupuestoid")
            .eq("nombre", "Borrador")
            .maybe_single()
            .execute()
            .data
        )
        if e:
            estadoid = e.get("estado_presupuestoid")
    except Exception:
        pass

    insert_pres = {
        "numero": numero,
        "clienteid": clienteid,
        "fecha_presupuesto": fecha_pres.isoformat(),   # ← usa la seleccionada
        "fecha_validez": fecha_validez.isoformat(),
        "observaciones": None,
        "facturar_individual": False,
        "total_estimada": 0.0,
        "editable": True,
        "regionid": regionid,
        "estado_presupuestoid": estadoid,
        "creado_en": datetime.now().isoformat(),       # ← CORRECCIÓN: columna real (no 'fecha_creacion')
    }

    try:
        pres = supabase.table("presupuesto").insert(insert_pres).execute().data[0]
    except Exception as e:
        st.error(f"❌ Error creando el presupuesto: {e}")
        return

    presupuestoid = pres["presupuestoid"]

    # Línea inicial con motor de tarifas — fecha de cálculo = validez (si se quiere “campaña de diciembre” etc.)
    try:
        from modules.precio_engine import calcular_precio_linea

        # ⚠️ MUY IMPORTANTE: pasar un date, NO un string
        fecha_calc = fecha_validez or fecha_pres

        precio_linea = calcular_precio_linea(
            supabase=supabase,
            clienteid=clienteid,
            productoid=producto["productoid"],
            cantidad=float(cantidad),
            fecha=fecha_calc,                 # ← date object
        )

        # Tomamos SIEMPRE los campos del engine (como el simulador)
        unit_bruto   = float(precio_linea.get("unit_bruto", producto.get("precio_generico", 0.0)))
        dto_pct      = float(precio_linea.get("descuento_pct", 0.0))
        iva_pct      = float(precio_linea.get("iva_pct", 21.0))
        subtotal     = float(precio_linea.get("subtotal_sin_iva", cantidad * unit_bruto * (1 - dto_pct/100)))
        total        = float(precio_linea.get("total_con_iva", subtotal * (1 + iva_pct/100)))

        linea = {
            "presupuestoid": presupuestoid,
            "productoid": producto["productoid"],
            "descripcion": producto["nombre"],
            "cantidad": float(cantidad),
            "precio_unitario": unit_bruto,                 # unitario BRUTO (antes de dto)
            "descuento_pct": dto_pct,
            "iva_pct": iva_pct,
            "importe_base": subtotal,                      # base tras dto (sin IVA)
            "importe_total_linea": total,                  # con IVA
            "fecha_alta": datetime.now().isoformat(),
            "tarifa_aplicada": precio_linea.get("tarifa_aplicada"),
            "nivel_tarifa": precio_linea.get("nivel_tarifa"),
            "iva_origen": precio_linea.get("iva_origen"),
        }
        supabase.table("presupuesto_detalle").insert(linea).execute()
    except Exception as e:
        st.warning(f"⚠️ Presupuesto creado, pero error en cálculo de la primera línea: {e}")

    # Recalcular totales
    try:
        from modules.presupuesto_detalle import actualizar_total_presupuesto
        actualizar_total_presupuesto(supabase, presupuestoid)
    except Exception:
        pass

    st.session_state["presupuesto_modal_id"] = presupuestoid
    st.session_state["show_presupuesto_modal"] = True
    st.success(f"✅ Presupuesto creado correctamente: {numero}")
    st.rerun()


# ======================================================
# 📄 Emitir presupuesto (generar PDF + marcar Enviado)
# ======================================================
def emitir_presupuesto(supabase, presupuestoid: int, estados: dict):
    """Genera el PDF final del presupuesto, lo sube a Supabase y cambia el estado a 'Enviado'."""
    try:
        # 1️⃣ Obtener presupuesto + cliente + líneas
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

        cliente = (
            supabase.table("cliente")
            .select("*")
            .eq("clienteid", pres["clienteid"])
            .maybe_single()
            .execute()
            .data
            or {}
        )

        direccion = {}
        if pres.get("direccion_envioid"):
            direccion = (
                supabase.table("cliente_direccion")
                .select("direccion, cp, ciudad, provincia, region(nombre)")
                .eq("cliente_direccionid", pres["direccion_envioid"])
                .maybe_single()
                .execute()
                .data
                or {}
            )

        region_nombre = "-"
        if direccion.get("region") and isinstance(direccion["region"], dict):
            region_nombre = direccion["region"].get("nombre")

        lineas = (
            supabase.table("presupuesto_detalle")
            .select("descripcion, cantidad, precio_unitario, descuento_pct, iva_pct, importe_base, importe_total_linea")
            .eq("presupuestoid", presupuestoid)
            .order("presupuesto_detalleid")
            .execute()
            .data
            or []
        )

        if not lineas:
            st.warning("⚠️ No se puede emitir un presupuesto vacío.")
            return

        total_base = sum([float(l.get("importe_base") or 0) for l in lineas])
        total_iva = sum([(float(l.get("importe_base") or 0) * float(l.get("iva_pct") or 0) / 100) for l in lineas])
        total_total = total_base + total_iva

        data_real = {
            "empresa": {
                "nombre": "EnteNova S.L.",
                "cif": "B-12345678",
                "direccion": "C/ Mayor 123",
                "cp": "28013",
                "ciudad": "Madrid",
                "web": "www.entenova.com",
                "pie": "EnteNova · Presupuestos · www.entenova.com",
            },
            "cliente": {
                "nombre": cliente.get("razon_social") or cliente.get("nombre_comercial") or "-",
                "identificador": cliente.get("cif_nif") or cliente.get("cif") or "-",
                "direccion": direccion.get("direccion") or "-",
                "cp": direccion.get("cp") or "-",
                "ciudad": direccion.get("ciudad") or "-",
                "provincia": direccion.get("provincia") or "-",
                "region": region_nombre,
            },
            "presupuesto": {
                "numero": pres.get("numero"),
                "fecha": pres.get("fecha_presupuesto"),
                "notas": pres.get("observaciones") or "Oferta válida 30 días. Portes no incluidos.",
                "total": total_total,
            },
            "lineas": [
                {
                    "concepto": l["descripcion"],
                    "unidades": l["cantidad"],
                    "precio": l["precio_unitario"],
                    "dto": l.get("descuento_pct") or 0,
                    "iva": l.get("iva_pct") or 0,
                    "base": l.get("importe_base"),
                    "total": l.get("importe_total_linea"),
                }
                for l in lineas
            ],
            "totales": {
                "base": total_base,
                "iva": total_iva,
                "total": total_total,
            },
        }

        # 2️⃣ Generar y subir PDF
        from modules.pdf_templates import render_presupuesto_pdf_panel
        st.info("📄 Generando documento PDF final...")
        render_presupuesto_pdf_panel(
            data_real,
            supabase=supabase,
            bucket="presupuestos",
            height_preview=500,
        )

        # 3️⃣ Marcar estado como “Enviado” (si existe)
        enviado_id = None
        for nombre, eid in estados.items():
            if "envi" in nombre.lower():
                enviado_id = eid
                break

        if enviado_id:
            supabase.table("presupuesto").update({
                "estado_presupuestoid": enviado_id,
                "editable": False,
                "fecha_envio": datetime.now().isoformat(),
            }).eq("presupuestoid", presupuestoid).execute()
            st.success("📨 Presupuesto marcado como 'Enviado'.")
        else:
            st.warning("⚠️ No se encontró el estado 'Enviado' en la tabla 'estado_presupuesto'.")

    except Exception as e:
        st.error(f"❌ Error al emitir presupuesto: {e}")



# ======================
# Tarjeta (muestra también ID interno)
# ======================
def _render_card(r, supabase, clientes, trabajadores, estados):
    cli = _label_from(clientes, r.get("clienteid"))
    tra = _label_from(trabajadores, r.get("trabajadorid"))
    est_nombre = _label_from(estados, r.get("estado_presupuestoid"))
    bloqueado = _is_bloqueado(est_nombre)

    # Color estado
    if 'acept' in (est_nombre or '').lower():
        color_estado = "#10b981"
    elif 'rechaz' in (est_nombre or '').lower():
        color_estado = "#ef4444"
    elif 'convert' in (est_nombre or '').lower():
        color_estado = "#6b7280"
    else:
        color_estado = "#3b82f6"

    pres_id = r.get("presupuestoid")

    st.markdown(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin-bottom:10px;background:#fff;">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="background:#111827;color:#fff;padding:2px 8px;border-radius:999px;font-size:0.75rem;">
                        #{pres_id}
                    </span>
                    <div><b>{_safe(r.get('numero'))}</b> — {_safe(cli)}</div>
                </div>
                <span style="background:{color_estado};color:#fff;padding:3px 8px;border-radius:8px;font-size:0.8rem;">
                    {est_nombre or '-'}
                </span>
            </div>
            <div style="margin-top:4px;color:#555;font-size:0.9rem;">
                📅 {_safe(r.get("fecha_presupuesto"))} &nbsp; | &nbsp; 👤 {_safe(tra)} &nbsp; | &nbsp; 💶 {_safe(r.get("total_estimada"))} €
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("📄 Ver ficha", key=f"pres_ficha_{pres_id}", use_container_width=True):
        st.session_state["presupuesto_modal_id"] = pres_id
        st.session_state["show_presupuesto_modal"] = True
        st.rerun()


def _render_table(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No hay presupuestos.")
        return
    cols = ["presupuestoid", "numero", "clienteid", "estado_presupuestoid", "fecha_presupuesto", "fecha_validez", "total_estimada"]
    # Añade columnas si no existen
    for c in cols:
        if c not in df.columns:
            df[c] = None
    st.dataframe(df[cols], use_container_width=True, hide_index=True)
    buff = io.StringIO()
    df[cols].to_csv(buff, index=False)
    st.download_button("⬇️ Exportar CSV", buff.getvalue(), file_name=f"presupuestos_{date.today()}.csv", mime="text/csv")

# ======================================================
# Render principal (mejorado con filtro de cliente y orden)
# ======================================================
def render_presupuesto_lista(supabase):
    st.header("💼 Gestión de presupuestos")
    st.caption("Visualiza, edita y genera presupuestos con tarifas y validez.")

    # Estado UI
    st.session_state.setdefault("pres_page", 1)
    st.session_state.setdefault("pres_view", "Tarjetas")
    st.session_state.setdefault("show_presupuesto_modal", False)
    st.session_state.setdefault("presupuesto_modal_id", None)
    st.session_state.setdefault("show_creator", False)

    page_size_cards, page_size_table = 12, 30

    # Catálogos
    clientes = load_clientes(supabase)       # {nombre: id}
    trabajadores = load_trabajadores(supabase)
    estados = _load_estados_presupuesto(supabase)

    # =======================
    # Filtros superiores
    # =======================
    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
    with c1:
        q = st.text_input("🔎 Buscar", placeholder="Número o referencia…", key="pres_q")
    with c2:
        estado_sel = st.selectbox("Estado", ["Todos"] + list(estados.keys()), key="pres_estado")
    with c3:
        # Orden por creación (defecto) o por fecha del documento
        orden_sel = st.selectbox("Ordenar por", ["Últimos creados", "Fecha de presupuesto"], index=0, key="pres_orden")
    with c4:
        # Filtro por cliente
        cliente_filtro = st.selectbox("Cliente", ["Todos"] + list(clientes.keys()), key="pres_cliente_filtro")
    with c5:
        if st.button("➕ Nuevo presupuesto", use_container_width=True):
            st.session_state["show_creator"] = True
            st.rerun()

    if st.session_state.get("show_creator"):
        with st.container(border=True):
            _render_nuevo_presupuesto_inline(supabase)
        st.markdown("---")

    # =======================
    # Consulta paginada
    # =======================
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
        total = getattr(cres, "count", None) or len(cres.data or [])

        # Paginación
        per_page = page_size_cards if st.session_state.pres_view == "Tarjetas" else page_size_table
        start, end = _range(st.session_state.pres_page, per_page)

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
            # Prioriza creado_en si existe; si no existe en tu tabla, quedará “sin efecto”
            try:
                rows = base.order("creado_en", desc=True).range(start, end).execute().data or []
            except Exception:
                rows = base.order("fecha_presupuesto", desc=True).range(start, end).execute().data or []
        else:
            rows = base.order("fecha_presupuesto", desc=True).range(start, end).execute().data or []

    except Exception as e:
        st.error(f"❌ Error cargando presupuestos: {e}")

    # Paginación UI
    total_pages = max(1, math.ceil(total / (page_size_cards if st.session_state.pres_view == "Tarjetas" else page_size_table)))
    st.caption(f"Mostrando página {st.session_state.pres_page} de {total_pages} — Total: {total} presupuestos")

    p1, p2, p3, _ = st.columns([1, 1, 1, 5])
    if p1.button("⏮️", disabled=st.session_state.pres_page <= 1):
        st.session_state.pres_page = 1; st.rerun()
    if p2.button("◀️", disabled=st.session_state.pres_page <= 1):
        st.session_state.pres_page -= 1; st.rerun()
    if p3.button("▶️", disabled=st.session_state.pres_page >= total_pages):
        st.session_state.pres_page += 1; st.rerun()

    st.markdown("---")

    # Render
    if not rows:
        st.info("📭 No hay presupuestos que coincidan con los filtros.")
        return

    view = st.session_state.pres_view
    if view == "Tarjetas":
        cols = st.columns(3)
        for i, r in enumerate(rows):
            with cols[i % 3]:
                _render_card(r, supabase, clientes, trabajadores, estados)
    else:
        _render_table(rows)

    # Modal
    if st.session_state.get("show_presupuesto_modal"):
        _render_presupuesto_modal(supabase, clientes, trabajadores, estados)


# ======================
# MODAL PRESUPUESTO COMPLETO (versión optimizada y unificada)
# ======================
def _render_presupuesto_modal(supabase, clientes, trabajadores, estados):
    pid = st.session_state.get("presupuesto_modal_id")
    if not pid:
        return

    # ================= CARGAR PRESUPUESTO =================
    try:
        pres = (
            supabase.table("presupuesto")
            .select("*")
            .eq("presupuestoid", pid)
            .single()
            .execute()
            .data
        )
        if not pres:
            st.warning("⚠️ No se encontró el presupuesto.")
            return
    except Exception as e:
        st.error(f"❌ Error cargando presupuesto: {e}")
        return

    est_nombre = _label_from(estados, pres.get("estado_presupuestoid"))
    bloqueado = _is_bloqueado(est_nombre)

    # ================= CABECERA =================
    st.markdown("---")
    st.markdown(
        f"### 📄 Ficha del presupuesto {pres.get('numero') or '—'} "
        f"<span style='color:#6b7280'>(ID interno: #{pid})</span> — "
        f"Estado: **{est_nombre or 'Sin estado'}**",
        unsafe_allow_html=True
    )

    # ================= BOTONERA SUPERIOR =================
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("⬅️ Cerrar ficha", use_container_width=True):
            st.session_state["show_presupuesto_modal"] = False
            st.rerun()
    with c2:
        if st.button("🗑️ Eliminar presupuesto", use_container_width=True, disabled=bloqueado):
            try:
                supabase.table("presupuesto_detalle").delete().eq("presupuestoid", pid).execute()
                supabase.table("presupuesto").delete().eq("presupuestoid", pid).execute()
                st.success("🗑️ Presupuesto eliminado correctamente.")
                st.session_state["show_presupuesto_modal"] = False
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al eliminar: {e}")

    # ================= ESTADO / BLOQUEO =================
    if bloqueado:
        st.warning("🔒 Este presupuesto está **Aceptado o Convertido** y no se puede editar.")
    else:
        st.info("✏️ Presupuesto editable (estado: Borrador o Enviado).")

    # ================= PDF (PRIMERO EN ORDEN LÓGICO) =================
    st.markdown("---")
    st.markdown("#### 🧾 Documento del presupuesto (PDF)")

    try:
        # Import seguro de funciones
        from modules.presupuesto_pdf import build_pdf_bytes, upload_pdf_to_storage

        # Obtener cliente y dirección
        cliente, direccion = {}, {}
        if pres.get("clienteid"):
            cliente = (
                supabase.table("cliente")
                .select("*")
                .eq("clienteid", pres["clienteid"])
                .single()
                .execute()
                .data
                or {}
            )

        if pres.get("direccion_envioid"):
            direccion = (
                supabase.table("cliente_direccion")
                .select("direccion, cp, ciudad, provincia, region(nombre)")
                .eq("cliente_direccionid", pres["direccion_envioid"])
                .single()
                .execute()
                .data
                or {}
            )

        region_nombre = "-"
        if direccion.get("region") and isinstance(direccion["region"], dict):
            region_nombre = direccion["region"].get("nombre")

        # Cargar líneas
        lineas = (
            supabase.table("presupuesto_detalle")
            .select("descripcion, cantidad, precio_unitario, descuento_pct, iva_pct, importe_base, importe_total_linea")
            .eq("presupuestoid", pid)
            .order("presupuesto_detalleid", desc=False)
            .execute()
            .data
            or []
        )

        if not lineas:
            st.info("📭 Este presupuesto no tiene líneas aún.")
        else:
            total_base = sum(float(l.get("importe_base") or 0) for l in lineas)
            total_iva = sum(
                (float(l.get("importe_base") or 0) * float(l.get("iva_pct") or 0) / 100)
                for l in lineas
            )
            total_total = total_base + total_iva

            data_real = {
                "empresa": {
                    "nombre": "EnteNova S.L.",
                    "cif": "B-12345678",
                    "direccion": "C/ Mayor 123",
                    "cp": "28013",
                    "ciudad": "Madrid",
                    "web": "www.entenova.com",
                    "pie": "EnteNova · Presupuestos · www.entenova.com",
                },
                "cliente": {
                    "nombre": cliente.get("razon_social") or cliente.get("nombre_comercial") or "-",
                    "identificador": cliente.get("cif_nif") or cliente.get("cif") or "-",
                    "direccion": direccion.get("direccion") or "-",
                    "cp": direccion.get("cp") or "-",
                    "ciudad": direccion.get("ciudad") or "-",
                    "provincia": direccion.get("provincia") or "-",
                    "region": region_nombre,
                },
                "presupuesto": {
                    "numero": pres.get("numero"),
                    "fecha": pres.get("fecha_presupuesto"),
                    "notas": pres.get("observaciones") or "Oferta válida 30 días. Portes no incluidos.",
                    "total": total_total,
                },
                "lineas": [
                    {
                        "concepto": l["descripcion"],
                        "unidades": l["cantidad"],
                        "precio": l["precio_unitario"],
                        "dto": l.get("descuento_pct") or 0,
                        "iva": l.get("iva_pct") or 0,
                        "base": l.get("importe_base"),
                        "total": l.get("importe_total_linea"),
                    }
                    for l in lineas
                ],
                "totales": {
                    "base": total_base,
                    "iva": total_iva,
                    "total": total_total,
                },
            }

            # Generar bytes del PDF correctamente (compatible con tuple o bytes)
            pdf_result = build_pdf_bytes(data_real)
            if isinstance(pdf_result, tuple):
                pdf_bytes, file_name = pdf_result
            else:
                pdf_bytes = pdf_result
                file_name = f"presupuesto_{pres.get('numero','sin_numero')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"


            import base64
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{pdf_b64}" width="100%" height="720px"></iframe>',
                unsafe_allow_html=True,
            )

            # Botones PDF
            col1, col2 = st.columns([2, 1])
            with col1:
                st.download_button(
                    "⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=file_name,
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"download_pdf_{pid}",
                )
            with col2:
                if st.button("☁️ Subir a Storage", use_container_width=True, key=f"upload_pdf_{pid}"):
                    try:
                        url = upload_pdf_to_storage(
                            supabase, pdf_bytes, file_name, bucket="presupuestos"
                        )
                        st.success("📤 PDF subido a Supabase Storage.")
                        if url:
                            st.markdown(f"🔗 [Abrir en Supabase Storage]({url})")
                    except Exception as e:
                        st.error(f"❌ No se pudo subir el PDF: {e}")
    except Exception as e:
        if "Bucket not found" in str(e):
            st.warning("⚠️ No se encontró el bucket 'presupuestos'. Créalo en Supabase Storage.")
        else:
            st.error(f"❌ Error generando PDF: {e}")

    # ================= CONVERTIR A PEDIDO =================
    from modules.presupuesto_convert import convertir_presupuesto_a_pedido
    if pres.get("estado_presupuestoid") == 3:  # ✅ Aceptado
        st.markdown("---")
        if st.button("🧾 Convertir a Pedido", use_container_width=True):
            convertir_presupuesto_a_pedido(supabase, pid)
            st.rerun()

    # ================= RECALCULAR LÍNEAS =================
    st.markdown("---")
    from modules.presupuesto_detalle import recalcular_lineas_presupuesto

    st.markdown("#### 🔁 Recalcular líneas según tarifas vigentes")
    fecha_manual = st.date_input(
        "📅 Fecha de cálculo (opcional)",
        value=None,
        key=f"recalc_fecha_{pid}",
        help="Si se indica, se usará esta fecha en lugar de la fecha de validez.",
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
            st.rerun()
        except Exception as _e:
            st.error(f"❌ No se pudo recalcular: {_e}")

    # ================= FORMULARIO Y DETALLE =================
    st.markdown("---")
    render_presupuesto_form(supabase, presupuestoid=pid, bloqueado=bloqueado)
    st.markdown("---")
    render_presupuesto_detalle(
        supabase,
        presupuestoid=pid,
        clienteid=pres.get("clienteid"),
        fecha_validez=pres.get("fecha_validez"),
        bloqueado=bloqueado,
    )

