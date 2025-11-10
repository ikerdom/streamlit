import io
import math
import pandas as pd
import streamlit as st
from datetime import date

from modules.cliente_models import (
    load_estados_cliente,
    load_categorias,
    load_grupos,
    load_trabajadores,
    load_formas_pago,
    get_estado_label,
    get_categoria_label,
    get_grupo_label,
    get_trabajador_label,
    get_formapago_label,
)

from modules.orbe_theme import apply_orbe_theme

# Formularios
from modules.cliente_direccion_form import render_direccion_form
from modules.cliente_facturacion_form import render_facturacion_form
from modules.cliente_observacion_form import render_observaciones_form
from modules.cliente_crm_form import render_crm_form
from modules.cliente_documento_form import render_documento_form
from modules.cliente_contacto_form import render_contacto_form

# =========================================================
# 🔧 Utils
# =========================================================
def _safe(v, d="-"):
    return v if v not in (None, "", "null") else d

def _range(page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size - 1
    return start, end

def _build_search_or(s, fields=("razon_social", "identificador")):
    s = (s or "").strip()
    if not s:
        return None
    return ",".join([f"{f}.ilike.%{s}%" for f in fields])

# =========================================================
# 🧭 Vista principal
# =========================================================

def render_cliente_lista(supabase):
    apply_orbe_theme()

    """Vista principal de clientes — versión profesional coherente con la ficha."""
    st.header("🏢 Gestión de clientes")
    st.caption("Consulta, filtra y accede a la ficha completa de tus clientes.")

    # Estado de sesión inicial
    defaults = {
        "cli_page": 1,
        "cli_view": "Tarjetas",
        "cli_sort": "razon_social ASC",
        "show_cliente_modal": False,
        "cliente_modal_id": None,
        "confirm_delete": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    # Cargar catálogos
    estados = load_estados_cliente(supabase)
    categorias = load_categorias(supabase)
    grupos = load_grupos(supabase)
    trabajadores = load_trabajadores(supabase)
    fpagos = load_formas_pago(supabase)
    # ---------------------------------------------------------
    # 🎛️ Cabecera y buscador avanzado
    # ---------------------------------------------------------
    st.markdown("""
    <div style="background:#eef2ff;padding:16px 20px;border-radius:10px;margin-bottom:12px;
                border-left:5px solid #3b82f6;">
        <h3 style="margin:0;color:#1e3a8a;">🏢 Panel de Clientes</h3>
        <p style="color:#374151;margin:2px 0 8px 0;font-size:0.9rem;">
            Gestiona tus clientes activos, busca por nombre o identificador y filtra por estado o trabajador asignado.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 🔍 Buscador con autocompletado y contador
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input("Buscar cliente", placeholder="Escribe para buscar...", key="cli_q", help="Filtra en tiempo real por nombre o identificador.")
    with c2:
        st.metric("👥 Resultados", st.session_state.get("cli_result_count", 0))

    # Autocompletado simple (solo visual, no ejecuta query)
    if q and len(q) >= 2:
        try:
            sugerencias = (
                supabase.table("cliente")
                .select("razon_social")
                .ilike("razon_social", f"%{q}%")
                .limit(5)
                .execute()
                .data
            ) or []
            if sugerencias:
                st.caption("🔎 Sugerencias:")
                for s in sugerencias:
                    st.markdown(f"- {s['razon_social']}")
        except Exception:
            pass

    st.markdown("---")

    # ---------------------------------------------------------
    # 🎛️ Filtros reorganizados
    # ---------------------------------------------------------
    with st.expander("⚙️ Filtros de búsqueda avanzada", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            estado_sel = st.selectbox("Estado", ["Todos"] + list(estados.keys()), key="cli_estado")
        with c2:
            categoria_sel = st.selectbox("Categoría", ["Todas"] + list(categorias.keys()), key="cli_categoria")
        with c3:
            grupo_sel = st.selectbox("Grupo", ["Todos"] + list(grupos.keys()), key="cli_grupo")
        with c4:
            fpago_sel = st.selectbox("Forma de pago", ["Todas"] + list(fpagos.keys()), key="cli_fpago")

        c5, c6 = st.columns([2, 2])
        with c5:
            trab_sel = st.selectbox("Trabajador asignado", ["Todos"] + list(trabajadores.keys()), key="cli_trab")
        with c6:
            view = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, key="cli_view")

    # ---------------------------------------------------------
    # 📊 Carga de clientes
    # ---------------------------------------------------------
    clientes, total = [], 0
    try:
        base = supabase.table("cliente").select(
            "clienteid, razon_social, identificador, estadoid, categoriaid, grupoid, trabajadorid, formapagoid"
        ).eq("tipo_cliente", "cliente")

        or_filter = _build_search_or(q)
        if or_filter:
            base = base.or_(or_filter)
        if estado_sel != "Todos" and estado_sel in estados:
            base = base.eq("estadoid", estados[estado_sel])
        if categoria_sel != "Todas" and categoria_sel in categorias:
            base = base.eq("categoriaid", categorias[categoria_sel])
        if grupo_sel != "Todos" and grupo_sel in grupos:
            base = base.eq("grupoid", grupos[grupo_sel])
        if trab_sel != "Todos" and trab_sel in trabajadores:
            base = base.eq("trabajadorid", trabajadores[trab_sel])
        if fpago_sel != "Todas" and fpago_sel in fpagos:
            base = base.eq("formapagoid", fpagos[fpago_sel])

        field, direction = st.session_state.cli_sort.split(" ")
        base = base.order(field, desc=(direction.upper() == "DESC"))

        data = base.execute()
        clientes = data.data or []
        total = len(clientes)
        st.session_state["cli_result_count"] = total

    except Exception as e:
        st.error(f"❌ Error cargando clientes: {e}")

    # ---------------------------------------------------------
    # 📈 KPIs rápidos
    # ---------------------------------------------------------
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Total clientes", total)
    col2.metric("👁️ Vista", st.session_state.cli_view)
    col3.metric("↕️ Orden", st.session_state.cli_sort)

    # ---------------------------------------------------------
    # 🧾 Listado
    # ---------------------------------------------------------
    if not clientes:
        st.info("📭 No hay clientes que coincidan con los filtros.")
        return

    st.caption(f"Mostrando {total} resultados")
    st.markdown("---")

    if view == "Tarjetas":
        # 🔄 Cargamos catálogos solo una vez (sin repetir por cliente)
        estado_labels = {v: k for k, v in estados.items()}
        categoria_labels = {v: k for k, v in categorias.items()}
        grupo_labels = {v: k for k, v in grupos.items()}
        trabajador_labels = {v: k for k, v in trabajadores.items()}
        fpago_labels = {v: k for k, v in fpagos.items()}

        # 🔄 Traer presupuestos recientes de todos los clientes de una vez
        ids_clientes = [c["clienteid"] for c in clientes]
        presupuestos = {}
        if ids_clientes:
            try:
                pres_data = (
                    supabase.table("presupuesto")
                    .select("clienteid, estado_presupuestoid, fecha_presupuesto")
                    .in_("clienteid", ids_clientes)
                    .order("fecha_presupuesto", desc=True)
                    .execute()
                    .data or []
                )
                for p in pres_data:
                    cid = p["clienteid"]
                    if cid not in presupuestos:
                        presupuestos[cid] = p  # solo el más reciente
            except Exception:
                presupuestos = {}

        cols = st.columns(3)
        for i, c in enumerate(clientes):
            c["presupuesto_info"] = presupuestos.get(c["clienteid"])
            with cols[i % 3]:
                _render_card(c, supabase)

    # ---------------------------------------------------------
    # 📄 Modal activo
    # ---------------------------------------------------------
    if st.session_state.get("show_cliente_modal"):
        render_cliente_modal(supabase)
def _render_card(c, supabase):
    apply_orbe_theme()

    """Tarjeta visual mejorada del cliente (coherente con la ficha modal)."""
    razon = _safe(c.get("razon_social"))
    ident = _safe(c.get("identificador"))
    estado = get_estado_label(c.get("estadoid"), supabase)
    categoria = get_categoria_label(c.get("categoriaid"), supabase)
    grupo = get_grupo_label(c.get("grupoid"), supabase)
    trabajador = get_trabajador_label(c.get("trabajadorid"), supabase)
    forma_pago = get_formapago_label(c.get("formapagoid"), supabase)

    # Último presupuesto
    try:
        pres = (
            supabase.table("presupuesto")
            .select("estado_presupuestoid, fecha_presupuesto")
            .eq("clienteid", c["clienteid"])
            .order("fecha_presupuesto", desc=True)
            .limit(1)
            .execute()
        )
        pres_estadoid = pres.data[0]["estado_presupuestoid"] if pres.data else None
        pres_fecha = pres.data[0]["fecha_presupuesto"] if pres.data else None
        estado_map = {1: "Pendiente", 2: "Aceptado", 3: "Rechazado"}
        pres_estado = estado_map.get(pres_estadoid, "Sin presupuesto")
    except Exception:
        pres_estado, pres_fecha = "Sin presupuesto", None

    # Colores
    color_estado = {
        "Activo": "#10b981",
        "Potencial": "#3b82f6",
        "Suspendido": "#dc2626",
    }.get(estado, "#6b7280")

    color_pres = {
        "Aceptado": "#16a34a",
        "Pendiente": "#f59e0b",
        "Rechazado": "#dc2626",
        "Sin presupuesto": "#6b7280",
    }.get(pres_estado, "#6b7280")

    st.markdown(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;
                    background:#f9fafb;padding:14px;margin-bottom:14px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:1.05rem;font-weight:600;">🏢 {razon}</div>
                    <div style="color:#6b7280;font-size:0.9rem;">{ident}</div>
                </div>
                <div style="color:{color_estado};font-weight:600;">{estado}</div>
            </div>
            <div style="margin-top:8px;font-size:0.9rem;line-height:1.4;">
                👥 <b>Grupo:</b> {grupo}<br>
                🧩 <b>Categoría:</b> {categoria}<br>
                💳 <b>Pago:</b> {forma_pago}<br>
                🧑 <b>Trabajador:</b> {trabajador}<br>
                <span style="color:{color_pres};font-weight:600;">📦 {pres_estado}</span>
                {'<div style="color:#4b5563;font-size:0.8rem;">🗓️ '+pres_fecha+'</div>' if pres_fecha else ''}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("📄 Ficha", key=f"ficha_cli_{c['clienteid']}", use_container_width=True):
            st.session_state.update({
                "cliente_modal_id": c["clienteid"],
                "show_cliente_modal": True,
                "confirm_delete": False,
            })
            st.rerun()
    with c2:
        if st.button("📨 Presupuesto", key=f"pres_cli_{c['clienteid']}", use_container_width=True):
            try:
                supabase.table("presupuesto").insert({
                    "numero": f"PRES-{date.today().year}-{c['clienteid']}",
                    "clienteid": c["clienteid"],
                    "trabajadorid": c.get("trabajadorid"),
                    "estado_presupuestoid": 1,
                    "fecha_presupuesto": date.today().isoformat(),
                    "observaciones": "Presupuesto inicial creado desde listado de clientes.",
                    "editable": True,
                    "facturar_individual": False,
                }).execute()
                st.toast(f"✅ Presupuesto creado para {razon}.", icon="📨")
            except Exception as e:
                st.error(f"❌ Error creando presupuesto: {e}")
    with c3:
        if st.button("🗑️ Eliminar", key=f"elim_cli_{c['clienteid']}", use_container_width=True):
            st.session_state.update({
                "cliente_modal_id": c["clienteid"],
                "confirm_delete": True,
                "show_cliente_modal": True,
            })
            st.rerun()

def _render_table(clientes, supabase):
    """Tabla de clientes con formato visual, badges y acciones, estilo verde corporativo."""
    import io
    import pandas as pd
    from datetime import date

    if not clientes:
        st.info("📭 No hay clientes para mostrar.")
        return

    # =========================================================
    # 💅 Estilos globales (tema Orbe)
    # =========================================================
    st.markdown("""
    <style>
    /* =============================
       🌿 ORBE THEME — ESTILOS GLOBALES
       ============================= */
    main, [data-testid="stAppViewContainer"] {
        max-width: 1200px !important;
        margin: auto;
        padding: 1rem 2rem;
    }
    h1, h2, h3 {
        color: #065f46 !important;
    }
    div.stButton > button {
        background: linear-gradient(90deg, #16a34a, #15803d) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 0.6rem 1rem !important;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #15803d, #166534) !important;
        transform: scale(1.02);
    }
    [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
        color: #065f46 !important;
    }
    .tabla-clientes {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        font-size: 0.93rem;
    }
    .tabla-clientes th {
        text-align: left;
        background-color: #ecfdf5;
        color: #065f46;
        padding: 8px;
        border-bottom: 2px solid #a7f3d0;
    }
    .tabla-clientes td {
        padding: 10px 8px;
        border-bottom: 1px solid #e5e7eb;
    }
    .tabla-clientes tr:nth-child(even) {
        background-color: #f9fafb;
    }
    .badge {
        border-radius: 999px;
        padding: 3px 8px;
        font-size: 0.78rem;
        color: white;
        font-weight: 500;
    }
    .estado-activo { background-color: #10b981; }
    .estado-potencial { background-color: #3b82f6; }
    .estado-suspendido { background-color: #dc2626; }
    .pres-aceptado { background-color: #16a34a; }
    .pres-pendiente { background-color: #f59e0b; }
    .pres-rechazado { background-color: #dc2626; }
    .pres-sin { background-color: #6b7280; }
    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # 📋 Cabecera de tabla
    # =========================================================
    st.markdown("""
    <table class="tabla-clientes">
        <tr>
            <th>🏢 Cliente</th>
            <th>📋 Estado</th>
            <th>💰 Presupuesto</th>
            <th>💳 Forma de pago</th>
            <th>🧩 Categoría</th>
            <th>👥 Grupo</th>
            <th>🧑 Trabajador</th>
            <th style="text-align:center;">⚙️ Acciones</th>
        </tr>
    """, unsafe_allow_html=True)

    # =========================================================
    # 🔁 Filas dinámicas
    # =========================================================
    for c in clientes:
        razon = _safe(c.get("razon_social"))
        ident = _safe(c.get("identificador"))
        estado = get_estado_label(c.get("estadoid"), supabase)
        categoria = get_categoria_label(c.get("categoriaid"), supabase)
        grupo = get_grupo_label(c.get("grupoid"), supabase)
        trabajador = get_trabajador_label(c.get("trabajadorid"), supabase)
        forma_pago = get_formapago_label(c.get("formapagoid"), supabase)

        # Último presupuesto
        try:
            pres = (
                supabase.table("presupuesto")
                .select("estado_presupuestoid, fecha_presupuesto")
                .eq("clienteid", c["clienteid"])
                .order("fecha_presupuesto", desc=True)
                .limit(1)
                .execute()
            )
            pres_estadoid = pres.data[0]["estado_presupuestoid"] if pres.data else None
            pres_fecha = pres.data[0]["fecha_presupuesto"] if pres.data else None
            estado_map = {1: "Pendiente", 2: "Aceptado", 3: "Rechazado"}
            pres_estado = estado_map.get(pres_estadoid, "Sin presupuesto")
        except Exception:
            pres_estado, pres_fecha = "Sin presupuesto", None

        # Colores
        estado_class = {
            "Activo": "estado-activo",
            "Potencial": "estado-potencial",
            "Suspendido": "estado-suspendido",
        }.get(estado, "estado-activo")

        pres_class = {
            "Aceptado": "pres-aceptado",
            "Pendiente": "pres-pendiente",
            "Rechazado": "pres-rechazado",
            "Sin presupuesto": "pres-sin",
        }.get(pres_estado, "pres-sin")

        pres_text = pres_fecha if pres_fecha else "-"

        # Render HTML fila
        st.markdown(
            f"""
            <tr>
                <td><b>{razon}</b><br><span style='color:#6b7280;font-size:0.83rem'>{ident}</span></td>
                <td><span class='badge {estado_class}'>{estado}</span></td>
                <td><span class='badge {pres_class}'>{pres_estado}</span><br><span style='font-size:0.8rem;color:#4b5563;'>{pres_text}</span></td>
                <td>{forma_pago}</td>
                <td>{categoria}</td>
                <td>{grupo}</td>
                <td>{trabajador}</td>
                <td style='text-align:center;'>
                    <form action='#' style='display:flex;justify-content:center;gap:6px;'>
                        <button onclick="window.parent.postMessage({{type:'streamlitRerun',data:'ficha_{c['clienteid']}'}})" style='padding:3px 8px;border-radius:6px;border:1px solid #16a34a;background:#ecfdf5;cursor:pointer;'>📄</button>
                        <button onclick="window.parent.postMessage({{type:'streamlitRerun',data:'pres_{c['clienteid']}'}})" style='padding:3px 8px;border-radius:6px;border:1px solid #16a34a;background:#dcfce7;cursor:pointer;'>📨</button>
                        <button onclick="window.parent.postMessage({{type:'streamlitRerun',data:'elim_{c['clienteid']}'}})" style='padding:3px 8px;border-radius:6px;border:1px solid #dc2626;background:#fef2f2;cursor:pointer;'>🗑️</button>
                    </form>
                </td>
            </tr>
            """,
            unsafe_allow_html=True,
        )

    # Cierre de tabla
    st.markdown("</table>", unsafe_allow_html=True)

    # =========================================================
    # ⬇️ Exportar CSV
    # =========================================================
    df = pd.DataFrame(clientes)
    buff = io.StringIO()
    df.to_csv(buff, index=False)
    st.download_button(
        "⬇️ Exportar CSV",
        buff.getvalue(),
        file_name=f"clientes_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )


from datetime import date
import streamlit as st
from modules.cliente_direccion_form import render_direccion_form
from modules.cliente_facturacion_form import render_facturacion_form
from modules.cliente_observacion_form import render_observaciones_form
from modules.cliente_crm_form import render_crm_form
from modules.cliente_contacto_form import render_contacto_form
from datetime import date
import streamlit as st
from modules.cliente_direccion_form import render_direccion_form
from modules.cliente_facturacion_form import render_facturacion_form
from modules.cliente_observacion_form import render_observaciones_form
from modules.cliente_crm_form import render_crm_form
from modules.cliente_contacto_form import render_contacto_form
from modules.cliente_models import (
    get_estado_label, get_trabajador_label,
    get_formapago_label, get_grupo_label, get_categoria_label
)

def render_cliente_modal(supabase):
    apply_orbe_theme()

    """Ficha visual y profesional del cliente activo."""
    if not st.session_state.get("show_cliente_modal"):
        return

    clienteid = st.session_state.get("cliente_modal_id")
    if not clienteid:
        st.warning("⚠️ No hay cliente activo.")
        return

    # ======================================================
    # 🏢 Cabecera del cliente
    # ======================================================
    st.markdown("---")

    try:
        cli = (
            supabase.table("cliente")
            .select("razon_social, identificador, estadoid, trabajadorid, formapagoid, grupoid, categoriaid")
            .eq("clienteid", int(clienteid))
            .single()
            .execute()
            .data
        )
        estado_nombre = get_estado_label(cli.get("estadoid"), supabase)
    except Exception:
        cli, estado_nombre = {}, "Desconocido"

    # Color dinámico según estado
    bg_color = {
        "Activo": "#ecfdf5",
        "Potencial": "#eff6ff",
        "Suspendido": "#fef2f2",
    }.get(estado_nombre, "#f9fafb")

    border_color = {
        "Activo": "#10b981",
        "Potencial": "#3b82f6",
        "Suspendido": "#dc2626",
    }.get(estado_nombre, "#9ca3af")

    # Último presupuesto aceptado (solo 1)
    try:
        pres = (
            supabase.table("presupuesto")
            .select("numero, fecha_presupuesto, total_estimada")
            .eq("clienteid", int(clienteid))
            .eq("estado_presupuestoid", 3)
            .order("fecha_presupuesto", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if pres:
            pres_info = pres[0]
            resumen_pres = f"🧾 <b>{pres_info['numero']}</b> — {pres_info['fecha_presupuesto']} — 💰 {pres_info.get('total_estimada','-')} €"
        else:
            resumen_pres = "📭 Sin presupuestos aceptados"
    except Exception:
        resumen_pres = "⚠️ Error al cargar presupuesto"

    st.markdown(
        f"""
        <div style="border-left:6px solid {border_color};
                    background:{bg_color};
                    border-radius:10px;
                    padding:16px;
                    margin-bottom:12px;">
            <h3 style="margin:0;color:#111827;">🏢 {cli.get('razon_social','(Sin nombre)')}</h3>
            <p style="color:#374151;margin:2px 0;">Identificador: <b>{cli.get('identificador','-')}</b></p>
            <p style="color:#374151;margin:2px 0;">
                Estado actual: <b style='color:{border_color};'>{estado_nombre}</b><br>
                {resumen_pres}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ======================================================
    # 🔘 Botones superiores
    # ======================================================
    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        if st.button("⬅️  Cerrar ficha", use_container_width=True):
            st.session_state.update({"show_cliente_modal": False, "confirm_delete": False})
            st.rerun()

    with c2:
        if not st.session_state.get("confirm_delete"):
            if st.button("🗑️  Eliminar cliente", use_container_width=True):
                st.session_state["confirm_delete"] = True
                st.warning("⚠️  Pulsa **Confirmar eliminación** para borrar definitivamente este cliente.")
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state["confirm_delete"] = False
                    st.rerun()
            with col_b:
                if st.button("✅ Confirmar", use_container_width=True):
                    try:
                        supabase.table("cliente").delete().eq("clienteid", int(clienteid)).execute()
                        st.success("🗑️ Cliente eliminado correctamente.")
                        st.session_state.update({"show_cliente_modal": False, "confirm_delete": False})
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al eliminar cliente: {e}")

    with c3:
        if st.button("📨  Crear presupuesto", use_container_width=True):
            try:
                supabase.table("presupuesto").insert({
                    "numero": f"PRES-{date.today().year}-{clienteid}",
                    "clienteid": int(clienteid),
                    "trabajadorid": st.session_state.get("trabajadorid", 13),
                    "estado_presupuestoid": 1,
                    "fecha_presupuesto": date.today().isoformat(),
                    "observaciones": "Presupuesto creado desde ficha del cliente.",
                    "editable": True,
                    "facturar_individual": False,
                }).execute()
                st.toast("📨  Presupuesto creado correctamente.", icon="📨")
            except Exception as e:
                st.error(f"❌ Error creando presupuesto: {e}")

    # ======================================================
    # 🧾 Detalles compactos
    # ======================================================
    try:
        dir_fiscal = (
            supabase.table("cliente_direccion")
            .select("direccion, ciudad, cp, pais")
            .eq("clienteid", int(clienteid))
            .eq("tipo", "fiscal")
            .limit(1)
            .execute()
            .data
        )

        direccion = dir_fiscal[0].get("direccion", "-") if dir_fiscal else "-"
        ciudad = dir_fiscal[0].get("ciudad", "-") if dir_fiscal else "-"
        cp = dir_fiscal[0].get("cp", "-") if dir_fiscal else "-"
        pais = dir_fiscal[0].get("pais", "-") if dir_fiscal else "-"

        st.markdown(
            f"""
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;
                        padding:14px;margin:10px 0;box-shadow:0 1px 2px rgba(0,0,0,0.04);">
                💳 <b>Forma de pago:</b> {get_formapago_label(cli.get('formapagoid'), supabase)}<br>
                👥 <b>Grupo:</b> {get_grupo_label(cli.get('grupoid'), supabase)}<br>
                🧩 <b>Categoría:</b> {get_categoria_label(cli.get('categoriaid'), supabase)}<br>
                🧑 <b>Trabajador:</b> {get_trabajador_label(cli.get('trabajadorid'), supabase)}<br>
                📍 <b>Dirección:</b> {direccion}, {ciudad} ({cp}) — {pais}
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar los detalles: {e}")
    # ======================================================
    # 🧭 Pestañas principales
    # ======================================================
    st.session_state["cliente_actual"] = int(clienteid)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Direcciones",
        "💳 Facturación",
        "👥 Contactos",
        "🗒️ Observaciones",
        "💬 Seguimiento / CRM"
    ])

    # -----------------------------------
    # 🏠 Direcciones
    # -----------------------------------
    with tab1:
        render_direccion_form(supabase, int(clienteid), modo="cliente")

    # -----------------------------------
    # 💳 Facturación
    # -----------------------------------
    with tab2:
        render_facturacion_form(supabase, int(clienteid))

    # -----------------------------------
    # 👥 Contactos
    # -----------------------------------
    with tab3:
        render_contacto_form(supabase, int(clienteid))

    # -----------------------------------
    # 🗒️ Observaciones
    # -----------------------------------
    with tab4:
        render_observaciones_form(supabase, int(clienteid))

    # -----------------------------------
    # 💬 Seguimiento / CRM
    # -----------------------------------
    with tab5:
        st.markdown("### 💬 Actividad reciente del cliente")
        try:
            actividades = (
                supabase.table("crm_actuacion")
                .select("titulo, descripcion, estado, fecha_accion, prioridad, trabajadorid")
                .eq("clienteid", int(clienteid))
                .order("fecha_accion", desc=True)
                .limit(6)
                .execute()
                .data
            ) or []

            if not actividades:
                st.info("📭 No hay actuaciones registradas todavía.")
            else:
                for act in actividades:
                    color_estado = {
                        "Pendiente": "#f59e0b",
                        "Completada": "#16a34a",
                        "Cancelada": "#dc2626",
                    }.get(act.get("estado"), "#6b7280")

                    st.markdown(
                        f"""
                        <div style='border-left:5px solid {color_estado};
                                    background:#f9fafb;padding:10px 12px;margin:6px 0;border-radius:8px;'>
                            <b>{act.get('titulo','(Sin título)')}</b><br>
                            <span style='color:#4b5563;font-size:0.85rem;'>
                                🧑 {get_trabajador_label(act.get('trabajadorid'), supabase)} · 
                                {act.get('fecha_accion','-')}
                            </span><br>
                            <span style='font-size:0.9rem;'>{act.get('descripcion','-')}</span><br>
                            <span style='font-size:0.8rem;color:{color_estado};font-weight:600;'>
                                {act.get('estado','-')} · {act.get('prioridad','-')}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        except Exception as e:
            st.error(f"❌ Error cargando CRM: {e}")

        if st.button("➕ Registrar nueva actuación", use_container_width=True):
            try:
                supabase.table("crm_actuacion").insert({
                    "clienteid": int(clienteid),
                    "trabajadorid": st.session_state.get("trabajadorid", 13),
                    "titulo": "Nueva actuación",
                    "estado": "Pendiente",
                    "prioridad": "Media",
                    "descripcion": "Seguimiento inicial creado desde la ficha del cliente."
                }).execute()
                st.toast("✅ Nueva actuación registrada.", icon="🗒️")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al crear la actuación: {e}")

    # ======================================================
    # 💼 Presupuestos del cliente (detalle mejorado)
    # ======================================================
    st.markdown("---")
    st.subheader("💼 Presupuestos del cliente")

    try:
        presupuestos = (
            supabase.table("presupuesto")
            .select("presupuestoid, numero, fecha_presupuesto, total_estimada, estado_presupuestoid")
            .eq("clienteid", int(clienteid))
            .order("fecha_presupuesto", desc=True)
            .execute()
            .data
        ) or []

        if not presupuestos:
            st.info("📭 Este cliente no tiene presupuestos registrados aún.")
        else:
            estado_map = {1: "Pendiente", 2: "Aceptado", 3: "Rechazado"}
            color_map = {"Pendiente": "#f59e0b", "Aceptado": "#16a34a", "Rechazado": "#dc2626"}

            for p in presupuestos:
                estado = estado_map.get(p.get("estado_presupuestoid"), "Desconocido")
                color = color_map.get(estado, "#6b7280")
                st.markdown(
                    f"""
                    <div style='border:1px solid #e5e7eb;border-left:5px solid {color};
                                background:#f9fafb;padding:10px 12px;margin:6px 0;border-radius:8px;'>
                        <b>{p['numero']}</b> — 🗓️ {p['fecha_presupuesto']}<br>
                        💰 <b>{p.get('total_estimada','-')} €</b><br>
                        <span style='color:{color};font-weight:600;'>{estado}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    except Exception as e:
        st.warning(f"⚠️ No se pudieron cargar los presupuestos: {e}")
