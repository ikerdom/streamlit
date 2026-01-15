# backend/app/core/database.py
import os
from supabase import create_client, Client
from functools import lru_cache
from dotenv import load_dotenv

# Carga .env desde la raíz ENV para evitar fallos de variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


@lru_cache
def get_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("❌ Variables SUPABASE_URL o SUPABASE_SERVICE_KEY no definidas")

    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
