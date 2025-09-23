# modules/ui_queries.py
import streamlit as st
import pandas as pd

class QueryHelper:
    def __init__(self, supabase, table, fields, display_fields=None, search_fields=None):
        self.supabase = supabase
        self.table = table
        self.fields = fields
        self.display_fields = display_fields or fields
        self.search_fields = search_fields or fields

    def _fetch_all(self):
        res = self.supabase.table(self.table).select("*").execute()
        return pd.DataFrame(res.data or [])

    def render_quick_view(self, label="👁️ Vista rápida"):
        if st.button(label):
            df = self._fetch_all()
            if not df.empty:
                # Mostrar solo columnas que existan
                cols = [c for c in self.display_fields if c in df.columns]
                st.dataframe(df[cols], use_container_width=True)
            else:
                st.info("ℹ️ No hay datos en la tabla.")

    def render_search(self, label="🔎 Buscar"):
        query = st.text_input(label)
        if query:
            df = self._fetch_all()
            mask = df[self.search_fields].apply(
                lambda row: row.astype(str).str.contains(query, case=False, na=False).any(), axis=1
            )
            cols = [c for c in self.display_fields if c in df.columns]
            st.dataframe(df.loc[mask, cols], use_container_width=True)

    def render_filter(self, label="🎯 Filtrar por campo"):
        df = self._fetch_all()
        if df.empty:
            st.info("ℹ️ No hay datos para filtrar.")
            return

        col = st.selectbox("Selecciona un campo", self.fields)
        val = st.text_input("Valor a buscar")
        order = st.radio("Ordenar por:", ["Ascendente", "Descendente"], horizontal=True)

        if val:
            mask = df[col].astype(str).str.contains(val, case=False, na=False)
            df = df[mask]

        df = df.sort_values(by=col, ascending=(order == "Ascendente"))
        cols = [c for c in self.display_fields if c in df.columns]
        st.dataframe(df[cols], use_container_width=True)
