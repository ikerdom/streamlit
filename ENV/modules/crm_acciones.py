# =============================================================
# 📆 CRM · Acciones y Calendario (API FastAPI + FullCalendar)
# =============================================================

from __future__ import annotations
import calendar as _pycalendar
from datetime import date, datetime, timedelta, time
from typing import Optional
import uuid
import streamlit as st
from dateutil.parser import parse as parse_date

from modules.crm_api import listar as api_listar, crear as api_crear, actualizar as api_actualizar

# ==============================
# Dependencias de FullCalendar
# ==============================
try:
    from streamlit_calendar import calendar as st_calendar
    _HAS_CAL = True
except Exception:
    _HAS_CAL = False

# ==============================
# Estilos y helpers
# ==============================
_ESTADO_COLOR = {
    "pendiente": "#ef4444",
    "completada": "#16a34a",
    "cancelada": "#6b7280",
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


# ==============================
# UI principal
# ==============================
def render_crm_acciones(_supabase_unused=None, clienteid: Optional[int] = None):
    st.markdown(_CSS, unsafe_allow_html=True)

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
        col1.button("⬅️ Anterior", on_click=_mover, args=(-1,), key="btn_prev")
        col2.button("Siguiente ➡️", on_click=_mover, args=(1,), key="btn_next")

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

            st.markdown("### 👤 Asignar trabajador responsable")
            trabajador_asignado = trabajadorid  # por defecto el logueado
            enviado = st.form_submit_button("💾 Guardar", use_container_width=True)

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
                api_crear(payload)
                st.toast("✅ Acción creada.", icon="✅")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al crear acción: {e}")

    if st.session_state.get("force_reload"):
        st.session_state["force_reload"] = False
        st.rerun()

    # ---------- Carga desde API ----------
    try:
        payload = {
            "trabajador_asignadoid": trabajadorid,
            "clienteid": clienteid,
            "estado": None if filtro_estado == "Todos" else filtro_estado,
            "canal": None if filtro_canal == "Todos" else filtro_canal,
            "buscar": buscar or None,
        }
        rows = api_listar(payload).get("data", [])
    except Exception as e:
        st.error(f"❌ Error al cargar acciones: {e}")
        rows = []

    events = [_to_event(r) for r in rows]

    # ---------- Calendario / lista ----------
    if _HAS_CAL:
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

        ev_click = (ret.get("eventClick", {}) or {}).get("event")
        if ev_click and ev_click.get("id"):
            st.session_state["crm_accion_abierta"] = int(ev_click["id"])
    else:
        # Fallback silencioso sin dependencia externa
        if not rows:
            st.info("Sin actuaciones.")
        else:
            simple = [
                {
                    "ID": r.get("crm_actuacionid"),
                    "Título": r.get("titulo"),
                    "Estado": r.get("estado"),
                    "Fecha": r.get("fecha_accion") or r.get("fecha_vencimiento"),
                    "Canal": r.get("canal"),
                }
                for r in rows
            ]
            st.dataframe(simple, hide_index=True, use_container_width=True)

    if _HAS_CAL and st.session_state.get("crm_accion_abierta"):
        _render_panel_detalle(st.session_state["crm_accion_abierta"])


def _render_panel_detalle(accionid: int):
    suffix = str(uuid.uuid4())[:8]
    st.markdown("---")
    st.subheader("🧾 Detalle de la acción seleccionada")
    render_crm_accion_detalle = _lazy_import_detalle()
    if render_crm_accion_detalle:
        render_crm_accion_detalle(None, accionid)

    st.markdown("### ⚡ Acciones rápidas")
    with st.expander("⏰ Posponer acción", expanded=False):
        new_date = st.date_input("Nueva fecha", date.today() + timedelta(days=1), key=f"posp_date_{accionid}_{suffix}")
        new_time = st.time_input("Nueva hora", time(9, 0), key=f"posp_time_{accionid}_{suffix}")
        if st.button("💾 Guardar nueva fecha", key=f"btn_posp_{accionid}_{suffix}", use_container_width=True):
            try:
                api_actualizar(
                    accionid,
                    {
                        "fecha_vencimiento": new_date.isoformat(),
                        "fecha_accion": datetime.combine(new_date, new_time).isoformat(),
                    },
                )
                st.success("✅ Acción pospuesta.")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al posponer: {e}")

    with st.expander("👤 Reasignar trabajador", expanded=False):
        nuevo_id = st.number_input("ID trabajador", min_value=1, step=1, key=f"reasg_{accionid}_{suffix}")
        if st.button("♻️ Reasignar", key=f"reasg_btn_{accionid}_{suffix}", use_container_width=True):
            try:
                api_actualizar(accionid, {"trabajador_asignadoid": int(nuevo_id)})
                st.success("✅ Reasignado.")
                st.session_state["force_reload"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al reasignar: {e}")

    with st.expander("🎯 Cambiar estado", expanded=False):
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Completada", key=f"done_{accionid}_{suffix}", use_container_width=True):
            _set_estado(accionid, "Completada")
        if c2.button("🚫 Cancelada", key=f"cancel_{accionid}_{suffix}", use_container_width=True):
            _set_estado(accionid, "Cancelada")
        if c3.button("⏳ Pendiente", key=f"pend_{accionid}_{suffix}", use_container_width=True):
            _set_estado(accionid, "Pendiente")

    st.markdown("---")
    if st.button("Cerrar acción", key=f"cerrar_{accionid}_{suffix}", use_container_width=True):
        st.session_state.pop("crm_accion_abierta", None)
        st.rerun()


def _set_estado(accionid: int, estado: str):
    try:
        api_actualizar(accionid, {"estado": estado})
        st.success(f"✅ Estado cambiado a {estado}.")
        st.session_state["force_reload"] = True
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error actualizando estado: {e}")


def _lazy_import_detalle():
    try:
        from modules.crm_accion_detalle import render_crm_accion_detalle
        return render_crm_accion_detalle
    except Exception:
        st.info("Panel de detalle no disponible: importa modules.crm_accion_detalle")
        return None


# =============================================================
# Navegación fecha
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
