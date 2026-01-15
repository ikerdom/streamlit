# =========================================================
# 🗒️ FORM · Observaciones internas del cliente (UI ONLY)
# =========================================================
import streamlit as st
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional


# =========================================================
# 🔧 API helpers (UI ONLY)
# =========================================================
def api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return st.session_state.get("ORBE_API_URL") or "http://127.0.0.1:8000"


def api_get(path: str, params: Optional[dict] = None):
    try:
        r = requests.get(f"{api_base()}{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Error API: {e}")
        return []


def api_post(path: str, payload: dict):
    try:
        r = requests.post(f"{api_base()}{path}", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Error API: {e}")
        return None


# =========================================================
# 🗒️ Render principal (UI ONLY)
# =========================================================
def render_observaciones_form(clienteid: int, key_prefix: str = ""):
    clienteid = int(clienteid)
    kp = key_prefix or ""

    # =========================
    # CABECERA
    # =========================
    st.markdown(
        """
        <div style="
            padding:10px;
            background:#f8fafc;
            border:1px solid #e5e7eb;
            border-radius:10px;
            margin-bottom:10px;">
            <div style="font-size:1.15rem; font-weight:600; color:#111827;">
                🗒️ Observaciones internas
            </div>
            <div style="font-size:0.9rem; color:#6b7280;">
                Notas privadas de seguimiento, incidencias o información relevante del cliente.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================
    # 📋 CARGA DE OBSERVACIONES (API)
    # =========================
    notas: List[Dict[str, Any]] = api_get(
        f"/api/clientes/{clienteid}/observaciones"
    )

    # =========================
    # 🎨 MAPA DE COLORES (sobrio ERP)
    # =========================
    color_map = {
        "General": "#f8fafc",
        "Comercial": "#eff6ff",
        "Administración": "#fffbeb",
        "Otro": "#faf5ff",
    }

    border_map = {
        "General": "#94a3b8",
        "Comercial": "#3b82f6",
        "Administración": "#f59e0b",
        "Otro": "#8b5cf6",
    }

    # =========================
    # 🧾 LISTADO DE NOTAS
    # =========================
    if notas:
        for n in notas:
            tipo = n.get("tipo", "General")
            comentario = n.get("comentario", "")
            usuario = n.get("usuario") or "Desconocido"

            fecha_raw = n.get("fecha")
            fecha = "-"
            if fecha_raw:
                # Intento formatear bonito si viene ISO
                try:
                    dt = datetime.fromisoformat(str(fecha_raw).replace("Z", "+00:00"))
                    fecha = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    fecha = str(fecha_raw)

            bg = color_map.get(tipo, "#f8fafc")
            border = border_map.get(tipo, "#94a3b8")

            st.markdown(
                f"""
                <div style="
                    background:{bg};
                    border:1px solid #e5e7eb;
                    border-left:5px solid {border};
                    border-radius:8px;
                    padding:12px 14px;
                    margin-bottom:8px;">

                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="font-weight:600;color:#111827;">
                            🗂️ {tipo}
                        </div>
                        <div style="font-size:0.8rem;color:#6b7280;">
                            {fecha}
                        </div>
                    </div>

                    <div style="margin-top:6px;color:#111827;font-size:0.95rem;">
                        {comentario}
                    </div>

                    <div style="margin-top:6px;text-align:right;
                                font-size:0.8rem;color:#6b7280;">
                        ✏️ {usuario}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("📭 No hay observaciones registradas aún.")

    # =========================
    # ➕ NUEVA OBSERVACIÓN
    # =========================
    st.markdown("---")

    with st.expander("➕ Añadir nueva observación"):
        col1, col2 = st.columns(2)

        with col1:
            tipo = st.selectbox(
                "Tipo de nota",
                ["General", "Comercial", "Administración", "Otro"],
                index=0,
                key=f"{kp}obs_tipo_{clienteid}",
            )

        with col2:
            usuario = st.session_state.get("user_nombre", "Desconocido")
            st.text_input("Usuario", value=usuario, disabled=True, key=f"{kp}obs_user_{clienteid}")

        comentario = st.text_area(
            "Comentario",
            placeholder="Ejemplo: Cliente solicita retrasar entrega una semana…",
            height=100,
            key=f"{kp}obs_text_{clienteid}",
        )

        if st.button("💾 Guardar observación", width="stretch", key=f"{kp}obs_save_{clienteid}"):
            if not comentario.strip():
                st.warning("⚠️ Debes escribir un comentario.")
                return

            payload = {
                "tipo": tipo,
                "comentario": comentario.strip(),
                "usuario": usuario,
            }

            res = api_post(
                f"/api/clientes/{clienteid}/observaciones",
                payload,
            )

            if res:
                st.toast("✅ Observación guardada correctamente.")
                st.rerun()
