import os
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


# =========================================================
# 🔧 API helpers (UI ONLY)
# =========================================================
def api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return (
            os.getenv("ORBE_API_URL")
            or st.session_state.get("ORBE_API_URL")
            or "http://127.0.0.1:8000"
        )


def api_get(path: str, params: Optional[dict] = None):
    try:
        r = requests.get(f"{api_base()}{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Error API: {e}")
        return []


def api_post(path: str, payload: Optional[dict] = None):
    try:
        r = requests.post(f"{api_base()}{path}", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Error API: {e}")
        return None


def api_put(path: str, payload: dict):
    try:
        r = requests.put(f"{api_base()}{path}", json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Error API: {e}")
        return None


def api_delete(path: str):
    try:
        r = requests.delete(f"{api_base()}{path}", timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"❌ Error API: {e}")
        return None


# =========================================================
# Utils UI
# =========================================================
def _safe(v, d: str = "—"):
    return v if v not in (None, "", "null") else d


def _to_csv_list(vals: Any) -> str:
    """Convierte lista de strings en texto para inputs (coma-separated)."""
    if vals is None:
        return ""
    if isinstance(vals, list):
        return ", ".join([str(x).strip() for x in vals if str(x).strip()])
    return str(vals).strip()


def _from_csv_list(txt: str) -> Optional[List[str]]:
    """Convierte 'a,b,c' -> ['a','b','c'] para enviar al backend."""
    if not txt:
        return None
    parts = [p.strip() for p in str(txt).split(",") if p.strip()]
    return parts if parts else None


# =========================================================
# 👥 Render principal (UI ONLY)
# =========================================================
def render_contacto_form(clienteid: int, key_prefix: str = ""):
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
                👥 Contactos del cliente
            </div>
            <div style="font-size:0.9rem; color:#6b7280;">
                Personas de contacto asociadas al cliente.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================
    # Cargar contactos (API)
    # =========================
    contactos: List[Dict[str, Any]] = api_get(
        f"/api/clientes/{clienteid}/contactos"
    )

    # =========================
    # ➕ Nuevo contacto
    # =========================
    with st.expander("➕ Añadir nuevo contacto"):
        _contacto_editor(clienteid, None, key_prefix=kp)

    # =========================
    # Listado
    # =========================
    if not contactos:
        st.info("📭 Este cliente no tiene contactos registrados.")
        return

    st.markdown("---")

    for c in contactos:
        cid = c["cliente_contactoid"]

        nombre = c.get("nombre", "(Sin nombre)")
        cargo = _safe(c.get("cargo"))
        rol = _safe(c.get("rol"))
        emails = ", ".join(c.get("email", []) or []) or "—"
        telefonos = ", ".join(c.get("telefono", []) or []) or "—"
        obs = _safe(c.get("observaciones"))
        es_principal = bool(c.get("es_principal"))

        bg = "#f0f9ff" if es_principal else "#ffffff"
        border = "#38bdf8" if es_principal else "#e5e7eb"

        st.markdown(
            f"""
            <div style="
                background:{bg};
                border:1px solid {border};
                border-left:5px solid {border};
                border-radius:10px;
                padding:12px 14px;
                margin-bottom:10px;">

                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="font-size:1.05rem;font-weight:600;">
                        {nombre}
                        <span style="color:#6b7280;font-size:0.9rem;">
                            — {cargo}
                        </span>
                    </div>
                    {"<span style='padding:3px 8px;background:#dbeafe;color:#1e3a8a;border-radius:999px;font-size:0.75rem;'>⭐ Principal</span>" if es_principal else ""}
                </div>

                <div style="margin-top:6px;font-size:0.9rem;color:#374151;">
                    📧 <b>Email:</b> {emails}<br>
                    📞 <b>Teléfono:</b> {telefonos}<br>
                    🧩 <b>Rol:</b> {rol}<br>
                    📝 <b>Notas:</b> {obs}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # -------------------------
        # BOTONES
        # -------------------------
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Editar", key=f"{kp}edit_contact_{cid}", use_container_width=True):
                st.session_state[f"{kp}edit_contact_{cid}"] = not st.session_state.get(
                    f"{kp}edit_contact_{cid}", False
                )

        with col2:
            if st.button("Eliminar", key=f"{kp}delete_contact_{cid}", use_container_width=True):
                api_delete(f"/api/clientes/{clienteid}/contactos/{cid}")
                st.toast("Contacto eliminado.")
                st.rerun()

        with col3:
            if not es_principal:
                if st.button("Hacer principal", key=f"{kp}main_contact_{cid}", use_container_width=True):
                    api_post(f"/api/clientes/{clienteid}/contactos/{cid}/hacer-principal")
                    st.toast("Contacto marcado como principal.")
                    st.rerun()

        # -------------------------
        # EDITOR
        # -------------------------
        if st.session_state.get(f"{kp}edit_contact_{cid}"):
            with st.expander(f"Editar contacto — {nombre}", expanded=True):
                _contacto_editor(clienteid, c, key_prefix=kp)


# =========================================================
# ✏️ Editor de contacto (alta / edición) — UI ONLY
# =========================================================
def _contacto_editor(clienteid: int, c: Optional[Dict[str, Any]] = None, key_prefix: str = ""):
    is_new = c is None
    cid = (c or {}).get("cliente_contactoid")
    prefix = f"{key_prefix}contact_{cid or 'new'}"

    def field(key, label, default=""):
        k = f"{prefix}_{key}"
        st.session_state.setdefault(k, (c or {}).get(key, default))
        return st.text_input(label, key=k)

    nombre = field("nombre", "Nombre *")
    cargo = field("cargo", "Cargo")
    rol = field("rol", "Rol")

    email = field("email", "Email (separar por comas)", _to_csv_list((c or {}).get("email")))
    telefono = field("telefono", "Teléfono (separar por comas)", _to_csv_list((c or {}).get("telefono")))

    direccion = field("direccion", "Dirección")
    ciudad = field("ciudad", "Ciudad")
    provincia = field("provincia", "Provincia")
    pais = field("pais", "País", "España")

    observaciones = st.text_area(
        "Observaciones",
        value=(c or {}).get("observaciones", ""),
        key=f"{prefix}_obs",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Guardar", key=f"{prefix}_save", use_container_width=True):
            if not nombre.strip():
                st.warning("El nombre es obligatorio.")
                return

            payload = {
                "nombre": nombre.strip(),
                "cargo": cargo.strip() or None,
                "rol": rol.strip() or None,
                "email": _from_csv_list(email),
                "telefono": _from_csv_list(telefono),
                "direccion": direccion.strip() or None,
                "ciudad": ciudad.strip() or None,
                "provincia": provincia.strip() or None,
                "pais": pais.strip() or None,
                "observaciones": observaciones.strip() or None,
            }

            if is_new:
                api_post(f"/api/clientes/{clienteid}/contactos", payload)
                st.toast("Contacto añadido.")
            else:
                api_put(f"/api/clientes/{clienteid}/contactos/{cid}", payload)
                st.toast("Contacto actualizado.")

            st.rerun()

    with col2:
        if not is_new:
            if st.button("Eliminar", key=f"{prefix}_delete", use_container_width=True):
                api_delete(f"/api/clientes/{clienteid}/contactos/{cid}")
                st.toast("Contacto eliminado.")
                st.rerun()
