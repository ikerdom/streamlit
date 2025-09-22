# modules/producto.py
import streamlit as st
import pandas as pd
from .ui import draw_live_df, can_edit, render_header, draw_feed_generic

TABLE = "producto"
FIELDS_LIST = [
    "productoid","sku","isbn13","ean13","titulo","autor","coleccion","edicion",
    "formato","idioma","anopublicacion","pvp","tipoiva",
    "stockactual","activo","fechaalta"
]

def render_producto(supabase):
    # ✅ Cabecera unificada con mini feed
    render_header(
        "📚 Gestión de Productos",
        "Libros y materiales en catálogo."
    )
    draw_feed_generic(supabase, TABLE, "titulo", "fechaalta", "productoid")

    tab1, tab2, tab3 = st.tabs(["📝 Formulario", "📂 CSV", "📖 Instrucciones"])

    # --- TAB 1: Formulario
    with tab1:
        st.subheader("Añadir Producto")
        with st.form("form_producto"):
            sku = st.text_input("SKU *", max_chars=50)

            # ISBN y EAN
            col1, col2 = st.columns(2)
            with col1:
                isbn = st.text_input("ISBN13", max_chars=13)
            with col2:
                ean = st.text_input("EAN13", max_chars=13)

            titulo = st.text_input("Título *", max_chars=250)

            # Autor y Colección
            col3, col4 = st.columns(2)
            with col3:
                autor = st.text_input("Autor", max_chars=200)
            with col4:
                coleccion = st.text_input("Colección", max_chars=150)

            # Edición / formato / idioma / año / PVP
            col5, col6, col7, col8, col9 = st.columns([1,1,1,1,1])
            with col5:
                edicion = st.text_input("Edición", max_chars=50)
            with col6:
                formato = st.text_input("Formato", max_chars=50)
            with col7:
                idioma  = st.text_input("Idioma", max_chars=50)
            with col8:
                anio    = st.number_input("Año publicación", min_value=1900, max_value=2100, value=2025)
            with col9:
                pvp     = st.number_input("PVP (€)", min_value=0.0, value=0.0, format="%.2f")

            # IVA y stock
            col10, col11 = st.columns(2)
            with col10:
                iva   = st.number_input("Tipo IVA (%)", min_value=0.0, value=4.0, format="%.2f")
            with col11:
                stock = st.number_input("Stock actual", min_value=0, value=0)

            if st.form_submit_button("➕ Insertar"):
                if not sku or not titulo:
                    st.error("❌ SKU y Título obligatorios")
                else:
                    supabase.table(TABLE).insert({
                        "sku": sku,
                        "isbn13": isbn,
                        "ean13": ean,
                        "titulo": titulo,
                        "autor": autor,
                        "coleccion": coleccion,
                        "edicion": edicion,
                        "formato": formato,
                        "idioma": idioma,
                        "anopublicacion": anio,
                        "pvp": pvp,
                        "tipoiva": iva,
                        "stockactual": stock
                    }).execute()
                    st.success("✅ Producto insertado")
                    st.rerun()

        st.markdown("#### 📑 Productos (en vivo) con acciones")
        df = draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

        if not df.empty:
            st.write("✏️ **Editar** o 🗑️ **Borrar** registros directamente:")

            header = st.columns([0.5,0.5,1.5,3,2,1,1])
            for col, txt in zip(header, ["✏️","🗑️","SKU","Título","Autor","Stock","ID"]):
                col.markdown(f"**{txt}**")

            for _, row in df.iterrows():
                pid = int(row["productoid"])
                cols = st.columns([0.5,0.5,1.5,3,2,1,1])

                # Editar
                with cols[0]:
                    if can_edit():
                        if st.button("✏️", key=f"pro_edit_{pid}"):
                            st.session_state["editing"] = pid
                            st.rerun()
                    else:
                        st.button("✏️", key=f"pro_edit_{pid}", disabled=True)

                # Borrar
                with cols[1]:
                    if can_edit():
                        if st.button("🗑️", key=f"pro_delask_{pid}"):
                            st.session_state["pending_delete"] = pid
                            st.rerun()
                    else:
                        st.button("🗑️", key=f"pro_delask_{pid}", disabled=True)

                cols[2].write(row.get("sku",""))
                cols[3].write(row.get("titulo",""))
                cols[4].write(row.get("autor",""))
                cols[5].write(row.get("stockactual",""))
                cols[6].write(pid)

            # Confirmación de borrado
            if st.session_state.get("pending_delete"):
                did = st.session_state["pending_delete"]
                st.markdown("---")
                st.error(f"⚠️ ¿Seguro que quieres eliminar el producto #{did}?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar", key="pro_confirm_del"):
                        supabase.table(TABLE).delete().eq("productoid", did).execute()
                        st.success("✅ Producto eliminado")
                        st.session_state["pending_delete"] = None
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="pro_cancel_del"):
                        st.session_state["pending_delete"] = None
                        st.rerun()

            # Edición inline
            if st.session_state.get("editing"):
                eid = st.session_state["editing"]
                cur = df[df["productoid"]==eid].iloc[0].to_dict()
                st.markdown("---")
                st.subheader(f"Editar Producto #{eid}")
                with st.form("edit_producto"):
                    col1, col2 = st.columns(2)
                    with col1:
                        sku  = st.text_input("SKU", cur.get("sku",""))
                        tit  = st.text_input("Título", cur.get("titulo",""))
                        aut  = st.text_input("Autor", cur.get("autor",""))
                        edi  = st.text_input("Edición", cur.get("edicion",""))
                        frm  = st.text_input("Formato", cur.get("formato",""))
                    with col2:
                        idi  = st.text_input("Idioma", cur.get("idioma",""))
                        anio = st.number_input("Año publicación", 
                                               min_value=1900, max_value=2100, 
                                               value=int(cur.get("anopublicacion") or 2025))
                        precio = st.number_input("PVP (€)", 
                                                 min_value=0.0, 
                                                 value=float(cur.get("pvp") or 0.0), 
                                                 format="%.2f")
                        stk  = st.number_input("Stock", 
                                               min_value=0, 
                                               value=int(cur.get("stockactual",0)))

                    if st.form_submit_button("💾 Guardar"):
                        if can_edit():
                            supabase.table(TABLE).update({
                                "sku": sku,
                                "titulo": tit,
                                "autor": aut,
                                "edicion": edi,
                                "formato": frm,
                                "idioma": idi,
                                "anopublicacion": anio,
                                "pvp": precio,
                                "stockactual": stk
                            }).eq("productoid", eid).execute()
                            st.success("✅ Producto actualizado")
                            st.session_state["editing"] = None
                            st.rerun()
                        else:
                            st.error("⚠️ Inicia sesión para editar registros.")

    # --- TAB 2: CSV
    with tab2:
        st.subheader("Importar desde CSV")
        st.caption("Columnas: sku,isbn13,ean13,titulo,autor,coleccion,edicion,formato,idioma,anopublicacion,pvp,tipoiva,stockactual")
        up = st.file_uploader("Selecciona CSV", type=["csv"], key="csv_producto")
        if up:
            df_csv = pd.read_csv(up)
            st.dataframe(df_csv, use_container_width=True)
            if st.button("➕ Insertar todos", key="btn_csv_producto"):
                supabase.table(TABLE).insert(df_csv.to_dict(orient="records")).execute()
                st.success(f"✅ Insertados {len(df_csv)}")
                st.rerun()

        st.markdown("#### 📑 Productos (en vivo)")
        draw_live_df(supabase, TABLE, columns=FIELDS_LIST)

    # --- TAB 3: Instrucciones
    with tab3:
        st.subheader("📑 Campos de Producto")
        st.markdown("""
        - **sku** → Código interno único del producto.  
        - **isbn13 / ean13** → Identificadores estándar de libros y materiales.  
        - **titulo** → Nombre del producto o libro.  
        - **autor / coleccion** → Autor principal y colección a la que pertenece.  
        - **edicion / formato / idioma / anopublicacion / pvp** → Datos editoriales tabulados.  
        - **tipoiva** → Porcentaje de IVA aplicado.  
        - **stockactual** → Cantidad disponible en inventario.  
        - **activo** → Indica si el producto está disponible para la venta.  
        - **fechaalta** → Fecha de creación automática.  
        """)    
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "sku,isbn13,ean13,titulo,autor,coleccion,edicion,formato,idioma,anopublicacion,pvp,tipoiva,stockactual\n"
            "SKU001,9781234567890,8412345678901,Matemáticas Básicas,Luis García,Colección ESO,1ª,Tapa blanda,Español,2023,25.00,4.00,100",
            language="csv"
        )
