# modules/cliente_potencial_lista.py

import math
from datetime import date
from typing import Any, Dict, Optional, List

import streamlit as st
from streamlit.components.v1 import html as st_html

from modules.orbe_theme import apply_orbe_theme

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

from modules.cliente_direccion_form import render_direccion_form
from modules.cliente_facturacion_form import render_facturacion_form
from modules.cliente_observacion_form import render_observaciones_form
from modules.cliente_crm_form import render_crm_form
from modules.cliente_contacto_form import render_contacto_form

# ✅ NUEVO: alta de potenciales reutilizando tu form (adaptado ya a tipo_cliente="potencial")
# ⚠️ Cambia este import si tu fichero se llama distinto:
from modules.cliente_form import render_cliente_form


# =========================================================
# 🔧 UTILS
# =========================================================
def _safe(v, d: str = "-"):
    return v if v not in (None, "", "null") else d


def _build_search_or(s: Optional[str], fields=("razon_social", "identificador")):
    s = (s or "").strip()
    if not s:
        return None
    return ",".join([f"{f}.ilike.%{s}%" for f in fields])


def _normalize_id(v: Any):
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _short(s: str, n: int = 48) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _bool(v: Any) -> bool:
    # PostgREST a veces devuelve "true"/"false" como string
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "t", "yes", "y")
    return bool(v)


# =========================================================
# 📦 PREFETCH DATOS (OPTIMIZACIÓN)
# =========================================================
def _prefetch_presupuestos(supabase, ids_clientes: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Devuelve por clienteid el ÚLTIMO presupuesto (por fecha_presupuesto desc).
    """
    if not ids_clientes:
        return {}

    try:
        rows = (
            supabase.table("presupuesto")
            .select("clienteid, estado_presupuestoid, fecha_presupuesto, numero, total_estimada")
            .in_("clienteid", ids_clientes)
            .order("fecha_presupuesto", desc=True)
            .execute()
            .data
            or []
        )

        out: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            cid = r.get("clienteid")
            if cid and cid not in out:
                out[int(cid)] = r
        return out
    except Exception:
        return {}


def _prefetch_ultimo_crm(supabase, ids_clientes: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Devuelve por clienteid la acción CRM “más reciente/relevante”.
    Priorizamos: fecha_vencimiento desc.
    """
    if not ids_clientes:
        return {}

    try:
        rows = (
            supabase.table("crm_actuacion")
            .select("clienteid, titulo, estado, fecha_vencimiento, prioridad")
            .in_("clienteid", ids_clientes)
            .order("fecha_vencimiento", desc=True)
            .execute()
            .data
            or []
        )

        out: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            cid = r.get("clienteid")
            if cid and int(cid) not in out:
                out[int(cid)] = r
        return out
    except Exception:
        return {}


# =========================================================
# 🧠 PERFIL: cálculo de “faltan datos”
# =========================================================
def _calcular_faltantes_perfil(supabase, cliente_row: Dict[str, Any]) -> List[str]:
    """
    Regla de negocio que ya estabas usando:
    - Dirección fiscal con CP
    - Forma de pago
    - Comercial/trabajador asignado
    """
    clienteid = cliente_row.get("clienteid")
    if not clienteid:
        return ["Cliente sin ID"]

    faltan: List[str] = []

    # Dirección fiscal con CP
    try:
        dir_fiscal = (
            supabase.table("cliente_direccion")
            .select("cp")
            .eq("clienteid", int(clienteid))
            .eq("tipo", "fiscal")
            .limit(1)
            .execute()
            .data
        )
        if not dir_fiscal or not dir_fiscal[0].get("cp"):
            faltan.append("Dirección fiscal con CP")
    except Exception:
        faltan.append("Dirección fiscal con CP")

    # Forma de pago
    if not cliente_row.get("formapagoid"):
        faltan.append("Forma de pago")

    # Comercial/trabajador asignado
    if not cliente_row.get("trabajadorid"):
        faltan.append("Comercial asignado")

    return faltan


def _persistir_perfil_completo(supabase, clienteid: int, perfil_ok: bool):
    """
    Guarda el flag perfil_completo en BBDD.
    """
    try:
        supabase.table("cliente").update({"perfil_completo": bool(perfil_ok)}).eq("clienteid", int(clienteid)).execute()
    except Exception:
        pass


# =========================================================
# 🌱 LISTA PRINCIPAL DE CLIENTES POTENCIALES
# =========================================================
def render_cliente_potencial_lista(supabase):
    apply_orbe_theme()

    st.header("🌱 Clientes potenciales")
    st.caption(
        "Contactos comerciales en fase previa. "
        "Trabajan con presupuestos y CRM hasta completar su perfil."
    )

    # ---------------------------
    # Session state defaults
    # ---------------------------
    defaults = {
        "pot_page": 1,
        "pot_sort_field": "razon_social",
        "pot_sort_dir": "ASC",
        "show_potencial_modal": False,
        "cliente_potencial_id": None,
        "pot_confirm_delete": False,

        # ✅ NUEVO: UI alta potencial
        "show_create_potencial": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    trabajador_actual = st.session_state.get("trabajadorid")

    # =====================================================
    # ✅ NUEVO BLOQUE: CREAR CLIENTE POTENCIAL DESDE AQUÍ
    # =====================================================
    with st.expander("➕ Crear cliente potencial", expanded=False):
        st.caption("Usa el alta completa, pero se guardará como tipo_cliente='potencial'.")
        # Nota: tu render_cliente_form debe aceptar supabase y modo="potencial"
        # (como ya acordamos y como tú lo adaptaste)
        render_cliente_form(supabase, modo="potencial")

    # =====================================================
    # ✅ NUEVO HOOK POST-CREACIÓN
    # Si el form guarda el clienteid en st.session_state["cliente_actual"],
    # abrimos automáticamente la ficha del potencial recién creado.
    # =====================================================
    if st.session_state.get("cliente_actual"):
        nuevo_id = st.session_state.get("cliente_actual")
        st.session_state["cliente_potencial_id"] = int(nuevo_id)
        st.session_state["show_potencial_modal"] = True
        st.session_state["pot_confirm_delete"] = False
        st.session_state["cliente_actual"] = None
        st.toast("✅ Potencial creado. Abriendo ficha…", icon="✅")
        st.rerun()

    st.markdown("---")

    # ---------------------------
    # Ficha superior (si aplica)
    # ---------------------------
    if st.session_state.get("show_potencial_modal") and st.session_state.get("cliente_potencial_id"):
        _render_potencial_ficha(supabase)
        st.markdown("---")

    # ---------------------------
    # Catálogos
    # ---------------------------
    estados = load_estados_cliente(supabase)
    categorias = load_categorias(supabase)
    grupos = load_grupos(supabase)
    trabajadores = load_trabajadores(supabase)
    formas_pago = load_formas_pago(supabase)

    # ---------------------------
    # Buscador
    # ---------------------------
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input("Buscar", placeholder="Razón social o identificador", key="pot_q")
        if q != st.session_state.get("last_pot_q"):
            st.session_state["pot_page"] = 1
            st.session_state["last_pot_q"] = q

    with c2:
        st.metric("Resultados", st.session_state.get("pot_result_count", 0))

    st.markdown("---")

    # ---------------------------
    # Filtros avanzados
    # ---------------------------
    with st.expander("⚙️ Filtros avanzados", expanded=False):
        f1, f2, f3, f4 = st.columns(4)

        with f1:
            perfil_sel = st.selectbox("Perfil", ["Todos", "Completos", "Incompletos"], key="pot_perfil")

        with f2:
            ver_todos = st.toggle("Ver todos", value=False, key="pot_ver_todos")

        with f3:
            estado_sel = st.selectbox("Estado", ["Todos"] + list(estados.keys()), key="pot_estado")

        with f4:
            trab_sel = st.selectbox("Comercial", ["Todos"] + list(trabajadores.keys()), key="pot_trab_sel")

        s1, s2 = st.columns(2)
        with s1:
            st.session_state["pot_sort_field"] = st.selectbox(
                "Ordenar por",
                ["razon_social", "identificador", "estadoid", "grupoid"],
                index=["razon_social", "identificador", "estadoid", "grupoid"].index(
                    st.session_state.get("pot_sort_field", "razon_social")
                ),
                key="pot_sort_field_sel",
            )
        with s2:
            st.session_state["pot_sort_dir"] = st.radio(
                "Dirección", ["ASC", "DESC"],
                horizontal=True,
                index=0 if st.session_state.get("pot_sort_dir", "ASC") == "ASC" else 1,
                key="pot_sort_dir_sel"
            )

    # ---------------------------
    # Query base
    # ---------------------------
    try:
        base = (
            supabase.table("cliente")
            .select(
                "clienteid, razon_social, identificador, estadoid, categoriaid, "
                "grupoid, trabajadorid, perfil_completo, formapagoid"
            )
            .eq("tipo_cliente", "potencial")
        )

        count_q = (
            supabase.table("cliente")
            .select("clienteid", count="exact")
            .eq("tipo_cliente", "potencial")
        )

        if q:
            or_q = _build_search_or(q)
            base = base.or_(or_q)
            count_q = count_q.or_(or_q)

        if perfil_sel != "Todos":
            is_completo = (perfil_sel == "Completos")
            base = base.eq("perfil_completo", is_completo)
            count_q = count_q.eq("perfil_completo", is_completo)

        # Solo mis potenciales (si no "ver todos")
        if not ver_todos and trabajador_actual:
            base = base.eq("trabajadorid", trabajador_actual)
            count_q = count_q.eq("trabajadorid", trabajador_actual)

        # filtro comercial explícito
        if trab_sel != "Todos" and trab_sel in trabajadores:
            tid = trabajadores[trab_sel]
            base = base.eq("trabajadorid", tid)
            count_q = count_q.eq("trabajadorid", tid)

        if estado_sel != "Todos" and estado_sel in estados:
            eid = estados[estado_sel]
            base = base.eq("estadoid", eid)
            count_q = count_q.eq("estadoid", eid)

        total = count_q.execute().count or 0

        page_size = 30
        page = int(st.session_state.get("pot_page", 1))
        total_pages = max(1, math.ceil(total / page_size))

        # Corrige si se queda fuera
        if page > total_pages:
            page = total_pages
            st.session_state["pot_page"] = page
        if page < 1:
            page = 1
            st.session_state["pot_page"] = 1

        start = (page - 1) * page_size
        end = start + page_size - 1

        data = (
            base.order(
                st.session_state.get("pot_sort_field", "razon_social"),
                desc=(st.session_state.get("pot_sort_dir", "ASC") == "DESC"),
            )
            .range(start, end)
            .execute()
            .data
            or []
        )

        st.session_state["pot_result_count"] = len(data)

    except Exception as e:
        st.error(f"❌ Error cargando potenciales: {e}")
        return

    # ---------------------------
    # Panel métricas
    # ---------------------------
    m1, m2, m3 = st.columns(3)
    m1.metric("🌱 Total", total)
    m2.metric("📄 Página", f"{page}/{total_pages}")
    m3.metric("📆 Hoy", date.today().strftime("%d/%m/%Y"))

    st.caption(
        f"Mostrando {len(data)} de {total} potenciales "
        f"({('todos' if ver_todos else 'asignados a ti')})."
    )

    st.markdown("---")

    if not data:
        st.info("📭 No hay clientes potenciales para mostrar con esos filtros.")
        return

    # ---------------------------
    # Prefetch
    # ---------------------------
    ids = [int(c["clienteid"]) for c in data if c.get("clienteid") is not None]
    last_pres = _prefetch_presupuestos(supabase, ids)
    last_crm = _prefetch_ultimo_crm(supabase, ids)

    # ---------------------------
    # Tarjetas
    # ---------------------------
    cols = st.columns(3)
    for i, c in enumerate(data):
        cid = int(c["clienteid"])
        c["__last_pres__"] = last_pres.get(cid)
        c["__last_crm__"] = last_crm.get(cid)
        with cols[i % 3]:
            _render_potencial_card(c, supabase)

    # ---------------------------
    # Paginación
    # ---------------------------
    st.markdown("---")
    p1, p2, p3 = st.columns(3)

    with p1:
        if st.button("⬅️ Anterior", disabled=page <= 1, use_container_width=True):
            st.session_state["pot_page"] = page - 1
            st.rerun()

    with p2:
        st.write(f"Página {page} / {total_pages}")

    with p3:
        if st.button("Siguiente ➡️", disabled=page >= total_pages, use_container_width=True):
            st.session_state["pot_page"] = page + 1
            st.rerun()


# =========================================================
# 🧾 TARJETA DE CLIENTE POTENCIAL
# =========================================================
def _render_potencial_card(c: Dict[str, Any], supabase):
    apply_orbe_theme()

    razon = _safe(c.get("razon_social"))
    ident = _safe(c.get("identificador"))

    categoria = get_categoria_label(c.get("categoriaid"), supabase) or "-"
    grupo = get_grupo_label(c.get("grupoid"), supabase) or "Sin grupo"
    trabajador = get_trabajador_label(c.get("trabajadorid"), supabase) or "Sin comercial"

    fid = _normalize_id(c.get("formapagoid"))
    forma_pago = get_formapago_label(fid, supabase) if fid else "-"

    completo = _bool(c.get("perfil_completo"))
    perfil_badge = (
        "<span style='color:#16a34a;font-weight:600;'>🟢 Perfil completo</span>"
        if completo
        else "<span style='color:#dc2626;font-weight:600;'>🔴 Perfil incompleto</span>"
    )

    # ---------- Presupuesto ----------
    pres = c.get("__last_pres__") or {}
    estado_pres = {1: "Pendiente", 2: "Aceptado", 3: "Rechazado"}.get(
        pres.get("estado_presupuestoid"), "Sin presupuesto"
    )
    pres_num = pres.get("numero") or "-"
    pres_fecha = pres.get("fecha_presupuesto") or "-"
    pres_color = {
        "Pendiente": "#f59e0b",
        "Aceptado": "#16a34a",
        "Rechazado": "#dc2626",
        "Sin presupuesto": "#6b7280",
    }.get(estado_pres, "#6b7280")

    # ---------- CRM ----------
    crm = c.get("__last_crm__") or {}
    crm_estado = crm.get("estado", "—")
    crm_fecha = crm.get("fecha_vencimiento", "—")
    crm_titulo = _short(crm.get("titulo", "—"), 36)

    html = f"""
    <div style="border:1px solid #d1fae5;border-radius:12px;
                background:#f0fdf4;padding:14px;margin-bottom:14px;
                box-shadow:0 1px 3px rgba(0,0,0,.08);">

        <div style="display:flex;justify-content:space-between;gap:10px;">
            <div style="min-width:0;">
                <div style="font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    🌱 {razon}
                </div>
                <div style="color:#6b7280;font-size:.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    {ident}
                </div>
            </div>
            <div style="color:#3b82f6;font-weight:700;white-space:nowrap;">
                Potencial
            </div>
        </div>

        <div style="margin-top:8px;font-size:.9rem;line-height:1.45;">
            🧩 <b>Categoría:</b> {categoria}<br>
            👥 <b>Grupo:</b> {grupo}<br>
            🧑 <b>Comercial:</b> {trabajador}<br>
            💳 <b>Forma de pago:</b> {forma_pago}<br>
            {perfil_badge}

            <div style="margin-top:8px;border-top:1px dashed #d1d5db;padding-top:6px;">
                <b>📨 Último presupuesto</b><br>
                <span style="color:{pres_color};font-weight:700;">{estado_pres}</span>
                <span style="color:#6b7280;"> · {pres_num} · {pres_fecha}</span><br>

                <b>💬 Última acción CRM</b><br>
                <span style="font-weight:700;">{crm_estado}</span>
                <span style="color:#6b7280;"> · {crm_fecha}</span><br>
                <span style="color:#374151;">{crm_titulo}</span>
            </div>
        </div>
    </div>
    """

    st_html(html, height=330)

    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("📄 Ficha", key=f"pot_ficha_{c['clienteid']}", use_container_width=True):
            st.session_state.update(
                {
                    "cliente_potencial_id": c["clienteid"],
                    "show_potencial_modal": True,
                    "pot_confirm_delete": False,
                }
            )
            st.rerun()

    with b2:
        if st.button("📨 Presupuesto", key=f"pot_pres_{c['clienteid']}", use_container_width=True):
            try:
                supabase.table("presupuesto").insert(
                    {
                        "clienteid": c["clienteid"],
                        "numero": f"PRES-{date.today().year}-{c['clienteid']}",
                        "estado_presupuestoid": 1,
                        "fecha_presupuesto": date.today().isoformat(),
                        "editable": True,
                    }
                ).execute()
                st.toast("📨 Presupuesto creado", icon="📨")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error creando presupuesto: {e}")

    with b3:
        if completo:
            if st.button("🚀 Convertir", key=f"pot_conv_{c['clienteid']}", use_container_width=True):
                try:
                    supabase.table("cliente").update({"tipo_cliente": "cliente", "estadoid": 1}).eq(
                        "clienteid", c["clienteid"]
                    ).execute()
                    st.success("🎉 Convertido a cliente")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al convertir: {e}")
        else:
            st.button("❌ Incompleto", disabled=True, use_container_width=True)


# =========================================================
# 🌱 FICHA COMPLETA DE POTENCIAL
# =========================================================
def _render_potencial_ficha(supabase):
    apply_orbe_theme()

    clienteid = st.session_state.get("cliente_potencial_id")
    if not clienteid:
        return

    # ---------------------------
    # Cargar cliente base
    # ---------------------------
    try:
        cli = (
            supabase.table("cliente")
            .select(
                "clienteid, razon_social, identificador, trabajadorid, "
                "formapagoid, grupoid, categoriaid, estadoid, observaciones, perfil_completo, tipo_cliente"
            )
            .eq("clienteid", int(clienteid))
            .single()
            .execute()
            .data
        )
    except Exception as e:
        st.error(f"❌ Error cargando cliente potencial: {e}")
        return

    razon = _safe(cli.get("razon_social"), "(Sin nombre)")
    identificador = _safe(cli.get("identificador"))
    tipo_cliente = _safe(cli.get("tipo_cliente"), "potencial")

    estado_txt = get_estado_label(cli.get("estadoid"), supabase) or "—"
    categoria_txt = get_categoria_label(cli.get("categoriaid"), supabase) or "—"
    grupo_txt = get_grupo_label(cli.get("grupoid"), supabase) or "Sin grupo"
    comercial_txt = get_trabajador_label(cli.get("trabajadorid"), supabase) or "Sin comercial"
    forma_pago_txt = get_formapago_label(_normalize_id(cli.get("formapagoid")), supabase) if cli.get("formapagoid") else "—"

    # ---------------------------
    # Perfil: faltantes + persistencia
    # ---------------------------
    faltan = _calcular_faltantes_perfil(supabase, cli)
    perfil_ok = (len(faltan) == 0)
    _persistir_perfil_completo(supabase, int(clienteid), perfil_ok)

    # ---------------------------
    # Cabecera + volver
    # ---------------------------
    st.markdown("## ")
    c1, c2 = st.columns([1, 5])

    with c1:
        if st.button("⬅️ Volver", key="pot_back", use_container_width=True):
            st.session_state["show_potencial_modal"] = False
            st.session_state["cliente_potencial_id"] = None
            st.session_state["pot_confirm_delete"] = False
            st.rerun()

    with c2:
        st.markdown(
            f"""
            <div style="padding:14px;border-radius:12px;
                        background:{'#f0fdf4' if perfil_ok else '#fef3c7'};
                        border:1px solid {'#16a34a' if perfil_ok else '#f59e0b'};">
                <div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start;">
                    <div style="min-width:0;">
                        <h3 style="margin:0;">🌱 {razon}</h3>
                        <p style="margin:.25rem 0 0 0;color:#4b5563;">
                            <b>ID:</b> {clienteid} · <b>Identificador:</b> {identificador} · <b>Tipo:</b> {tipo_cliente} · <b>Estado:</b> {estado_txt}
                        </p>
                        <p style="margin:.25rem 0 0 0;color:#374151;">
                            <b>Categoría:</b> {categoria_txt} · <b>Grupo:</b> {grupo_txt} · <b>Comercial:</b> {comercial_txt} · <b>Forma pago:</b> {forma_pago_txt}
                        </p>
                    </div>
                    <div style="font-weight:800;color:{'#16a34a' if perfil_ok else '#b45309'};white-space:nowrap;">
                        {'✅ Perfil completo' if perfil_ok else '⚠️ Perfil incompleto'}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---------------------------
    # Avisos “faltan datos”
    # ---------------------------
    if not perfil_ok:
        st.warning("⚠️ Faltan datos para poder convertir este potencial a cliente:")
        for f in faltan:
            st.write(f"❌ {f}")
    else:
        st.success("✅ Perfil completo. Ya se puede convertir a cliente cuando quieras.")

    obs = (cli.get("observaciones") or "").strip()
    if obs:
        st.info(obs)

    # ---------------------------
    # KPIs rápidos (presupuestos + CRM pendientes)
    # ---------------------------
    try:
        pres_count = (
            supabase.table("presupuesto")
            .select("presupuestoid", count="exact")
            .eq("clienteid", int(clienteid))
            .execute()
        ).count or 0
    except Exception:
        pres_count = "N/D"

    try:
        crm_pend = (
            supabase.table("crm_actuacion")
            .select("crm_actuacionid", count="exact")
            .eq("clienteid", int(clienteid))
            .eq("estado", "Pendiente")
            .execute()
        ).count or 0
    except Exception:
        crm_pend = "N/D"

    k1, k2 = st.columns(2)
    k1.metric("📨 Presupuestos", pres_count)
    k2.metric("💬 CRM pendientes", crm_pend)

    st.markdown("---")

    # ---------------------------
    # Tabs
    # ---------------------------
    (
        tab_dir,
        tab_fact,
        tab_cont,
        tab_obs,
        tab_crm,
        tab_pres,
        tab_conv,
    ) = st.tabs(
        [
            "🏠 Direcciones",
            "💳 Facturación",
            "👥 Contactos",
            "🗒️ Observaciones",
            "💬 CRM",
            "🧾 Presupuestos",
            "🚀 Conversión",
        ]
    )

    with tab_dir:
        render_direccion_form(supabase, int(clienteid), modo="potencial")

    with tab_fact:
        render_facturacion_form(supabase, int(clienteid))

    with tab_cont:
        render_contacto_form(supabase, int(clienteid))

    with tab_obs:
        render_observaciones_form(supabase, int(clienteid))

    with tab_crm:
        render_crm_form(supabase, int(clienteid))

    with tab_pres:
        st.markdown("### 🧾 Presupuestos del potencial")
        st.caption("Los potenciales trabajan con presupuestos mientras se completa el perfil.")

        try:
            presupuestos = (
                supabase.table("presupuesto")
                .select("presupuestoid, numero, fecha_presupuesto, total_estimada, estado_presupuestoid")
                .eq("clienteid", int(clienteid))
                .order("fecha_presupuesto", desc=True)
                .execute()
                .data
                or []
            )
        except Exception as e:
            st.error(f"❌ Error cargando presupuestos: {e}")
            presupuestos = []

        if not presupuestos:
            st.info("📭 Este potencial no tiene presupuestos registrados aún.")
        else:
            estado_map = {1: "Pendiente", 2: "Aceptado", 3: "Rechazado"}
            color_map = {"Pendiente": "#f59e0b", "Aceptado": "#16a34a", "Rechazado": "#dc2626"}

            for p in presupuestos:
                est = estado_map.get(p.get("estado_presupuestoid"), "Desconocido")
                color = color_map.get(est, "#6b7280")

                st.markdown(
                    f"""
                    <div style='border:1px solid #e5e7eb;border-left:5px solid {color};
                                background:#f9fafb;padding:10px 12px;margin:6px 0;border-radius:8px;'>
                        <b>{p.get('numero','(Sin número)')}</b> — 🗓️ {p.get('fecha_presupuesto','-')}<br>
                        💰 <b>{p.get('total_estimada','-')} €</b><br>
                        <span style='color:{color};font-weight:700;'>{est}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with tab_conv:
        st.markdown("### 🚀 Conversión a cliente activo")

        if perfil_ok:
            st.success("✅ Perfil completo. Puedes convertirlo a cliente activo.")
        else:
            st.warning("⚠️ Antes de convertir, completa lo siguiente:")
            for f in faltan:
                st.write(f"❌ {f}")

        st.markdown("---")

        cA, cB = st.columns([2, 1])

        with cA:
            if perfil_ok:
                if st.button("✅ Convertir a cliente", key="pot_convert_btn", use_container_width=True):
                    try:
                        supabase.table("cliente").update({"tipo_cliente": "cliente", "estadoid": 1}).eq(
                            "clienteid", int(clienteid)
                        ).execute()
                        st.success("🎉 Cliente convertido a activo")
                        st.session_state["show_potencial_modal"] = False
                        st.session_state["cliente_potencial_id"] = None
                        st.session_state["pot_confirm_delete"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al convertir: {e}")
            else:
                st.button("✅ Convertir a cliente", disabled=True, use_container_width=True)

        with cB:
            st.markdown("### ")
            if not st.session_state.get("pot_confirm_delete"):
                if st.button("🗑️ Eliminar potencial", key="pot_delete_btn", use_container_width=True):
                    st.session_state["pot_confirm_delete"] = True
                    st.warning("⚠️ Pulsa Confirmar para eliminar definitivamente.")
            else:
                d1, d2 = st.columns(2)
                with d1:
                    if st.button("Cancelar", key="pot_delete_cancel", use_container_width=True):
                        st.session_state["pot_confirm_delete"] = False
                        st.rerun()
                with d2:
                    if st.button("Confirmar", key="pot_delete_confirm", use_container_width=True):
                        try:
                            supabase.table("cliente").delete().eq("clienteid", int(clienteid)).execute()
                            st.success("🗑️ Potencial eliminado")
                            st.session_state["show_potencial_modal"] = False
                            st.session_state["cliente_potencial_id"] = None
                            st.session_state["pot_confirm_delete"] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error eliminando: {e}")
