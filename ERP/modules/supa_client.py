# modules/supa_client.py
from supabase import create_client
import os

# =====================================
# 🔧 CONFIG SUPABASE
# =====================================
SUPABASE_URL = "https://gqhrbvusvcaytcbnusdx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxaHJidnVzdmNheXRjYm51c2R4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MzM3MDQsImV4cCI6MjA3NTAwOTcwNH0.y3018JLs9A08sSZKHLXeMsITZ3oc4s2NDhNLxWqM9Ag"

# =====================================
# 🔹 OPCIÓN 1 — Streamlit (modo app)
# =====================================
def get_supabase_client():
    """
    Devuelve un cliente Supabase reutilizable dentro de una sesión Streamlit.
    Se usa en toda la app (modo interfaz).
    """
    try:
        from streamlit import session_state as st
        if "supabase" not in st:
            st.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        return st.supabase
    except ModuleNotFoundError:
        raise RuntimeError("❌ Streamlit no disponible. Usa get_client() si estás fuera de la app.")

# =====================================
# 🔹 OPCIÓN 2 — Directo (modo terminal)
# =====================================
def get_client():
    """
    Devuelve un cliente Supabase independiente, para scripts o terminal.
    No requiere Streamlit.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("❌ Faltan las credenciales SUPABASE_URL o SUPABASE_KEY.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)
