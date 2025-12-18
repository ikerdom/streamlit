# ai_assistant.py

import os
import re
from datetime import timedelta

import numpy as np
import pandas as pd
from openai import OpenAI
from sklearn.linear_model import LinearRegression
from pandas.api.types import is_numeric_dtype   # <--- AÑADE ESTA LÍNEA
from datetime import timedelta


# ============================================================
# Cliente OpenAI (usa la API key del entorno)
# ============================================================
# ============================================================
# 🔥 FORZAMOS USO EXCLUSIVO DE LA API KEY DEL ERP
# ============================================================

API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

# Mostrar solo los primeros caracteres para debug seguro
print("🔍 OPENAI KEY QUE DATAQUERYBOT VA A USAR ->", API_KEY[:12] + "***")

if not API_KEY:
    raise RuntimeError("❌ ERROR CRÍTICO: DataQueryBot NO ha recibido OPENAI_API_KEY del ERP.")

# Crear cliente con ESA clave, ignorando cualquier otra del sistema
client = OpenAI(api_key=API_KEY)


SQL_MODEL = os.getenv("OPENAI_SQL_MODEL", "gpt-4o")
SUMMARY_MODEL = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4o")
ANALYSIS_MODEL = os.getenv("OPENAI_ANALYSIS_MODEL", "gpt-4o")


# ============================================================
# Utilidades para generación y limpieza de SQL
# ============================================================

def _schema_to_text(schema: pd.DataFrame) -> str:
    """
    Convierte el DataFrame de esquema (table_name, column_name, data_type)
    en un texto legible para el modelo.
    """
    if schema is None or schema.empty:
        return "No hay columnas disponibles."

    lines = []
    for _, row in schema.iterrows():
        table = row.get("table_name") or row.get("TABLE_NAME")
        col = row.get("column_name") or row.get("COLUMN_NAME")
        dtype = row.get("data_type") or row.get("DATA_TYPE")
        lines.append(f"- {table}.{col} ({dtype})")
    return "\n".join(lines)


def _extract_sql_only(raw: str) -> str:
    """
    Extrae SOLO la sentencia SQL de la respuesta del modelo.
    Admite:
      - Bloques ```sql ... ```
      - Texto con explicación + SELECT / WITH
    """
    if not raw:
        return ""

    text = raw.strip()

    # 1) Bloques ```sql ... ```
    code_block = re.search(r"```sql(.*?)```", text, flags=re.I | re.S)
    if code_block:
        sql = code_block.group(1).strip()
        return sql

    # 2) Bloques ``` ... ```
    code_block = re.search(r"```(.*?)```", text, flags=re.S)
    if code_block:
        sql = code_block.group(1).strip()
        return sql

    # 3) Buscar desde WITH o SELECT
    m = re.search(r"(WITH\b.*|SELECT\b.*)", text, flags=re.I | re.S)
    if m:
        sql = m.group(0).strip()
        return sql

    return text


def _ensure_limit(sql: str, default_limit: int = 1000) -> str:
    """
    Asegura que la consulta tiene LIMIT, pero sin cargarse consultas
    agregadas típicas (GROUP BY por mes/año, etc.).
    """
    if not sql:
        return sql

    # Si ya tiene LIMIT, no tocamos nada
    if re.search(r"\bLIMIT\b", sql, flags=re.I):
        return sql

    # Si es una consulta agregada con GROUP BY, normalmente no queremos
    # recortar arbitrariamente el número de filas (ej. 12 meses).
    if re.search(r"\bGROUP\s+BY\b", sql, flags=re.I):
        return sql

    # Si es una subconsulta terminada en ';', mantén el ';' al final
    stripped = sql.rstrip()
    has_semicolon = stripped.endswith(";")
    if has_semicolon:
        stripped = stripped[:-1].rstrip()

    sql_with_limit = f"{stripped} LIMIT {default_limit}"

    if has_semicolon:
        sql_with_limit += ";"

    return sql_with_limit


# ============================================================
# Generación de SQL a partir de lenguaje natural
# ============================================================

# ============================================================
# Generación de SQL a partir de lenguaje natural
# ============================================================

def generate_sql_query(question: str, schema: pd.DataFrame, default_limit: int = 1000) -> str:
    """
    Genera una consulta SQL (PostgreSQL) a partir de la pregunta del usuario
    y el esquema de la base de datos. Solo devuelve SELECT.
    """
    schema_text = _schema_to_text(schema)

    extra_rules = """
Reglas adicionales importantes:
- Si usas subconsultas con alias (por ejemplo: FROM (...) sub),
  en la parte EXTERIOR solo puedes usar las columnas definidas en el SELECT interno
  (por ejemplo: sub.columna o directamente el nombre de la columna si no pones alias de tabla).
  NO reutilices los alias de tablas internas (f., p., c., etc.) fuera de la subconsulta,
  porque eso genera errores de "missing FROM-clause entry" en PostgreSQL.

- Está TOTALMENTE PROHIBIDO generar instrucciones que no sean SELECT:
  no uses INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, GRANT, REVOKE,
  TRUNCATE, EXEC, CALL ni nada parecido.

- Usa únicamente las tablas y columnas que aparecen en el esquema.
  Si el usuario menciona un concepto de negocio ("cliente", "familia de producto"),
  intenta mapearlo a las columnas más probables sin inventar nombres nuevos.

- Si el usuario pide "los N más vendidos POR cada X" o "el más vendido de CADA X"
  (por ejemplo: por mes, por año, por familia, por cliente, por canal...),
  NO basta con ORDER BY + LIMIT global. En esos casos:

  1) Calcula un agregado por grupo (SUM, COUNT, etc.).
  2) Calcula un ranking dentro de cada grupo usando funciones de ventana como:
     ROW_NUMBER() OVER (PARTITION BY grupo ORDER BY medida DESC)
  3) Filtra por ese ranking (ej. WHERE rn = 1 para el top 1 por grupo,
     o WHERE rn <= N para top N por grupo).

- Para agrupar por meses o años en PostgreSQL, utiliza DATE_TRUNC:
    DATE_TRUNC('month', fecha) AS mes
    DATE_TRUNC('year', fecha)  AS anio

- Si el usuario pide "un registro por mes" o "todas las familias por año",
  asegúrate de que la consulta devuelve una fila por cada mes/año solicitado,
  no solo unas pocas filas recortadas por LIMIT global.
"""

    examples = """
Ejemplos de conversión (NO los ejecutes, solo úsalos como referencia de estilo):

Ejemplo 1
Pregunta: "La familia de producto más vendida en cada mes de 2025."
SQL correcta:

SELECT mes, familia, total_importe
FROM (
  SELECT
    DATE_TRUNC('month', p.fecha_pedido) AS mes,
    pf.nombre AS familia,
    SUM(pd.importe_total_linea) AS total_importe,
    ROW_NUMBER() OVER (
      PARTITION BY DATE_TRUNC('month', p.fecha_pedido)
      ORDER BY SUM(pd.importe_total_linea) DESC
    ) AS rn
  FROM pedido p
  JOIN pedido_detalle pd ON p.pedidoid = pd.pedidoid
  JOIN producto pr ON pd.productoid = pr.productoid
  JOIN producto_familia pf ON pr.familia_productoid = pf.familia_productoid
  WHERE p.fecha_pedido >= '2025-01-01'
    AND p.fecha_pedido <  '2026-01-01'
  GROUP BY DATE_TRUNC('month', p.fecha_pedido), pf.nombre
) sub
WHERE rn = 1
ORDER BY mes;

Ejemplo 2
Pregunta: "Importe total de ventas por año y familia de producto."
SQL correcta:

SELECT
  DATE_TRUNC('year', f.fecha_emision) AS anio,
  pf.nombre AS familia,
  SUM(f.total_declarado) AS total_ventas
FROM factura f
JOIN cliente c ON f.clienteid = c.clienteid
JOIN producto_familia pf ON f.familia_productoid = pf.familia_productoid
GROUP BY DATE_TRUNC('year', f.fecha_emision), pf.nombre
ORDER BY anio, total_ventas DESC;

Ejemplo 3
Pregunta: "Dime la facturación total en Aragón por cada mes en 2025."
SQL correcta:

SELECT
  DATE_TRUNC('month', f.fecha_emision) AS mes,
  SUM(f.total_declarado) AS facturacion_total
FROM factura f
JOIN cliente c          ON f.clienteid   = c.clienteid
JOIN cliente_direccion cd ON c.clienteid = cd.clienteid
JOIN postal_localidad pl  ON cd.postallocid = pl.postallocid
WHERE pl.regionid = (
    SELECT regionid FROM region WHERE nombre = 'Aragón'
)
  AND f.fecha_emision >= '2025-01-01'
  AND f.fecha_emision <  '2026-01-01'
GROUP BY DATE_TRUNC('month', f.fecha_emision)
ORDER BY mes;

"""

    system_content = (
        "Eres un experto en SQL para PostgreSQL. "
        "Tu trabajo es convertir preguntas en español sobre datos de negocio "
        "en UNA única sentencia SQL válida. "
        "Nunca ejecutes nada, solo genera la consulta."
    )

    prompt = (
        "Convierte la siguiente pregunta en una consulta SQL de PostgreSQL usando SOLO SELECT.\n\n"
        "Instrucciones generales:\n"
        "- Prohibido usar INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, TRUNCATE, GRANT, REVOKE, EXEC, CALL.\n"
        "- Usa exclusivamente las tablas y columnas listadas en el esquema.\n"
        "- No inventes nombres de tablas ni de columnas.\n"
        "- Si esperas muchas filas de detalle, puedes añadir un LIMIT razonable.\n"
        f"{extra_rules}\n\n"
        "Esquema disponible:\n"
        f"{schema_text}\n\n"
        "Ejemplos de estilo:\n"
        f"{examples}\n\n"
        f"Pregunta del usuario: {question}\n\n"
        "Devuelve ÚNICAMENTE la consulta SQL, sin explicaciones alrededor."
    )

    try:
        resp = client.chat.completions.create(
            model=SQL_MODEL,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as e:
        print(f"[ERROR OpenAI SQL] {e}")
        return ""

    raw = resp.choices[0].message.content or ""
    sql = _extract_sql_only(raw).strip()

    if not sql:
        return ""

    # Validación básica: debe empezar por SELECT, WITH o "("
    if not re.match(r"^\s*(SELECT|WITH|\()", sql, flags=re.I):
        m = re.search(r"(WITH\b.*|SELECT\b.*)", raw, flags=re.I | re.S)
        if m:
            sql = m.group(0).strip()
        else:
            return ""

    # Saneado: evitar verbos peligrosos
    forbidden = ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER",
                 "TRUNCATE", "GRANT", "REVOKE", "EXEC", "CALL"]
    upper_sql = sql.upper()
    if any(fb in upper_sql for fb in forbidden):
        m = re.search(r"(WITH\b.*|SELECT\b.*)", sql, flags=re.I | re.S)
        if m:
            sql = m.group(0).strip()
        else:
            return ""

    # Añadimos LIMIT solo si procede
    sql = _ensure_limit(sql, default_limit=default_limit)

    return sql


def repair_sql_query(question: str, schema: pd.DataFrame, bad_sql: str, error_message: str) -> str:
    """
    Intenta reparar una consulta SQL que ha fallado, usando el mensaje de error de la BD.
    """
    if not bad_sql:
        return ""

    schema_text = _schema_to_text(schema)

    system_content = (
        "Eres un experto en SQL para PostgreSQL. "
        "Tu tarea es corregir consultas SQL que dan error, "
        "usando el mensaje de error de la base de datos."
    )

    user_content = (
        "Tengo esta pregunta de negocio, una consulta SQL generada y un error de la base de datos.\n\n"
        f"Pregunta original del usuario:\n{question}\n\n"
        f"Esquema disponible (tablas y columnas):\n{schema_text}\n\n"
        f"Consulta SQL que ha fallado:\n{bad_sql}\n\n"
        f"Mensaje de error devuelto por la base de datos:\n{error_message}\n\n"
        "Corrige la consulta para que sea sintácticamente válida en PostgreSQL y coherente con la pregunta. "
        "Devuelve ÚNICAMENTE la nueva consulta SQL corregida, sin explicaciones alrededor."
    )

    try:
        resp = client.chat.completions.create(
            model=SQL_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )
        raw = resp.choices[0].message.content or ""
        sql = _extract_sql_only(raw).strip()
        return sql
    except Exception as e:
        print(f"[ERROR OpenAI SQL REPAIR] {e}")
        return ""


# ============================================================
# Resumen sencillo de resultados (para la parte "Respuesta")
# ============================================================

def generate_response(question: str, df: pd.DataFrame | None, sql_query: str | None) -> str:
    """
    Genera una respuesta corta en lenguaje natural a partir de la pregunta,
    la SQL generada y (opcionalmente) los primeros resultados.
    """
    if df is None:
        context_rows = "No se ha podido ejecutar la consulta o ha ocurrido un error."
    elif df.empty:
        context_rows = "La consulta se ha ejecutado correctamente pero no ha devuelto filas."
    else:
        # Nos quedamos con una vista muy resumida
        sample = df.head(10)
        context_rows = f"Primeras filas del resultado (máx 10):\n{sample.to_markdown(index=False)}"

    user_content = (
        f"Pregunta original del usuario:\n{question}\n\n"
        f"Consulta SQL ejecutada:\n{sql_query or '(no disponible)'}\n\n"
        f"Descripción del resultado:\n{context_rows}\n\n"
        "Redacta una respuesta breve en español (2–4 frases), "
        "explicando qué información se ha obtenido y cualquier aspecto relevante "
        "(por ejemplo, si no hay resultados, si parece que faltan datos, etc.). "
        "No incluyas la consulta SQL en la respuesta, solo una explicación amigable."
    )

    try:
        resp = client.chat.completions.create(
            model=SUMMARY_MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de negocio que explica resultados de consultas SQL "
                        "a usuarios no técnicos. Sé claro, directo y sin relleno."
                    ),
                },
                {"role": "user", "content": user_content},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR OpenAI SUMMARY] {e}")
        # Fallback simple
        if df is None:
            return "No he podido ejecutar la consulta ni analizar los resultados."
        if df.empty:
            return "La consulta se ha ejecutado correctamente, pero no hay datos que mostrar."
        return "He ejecutado la consulta y se han obtenido resultados. Revisa la tabla y los gráficos para más detalle."


# ============================================================
# Análisis enriquecido de resultados (KPIs, tendencias...)
# ============================================================

def _detect_temporal_column(df: pd.DataFrame) -> str | None:
    """
    Intenta detectar una columna temporal razonable.
    """
    date_like = [c for c in df.columns if "fecha" in c.lower() or "date" in c.lower() or "time" in c.lower()]
    for c in date_like:
        if np.issubdtype(df[c].dtype, np.datetime64):
            return c
    return None


def synthesize_metrics(df: pd.DataFrame) -> dict:
    """
    Extrae métricas básicas para apoyar el análisis automático:
    - columnas numéricas
    - columna temporal (si hay)
    - agregados principales sobre la COLUMNA DE NEGOCIO más relevante
    """
    if df is None or df.empty:
        return {"error": "no_data"}

    metrics: dict = {}

    # Intentar detectar columna temporal
    temporal_col = _detect_temporal_column(df)
    metrics["temporal_col"] = temporal_col

    # Detectar columnas numéricas (con intento de conversión)
    numeric_cols: list[str] = []
    for c in df.columns:
        serie = df[c]

        if is_numeric_dtype(serie):
            numeric_cols.append(c)
            continue

        # Intento de conversión, por si viene como texto "123,45"
        converted = pd.to_numeric(serie, errors="coerce")
        if not converted.isna().all():
            df[c] = converted
            numeric_cols.append(c)

    metrics["numeric_cols"] = numeric_cols

    if not numeric_cols:
        return metrics

    # 🔍 Elegir la "columna principal" de negocio:
    #    priorizamos columnas cuyo nombre sugiera importe / facturación / ventas
    prefer_patterns = [
        "factur",     # total_facturado, facturaconiva...
        "importe",
        "total",
        "venta",
        "ingres",
        "margen",
        "benef",
        "iva",
    ]

    main_col = numeric_cols[0]  # fallback
    for c in numeric_cols:
        cname = c.lower()
        if any(pat in cname for pat in prefer_patterns):
            main_col = c
            break

    metrics["main_numeric_col"] = main_col

    # A partir de aquí, todas las métricas se calculan sobre la columna principal
    serie = df[main_col].dropna().astype(float)
    if serie.empty:
        return metrics

    metrics["count"] = int(serie.count())
    metrics["sum"] = float(serie.sum())
    metrics["mean"] = float(serie.mean())
    metrics["min"] = float(serie.min())
    metrics["max"] = float(serie.max())
    metrics["std"] = float(serie.std()) if serie.count() > 1 else 0.0

    # Último valor / variación ordenando por fecha si hay columna temporal
    if temporal_col and temporal_col in df.columns:
        df_sorted = df.sort_values(temporal_col)
        serie_sorted = df_sorted[main_col].dropna().astype(float)
    else:
        serie_sorted = serie

    if serie_sorted.size >= 1:
        metrics["last_value"] = float(serie_sorted.iloc[-1])
    if serie_sorted.size >= 2:
        metrics["prev_value"] = float(serie_sorted.iloc[-2])
        metrics["delta"] = float(serie_sorted.iloc[-1] - serie_sorted.iloc[-2])

    # Outliers simples (±2 std)
    if metrics.get("std", 0) > 0:
        mean = metrics["mean"]
        std = metrics["std"]
        upper = mean + 2 * std
        lower = mean - 2 * std
        outlier_mask = (serie > upper) | (serie < lower)
        metrics["outliers_count"] = int(outlier_mask.sum())
    else:
        metrics["outliers_count"] = 0

    # Tendencia lineal si hay tiempo
    if temporal_col and temporal_col in df.columns and df[temporal_col].notna().sum() >= 3:
        try:
            df_ts = df[[temporal_col, main_col]].dropna()
            df_ts = df_ts.sort_values(temporal_col)
            t0 = df_ts[temporal_col].min()
            x = (df_ts[temporal_col] - t0) / timedelta(days=1)
            X = x.values.reshape(-1, 1)
            y = df_ts[main_col].astype(float).values

            model = LinearRegression()
            model.fit(X, y)
            slope = model.coef_[0]
            metrics["trend_slope_per_day"] = float(slope)
        except Exception:
            metrics["trend_slope_per_day"] = None
    else:
        metrics["trend_slope_per_day"] = None

    return metrics


def generate_analysis_response(question: str, sql_result: pd.DataFrame) -> str:
    """
    Genera un análisis en 3 bloques para dirección / área comercial:

    1. Resumen ejecutivo (máx. 5 líneas).
    2. Qué nos dicen los datos (lectura comercial).
    3. Qué haría ahora mismo (acciones recomendadas).
    """
    if sql_result is None or sql_result.empty:
        return "No hay datos para analizar."

    # Métricas técnicas de apoyo (no se muestran tal cual, solo para el modelo)
    metrics = synthesize_metrics(sql_result)
    head_limited = sql_result.head(50).to_string(index=False)

    prompt = (
        "Actúa como analista de datos senior en un contexto de negocio.\n"
        "Te paso la pregunta del usuario, un conjunto de métricas calculadas y una "
        "muestra de los datos (hasta 50 filas).\n\n"
        "Tu audiencia son el CEO y la dirección comercial de la empresa.\n\n"
        "FORMATO DE RESPUESTA (respétalo estrictamente):\n"
        "1. 'Resumen ejecutivo:'. Un único párrafo de como máximo 5 líneas, "
        "explicando en lenguaje sencillo qué está pasando y cuál es la idea clave.\n"
        "2. 'Qué nos dicen los datos:'. Uno o dos párrafos donde expliques la lectura "
        "comercial: concentración de clientes/productos, evolución a lo largo del tiempo, "
        "patrones relevantes, riesgos y oportunidades. Evita tecnicismos estadísticos.\n"
        "3. 'Qué haría ahora mismo:'. Una lista numerada de 3 a 5 acciones concretas "
        "que se puedan tomar (revisar condiciones con un cliente, lanzar campaña, "
        "pedir más detalle, crear cuadro de mando, etc.).\n\n"
        "Instrucciones importantes:\n"
        "- No repitas toda la tabla ni enumeres fila por fila.\n"
        "- No hables de formatos internos (nanosegundos, tipos de dato, etc.).\n"
        "- Evita términos muy técnicos de estadística salvo que aporten algo claro al negocio.\n"
        "- No comentes ni saques conclusiones a partir de columnas que sean identificadores "
        "(id, código, clienteid, pedidoid, etc.). Solo úsalas si necesitas mencionar un cliente "
        "o código concreto como ejemplo.\n"
        "- Cuando menciones cantidades numéricas de dinero, usa SIEMPRE el formato europeo "
        "con punto para miles y coma para decimales (por ejemplo, 428.969,73) y añade el símbolo € cuando proceda.\n"
        "- Cuando hables de unidades o recuentos (número de libros vendidos, número de clientes, "
        "número de pedidos, etc.), escríbelos como enteros sin decimales (por ejemplo, 125 libros, 8 clientes).\n"
        "- Redacta siempre en español de España, con tono ejecutivo pero cercano.\n\n"
        f"Pregunta del usuario:\n{question}\n\n"
        f"Métricas (JSON):\n{metrics}\n\n"
        f"Muestra de datos (hasta 50 filas):\n{head_limited}\n"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista de negocio experto. Sé conciso, práctico, "
                        "orientado a decisiones y respeta exactamente el formato pedido."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )

        return resp.choices[0].message.content.strip()

    except Exception as e:
        print(f"[ERROR OpenAI ANALYSIS] {e}")
        return (
            "No he podido generar el análisis automático en este momento, "
            "pero puedes revisar las tablas y gráficos para extraer tus propias conclusiones."
        )