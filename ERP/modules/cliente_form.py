# ======================================================
# 👤 FORMULARIO PRINCIPAL DE CLIENTE / CLIENTE POTENCIAL
# ======================================================
import streamlit as st
from datetime import date


# ======================================================
# 🔍 Buscar por Código Postal (con soporte ceros izquierda)
# ======================================================
def buscar_por_cp(supabase, cp: str):
    cp = (cp or "").strip()
    if not cp:
        return []

    resultados = []

    # Exacto
    try:
        exact = (
            supabase.table("postal_localidad")
            .select("*")
            .eq("cp", cp)
            .order("localidad")
            .execute()
            .data or []
        )
        resultados.extend(exact)
    except Exception:
        pass

    # Variante sin ceros (09003 → 9003)
    if cp.startswith("0"):
        try:
            alt_cp = cp.lstrip("0")
            if alt_cp:
                alt = (
                    supabase.table("postal_localidad")
                    .select("*")
                    .eq("cp", alt_cp)
                    .order("localidad")
                    .execute()
                    .data or []
                )
                resultados.extend(alt)
        except Exception:
            pass

    # Quitar duplicados
    finales = {r["postallocid"]: r for r in resultados if r.get("postallocid")}
    return list(finales.values())


# ======================================================
# 👤 RENDER FORM CLIENTE / POTENCIAL
# ======================================================
def render_cliente_form(supabase, modo: str = "cliente"):
    is_potencial = modo == "potencial"

    st.title("🌱 Nuevo cliente potencial" if is_potencial else "👤 Nuevo cliente")
    st.caption(
        "Alta rápida de cliente potencial (perfil incompleto permitido)."
        if is_potencial
        else "Alta completa del cliente en el sistema."
    )

    # ==================================================
    # 📦 Cargar catálogos base
    # ==================================================
    def get_options(tabla, campo="nombre", value_field=None):
        try:
            rows = supabase.table(tabla).select("*").execute().data or []
            value_field = value_field or f"{tabla}id"
            return {r[campo]: r[value_field] for r in rows if campo in r}
        except Exception:
            return {}

    estados = get_options("cliente_estado")
    categorias = get_options("cliente_categoria")
    formas_pago = get_options("forma_pago")
    grupos = get_options("grupo", campo="nombre", value_field="grupoid")
    trabajadores = get_options("trabajador", campo="nombre", value_field="trabajadorid")

    try:
        tarifas = (
            supabase.table("tarifa")
            .select("tarifaid,nombre")
            .eq("activa", True)
            .order("nombre")
            .execute()
            .data or []
        )
        tarifas_dict = {t["nombre"]: t["tarifaid"] for t in tarifas}
    except Exception:
        tarifas_dict = {}

    # ==================================================
    # 🧾 INFORMACIÓN GENERAL
    # ==================================================
    with st.expander("🧾 Información general", expanded=True):
        c1, c2 = st.columns(2)

        with c1:
            razon_social = st.text_input("Razón social *")
            identificador = st.text_input("Identificador único *")
            estado_nombre = st.selectbox("Estado", list(estados.keys()))
            categoria_nombre = st.selectbox("Categoría", list(categorias.keys()))
            grupo_nombre = st.selectbox("Grupo", ["(Sin grupo)"] + list(grupos.keys()))

        with c2:
            formapago_nombre = st.selectbox(
                "Forma de pago",
                list(formas_pago.keys()),
                disabled=is_potencial,
            )
            trabajador_nombre = st.selectbox(
                "Trabajador asignado",
                ["(Sin asignar)"] + list(trabajadores.keys()),
            )
            observaciones = st.text_area("Observaciones internas")

        tarifa_nombre = st.selectbox(
            "💰 Tarifa asignada",
            ["(Sin tarifa)"] + list(tarifas_dict.keys()),
        )

    # ==================================================
    # 📍 DIRECCIÓN FISCAL
    # ==================================================
    with st.expander("📍 Dirección fiscal", expanded=False):
        d1, d2 = st.columns(2)

        with d1:
            direccion = st.text_input("Dirección")
            ciudad = st.text_input("Ciudad")
            provincia = st.text_input("Provincia")
            pais = st.text_input("País", value="España")

        with d2:
            cp = st.text_input("Código postal")

            if st.button("🔍 Rellenar desde CP"):
                filas = buscar_por_cp(supabase, cp)
                if not filas:
                    st.warning("⚠️ No se encontró ese código postal.")
                elif len(filas) == 1:
                    r = filas[0]
                    ciudad = r.get("localidad", ciudad)
                    provincia = r.get("provincia_nombre_raw", provincia)
                    st.success(f"📍 {ciudad} ({provincia})")
                else:
                    opciones = [
                        f"{r['localidad']} ({r['provincia_nombre_raw']})"
                        for r in filas
                    ]
                    sel = st.selectbox("Selecciona localidad", opciones)
                    r = filas[opciones.index(sel)]
                    ciudad = r["localidad"]
                    provincia = r["provincia_nombre_raw"]

            telefono = st.text_input("Teléfono")
            email = st.text_input("Email")
            documentacion_impresa = st.selectbox(
                "Documentación impresa",
                ["valorado", "no_valorado", "factura"],
            )

    # ==================================================
    # 👤 CONTACTO PRINCIPAL
    # ==================================================
    with st.expander("👤 Contacto principal", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            contacto_nombre = st.text_input("Nombre contacto")
            contacto_email = st.text_input("Email contacto")
        with c2:
            contacto_tel = st.text_input("Teléfono contacto")
            contacto_rol = st.text_input("Rol / Cargo")

    # ==================================================
    # 🏦 DATOS BANCARIOS (solo cliente)
    # ==================================================
    if not is_potencial:
        with st.expander("🏦 Datos bancarios", expanded=False):
            iban = st.text_input("IBAN")
            banco_nombre = st.text_input("Banco")
            fecha_baja = st.date_input("Fecha de baja", value=None)
    else:
        iban = banco_nombre = fecha_baja = None

    # ==================================================
    # 💾 GUARDAR CLIENTE / POTENCIAL
    # ==================================================
    if st.button("💾 Guardar", use_container_width=True):

        if not razon_social or not identificador:
            st.warning("⚠️ Razón social e identificador son obligatorios.")
            return

        if not is_potencial and not (direccion and ciudad and cp):
            st.warning("⚠️ Dirección fiscal completa obligatoria para clientes.")
            return

        try:
            with st.spinner("Guardando..."):

                cliente_data = {
                    "razon_social": razon_social,
                    "identificador": identificador,
                    "estadoid": estados.get(estado_nombre),
                    "categoriaid": categorias.get(categoria_nombre),
                    "grupoid": grupos.get(grupo_nombre),
                    "formapagoid": None if is_potencial else formas_pago.get(formapago_nombre),
                    "trabajadorid": trabajadores.get(trabajador_nombre),
                    "observaciones": observaciones,
                    "tarifaid": tarifas_dict.get(tarifa_nombre),
                    "tipo_cliente": "potencial" if is_potencial else "cliente",
                    "perfil_completo": False,  # siempre se recalcula luego
                }

                res = supabase.table("cliente").insert(cliente_data).execute()
                clienteid = res.data[0]["clienteid"]

                # Dirección fiscal (si hay algo informado)
                if direccion or ciudad or cp:
                    supabase.table("cliente_direccion").insert({
                        "clienteid": clienteid,
                        "tipo": "fiscal",
                        "direccion": direccion,
                        "ciudad": ciudad,
                        "provincia": provincia,
                        "pais": pais,
                        "cp": cp,
                        "telefono": telefono,
                        "email": email,
                        "documentacion_impresa": documentacion_impresa,
                    }).execute()

                # Contacto principal
                if contacto_nombre or contacto_email:
                    supabase.table("cliente_contacto").insert({
                        "clienteid": clienteid,
                        "nombre": contacto_nombre,
                        "email": contacto_email,
                        "telefono": contacto_tel,
                        "rol": contacto_rol,
                        "es_principal": True,
                    }).execute()

                # Banco (solo cliente)
                if iban:
                    supabase.table("cliente_banco").insert({
                        "clienteid": clienteid,
                        "iban": iban,
                        "nombre_banco": banco_nombre,
                        "fecha_baja": str(fecha_baja) if fecha_baja else None,
                    }).execute()

                if is_potencial:
                    st.toast(f"🌱 Cliente potencial '{razon_social}' creado.", icon="🌱")
                else:
                    st.toast(f"✅ Cliente '{razon_social}' creado correctamente.", icon="✅")

                st.session_state["cliente_actual"] = clienteid
                st.rerun()

        except Exception as e:
            st.error(f"❌ Error creando cliente: {e}")
