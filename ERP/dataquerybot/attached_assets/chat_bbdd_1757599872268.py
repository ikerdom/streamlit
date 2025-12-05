# chat_bbdd.py — Chat T-SQL para SQL Server con reintento por nombres inválidos (modelo gpt-5)
from __future__ import annotations
import os, sys, re, traceback
import pyodbc
from openai import OpenAI

print(">>> Arrancando chat_bbdd.py (SQL Server)", flush=True)

# ---------------------------
# Configuración
# ---------------------------
MODEL = "gpt-5"                        # solicitado
TOP_DEFAULT = int(os.getenv("SQL_TOP_DEFAULT", "200"))

def conectar_sqlserver():
    """Construye la cadena de conexión y conecta a SQL Server."""
    dsn = os.getenv("SQLSERVER_DSN")
    if dsn:
        conn_str = f"DSN={dsn};TrustServerCertificate=yes;"
    else:
        server  = os.getenv("SQLSERVER_SERVER", r"localhost\SQLEXPRESS")
        db      = os.getenv("SQLSERVER_DB", "ERP_IA")
        trusted = os.getenv("SQLSERVER_TRUSTED", "1") in ("1","true","TRUE","yes","YES")
        driver  = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server")

        if trusted:
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};DATABASE={db};"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
            )
        else:
            user = os.getenv("SQLSERVER_USER", "")
            pwd  = os.getenv("SQLSERVER_PWD", "")
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};DATABASE={db};UID={user};PWD={pwd};"
                "TrustServerCertificate=yes;"
            )
    return pyodbc.connect(conn_str)

def leer_esquema(conn) -> dict[str, set[str]]:
    """Devuelve { [schema].[tabla] : {columnas} } usando INFORMATION_SCHEMA."""
    esquema: dict[str, set[str]] = {}
    q = """
    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS
    ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;
    """
    cur = conn.cursor()
    for sch, tbl, col in cur.execute(q):
        full = f"[{sch}].[{tbl}]"
        esquema.setdefault(full, set()).add(col)
    return esquema

def esquema_a_texto(esquema: dict[str, set[str]]) -> str:
    bloques = []
    for full, cols in sorted(esquema.items()):
        cols_txt = ", ".join(f"[{c}]" for c in sorted(cols))
        bloques.append(f"- {full}: {cols_txt}")
    return "\n".join(bloques)

# ---------------------------
# Normalización (T-SQL)
# ---------------------------
_lim_limit = re.compile(r"\sLIMIT\s+(\d+)\s*;?\s*$", re.IGNORECASE)

def asegurar_top(sql: str, top_por_defecto: int = TOP_DEFAULT) -> str:
    s = sql.strip()
    if not s.upper().startswith("SELECT"):
        return s
    m = _lim_limit.search(s)
    if m:
        n = int(m.group(1))
        s = _lim_limit.sub("", s).rstrip()
        return _inyectar_top(s, n)
    if " TOP " not in s.upper():
        s = _inyectar_top(s, top_por_defecto)
    return s

def _inyectar_top(s: str, n: int) -> str:
    su = s.lstrip()
    if su[:15].upper() == "SELECT DISTINCT":
        return f"SELECT DISTINCT TOP {n} " + su[16:].lstrip()
    if su[:6].upper() == "SELECT":
        return f"SELECT TOP {n} " + su[7:].lstrip()
    return s

def es_select(sql: str) -> bool:
    return sql.strip().upper().startswith("SELECT")

# ---------------------------
# Prompting (T-SQL)
# ---------------------------
def reglas_tsql(ident_txt: str, estricto: bool) -> str:
    base = (
        "Convierte preguntas en español a T-SQL para SQL Server.\n"
        "Responde SOLO con UNA consulta SELECT válida (sin texto extra ni ```).\n"
        "Reglas de dialecto:\n"
        "- Solo SELECT (prohibido INSERT/UPDATE/DELETE/DDL/EXEC).\n"
        "- Usa TOP n para limitar; fechas 'YYYY-MM-DD'; comodines % y _ en LIKE.\n"
        "- Usa ISNULL() o COALESCE() para nulos (no Nz, no IIf).\n"
        "- Identificadores entre corchetes: [schema].[tabla], [columna].\n"
        "- Evita FORMAT si no es necesario; para año/mes usa YEAR(), MONTH() o CONVERT/FORMAT sólo si procede.\n"
        "Identificadores permitidos (lista exhaustiva):\n"
        f"{ident_txt}\n"
    )
    if estricto:
        base += (
            "\nModo estricto: ajusta EXACTAMENTE a esos identificadores; "
            "si un término común (p.ej. 'facturación') no existe, elige el campo más plausible de la lista "
            "(p.ej. [dbo].[MODULOS].[PRECIO_FIN], [dbo].[FACTURAS].[IMPORTE], [dbo].[FACTURAS].[IVA], etc.).\n"
        )
    else:
        base += "\nEmplea exclusivamente los identificadores listados.\n"
    return base

def prompt_usuario(pregunta: str) -> str:
    return (
        "Devuelve una única consulta SELECT T-SQL para SQL Server, usando SOLO los identificadores listados.\n"
        f"Pregunta: {pregunta}\n"
    )

def generar_sql(client: OpenAI, pregunta: str, ident_txt: str, estricto=False) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.2 if not estricto else 0.1,
        messages=[
            {"role":"system","content": reglas_tsql(ident_txt, estricto)},
            {"role":"user",  "content": prompt_usuario(pregunta)},
        ],
    )
    sql = resp.choices[0].message.content.strip()
    # Por si viniese con fences
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.IGNORECASE)
    return sql

# ---------------------------
# Ejecución y salida
# ---------------------------
def ejecutar_y_mostrar(conn, sql: str):
    cur = conn.cursor()
    cur.execute(sql)
    if cur.description is None:
        print("\n(Consulta sin conjunto de resultados)\n", flush=True)
        return
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    # Tabla simple en texto
    ancho = [max(len(str(v)) for v in [col] + [r[i] for r in rows]) for i, col in enumerate(cols)]
    sep = "+".join("-" * (w + 2) for w in ancho)
    def fmt_row(r):
        return "|".join(f" {str(r[i])[:w]}".ljust(w + 2) for i, w in enumerate(ancho))
    print("\n" + sep, flush=True)
    print(fmt_row(cols), flush=True)
    print(sep, flush=True)
    for r in rows:
        print(fmt_row(r), flush=True)
    print(sep + "\n", flush=True)
    print(f"Filas: {len(rows)}\n", flush=True)

def es_error_nombres(e: pyodbc.Error) -> bool:
    s = str(e)
    return ("Invalid column name" in s) or ("Invalid object name" in s)

# ---------------------------
# Main
# ---------------------------
def main():
    print(">>> Entrando en main()", flush=True)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Falta la variable de entorno OPENAI_API_KEY", flush=True)
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Conexión
    try:
        conn = conectar_sqlserver()
        print(">>> Conectado a SQL Server", flush=True)
    except Exception:
        print("Error conectando a SQL Server")
        traceback.print_exc()
        sys.exit(1)

    # Esquema
    try:
        esquema = leer_esquema(conn)
        print(">>> Esquema leído", flush=True)
    except Exception:
        print("No se pudo leer el esquema")
        traceback.print_exc()
        sys.exit(1)

    ident_txt = esquema_a_texto(esquema)
    # print(">>> Identificadores:\n", ident_txt)  # descomenta si quieres verlos

    print("\nBienvenido al chat T-SQL. Escribe 'salir' para terminar.\n", flush=True)

    while True:
        try:
            pregunta = input("Pregunta (es/es): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.", flush=True)
            break
        if not pregunta:
            continue
        if pregunta.lower() in {"salir","exit","quit"}:
            print("Hasta luego.", flush=True)
            break

        print(f">>> Recibida pregunta: {pregunta}", flush=True)

        try:
            sql = generar_sql(client, pregunta, ident_txt, estricto=False)
        except Exception:
            print("Error al generar SQL (modo normal)")
            traceback.print_exc()
            continue

        if not es_select(sql):
            print("Solo se permiten consultas SELECT. Reformula la pregunta.", flush=True)
            continue

        sql_norm = asegurar_top(sql)
        if sql_norm != sql:
            print("Ajuste de dialecto T-SQL aplicado:", flush=True)
            print("  " + sql, flush=True)
            print("  ->", flush=True)
            print("  " + sql_norm, flush=True)

        try:
            ejecutar_y_mostrar(conn, sql_norm)
        except pyodbc.Error as e:
            print("\nSQL Server devolvió un error:", flush=True)
            print(sql_norm, flush=True)
            print(f"\nDetalle: {e}\n", flush=True)

            if es_error_nombres(e):
                print("Reintentando con ajuste estricto de nombres del esquema...\n", flush=True)
                try:
                    sql2 = asegurar_top(generar_sql(client, pregunta, ident_txt, estricto=True))
                    ejecutar_y_mostrar(conn, sql2)
                except pyodbc.Error as e2:
                    print("\nFalló también el reintento estricto.", flush=True)
                    print(sql2, flush=True)
                    print(f"\nDetalle: {e2}\n", flush=True)
                except Exception:
                    print("Error al generar SQL (modo estricto)")
                    traceback.print_exc()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Error inesperado al ejecutar main()")
        traceback.print_exc()
