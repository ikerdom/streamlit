import os
import pandas as pd
from sqlalchemy import create_engine, text

url = os.getenv("SUPABASE_URL")
print("Conectando a:", url)

try:
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';"))
        tables = [row[0] for row in result]
        print("Tablas en Supabase:", tables)
except Exception as e:
    print("❌ Error al conectar:", e)
