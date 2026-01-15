import os
from typing import Dict, Any, Optional, List

import requests
import streamlit as st
from streamlit.components.v1 import html as st_html


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
def _safe(v, d: str = "-"):
    return v if v not in (None, "", "null") else d


# =========================================================
# 🧱 Card HTML (UI ONLY)
# =========================================================
def _render_dir_card(tipo, direccion, cp, ciudad, provincia):
    tipo = (tipo or "envio").lower()
    titulo = f"📦 {tipo.capitalize()} {'⭐' if tipo == 'fiscal' else ''}"

    st_html(
        f"""
        <div style="border:1px solid #d1d5db;background:#ffffff;
                    border-radius:8px;padding:12px 14px;margin-bottom:6px;">
            <div style="font-size:1rem;font-weight:600;color:#065f46;">
                {titulo}
            </div>
            <div style="font-size:0.88rem;color:#475569;margin-top:4px;">
                {direccion} — {cp} {ciudad} ({provincia})
            </div>
        </div>
        """,
        height=90,
    )


# =========================================================
# 🏠 FORMULARIO PRINCIPAL (UI ONLY)
# =========================================================
def render_direccion_form(clienteid: int, key_prefix: str = ""):
    clienteid = int(clienteid)
    kp = key_prefix or ""

    st.markdown("### 🏠 Direcciones del cliente")
    st.caption("Direcciones fiscales y de envío. Solo puede haber una fiscal.")

    # =====================================================
    # Cargar direcciones (API)
    # =====================================================
    direcciones: List[Dict[str, Any]] = api_get(
        f"/api/clientes/{clienteid}/direcciones"
    )

    # =====================================================
    # Buscador
    # =====================================================
    search = st.text_input("Buscar dirección", key=f"{kp}buscar_dir_{clienteid}")
    if search:
        s = search.lower()
        direcciones = [
            d
            for d in direcciones
            if s
            in (
                (d.get("direccion", "") +
                 d.get("ciudad", "") +
                 d.get("cp", "") +
                 d.get("provincia", "")).lower()
            )
        ]

    # =====================================================
    # Filtro tipo
    # =====================================================
    filtro = st.selectbox("Tipo", ["Todos", "Fiscales", "Envio"], key=f"{kp}filtro_tipo_{clienteid}")
    if filtro == "Fiscales":
        direcciones = [d for d in direcciones if d.get("tipo") == "fiscal"]
    elif filtro == "Envío":
        direcciones = [d for d in direcciones if d.get("tipo") == "envio"]

    # =====================================================
    # Paginación
    # =====================================================
    PAGE_SIZE = 10
    page_key = f"page_dir_{clienteid}"
    st.session_state.setdefault(page_key, 0)
    page = st.session_state[page_key]

    max_page = max((len(direcciones) - 1) // PAGE_SIZE, 0)
    page = min(page, max_page)
    st.session_state[page_key] = page

    page_dirs = direcciones[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    # =====================================================
    # Cards
    # =====================================================
    for d in page_dirs:
        dir_id = d["cliente_direccionid"]
        edit_key = f"{kp}edit_{dir_id}"
        confirm_key = f"{kp}confirm_{dir_id}"

        st.session_state.setdefault(edit_key, False)
        st.session_state.setdefault(confirm_key, False)

        _render_dir_card(
            d.get("tipo"),
            d.get("direccion", "-"),
            d.get("cp", "-"),
            d.get("ciudad", "-"),
            d.get("provincia", "-"),
        )

        c1, c2, c3 = st.columns([1, 1, 2])

        with c1:
            if st.button("Editar", key=f"{kp}btn_edit_{dir_id}"):
                st.session_state[edit_key] = not st.session_state[edit_key]

        with c2:
            if st.button("Borrar", key=f"{kp}btn_del_{dir_id}"):
                api_delete(
                    f"/api/clientes/{clienteid}/direcciones/{dir_id}"
                )
                st.toast("Dirección eliminada")
                st.rerun()

        with c3:
            if d.get("tipo") != "fiscal":
                if st.button("Hacer fiscal", key=f"{kp}btn_fiscal_{dir_id}"):
                    st.session_state[confirm_key] = True

        # Confirmar fiscal
        if st.session_state[confirm_key]:
            st.warning("¿Marcar esta dirección como fiscal?")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("Confirmar", key=f"{kp}ok_{dir_id}"):
                    api_post(
                        f"/api/clientes/{clienteid}/direcciones/{dir_id}/hacer-fiscal"
                    )
                    st.toast("Dirección fiscal actualizada")
                    st.rerun()
            with cc2:
                if st.button("Cancelar", key=f"{kp}cancel_{dir_id}"):
                    st.session_state[confirm_key] = False

        # Form editar
        if st.session_state[edit_key]:
            with st.expander("Editar dirección", expanded=True):
                direccion = st.text_input(
                    "Dirección", value=d.get("direccion", ""), key=f"{kp}dir_{dir_id}"
                )
                ciudad = st.text_input(
                    "Ciudad", value=d.get("ciudad", ""), key=f"{kp}ciu_{dir_id}"
                )
                cp = st.text_input(
                    "CP", value=d.get("cp", ""), key=f"{kp}cp_{dir_id}"
                )
                provincia = st.text_input(
                    "Provincia", value=d.get("provincia", ""), key=f"{kp}prov_{dir_id}"
                )
                pais = st.text_input(
                    "País", value=d.get("pais", "España"), key=f"{kp}pais_{dir_id}"
                )
                email = st.text_input(
                    "Email", value=d.get("email", ""), key=f"{kp}email_{dir_id}"
                )

                if st.button("Guardar cambios", key=f"{kp}save_{dir_id}"):
                    payload = {
                        "direccion": direccion.strip(),
                        "ciudad": ciudad.strip(),
                        "cp": cp.strip(),
                        "provincia": provincia.strip(),
                        "pais": pais.strip(),
                        "email": email.strip(),
                        "tipo": d.get("tipo"),
                    }
                    api_put(
                        f"/api/clientes/{clienteid}/direcciones/{dir_id}",
                        payload,
                    )
                    st.toast("Dirección guardada")
                    st.rerun()

    # =====================================================
    # Nueva dirección
    # =====================================================
    st.markdown("---")
    with st.expander("➕ Añadir nueva dirección"):
        fiscal_exist = any(d.get("tipo") == "fiscal" for d in direcciones)

        direccion = st.text_input("Dirección", key=f"{kp}new_dir_{clienteid}")
        ciudad = st.text_input("Ciudad", key=f"{kp}new_ciu_{clienteid}")
        cp = st.text_input("CP", key=f"{kp}new_cp_{clienteid}")
        provincia = st.text_input("Provincia", key=f"{kp}new_prov_{clienteid}")
        pais = st.text_input("País", "España", key=f"{kp}new_pais_{clienteid}")
        email = st.text_input("Email", key=f"{kp}new_email_{clienteid}")

        tipo = "envio"
        if not fiscal_exist:
            tipo = st.selectbox(
                "Tipo", ["fiscal", "envio"], key=f"{kp}new_tipo_{clienteid}"
            )

        if st.button("Guardar nueva dirección", key=f"{kp}save_new_{clienteid}"):
            payload = {
                "direccion": direccion.strip(),
                "ciudad": ciudad.strip(),
                "cp": cp.strip(),
                "provincia": provincia.strip(),
                "pais": pais.strip(),
                "email": email.strip(),
                "tipo": tipo,
            }
            api_post(
                f"/api/clientes/{clienteid}/direcciones",
                payload,
            )
            st.toast("Dirección creada")
            st.rerun()
