import streamlit as st
import re
import unicodedata

# ==========================================================
# 🔧 Utilidades
# ==========================================================
def normalizar_texto(texto: str) -> str:
    """Quita acentos y caracteres especiales."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def generar_identificador(razon_social: str, categoria: str | None) -> str:
    """Genera un slug único tipo LIB-libreria-san-marcos."""
    if not razon_social:
        return None
    slug = normalizar_texto(razon_social.lower())
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    prefijo = categoria[:3].upper() if categoria else "GEN"
    return f"{prefijo}-{slug}"


# ==========================================================
# 🧩 Alta básica de cliente (solo trabajadores)
# ==========================================================
def render_cliente_nuevo_basico(supabase):
    st.header("🧩 Alta rápida de cliente (Pre-alta)")
    st.caption("Permite registrar un nuevo cliente potencial con los datos mínimos. Luego podrá completar su perfil para activarse.")

    # -------------------------------------------------------
    # 🧩 Control de permisos
    # -------------------------------------------------------
    tipo_usuario = st.session_state.get("tipo_usuario")
    if tipo_usuario == "cliente":
        st.warning("⚠️ Esta sección es exclusiva para trabajadores.")
        st.info("Inicia sesión como trabajador para poder registrar nuevos clientes.")
        st.stop()

    # -------------------------------------------------------
    # 📝 CAMPOS DEL FORMULARIO
    # -------------------------------------------------------
    razon = st.text_input("🏢 Razón social *", placeholder="Ej: Librería San Marcos")
    email = st.text_input("📧 Correo electrónico *", placeholder="Ej: contacto@libreriasanmarcos.com")
    telefono = st.text_input("📞 Teléfono (opcional)", value="+34 ", max_chars=20)
    pais = st.text_input("🌍 País *", value="España")
    categoria = st.selectbox("🏷️ Categoría", ["Librería", "Distribuidor", "Centro educativo", "Particular"])
    observaciones = st.text_area("🗒️ Observaciones", placeholder="Notas internas o comentarios...")

    # -------------------------------------------------------
    # 💾 BOTÓN DE CREACIÓN
    # -------------------------------------------------------
    if st.button("💾 Crear cliente", type="primary"):
        if not razon.strip() or not email.strip():
            st.error("❗ Los campos 'Razón social' y 'Correo electrónico' son obligatorios.")
            return

        try:
            # 1️⃣ Verificar duplicados por nombre
            existe = (
                supabase.table("cliente")
                .select("clienteid, razon_social")
                .ilike("razon_social", razon.strip())
                .limit(1)
                .execute()
            )
            if existe.data:
                st.warning(f"⚠️ Ya existe un cliente con el nombre **{razon.strip()}**. Usa otro o edita el existente.")
                return

            # 2️⃣ Verificar duplicados por email
            existe_mail = (
                supabase.table("cliente_contacto")
                .select("cliente_contactoid")
                .eq("email", email.strip())
                .limit(1)
                .execute()
            )
            if existe_mail.data:
                st.warning(f"⚠️ El correo **{email.strip()}** ya está asociado a otro cliente.")
                return

            # 3️⃣ Obtener estadoid de 'Pre-alta'
            estado_pre = supabase.table("cliente_estado").select("estadoid").eq("nombre", "Pre-alta").limit(1).execute()
            estadoid_pre = estado_pre.data[0]["estadoid"] if estado_pre.data else 1

            # 4️⃣ Generar identificador
            identificador = generar_identificador(razon, categoria)
            st.info(f"Identificador generado automáticamente: `{identificador}`")

            # 5️⃣ Insertar cliente principal
            data_cliente = {
                "razon_social": razon.strip(),
                "identificador": identificador,
                "categoriaid": None,
                "cuenta_comision": 0,
                "observaciones": observaciones.strip(),
                "estadoid": estadoid_pre,
                "perfil_completo": False,
            }
            result = supabase.table("cliente").insert(data_cliente).execute()
            if not result.data:
                st.error("❌ No se pudo crear el cliente.")
                return

            clienteid = result.data[0]["clienteid"]

            # 6️⃣ Insertar contacto principal asociado
            data_contacto = {
                "clienteid": clienteid,
                "nombre": razon.strip(),
                "email": email.strip(),
                "telefono": telefono.strip() if telefono else None,
                "rol": "Principal",
                "pais": pais.strip(),
                "es_principal": True,
            }
            supabase.table("cliente_contacto").insert(data_contacto).execute()

            # 7️⃣ Guardar en sesión (como cliente recién creado)
            st.session_state["cliente_actual"] = clienteid
            st.session_state["user_email"] = email.strip()
            st.session_state["user_nombre"] = razon.strip()
            st.session_state["tipo_usuario"] = "cliente"

            # 8️⃣ Mensaje final
            st.success(f"✅ Cliente '{razon}' creado correctamente con ID {clienteid}.")
            st.info("Este cliente está en estado *Pre-alta*. Completa su perfil para activarlo.")

        except Exception as e:
            st.error(f"❌ Error al crear cliente: {e}")

    # -------------------------------------------------------
    # 👣 PIE DE PÁGINA
    # -------------------------------------------------------
    st.markdown("---")
    st.caption("© 2025 EnteNova Gnosis · Orbe · Módulo de gestión de clientes")
