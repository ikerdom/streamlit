import streamlit as st

def apply_orbe_theme():
    """🎨 Aplica el tema visual corporativo Orbe a toda la app Streamlit."""
    st.markdown("""
    <style>

    /* =============================
       🌿 ORBE THEME · EnteNova Gnosis · ERP Editorial Orbe
       ============================= */

    /* --- Layout general --- */
    main, [data-testid="stAppViewContainer"] {
        max-width: 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        padding: 1rem 2rem 2rem 2rem !important;
        background-color: #ffffff !important;
    }

    /* --- Sidebar --- */
    [data-testid="stSidebar"] {
        background-color: #f0fdf4 !important;
        border-right: 1px solid #dcfce7 !important;
        padding-top: 1.2rem !important;
    }
    [data-testid="stSidebarNav"] h1, [data-testid="stSidebar"] h2 {
        color: #065f46 !important;
        font-weight: 600 !important;
    }

    /* --- Scrollbars suaves --- */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #f9fafb; }
    ::-webkit-scrollbar-thumb {
        background-color: #86efac;
        border-radius: 4px;
    }

    /* --- Cabeceras --- */
    h1, h2, h3, h4 {
        color: #065f46 !important;
        font-weight: 600 !important;
    }

    /* --- Inputs y selects --- */
    input, select, textarea {
        border: 1px solid #a7f3d0 !important;
        border-radius: 6px !important;
        padding: 0.4rem 0.6rem !important;
        background-color: #ffffff !important;
    }
    input:focus, select:focus, textarea:focus {
        border-color: #16a34a !important;
        box-shadow: 0 0 0 1px #16a34a !important;
    }
    /* --- Botones principales (versión verde-azulada corporativa) --- */
    div.stButton > button {
        background: linear-gradient(90deg, #60a5fa, #34d399) !important; /* azul -> verde agua */
        color: #083344 !important; /* texto azul petróleo */
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.1rem !important;
        transition: all 0.25s ease-in-out;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.08);
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #3b82f6, #10b981) !important; /* azul más intenso + verde */
        transform: translateY(-1px) scale(1.02);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    div.stButton > button:active {
        transform: scale(0.98);
        background: linear-gradient(90deg, #2563eb, #059669) !important;
    }


    /* --- Métricas --- */
    [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
        color: #065f46 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricLabel"] { color: #166534 !important; }

    /* --- Tarjetas, tablas y contenedores --- */
    .card-container, .stDataFrame, .stDataTable {
        border: 1px solid #d1fae5 !important;
        border-radius: 12px !important;
        background: #f0fdf4 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        padding: 12px !important;
    }
    table { border-collapse: collapse !important; width: 100%; }
    th {
        background: #ecfdf5 !important;
        color: #065f46 !important;
        padding: 8px !important;
        border-bottom: 2px solid #a7f3d0 !important;
    }
    td {
        padding: 8px !important;
        border-bottom: 1px solid #e5e7eb !important;
    }
    tr:nth-child(even) { background: #f9fafb !important; }

    /* --- Expanders --- */
    details, summary {
        background: #f0fdf4 !important;
        border: 1px solid #a7f3d0 !important;
        border-radius: 8px !important;
        padding: 6px !important;
    }

    /* --- Scroll interno CRM --- */
    .crm-scroll {
        max-height: 450px;
        overflow-y: auto;
        padding-right: 6px;
    }

    /* --- Toasts / Alertas --- */
    [data-testid="stToast"] {
        background: #f0fdf4 !important;
        color: #065f46 !important;
        border: 1px solid #a7f3d0 !important;
        border-radius: 10px !important;
    }

    /* --- Tabs --- */
    [data-baseweb="tab-list"] button {
        color: #065f46 !important;
        font-weight: 500 !important;
    }
    [data-baseweb="tab-list"] button[aria-selected="true"] {
        border-bottom: 3px solid #16a34a !important;
        color: #065f46 !important;
    }

    /* --- Código, texto y pequeños detalles --- */
    .stMarkdown code {
        background: #ecfdf5 !important;
        color: #065f46 !important;
        border-radius: 4px;
        padding: 2px 5px;
    }

    /* --- Footer (opcional) --- */
    footer {
        visibility: hidden !important;
    }

    </style>
    """, unsafe_allow_html=True)
