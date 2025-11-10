# modules/cliente_potencial_lista.py
import streamlit as st
import math
from datetime import date

from modules.cliente_models import (
    load_estados_cliente,
    load_categorias,
    load_grupos,
    load_trabajadores,
    get_estado_label,
    get_categoria_label,
    get_grupo_label,
    get_trabajador_label,
)

from modules.orbe_theme import apply_orbe_theme

    # ✏️ Formularios organizados en pestañas
from modules.cliente_direccion_form import render_direccion_form
from modules.cliente_facturacion_form import render_facturacion_form
from modules.cliente_observacion_form import render_observaciones_form
from modules.cliente_crm_form import render_crm_form
from modules.cliente_contacto_form import render_contacto_form
# =========================================================
# 💅 Estilos globales responsive (modo móvil / tablet)
# =========================================================
st.markdown("""
<style>
main, [data-testid="stAppViewContainer"] {
    max-width: 1200px !important;
    margin: auto;
    padding: 1rem 2rem;
}
h1, h2, h3 { color: #065f46 !important; }
.card-pot {
    border: 1px solid #d1fae5;
    border-radius: 12px;
    background: #f0fdf4;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    padding: 14px;
    margin-bottom: 10px;
}
@media (max-width: 900px) {
    [data-testid="column"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
}
div.stButton > button {
    background: linear-gradient(90deg, #16a34a, #15803d);
    color: white !important;
    border: none !important;
    border-radius: 10px;
    font-weight: 500;
    padding: 0.6rem 1rem !important;
}
div.stButton > button:hover {
    background: linear-gradient(90deg, #15803d, #166534);
}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# 🌱 VISTA PRINCIPAL — CLIENTES POTENCIALES
# ==========================================================
def render_cliente_potencial_lista(supabase):
    apply_orbe_theme()

    st.header("🌱 Gestión de clientes potenciales")
    st.caption("Visualiza y gestiona tus clientes potenciales, completa su perfil y conviértelos en clientes activos cuando estén listos.")

    trabajadorid = st.session_state.get("trabajadorid", 13)
    st.session_state.setdefault("pot_page", 1)

    page_size = 9
    estados = load_estados_cliente(supabase)
    categorias = load_categorias(supabase)
    grupos = load_grupos(supabase)
    trabajadores = load_trabajadores(supabase)
    # ---------------------------------------------------------
    # 🎨 Cabecera visual
    # ---------------------------------------------------------
    st.markdown("""
    <div style="background:#ecfdf5;padding:16px 20px;border-radius:10px;margin-bottom:12px;
                border-left:5px solid #16a34a;">
        <h3 style="margin:0;color:#065f46;">🌱 Panel de Clientes Potenciales</h3>
        <p style="color:#374151;margin:2px 0 8px 0;font-size:0.9rem;">
            Gestiona tus clientes potenciales, completa su perfil y conviértelos en clientes activos.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 🔍 Buscador + métricas
    c1, c2 = st.columns([3, 1])
    with c1:
        q = st.text_input("Buscar potencial", placeholder="Razón social o identificador…", key="pot_q")
    with c2:
        st.metric("🔎 Resultados", st.session_state.get("pot_result_count", 0))

    st.markdown("---")

    # ---------------------------------------------------------
    # ⚙️ Filtros avanzados (alineados con clientes)
    # ---------------------------------------------------------
    with st.expander("⚙️ Filtros avanzados", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            perfil_sel = st.selectbox("Perfil", ["Todos", "Completos", "Incompletos"], key="pot_perfil")
        with c2:
            ver_todos = st.toggle("👀 Ver todos", value=False)
        with c3:
            estado_sel = st.selectbox("Estado", ["Todos"] + list(estados.keys()), key="pot_estado")
        with c4:
            trab_sel = st.selectbox("Trabajador", ["Todos"] + list(trabajadores.keys()), key="pot_trab")

    # ------------------------------
    # 📊 Query principal
    # ------------------------------
    total = 0
    potenciales = []

    try:
        base = (
            supabase.table("cliente")
            .select("clienteid, razon_social, identificador, estadoid, categoriaid, grupoid, trabajadorid, perfil_completo")
            .eq("tipo_cliente", "potencial")
        )

        if q:
            base = base.or_(f"razon_social.ilike.%{q}%,identificador.ilike.%{q}%")
        if not ver_todos:
            base = base.eq("trabajadorid", trabajadorid)
        if perfil_sel != "Todos":
            base = base.eq("perfil_completo", perfil_sel == "Completos")

        base = base.order("razon_social", desc=False)
        data = base.execute()
        potenciales = data.data or []
        total = len(potenciales)


        
    except Exception as e:
        st.error(f"❌ Error cargando clientes potenciales: {e}")



    st.caption(f"Mostrando {total} potenciales {'(todos)' if ver_todos else '(solo los tuyos)'}")
    # ---------------------------------------------------------
    # 📈 Panel de métricas rápidas
    # ---------------------------------------------------------
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("🌱 Total potenciales", total)
    col2.metric("👁️ Vista", "Tarjetas")
    col3.metric("📆 Última actualización", date.today().strftime("%d/%m/%Y"))

    st.markdown("---")

    # ---------------------------------------------------------
    # 📄 Resumen de resultados
    # ---------------------------------------------------------
    resumen = f"Mostrando {total} clientes potenciales {'(todos los trabajadores)' if ver_todos else '(solo los asignados a ti)'}"
    st.caption(resumen)
    st.markdown("---")

    # ---------------------------------------------------------
    # 💅 Estilos adicionales coherentes
    # ---------------------------------------------------------
    st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
        color: #065f46 !important;
    }
    div.stButton > button {
        background: linear-gradient(90deg, #16a34a, #15803d) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #15803d, #166534) !important;
    }
    </style>
    """, unsafe_allow_html=True)




    if not potenciales:
        st.info("📭 No hay clientes potenciales para mostrar.")
        return

    # ------------------------------
    # 🧾 Renderizado de tarjetas
    # ------------------------------
    cols = st.columns(3)
    for i, c in enumerate(potenciales):
        with cols[i % 3]:
            _render_potencial_card(c, supabase)

    # ------------------------------
    # 📑 Paginación
    # ------------------------------
    st.markdown("---")
    total_pages = max(1, math.ceil(total / page_size))
    colp1, colp2, _ = st.columns([1, 1, 6])
    with colp1:
        if st.button("◀️", disabled=st.session_state.pot_page <= 1):
            st.session_state.pot_page -= 1
            st.rerun()
    with colp2:
        if st.button("▶️", disabled=st.session_state.pot_page >= total_pages):
            st.session_state.pot_page += 1
            st.rerun()

    # Modal activo
    if st.session_state.get("show_potencial_modal"):
        render_potencial_modal(supabase)

def _render_potencial_card(c, supabase):
    apply_orbe_theme()

    """Tarjeta visual del cliente potencial, coherente con la ficha principal."""
    razon = c.get("razon_social", "-")
    ident = c.get("identificador", "-")
    estado = get_estado_label(c.get("estadoid"), supabase)
    categoria = get_categoria_label(c.get("categoriaid"), supabase)
    grupo = get_grupo_label(c.get("grupoid"), supabase)
    trabajador = get_trabajador_label(c.get("trabajadorid"), supabase)
    completo = c.get("perfil_completo", False)

    # Badge de perfil
    perfil_html = (
        "<span style='color:#16a34a;font-weight:600;'>🟢 Perfil completo</span>"
        if completo
        else "<span style='color:#dc2626;font-weight:600;'>🔴 Faltan datos</span>"
    )

    # Colores de estado y borde
    color_estado = {
        "Activo": "#10b981",
        "Potencial": "#16a34a",
        "Suspendido": "#dc2626",
    }.get(estado, "#6b7280")

    st.markdown(
        f"""
        <div style="border:1px solid #d1fae5;border-radius:12px;
                    background:#f0fdf4;padding:14px;margin-bottom:14px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:1.05rem;font-weight:600;color:#065f46;">🌱 {razon}</div>
                    <div style="color:#6b7280;font-size:0.9rem;">{ident}</div>
                </div>
                <div style="color:{color_estado};font-weight:600;">{estado}</div>
            </div>
            <div style="margin-top:8px;font-size:0.9rem;line-height:1.4;">
                🧩 <b>Categoría:</b> {categoria}<br>
                👥 <b>Grupo:</b> {grupo}<br>
                🧑 <b>Trabajador:</b> {trabajador}<br>
                {perfil_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Botones de acción (alineados)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("📄 Ficha", key=f"ficha_pot_{c['clienteid']}", use_container_width=True):
            st.session_state.update({
                "cliente_actual": c["clienteid"],
                "show_potencial_modal": True,
                "confirm_delete": False,
            })
            st.rerun()
    with col2:
        if st.button("📨 Presupuesto", key=f"pres_pot_{c['clienteid']}", use_container_width=True):
            try:
                supabase.table("presupuesto").insert({
                    "numero": f"PRES-{date.today().year}-{c['clienteid']}",
                    "clienteid": c["clienteid"],
                    "estado_presupuestoid": 1,
                    "fecha_presupuesto": date.today().isoformat(),
                    "observaciones": "Presupuesto creado desde cliente potencial.",
                }).execute()
                st.toast(f"📨 Presupuesto creado para {razon}.", icon="📨")
            except Exception as e:
                st.error(f"❌ Error creando presupuesto: {e}")
    with col3:
        if completo:
            if st.button("🚀 Convertir a cliente", key=f"conv_{c['clienteid']}", use_container_width=True):
                try:
                    supabase.table("cliente").update(
                        {"tipo_cliente": "cliente", "estadoid": 1}
                    ).eq("clienteid", c["clienteid"]).execute()
                    st.success(f"🎉 {razon} convertido a cliente activo.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al convertir: {e}")
        else:
            st.button("❌ Incompleto", key=f"no_conv_{c['clienteid']}", use_container_width=True, disabled=True)


def render_potencial_modal(supabase):
    apply_orbe_theme()

    """Ficha visual profesional del cliente potencial."""
    if not st.session_state.get("show_potencial_modal"):
        return

    clienteid = st.session_state.get("cliente_actual")
    if not clienteid:
        st.warning("⚠️ No hay cliente activo.")
        return

    # ======================================================
    # 🌱 Cabecera del cliente potencial
    # ======================================================
    st.markdown("---")

    try:
        cli = (
            supabase.table("cliente")
            .select("razon_social, identificador, trabajadorid, formapagoid, grupoid, categoriaid, perfil_completo")
            .eq("clienteid", int(clienteid))
            .single()
            .execute()
            .data
        )
    except Exception:
        cli = {}

    perfil_ok = cli.get("perfil_completo", False)
    bg_color = "#f0fdf4" if perfil_ok else "#fef3c7"
    border_color = "#16a34a" if perfil_ok else "#f59e0b"

    st.markdown(
        f"""
        <div style="border-left:6px solid {border_color};
                    background:{bg_color};
                    border-radius:10px;
                    padding:16px;
                    margin-bottom:12px;">
            <h3 style="margin:0;color:#065f46;">🌱 {cli.get('razon_social','(Sin nombre)')}</h3>
            <p style="color:#374151;margin:2px 0;">Identificador: <b>{cli.get('identificador','-')}</b></p>
            <p style="color:#065f46;margin:2px 0;font-weight:500;">
                Estado actual: <b>Potencial</b><br>
                Perfil: {"✅ Completo" if perfil_ok else "⚠️ Incompleto"}
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
            st.session_state.update({"show_potencial_modal": False, "confirm_delete": False})
            st.rerun()

    with c2:
        if not st.session_state.get("confirm_delete"):
            if st.button("🗑️  Eliminar", use_container_width=True):
                st.session_state["confirm_delete"] = True
                st.warning("⚠️ Pulsa **Confirmar eliminación** para borrar este cliente potencial.")
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state["confirm_delete"] = False
                    st.rerun()
            with col_b:
                if st.button("✅ Confirmar", use_container_width=True):
                    try:
                        supabase.table("cliente").delete().eq("clienteid", clienteid).execute()
                        st.success("🗑️ Cliente eliminado correctamente.")
                        st.session_state.update({"show_potencial_modal": False, "confirm_delete": False})
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al eliminar cliente: {e}")

    with c3:
        if st.button("📨  Crear presupuesto", use_container_width=True):
            try:
                supabase.table("presupuesto").insert({
                    "clienteid": clienteid,
                    "fecha_presupuesto": date.today().isoformat(),
                    "estado_presupuestoid": 1,
                    "observaciones": "Presupuesto creado desde cliente potencial."
                }).execute()
                st.toast("📨  Presupuesto creado correctamente.", icon="📨")
            except Exception as e:
                st.error(f"❌ Error creando presupuesto: {e}")

    # ======================================================
    # 📋 Estado del perfil
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
        tiene_dir = bool(dir_fiscal and dir_fiscal[0].get("direccion") and dir_fiscal[0].get("cp"))
        tiene_pago = bool(cli.get("formapagoid"))
        tiene_trab = bool(cli.get("trabajadorid"))

        faltan = []
        if not tiene_dir: faltan.append("Dirección fiscal (con CP)")
        if not tiene_pago: faltan.append("Forma de pago")
        if not tiene_trab: faltan.append("Trabajador asignado")
        perfil_ok = not faltan

        color_bg = "#dcfce7" if perfil_ok else "#fef3c7"
        color_border = "#16a34a" if perfil_ok else "#fcd34d"

        with st.expander("📋 Estado del perfil", expanded=True):
            st.markdown(
                f"""
                <div style="background:{color_bg};border:1px solid {color_border};
                            padding:10px;border-radius:8px;margin-top:10px;">
                    <b>Cliente:</b> {cli.get('razon_social','-')}<br>
                    {'✅ Dirección fiscal añadida' if tiene_dir else '❌ Sin dirección fiscal o CP'}<br>
                    {'✅ Forma de pago definida' if tiene_pago else '❌ Sin forma de pago'}<br>
                    {'✅ Trabajador asignado' if tiene_trab else '❌ Sin trabajador asignado'}<br><br>
                    {("<span style='color:#16a34a;font-weight:600;'>Todo correcto</span>" 
                    if perfil_ok else "".join([f"<span style='color:#dc2626'>• {m}</span><br>" for m in faltan]))}
                </div>
                """,
                unsafe_allow_html=True,
            )
            try:
                supabase.table("cliente").update({"perfil_completo": perfil_ok}).eq("clienteid", clienteid).execute()
            except Exception:
                pass
    except Exception as e:
        st.warning(f"⚠️ No se pudo evaluar el perfil: {e}")

    # ======================================================
    # 🧭 Pestañas principales
    # ======================================================
    st.session_state["cliente_actual"] = clienteid

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Direcciones",
        "💳 Facturación",
        "👥 Contactos",
        "🗒️ Observaciones",
        "💬 Seguimiento / CRM"
    ])

    with tab1:
        render_direccion_form(supabase, clienteid, modo="potencial")

    with tab2:
        render_facturacion_form(supabase, clienteid)

    with tab3:
        render_contacto_form(supabase, clienteid)

    with tab4:
        render_observaciones_form(supabase, clienteid)

    with tab5:
        st.markdown("### 💬 Actividad CRM del potencial")
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
                st.info("📭 Sin actuaciones aún.")
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
                    "titulo": "Nuevo seguimiento (potencial)",
                    "estado": "Pendiente",
                    "prioridad": "Media",
                    "descripcion": "Seguimiento creado desde ficha de cliente potencial."
                }).execute()
                st.toast("✅ Nueva actuación registrada.", icon="🗒️")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al crear la actuación: {e}")

    # ======================================================
    # 🚀 Conversión a cliente activo
    # ======================================================
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center;margin-top:30px;">
            <h3 style="color:#065f46;">🚀 Convertir a cliente activo</h3>
            <p style="color:#374151;margin-top:4px;">Completa el perfil y activa este cliente en el sistema.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if perfil_ok:
        if st.button("✅ Convertir a cliente activo", key="convertir_cliente_real", use_container_width=True):
            try:
                supabase.table("cliente").update(
                    {"tipo_cliente": "cliente", "estadoid": 1}
                ).eq("clienteid", clienteid).execute()
                st.success("🎉 Cliente convertido a cliente activo correctamente.")
                st.session_state["show_potencial_modal"] = False
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al convertir cliente: {e}")
    else:
        st.warning("⚠️ Completa los datos obligatorios antes de convertir a cliente (dirección, forma de pago y trabajador).")
