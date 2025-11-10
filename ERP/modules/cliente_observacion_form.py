# =========================================================
# 🗒️ FORM · Observaciones internas del cliente (versión pro)
# =========================================================
import streamlit as st
from datetime import datetime

# ---------------------------------------------------------
# 🔍 Helper para detectar si existe la tabla cliente_observacion
# ---------------------------------------------------------
def _has_table(supabase, table_name: str) -> bool:
    try:
        supabase.table(table_name).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def render_observaciones_form(supabase, clienteid: int):
    """Visualización y gestión moderna de observaciones internas."""
    st.markdown("### 🗒️ Observaciones internas")
    st.caption("Notas privadas de seguimiento, incidencias o información relevante del cliente.")

    use_obs_table = _has_table(supabase, "cliente_observacion")

    # -------------------------------------------------
    # 📋 Cargar observaciones
    # -------------------------------------------------
    try:
        if use_obs_table:
            notas = (
                supabase.table("cliente_observacion")
                .select("cliente_observacionid, comentario, tipo, fecha, usuario")
                .eq("clienteid", clienteid)
                .order("fecha", desc=True)
                .execute()
                .data or []
            )
        else:
            rows = (
                supabase.table("cliente_parametro")
                .select("clave, valor")
                .eq("clienteid", clienteid)
                .execute()
                .data or []
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
                if str(r["clave"]).startswith("observacion_")
            ]
    except Exception as e:
        st.error(f"❌ Error cargando observaciones: {e}")
        return

    # -------------------------------------------------
    # 🎨 Mostrar notas tipo sticky
    # -------------------------------------------------
    if notas:
        color_map = {
            "General": "#fef9c3",
            "Comercial": "#bfdbfe",
            "Administración": "#fde68a",
            "Otro": "#e9d5ff",
        }
        for n in notas:
            tipo = n.get("tipo", "General")
            color = color_map.get(tipo, "#f3f4f6")
            usuario = n.get("usuario", "Desconocido")
            fecha = n.get("fecha", "-")
            comentario = n.get("comentario", "")

            st.markdown(
                f"""
                <div style="background:{color};
                            padding:12px 16px;
                            border-radius:10px;
                            margin-bottom:10px;
                            box-shadow:0 2px 4px rgba(0,0,0,0.05);
                            border-left:6px solid rgba(0,0,0,0.2);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <b style="font-size:1rem;">🗂️ {tipo}</b>
                        <span style="color:#374151;font-size:0.85rem;">{fecha}</span>
                    </div>
                    <p style="margin:6px 0 4px 0;color:#111827;">{comentario}</p>
                    <div style="text-align:right;color:#4b5563;font-size:0.8rem;">✏️ {usuario}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("📭 No hay observaciones registradas aún.")

    # -------------------------------------------------
    # ➕ Añadir nueva observación (expander)
    # -------------------------------------------------
    with st.expander("➕ Añadir nueva observación", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox(
                "Tipo de nota",
                ["General", "Comercial", "Administración", "Otro"],
                index=0,
            )
        with col2:
            usuario = st.session_state.get("user_nombre", "Desconocido")

        comentario = st.text_area(
            "✏️ Escribe tu comentario",
            placeholder="Ejemplo: Cliente pidió aplazar entrega una semana…",
            height=100,
        )

        if st.button("💾 Guardar observación", use_container_width=True):
            if not comentario.strip():
                st.warning("⚠️ Debes escribir un comentario antes de guardar.")
                return
            try:
                now = datetime.now().isoformat()
                if use_obs_table:
                    supabase.table("cliente_observacion").insert({
                        "clienteid": clienteid,
                        "tipo": tipo,
                        "comentario": comentario.strip(),
                        "usuario": usuario,
                        "fecha": now,
                    }).execute()
                else:
                    supabase.table("cliente_parametro").upsert({
                        "clienteid": clienteid,
                        "clave": f"observacion_{tipo.lower()}",
                        "valor": comentario.strip(),
                    }, on_conflict="clienteid,clave").execute()

                st.toast("✅ Observación guardada correctamente.", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error guardando observación: {e}")
