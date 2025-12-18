# =========================================================
# 🗒️ FORM · Observaciones internas del cliente (ERP style)
# =========================================================
import streamlit as st
from datetime import datetime


# ---------------------------------------------------------
# 🔍 Helper: comprobar si existe una tabla
# ---------------------------------------------------------
def _has_table(supabase, table_name: str) -> bool:
    try:
        supabase.table(table_name).select("*").limit(1).execute()
        return True
    except Exception:
        return False


# ---------------------------------------------------------
# 🗒️ Render principal
# ---------------------------------------------------------
def render_observaciones_form(supabase, clienteid: int):

    # =========================
    # CABECERA (misma línea visual que Direcciones)
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

    use_obs_table = _has_table(supabase, "cliente_observacion")

    # =========================
    # 📋 CARGA DE OBSERVACIONES
    # =========================
    try:
        if use_obs_table:
            notas = (
                supabase.table("cliente_observacion")
                .select("cliente_observacionid, comentario, tipo, fecha, usuario")
                .eq("clienteid", int(clienteid))
                .order("fecha", desc=True)
                .execute()
                .data
                or []
            )
        else:
            rows = (
                supabase.table("cliente_parametro")
                .select("clave, valor")
                .eq("clienteid", int(clienteid))
                .execute()
                .data
                or []
            )

            notas = [
                {
                    "cliente_observacionid": i,
                    "tipo": r["clave"].replace("observacion_", "").capitalize(),
                    "comentario": r["valor"],
                    "fecha": "-",
                    "usuario": "-",
                }
                for i, r in enumerate(rows)
                if str(r.get("clave", "")).startswith("observacion_")
            ]

    except Exception as e:
        st.error(f"❌ Error cargando observaciones: {e}")
        return

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
            fecha = n.get("fecha") or "-"

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
            )

        with col2:
            usuario = st.session_state.get("user_nombre", "Desconocido")
            st.text_input("Usuario", value=usuario, disabled=True)

        comentario = st.text_area(
            "Comentario",
            placeholder="Ejemplo: Cliente solicita retrasar entrega una semana…",
            height=100,
        )

        if st.button("💾 Guardar observación", use_container_width=True):
            if not comentario.strip():
                st.warning("⚠️ Debes escribir un comentario.")
                return

            try:
                now = datetime.now().isoformat()

                if use_obs_table:
                    supabase.table("cliente_observacion").insert({
                        "clienteid": int(clienteid),
                        "tipo": tipo,
                        "comentario": comentario.strip(),
                        "usuario": usuario,
                        "fecha": now,
                    }).execute()
                else:
                    supabase.table("cliente_parametro").upsert(
                        {
                            "clienteid": int(clienteid),
                            "clave": f"observacion_{tipo.lower()}",
                            "valor": comentario.strip(),
                        },
                        on_conflict="clienteid,clave",
                    ).execute()

                st.toast("✅ Observación guardada correctamente.")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error guardando observación: {e}")
