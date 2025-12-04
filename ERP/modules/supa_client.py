from supabase import create_client, Client
import os
import streamlit as st

# =====================================================
# 🔧 CONFIG SUPABASE (usar .env o variables de sistema)
# =====================================================
SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://gqhrbvusvcaytcbnusdx.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxaHJidnVzdmNheXRjYm51c2R4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MzM3MDQsImV4cCI6MjA3NTAwOTcwNH0.y3018JLs9A08sSZKHLXeMsITZ3oc4s2NDhNLxWqM9Ag"

# =====================================================
# 🌐 CLIENTE SUPABASE PARA STREAMLIT
# =====================================================
def get_supabase_client() -> Client:
    """Devuelve un cliente Supabase persistente dentro de Streamlit."""
    if "supabase_client" not in st.session_state:
        st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return st.session_state.supabase_client

# =====================================================
# 🌐 CLIENTE SUPABASE DIRECTO (scripts)
# =====================================================
def get_client() -> Client:
    """Devuelve un cliente Supabase independiente."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)
