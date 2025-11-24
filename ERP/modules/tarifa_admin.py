# ============================================================
# 📊 ADMINISTRACIÓN DE TARIFAS (Consulta + Asignación)
# EnteNova · ERP — Fase 2 consolidada
# ============================================================

import math
import pandas as pd
import streamlit as st
from datetime import date, datetime
from typing import Optional, Dict, Any, List

# ============================================================
# Flags de características
# ============================================================
ENABLE_CREAR_TARIFA = False   # Bloqueado por negocio (placeholder)
PAGE_SIZE = 50
TARIFA_GENERAL_ID = 5

# ============================================================
# Utils genéricos
# ============================================================
def _safe(v, d="-"):
    return v if v not in ("", None, "null") else d

def _range(page: int, page_size: int):
    start = (page - 1) * page_size
    end = start + page_size - 1
    return start, end

# ============================================================
# Validación / Inserción (añadir antes de render_tarifa_admin)
# ============================================================
def _validate_tarifa_regla_payload(payload: dict) -> Optional[str]:
    campos = ("productoid", "familia_productoid", "clienteid", "grupoid")
    if not any(payload.get(k) for k in campos):
        return "Debes seleccionar al menos un cliente, grupo, producto o familia."
    return None


def _insert_tarifa_regla(supabase, payload: dict):
    err = _validate_tarifa_regla_payload(payload)
    if err:
        raise ValueError(err)
    return supabase.table("tarifa_regla").insert(payload).execute()

def _label_from(catalog: dict, id_val) -> str:
    if not id_val:
        return "-"
    for k, v in (catalog or {}).items():
        if v == id_val:
            return k
    return "-"

# ============================================================
# Catálogos
# ============================================================
def _options(supabase, tabla: str, value_field: Optional[str] = None, label_field: str = "nombre", where_enabled: bool = False) -> dict:
    try:
        q = supabase.table(tabla).select("*")
        if where_enabled:
            try:
                q = q.eq("habilitado", True)
                data = q.order(label_field).execute().data or []
            except Exception:
                data = supabase.table(tabla).select("*").order(label_field).execute().data or []
        else:
            data = q.order(label_field).execute().data or []
        if not data:
            return {}
        value_field = value_field or f"{tabla}id"
        return {str(d.get(label_field)): d.get(value_field) for d in data if d.get(value_field) is not None}
    except Exception:
        return {}

def _load_catalogos(supabase):
    tarifas   = _options(supabase, "tarifa", value_field="tarifaid", label_field="nombre")
    clientes  = _options(supabase, "cliente", value_field="clienteid", label_field="razon_social")
    grupos    = _options(supabase, "grupo", value_field="grupoid", label_field="nombre")
    productos = _options(supabase, "producto", value_field="productoid", label_field="nombre")
    familias  = _options(supabase, "producto_familia", value_field="familia_productoid", label_field="nombre")
    return tarifas, clientes, grupos, productos, familias

# ============================================================
# Contexto producto (familia)
# ============================================================
def _get_producto_ctx(supabase, productoid: Optional[int]) -> Dict[str, Any]:
    ctx = {"familia_productoid": None}
    if not productoid:
        return ctx
    try:
        row = (
            supabase.table("producto")
            .select("familia_productoid")
            .eq("productoid", productoid)
            .maybe_single()
            .execute()
            .data
        )
        if row:
            ctx["familia_productoid"] = row.get("familia_productoid")
    except Exception:
        pass
    return ctx

# ============================================================
# Carga efectiva de reglas
# ============================================================
def _fetch_reglas_effective(
    supabase,
    *,
    clienteid: Optional[int] = None,
    grupoid: Optional[int] = None,
    productoid: Optional[int] = None,
    familia_productoid: Optional[int] = None,
) -> List[dict]:
    try:
        data_all = (
            supabase.table("tarifa_regla")
            .select("tarifa_reglaid, tarifaid, clienteid, grupoid, productoid, familia_productoid, fecha_inicio, fecha_fin, habilitada")
            .execute()
            .data or []
        )
    except Exception:
        data_all = []

    if clienteid:
        data_all = [r for r in data_all if (r.get("clienteid") in (None, clienteid))]
    if grupoid:
        data_all = [r for r in data_all if (r.get("grupoid") in (None, grupoid))]

    if productoid and not familia_productoid:
        ctx = _get_producto_ctx(supabase, productoid)
        familia_productoid = ctx.get("familia_productoid")

    def match_rule(r) -> bool:
        rid_prod = r.get("productoid")
        rid_fam = r.get("familia_productoid")
        conds = []
        if productoid:
            conds.append(rid_prod == productoid)
            conds.append(rid_fam == familia_productoid)
        elif familia_productoid:
            conds.append(rid_fam == familia_productoid)
        else:
            conds.append(True)
        return any(conds)

    return [r for r in data_all if match_rule(r)]

# ============================================================
# Enriquecer tabla
# ============================================================
def _enrich_reglas_for_table(reglas: List[dict], *, tarifas, clientes, grupos, productos, familias) -> List[dict]:
    out = []
    for r in reglas:
        out.append({
            "ID": r.get("tarifa_reglaid"),
            "Tarifa": _label_from(tarifas, r.get("tarifaid")),
            "Cliente": _label_from(clientes, r.get("clienteid")),
            "Grupo": _label_from(grupos, r.get("grupoid")),
            "Producto": _label_from(productos, r.get("productoid")),
            "Familia": _label_from(familias, r.get("familia_productoid")),
            "Desde": _safe(r.get("fecha_inicio")),
            "Hasta": _safe(r.get("fecha_fin")),
            "Habilitada": bool(r.get("habilitada", True)),
        })
    return out

# ============================================================
# UI principal (parte 1) — TARIFA ADMIN
# ============================================================
def render_tarifa_admin(supabase):
    st.header("🏷️ Administración de Tarifas")
    st.caption("Consulta, habilita/deshabilita y gestiona reglas de tarifas por cliente, grupo o familia.")

    # ============================
    # 📦 Cargar catálogos
    # ============================
    tarifas, clientes, grupos, productos, familias = _load_catalogos(supabase)

    # ============================
    # 🔍 FILTROS
    # ============================
    with st.expander("🔎 Filtros", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            cli_sel = st.selectbox("Cliente", ["(Todos)"] + list(clientes.keys()))
        with c2:
            grp_sel = st.selectbox("Grupo", ["(Todos)"] + list(grupos.keys()))
        with c3:
            tar_sel = st.selectbox("Tarifa", ["(Todas)"] + list(tarifas.keys()))

        c4, c5 = st.columns(2)
        with c4:
            prod_sel = st.selectbox("Producto", ["(Todos)"] + list(productos.keys()))
        with c5:
            fam_sel = st.selectbox("Familia de producto", ["(Todas)"] + list(familias.keys()))

        show_disabled = st.toggle("👁️ Mostrar también deshabilitadas", value=False)

        clienteid    = clientes.get(cli_sel) if cli_sel != "(Todos)" else None
        grupoid      = grupos.get(grp_sel) if grp_sel != "(Todos)" else None
        tarifaid_fil = tarifas.get(tar_sel) if tar_sel != "(Todas)" else None
        productoid   = productos.get(prod_sel) if prod_sel != "(Todos)" else None
        familiaid    = familias.get(fam_sel) if fam_sel != "(Todas)" else None

    # ============================
    # 📥 CARGA DE REGLAS
    # ============================
    reglas = _fetch_reglas_effective(
        supabase,
        clienteid=clienteid,
        grupoid=grupoid,
        productoid=productoid,
        familia_productoid=familiaid,
    )

    if tarifaid_fil:
        reglas = [r for r in reglas if r.get("tarifaid") == tarifaid_fil]
    if not show_disabled:
        reglas = [r for r in reglas if r.get("habilitada")]

    rows = _enrich_reglas_for_table(
        reglas,
        tarifas=tarifas,
        clientes=clientes,
        grupos=grupos,
        productos=productos,
        familias=familias,
    )

    st.markdown("---")
    st.subheader("📋 Reglas aplicables")

    # ============================
    # 🖼️ TABLA DE VISUALIZACIÓN
    # ============================
    if not rows:
        st.info("No hay reglas que coincidan con los filtros seleccionados.")
    else:
        df = pd.DataFrame(rows)

        edited = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            disabled=["ID", "Tarifa", "Cliente", "Grupo", "Producto", "Familia", "Desde", "Hasta"],
            key="tabla_tarifas_editor",
        )

        for idx, row in edited.iterrows():
            orig = reglas[idx]
            if bool(row["Habilitada"]) != bool(orig["habilitada"]):
                supabase.table("tarifa_regla").update({
                    "habilitada": bool(row["Habilitada"])
                }).eq("tarifa_reglaid", orig["tarifa_reglaid"]).execute()

                st.toast(f"🔁 Regla {orig['tarifa_reglaid']} actualizada.")

        habil = len([r for r in reglas if r.get("habilitada")])
        total = len(reglas)
        st.caption(f"✅ {habil} habilitadas · 🚫 {total - habil} deshabilitadas · Total {total}")

        # ============================
        # 🧰 MANTENIMIENTO
        # ============================
        with st.expander("🧰 Mantenimiento de reglas", expanded=False):

            st.caption("Modifica la vigencia de una regla o elimínala permanentemente.")

            if not reglas:
                st.info("No hay reglas disponibles.")
            else:
                # ---- Construcción de etiquetas ----------------
                opciones = []
                for r in reglas:
                    t = _label_from(tarifas,   r.get("tarifaid"))
                    c = _label_from(clientes, r.get("clienteid"))
                    g = _label_from(grupos,   r.get("grupoid"))
                    p = _label_from(productos,r.get("productoid"))
                    f = _label_from(familias, r.get("familia_productoid"))

                    vig = f"{_safe(r.get('fecha_inicio'))} → {_safe(r.get('fecha_fin'))}"

                    etiqueta = f"[{r['tarifa_reglaid']}] {t} · C:{c} · G:{g} · P:{p} · F:{f} · {vig}"
                    opciones.append((etiqueta, r["tarifa_reglaid"]))

                choice_label = st.selectbox(
                    "Selecciona una regla",
                    [lbl for (lbl, _) in opciones],
                )

                regla_sel = next(v for (lbl, v) in opciones if lbl == choice_label)
                regla_obj = next(r for r in reglas if r["tarifa_reglaid"] == regla_sel)

                # ---- Vigencia ----------------
                st.markdown("### 📅 Vigencia")
                st.write(f"**Inicio actual:** {_safe(regla_obj.get('fecha_inicio'))}")

                # Fecha fin — default inteligente
                try:
                    default_fin = (
                        date.fromisoformat(regla_obj["fecha_fin"])
                        if regla_obj.get("fecha_fin")
                        else date(2999, 12, 31)
                    )
                except Exception:
                    default_fin = date(2999, 12, 31)

                nueva_fin = st.date_input(
                    "Nueva fecha fin",
                    value=default_fin,
                    key=f"new_fin_{regla_sel}",
                )

                colA, colB = st.columns(2)

                # ---- Guardar vigencia ----
                with colA:
                    if st.button("💾 Guardar vigencia", use_container_width=True):
                        try:
                            supabase.table("tarifa_regla").update({
                                "fecha_fin": nueva_fin.isoformat()
                            }).eq("tarifa_reglaid", regla_sel).execute()
                            st.success("✅ Vigencia actualizada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error guardando: {e}")

                # ---- Eliminar regla ----
                with colB:
                    if st.button("🗑️ Eliminar regla", use_container_width=True):
                        try:
                            supabase.table("tarifa_regla").delete() \
                                .eq("tarifa_reglaid", regla_sel).execute()

                            st.success("🗑️ Regla eliminada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error eliminando: {e}")
    # ============================
    # 🧩 ASIGNAR TARIFA
    # ============================
    st.markdown("---")
    st.subheader("🧩 Asignar tarifa")

    st.caption(
        "La tarifa se aplicará automáticamente según la jerarquía:\n"
        "1) Prod+Cliente = Tarifa 25 · 2) Fam+Cliente = Tarifa 20 · "
        "3) Prod+Grupo = Tarifa 15 · 4) Fam+Grupo = Tarifa 10 · 5) General = Tarifa 5"
    )

    jerarquias = [
        "1) Producto + Cliente",
        "2) Familia + Cliente",
        "3) Producto + Grupo",
        "4) Familia + Grupo",
        "5) General (cliente_tarifa)",
    ]
    pat = st.selectbox("Jerarquía", jerarquias)

    # MAPEO AUTOMÁTICO DE TARIFAS
    TARIFA_BY_JERARQUIA = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
    }

    numero = pat.split(")")[0]  # "1", "2", "3", "4", "5"
    t_id = TARIFA_BY_JERARQUIA[numero]

    colA, colB = st.columns(2)
    with colA:
        fecha_desde = st.date_input("📅 Vigente desde", value=date.today())
    with colB:
        fecha_hasta = st.date_input("📅 Vigente hasta (opcional)", value=None)

    if st.checkbox("⏳ Sin fecha final", value=False):
        fecha_hasta = date(2999, 12, 31)

    # ===== SELECCIÓN ENTIDADES SEGÚN JERARQUÍA =====
    sel_cliente = sel_grupo = sel_producto = sel_familia = None

    if numero == "1":
        sel_cliente = st.selectbox("Cliente", list(clientes.keys()))
        sel_producto = st.selectbox("Producto", list(productos.keys()))

    elif numero == "2":
        sel_cliente = st.selectbox("Cliente", list(clientes.keys()))
        sel_familia = st.selectbox("Familia", list(familias.keys()))

    elif numero == "3":
        sel_grupo = st.selectbox("Grupo", list(grupos.keys()))
        sel_producto = st.selectbox("Producto", list(productos.keys()))

    elif numero == "4":
        sel_grupo = st.selectbox("Grupo", list(grupos.keys()))
        sel_familia = st.selectbox("Familia", list(familias.keys()))

    elif numero == "5":
        sel_cliente = st.selectbox("Cliente", list(clientes.keys()))


    # ===== GUARDAR =====
    if st.button("💾 Guardar asignación", type="primary", use_container_width=True):
        try:
            payload = {
                "tarifaid": t_id,
                "habilitada": True,
                "fecha_inicio": fecha_desde.isoformat(),
            }
            if fecha_hasta:
                payload["fecha_fin"] = fecha_hasta.isoformat()

            if numero == "1":
                payload["clienteid"]  = clientes[sel_cliente]
                payload["productoid"] = productos[sel_producto]

            elif numero == "2":
                payload["clienteid"] = clientes[sel_cliente]
                payload["familia_productoid"] = familias[sel_familia]

            elif numero == "3":
                payload["grupoid"] = grupos[sel_grupo]
                payload["productoid"] = productos[sel_producto]

            elif numero == "4":
                payload["grupoid"] = grupos[sel_grupo]
                payload["familia_productoid"] = familias[sel_familia]

            elif numero == "5":
                supabase.table("cliente_tarifa").insert({
                    "clienteid": clientes[sel_cliente],
                    "tarifaid": t_id,
                    "fecha_desde": fecha_desde.isoformat(),
                    "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                }).execute()
                st.success("✅ Tarifa general asignada.")
                st.rerun()

            _insert_tarifa_regla(supabase, payload)
            st.success("✅ Asignación registrada correctamente.")
            st.rerun()

        except ValueError as ve:
            st.warning(f"⚠️ {ve}")
        except Exception as e:
            msg = str(e)
            if "duplicate key" in msg:
                st.info("ℹ️ Ya existe una regla equivalente para ese objetivo y rango de fechas.")
            else:
                st.error(f"❌ Error: {e}")

    # ============================
    # ❌ CREAR TARIFA (bloqueado)
    # ============================
    with st.expander("➕ Crear NUEVA tarifa (bloqueado)", expanded=False):
        st.info("Funcionalidad deshabilitada por política interna.")
