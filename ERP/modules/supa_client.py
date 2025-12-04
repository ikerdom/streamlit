# ============================================
# 🧩 SUPABASE CLIENT (SDK 2.x)
# ============================================
import os
import streamlit as st
from supabase import create_client

# ============================================
# 🔧 CONFIG
# ============================================
SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://gqhrbvusvcaytcbnusdx.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdxaHJidnVzdmNheXRjYm51c2R4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MzM3MDQsImV4cCI6MjA3NTAwOTcwNH0.y3018JLs9A08sSZKHLXeMsITZ3oc4s2NDhNLxWqM9Ag"

# ============================================
# 🌐 CLIENTE PARA STREAMLIT
# ============================================
def get_supabase_client():
    """Retorna un cliente Supabase persistente en Streamlit."""
    if "supabase" not in st.session_state:
        st.session_state.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return st.session_state.supabase

# ============================================
# 🌐 CLIENTE PARA SCRIPTS
# ============================================
def get_client():
    """Retorna un cliente Supabase independiente."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)
