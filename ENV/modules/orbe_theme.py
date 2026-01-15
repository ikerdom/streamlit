import streamlit as st

PRIMARY = "#16a34a"
PRIMARY_DARK = "#15803d"
SECONDARY = "#3b82f6"
SUCCESS = "#10b981"
WARNING = "#f59e0b"
DANGER = "#dc2626"
TEXT = "#065f46"
BACKGROUND = "#f0fdf4"
BORDER = "#a7f3d0"
LIGHT = "#ecfdf5"

def apply_orbe_theme():
    st.markdown("""
    <style>

    /* ============================================================
       🌿 ORBE THEME — FIX SELECT / ICONOS MATERIAL
       ============================================================ */

    /* ---------------------------
       1) Base font (NO romper iconos)
       --------------------------- */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        font-size: 1.13rem !important;
        line-height: 1.34 !important;
        color: #064e3b !important;
    }

    /* ---------------------------
       2) Headers
       --------------------------- */
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.48rem !important; }
    h3 { font-size: 1.30rem !important; }
    h4 { font-size: 1.18rem !important; }

    h1,h2,h3,h4 {
        color: #065f46 !important;
        font-weight: 650 !important;
        margin-top: 0.36rem !important;
        margin-bottom: 0.34rem !important;
    }

    /* ---------------------------
       3) Inputs / Selects
       --------------------------- */
    input, textarea, select {
        border: 1px solid #a7f3d0 !important;
        border-radius: 6px !important;
        padding: 0.44rem 0.60rem !important;
        font-size: 1.10rem !important;
        background: #ffffff !important;
    }

    input:focus, textarea:focus, select:focus {
        outline: none !important;
        box-shadow: 0 0 0 1px #16a34a !important;
        border-color: #16a34a !important;
    }

    label, .stTextInput label, .stSelectbox label {
        font-size: 1.08rem !important;
        font-weight: 600 !important;
        color: #065f46 !important;
        margin-bottom: 0.14rem !important;
    }

    /* ================================
       5) BOTONES — tamaño mayor y texto centrado
       ================================ */

    /* Botones del CUERPO PRINCIPAL */
    div.stButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.45rem !important;

        background: linear-gradient(90deg,#22c55e,#16a34a) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;

        font-size: 1.14rem !important;
        font-weight: 700 !important;

        padding: 0.55rem 1.05rem !important;
        min-height: 3.0rem !important;
        min-width: 10.0rem !important;

        text-align: center !important;
        white-space: nowrap !important;
        overflow: hidden !important;
    }

    div.stButton > button:hover {
        background: linear-gradient(90deg,#16a34a,#15803d) !important;
        transform: translateY(-1px) !important;
    }

    button[kind="secondary"], .small-icon-btn, button[title][aria-label] {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;

        min-width: 3.6rem !important;
        max-width: 3.6rem !important;
        min-height: 3.0rem !important;
        padding: 0.36rem !important;
        font-size: 1.02rem !important;
        border-radius: 8px !important;
    }

    div.stButton > button > span, div.stButton > button > svg {
        display: inline-block !important;
        vertical-align: middle !important;
        line-height: 1 !important;
    }


    /* ⭐⭐⭐ FIX CRÍTICO — BOTONES DEL SIDEBAR (invisibles sin esto) ⭐⭐⭐ */
    [data-testid="stSidebar"] div.stButton > button {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.45rem !important;

        background: linear-gradient(90deg,#22c55e,#16a34a) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;

        font-size: 1.08rem !important;
        font-weight: 700 !important;

        padding: 0.45rem 0.60rem !important;
        margin-top: 0.50rem !important;

        width: 100% !important;
        min-height: 2.8rem !important;
    }

    [data-testid="stSidebar"] div.stButton > button:hover {
        background: linear-gradient(90deg,#16a34a,#15803d) !important;
        transform: translateY(-1px) !important;
    }

    /* ================================
       6) Espaciado vertical compacto
       ================================ */
    [data-testid="stVerticalBlock"] {
        padding-top: 0.06rem !important;
        padding-bottom: 0.06rem !important;
        margin-bottom: 0.26rem !important;
    }

    details, summary {
        padding: 0.42rem 0.60rem !important;
        font-size: 1.10rem !important;
    }

    th, td {
        padding: 7px !important;
        font-size: 1.06rem !important;
    }

    [data-testid="stSidebar"] {
        font-size: 1.10rem !important;
    }

    footer { visibility: hidden !important; }

    </style>
    """, unsafe_allow_html=True)
