import streamlit as st
import pandas as pd
import plotly.express as px
import base64
from pandas.api.types import is_integer_dtype

from database import DatabaseManager
from ai_assistant import (
    generate_sql_query,
    generate_response,
    generate_analysis_response,
    repair_sql_query,
)

# ---------- helper para logos en base64 ----------

def load_image_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


def init_session_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "db_manager" not in st.session_state:
        st.session_state.db_manager = DatabaseManager(db_type="supabase")
    if "question_input" not in st.session_state:
        st.session_state.question_input = ""
    if "want_analysis" not in st.session_state:
        st.session_state.want_analysis = False


def add_chat_entry(entry):
    st.session_state.chat_history.append(entry)


# -------------------------------------------------
# FORMATEADORES GENERALES
# -------------------------------------------------

def fmt_money(x):
    """Formato dinero: 1.234,56"""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "0,00"
    try:
        base = f"{float(x):,.2f}"
        return (
            base.replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
        )
    except Exception:
        return str(x)


def fmt_int(x):
    """Entero con separador de miles: 1.234"""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "0"
    try:
        n = int(round(float(x)))
        base = f"{n:,}"
        return base.replace(",", ".")
    except Exception:
        return str(x)


def fmt_generic(x):
    """Genérico numérico con 2 decimales en formato ES."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    try:
        base = f"{float(x):,.2f}"
        return (
            base.replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
        )
    except Exception:
        return str(x)


# -------------------------------------------------
# MOSTRAR UNA ENTRADA DEL CHAT (PREGUNTA + RESULTADO)
# -------------------------------------------------

def display_chat_entry(entry, entry_index=0):
    st.write(f"**Pregunta:** {entry['question']}")
    st.write(f"**Respuesta:** {entry['answer']}")

    if entry.get("analysis"):
        st.markdown("🧠 **Análisis:**")
        st.write(entry["analysis"])

    # Consulta SQL: mostrarla opcionalmente con un checkbox
    if entry.get("sql_query"):
        show_sql = st.checkbox(
            "🔍 Mostrar consulta SQL generada",
            key=f"show_sql_{entry_index}",
        )
        if show_sql:
            st.code(entry["sql_query"], language="sql")

    # Resultados de la consulta
    if entry.get("sql_result") is not None:
        st.markdown("📊 **Resultados de la consulta:**")
        # Trabajamos con una copia para no romper el historial
        df = entry["sql_result"].copy()

        # 🔧 Arreglo: algunas columnas de fecha llegan como enteros enormes (epoch en ns)
        for c in df.columns:
            col_name = c.lower()
            if ("fecha" in col_name or "mes" in col_name) and is_integer_dtype(df[c]):
                s = df[c].dropna()
                if not s.empty and s.abs().max() > 10**10:
                    try:
                        df[c] = pd.to_datetime(df[c], unit="ns")
                    except Exception:
                        pass

        # -------------------------------------------------
        # CONVERSIÓN DE NÚMEROS (por si vienen como texto)
        # -------------------------------------------------
        for c in df.columns:
            if df[c].dtype == object:
                s = df[c].astype(str)
                cleaned = (
                    s.str.replace(".", "", regex=False)
                     .str.replace(",", ".", regex=False)
                )
                converted = pd.to_numeric(cleaned, errors="coerce")
                if not converted.isna().all():
                    df[c] = converted

        # -------------------------------------------------
        # PREPARAR DF DE DISPLAY (fechas bonitas + formato ES)
        # -------------------------------------------------
        df_display = df.copy()

        meses_es = {
            1: "enero",
            2: "febrero",
            3: "marzo",
            4: "abril",
            5: "mayo",
            6: "junio",
            7: "julio",
            8: "agosto",
            9: "septiembre",
            10: "octubre",
            11: "noviembre",
            12: "diciembre",
        }

        # Fechas → "enero 2025", etc.
        for c in df_display.columns:
            if pd.api.types.is_datetime64_any_dtype(df_display[c]):
                serie = df_display[c]
                meses = serie.dt.month.map(meses_es)
                anyos = serie.dt.year.astype(str)
                df_display[c] = meses + " " + anyos

        numeric_cols_all = [
            c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
        ]

        # -------------------------------------------------
        # CLASIFICACIÓN DE COLUMNAS NUMÉRICAS Y FORMATOS
        # -------------------------------------------------
        money_patterns = [
            "importe", "total", "factur", "precio", "coste", "costo",
            "margen", "base_imponible", "iva", "bruto", "neto"
        ]
        count_patterns = [
            "unidades", "unidad", "cantidad", "libros", "ejemplares",
            "n_pedidos", "num_pedidos", "n_clientes", "num_clientes",
            "numero", "número", "n_"
        ]
        id_patterns = [
            "id", "id_", "_id", "clienteid", "pedidoid",
            "codigo", "código", "cod_", "pk_", "dni", "nif"
        ]

        money_cols = []
        count_cols = []
        id_cols = []
        other_cols = []

        for c in numeric_cols_all:
            cl = c.lower()
            if any(p in cl for p in id_patterns):
                id_cols.append(c)
            elif any(p in cl for p in count_patterns):
                count_cols.append(c)
            elif any(p in cl for p in money_patterns):
                money_cols.append(c)
            else:
                other_cols.append(c)

        def fmt_money_local(x):
            if pd.isna(x):
                return ""
            return fmt_money(x)

        def fmt_int_local(x):
            if pd.isna(x):
                return ""
            return fmt_int(x)

        def fmt_generic_local(x):
            if pd.isna(x):
                return ""
            return fmt_generic(x)

        if numeric_cols_all:
            fmt_dict = {}
            for c in money_cols:
                fmt_dict[c] = fmt_money_local
            # cantidades e IDs como enteros
            for c in count_cols + id_cols:
                fmt_dict[c] = fmt_int_local
            for c in other_cols:
                fmt_dict[c] = fmt_generic_local

            styler = df_display.style.format(fmt_dict)
            st.dataframe(styler, width="stretch")
        else:
            st.dataframe(df_display, width="stretch")

        # -------------------------------------------------
        # MINI DASHBOARD (KPIs)
        # -------------------------------------------------
        has_factura_context = any("factura" in c.lower() for c in df.columns)

        if has_factura_context and numeric_cols_all:
            total_fact = None
            num_fact = None

            for c in numeric_cols_all:
                cname = c.lower()
                if any(k in cname for k in ["facturadoconiva", "importe", "total"]):
                    try:
                        total_fact = df[c].sum()
                    except Exception:
                        pass
                if any(k in cname for k in ["numfacturas", "facturas"]):
                    try:
                        num_fact = df[c].sum()
                    except Exception:
                        pass

            if total_fact is not None:
                kpi_cols = st.columns(3)
                kpi_cols[0].metric(
                    "💶 Total facturado",
                    fmt_money(total_fact) + " €",
                )
                if num_fact is not None and num_fact > 0:
                    kpi_cols[1].metric(
                        "🧾 Nº facturas",
                        fmt_int(num_fact),
                    )
                    ticket_medio = total_fact / num_fact
                    kpi_cols[2].metric(
                        "📊 Ticket medio",
                        fmt_money(ticket_medio) + " €",
                    )
        else:
            if numeric_cols_all:
                kpi_cols = st.columns(min(3, len(numeric_cols_all)))
                for i, c in enumerate(numeric_cols_all[:3]):
                    total = df[c].sum()
                    cname_pretty = c.replace("_", " ").capitalize()
                    clower = c.lower()

                    es_dinero = any(
                        k in clower
                        for k in ["importe", "precio", "coste", "costo", "margen", "iva", "total", "factur"]
                    )
                    es_contador = any(
                        k in clower
                        for k in count_patterns + id_patterns
                    )

                    if es_dinero:
                        value_str = fmt_money(total) + " €"
                    elif es_contador:
                        value_str = fmt_int(total)
                    else:
                        if float(total).is_integer():
                            value_str = fmt_int(total)
                        else:
                            value_str = fmt_generic(total)

                    kpi_cols[i].metric(f"Total {cname_pretty}", value_str)

        # -------------------------------------------------
        # SELECTORES PARA GRÁFICOS
        # -------------------------------------------------
        numeric_cols = [
            c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
        ]
        temporal_col = None
        for c in df.columns:
            if any(
                k in c.lower()
                for k in ["fecha", "emitida", "periodo", "mes", "año", "anio", "dia"]
            ):
                temporal_col = c
                break

        st.markdown("### 📈 Configuración de gráfico")
        if len(df.columns) > 1 and numeric_cols:
            default_x_index = (
                df.columns.get_loc(temporal_col)
                if temporal_col in df.columns
                else 0
            )
            x_col = st.selectbox(
                "Eje X:",
                df.columns,
                index=default_x_index,
                key=f"xcol_{entry_index}",
            )
            y_col = st.selectbox(
                "Eje Y (primaria):",
                numeric_cols,
                key=f"ycol1_{entry_index}",
            )
            y2_col = st.selectbox(
                "Eje Y (secundaria, opcional):",
                ["(ninguna)"] + numeric_cols,
                index=0,
                key=f"ycol2_{entry_index}",
            )

            chart_type = st.radio(
                "Tipo de gráfico:",
                ["Auto", "Líneas", "Barras", "Barras horizontales", "Sectores"],
                horizontal=True,
                key=f"charttype_{entry_index}",
            )

            # Lógica "Auto"
            if chart_type == "Auto":
                lower_x = x_col.lower()
                n_cat = df[x_col].nunique()
                if any(k in lower_x for k in ["fecha", "mes", "dia", "año", "anio"]):
                    chart_type = "Líneas"
                elif n_cat > 10:
                    # Muchas categorías: ranking → barras horizontales
                    chart_type = "Barras horizontales"
                elif n_cat <= 10:
                    # Pocas categorías: sectores puede tener sentido
                    chart_type = "Sectores"
                else:
                    chart_type = "Barras"

            try:
                if chart_type == "Líneas":
                    fig = px.line(
                        df,
                        x=x_col,
                        y=y_col,
                        markers=True,
                        title=f"{y_col} por {x_col}",
                    )
                    if y2_col != "(ninguna)":
                        fig.add_scatter(
                            x=df[x_col],
                            y=df[y2_col],
                            mode="lines+markers",
                            name=y2_col,
                            yaxis="y2",
                        )
                        fig.update_layout(
                            yaxis2=dict(
                                title=y2_col,
                                overlaying="y",
                                side="right",
                            )
                        )

                elif chart_type == "Barras":
                    if y2_col != "(ninguna)":
                        fig = px.bar(
                            df,
                            x=x_col,
                            y=[y_col, y2_col],
                            barmode="group",
                            title=f"{y_col} y {y2_col} por {x_col}",
                        )
                    else:
                        fig = px.bar(
                            df,
                            x=x_col,
                            y=y_col,
                            title=f"{y_col} por {x_col}",
                        )
                    # Etiquetas encima de las barras
                    fig.update_traces(
                        texttemplate="%{y:.0f}",
                        textposition="outside",
                        hovertemplate=f"{x_col}: %{{x}}<br>{y_col}: %{{y:.2f}}",
                    )

                elif chart_type == "Barras horizontales":
                    fig = px.bar(
                        df,
                        x=y_col,   # importe / valor
                        y=x_col,   # categorías (clientes, productos...)
                        orientation="h",
                        title=f"{y_col} por {x_col}",
                    )
                    # Ordenar de menor a mayor (ranking)
                    fig.update_layout(yaxis={"categoryorder": "total ascending"})
                    fig.update_traces(
                        texttemplate="%{x:.0f}",
                        textposition="outside",
                        hovertemplate=f"{x_col}: %{{y}}<br>{y_col}: %{{x:.2f}}",
                    )

                elif chart_type == "Sectores":
                    fig = px.pie(
                        df,
                        names=x_col,
                        values=y_col,
                        title=f"Distribución de {y_col} por {x_col}",
                    )

                st.plotly_chart(fig, width="stretch")

            except Exception as e:
                st.warning(f"No se pudo generar gráfico: {e}")
        else:
            st.info("No hay suficientes columnas numéricas para generar un gráfico.")


# --------- callback para el botón "Nueva consulta" ---------

def clear_query():
    """Deja la caja de consulta y el checkbox en blanco."""
    st.session_state["question_input"] = ""
    st.session_state["want_analysis"] = False


# -------------------------------------------------
# TABLERO CEO
# -------------------------------------------------

def dashboard_ceo():
    st.subheader("📊 Tablero CEO - Visión general de ventas")

    db = st.session_state.db_manager

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_ini = st.date_input("Desde", value=pd.to_datetime("2025-01-01"))
    with col_f2:
        fecha_fin = st.date_input("Hasta", value=pd.to_datetime("2025-12-31"))

    # Consulta 1: facturación y número de facturas en el periodo
    sql_resumen = f"""
        SELECT
            COUNT(*) AS num_facturas,
            SUM(total_declarado) AS total_importe
        FROM factura
        WHERE fecha_emision >= '{fecha_ini}'
          AND fecha_emision <  '{fecha_fin}'
    """
    df_resumen = db.execute_query(sql_resumen)

    # Consulta 2: facturación mensual
    sql_mensual = f"""
        SELECT
            DATE_TRUNC('month', fecha_emision) AS mes,
            SUM(total_declarado) AS total_importe
        FROM factura
        WHERE fecha_emision >= '{fecha_ini}'
          AND fecha_emision <  '{fecha_fin}'
        GROUP BY DATE_TRUNC('month', fecha_emision)
        ORDER BY mes;
    """
    df_mensual = db.execute_query(sql_mensual)

    # Consulta 3: top 10 clientes por facturación
    sql_top_clientes = f"""
        SELECT
            c.razon_social AS cliente,
            SUM(f.total_declarado) AS total_importe
        FROM factura f
        JOIN cliente c ON f.clienteid = c.clienteid
        WHERE f.fecha_emision >= '{fecha_ini}'
          AND f.fecha_emision <  '{fecha_fin}'
        GROUP BY c.razon_social
        ORDER BY total_importe DESC
        LIMIT 10;
    """
    df_top = db.execute_query(sql_top_clientes)

    # ---------- KPIs ----------
    if not df_resumen.empty:
        total_importe = df_resumen["total_importe"].iloc[0] or 0
        num_facturas = df_resumen["num_facturas"].iloc[0] or 0
        ticket_medio = total_importe / num_facturas if num_facturas else 0

        k1, k2, k3 = st.columns(3)
        k1.metric("💶 Total facturado", fmt_money(total_importe) + " €")
        k2.metric("🧾 Nº facturas", fmt_int(num_facturas))
        k3.metric("🎫 Ticket medio", fmt_money(ticket_medio) + " €")
    else:
        st.info("No hay facturas en el periodo seleccionado.")

    st.markdown("---")

    # ---------- Gráfico facturación mensual ----------
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("#### Facturación por mes")
        if not df_mensual.empty:
            df_m = df_mensual.copy()
            df_m["mes"] = pd.to_datetime(df_m["mes"])
            df_m["mes_label"] = df_m["mes"].dt.strftime("%b %Y")  # Ene 2025, etc.

            fig = px.bar(
                df_m,
                x="mes_label",
                y="total_importe",
                labels={"mes_label": "Mes", "total_importe": "Importe"},
            )
            fig.update_traces(
                texttemplate="%{y:.0f}",
                textposition="outside",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Sin datos mensuales en el rango elegido.")

    # ---------- Gráfico top 10 clientes ----------
    with col_g2:
        st.markdown("#### Top 10 clientes por facturación")
        if not df_top.empty:
            df_t = df_top.copy()
            fig2 = px.bar(
                df_t,
                x="total_importe",
                y="cliente",
                orientation="h",
                labels={"total_importe": "Importe", "cliente": "Cliente"},
            )
            fig2.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig2, width="stretch")
        else:
            st.info("No se han encontrado clientes en el periodo.")


# -------------------------------------------------
# MAIN
# -------------------------------------------------

def main():
    st.set_page_config(
        page_title="Kika - Pregunta a tu base de datos",
        layout="wide",
    )

    # Cargamos logos en base64
    orbe_b64 = load_image_base64("logo_orbe.png")
    entenova_b64 = load_image_base64("logo_entenova.jpg")

    orbe_tag = (
        f'<img src="data:image/png;base64,{orbe_b64}" alt="Orbe logo">'
        if orbe_b64
        else "<div style='font-size:2rem;font-weight:700;'>Orbe</div>"
    )
    entenova_tag = (
        f'<img src="data:image/jpeg;base64,{entenova_b64}" alt="EnteNova Gnosis">'
        if entenova_b64
        else "<div>EnteNova Gnosis</div>"
    )

    # -------------------------------------------------
    # CSS GLOBAL PARA LOOK "HERO"
    # -------------------------------------------------
    st.markdown(
        """
<style>
.stApp {
    background: #f5f7fb;
}

.hero-kika {
    position: relative;
    margin: -3rem -3rem 2rem -3rem;
    padding: 3rem 4rem 4.5rem 4rem;
    background: linear-gradient(120deg, #facc15, #8b5cf6);
    color: #ffffff;
    border-bottom-left-radius: 32px;
    border-bottom-right-radius: 32px;
    box-shadow: 0 14px 40px rgba(15, 23, 42, 0.35);
}

.hero-grid {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 2.5rem;
}

.hero-orbe img {
    max-height: 80px;
}

.hero-erp {
    font-size: 1.05rem;
    font-weight: 600;
    margin-top: 0.4rem;
    letter-spacing: 0.08em;
}

.hero-center {
    align-self: center;
}

.hero-title-row {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    margin-bottom: 0.25rem;
}

.hero-kika-icon {
    font-size: 3rem;
}

.hero-title {
    font-size: 2.5rem;
    font-weight: 800;
    line-height: 1.1;
}

.hero-subtitle {
    font-size: 0.95rem;
    opacity: 0.92;
    margin-top: 0.35rem;
}

.hero-dev-card {
    background: rgba(255,255,255,0.96);
    color: #0f172a;
    padding: 1rem 1.6rem;
    border-radius: 18px;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.35);
    text-align: center;
    font-size: 0.85rem;
}

.hero-dev-card img {
    max-height: 40px;
    margin-top: 0.25rem;
}

/* Formulario como tarjeta flotante, ancho y centrado */
div[data-testid="stForm"] {
    background: #ffffff;
    margin-top: 0.75rem;
    margin-bottom: 1.5rem;
    padding: 1.5rem 1.75rem 1.25rem 1.75rem;
    border-radius: 18px;
    box-shadow: 0 14px 40px rgba(15, 23, 42, 0.18);
    width: 100%;
}



/* Botones redondeados */
.stButton>button {
    border-radius: 999px;
    padding: 0.4rem 1.2rem;
    border: none;
    background: #00b8b5;
    color: #ffffff;
    font-weight: 600;
    font-size: 0.95rem;
}

.stButton>button:hover {
    background: #019896;
}

/* Checkbox ajustado */
label[for^="want_analysis"] div:nth-child(2) {
    line-height: 1.1;
}
</style>
""",
        unsafe_allow_html=True,
    )

    # -------------------------------------------------
    # HERO CON LOGOS Y TÍTULO
    # -------------------------------------------------
    st.markdown(
        f"""
<div class="hero-kika">
  <div class="hero-grid">
    <div class="hero-orbe">
      {orbe_tag}
      <div class="hero-erp">ERP - CRM</div>
    </div>
    <div class="hero-center">
      <div class="hero-title-row">
        <div class="hero-kika-icon">🤖</div>
        <div class="hero-title">Kika - Pregunta a<br>tu base de datos</div>
      </div>
      <div class="hero-subtitle">
        Pregunta en lenguaje natural y deja que Kika genere la consulta SQL,<br>
        ejecute el análisis y te muestre los resultados listos para decidir.
      </div>
    </div>
    <div class="hero-right">
      <div class="hero-dev-card">
        <div>Desarrollado por:</div>
        {entenova_tag}
      </div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    init_session_state()
    db = st.session_state.db_manager

    # ---- Pestañas: chat de Kika y tablero CEO ----
    tab_chat, tab_ceo = st.tabs(["🧠 Kika (chat)", "📊 Tablero CEO"])

    # =====================
    #  TAB KIKA (CHAT)
    # =====================
    with tab_chat:
        # FORMULARIO DE CONSULTA
        with st.form("consulta_form"):
            c1, c2, c3 = st.columns([5, 1, 1])
            with c1:
                question = st.text_input(
                    "Escribe tu pregunta en español:",
                    key="question_input",
                )
            with c2:
                want_analysis = st.checkbox(
                    "Pedir\nanálisis",
                    value=st.session_state.get("want_analysis", False),
                    key="want_analysis",
                )
            with c3:
                submitted = st.form_submit_button("Preguntar")
                st.form_submit_button(
                    "Nueva consulta",
                    on_click=clear_query,
                )

        # Procesar envío
        if submitted and question:
            with st.spinner("Generando consulta SQL..."):
                schema = db.get_schema()
                sql_query = generate_sql_query(question, schema)

                try:
                    sql_result = db.execute_query(sql_query) if sql_query else None
                except Exception as e:
                    error_msg = str(e)

                    # Intento de reparación automática
                    repaired_sql = repair_sql_query(question, schema, sql_query, error_msg)

                    if repaired_sql and repaired_sql != sql_query:
                        try:
                            sql_query = repaired_sql  # usamos la consulta corregida
                            sql_result = db.execute_query(sql_query)
                        except Exception as e2:
                            sql_result = pd.DataFrame(
                                {
                                    "Error": [str(e2)],
                                    "SQL_generada": [sql_query],
                                }
                            )
                    else:
                        sql_result = pd.DataFrame(
                            {
                                "Error": [error_msg],
                                "SQL_generada": [sql_query],
                            }
                        )


                answer = generate_response(question, sql_result, sql_query)

                qlow = question.lower()
                analysis_intent = any(
                    k in qlow for k in ["analiza", "interpreta", "comenta"]
                )

                analysis_text = None
                if (
                    (want_analysis or analysis_intent)
                    and sql_result is not None
                    and not sql_result.empty
                ):
                    with st.spinner("Analizando resultados..."):
                        analysis_text = generate_analysis_response(
                            question, sql_result
                        )

                entry = {
                    "question": question,
                    "answer": answer,
                    "sql_query": sql_query,
                    "sql_result": sql_result,
                }
                if analysis_text:
                    entry["analysis"] = analysis_text
                add_chat_entry(entry)

        st.markdown("---")
        st.subheader("Historial de consultas")

        for i, entry in enumerate(reversed(st.session_state.chat_history)):
            titulo = entry["question"]
            if len(titulo) > 50:
                titulo = f"{titulo[:50]}..."
            with st.expander(f"🔍 {titulo}", expanded=(i == 0)):
                display_chat_entry(entry, i)

    # =====================
    #  TAB TABLERO CEO
    # =====================
    with tab_ceo:
        dashboard_ceo()


if __name__ == "__main__":
    main()
