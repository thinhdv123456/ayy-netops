import streamlit as st
from config import APP_NAME, APP_VERSION, OPERATOR
from i18n import t
from database import init_database

init_database()

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "lang" not in st.session_state:
    st.session_state.lang = "vi"

lang = st.session_state.lang

st.markdown(
    """
    <style>
    /* ====== Apple Design System ====== */
    /* Adaptive colors: work in both light and dark Streamlit themes */
    :root {
        --apple-radius-sm: 8px;
        --apple-radius-md: 12px;
        --apple-radius-lg: 16px;
        --apple-radius-xl: 22px;
        --apple-shadow-light: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
        --apple-shadow-md: 0 4px 14px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04);
        --apple-shadow-lg: 0 8px 30px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06);
        --apple-transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* --- KPI Metric cards --- */
    .stMetric > div {
        border: 1px solid rgba(142,142,147,0.18);
        border-radius: var(--apple-radius-lg) !important;
        padding: 18px 16px;
        box-shadow: var(--apple-shadow-md);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: var(--apple-transition);
    }
    .stMetric > div:hover {
        box-shadow: var(--apple-shadow-lg);
        transform: translateY(-1px);
    }
    .stMetric label {
        font-weight: 500 !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.01em;
        opacity: 0.72;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-weight: 700 !important;
        font-size: 1.9rem !important;
        letter-spacing: -0.02em;
    }

    /* --- Sidebar (fresh, vibrant) --- */
    div[data-testid="stSidebarContent"] {
        background: linear-gradient(180deg, #007AFF 0%, #5856D6 100%) !important;
    }
    div[data-testid="stSidebarContent"] * {
        color: #FFFFFF !important;
    }
    div[data-testid="stSidebarContent"] .stMarkdown p,
    div[data-testid="stSidebarContent"] .stMarkdown h3,
    div[data-testid="stSidebarContent"] .stCaption p {
        color: rgba(255,255,255,0.95) !important;
    }
    div[data-testid="stSidebarContent"] hr {
        border-color: rgba(255,255,255,0.25) !important;
    }
    div[data-testid="stSidebarContent"] [data-testid="stSidebarNav"] a {
        color: rgba(255,255,255,0.9) !important;
        border-radius: var(--apple-radius-md) !important;
        transition: var(--apple-transition);
    }
    div[data-testid="stSidebarContent"] [data-testid="stSidebarNav"] a:hover {
        background: rgba(255,255,255,0.15) !important;
    }
    div[data-testid="stSidebarContent"] [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background: rgba(255,255,255,0.22) !important;
        font-weight: 700 !important;
    }
    div[data-testid="stSidebarContent"] .stButton > button {
        background: rgba(255,255,255,0.2) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        backdrop-filter: blur(8px);
    }
    div[data-testid="stSidebarContent"] .stButton > button:hover {
        background: rgba(255,255,255,0.3) !important;
    }
    div[data-testid="stSidebarContent"] span[data-testid="stHeaderActionElements"] {
        color: #FFFFFF !important;
    }
    div[data-testid="stSidebarContent"] [data-testid="stSidebarNavSeparator"] span {
        color: rgba(255,255,255,0.7) !important;
        font-weight: 600 !important;
        font-size: 0.7rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* --- Buttons (Apple pill style) --- */
    .stButton > button {
        border-radius: var(--apple-radius-xl) !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 0.45rem 1.2rem !important;
        border: none !important;
        box-shadow: var(--apple-shadow-light);
        transition: var(--apple-transition);
        letter-spacing: 0.005em;
    }
    .stButton > button:hover {
        box-shadow: var(--apple-shadow-md);
        transform: translateY(-1px);
        filter: brightness(1.06);
    }
    .stButton > button:active {
        transform: scale(0.97);
        box-shadow: none;
    }

    /* --- Tabs (Apple segmented control) --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        border-radius: var(--apple-radius-md);
        padding: 3px;
        background: rgba(142,142,147,0.1);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: var(--apple-radius-sm) !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        padding: 8px 16px !important;
        transition: var(--apple-transition);
    }
    .stTabs [aria-selected="true"] {
        box-shadow: var(--apple-shadow-light);
    }

    /* --- Data tables --- */
    .stDataFrame, [data-testid="stDataFrame"] {
        border-radius: var(--apple-radius-lg) !important;
        overflow: hidden;
        box-shadow: var(--apple-shadow-light);
        border: 1px solid rgba(142,142,147,0.15) !important;
    }

    /* --- Expander / containers --- */
    .streamlit-expanderHeader {
        border-radius: var(--apple-radius-md) !important;
        font-weight: 600 !important;
    }
    [data-testid="stExpander"] {
        border-radius: var(--apple-radius-lg) !important;
        border: 1px solid rgba(142,142,147,0.15) !important;
        overflow: hidden;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] > [data-testid="stCheckbox"]),
    div[data-testid="stVerticalBlockBorderWrapper"][style*="border"] {
        border-radius: var(--apple-radius-lg) !important;
        border-color: rgba(142,142,147,0.15) !important;
        box-shadow: var(--apple-shadow-light);
    }

    /* --- Select boxes / inputs --- */
    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        border-radius: var(--apple-radius-md) !important;
        border: 1px solid rgba(142,142,147,0.25) !important;
        transition: var(--apple-transition);
    }
    .stSelectbox > div > div:focus-within,
    .stTextInput > div > div > input:focus {
        border-color: #007aff !important;
        box-shadow: 0 0 0 3px rgba(0,122,255,0.15) !important;
    }

    /* --- Download button --- */
    .stDownloadButton > button {
        border-radius: var(--apple-radius-xl) !important;
        font-weight: 600 !important;
    }

    /* --- Alert boxes --- */
    .stAlert {
        border-radius: var(--apple-radius-lg) !important;
        border: none !important;
        box-shadow: var(--apple-shadow-light);
    }

    /* --- Headings --- */
    h1, h2, h3 {
        letter-spacing: -0.02em !important;
        font-weight: 700 !important;
    }
    h2 { font-size: 1.65rem !important; }
    h3 { font-size: 1.2rem !important; }

    /* --- Plotly charts container --- */
    .stPlotlyChart {
        border-radius: var(--apple-radius-lg);
        overflow: hidden;
    }

    /* --- Scrollbar (subtle) --- */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: rgba(142,142,147,0.3);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: rgba(142,142,147,0.5); }

    /* --- Dark mode adaptive text --- */
    @media (prefers-color-scheme: dark) {
        .stMetric > div {
            border-color: rgba(142,142,147,0.25);
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(f"### 📡 {APP_NAME}")
    st.caption(f"v{APP_VERSION}")

    toggle_label = "🇬🇧 Switch to English" if lang == "vi" else "🇻🇳 Chuyển sang Tiếng Việt"
    if st.button(toggle_label, use_container_width=True):
        st.session_state.lang = "en" if lang == "vi" else "vi"
        st.rerun()

    current_lang = "🇻🇳 Tiếng Việt" if lang == "vi" else "🇬🇧 English"
    st.caption(current_lang)

    st.divider()
    st.markdown(f"👤 **{t('operator', lang)}:** {OPERATOR}")

    # --- Network Access ---
    st.divider()
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "N/A"

    st.markdown(f"🌐 **{'Truy cập mạng' if lang == 'vi' else 'Network Access'}**")
    st.code(f"http://{local_ip}:8501", language=None)
    st.caption("LAN — " + ("cùng mạng WiFi" if lang == "vi" else "same WiFi network"))

    # External access via ngrok
    import urllib.request, json as _json
    ngrok_url = None
    try:
        resp = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=1)
        tunnels = _json.loads(resp.read())["tunnels"]
        if tunnels:
            ngrok_url = tunnels[0]["public_url"]
    except Exception:
        pass

    if ngrok_url:
        st.markdown(f"🌍 **{'Truy cập ngoài mạng' if lang == 'vi' else 'External Access'}**")
        st.code(ngrok_url, language=None)
        st.caption("🌐 " + ("Chia sẻ link này cho mọi thiết bị" if lang == "vi"
                             else "Share this link with any device"))
    else:
        st.caption("🌍 " + ("Ngoài mạng: ngrok chưa chạy" if lang == "vi"
                             else "External: ngrok not running"))

    st.divider()

pg = st.navigation([
    st.Page("pages/01_dashboard.py", title=f"🏠 {t('dashboard', lang)}", default=True),
    st.Page("pages/02_cellhr.py", title=f"📊 {t('cellhr_analysis', lang)}"),
    st.Page("pages/03_power.py", title=f"🔋 {t('power_mgmt', lang)}"),
    st.Page("pages/04_transmission.py", title=f"📡 {t('transmission', lang)}"),
    st.Page("pages/05_sites.py", title=f"🏗️ {t('site_mgmt', lang)}"),
    st.Page("pages/06_manpower.py", title=f"👥 {t('manpower', lang)}"),
    st.Page("pages/07_reports.py", title=f"📈 {t('reports', lang)}"),
    st.Page("pages/08_command.py", title=f"🎯 {t('command_center', lang)}"),
    st.Page("pages/09_alerts.py", title=f"⚠️ {t('smart_alerts', lang)}"),
    st.Page("pages/10_action_tracker.py", title=f"📋 {t('action_tracker', lang)}"),
])
pg.run()
