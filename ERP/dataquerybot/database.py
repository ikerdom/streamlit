import os
import pandas as pd
import pyodbc
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

class DatabaseManager:
    def __init__(self, db_type="supabase"):
        """
        db_type puede ser 'supabase' (PostgreSQL) o 'sqlserver'
        """
        self.db_type = db_type.lower()

        if self.db_type == "sqlserver":
            self.conn_str = (
                "DRIVER={ODBC Driver 17 for SQL Server};"
                "SERVER=localhost;"
                "DATABASE=ERP_DB;"
                "Trusted_Connection=yes;"
            )
            self.engine = None

        elif self.db_type == "supabase":
            # -------------------------------------------
            # 🔥 Leemos la URL enviada por el ERP
            # -------------------------------------------
            supabase_url = os.getenv("SUPABASE_URL")

            if not supabase_url:
                raise RuntimeError(
                    "❌ Falta SUPABASE_URL en el entorno. "
                    "DataQueryBot no puede conectarse."
                )

            # -------------------------------------------
            # 🔥 Normalizamos la URL (añadir sslmode si falta)
            # -------------------------------------------
            if "sslmode" not in supabase_url.lower():
                if "?" in supabase_url:
                    supabase_url += "&sslmode=require"
                else:
                    supabase_url += "?sslmode=require"

            # -------------------------------------------
            # DEBUG para confirmar qué está recibiendo realmente
            # -------------------------------------------
            print("\n==============================")
            print("DEBUG SUPABASE_URL USADA POR DATAQUERYBOT ->")
            print(supabase_url)
            print("==============================\n")

            # -------------------------------------------
            # Crear motor SQLAlchemy
            # -------------------------------------------
            self.engine = create_engine(
                supabase_url,
                pool_pre_ping=True,   # evita conexiones cerradas
                pool_recycle=1800     # recicla cada 30 min
            )
            self.conn_str = None

        else:
            raise ValueError("db_type debe ser 'supabase' o 'sqlserver'")

    # =====================================================
    # Ejecutar consultas SQL
    # =====================================================
    def execute_query(self, sql: str):
        """
        Ejecuta una consulta SQL y devuelve un DataFrame de pandas.
        Incluye control de errores.
        """
        try:
            if self.db_type == "sqlserver":
                with pyodbc.connect(self.conn_str) as conn:
                    return pd.read_sql(sql, conn)

            elif self.db_type == "supabase":
                with self.engine.connect() as conn:
                    return pd.read_sql(text(sql), conn)

        except ProgrammingError as e:
            print("❌ ERROR SQL (sintaxis o columnas):", e)
            raise

        except OperationalError as e:
            print("❌ ERROR DE CONEXIÓN A SUPABASE:", e)
            raise

        except Exception as e:
            print("❌ ERROR GENERAL:", e)
            raise

    # =====================================================
    # Obtener esquema de tablas
    # =====================================================
    def get_schema(self):
        """
        Obtiene las tablas y columnas de la base de datos.
        """
        if self.db_type == "sqlserver":
            sql = """
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            ORDER BY TABLE_NAME, ORDINAL_POSITION;
            """

        elif self.db_type == "supabase":
            sql = """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
            """

        return self.execute_query(sql)
