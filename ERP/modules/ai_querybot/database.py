# database.py
import os
import pandas as pd
from .settings import SUPABASE_URL

from sqlalchemy import create_engine, text

class DatabaseManager:
    def __init__(self, db_type="supabase"):
        """
        db_type puede ser 'supabase' (PostgreSQL) o 'sqlserver'
        """
        self.db_type = db_type.lower()

        if self.db_type == "sqlserver":
            # Ajusta según tu configuración local
            self.conn_str = (
                "DRIVER={ODBC Driver 17 for SQL Server};"
                "SERVER=localhost;"
                "DATABASE=ERP_DB;"
                "Trusted_Connection=yes;"
            )
            self.engine = None

        elif self.db_type == "supabase":
            supabase_url = os.getenv("SUPABASE_URL")

            self.engine = create_engine(supabase_url)
            self.conn_str = None

        else:
            raise ValueError("db_type debe ser 'supabase' o 'sqlserver'")

    def execute_query(self, sql: str):
        """
        Ejecuta una consulta SQL y devuelve un DataFrame de pandas.
        """
        if self.db_type == "sqlserver":
            with pyodbc.connect(self.conn_str) as conn:
                return pd.read_sql(sql, conn)
        elif self.db_type == "supabase":
            with self.engine.connect() as conn:
                return pd.read_sql(text(sql), conn)

    def get_schema(self):
        """
        Obtiene las tablas y columnas de la base de datos.
        """
        if self.db_type == "sqlserver":
            sql = """
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            ORDER BY TABLE_NAME, ORDINAL_POSITION
            """
        elif self.db_type == "supabase":
            sql = """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        return self.execute_query(sql)
