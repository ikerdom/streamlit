# ======================================================
# 👤 FORMULARIO PRINCIPAL DE CLIENTE — Alta completa
# ======================================================
import streamlit as st
from supabase import create_client
from datetime import date

# ======================================================
# 🔌 CONFIGURACIÓN SUPABASE
# ======================================================
SUPABASE_URL = "https://gqhrbvusvcaytcbnusdx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxaHJidnVzdmNheXRjYm51c2R4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MzM3MDQsImV4cCI6MjA3NTAwOTcwNH0.y3018JLs9A08sSZKHLXeMsITZ3oc4s2NDhNLxWqM9Ag"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render_cliente_form():
    st.title("👤 Nuevo Cliente")
    st.caption("Formulario de alta completo en Supabase · Incluye dirección, contacto, banco y facturación.")

    # ------------------------------
    # Cargar catálogos base
    # ------------------------------
    def get_options(tabla, campo="nombre", value_field=None):
        try:
            data = supabase.table(tabla).select("*").eq("habilitado", True).execute().data
            if not data:
                return {}
            value_field = value_field or f"{tabla}id"
            return {d[campo]: d[value_field] for d in data}
        except Exception:
            return {}

    estados = get_options("cliente_estado")
    categorias = get_options("cliente_categoria")
    formas_pago = get_options("forma_pago")
    grupos = get_options("grupo", campo="nombre", value_field="grupoid")
    trabajadores = get_options("trabajador", campo="nombre", value_field="trabajadorid")

    # 🔹 NUEVO: catálogo de tarifas activas
    try:
        tarifas = (
            supabase.table("tarifa")
            .select("tarifaid, nombre")
            .eq("activa", True)
            .order("nombre")
            .execute()
            .data or []
        )
        tarifas_dict = {t["nombre"]: t["tarifaid"] for t in tarifas}
    except Exception:
        tarifas_dict = {}

    # ======================================================
    # 🧾 INFORMACIÓN GENERAL
    # ======================================================
    with st.expander("🧾 Información general del cliente", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            razon_social = st.text_input("Razón social *")
            identificador = st.text_input("Identificador único *", help="Slug o código único del cliente.")
            estado_nombre = st.selectbox("Estado", list(estados.keys()))
            categoria_nombre = st.selectbox("Categoría", list(categorias.keys()))
            grupo_nombre = st.selectbox("Grupo", ["(Sin grupo)"] + list(grupos.keys()))
        with c2:
            formapago_nombre = st.selectbox("Forma de pago", list(formas_pago.keys()))
            trabajador_nombre = st.selectbox("Trabajador asignado", list(trabajadores.keys()) + ["➕ Añadir nuevo…"])
            observaciones = st.text_area("Observaciones", placeholder="Notas internas o condiciones especiales...")

        # 💰 NUEVO CAMPO: Tarifa asignada
        tarifa_nombre = st.selectbox(
            "💰 Tarifa asignada",
            ["(Sin tarifa)"] + list(tarifas_dict.keys()),
            help="Tarifa de precios base que se aplicará en presupuestos y pedidos."
        )

        # 🔹 Alta rápida de trabajador
        if trabajador_nombre == "➕ Añadir nuevo…":
            with st.expander("➕ Añadir nuevo trabajador", expanded=True):
                nt_col1, nt_col2 = st.columns(2)
                with nt_col1:
                    nt_nombre = st.text_input("Nombre *")
                    nt_apellidos = st.text_input("Apellidos *")
                with nt_col2:
                    nt_email = st.text_input("Email *")
                    nt_tel = st.text_input("Teléfono")

                if st.button("💾 Guardar trabajador", use_container_width=True):
                    if nt_nombre and nt_apellidos and nt_email:
                        res = supabase.table("trabajador").insert({
                            "nombre": nt_nombre,
                            "apellidos": nt_apellidos,
                            "email": nt_email,
                            "telefono": nt_tel,
                        }).execute()
                        if res.data:
                            st.toast("✅ Trabajador creado correctamente. Recarga la página para seleccionarlo.", icon="✅")
                    else:
                        st.warning("⚠️ Completa nombre, apellidos y email para guardar.")
            st.stop()

    # ======================================================
    # 📍 DIRECCIÓN PRINCIPAL (FISCAL)
    # ======================================================
    with st.expander("📍 Dirección principal (Fiscal)", expanded=False):
        d1, d2 = st.columns(2)
        with d1:
            direccion = st.text_input("Dirección *")
            ciudad = st.text_input("Ciudad *")
            provincia = st.text_input("Provincia")
            pais = st.text_input("País", value="España")
        with d2:
            cp = st.text_input("Código postal")
            telefono = st.text_input("Teléfono")
            email = st.text_input("Email de contacto")
            documentacion_impresa = st.selectbox("Documentación impresa", ["valorado", "no_valorado", "factura"])

    # ======================================================
    # 🧾 FACTURACIÓN
    # ======================================================
    with st.expander("🧾 Configuración de facturación", expanded=False):
        resumen_facturacion = st.checkbox("Resumen de facturas", value=False)
        recargo_eq = st.checkbox("Recargo de equivalencia", value=False)
        dias_venc = st.number_input("Días vencimiento", 0, 365, 30)
        canal_contables = get_options("canal_contable", campo="nombre", value_field="canalcontableid")
        canal_nombre = st.selectbox("Canal contable", list(canal_contables.keys()))

    # ======================================================
    # 👤 CONTACTO PRINCIPAL
    # ======================================================
    with st.expander("👤 Contacto principal", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            contacto_nombre = st.text_input("Nombre de contacto")
            contacto_email = st.text_input("Email")
        with c2:
            contacto_tel = st.text_input("Teléfono")
            contacto_rol = st.text_input("Rol / Cargo")

    # ======================================================
    # 🏦 CUENTA BANCARIA
    # ======================================================
    with st.expander("🏦 Datos bancarios", expanded=False):
        iban = st.text_input("IBAN")
        banco_nombre = st.text_input("Nombre del banco")
        fecha_baja = st.date_input("Fecha de baja (opcional)", value=None)

    # ======================================================
    # 💾 GUARDAR CLIENTE COMPLETO
    # ======================================================
    if st.button("💾 Guardar cliente completo", use_container_width=True):
        if not razon_social or not identificador:
            st.warning("⚠️ Los campos obligatorios son requeridos.")
            return

        try:
            with st.spinner("Guardando cliente en Supabase..."):
                estadoid = estados[estado_nombre]
                categoriaid = categorias[categoria_nombre]
                formapagoid = formas_pago[formapago_nombre]
                grupoid = grupos.get(grupo_nombre) if grupo_nombre != "(Sin grupo)" else None
                trabajadorid = trabajadores.get(trabajador_nombre)
                tarifaid = tarifas_dict.get(tarifa_nombre) if tarifa_nombre != "(Sin tarifa)" else None

                cliente_insert = {
                    "razon_social": razon_social,
                    "identificador": identificador,
                    "estadoid": estadoid,
                    "categoriaid": categoriaid,
                    "grupoid": grupoid,
                    "formapagoid": formapagoid,
                    "trabajadorid": trabajadorid,
                    "observaciones": observaciones,
                    "tarifaid": tarifaid,  # 💰 Nuevo campo
                }
                res_cliente = supabase.table("cliente").insert(cliente_insert).execute()
                clienteid = res_cliente.data[0]["clienteid"]

                # Dirección
                dir_data = {
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
                }
                supabase.table("cliente_direccion").insert(dir_data).execute()

                # Contacto
                if contacto_nombre or contacto_email:
                    supabase.table("cliente_contacto").insert({
                        "clienteid": clienteid,
                        "nombre": contacto_nombre,
                        "email": contacto_email,
                        "telefono": contacto_tel,
                        "rol": contacto_rol,
                    }).execute()

                # Banco
                if iban:
                    supabase.table("cliente_banco").insert({
                        "clienteid": clienteid,
                        "iban": iban,
                        "nombre_banco": banco_nombre,
                        "fecha_baja": str(fecha_baja) if fecha_baja else None,
                    }).execute()

                # Facturación
                supabase.table("cliente_facturacion").insert({
                    "clienteid": clienteid,
                    "resumen_facturacion": resumen_facturacion,
                    "recargo_equivalencia": recargo_eq,
                    "dias_vencimiento": dias_venc,
                    "canalcontableid": canal_contables[canal_nombre],
                }).execute()

                st.toast(f"✅ Cliente '{razon_social}' creado correctamente.", icon="✅")
                st.session_state["cliente_actual"] = clienteid

        except Exception as e:
            st.error(f"❌ Error durante la inserción: {e}")
