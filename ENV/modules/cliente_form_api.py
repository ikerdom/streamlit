import os
import requests
import streamlit as st


def _api_base() -> str:
    try:
        return st.secrets["ORBE_API_URL"]  # type: ignore[attr-defined]
    except Exception:
        return (
            os.getenv("ORBE_API_URL")
            or st.session_state.get("ORBE_API_URL")
            or "http://127.0.0.1:8000"
        )


def _api_get(path: str, params=None):
    r = requests.get(f"{_api_base()}{path}", params=params, timeout=25)
    r.raise_for_status()
    return r.json()


def _api_post(path: str, json=None):
    r = requests.post(f"{_api_base()}{path}", json=json, timeout=40)
    r.raise_for_status()
    return r.json()


def render_cliente_form(modo: str = "cliente"):
    """Formulario de alta de cliente/potencial."""
    is_potencial = modo == "potencial"

    st.title("Nuevo cliente potencial" if is_potencial else "Nuevo cliente")
    st.caption(
        "Alta rápida de cliente potencial (perfil incompleto permitido)."
        if is_potencial
        else "Alta completa del cliente en el sistema."
    )

    # Catálogos
    try:
        cats = _api_get("/api/clientes/catalogos")
    except Exception as e:
        st.error(f"No se pudieron cargar catálogos desde API: {e}")
        return

    def to_map(items):
        return {i["label"]: i["id"] for i in (items or [])}

    estados = to_map(cats.get("estados"))
    categorias = to_map(cats.get("categorias"))
    formas_pago = to_map(cats.get("formas_pago"))
    grupos = to_map(cats.get("grupos"))
    trabajadores = to_map(cats.get("trabajadores"))
    tarifas = to_map(cats.get("tarifas"))

    # Información general
    with st.expander("Información general", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            razon_social = st.text_input("Razón social *", key=f"{modo}_razon")
            identificador = st.text_input("Identificador único *", key=f"{modo}_ident")
            estado_nombre = st.selectbox("Estado", list(estados.keys()) or ["-"], key=f"{modo}_estado")
            categoria_nombre = st.selectbox("Categoría", list(categorias.keys()) or ["-"], key=f"{modo}_cat")
            grupo_nombre = st.selectbox("Grupo", ["(Sin grupo)"] + list(grupos.keys()), key=f"{modo}_grupo")
        with c2:
            formapago_nombre = st.selectbox(
                "Forma de pago",
                list(formas_pago.keys()) or ["-"],
                disabled=is_potencial,
                key=f"{modo}_fp",
            )
            trabajador_nombre = st.selectbox(
                "Trabajador asignado",
                ["(Sin asignar)"] + list(trabajadores.keys()),
                key=f"{modo}_trab",
            )
            observaciones = st.text_area("Observaciones internas", key=f"{modo}_obs")
        tarifa_nombre = st.selectbox(
            "Tarifa asignada",
            ["(Sin tarifa)"] + list(tarifas.keys()),
            key=f"{modo}_tarifa",
        )

    # Dirección fiscal
    with st.expander("Dirección fiscal", expanded=False):
        d1, d2 = st.columns(2)
        with d1:
            direccion = st.text_input("Dirección", key=f"{modo}_dir")
            ciudad = st.text_input("Ciudad", key=f"{modo}_ciudad")
            provincia = st.text_input("Provincia", key=f"{modo}_prov")
            pais = st.text_input("País", value="España", key=f"{modo}_pais")
        with d2:
            cp = st.text_input("Código postal", key=f"{modo}_cp")
            if st.button("Rellenar desde CP", key=f"{modo}_btn_cp"):
                try:
                    filas = _api_get("/api/postal/buscar", params={"cp": cp})
                except Exception as e:
                    st.error(f"Error buscando CP: {e}")
                    filas = []
                if not filas:
                    st.warning("No se encontró ese código postal.")
                elif len(filas) == 1:
                    r = filas[0]
                    st.session_state[f"{modo}_ciudad"] = r.get("localidad") or ciudad
                    st.session_state[f"{modo}_prov"] = r.get("provincia_nombre_raw") or provincia
                    st.success(f"{st.session_state[f'{modo}_ciudad']} ({st.session_state[f'{modo}_prov']})")
                    st.rerun()
                else:
                    opciones = [f"{r.get('localidad')} ({r.get('provincia_nombre_raw')})" for r in filas]
                    sel = st.selectbox("Selecciona localidad", opciones, key=f"{modo}_cp_sel")
                    idx = opciones.index(sel)
                    r = filas[idx]
                    st.session_state[f"{modo}_ciudad"] = r.get("localidad") or ciudad
                    st.session_state[f"{modo}_prov"] = r.get("provincia_nombre_raw") or provincia
                    st.rerun()
            telefono = st.text_input("Teléfono", key=f"{modo}_tel")
            email = st.text_input("Email", key=f"{modo}_email")
            documentacion_impresa = st.selectbox(
                "Documentación impresa",
                ["valorado", "no_valorado", "factura"],
                key=f"{modo}_docimp",
            )

    # Contacto principal
    with st.expander("Contacto principal", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            contacto_nombre = st.text_input("Nombre contacto", key=f"{modo}_c_nom")
            contacto_email = st.text_input("Email contacto", key=f"{modo}_c_mail")
        with c2:
            contacto_tel = st.text_input("Teléfono contacto", key=f"{modo}_c_tel")
            contacto_rol = st.text_input("Rol / Cargo", key=f"{modo}_c_rol")

    # Banco
    if not is_potencial:
        with st.expander("Datos bancarios", expanded=False):
            iban = st.text_input("IBAN", key=f"{modo}_iban")
            banco_nombre = st.text_input("Banco", key=f"{modo}_banco")
            fecha_baja = st.date_input("Fecha de baja", value=None, key=f"{modo}_fbaja")
    else:
        iban = banco_nombre = fecha_baja = None

    # Guardar / salir
    colg, colx = st.columns([3, 1])
    guardar = colg.button("Guardar", use_container_width=True, key=f"{modo}_guardar")
    cancelar = colx.button("Salir", use_container_width=True, key=f"{modo}_cancelar")

    if cancelar:
        st.session_state["cli_show_form"] = None
        st.rerun()

    if guardar:
        if not razon_social or not identificador:
            st.warning("Razón social e identificador son obligatorios.")
            return
        if not is_potencial and not (direccion and ciudad and cp):
            st.warning("Dirección fiscal completa obligatoria para clientes.")
            return

        body = {
            "tipo": "potencial" if is_potencial else "cliente",
            "razon_social": razon_social,
            "identificador": identificador,
            "estadoid": estados.get(estado_nombre),
            "categoriaid": categorias.get(categoria_nombre),
            "grupoid": None if grupo_nombre == "(Sin grupo)" else grupos.get(grupo_nombre),
            "formapagoid": None if is_potencial else formas_pago.get(formapago_nombre),
            "trabajadorid": None if trabajador_nombre == "(Sin asignar)" else trabajadores.get(trabajador_nombre),
            "observaciones": observaciones,
            "tarifaid": None if tarifa_nombre == "(Sin tarifa)" else tarifas.get(tarifa_nombre),
            "perfil_completo": False,
            "direccion_fiscal": {
                "tipo": "fiscal",
                "direccion": direccion,
                "ciudad": ciudad,
                "provincia": provincia,
                "pais": pais,
                "cp": cp,
                "telefono": telefono,
                "email": email,
                "documentacion_impresa": documentacion_impresa,
            },
            "contacto_principal": {
                "nombre": contacto_nombre,
                "email": contacto_email,
                "telefono": contacto_tel,
                "rol": contacto_rol,
                "es_principal": True,
            },
            "banco": None
            if is_potencial
            else {
                "iban": iban,
                "nombre_banco": banco_nombre,
                "fecha_baja": str(fecha_baja) if fecha_baja else None,
            },
        }

        try:
            with st.spinner("Guardando..."):
                res = _api_post("/api/clientes", json=body)
            st.toast(res.get("mensaje", "Guardado"), icon="✅")
            st.session_state["cliente_actual"] = res.get("clienteid")
            st.session_state["cli_show_form"] = None
            st.rerun()
        except requests.HTTPError as e:
            try:
                st.error(f"Error: {e.response.json()}")
            except Exception:
                st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"Error creando cliente: {e}")
