import os
import re
from datetime import timedelta

import numpy as np
import pandas as pd
from openai import OpenAI
from sklearn.linear_model import LinearRegression

# Cliente OpenAI (usa la API key del entorno)
from .settings import client


# ============================================================
# Utilidades para generación y limpieza de SQL
# ============================================================

def _extract_sql_only(text: str) -> str:
    """
    Extrae la PRIMERA sentencia SELECT que aparezca en el texto.
    Soporta respuestas con bloques ```sql``` o con texto alrededor.
    """
    # 1) Intentar primero con bloque ```sql ... ```
    fenced_blocks = re.findall(r"```(?:sql)?\s*(.*?)```", text, flags=re.I | re.S)
    if fenced_blocks:
        candidate = fenced_blocks[0].strip()
        # Si dentro del bloque hay texto antes del SELECT, lo recortamos
        m = re.search(r"\bSELECT\b", candidate, flags=re.I)
        if m:
            candidate = candidate[m.start():].strip()
        # Nos quedamos solo hasta el primer ';' si existe
        sc = candidate.find(";")
        if sc != -1:
            candidate = candidate[: sc + 1]
        return candidate.strip()

    # 2) Sin bloque: buscar primer SELECT en todo el texto
    m = re.search(r"\bSELECT\b", text, flags=re.I)
    if m:
        candidate = text[m.start():].strip()
        sc = candidate.find(";")
        if sc != -1:
            candidate = candidate[: sc + 1]
        return candidate.strip()

    # 3) Fallback: devolver el texto tal cual recortado
    return text.strip()


def _ensure_limit(sql: str, default_limit: int = 1000) -> str:
    """
    Asegura que la consulta tiene un LIMIT. Si ya existe, no hace nada.
    No pretende ser un parser SQL completo, solo un safeguard básico.
    """
    if re.search(r"\bLIMIT\b", sql, flags=re.I):
        return sql

    stripped = sql.strip()
    has_semicolon = stripped.endswith(";")
    if has_semicolon:
        stripped = stripped[:-1].rstrip()

    limited = f"{stripped} LIMIT {default_limit}"
    if has_semicolon:
        limited += ";"
    else:
        limited += ";"
    return limited


def generate_sql_query(question: str, schema: pd.DataFrame) -> str:
    """
    Recibe una pregunta en lenguaje natural y un esquema de BD en DataFrame
    (con columnas table_name, column_name, data_type) y devuelve una sentencia
    SELECT de PostgreSQL lo más segura posible.
    """
    # Convertimos el esquema en un texto legible para el modelo
    if (
        isinstance(schema, pd.DataFrame)
        and {"table_name", "column_name", "data_type"} <= set(schema.columns)
    ):
        schema_text = "\n".join(
            f"- {row.table_name}.{row.column_name} ({row.data_type})"
            for _, row in schema.iterrows()
        )
    else:
        schema_text = str(schema)

    prompt = (
        "Convierte la siguiente pregunta en una consulta de PostgreSQL usando SOLO SELECT.\n"
        "REGLAS:\n"
        "- Prohibido usar INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, GRANT, EXEC.\n"
        "- Usa exclusivamente las tablas y columnas listadas en el esquema.\n"
        "- No inventes nombres de tablas ni de columnas.\n"
        "- Si esperas muchas filas, añade un LIMIT razonable.\n"
        "Devuelve ÚNICAMENTE la consulta SQL en texto plano, sin explicaciones, sin comentarios,\n"
        "sin prefijos ni sufijos y sin bloques ```.\n\n"
        "Esquema disponible:\n"
        f"{schema_text}\n\n"
        f"Pregunta del usuario: {question}\n"
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,    # máximo determinismo
        top_p=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un experto en SQL para PostgreSQL. "
                    "Respondes SIEMPRE con una sola sentencia SELECT válida."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    raw = resp.choices[0].message.content.strip()
    sql = _extract_sql_only(raw)

    # Saneado: aseguramos que empieza por SELECT
    if not re.match(r"^\s*SELECT\b", sql, flags=re.I):
        # Último intento buscando un SELECT dentro del texto crudo
        m = re.search(r"\bSELECT\b.*", raw, flags=re.I | re.S)
        if m:
            sql = m.group(0).strip()

    # Borramos cualquier rastro de verbos peligrosos, por si se ha colado algo
    forbidden_pattern = re.compile(
        r"\b(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|GRANT|EXEC)\b",
        flags=re.I,
    )
    if forbidden_pattern.search(sql):
        # Nos quedamos solo con lo que siga al primer SELECT
        m = re.search(r"\bSELECT\b.*", sql, flags=re.I | re.S)
        if m:
            sql = m.group(0).strip()

    if not re.match(r"^\s*SELECT\b", sql, flags=re.I):
        raise ValueError(
            "No se ha podido generar una consulta SQL segura a partir de la pregunta."
        )

    # Añadimos LIMIT si no lo hay
    sql = _ensure_limit(sql)

    return sql


# ============================================================
# Respuesta en lenguaje natural a partir del resultado SQL
# ============================================================

def generate_response(question: str, sql_result: pd.DataFrame, sql_query: str) -> str:
    """
    Recibe la pregunta original, el DataFrame con resultados y la SQL,
    y genera una respuesta breve en castellano.
    """
    if sql_result is None or sql_result.empty:
        return "No se encontraron resultados para tu consulta."

    result_text = sql_result.head(50).to_string(index=False)

    prompt = (
        "Te paso una consulta SQL, la pregunta del usuario y una muestra de los resultados.\n"
        "Redacta una respuesta BREVE en español (2 a 4 frases) que explique lo esencial,\n"
        "sin listar fila por fila ni repetir toda la tabla.\n"
        "Puedes mencionar que es una muestra de datos si lo consideras útil.\n\n"
        f"Pregunta original: {question}\n"
        f"Consulta SQL:\n{sql_query}\n\n"
        f"Resultados (muestra hasta 50 filas):\n{result_text}\n"
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un asistente experto en análisis de datos. "
                    "Explicas de forma clara, directa y sin relleno."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    return resp.choices[0].message.content.strip()


# ============================================================
# Inteligencia y análisis extendido de resultados
# ============================================================

def _infer_series(df: pd.DataFrame):
    """
    Intenta deducir una columna temporal y una o varias columnas numéricas
    interesantes para el análisis.
    """
    cols = list(df.columns)

    # Candidatas temporales por nombre
    temporal_candidates = [
        c
        for c in cols
        if any(
            k in c.lower()
            for k in ["fecha", "mes", "anio", "año", "emitida", "period", "dia", "día"]
        )
    ]
    temporal_col = temporal_candidates[0] if temporal_candidates else None

    # Columnas numéricas
    numeric_all = [
        c for c in cols if np.issubdtype(df[c].dtype, np.number)
    ]

    # Priorizamos nombres típicos de importe / cantidades
    priority_keywords = [
        "importe",
        "total",
        "monto",
        "factur",
        "cantidad",
        "unidades",
        "precio",
        "coste",
        "costo",
    ]
    numeric_priority = [
        c
        for c in numeric_all
        if any(k in c.lower() for k in priority_keywords)
    ]

    if numeric_priority:
        numeric_cols = numeric_priority
    else:
        numeric_cols = numeric_all

    return temporal_col, numeric_cols


def synthesize_metrics(df: pd.DataFrame) -> dict:
    """
    Calcula un conjunto de métricas básicas y, si es posible, una pequeña
    proyección temporal.
    """
    out: dict = {}
    temporal_col, numeric_cols = _infer_series(df)

    out["temporal_col"] = temporal_col
    out["numeric_cols"] = numeric_cols

    # --- Métricas sobre la columna numérica principal ---
    if numeric_cols:
        main_col = numeric_cols[0]
        serie = df[main_col].dropna().astype(float)
        if not serie.empty:
            out["main_metric"] = main_col
            out["sum"] = float(serie.sum())
            out["mean"] = float(serie.mean())
            out["min"] = float(serie.min())
            out["max"] = float(serie.max())
            out["count"] = int(serie.count())

            # Último valor y comparación con el anterior
            out["last_value"] = float(serie.iloc[-1])
            if len(serie) > 1:
                prev = float(serie.iloc[-2])
                out["prev_value"] = prev
                if prev != 0:
                    out["pct_change_last"] = float(
                        (serie.iloc[-1] - prev) / prev * 100
                    )

            # Outliers simples: ±2 desviaciones típicas
            mean = serie.mean()
            std = serie.std(ddof=0) if serie.std(ddof=0) != 0 else None
            if std is not None and not np.isnan(std) and std > 0:
                outlier_mask = (serie > mean + 2 * std) | (serie < mean - 2 * std)
                outliers = serie[outlier_mask]
                if not outliers.empty:
                    # Guardamos solo unos pocos para contexto
                    out["outliers"] = [
                        {"index": int(idx), "value": float(val)}
                        for idx, val in outliers.head(10).items()
                    ]

            # Contribución porcentual
            total = serie.sum()
            if total != 0:
                contrib = (serie / total) * 100
                contrib_sorted = contrib.sort_values(ascending=False)
                cumulative = contrib_sorted.cumsum()
                out["concentration_over_50pct"] = bool(
                    (cumulative <= 50).sum() < len(contrib_sorted)
                )

    # --- Forecast sencillo si hay columna temporal y métrica principal ---
    if temporal_col and numeric_cols:
        try:
            main_col = numeric_cols[0]
            df2 = df[[temporal_col, main_col]].dropna().copy()

            # Intentar parsear a datetime
            if not pd.api.types.is_datetime64_any_dtype(df2[temporal_col]):
                df2[temporal_col] = pd.to_datetime(
                    df2[temporal_col], errors="coerce"
                )
            df2 = df2.dropna(subset=[temporal_col, main_col])
            if len(df2) >= 5:
                df2 = df2.sort_values(temporal_col)
                df2 = df2.drop_duplicates(subset=[temporal_col])

                # X: índice temporal como 0, 1, 2, ...
                df2["t"] = range(len(df2))
                X = df2[["t"]].values
                y = df2[main_col].astype(float).values

                model = LinearRegression()
                model.fit(X, y)

                last_t = df2["t"].iloc[-1]
                last_date = df2[temporal_col].iloc[-1]

                # Heurística muy simple para el "paso" temporal
                if len(df2) >= 2:
                    delta = df2[temporal_col].iloc[-1] - df2[temporal_col].iloc[-2]
                    if delta.days >= 25:
                        step = "M"  # mensual aproximado
                    elif delta.days >= 5:
                        step = "W"  # semanal aproximado
                    else:
                        step = "D"  # diario
                else:
                    step = "D"

                future_points = 3
                future_t = np.array(
                    [[last_t + i] for i in range(1, future_points + 1)]
                )
                y_pred = model.predict(future_t)

                future_dates = []
                current = last_date
                for _ in range(future_points):
                    if step == "M":
                        # sumamos ~30 días como aproximación mensual
                        current = current + timedelta(days=30)
                    elif step == "W":
                        current = current + timedelta(weeks=1)
                    else:
                        current = current + timedelta(days=1)
                    future_dates.append(current)

                out["forecast"] = [
                    {
                        "date": d.strftime("%Y-%m-%d"),
                        "value": float(val),
                    }
                    for d, val in zip(future_dates, y_pred)
                ]

        except Exception:
            # Si algo falla en el forecast, simplemente no lo añadimos
            pass

    return out


def generate_analysis_response(question: str, sql_result: pd.DataFrame) -> str:
    """
    Genera un análisis más elaborado a partir de un DataFrame de resultados:
    tendencias, outliers, concentración y, si existe, forecast.
    """
    if sql_result is None or sql_result.empty:
        return "No hay datos para analizar."

    metrics = synthesize_metrics(sql_result)
    head_limited = sql_result.head(50).to_string(index=False)

    prompt = (
        "Actúa como analista de datos senior en un contexto de negocio.\n"
        "Te paso la pregunta del usuario, un conjunto de métricas calculadas y una "
        "muestra de los datos (hasta 50 filas).\n\n"
        "Tareas:\n"
        "- Describe las tendencias principales de la métrica numérica principal (si existe).\n"
        "- Comenta si hay valores atípicos (outliers) y qué podrían significar.\n"
        "- Indica si parece haber concentración de riesgo o de facturación en pocos elementos.\n"
        "- Si hay forecast disponible, coméntalo como proyección de los próximos periodos.\n"
        "- No repitas toda la tabla ni enumeres fila por fila. Céntrate en ideas clave.\n"
        "- Redacta en 3 a 6 párrafos, en español, con tono ejecutivo pero claro.\n\n"
        f"Pregunta del usuario:\n{question}\n\n"
        f"Métricas (JSON):\n{metrics}\n\n"
        f"Muestra de datos:\n{head_limited}\n"
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un analista de negocio experto. Sé conciso, práctico y evita el relleno."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    return resp.choices[0].message.content.strip()
