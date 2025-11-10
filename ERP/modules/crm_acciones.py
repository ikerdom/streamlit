# =============================================================
# 📅 CRM · Acciones y Calendario FullCalendar
# =============================================================

from __future__ import annotations
import calendar as _pycalendar
from datetime import date, datetime, timedelta, time
from typing import Dict, List, Optional
import uuid
import streamlit as st
from dateutil.parser import parse as parse_date

# =============================================================
# 📦 Dependencias
# =============================================================
try:
    from streamlit_calendar import calendar as st_calendar
    _HAS_CAL = True
except Exception:
    _HAS_CAL = False

# =============================================================
# 🔗 Panel de detalle
# =============================================================
try:
    from modules.crm_accion_detalle import render_crm_accion_detalle
except Exception:
    def render_crm_accion_detalle(*_, **__):
        st.info("Panel de detalle no disponible: importa modules.crm_accion_detalle")

# =============================================================
# 🎨 Estilos y helpers
# =============================================================
_ESTADO_COLOR = {
    "pendiente": "#ef4444",   # rojo
    "completada": "#16a34a",  # verde
    "cancelada": "#6b7280",   # gris
}

_CSS = """
<style>
.fc .fc-toolbar-title{font-weight:700}
.fc .fc-daygrid-event,.fc .fc-timegrid-event{border-radius:10px}
.fc .fc-button{border-radius:10px}
.fc-event:hover{filter:brightness(1.05)}
.fc .fc-button-primary{background:#2563eb;border:none}
.fc .fc-button-primary:hover{background:#1d4ed8}
</style>
"""

def _color_for(estado: Optional[str]) -> str:
    e = (estado or "").strip().lower()
    return _ESTADO_COLOR.get(e, _ESTADO_COLOR["pendiente"])

def _to_event(row: dict) -> dict:
    """Convierte una fila de crm_actuacion en evento para FullCalendar."""
    start = end = None
    if row.get("fecha_accion"):
        start = parse_date(str(row["fecha_accion"])).isoformat()
        end = (parse_date(str(row["fecha_accion"])) + timedelta(hours=1)).isoformat()
    elif row.get("fecha_vencimiento"):
        d = parse_date(str(row["fecha_vencimiento"])).date()
        start = datetime.combine(d, time.min).isoformat()
        end = (datetime.combine(d, time.min) + timedelta(days=1)).isoformat()
    return {
        "id": str(row.get("crm_actuacionid")),
        "title": (row.get("titulo") or "(Sin título)"),
        "start": start,
        "end": end,
        "allDay": not bool(row.get("fecha_accion")),
        "color": _color_for(row.get("estado")),
        "extendedProps": {
            "estado": row.get("estado"),
            "canal": row.get("canal"),
            "prioridad": row.get("prioridad"),
            "clienteid": row.get("clienteid"),
        },
    }

# =============================================================
# 🔧 Helpers de actualización
# =============================================================
def _update_accion(supabase, accionid: int, changes: dict):
    """Actualiza una acción y marca recarga en session_state."""
    try:
        clean = {}
        for k, v in changes.items():
            if isinstance(v, (datetime, date)):
                clean[k] = v.isoformat()
            else:
                clean[k] = v
        supabase.table("crm_actuacion").update(clean).eq("crm_actuacionid", accionid).execute()
        st.toast("✅ Acción actualizada correctamente.", icon="✅")
        st.session_state["force_reload"] = True
    except Exception as e:
        st.error(f"❌ Error al actualizar: {e}")

def _load_trabajadores(supabase) -> List[dict]:
    try:
        res = supabase.table("trabajador").select("trabajadorid,nombre,apellidos").execute()
        return res.data or []
    except Exception:
        return []

# =============================================================
# 🚀 Render principal
# =============================================================
def render_crm_acciones(supabase, clienteid: Optional[int] = None):
    st.markdown(_CSS, unsafe_allow_html=True)

    if not _HAS_CAL:
        st.error("Falta dependencia `streamlit-calendar`. Instala con: `pip install streamlit-calendar`.")
        return

    trabajadorid = st.session_state.get("trabajadorid")
    if not trabajadorid:
        st.warning("⚠️ No hay sesión de trabajador activa.")
        return

    if clienteid is None:
        clienteid = st.session_state.get("cliente_actual")

    # ---------- Controles ----------
    top_l, top_c, top_r = st.columns([2, 3, 2])
    with top_l:
        vista = st.radio(
            "Vista",
            ["Mensual", "Semanal", "Diaria"],
            horizontal=True,
            key="crm_vista",
            index=["Mensual", "Semanal", "Diaria"].index(st.session_state.get("crm_vista", "Mensual")),
        )

    with top_c:
        fecha_base = st.date_input("Fecha base", value=st.session_state.get("crm_fecha_base", date.today()))
        st.session_state["crm_fecha_base"] = fecha_base

    with top_r:
        col1, col2 = st.columns(2)
        col1.button("◀️ Anterior", on_click=_mover, args=(-1,), key="btn_prev")
        col2.button("Siguiente ▶️", on_click=_mover, args=(1,), key="btn_next")

    # ---------- Filtros ----------
    f1, f2, f3 = st.columns(3)
    filtro_estado = f1.selectbox("Estado", ["Todos", "Pendiente", "Completada", "Cancelada"], index=0)
    filtro_canal = f2.selectbox("Canal", ["Todos", "Teléfono", "Email", "Reunión", "Otro"], index=0)
    buscar = f3.text_input("Buscar título...", placeholder="Ej: llamada, presupuesto, reunión…")

    # ---------- Alta rápida ----------
    with st.expander("➕ Añadir nueva acción", expanded=False):
        with st.form("form_accion"):
            c1, c2 = st.columns(2)
            with c1:
                titulo = st.text_input("Título *")
                fecha_venc = st.date_input("Fecha límite", value=fecha_base)
                hora = st.time_input("Hora (opcional)", value=time(9, 0))
            with c2:
                canal = st.selectbox("Canal", ["Teléfono", "Email", "Reunión", "Otro"])
                prioridad = st.selectbox("Prioridad", ["Alta", "Media", "Baja"], index=1)
                descripcion = st.text_area("Descripción", placeholder="Detalles…")

            # -----------------------------------------------
            # 👥 Asignar trabajador responsable (por defecto logueado)
            # -----------------------------------------------
            st.markdown("### 👥 Asignar trabajador responsable")
            trabajadores = _load_trabajadores(supabase)

            if not trabajadores:
                st.warning("⚠️ No se pudieron cargar los trabajadores.")
                trabajadores_map = {}
            else:
                trabajadores_map = {
                    f"{t['nombre']} {t['apellidos']}": t["trabajadorid"]
                    for t in trabajadores
                }

            # Determinar índice por defecto
            nombre_logueado = (st.session_state.get("user_nombre") or "").strip().lower()
            idx_default = 0
            for i, (nombre, tid) in enumerate(trabajadores_map.items()):
                if nombre_logueado and nombre_logueado in nombre.lower():
                    idx_default = i
                    break

            trab_sel = st.selectbox(
                "Asignar a:",
                list(trabajadores_map.keys()) or ["(Ninguno)"],
                index=idx_default if trabajadores_map else 0,
                help="Selecciona el trabajador responsable de esta acción."
            )
            trabajador_asignado = trabajadores_map.get(trab_sel, trabajadorid)
            enviado = st.form_submit_button("💾 Guardar", width="stretch")

        # ---------- Guardado ----------
        if enviado and titulo.strip():
            payload = {
                "titulo": titulo.strip(),
                "descripcion": descripcion or None,
                "canal": canal,
                "estado": "Pendiente",
                "fecha_vencimiento": fecha_venc.isoformat(),
                "prioridad": prioridad,
                "trabajadorid": trabajadorid,
                "trabajador_asignadoid": trabajador_asignado,
            }
            if hora:
                payload["fecha_accion"] = datetime.combine(fecha_venc, hora).replace(microsecond=0).isoformat()
            if clienteid:
                payload["clienteid"] = clienteid
            try:
                supabase.table("crm_actuacion").insert(payload).execute()
                st.toast(f"✅ Acción creada y asignada a {trab_sel}.", icon="✅")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al crear acción: {e}")

    # ---------- Carga ----------
    if st.session_state.get("force_reload"):
        st.session_state["force_reload"] = False
        st.rerun()

    try:
        q = (
            supabase.table("crm_actuacion")
            .select("crm_actuacionid,titulo,estado,canal,fecha_accion,fecha_vencimiento,prioridad,clienteid,trabajador_asignadoid")
            .eq("trabajador_asignadoid", trabajadorid)
            .order("fecha_vencimiento", desc=False)
        )
        if clienteid:
            q = q.eq("clienteid", clienteid)
        if filtro_estado != "Todos":
            q = q.eq("estado", filtro_estado)
        if filtro_canal != "Todos":
            q = q.eq("canal", filtro_canal)
        rows = q.execute().data or []
        if buscar:
            s = buscar.lower()
            rows = [r for r in rows if s in (r.get("titulo") or "").lower()]
    except Exception as e:
        st.error(f"❌ Error al cargar acciones: {e}")
        rows = []

    events = [_to_event(r) for r in rows]

    # ---------- Calendario ----------
    initial_view = {"Mensual": "dayGridMonth", "Semanal": "timeGridWeek", "Diaria": "timeGridDay"}[vista]
    options = {
        "initialView": initial_view,
        "locale": "es",
        "firstDay": 1,
        "nowIndicator": True,
        "slotMinTime": "08:00:00",
        "slotMaxTime": "20:00:00",
        "height": "auto",
        "expandRows": True,
        "selectable": True,
        "dayMaxEvents": True,
        "initialDate": fecha_base.isoformat(),
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek,timeGridDay"},
    }

    ret = st_calendar(events=events, options=options, key="crm_calendar")

    # ---------- Interacciones ----------
    ev_click = (ret.get("eventClick", {}) or {}).get("event")
    if ev_click and ev_click.get("id"):
        st.session_state["crm_accion_abierta"] = int(ev_click["id"])

    # ---------- Panel de detalle ----------
    if st.session_state.get("crm_accion_abierta"):
        eid = st.session_state["crm_accion_abierta"]
        suffix = str(uuid.uuid4())[:8]
        st.markdown("---")
        st.subheader("🧾 Detalle de la acción seleccionada")
        render_crm_accion_detalle(supabase, eid)

        st.markdown("### ⚙️ Acciones rápidas")
        # POSPONER
        with st.expander("⏰ Posponer acción", expanded=False):
            new_date = st.date_input("Nueva fecha", date.today() + timedelta(days=1), key=f"posp_date_{eid}_{suffix}")
            new_time = st.time_input("Nueva hora", time(9, 0), key=f"posp_time_{eid}_{suffix}")
            if st.button("💾 Guardar nueva fecha", key=f"btn_posp_{eid}_{suffix}", width="stretch"):
                _update_accion(supabase, eid, {
                    "fecha_vencimiento": new_date,
                    "fecha_accion": datetime.combine(new_date, new_time)
                })

        # REASIGNAR
        with st.expander("👥 Reasignar trabajador", expanded=False):
            trabajadores = _load_trabajadores(supabase)
            options = {f"{t['nombre']} {t['apellidos']}": t["trabajadorid"] for t in trabajadores}
            nuevo_id = st.selectbox("Asignar a:", list(options.keys()), key=f"reasg_sel_{eid}_{suffix}")
            if st.button("🔄 Reasignar", key=f"reasg_btn_{eid}_{suffix}", width="stretch"):
                _update_accion(supabase, eid, {"trabajador_asignadoid": options[nuevo_id]})

        # ESTADO
        with st.expander("📋 Cambiar estado", expanded=False):
            c1, c2, c3 = st.columns(3)
            if c1.button("✅ Completada", key=f"done_{eid}_{suffix}", width="stretch"):
                _update_accion(supabase, eid, {"estado": "Completada"})
            if c2.button("🚫 Cancelada", key=f"cancel_{eid}_{suffix}", width="stretch"):
                _update_accion(supabase, eid, {"estado": "Cancelada"})
            if c3.button("⏳ Pendiente", key=f"pend_{eid}_{suffix}", width="stretch"):
                _update_accion(supabase, eid, {"estado": "Pendiente"})

        st.markdown("---")
        if st.button("❌ Cerrar acción", key=f"cerrar_{eid}_{suffix}", width="stretch"):
            del st.session_state["crm_accion_abierta"]
            st.rerun()

# =============================================================
# ⏮️⏭️ Navegación
# =============================================================
def _mover(delta: int):
    base = st.session_state.get("crm_fecha_base", date.today())
    vista = st.session_state.get("crm_vista", "Mensual")
    if vista == "Mensual":
        y, m = base.year, base.month
        m += delta
        if m < 1:
            y -= 1; m = 12
        elif m > 12:
            y += 1; m = 1
        st.session_state["crm_fecha_base"] = date(y, m, min(base.day, _dias_mes(y, m)))
    elif vista == "Semanal":
        st.session_state["crm_fecha_base"] = base + timedelta(days=7 * delta)
    else:
        st.session_state["crm_fecha_base"] = base + timedelta(days=delta)

def _dias_mes(y: int, m: int) -> int:
    return _pycalendar.monthrange(y, m)[1]
