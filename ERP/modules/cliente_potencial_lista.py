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


# =========================================================
# 🔧 Utils
# =========================================================
def _safe(v, d: str = "-"):
    return v if v not in (None, "", "null") else d


def _build_search_or(s: Optional[str], fields=("razon_social", "identificador")):
    s = (s or "").strip()
    if not s:
        return None
    return ",".join([f"{f}.ilike.%{s}%" for f in fields])


def _normalize_id(v: Any):
    """Normaliza IDs numéricos que puedan venir como float (1.0 -> 1)."""
    if isinstance(v, float):
        if v.is_integer():
            return int(v)
        return v
    return v


# =========================================================
# 🌱 Vista principal de clientes potenciales
# =========================================================
def render_cliente_potencial_lista(supabase):
    apply_orbe_theme()

    st.header("🌱 Gestión de clientes potenciales")
    st.caption(
        "Visualiza y gestiona tus clientes potenciales, completa su perfil y "
        "conviértelos en clientes activos cuando estén listos."
    )

    # Estado inicial
    defaults = {
        "pot_page": 1,
        "pot_sort_field": "razon_social",
        "pot_sort_dir": "ASC",
        "show_potencial_modal": False,
        "cliente_potencial_id": None,
        "pot_confirm_delete": False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    trabajadorid = st.session_state.get("trabajadorid", None)

    # ===============================
    # 📌 FICHA POTENCIAL ARRIBA (SI HAY)
    # ===============================
    if st.session_state.get("show_potencial_modal") and st.session_state.get("cliente_potencial_id"):
        try:
            st.session_state.pop("_dialog_state", None)
        except Exception:
            pass
        _render_potencial_ficha(supabase)
        st.markdown("## ")  # separación visual

    # Catálogos
    estados = load_estados_cliente(supabase)
    categorias = load_categorias(supabase)
    grupos = load_grupos(supabase)
    trabajadores = load_trabajadores(supabase)
    _ = load_formas_pago(supabase)

    # ===============================
    # 🔍 Buscador
    # ===============================
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input(
            "Buscar potencial",
            placeholder="Razón social o identificador…",
            key="pot_q",
        )

        # reset de página si cambia el texto de búsqueda
        if "last_pot_q" not in st.session_state:
            st.session_state["last_pot_q"] = ""
        if q != st.session_state["last_pot_q"]:
            st.session_state["pot_page"] = 1
            st.session_state["last_pot_q"] = q

    with c2:
        st.metric("🔎 Resultados (página)", st.session_state.get("pot_result_count", 0))

    st.markdown("---")

    # ===============================
    # 🎛 Filtros avanzados
    # ===============================
    with st.expander("⚙️ Filtros avanzados", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            perfil_sel = st.selectbox(
                "Perfil",
                ["Todos", "Completos", "Incompletos"],
                key="pot_perfil",
            )
        with c2:
            ver_todos = st.toggle("👀 Ver todos (no solo mis potenciales)", value=False)
        with c3:
            estado_sel = st.selectbox("Estado", ["Todos"] + list(estados.keys()), key="pot_estado")
        with c4:
            trab_sel = st.selectbox(
                "Trabajador",
                ["Todos"] + list(trabajadores.keys()),
                key="pot_trab",
            )

        # Opcional: orden
        st.markdown("### ↕️ Ordenar")
        c5, c6 = st.columns(2)
        with c5:
            sort_field = st.selectbox(
                "Campo",
                ["razon_social", "identificador", "estadoid", "grupoid"],
                index=["razon_social", "identificador", "estadoid", "grupoid"].index(
                    st.session_state.get("pot_sort_field", "razon_social")
                ),
            )
            st.session_state["pot_sort_field"] = sort_field

        with c6:
            sort_dir = st.radio(
                "Dirección",
                ["ASC", "DESC"],
                index=0 if st.session_state.get("pot_sort_dir", "ASC") == "ASC" else 1,
                horizontal=True,
            )
            st.session_state["pot_sort_dir"] = sort_dir

    # ===============================
    # 📥 Carga + filtros + paginación
    # ===============================
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

        # Búsqueda texto
        or_filter = _build_search_or(q)
        if or_filter:
            base = base.or_(or_filter)
            count_q = count_q.or_(or_filter)

        # Filtros de perfil
        if perfil_sel != "Todos":
            base = base.eq("perfil_completo", perfil_sel == "Completos")
            count_q = count_q.eq("perfil_completo", perfil_sel == "Completos")

        # Filtro trabajador / ver solo los míos
        if not ver_todos and trabajadorid:
            base = base.eq("trabajadorid", trabajadorid)
            count_q = count_q.eq("trabajadorid", trabajadorid)
        elif trab_sel != "Todos" and trab_sel in trabajadores:
            tid = trabajadores[trab_sel]
            base = base.eq("trabajadorid", tid)
            count_q = count_q.eq("trabajadorid", tid)

        # Filtro estado
        if estado_sel != "Todos" and estado_sel in estados:
            eid = estados[estado_sel]
            base = base.eq("estadoid", eid)
            count_q = count_q.eq("estadoid", eid)

        # Conteo total según filtros
        count_res = count_q.execute()
        total_potenciales = count_res.count or 0

        # Paginación real
        page_size = 30
        page = st.session_state["pot_page"]
        total_paginas = max(1, math.ceil(total_potenciales / page_size))
        if page > total_paginas:
            page = total_paginas
            st.session_state["pot_page"] = page

        start = (page - 1) * page_size
        end = start + page_size - 1

        base = base.order(
            st.session_state["pot_sort_field"],
            desc=(st.session_state["pot_sort_dir"] == "DESC"),
        )

        data = base.range(start, end).execute()
        potenciales = data.data or []
        st.session_state["pot_result_count"] = len(potenciales)

    except Exception as e:
        st.error(f"❌ Error cargando clientes potenciales: {e}")
        return

    # ===============================
    # 📈 Panel de métricas
    # ===============================
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("🌱 Total potenciales", total_potenciales)
    col2.metric("👁️ Vista", "Tarjetas")
    col3.metric("📆 Última actualización", date.today().strftime("%d/%m/%Y"))

    st.caption(
        f"Mostrando página {page} de {total_paginas} "
        f"({total_potenciales} potenciales {'de todos los trabajadores' if ver_todos else 'asignados a ti'})"
    )

    st.markdown("---")

    if not potenciales:
        st.info("📭 No hay clientes potenciales para mostrar con esos filtros.")
        return

    # ===============================
    # 🧾 Tarjetas de potenciales
    # ===============================
    cols = st.columns(3)
    for i, c in enumerate(potenciales):
        with cols[i % 3]:
            _render_potencial_card(c, supabase)

    # ===============================
    # 🔢 Paginación
    # ===============================
    st.markdown("---")
    pag1, pag2, pag3 = st.columns(3)
    with pag1:
        if st.button("⬅️ Anterior", disabled=page <= 1):
            st.session_state["pot_page"] = page - 1
            st.rerun()
    with pag2:
        st.write(f"Página {page} / {total_paginas}")
    with pag3:
        if st.button("Siguiente ➡️", disabled=page >= total_paginas):
            st.session_state["pot_page"] = page + 1
            st.rerun()


# =========================================================
# 🧾 Tarjeta de cliente potencial
# =========================================================
def _render_potencial_card(c: Dict[str, Any], supabase):
    apply_orbe_theme()

    razon = _safe(c.get("razon_social"))
    ident = _safe(c.get("identificador"))

    estado = get_estado_label(c.get("estadoid"), supabase) or "Potencial"
    categoria = get_categoria_label(c.get("categoriaid"), supabase) or "-"
    grupo = get_grupo_label(c.get("grupoid"), supabase) or "Sin grupo"
    trabajador = get_trabajador_label(c.get("trabajadorid"), supabase) or "Sin comercial"
    fid = _normalize_id(c.get("formapagoid"))
    forma_pago = get_formapago_label(fid, supabase) if fid else "-"

    completo = bool(c.get("perfil_completo", False))

    # Badge de perfil
    perfil_html = (
        "<span style='color:#16a34a;font-weight:600;'>🟢 Perfil completo</span>"
        if completo
        else "<span style='color:#dc2626;font-weight:600;'>🔴 Faltan datos</span>"
    )

    color_estado = "#3b82f6"  # azul “Potencial”

    html = f"""
    <div style="border:1px solid #d1fae5;border-radius:12px;
                background:#f0fdf4;padding:14px;margin-bottom:14px;
                box-shadow:0 1px 3px rgba(0,0,0,0.08);">

        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-size:1.05rem;font-weight:600;
                            white-space:nowrap;overflow:hidden;
                            text-overflow:ellipsis;max-width:230px;">
                    🌱 {razon}
                </div>
                <div style="color:#6b7280;font-size:0.9rem;
                            white-space:nowrap;overflow:hidden;
                            text-overflow:ellipsis;max-width:230px;">
                    {ident}
                </div>
            </div>
            <div style="color:{color_estado};font-weight:600;
                        white-space:nowrap;margin-left:8px;">
                Potencial
            </div>
        </div>

        <div style="margin-top:8px;font-size:0.9rem;line-height:1.45;">
            🧩 <b>Categoría:</b> {categoria}<br>
            👥 <b>Grupo:</b> {grupo}<br>
            🧑 <b>Comercial:</b> {trabajador}<br>
            💳 <b>Forma de pago:</b> {forma_pago}<br>
            {perfil_html}
        </div>
    </div>
    """

    st_html(html, height=230)

    col1, col2, col3 = st.columns(3)

    # Ficha
    with col1:
        if st.button("📄 Ficha", key=f"ficha_pot_{c['clienteid']}", use_container_width=True):
            st.session_state.update(
                {
                    "cliente_potencial_id": c["clienteid"],
                    "show_potencial_modal": True,
                    "pot_confirm_delete": False,
                }
            )
            st.rerun()

    # Crear presupuesto (opcional, igual que clientes)
    with col2:
        if st.button("📨 Presupuesto", key=f"pres_pot_{c['clienteid']}", use_container_width=True):
            try:
                supabase.table("presupuesto").insert(
                    {
                        "numero": f"PRES-{date.today().year}-{c['clienteid']}",
                        "clienteid": c["clienteid"],
                        "estado_presupuestoid": 1,
                        "fecha_presupuesto": date.today().isoformat(),
                        "observaciones": "Presupuesto creado desde cliente potencial.",
                        "editable": True,
                        "facturar_individual": False,
                    }
                ).execute()
                st.toast(f"📨 Presupuesto creado para {razon}.", icon="📨")
            except Exception as e:
                st.error(f"❌ Error creando presupuesto: {e}")

    # Convertir a cliente
    with col3:
        if completo:
            if st.button("🚀 Convertir", key=f"conv_{c['clienteid']}", use_container_width=True):
                try:
                    supabase.table("cliente").update(
                        {"tipo_cliente": "cliente", "estadoid": 1}
                    ).eq("clienteid", c["clienteid"]).execute()
                    st.success(f"🎉 {razon} convertido a cliente activo.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al convertir: {e}")
        else:
            st.button(
                "❌ Incompleto",
                key=f"no_conv_{c['clienteid']}",
                use_container_width=True,
                disabled=True,
            )


# =========================================================
# 🌱 Ficha completa de cliente potencial (arriba)
# =========================================================
def _render_potencial_ficha(supabase):
    apply_orbe_theme()

    clienteid = st.session_state.get("cliente_potencial_id")
    if not clienteid:
        return

    # Cargar datos base
    try:
        cli = (
            supabase.table("cliente")
            .select(
                "clienteid, razon_social, identificador, trabajadorid, formapagoid, "
                "grupoid, categoriaid, estadoid, perfil_completo, tipo_cliente, observaciones"
            )
            .eq("clienteid", int(clienteid))
            .single()
            .execute()
            .data
        )
    except Exception as e:
        st.error(f"❌ Error cargando la ficha del potencial: {e}")
        return

    razon = cli.get("razon_social") or "(Sin nombre)"
    identificador = cli.get("identificador") or "-"
    tipo_cliente = cli.get("tipo_cliente") or "potencial"
    estado_txt = get_estado_label(cli.get("estadoid"), supabase) or "Potencial"
    grupo = get_grupo_label(cli.get("grupoid"), supabase) or "Sin grupo"
    categoria = get_categoria_label(cli.get("categoriaid"), supabase) or "-"
    comercial = get_trabajador_label(cli.get("trabajadorid"), supabase) or "Sin comercial"
    forma_pago = get_formapago_label(cli.get("formapagoid"), supabase) or "-"
    perfil_completo_flag = bool(cli.get("perfil_completo", False))

    # ======================================================
    # 📋 Evaluar estado del perfil (igual que tu lógica antigua)
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
        tiene_dir = bool(
            dir_fiscal
            and dir_fiscal[0].get("direccion")
            and dir_fiscal[0].get("cp")
        )
    except Exception:
        tiene_dir = False

    tiene_pago = bool(cli.get("formapagoid"))
    tiene_trab = bool(cli.get("trabajadorid"))

    faltan: List[str] = []
    if not tiene_dir:
        faltan.append("Dirección fiscal con código postal")
    if not tiene_pago:
        faltan.append("Forma de pago definida")
    if not tiene_trab:
        faltan.append("Trabajador asignado")

    perfil_ok = len(faltan) == 0

    # Guardar flag perfil_completo en BBDD (como antes)
    try:
        supabase.table("cliente").update({"perfil_completo": perfil_ok}).eq(
            "clienteid", int(clienteid)
        ).execute()
    except Exception:
        pass

    # ======================================================
    # 🧱 Cabecera y resumen
    # ======================================================
    st.markdown("## ")

    col_close, col_title = st.columns([1, 4])
    with col_close:
        if st.button("⬅️ Cerrar ficha", key="close_potencial_ficha", use_container_width=True):
            st.session_state["show_potencial_modal"] = False
            st.session_state["cliente_potencial_id"] = None
            st.session_state["pot_confirm_delete"] = False
            st.rerun()

    with col_title:
        bg_color = "#f0fdf4" if perfil_ok else "#fef3c7"
        border_color = "#16a34a" if perfil_ok else "#f59e0b"
        perfil_txt = "✅ Perfil completo" if perfil_ok else "⚠️ Perfil incompleto"

        st.markdown(
            f"""
            <div style='padding:14px;border-radius:12px;
                        background:{bg_color};border:1px solid {border_color};'>
                <h3 style='margin:0;'>🌱 {razon}</h3>
                <p style='margin:4px 0 0 0;color:#4b5563;font-size:0.9rem;'>
                    <b>ID interno:</b> {clienteid} · 
                    <b>Identificador:</b> {identificador} · 
                    <b>Tipo:</b> {tipo_cliente} ·
                    <b>Estado:</b> {estado_txt}
                </p>
                <p style='margin:4px 0 0 0;color:#065f46;font-weight:600;'>{perfil_txt}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Resumen detalle
    st.markdown(
        f"""
        <div style='margin-top:8px;margin-bottom:8px;
                    padding:12px 14px;border-radius:12px;
                    background:#ffffff;border:1px solid #e5e7eb;'>
            <div style='display:flex;flex-wrap:wrap;gap:18px;font-size:0.9rem;color:#374151;'>
                <div><b>Categoría:</b> {categoria}</div>
                <div><b>Grupo:</b> {grupo}</div>
                <div><b>Comercial:</b> {comercial}</div>
                <div><b>Forma de pago:</b> {forma_pago}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Bloque estado perfil
    color_bg = "#dcfce7" if perfil_ok else "#fef3c7"
    color_border = "#16a34a" if perfil_ok else "#fcd34d"

    st.markdown(
        f"""
        <div style="background:{color_bg};border:1px solid {color_border};
                    padding:10px 14px;border-radius:8px;margin-bottom:10px;">
            <b>📋 Estado del perfil</b><br>
            {'✅ Dirección fiscal con CP' if tiene_dir else '❌ Falta dirección fiscal con CP'}<br>
            {'✅ Forma de pago definida' if tiene_pago else '❌ Falta forma de pago'}<br>
            {'✅ Trabajador asignado' if tiene_trab else '❌ Falta trabajador asignado'}<br>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Observaciones breves en ficha base (si existe)
    obs_breve = cli.get("observaciones")
    if obs_breve:
        st.info(obs_breve)

    st.markdown("---")

    # ======================================================
    # 🧷 TABS (sin Presupuestos/Pedidos → opción B)
    # ======================================================
    (
        tab_dir,
        tab_fact,
        tab_contactos,
        tab_obs,
        tab_crm,
        tab_conv,
    ) = st.tabs(
        [
            "🏠 Direcciones",
            "💳 Facturación",
            "👥 Contactos",
            "🗒️ Observaciones",
            "💬 CRM",
            "🚀 Conversión",
        ]
    )

    with tab_dir:
        render_direccion_form(supabase, int(clienteid), modo="potencial")

    with tab_fact:
        render_facturacion_form(supabase, int(clienteid))

    with tab_contactos:
        render_contacto_form(supabase, int(clienteid))

    with tab_obs:
        render_observaciones_form(supabase, int(clienteid))

    with tab_crm:
        render_crm_form(supabase, int(clienteid))

    # TAB Conversión
    with tab_conv:
        st.markdown("### 🚀 Conversión a cliente activo")
        if perfil_ok:
            st.success(
                "✅ El perfil está completo. Puedes convertir este potencial en cliente activo."
            )
        else:
            st.warning("⚠️ Debes completar los siguientes puntos antes de convertir:")
            for m in faltan:
                st.markdown(f"- ❌ {m}")

        st.markdown("---")

        col_a, col_b = st.columns([2, 1])
        with col_a:
            if perfil_ok:
                if st.button(
                    "✅ Convertir a cliente activo",
                    key="convertir_cliente_potencial_real",
                    use_container_width=True,
                ):
                    try:
                        supabase.table("cliente").update(
                            {"tipo_cliente": "cliente", "estadoid": 1}
                        ).eq("clienteid", int(clienteid)).execute()
                        st.success("🎉 Cliente potencial convertido a cliente activo correctamente.")
                        st.session_state["show_potencial_modal"] = False
                        st.session_state["cliente_potencial_id"] = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al convertir cliente: {e}")
            else:
                st.button(
                    "✅ Convertir a cliente activo",
                    key="convertir_cliente_potencial_disabled",
                    disabled=True,
                    use_container_width=True,
                )

        with col_b:
            st.markdown("### ")
            if not st.session_state.get("pot_confirm_delete"):
                if st.button("🗑️ Eliminar potencial", use_container_width=True):
                    st.session_state["pot_confirm_delete"] = True
                    st.warning("⚠️ Pulsa **Confirmar eliminación** para borrar este cliente potencial.")
            else:
                col_c, col_d = st.columns(2)
                with col_c:
                    if st.button("❌ Cancelar", use_container_width=True):
                        st.session_state["pot_confirm_delete"] = False
                        st.rerun()
                with col_d:
                    if st.button("✅ Confirmar", use_container_width=True):
                        try:
                            supabase.table("cliente").delete().eq(
                                "clienteid", int(clienteid)
                            ).execute()
                            st.success("🗑️ Cliente potencial eliminado correctamente.")
                            st.session_state["pot_confirm_delete"] = False
                            st.session_state["show_potencial_modal"] = False
                            st.session_state["cliente_potencial_id"] = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al eliminar cliente: {e}")
