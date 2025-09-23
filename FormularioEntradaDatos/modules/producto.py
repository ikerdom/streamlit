# modules/producto.py
import streamlit as st
import pandas as pd
from .ui import (
    render_header, can_edit
)

TABLE = "producto"
FIELDS_LIST = [
    "productoid","sku","isbn13","ean13","titulo","autor","coleccion","edicion",
    "formato","idioma","anopublicacion","pvp","tipoiva",
    "stockactual","activo","fechaalta"
]

EDIT_KEY = "editing_pro"
DEL_KEY  = "pending_delete_pro"

def render_producto(supabase):
    # ✅ Cabecera corporativa
    render_header(
        "📚 Gestión de Productos",
        "Libros y materiales en catálogo."
    )

    tab1, tab2, tab3 = st.tabs(["📝 Formulario + Tabla", "📂 CSV", "📖 Instrucciones"])

    # -------------------------------
    # TAB 1
    # -------------------------------
    with tab1:
        st.subheader("Añadir Producto")
        with st.form("form_producto"):
            sku = st.text_input("SKU *", max_chars=50)

            col1, col2 = st.columns(2)
            isbn = col1.text_input("ISBN13", max_chars=13)
            ean  = col2.text_input("EAN13", max_chars=13)

            titulo = st.text_input("Título *", max_chars=250)

            col3, col4 = st.columns(2)
            autor     = col3.text_input("Autor", max_chars=200)
            coleccion = col4.text_input("Colección", max_chars=150)

            col5, col6, col7, col8, col9 = st.columns(5)
            edicion = col5.text_input("Edición", max_chars=50)
            formato = col6.text_input("Formato", max_chars=50)
            idioma  = col7.text_input("Idioma", max_chars=50)
            anio    = col8.number_input("Año publicación", min_value=1900, max_value=2100, value=2025)
            pvp     = col9.number_input("PVP (€)", min_value=0.0, value=0.0, format="%.2f")

            col10, col11 = st.columns(2)
            iva   = col10.number_input("Tipo IVA (%)", min_value=0.0, value=4.0, format="%.2f")
            stock = col11.number_input("Stock actual", min_value=0, value=0)

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

        # ---------------------------
        # 🔎 Búsqueda y filtros
        # ---------------------------
        st.markdown("### 🔎 Buscar / Filtrar productos")
        df = pd.DataFrame(supabase.table(TABLE).select("*").execute().data)

        if not df.empty:
            with st.expander("🔎 Filtros"):
                campo = st.selectbox("Selecciona un campo", df.columns, key="pro_campo")
                valor = st.text_input("Valor a buscar", key="pro_valor")
                orden = st.radio("Ordenar por", ["Ascendente", "Descendente"],
                                 horizontal=True, key="pro_orden")

                if valor:
                    df = df[df[campo].astype(str).str.contains(valor, case=False, na=False)]
                df = df.sort_values(by=campo, ascending=(orden=="Ascendente"))

        # ---------------------------
        # 📑 Tabla en vivo
        # ---------------------------
        st.markdown("### 📑 Productos registrados")
        st.dataframe(df, use_container_width=True)

        # ---------------------------
        # ⚙️ Acciones avanzadas
        # ---------------------------
        st.markdown("### ⚙️ Acciones avanzadas")
        with st.expander("⚙️ Editar / Borrar productos (requiere login)"):
            if can_edit():
                for _, row in df.iterrows():
                    pid = int(row["productoid"])
                    st.markdown(f"**{row.get('sku','')} — {row.get('titulo','')}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ Editar", key=f"edit_pro_{pid}"):
                            st.session_state[EDIT_KEY] = pid
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Borrar", key=f"del_pro_{pid}"):
                            st.session_state[DEL_KEY] = pid
                            st.rerun()
                    st.markdown("---")

                # Confirmación de borrado
                if st.session_state.get(DEL_KEY):
                    did = st.session_state[DEL_KEY]
                    st.error(f"⚠️ ¿Eliminar producto #{did}?")
                    c1,c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Confirmar", key="pro_confirm"):
                            supabase.table(TABLE).delete().eq("productoid", did).execute()
                            st.success("✅ Producto eliminado")
                            st.session_state[DEL_KEY] = None
                            st.rerun()
                    with c2:
                        if st.button("❌ Cancelar", key="pro_cancel"):
                            st.session_state[DEL_KEY] = None
                            st.rerun()

                # Edición inline
                if st.session_state.get(EDIT_KEY):
                    eid = st.session_state[EDIT_KEY]
                    cur = df[df["productoid"]==eid].iloc[0].to_dict()
                    st.subheader(f"Editar Producto #{eid}")
                    with st.form(f"edit_pro_{eid}"):
                        sku  = st.text_input("SKU", cur.get("sku",""))
                        tit  = st.text_input("Título", cur.get("titulo",""))
                        aut  = st.text_input("Autor", cur.get("autor",""))
                        edi  = st.text_input("Edición", cur.get("edicion",""))
                        frm  = st.text_input("Formato", cur.get("formato",""))
                        idi  = st.text_input("Idioma", cur.get("idioma",""))
                        anio = st.number_input("Año publicación",
                                               min_value=1900, max_value=2100,
                                               value=int(cur.get("anopublicacion") or 2025))
                        precio = st.number_input("PVP (€)",
                                                 min_value=0.0,
                                                 value=float(cur.get("pvp") or 0.0),
                                                 format="%.2f")
                        stk  = st.number_input("Stock actual",
                                               min_value=0,
                                               value=int(cur.get("stockactual",0)))

                        if st.form_submit_button("💾 Guardar"):
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
                            st.session_state[EDIT_KEY] = None
                            st.rerun()
            else:
                st.warning("⚠️ Debes iniciar sesión para editar o borrar productos.")

    # -------------------------------
    # TAB 2: CSV
    # -------------------------------
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

    # -------------------------------
    # TAB 3: Instrucciones
    # -------------------------------
    with tab3:
        st.subheader("📑 Campos de Producto")
        st.markdown("""
        - **sku** → Código interno único del producto.  
        - **isbn13 / ean13** → Identificadores estándar de libros y materiales.  
        - **titulo** → Nombre del producto o libro.  
        - **autor / coleccion** → Autor principal y colección.  
        - **edicion / formato / idioma / anopublicacion / pvp** → Datos editoriales.  
        - **tipoiva** → Porcentaje de IVA aplicado.  
        - **stockactual** → Cantidad disponible en inventario.  
        - **activo** → Si el producto está disponible.  
        - **fechaalta** → Fecha de creación automática.  
        """)
        st.subheader("📖 Ejemplo CSV")
        st.code(
            "sku,isbn13,ean13,titulo,autor,coleccion,edicion,formato,idioma,anopublicacion,pvp,tipoiva,stockactual\n"
            "SKU001,9781234567890,8412345678901,Matemáticas Básicas,Luis García,Colección ESO,1ª,Tapa blanda,Español,2023,25.00,4.00,100",
            language="csv"
        )
