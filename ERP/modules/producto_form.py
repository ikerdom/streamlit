# ======================================================
# 📦 FORMULARIO DE PRODUCTO — Alta y edición
# ======================================================
import streamlit as st
from datetime import date
from modules.producto_models import (
    load_familias,
    load_tipos_producto,
    load_impuestos,
    load_estados_producto,
)

def render_producto_form(supabase, productoid=None, on_saved_rerun=True):
    modo = "✏️ Editar producto" if productoid else "➕ Nuevo producto"
    st.subheader(modo)

    familias = load_familias(supabase)
    tipos = load_tipos_producto(supabase)
    impuestos = load_impuestos(supabase)
    estados = load_estados_producto(supabase)

    producto = {}
    if productoid:
        try:
            r = supabase.table("producto").select("*").eq("productoid", productoid).single().execute()
            producto = r.data or {}
        except Exception as e:
            st.error(f"❌ Error cargando producto: {e}")
            return

    with st.expander("📋 Datos generales", expanded=True):
        with st.form(f"form_producto_{productoid or 'new'}"):
            c1, c2 = st.columns(2)
            with c1:
                nombre = st.text_input("Nombre *", producto.get("nombre", ""))
                referencia = st.text_input("Referencia / SKU", producto.get("referencia", ""))
                isbn = st.text_input("ISBN", producto.get("isbn", ""))
                ean = st.text_input("EAN", producto.get("ean", ""))
                precio = st.number_input(
                    "💶 Precio genérico",
                    min_value=0.0,
                    step=0.01,
                    value=float(producto.get("precio_generico", 0.0)),
                )
                publico = st.checkbox("Visible al público", value=bool(producto.get("publico", True)))
            with c2:
                titulo = st.text_input("Título / Nombre comercial", producto.get("titulo", ""))
                tipo_txt = st.text_input("Tipo (texto libre)", producto.get("tipo", ""))
                versatilidad = st.text_input("Versatilidad", producto.get("versatilidad", ""))
                fecha_pub = st.date_input(
                    "📅 Fecha publicación",
                    value=date.fromisoformat(producto["fecha_publicacion"])
                    if producto.get("fecha_publicacion")
                    else date.today(),
                )
                portada_url = st.text_input("URL portada", producto.get("portada_url", ""))

            sinopsis = st.text_area("📝 Sinopsis / descripción", producto.get("sinopsis", ""), height=120)

            # --------------------------------------------
            # Catálogos con preselección desde el árbol
            # --------------------------------------------
            cA, cB, cC, cD = st.columns(4)

            # Prefill de familia si viene desde el árbol (solo si es alta)
            prefill_fid = None
            if not productoid:
                prefill_fid = st.session_state.get("prefill_familia_productoid")

            # Determinar índice de familia correcto
            familia_val = producto.get("familia_productoid") or prefill_fid
            familia_idx = _sel_idx(familias, familia_val)
            familia_sel = st.selectbox(
                "📂 Familia",
                ["(sin familia)"] + list(familias.keys()),
                index=familia_idx,
            )

            tipo_sel = st.selectbox(
                "🏷️ Tipo",
                ["(sin tipo)"] + list(tipos.keys()),
                index=_sel_idx(tipos, producto.get("producto_tipoid")),
            )

            imp_sel = st.selectbox(
                "💰 Impuesto",
                ["(sin impuesto)"] + list(impuestos.keys()),
                index=_sel_idx(impuestos, producto.get("impuestoid")),
            )

            est_sel = st.selectbox(
                "⚙️ Estado",
                ["(sin estado)"] + list(estados.keys()),
                index=_sel_idx(estados, producto.get("estado_productoid")),
            )

            guardar = st.form_submit_button("💾 Guardar producto", use_container_width=True)

        if guardar:
            if not nombre.strip():
                st.warning("⚠️ El nombre es obligatorio.")
                return

            payload = {
                "nombre": nombre.strip(),
                "titulo": titulo.strip() or None,
                "referencia": referencia.strip() or None,
                "isbn": isbn.strip() or None,
                "ean": ean.strip() or None,
                "precio_generico": float(precio),
                "publico": publico,
                "tipo": tipo_txt.strip() or None,
                "versatilidad": versatilidad.strip() or None,
                "fecha_publicacion": fecha_pub.isoformat(),
                "portada_url": portada_url.strip() or None,
                "sinopsis": sinopsis.strip() or None,
                "familia_productoid": familias.get(familia_sel),
                "producto_tipoid": tipos.get(tipo_sel),
                "impuestoid": impuestos.get(imp_sel),
                "estado_productoid": estados.get(est_sel),
            }

            try:
                if productoid:
                    supabase.table("producto").update(payload).eq("productoid", productoid).execute()
                    st.toast("✅ Producto actualizado correctamente.", icon="✅")
                else:
                    res = supabase.table("producto").insert(payload).execute()
                    nuevo_id = res.data[0]["productoid"] if res.data else None
                    st.toast(f"✅ Producto creado (ID {nuevo_id}).", icon="✅")

                # Limpiar preselección después de guardar
                if "prefill_familia_productoid" in st.session_state:
                    del st.session_state["prefill_familia_productoid"]

                if on_saved_rerun:
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error guardando producto: {e}")


def _sel_idx(d, val):
    for i, (k, v) in enumerate(d.items()):
        if v == val:
            return i + 1
    return 0
