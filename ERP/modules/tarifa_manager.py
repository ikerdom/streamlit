# modules/tarifa_manager.py
import streamlit as st
import pandas as pd
from datetime import date
from modules.precio_engine import calcular_precio_linea
from modules.tarifa_admin import render_tarifa_admin
from modules.simulador_pedido import render_simulador_pedido
# =========================================================
# 🧩 Helpers visuales
# =========================================================
def _pill(text, color="#eef2ff", border="#dbeafe"):
    return f"<span style='padding:4px 8px;border-radius:999px;background:{color};border:1px solid {border};font-size:12px'>{text}</span>"

def _card(title, subtitle, kpis: list[str]):
    items = "".join([f"<li style='margin:2px 0'>{k}</li>" for k in kpis])
    return f"""
    <div style="border:1px solid #eee;border-radius:12px;padding:14px 16px;
                box-shadow:0 1px 4px rgba(0,0,0,.05);background:#fff;margin-bottom:8px">
      <div style="font-weight:600;font-size:14px;margin-bottom:4px">{title}</div>
      <div style="color:#666;font-size:12px;margin-bottom:8px">{subtitle}</div>
      <ul style="padding-left:16px;margin:0">{items}</ul>
    </div>
    """

def _opts(supabase, table, idcol, namecol, ordercol=None):
    try:
        q = supabase.table(table).select(f"{idcol}, {namecol}")
        if ordercol:
            q = q.order(ordercol)
        return q.execute().data or []
    except Exception:
        return []

def _nivel_to_int(nivel: str) -> int:
    return {
        "Producto + Cliente": 1,
        "Familia + Cliente": 2,
        "Producto + Grupo": 3,
        "Familia + Grupo": 4,
    }.get(nivel, 999)

# =========================================================
# 🏷️ Módulo principal: Gestión de tarifas
# =========================================================
def render_tarifa_manager(supabase):
    st.header("🏷️ Gestión de tarifas y jerarquías")
    st.caption("Consulta, administra y crea reglas de tarifas con control jerárquico y promociones directas.")

    tabs = st.tabs(["📊 Vista general", "🧩 Reglas", "➕ Crear tarifa/reglas", "🧮 Simulador"])

    # ======================================================
    # TAB 1 · RESUMEN + JERARQUÍAS
    # ======================================================
    with tabs[0]:
        st.subheader("📊 Resumen general de tarifas")
        colf1, colf2 = st.columns([2, 1])
        with colf1:
            filtro = st.text_input("🔍 Buscar tarifa por nombre...")
        with colf2:
            solo_activas = st.checkbox("Mostrar solo activas", True)

        try:
            data = supabase.table("vw_tarifa_resumen_slim").select("*").execute().data or []
        except Exception as e:
            st.error(f"Error cargando resumen: {e}")
            data = []

        if not data:
            st.info("No hay tarifas definidas todavía.")
        else:
            df = pd.DataFrame(data)
            if filtro:
                df = df[df["nombre_tarifa"].str.contains(filtro, case=False, na=False)]
            if solo_activas and "habilitada" in df.columns:
                df = df[df["habilitada"] == True]

            for _, row in df.iterrows():
                nombre_t = row["nombre_tarifa"]
                fecha_inicio = row.get("fecha_inicio", "—")
                fecha_fin = row.get("fecha_fin", "Sin fecha final")
                vigencia = f"🗓️ {fecha_inicio} → {fecha_fin}"

                kpis = [
                    f"💸 Descuento: <b>{row.get('descuento_pct', 0):.0f}%</b>",
                    f"👥 Clientes: <b>{int(row.get('clientes_tarifa', 0))}</b>",
                    f"📦 Productos·Cliente: <b>{int(row.get('combos_prod_cli', 0))}</b>",
                    f"📚 Familias·Cliente: <b>{int(row.get('combos_fam_cli', 0))}</b>",
                    f"🏢 Productos·Grupo: <b>{int(row.get('combos_prod_grp', 0))}</b>",
                    f"🏷️ Familias·Grupo: <b>{int(row.get('combos_fam_grp', 0))}</b>",
                    _pill(f"Total combinaciones: {int(row.get('total_combos', 0))}")
                ]
                st.markdown(_card(nombre_t, vigencia, kpis), unsafe_allow_html=True)

                # --- Expander con jerarquías detalladas
                with st.expander(f"📊 Ver jerarquías de {nombre_t}", expanded=False):
                    try:
                        jer = (
                            supabase.table("vw_tarifa_jerarquias")
                            .select("*")
                            .eq("nombre_tarifa", nombre_t)
                            .single()
                            .execute()
                            .data
                        )
                    except Exception:
                        jer = None

                    if not jer:
                        st.caption("No hay reglas asociadas a esta tarifa.")
                    else:
                        col1, col2 = st.columns(2)
                        def _jer_card(icon, title, content, color):
                            html = f"""
                            <div style="border-left:4px solid {color};background:#fff;border-radius:8px;
                                        padding:10px 14px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.05);">
                                <div style="font-weight:600;margin-bottom:4px;">{icon} {title}</div>
                                <div style="font-size:13px;color:#333;">{content if content else '—'}</div>
                            </div>
                            """
                            st.markdown(html, unsafe_allow_html=True)

                        with col1:
                            _jer_card("📦", "Producto + Cliente", jer.get("producto_cliente"), "#4f46e5")
                            _jer_card("🏢", "Producto + Grupo", jer.get("producto_grupo"), "#2563eb")
                        with col2:
                            _jer_card("📚", "Familia + Cliente", jer.get("familia_cliente"), "#16a34a")
                            _jer_card("🏷️", "Familia + Grupo", jer.get("familia_grupo"), "#d97706")

    # ======================================================
    # TAB 2 · REGLAS
    # ======================================================
    with tabs[1]:
        st.subheader("🧩 Reglas de tarifas")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            q = st.text_input("Buscar cliente, grupo, producto o familia...")
        with c2:
            tarifas = _opts(supabase, "tarifa", "tarifaid", "nombre", "tarifaid")
            fil_tarifa = st.selectbox("Filtrar por tarifa", ["(todas)"] + [t["nombre"] for t in tarifas])
        with c3:
            fil_nivel = st.selectbox(
                "Filtrar jerarquía",
                ["(todas)", "Producto + Cliente", "Familia + Cliente", "Producto + Grupo", "Familia + Grupo"]
            )

        try:
            data = supabase.table("vw_tarifa_regla_pretty").select("*").execute().data or []
        except Exception as e:
            st.error(f"No pude cargar reglas: {e}")
            data = []

        df = pd.DataFrame(data)
        if fil_tarifa != "(todas)":
            df = df[df["nombre_tarifa"] == fil_tarifa]
        if fil_nivel != "(todas)":
            df = df[df["nivel"] == fil_nivel]
        if q:
            q = q.lower()
            mask = (
                df["cliente"].fillna("").str.lower().str.contains(q)
                | df["grupo"].fillna("").str.lower().str.contains(q)
                | df["producto"].fillna("").str.lower().str.contains(q)
                | df["familia"].fillna("").str.lower().str.contains(q)
            )
            df = df[mask]

        if df.empty:
            st.info("No hay reglas coincidentes.")
        else:
            st.dataframe(
                df[["nombre_tarifa", "descuento_pct", "nivel", "cliente", "grupo", "producto", "familia", "fecha_inicio", "fecha_fin"]],
                use_container_width=True,
                hide_index=True
            )

    # ======================================================
    # TAB 3 · CREAR NUEVA TARIFA / REGLAS + PROMOCIÓN
    # ======================================================
    with tabs[2]:
        st.subheader("➕ Crear nueva tarifa y sus reglas")
        clientes = _opts(supabase, "cliente", "clienteid", "razon_social", "razon_social")
        grupos   = _opts(supabase, "grupo", "grupoid", "nombre", "nombre")
        prods    = _opts(supabase, "producto", "productoid", "nombre", "nombre")
        fams     = _opts(supabase, "producto_familia", "familia_productoid", "nombre", "nombre")

        # --- CREACIÓN DE TARIFA ---
        with st.form("new_tarifa_form"):
            c1, c2 = st.columns([2, 1])
            with c1:
                nombre_t = st.text_input("Nombre de tarifa", placeholder="Tarifa Especial Navidad 2025")
            with c2:
                descuento = st.number_input("Descuento (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
            desc = st.text_area("Descripción (opcional)")

            st.markdown("### 🎯 Asociaciones opcionales")
            nivel = st.radio(
                "Tipo de jerarquía",
                ["(sin asociación)", "Producto + Cliente", "Familia + Cliente", "Producto + Grupo", "Familia + Grupo"],
                horizontal=True
            )

            clientes_sel = grupos_sel = productos_sel = familias_sel = []
            if "Cliente" in nivel:
                clientes_sel = st.multiselect("Clientes", [c["razon_social"] for c in clientes])
            if "Grupo" in nivel:
                grupos_sel = st.multiselect("Grupos", [g["nombre"] for g in grupos])
            if "Producto" in nivel:
                productos_sel = st.multiselect("Productos", [p["nombre"] for p in prods])
            if "Familia" in nivel:
                familias_sel = st.multiselect("Familias", [f["nombre"] for f in fams])

            colF1, colF2, colF3 = st.columns([1,1,1])
            with colF1:
                fd = st.date_input("Desde", value=date.today())
            with colF2:
                fh = st.date_input("Hasta (opcional)", value=None)
            with colF3:
                infinito = st.checkbox("📆 Sin caducidad", value=False)
            if infinito:
                fh = date(2999, 12, 31)

            ok = st.form_submit_button("💾 Crear tarifa y reglas")
            if ok:
                try:
                    t_res = supabase.table("tarifa").insert({
                        "nombre": nombre_t.strip(),
                        "descripcion": desc.strip() or None,
                        "descuento_pct": descuento,
                        "habilitada": True
                    }).execute()
                    new_tarifaid = t_res.data[0]["tarifaid"]
                    combos = []
                    for cli in clientes_sel or [None]:
                        for grp in grupos_sel or [None]:
                            for prod in productos_sel or [None]:
                                for fam in familias_sel or [None]:
                                    if any([cli, grp, prod, fam]):
                                        combos.append({
                                            "tarifaid": new_tarifaid,
                                            "clienteid": next((c["clienteid"] for c in clientes if c["razon_social"] == cli), None),
                                            "grupoid": next((g["grupoid"] for g in grupos if g["nombre"] == grp), None),
                                            "productoid": next((p["productoid"] for p in prods if p["nombre"] == prod), None),
                                            "familia_productoid": next((f["familia_productoid"] for f in fams if f["nombre"] == fam), None),
                                            "fecha_inicio": fd.isoformat(),
                                            "fecha_fin": fh.isoformat() if fh else None,
                                            "prioridad": _nivel_to_int(nivel),
                                            "habilitada": True
                                        })
                    for r in combos:
                        supabase.table("tarifa_regla").insert(r).execute()
                    st.success(f"✅ Tarifa '{nombre_t}' creada con {len(combos)} regla(s).")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creando tarifa/reglas: {e}")

        st.divider()

        # --- PROMOCIÓN DE CLIENTE / PRODUCTO ---
        st.subheader("⚙️ Promocionar combinaciones existentes a otra tarifa")
        st.caption("Asciende clientes o productos que actualmente usan la tarifa general a una superior.")

        tarifas = _opts(supabase, "tarifa", "tarifaid", "nombre", "tarifaid")

        colp1, colp2, colp3 = st.columns([2, 2, 1])
        with colp1:
            cliente_nom = st.selectbox("👤 Cliente", ["(Selecciona)"] + [c["razon_social"] for c in clientes])
        with colp2:
            producto_nom = st.selectbox("📦 Producto", ["(Selecciona)"] + [p["nombre"] for p in prods])
        with colp3:
            nueva_tarifa = st.selectbox("🏷️ Tarifa destino", ["(Selecciona)"] + [t["nombre"] for t in tarifas])

        colf1, colf2, colf3 = st.columns([1, 1, 1])
        with colf1:
            fd = st.date_input("Desde", value=date.today(), key="fd_prom")
        with colf2:
            fh = st.date_input("Hasta (opcional)", value=None, key="fh_prom")
        with colf3:
            infinito = st.checkbox("📆 Sin caducidad", value=False, key="inf_prom")
        if infinito:
            fh = date(2999, 12, 31)

        if st.button("🚀 Promocionar combinación", use_container_width=True):
            if "(Selecciona)" in (cliente_nom, producto_nom, nueva_tarifa):
                st.warning("⚠️ Selecciona cliente, producto y tarifa destino antes de continuar.")
            else:
                try:
                    clienteid = next(c["clienteid"] for c in clientes if c["razon_social"] == cliente_nom)
                    productoid = next(p["productoid"] for p in prods if p["nombre"] == producto_nom)
                    tarifaid = next(t["tarifaid"] for t in tarifas if t["nombre"] == nueva_tarifa)
                    supabase.table("tarifa_regla").insert({
                        "tarifaid": tarifaid,
                        "clienteid": clienteid,
                        "productoid": productoid,
                        "fecha_inicio": fd.isoformat(),
                        "fecha_fin": fh.isoformat() if fh else None,
                        "prioridad": 1,
                        "habilitada": True
                    }).execute()
                    st.success(f"✅ '{cliente_nom} · {producto_nom}' promovido a **{nueva_tarifa}**.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al promocionar: {e}")

    # ======================================================
    # TAB 4 · SIMULADOR
    # ======================================================
    with tabs[3]:
        from modules.simulador_pedido import render_simulador_pedido
        render_simulador_pedido(supabase)
