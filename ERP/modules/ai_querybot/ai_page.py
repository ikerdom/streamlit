import streamlit as st
from .database import DatabaseManager
from .ai_assistant import generate_sql_query, generate_response, generate_analysis_response
from .visualizer import ResultVisualizer

def render_ai_page():

    st.title("🤖 Consultas Inteligentes (DataQueryBot)")

    question = st.text_input("Introduce tu pregunta:")

    if st.button("Consultar"):
        if not question.strip():
            st.warning("Escribe una pregunta.")
            return

        try:
            db = DatabaseManager(db_type="supabase")
            schema = db.get_schema()

            # GENERAR SQL
            sql = generate_sql_query(question, schema)
            st.subheader("🧩 SQL generada")
            st.code(sql, language="sql")

            # EJECUTAR SQL
            df = db.execute_query(sql)
            st.subheader("📄 Resultados")
            st.dataframe(df)

            # RESPUESTA BREVE
            summary = generate_response(question, df, sql)
            st.subheader("📝 Resumen")
            st.write(summary)

            # ANÁLISIS
            analysis = generate_analysis_response(question, df)
            st.subheader("📊 Análisis avanzado")
            st.write(analysis)

            # GRAFICOS
            st.subheader("📈 Visualizaciones")
            vis = ResultVisualizer(df)
            for fig in [
                vis.create_line_chart(),
                vis.create_bar_chart(),
                vis.create_pie_chart(),
                vis.create_histogram(),
                vis.create_scatter_plot(),
            ]:
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error: {e}")
