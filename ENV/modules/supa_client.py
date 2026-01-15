"""
Supabase client for UI and scripts.
Credentials loaded from (in order):
1) Streamlit secrets (if present)
2) .env in current directory
3) SUPABASE_URL/SUPABASE_KEY env vars
"""
from supabase import create_client
import os
import streamlit as st
from dotenv import load_dotenv, dotenv_values

_SUPABASE_CACHED = None


def _load_env() -> str:
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.isfile(env_path):
        load_dotenv(env_path, override=False)
    return env_path


def _get_creds():
    env_path = _load_env()

    # Try Streamlit secrets first (if available)
    try:
        url = st.secrets["SUPABASE_URL"]  # type: ignore[attr-defined]
        key = st.secrets["SUPABASE_KEY"]  # type: ignore[attr-defined]
        return url, key
    except Exception:
        pass

    # Fallback to environment variables
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    # Fallback to .env values if still missing
    if not url or not key:
        file_vals = dotenv_values(env_path) if os.path.isfile(env_path) else {}
        url = url or file_vals.get("SUPABASE_URL")
        key = key or file_vals.get("SUPABASE_KEY")

    if not url or not key:
        msg = "Faltan credenciales Supabase. Rellena SUPABASE_URL/SUPABASE_KEY en .env o secrets.toml."
        try:
            st.error(msg)
            st.stop()
        except Exception:
            raise ValueError(msg)

    return url, key


def get_supabase_client():
    """
    Reusable Supabase client for Streamlit UI.
    """
    global _SUPABASE_CACHED
    if _SUPABASE_CACHED is None:
        url, key = _get_creds()
        _SUPABASE_CACHED = create_client(url, key)
    return _SUPABASE_CACHED


def get_client():
    """
    Supabase client for scripts/terminal (non-Streamlit).
    """
    global _SUPABASE_CACHED
    if _SUPABASE_CACHED is None:
        url, key = _get_creds()
        _SUPABASE_CACHED = create_client(url, key)
    return _SUPABASE_CACHED
