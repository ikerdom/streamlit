import streamlit as st
from supabase import create_client
from .ui import safe_image

SUPABASE_URL = "https://iwtapkspwdogppxhnhes.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml3dGFwa3Nwd2RvZ3BweGhuaGVzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc5MTk3NjAsImV4cCI6MjA3MzQ5NTc2MH0.6L7vNDpX336FFEuywSIFTVuB2vKb-LgSAVYgKP6hXUk"

def get_client():
    try:
        # Si hay secrets en Streamlit Cloud, se usan
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
    except Exception:
        # En local usa las constantes
        url, key = SUPABASE_URL, SUPABASE_ANON_KEY
    return create_client(url, key)
