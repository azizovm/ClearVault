import base64
import io
import json
import logging
import re
import sys
from pathlib import Path

logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

import pandas as pd

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

APP_DIR = Path(__file__).parent
CLEARVAULT_LOGO_PATH = APP_DIR / "ClearVault Logo.png"
CLEARVAULT_LOGO_B64 = base64.b64encode(CLEARVAULT_LOGO_PATH.read_bytes()).decode("utf-8")
CLEARVAULT_LOGO_URI = f"data:image/png;base64,{CLEARVAULT_LOGO_B64}"
DOCUMENTS_INDEX_PATH = Path("chroma_db/documents.json")

st.set_page_config(
    page_title="ClearVault",
    page_icon=str(CLEARVAULT_LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@400,0&display=swap');

*, *::before, *::after {
    box-sizing: border-box;
    font-family: 'Inter', sans-serif;
}

:root {
    --surface: #f7f9fb;
    --surface-lowest: #ffffff;
    --surface-low: #f2f4f6;
    --surface-container: #eceef0;
    --surface-high: #e6e8ea;
    --outline: #76777d;
    --outline-variant: #c6c6cd;
    --text: #191c1e;
    --text-variant: #475569;
    --navy: #0f172a;
    --navy-2: #131b2e;
    --green: #059669;
    --green-soft: #ecfdf5;
    --blue-soft: #eff6ff;
    --red-soft: #fff1f2;
}

/* ── Hide streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; height: 0; }
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }

/* ── App shell ── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: var(--surface) !important;
}
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
    background: var(--surface) !important;
}
section[data-testid="stMain"] { background: var(--surface) !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid var(--outline-variant) !important;
    min-width: 256px !important;
    max-width: 256px !important;
}
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    width: 100% !important;
    border-radius: 4px !important;
    padding: 10px 12px !important;
    justify-content: flex-start !important;
    text-align: left !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: #f1f5f9 !important;
    color: var(--navy) !important;
    border: 1px solid var(--outline-variant) !important;
    border-right: 2px solid var(--navy) !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    color: var(--text-variant) !important;
    border: 1px solid transparent !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
    background: #f8fafc !important;
    color: var(--navy) !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {
    background: #e2e8f0 !important;
}

/* ── Typography & spacing ── */
.page-shell {
    max-width: 1440px;
    margin: 0 auto;
    padding: 24px;
}
.page-header {
    display: flex;
    justify-content: space-between;
    align-items: end;
    gap: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--outline-variant);
    margin-bottom: 16px;
}
.page-title {
    font-size: 30px;
    line-height: 38px;
    letter-spacing: -0.02em;
    font-weight: 600;
    color: var(--text);
    margin: 0 0 4px 0;
}
.page-subtitle {
    font-size: 14px;
    line-height: 20px;
    color: var(--text-variant);
    margin: 0;
}

/* ── Surface primitives ── */
.surface-card,
.metric-card,
.table-shell,
.chat-shell,
.viewer-shell,
.dropzone-shell,
.queue-card {
    background: var(--surface-lowest);
    border: 1px solid var(--outline-variant);
    border-radius: 4px;
}
.surface-card { padding: 16px; }
.metric-card { padding: 16px; min-height: 132px; }
.section-label {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--text-variant);
    margin: 0 0 10px 0;
}

/* ── Buttons ── */
.main button,
.main .stButton > button {
    border-radius: 4px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
}
[data-testid="stForm"] [data-testid="stBaseButton-primary"],
[data-testid="stForm"] .stButton > button[kind="primary"],
.main .stButton > button[kind="primary"] {
    background: var(--navy) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.18) !important;
}
[data-testid="stForm"] [data-testid="stBaseButton-primary"]:hover,
[data-testid="stForm"] .stButton > button[kind="primary"]:hover,
.main .stButton > button[kind="primary"]:hover {
    background: #1e293b !important;
}

/* Guard: ensure text inside light-bg Streamlit containers stays dark */
.stMarkdown p, .stMarkdown li, .stMarkdown span:not([class*="material"]),
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] span {
    color: #0F172A;
}
[data-testid="stCaptionContainer"] p { color: var(--text-variant) !important; }
.main .stButton > button[kind="secondary"] {
    background: white !important;
    color: var(--navy) !important;
    border: 1px solid var(--outline-variant) !important;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    border-radius: 4px !important;
    font-size: 14px !important;
}
[data-testid="stTextInput"] input {
    border: 1px solid var(--outline-variant) !important;
    padding: 10px 12px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--navy) !important;
    box-shadow: 0 0 0 1px var(--navy) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #f7f9fb !important;
    border: 2px dashed #c6c6cd !important;
    border-radius: 4px !important;
    padding: 40px 24px !important;
    margin-bottom: 16px !important;
    text-align: center !important;
}
[data-testid="stFileUploader"] section { padding: 8px 0 !important; }
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    gap: 10px !important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #0f172a !important;
}
[data-testid="stFileUploader"] button {
    border-radius: 4px !important;
    background: var(--navy) !important;
    color: white !important;
    border: none !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    padding: 10px 22px !important;
}

/* ── Streamlit containers ── */
.main [data-testid="stVerticalBlock"] { gap: 0 !important; }
[data-testid="stCaptionContainer"] p,
[data-testid="stAlert"] p,
[data-testid="stSpinner"] p,
[data-testid="stStatusContainer"] { font-size: 14px !important; }

/* ── Table & row styling ── */
.table-shell { overflow: hidden; }
.table-header,
.table-row {
    display: grid;
    gap: 12px;
    align-items: center;
}
.table-header {
    background: var(--surface);
    border-bottom: 1px solid var(--outline-variant);
    padding: 10px 16px;
}
.table-row {
    padding: 12px 16px;
    border-bottom: 1px solid #f1f5f9;
}
.table-row:nth-child(even) { background: #f8fafc; }
.table-row:hover { background: #f8fafc; }

/* ── Badges / chips ── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
    line-height: 1;
}

/* ── Progress bars ── */
[data-testid="stProgressBar"] > div > div { background: var(--green) !important; }

/* ── Scrollbars ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #e0e3e5; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #c6c6cd; }

/* ── Status widget (the "Analyzing…" bar) ── */
[data-testid="stStatusWidget"] {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 4px !important;
}
[data-testid="stStatusWidget"] p,
[data-testid="stStatusWidget"] span,
[data-testid="stStatusWidget"] label { color: #e2e8f0 !important; }
[data-testid="stStatusWidget"] svg { stroke: #e2e8f0 !important; fill: #e2e8f0 !important; }
[data-testid="stStatusWidget"] button {
    background: transparent !important;
    color: #94a3b8 !important;
    border-color: rgba(255,255,255,0.12) !important;
}

/* ── Prompt chip buttons ── */
button[data-testid="stBaseButton-secondary"].chip-btn {
    border-radius: 9999px !important;
    font-size: 11px !important;
    padding: 4px 10px !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
}

/* ── Smooth scroll ── */
html { scroll-behavior: smooth; }


</style>
""",
    unsafe_allow_html=True,
)

# ── HTML helpers ──────────────────────────────────────────────────────────────

def _badge(label: str, cls: str) -> str:
    styles = {
        "critical": "background:#ffdad6;color:#93000a;border:1px solid rgba(186,26,26,0.20)",
        "high":     "background:#eceef0;color:#7c2d12;border:1px solid rgba(148,163,184,0.35)",
        "medium":   "background:#eef2ff;color:#3f465c;border:1px solid rgba(94,107,149,0.20)",
        "low":      "background:#f0fdf4;color:#166534;border:1px solid rgba(5,150,105,0.20)",
        "verified": "background:#ecfdf5;color:#069669;border:1px solid rgba(5,150,105,0.16)",
        "pending":  "background:#f8fafc;color:#64748b;border:1px solid #e2e8f0",
        "flagged":  "background:#fff1f2;color:#9f1239;border:1px solid rgba(190,24,93,0.18)",
        "indexed":  "background:#ecfdf5;color:#069669;border:1px solid rgba(5,150,105,0.16)",
        "info":     "background:#eff6ff;color:#1d4ed8;border:1px solid rgba(37,99,235,0.15)",
    }
    style = styles.get(cls, styles["pending"])
    return (
        f'<span class="badge" style="{style}">{label}</span>'
    )


def _card(content: str, padding: str = "20px") -> str:
    return (
        f'<div class="surface-card" style="padding:{padding};margin-bottom:16px;">{content}</div>'
    )


def _section_label(text: str) -> str:
    return (
        f'<div class="section-label">{text}</div>'
    )


def _clearvault_mark(size: int = 40) -> str:
    """Render the uploaded ClearVault logo asset."""
    return (
        f'<img src="{CLEARVAULT_LOGO_URI}" alt="ClearVault logo" '
        f'style="width:{size}px;height:{size}px;object-fit:contain;display:block;" />'
    )


def _clearvault_brand(show_subtitle: bool = False, mark_size: int = 40) -> str:
    """Render ClearVault branding with mark and wordmark."""
    mark_svg = _clearvault_mark(size=mark_size)
    subtitle = (
        '<div style="font-size:11px;color:#94a3b8;margin-top:4px;font-weight:500;">Audit Intelligence</div>'
        if show_subtitle else ''
    )
    return f'''
    <div style="display:flex;align-items:center;gap:12px;">
        {mark_svg}
        <div>
            <div style="font-size:18px;font-weight:700;color:#0f172a;letter-spacing:-0.02em;">ClearVault</div>
            {subtitle}
        </div>
    </div>
    '''


# ── Quick-prompt chips ────────────────────────────────────────────────────────

_SUGGESTED_PROMPTS = [
    ("", "Extract the 2023 depreciation schedule."),
    ("", "Show EBITDA and key adjustments as a table."),
    ("", "Extract working capital components."),
    ("", "List all critical liabilities and risks."),
    ("", "Summarize revenue breakdown by segment."),
    ("", "Extract the cap table or ownership structure."),
]

# ── Demo liability data (shown when no real extraction has run) ───────────────

_DEMO_LIABILITIES = [
    {"risk_type": "Financial",   "severity": "CRITICAL", "description": "Contingent liability ~$14.2M from pending regulatory investigation not reflected in balance sheet.", "page": "47"},
    {"risk_type": "Legal",       "severity": "HIGH",     "description": "Vendor MSA indemnification clause (Annex C, §12.3) lacks liability cap — unlimited exposure.", "page": "83"},
    {"risk_type": "Compliance",  "severity": "HIGH",     "description": "Customer PII handling does not satisfy GDPR Article 28 DPA requirements for sub-processors.", "page": "112"},
    {"risk_type": "Operational", "severity": "MEDIUM",   "description": "Top-3 customers represent 67% of ARR with no contractual lock-in beyond 12-month terms.", "page": "29"},
    {"risk_type": "Financial",   "severity": "MEDIUM",   "description": "Deferred revenue recognition policy change in Q2 2023 inflated reported ARR by an estimated 8–11%.", "page": "61"},
    {"risk_type": "Legal",       "severity": "MEDIUM",   "description": "Three pending employee FLSA claims; total exposure estimated at $800K–$1.2M.", "page": "94"},
    {"risk_type": "Operational", "severity": "LOW",      "description": "CTO holds sole access to core infrastructure credentials with no documented succession plan.", "page": "18"},
    {"risk_type": "Compliance",  "severity": "LOW",      "description": "SOC 2 Type I certificate expired 4 months ago; renewal audit in progress but not completed.", "page": "105"},
]

# ── Table helpers ─────────────────────────────────────────────────────────────

def _extract_markdown_table(text: str) -> str | None:
    """Return the first complete Markdown table block in text, or None."""
    lines = text.split("\n")
    table_lines: list[str] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
            in_table = True
            table_lines.append(stripped)
        elif in_table:
            break
    return "\n".join(table_lines) if len(table_lines) >= 3 else None


def _markdown_table_to_csv(table_md: str, row_pages: list[int | None] | None = None) -> str:
    """Convert a Markdown pipe table to CSV via pandas.

    If row_pages is provided, a "Source Page" column is appended as the final column.
    Each data row i receives str(row_pages[i]) when an int, "Unresolved" when None,
    or "Unresolved" when index exceeds the list. Values are never blanked or guessed.
    """
    rows = []
    for line in table_md.strip().split("\n"):
        if re.match(r"^[\|\s\-:]+$", line.strip()):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip() != ""]
        if cells:
            rows.append(cells)
    if len(rows) < 2:
        return ""
    max_cols = max(len(r) for r in rows)
    rows = [r + [""] * (max_cols - len(r)) for r in rows]
    if row_pages is not None:
        rows[0] = rows[0] + ["Source Page"]
        for i, row in enumerate(rows[1:], 0):
            if i < len(row_pages):
                p = row_pages[i]
                page_str = str(p) if p is not None else "Unresolved"
            else:
                page_str = "Unresolved"
            rows[i + 1] = row + [page_str]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


# ── Document index persistence ────────────────────────────────────────────────

def _save_documents_index() -> None:
    DOCUMENTS_INDEX_PATH.parent.mkdir(exist_ok=True)
    with open(DOCUMENTS_INDEX_PATH, "w") as f:
        json.dump(st.session_state.documents, f, indent=2)


def _load_documents_index() -> dict:
    if not DOCUMENTS_INDEX_PATH.exists():
        return {}
    try:
        with open(DOCUMENTS_INDEX_PATH) as f:
            data = json.load(f)
        return {
            doc_name: doc_info
            for doc_name, doc_info in data.items()
            if Path(doc_info.get("path", "")).exists()
        }
    except Exception:
        return {}


def _remove_document(doc_name: str) -> None:
    from src.vector_store import reset_collection
    reset_collection(doc_name)
    st.session_state.documents.pop(doc_name, None)
    if st.session_state.current_doc == doc_name:
        remaining = list(st.session_state.documents.keys())
        st.session_state.current_doc = remaining[0] if remaining else None
        st.session_state.chat_history = []
        st.session_state.cited_page = None
    _save_documents_index()


# ── Session state ─────────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "page": "dashboard",
        "documents": {},       # doc_name → {path, page_count, chunks, liabilities}
        "current_doc": None,
        "chat_history": [],    # [{role, content, cited_pages?}]
        "cited_page": None,
        "auto_prompt": None,
        "pdf_page_nav": 1,
        "pdf_current_page": 1,
        "pdf_zoom": 100,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Recover already-indexed documents after a browser refresh
    if not st.session_state.documents:
        recovered = _load_documents_index()
        if recovered:
            st.session_state.documents = recovered
            if not st.session_state.current_doc:
                st.session_state.current_doc = next(iter(recovered))


_init_state()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        f"""
        <div style="display:flex;flex-direction:column;height:100%;padding:24px 12px 20px;">
            <div style="padding:0 8px 18px;border-bottom:1px solid #e2e8f0;">
                {_clearvault_brand(show_subtitle=True, mark_size=40)}
            </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Initialize Audit", key="btn_init", use_container_width=True, type="primary", icon=":material/play_arrow:"):
        st.session_state.page = "document_hub"
        st.rerun()

    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
    st.markdown('<div style="padding:0 8px 6px;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:#64748b;">Navigation</div>', unsafe_allow_html=True)

    _nav_items = [
        ("dashboard",        ":material/dashboard:", "Project Dashboard"),
        ("document_hub",     ":material/upload_file:", "Document Hub"),
        ("audit_analysis",   ":material/query_stats:", "Audit Analysis"),
        ("liability_reports", ":material/description:", "Liability Reports"),
    ]
    for _pg_key, _icon, _pg_label in _nav_items:
        _is_active = st.session_state.page == _pg_key
        if st.button(_pg_label, key=f"nav_{_pg_key}", use_container_width=True, type="primary" if _is_active else "secondary", icon=_icon):
            st.session_state.page = _pg_key
            st.rerun()

    st.markdown('<div style="flex:1 1 auto;"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div style="padding:12px 8px 0;border-top:1px solid #e2e8f0;display:flex;flex-direction:column;gap:4px;">
            <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:4px;color:#475569;font-size:12px;font-weight:500;">
                <span class="material-symbols-outlined" style="font-size:16px;color:#069669;">verified_user</span>
                <span>SOC 2 Type II Compliant</span>
            </div>
            <div style="display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:4px;color:#475569;font-size:12px;font-weight:500;">
                <span class="material-symbols-outlined" style="font-size:16px;">settings</span>
                <span>System Settings</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)


# ── Top bar ───────────────────────────────────────────────────────────────────

def _top_bar(active_tab: str = "Due Diligence"):
    tabs = ["Portfolio", "Due Diligence", "Archive"]
    tab_html = ""
    for t in tabs:
        if t == active_tab:
            tab_html += (
                f'<span style="height:100%;display:inline-flex;align-items:center;'
                f'font-size:13px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;'
                f'color:#0f172a;border-bottom:2px solid #0f172a;padding-bottom:2px;">{t}</span>'
            )
        else:
            tab_html += (
                f'<span style="height:100%;display:inline-flex;align-items:center;'
                f'font-size:13px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;'
                f'color:#94a3b8;cursor:pointer;">{t}</span>'
            )

    # Inline ClearVault logo for the top bar
    logo_svg = _clearvault_mark(size=28)

    st.markdown(
        f"""
        <div style="background:#f8fafc;border-bottom:1px solid #e2e8f0;
                    padding:0 24px;height:56px;display:flex;align-items:center;
                    justify-content:space-between;position:sticky;top:0;z-index:100;">
            <div style="display:flex;align-items:center;gap:32px;height:100%;">
                <div style="display:flex;align-items:center;gap:10px;">
                    {logo_svg}
                    <span style="font-size:16px;font-weight:700;color:#0f172a;letter-spacing:-0.03em;">
                        ClearVault
                    </span>
                </div>
                <div style="display:flex;gap:24px;height:100%;align-items:center;">{tab_html}</div>
            </div>
            <div style="display:flex;align-items:center;gap:16px;">
                <div style="position:relative;display:flex;align-items:center;">
                    <span class="material-symbols-outlined" style="position:absolute;left:10px;top:50%;transform:translateY(-50%);font-size:16px;color:#94a3b8;">search</span>
                    <input type="text" value="" placeholder="Search parameters..." style="width:256px;height:32px;padding:0 12px 0 32px;border:1px solid #e2e8f0;border-radius:4px;font-size:12px;color:#0f172a;background:white;outline:none;" />
                </div>
                <div style="display:flex;align-items:center;gap:2px;border-right:1px solid #e2e8f0;padding-right:14px;">
                    <button style="width:32px;height:32px;border:none;background:transparent;color:#64748b;border-radius:4px;display:flex;align-items:center;justify-content:center;cursor:pointer;">
                        <span class="material-symbols-outlined" style="font-size:20px;">notifications_active</span>
                    </button>
                    <button style="width:32px;height:32px;border:none;background:transparent;color:#64748b;border-radius:4px;display:flex;align-items:center;justify-content:center;cursor:pointer;">
                        <span class="material-symbols-outlined" style="font-size:20px;">help_outline</span>
                    </button>
                </div>
                <div style="display:flex;align-items:center;gap:10px;">
                    <span style="font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#64748b;">Secure Logout</span>
                    <div style="width:32px;height:32px;border-radius:9999px;background:#e2e8f0;border:1px solid #cbd5e1;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#475569;">SA</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Document processing ───────────────────────────────────────────────────────

def _process_document(pdf_path: str):
    from src.extractor import extract_pages
    from src.vector_store import index_document
    from src.llm import extract_liabilities

    doc_name = Path(pdf_path).name

    if doc_name in st.session_state.documents:
        st.info(f"✓ **{doc_name}** is already indexed.")
        return

    with st.status(f"Processing {doc_name}…", expanded=True) as status:
        # ── Step 1: Render pages to images ────────────────────────────────
        st.write("📄 **Local Structuring** — rendering PDF pages to images…")
        prog1 = st.progress(0.0, text="Local Structuring")

        pages = extract_pages(
            pdf_path,
            on_progress=lambda done, total: prog1.progress(
                done / total,
                text=f"Local Structuring — page {done}/{total}",
            ),
        )
        page_count = len(pages)

        st.write(f"✅ Rendered **{page_count} pages** to local image cache")

        # ── Step 2: Vision embedding + indexing ───────────────────────────
        st.write("🔍 **Vision Embedding** — indexing with ColQwen2…")
        st.caption("Loading vision model on first run — this may take a few minutes.")
        prog2 = st.progress(0.0, text="Vision Embedding — loading model…")

        index_document(
            pages,
            doc_name,
            on_progress=lambda done, total: prog2.progress(
                done / total,
                text="Vision Embedding — loading model…" if done == 0
                     else "Vision Embedding — complete",
            ),
        )

        st.write(f"✅ Indexed **{page_count} pages** with visual patch embeddings")

        # ── Step 3: AI Liability Scan ─────────────────────────────────────
        st.write("⚠️ **AI Liability Scan** — scanning with Gemini Vision…")

        step = max(1, page_count // 10)
        scan_pages = [
            {"image_path": p.image_path, "page_num": p.page_num}
            for p in pages[::step][:10]
        ]

        try:
            liabilities = extract_liabilities(scan_pages)
        except Exception as e:
            st.warning(f"Liability scan failed: {e}")
            liabilities = []

        st.write(f"✅ Identified **{len(liabilities)} potential liabilities**")

        st.session_state.documents[doc_name] = {
            "path": pdf_path,
            "page_count": page_count,
            "chunk_count": page_count,
            "liabilities": liabilities,
            "image_dir": str(Path("data") / "images" / Path(pdf_path).stem),
        }
        st.session_state.current_doc = doc_name
        _save_documents_index()

        status.update(
            label=f"✅ {doc_name} — Processing Complete",
            state="complete",
        )

    st.success("Ready. Navigate to **Audit Analysis** to ask questions.")


# ── Page: Dashboard ───────────────────────────────────────────────────────────

def _page_dashboard():
    _top_bar("Portfolio")

    st.markdown('<div class="page-shell">', unsafe_allow_html=True)

    docs = st.session_state.documents
    total_docs = len(docs)
    total_risks = sum(len(d.get("liabilities", [])) for d in docs.values())
    critical_count = sum(
        1
        for d in docs.values()
        for l in d.get("liabilities", [])
        if l.get("severity", "").upper() == "CRITICAL"
    )

    st.markdown(
        f"""
        <div class="page-header">
            <div>
                <h2 class="page-title">Operations Dashboard</h2>
                <p class="page-subtitle">Real-time telemetry for active due diligence projects.</p>
            </div>
            <div class="surface-card" style="padding:10px 14px;display:flex;align-items:center;gap:10px;">
                {_clearvault_mark(size=24)}
                <div style="display:flex;flex-direction:column;line-height:1;">
                    <span style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#191c1e;margin-bottom:3px;">Secure Status</span>
                    <span style="font-size:12px;font-weight:600;color:#069669;">SOC 2 Type II · E2E Encrypted</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3)
    metric_data = [
        (m1, "Documents Audited", str(total_docs), f"{total_docs} active", "description"),
        (m2, "Identified Risks", str(total_risks), f"{critical_count} Critical · {total_risks - critical_count} Other", "warning"),
        (m3, "Processing Velocity", "1.2s", "avg per page", "speed"),
    ]
    for col, label, value, sub, icon in metric_data:
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;">
                        <div style="font-size:12px;font-weight:600;letter-spacing:0.05em;color:#475569;text-transform:uppercase;">{label}</div>
                        <span class="material-symbols-outlined" style="font-size:18px;color:#76777d;">{icon}</span>
                    </div>
                    <div style="font-size:30px;line-height:1;font-weight:600;color:#191c1e;letter-spacing:-0.02em;">{value}</div>
                    <div style="margin-top:10px;display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:4px;background:#ecfdf5;color:#069669;font-size:11px;font-weight:600;border:1px solid rgba(5,150,105,0.16);">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    content_col, telemetry_col = st.columns([8, 4], gap="large")
    with content_col:
        st.markdown(_section_label("Active Projects"), unsafe_allow_html=True)
        st.markdown('<div class="table-shell">', unsafe_allow_html=True)
        st.markdown(
            '<div class="table-header" style="grid-template-columns:2fr 80px 80px 80px 120px;">'
            '<span style="font-size:12px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#475569;">Document</span>'
            '<span style="font-size:12px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#475569;">Pages</span>'
            '<span style="font-size:12px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#475569;">Chunks</span>'
            '<span style="font-size:12px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#475569;">Risks</span>'
            '<span style="font-size:12px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#475569;">Status</span>'
            '</div>',
            unsafe_allow_html=True,
        )

        if docs:
            for doc_name, doc_info in docs.items():
                n_risks = len(doc_info.get("liabilities", []))
                crit = len([l for l in doc_info.get("liabilities", []) if l.get("severity", "").upper() == "CRITICAL"])
                st.markdown(
                    f"""
                    <div class="table-row" style="grid-template-columns:2fr 80px 80px 80px 120px;">
                        <div>
                            <div style="font-size:14px;font-weight:600;color:#191c1e;">{doc_name}</div>
                            <div style="font-size:12px;color:#475569;margin-top:3px;">Indexed locally and ready for analysis.</div>
                        </div>
                        <div style="font-size:14px;color:#475569;">{doc_info.get('page_count', 0)}</div>
                        <div style="font-size:14px;color:#475569;">{doc_info.get('chunk_count', 0)}</div>
                        <div style="font-size:14px;color:#475569;">{n_risks}{f' <span style=\"color:#93000a;font-weight:600;\">({crit} crit)</span>' if crit else ''}</div>
                        <div>{_badge('✓ INDEXED', 'indexed')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                _card(
                    '<div style="text-align:center;padding:36px 0;">'
                    '<div style="font-size:40px;margin-bottom:12px;">📁</div>'
                    '<div style="font-size:18px;font-weight:600;color:#191c1e;margin-bottom:6px;">No documents audited yet</div>'
                    '<div style="font-size:14px;color:#475569;">Upload a PDF in the Document Hub to begin.</div>'
                    '</div>',
                    padding="0",
                ),
                unsafe_allow_html=True,
            )
            if st.button("View Document Hub", type="primary"):
                st.session_state.page = "document_hub"
                st.rerun()

    with telemetry_col:
        st.markdown(_section_label("Audit Telemetry"), unsafe_allow_html=True)
        st.markdown(
            _card(
                """
                <div style="display:flex;flex-direction:column;gap:16px;position:relative;padding-left:14px;">
                    <div style="position:absolute;left:19px;top:10px;bottom:10px;width:1px;background:#e0e3e5;"></div>
                    <div style="position:relative;padding-left:22px;">
                        <div style="position:absolute;left:0;top:4px;width:8px;height:8px;border-radius:9999px;background:#069669;box-shadow:0 0 0 4px #ffffff;"></div>
                        <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start;margin-bottom:4px;">
                            <div style="font-size:12px;font-weight:600;color:#191c1e;">Contract Scanned</div>
                            <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:0.05em;">Just now</div>
                        </div>
                        <div style="font-size:13px;line-height:18px;color:#475569;">Master Service Agreement verified locally.</div>
                    </div>
                    <div style="position:relative;padding-left:22px;">
                        <div style="position:absolute;left:0;top:4px;width:8px;height:8px;border-radius:9999px;background:#ba1a1a;box-shadow:0 0 0 4px #ffffff;"></div>
                        <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start;margin-bottom:4px;">
                            <div style="font-size:12px;font-weight:600;color:#191c1e;">Liability Flagged</div>
                            <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:0.05em;">2m ago</div>
                        </div>
                        <div style="font-size:13px;line-height:18px;color:#475569;">Undefined indemnification clause found in vendor annex.</div>
                    </div>
                    <div style="position:relative;padding-left:22px;">
                        <div style="position:absolute;left:0;top:4px;width:8px;height:8px;border-radius:9999px;background:#0f172a;box-shadow:0 0 0 4px #ffffff;"></div>
                        <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start;margin-bottom:4px;">
                            <div style="font-size:12px;font-weight:600;color:#191c1e;">Batch Processing Complete</div>
                            <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:0.05em;">15m ago</div>
                        </div>
                        <div style="font-size:13px;line-height:18px;color:#475569;">54 employee non-compete agreements indexed for the active deal.</div>
                    </div>
                    <div style="position:relative;padding-left:22px;">
                        <div style="position:absolute;left:0;top:4px;width:8px;height:8px;border-radius:9999px;background:#c6c6cd;box-shadow:0 0 0 4px #ffffff;"></div>
                        <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start;margin-bottom:4px;">
                            <div style="font-size:12px;font-weight:600;color:#191c1e;">Node Sync</div>
                            <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:0.05em;">1h ago</div>
                        </div>
                        <div style="font-size:13px;line-height:18px;color:#475569;">Local encrypted cache synchronized with the terminal.</div>
                    </div>
                </div>
                """,
                padding="16px",
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    latest_doc = st.session_state.current_doc or (next(iter(docs)) if docs else None)
    st.markdown(_section_label("Latest Priority Document"), unsafe_allow_html=True)
    st.markdown(
        _card(
            f"""
            <div style="padding:0;overflow:hidden;">
                <div style="background:#f7f9fb;padding:10px 16px;border-bottom:1px solid #e0e3e5;display:flex;justify-content:space-between;align-items:center;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span class="material-symbols-outlined" style="font-size:16px;color:#475569;">description</span>
                        <span style="font-size:13px;font-weight:600;color:#191c1e;">{latest_doc or 'Alpha_Financials_Q3_Audited.pdf'}</span>
                    </div>
                    <div style="display:inline-flex;align-items:center;gap:6px;padding:4px 8px;border-radius:4px;background:#ecfdf5;color:#069669;border:1px solid rgba(5,150,105,0.16);font-size:11px;font-weight:600;">
                        <span class="material-symbols-outlined" style="font-size:12px;">verified</span>
                        Security Verified
                    </div>
                </div>
                <div style="background:#2c3136;padding:16px;display:flex;justify-content:center;align-items:flex-start;min-height:190px;position:relative;overflow:hidden;">
                    <div style="background:white;width:100%;max-width:720px;min-height:230px;border:1px solid #e0e3e5;box-shadow:0 1px 3px rgba(0,0,0,0.05);padding:18px;opacity:0.55;display:flex;flex-direction:column;gap:10px;">
                        <div style="height:10px;width:34%;background:#e2e8f0;border-radius:9999px;"></div>
                        <div style="height:8px;width:100%;background:#f1f5f9;border-radius:9999px;margin-top:10px;"></div>
                        <div style="height:8px;width:84%;background:#f1f5f9;border-radius:9999px;"></div>
                        <div style="height:8px;width:72%;background:#f1f5f9;border-radius:9999px;"></div>
                        <div style="margin-top:14px;border-top:1px solid #e2e8f0;padding-top:10px;display:flex;flex-direction:column;gap:8px;">
                            <div style="display:flex;gap:8px;"><div style="height:6px;width:25%;background:#e2e8f0;"></div><div style="height:6px;width:25%;background:#e2e8f0;"></div></div>
                            <div style="display:flex;gap:8px;"><div style="height:6px;width:25%;background:#f1f5f9;"></div><div style="height:6px;width:25%;background:#f1f5f9;"></div></div>
                        </div>
                    </div>
                    <div style="position:absolute;inset:0;background:linear-gradient(to top,#2c3136 0%,rgba(44,49,54,0.0) 50%,rgba(44,49,54,0.0) 100%);"></div>
                    <button style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:#0f172a;color:white;border:1px solid rgba(255,255,255,0.2);padding:10px 16px;border-radius:4px;font-size:12px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;">Open Secure Viewer</button>
                </div>
            </div>
            """,
            padding="0",
        ),
        unsafe_allow_html=True,
    )

    st.markdown('</div>', unsafe_allow_html=True)


# ── Page: Document Hub ────────────────────────────────────────────────────────

def _page_document_hub():
    _top_bar("Due Diligence")

    st.markdown('<div class="page-shell">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="page-header">
            <div>
                <h2 class="page-title">Document Ingestion</h2>
                <p class="page-subtitle">Upload scanned VDR PDFs and extract cell-aligned, Excel-ready financial tables in under 60 seconds.</p>
            </div>
            <div class="surface-card" style="padding:10px 14px;display:flex;align-items:center;gap:10px;">
                {_clearvault_mark(size=24)}
                <span style="font-size:12px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#069669;">SOC 2 Type II · Zero-Data-Retention DPA</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sample_path = Path("samples/klaviyo_s1.pdf")
    if sample_path.exists() and "klaviyo_s1.pdf" not in st.session_state.documents:
        st.markdown(
            f"""
            <div class="surface-card" style="margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;gap:12px;">
                <div style="display:flex;align-items:center;gap:12px;min-width:0;">
                    <div style="display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:9999px;background:#eff6ff;color:#1d4ed8;border:1px solid rgba(37,99,235,0.15);font-size:11px;font-weight:600;">SAMPLE</div>
                    <div style="min-width:0;">
                        <div style="font-size:14px;font-weight:600;color:#191c1e;">klaviyo_s1.pdf</div>
                        <div style="font-size:12px;color:#475569;">Klaviyo S-1 Filing (SEC EDGAR, 2023) · 5.6 MB</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Load Sample", type="primary", use_container_width=False):
            _process_document(str(sample_path))
            st.rerun()

    st.markdown(
        """
        <div style="background:#eff6ff;border:1px solid rgba(37,99,235,0.15);border-radius:4px;
                    padding:16px 20px;margin-bottom:16px;">
            <div style="font-size:12px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;
                        color:#1d4ed8;margin-bottom:6px;">How it works</div>
            <div style="font-size:14px;color:#191c1e;line-height:1.7;">
                Drag a scanned VDR PDF. Ask: <em>"Extract the 2023 depreciation schedule."</em>
                Receive a cell-aligned, source-traced Excel table in under 60 seconds.
            </div>
        </div>
        <div style="background:#f0fdf4;border:1px solid rgba(5,150,105,0.20);border-radius:4px;
                    padding:12px 16px;margin-bottom:16px;display:flex;align-items:flex-start;gap:10px;">
            <span class="material-symbols-outlined"
                  style="font-size:18px;color:#059669;margin-top:1px;flex-shrink:0;">document_scanner</span>
            <div>
                <div style="font-size:13px;font-weight:700;color:#065f46;margin-bottom:3px;">
                    Built for scanned PDFs
                </div>
                <div style="font-size:13px;color:#475569;line-height:1.5;">
                    Handles merged cells, split footnotes, low-quality scans, and broken column
                    alignment — the messy financial tables that VDR-native AI cannot accurately
                    extract at cell level.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(_section_label("Drop VDR PDF"), unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Drop VDR PDF",
        type=["pdf"],
        label_visibility="collapsed",
        help='Drag a scanned VDR PDF. Ask: "Extract the 2023 depreciation schedule." Receive a cell-aligned, source-traced Excel table in under 60 seconds.',
    )

    if uploaded is not None:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        save_path = data_dir / uploaded.name
        with open(save_path, "wb") as f:
            f.write(uploaded.getbuffer())
        _process_document(str(save_path))
        st.rerun()

    if st.session_state.documents:
        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
        st.markdown(_section_label(f"Active Processing Queue · {len(st.session_state.documents)}"), unsafe_allow_html=True)

        for doc_name, doc_info in list(st.session_state.documents.items()):
            n_risks = len(doc_info.get("liabilities", []))
            card_col, btn_col = st.columns([13, 1])
            with card_col:
                st.markdown(
                    f"""
                    <div class="queue-card" style="padding:16px;margin-bottom:0;box-shadow:0 4px 6px rgba(0,0,0,0.02);">
                        <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:16px;">
                            <div style="display:flex;align-items:center;gap:12px;min-width:0;">
                                <div style="width:32px;height:32px;background:#ffdad6;color:#93000a;border-radius:4px;border:1px solid rgba(186,26,26,0.2);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;">PDF</div>
                                <div style="min-width:0;">
                                    <div style="font-size:14px;font-weight:600;color:#191c1e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:520px;">{doc_name}</div>
                                    <div style="font-size:12px;color:#475569;">{doc_info.get('page_count', 0)} pages · {doc_info.get('chunk_count', 0)} chunks indexed · {n_risks} risks identified</div>
                                </div>
                            </div>
                            <div style="display:flex;align-items:center;gap:8px;color:#069669;font-size:11px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;">
                                <span class="material-symbols-outlined" style="font-size:16px;">check_circle</span>
                                Indexed
                            </div>
                        </div>
                        <div style="display:flex;flex-direction:column;gap:12px;">
                            <div style="display:flex;flex-direction:column;gap:6px;">
                                <div style="display:flex;justify-content:space-between;align-items:end;">
                                    <span style="font-size:11px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#475569;">Local Structuring</span>
                                    <span style="font-size:13px;color:#0f172a;font-weight:600;">100%</span>
                                </div>
                                <div style="height:6px;background:#e0e3e5;border-radius:9999px;overflow:hidden;"><div style="height:100%;width:100%;background:#069669;border-radius:9999px;"></div></div>
                            </div>
                            <div style="display:flex;flex-direction:column;gap:6px;">
                                <div style="display:flex;justify-content:space-between;align-items:end;">
                                    <span style="font-size:11px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#475569;">OCR Analysis &amp; Extraction</span>
                                    <span style="font-size:13px;color:#0f172a;font-weight:600;">100%</span>
                                </div>
                                <div style="height:6px;background:#e0e3e5;border-radius:9999px;overflow:hidden;"><div style="height:100%;width:100%;background:#069669;border-radius:9999px;"></div></div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with btn_col:
                st.markdown('<div style="padding-top:12px;"></div>', unsafe_allow_html=True)
                if st.button("✕", key=f"remove_{doc_name}", type="secondary", help=f"Remove {doc_name}"):
                    _remove_document(doc_name)
                    st.rerun()
            st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

        if st.button("Open in Audit Analysis", type="primary"):
            st.session_state.page = "audit_analysis"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ── Page: Audit Analysis ──────────────────────────────────────────────────────

def _set_page(p: int) -> None:
    st.session_state["pdf_current_page"] = p


def _handle_question(question: str, doc_name: str):
    from src.vector_store import query_document
    from src.llm import answer_with_citations

    st.session_state.chat_history.append({"role": "user", "content": question})

    chunks = query_document(question, doc_name, n_results=2)
    if not chunks:
        st.session_state.chat_history.append(
            {"role": "assistant", "content": "No relevant content found in the document.", "cited_pages": []}
        )
        return

    result = answer_with_citations(question, chunks, doc_name=doc_name)
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "cited_pages": result["cited_pages"],
            "is_verified": result.get("is_verified", True),
            "highlight_terms_by_page": result.get("highlight_terms_by_page", {}),
            "row_pages": result.get("row_pages", []),
            "provenance_cited_pages": result.get("provenance_cited_pages", []),
            "first_chunk_page": result.get("first_chunk_page"),
        }
    )
    _prov = result.get("provenance_cited_pages", [])
    if _prov:
        st.session_state["pdf_current_page"] = _prov[0]
    elif result["cited_pages"]:
        st.session_state["pdf_current_page"] = result["cited_pages"][0]
    elif result.get("first_chunk_page"):
        st.session_state["pdf_current_page"] = result["first_chunk_page"]
    if result["cited_pages"]:
        st.session_state.cited_page = result["cited_pages"][0]
        st.session_state["pdf_page_nav"] = result["cited_pages"][0]


def _render_page_image(pdf_path: str, page_num: int, page_count: int, zoom: int = 100):
    # Prefer pre-rendered images from the ingest pipeline (faster, consistent DPI)
    prerendered = Path("data") / "images" / Path(pdf_path).stem / f"page_{page_num:04d}.png"
    img_width = max(200, int(600 * zoom / 100))
    if prerendered.exists():
        st.image(str(prerendered), width=img_width)
        st.caption(f"Page {page_num} of {page_count}")
        return

    # Fallback: render on demand with PyMuPDF
    try:
        import fitz
        doc = fitz.open(pdf_path)
        if 1 <= page_num <= len(doc):
            page = doc[page_num - 1]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            st.image(pix.tobytes("png"), width=img_width)
            st.caption(f"Page {page_num} of {page_count}")
        doc.close()
    except Exception:
        with open(pdf_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<embed src="data:application/pdf;base64,{b64}" '
            f'width="100%" height="700px" type="application/pdf">',
            unsafe_allow_html=True,
        )


def _page_audit_analysis():
    _top_bar("Due Diligence")

    docs = st.session_state.documents
    if not docs:
        st.markdown('<div class="page-shell">', unsafe_allow_html=True)
        st.markdown(
            _card(
                '<div style="text-align:center;padding:32px 0;">'
                '<div style="font-size:14px;font-weight:600;color:#191c1e;margin-bottom:4px;">No documents indexed</div>'
                '<div style="font-size:13px;color:#475569;">Upload and process a PDF in the Document Hub first.</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        if st.button("→ Go to Document Hub", type="primary"):
            st.session_state.page = "document_hub"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    st.markdown('<div class="page-shell">', unsafe_allow_html=True)

    doc_options = list(docs.keys())
    current = st.session_state.current_doc or doc_options[0]
    if current not in doc_options:
        current = doc_options[0]

    st.markdown(
        f"""
        <div class="page-header" style="margin-bottom:12px;">
            <div>
                <h2 class="page-title">Audit Analysis</h2>
                <p class="page-subtitle">Ask questions over the selected filing and verify answers against the local PDF.</p>
            </div>
            <div class="surface-card" style="padding:10px 14px;display:flex;align-items:center;gap:10px;">
                {_clearvault_mark(size=24)}
                <div style="display:flex;flex-direction:column;line-height:1;">
                    <span style="font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#191c1e;margin-bottom:3px;">Analysis Terminal</span>
                    <span style="font-size:12px;font-weight:600;color:#475569;">Groq · Vision</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_sel, col_info = st.columns([3, 5])
    with col_sel:
        selected_doc = st.selectbox(
            "Active Document",
            doc_options,
            index=doc_options.index(current),
        )
        if selected_doc != st.session_state.current_doc:
            st.session_state.current_doc = selected_doc
            st.session_state.chat_history = []
            st.session_state.cited_page = None
            st.rerun()
    with col_info:
        # auto-prompt: execute a chip click before we render the page
        _auto_q = st.session_state.pop("auto_prompt", None)
        if _auto_q:
            with st.status(f"Analyzing: {_auto_q[:60]}…", expanded=True):
                _handle_question(_auto_q, selected_doc)
            st.rerun()
        doc_info = docs[selected_doc]
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;padding-top:31px;flex-wrap:wrap;">'
            + _badge("PDF", "info")
            + f'<span style="font-size:14px;font-weight:500;color:#475569;">📄 {doc_info.get("page_count",0)} pages · 🔗 {doc_info.get("page_count",0)} pages indexed</span>'
            + _badge("✓ Verified", "verified")
            + '</div>',
            unsafe_allow_html=True,
        )
    st.divider()

    # Dual-pane workspace
    chat_col, pdf_col = st.columns([5, 6], gap="small")

    # ── Left: chat ────────────────────────────────────────────────────────────
    with chat_col:
        with st.container(border=True):
            # Chat header
            st.markdown(
                '<div style="padding:12px 16px;border-bottom:1px solid #e0e3e5;display:flex;align-items:center;justify-content:space-between;background:#f7f9fb;">'
                '<div style="display:flex;align-items:center;gap:8px;">'
                f'{_clearvault_mark(size=22)}'
                '<span style="font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#191c1e;">Analysis Terminal</span>'
                "</div>"
                '<div style="display:flex;align-items:center;gap:6px;">'
                '<div style="width:8px;height:8px;border-radius:9999px;background:#069669;animation:pulse 2s infinite;"></div>'
                '<span style="font-size:12px;color:#475569;">Groq · Vision</span>'
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )

            # Chat history
            chat_area = st.container(height=360)
            with chat_area:
                if not st.session_state.chat_history:
                    st.markdown(
                        '<div style="text-align:center;padding:48px 16px;color:#94a3b8;">'
                        '<div style="font-size:28px;margin-bottom:12px;">💬</div>'
                        '<div style="font-size:16px;font-weight:600;color:#475569;margin-bottom:10px;">'
                        "Extract a table or ask a due diligence question</div>"
                        '<div style="font-size:14px;color:#94a3b8;line-height:1.7;">'
                        '"Extract the 2023 depreciation schedule."<br>'
                        '"Show the working capital components table."<br>'
                        '"What are the key liabilities in this document?"'
                        "</div></div>",
                        unsafe_allow_html=True,
                    )

                for _i, msg in enumerate(st.session_state.chat_history):
                    if msg["role"] == "user":
                        st.markdown(
                            f'<div style="display:flex;justify-content:flex-end;margin:8px 0;">'
                            f'<div style="background:#eceef0;border:1px solid #e0e3e5;color:#191c1e;'
                            f'padding:12px 16px;border-radius:8px 8px 2px 8px;font-size:14px;'
                            f'max-width:85%;line-height:1.6;">{msg["content"]}</div></div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        answer = msg["content"]

                        if msg.get("is_verified", True) is False:
                            st.warning(
                                "⚠️ SCANNED DOCUMENT DETECTED: No text layer found. "
                                "Cross-validation disabled. Extracted numbers may contain "
                                "AI hallucinations. Manual verification required."
                            )

                        st.markdown(
                            '<div style="display:flex;align-items:flex-start;gap:8px;margin:8px 0;">'
                            '<div style="width:28px;height:28px;background:#0f172a;border-radius:4px;'
                            'display:flex;align-items:center;justify-content:center;'
                            'flex-shrink:0;font-size:14px;color:white;margin-top:2px;">✦</div>'
                            '<div style="flex:1;">'
                            '<div style="font-size:13px;font-weight:600;color:#475569;margin-bottom:6px;">Audit Assistant</div>'
                            '<div style="background:white;border:1px solid #e0e3e5;box-shadow:0 1px 3px rgba(0,0,0,0.04);'
                            f'padding:16px;border-radius:2px 8px 8px 8px;font-size:14px;color:#191c1e;'
                            f'line-height:1.6;white-space:pre-wrap;">{answer}</div>',
                            unsafe_allow_html=True,
                        )

                        # Citation chips
                        cited = msg.get("cited_pages", [])
                        if cited:
                            chips = ""
                            for p in cited:
                                chips += (
                                    f'<span style="display:inline-flex;align-items:center;gap:4px;'
                                    f'background:#eff6ff;color:#1d4ed8;border:1px solid rgba(37,99,235,0.15);'
                                    f'padding:4px 10px;border-radius:4px;font-size:12px;font-weight:600;'
                                    f'cursor:pointer;margin:2px;" '
                                    f'title="Cited on page {p}">📄 Pg {p}</span>'
                                )
                            st.markdown(
                                f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid #f1f5f9;">'
                                f'<span style="font-size:12px;color:#94a3b8;margin-right:6px;">Source Citations:</span>'
                                f"{chips}</div>",
                                unsafe_allow_html=True,
                            )

                        st.markdown("</div></div>", unsafe_allow_html=True)

                        # CSV export + optional table-type tag — rendered outside the HTML card
                        _tbl = _extract_markdown_table(answer)
                        if _tbl:
                            _row_pages = msg.get("row_pages") or None
                            _csv = _markdown_table_to_csv(_tbl, row_pages=_row_pages)
                            if _csv:
                                _dl_col, _tag_col = st.columns([2, 3])
                                with _dl_col:
                                    st.download_button(
                                        label="⬇  Download Table as CSV",
                                        data=_csv,
                                        file_name=f"table_p{cited[0] if cited else _i}.csv",
                                        mime="text/csv",
                                        key=f"dl_{_i}",
                                    )
                                with _tag_col:
                                    _tag_options = [
                                        "Other",
                                        "Balance Sheet",
                                        "Income Statement / P&L",
                                        "Depreciation Schedule",
                                        "EBITDA Calculation",
                                        "Working Capital Components",
                                        "Cap Table",
                                    ]
                                    st.selectbox(
                                        "What type of table is this? (Optional — helps us improve)",
                                        options=_tag_options,
                                        index=0,
                                        key=f"table_tag_{_i}",
                                    )

            # Quick-prompt chips
            st.markdown(
                '<div style="padding:8px 12px 6px;border-top:1px solid #e0e3e5;'
                'background:#f8fafc;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;'
                'text-transform:uppercase;color:#94a3b8;margin-bottom:6px;">Quick extractions</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            _chip_row1 = st.columns(3)
            _chip_row2 = st.columns(3)
            for _ci, (_icon, _prompt) in enumerate(_SUGGESTED_PROMPTS):
                _col = _chip_row1[_ci] if _ci < 3 else _chip_row2[_ci - 3]
                with _col:
                    _short = (_icon + " " + _prompt[:22] + "…") if len(_prompt) > 22 else _icon + " " + _prompt
                    if st.button(_short, key=f"chip_{_ci}", use_container_width=True, type="secondary"):
                        st.session_state["auto_prompt"] = _prompt
                        st.rerun()

            # Input form
            with st.form("chat_form", clear_on_submit=True):
                question = st.text_input(
                    "question",
                    placeholder='e.g. "Extract the 2023 depreciation schedule."',
                    label_visibility="collapsed",
                )
                submitted = st.form_submit_button(
                    "Execute  →",
                    type="primary",
                    use_container_width=True,
                )

            if submitted and question.strip():
                with st.status("Analyzing…", expanded=True):
                    _handle_question(question.strip(), selected_doc)
                st.rerun()

            st.markdown(
                '<div style="text-align:center;padding:6px 0;">'
                '<span style="font-size:11px;color:#94a3b8;">AI analysis may require human verification.</span>'
                "</div>",
                unsafe_allow_html=True,
            )

    # ── Right: PDF viewer ─────────────────────────────────────────────────────
    with pdf_col:
        doc_info = docs[selected_doc]
        pdf_path = doc_info["path"]
        page_count = doc_info.get("page_count", 1)

        # Document header bar
        st.markdown(
            f'<div class="surface-card" style="padding:10px 16px;display:flex;align-items:center;justify-content:space-between;gap:12px;border-radius:4px 4px 0 0;border-bottom:none;">'
            f'<div style="display:flex;align-items:center;gap:10px;min-width:0;">'
            f'<span class="material-symbols-outlined" style="font-size:18px;color:#475569;">picture_as_pdf</span>'
            f'<span style="font-size:13px;font-weight:600;color:#191c1e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:420px;">{selected_doc}</span>'
            + _badge("Verified Copy", "verified")
            + '</div>'
            f'<div style="display:flex;align-items:center;gap:6px;color:#475569;">'
            f'<span class="material-symbols-outlined" style="font-size:18px;">zoom_out</span>'
            f'<span style="font-size:11px;font-weight:600;">100%</span>'
            f'<span class="material-symbols-outlined" style="font-size:18px;">zoom_in</span>'
            f'<span style="width:1px;height:16px;background:#e0e3e5;margin:0 6px;"></span>'
            f'<span class="material-symbols-outlined" style="font-size:18px;">download</span>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        # Page navigation — prev / page display / next
        cur_page = max(1, min(page_count, int(st.session_state.get("pdf_current_page", 1))))
        _pn_l, _pn_c, _pn_r = st.columns([1, 4, 1])
        with _pn_l:
            if st.button("← Prev", key="pdf_prev", use_container_width=True, type="secondary"):
                st.session_state["pdf_current_page"] = max(1, cur_page - 1)
                st.rerun()
        with _pn_c:
            st.markdown(
                f'<div style="text-align:center;font-size:14px;font-weight:600;'
                f'color:#191c1e;padding:7px 0;">Page {cur_page} of {page_count}</div>',
                unsafe_allow_html=True,
            )
        with _pn_r:
            if st.button("Next →", key="pdf_next", use_container_width=True, type="secondary"):
                st.session_state["pdf_current_page"] = min(page_count, cur_page + 1)
                st.rerun()

        # Zoom controls — + / zoom display / -
        zoom_level = int(st.session_state.get("pdf_zoom", 100))
        _z_l, _z_c, _z_r = st.columns([1, 4, 1])
        with _z_l:
            if st.button("−", key="zoom_out", use_container_width=True, type="secondary"):
                st.session_state["pdf_zoom"] = max(50, zoom_level - 25)
                st.rerun()
        with _z_c:
            st.markdown(
                f'<div style="text-align:center;font-size:12px;color:#94a3b8;padding:2px 0 8px;">'
                f'Zoom: {zoom_level}%</div>',
                unsafe_allow_html=True,
            )
        with _z_r:
            if st.button("+", key="zoom_in", use_container_width=True, type="secondary"):
                st.session_state["pdf_zoom"] = min(200, zoom_level + 25)
                st.rerun()

        # Collect provenance data from the most recent assistant message
        _prov_cited: list[int] = []
        _hl_by_page: dict[int, list[str]] = {}
        _first_chunk_pg: int | None = None
        _has_answer = False
        for _msg in reversed(st.session_state.chat_history):
            if _msg["role"] == "assistant":
                _prov_cited = _msg.get("provenance_cited_pages", [])
                _hl_by_page = _msg.get("highlight_terms_by_page", {})
                _first_chunk_pg = _msg.get("first_chunk_page")
                _has_answer = True
                break

        from src.extractor import render_page_with_highlights, render_thumbnail

        _query_id = sum(1 for _m in st.session_state.chat_history if _m["role"] == "assistant")

        if len(_prov_cited) >= 2:
            # Thumbnail strip on left + single highlighted page on right
            _thumb_col, _main_col = st.columns([1, 6])
            with _thumb_col:
                for _n in _prov_cited:
                    _thumb_bytes = render_thumbnail(pdf_path, _n, _hl_by_page.get(_n, []))
                    if _thumb_bytes:
                        st.image(_thumb_bytes, use_container_width=True)
                    st.button(
                        f"Page {_n}",
                        key=f"cv_thumb_btn_{_n}_{_query_id}",
                        on_click=_set_page,
                        args=(_n,),
                        use_container_width=True,
                    )
            with _main_col:
                st.caption(
                    f"Page {cur_page}  ·  Highlights on: {', '.join(str(_p) for _p in _prov_cited)}"
                )
                _terms = _hl_by_page.get(cur_page, [])
                _png, _ = render_page_with_highlights(pdf_path, cur_page, _terms)
                if _png:
                    st.image(_png, use_container_width=True)
                else:
                    _render_page_image(pdf_path, cur_page, page_count, zoom=zoom_level)

        elif len(_prov_cited) == 1:
            _pn = _prov_cited[0]
            _terms = _hl_by_page.get(_pn, [])
            _png, _ = render_page_with_highlights(pdf_path, _pn, _terms)
            if _png:
                st.image(_png, caption=f"Page {_pn}", use_container_width=True)
            else:
                _render_page_image(pdf_path, _pn, page_count, zoom=zoom_level)

        elif _has_answer and _first_chunk_pg is not None:
            with st.container(border=True):
                _render_page_image(pdf_path, _first_chunk_pg, page_count, zoom=zoom_level)
            st.caption("No deterministic source matches found for this answer.")

        else:
            # No answer yet — show nav-controlled page
            with st.container(border=True):
                _render_page_image(pdf_path, cur_page, page_count, zoom=zoom_level)

    st.markdown('</div>', unsafe_allow_html=True)


# ── Page: Liability Reports ───────────────────────────────────────────────────

def _page_liability_reports():
    _top_bar("Due Diligence")

    st.markdown('<div class="page-shell">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="page-header">
            <div>
                <h2 class="page-title">Liability Findings Register</h2>
                <p class="page-subtitle">Structured inventory of all identified liabilities, categorized by risk vector and verified against source documentation.</p>
            </div>
            <div style="display:flex;align-items:center;gap:10px;">
                <div class="surface-card" style="padding:10px 14px;display:flex;align-items:center;gap:10px;">
                    {_clearvault_mark(size=24)}
                    <span style="font-size:12px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:#0f172a;">Export to Due Diligence Report</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    docs = st.session_state.documents
    if not docs:
        st.markdown(
            _card(
                '<div style="text-align:center;padding:32px 0;">'
                '<div style="font-size:14px;font-weight:600;color:#191c1e;margin-bottom:4px;">No findings yet</div>'
                '<div style="font-size:13px;color:#475569;">Process a document to generate the liability report.</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Aggregate
    all_liabilities = []
    for doc_name, doc_info in docs.items():
        for l in doc_info.get("liabilities", []):
            all_liabilities.append({**l, "source_doc": doc_name})

    _is_demo = not all_liabilities
    if _is_demo:
        _demo_src = next(iter(docs.keys()), "Alpha_Financials_Q3_Audited.pdf")
        all_liabilities = [{**l, "source_doc": _demo_src, "verification": "PENDING"} for l in _DEMO_LIABILITIES]
        st.markdown(
            '<div style="display:inline-flex;align-items:center;gap:6px;padding:6px 12px;'
            'border-radius:4px;background:#eff6ff;border:1px solid rgba(37,99,235,0.15);'
            'color:#1d4ed8;font-size:12px;font-weight:600;margin-bottom:12px;">'
            '💡 Demo findings shown — run the AI Liability Scan to populate with real data.'
            '</div>',
            unsafe_allow_html=True,
        )

    # Metric cards
    _mc_total = len(all_liabilities)
    _mc_crit  = sum(1 for l in all_liabilities if l.get("severity","").upper() == "CRITICAL")
    _mc_high  = sum(1 for l in all_liabilities if l.get("severity","").upper() == "HIGH")
    _mc_other = _mc_total - _mc_crit - _mc_high
    _mc1, _mc2, _mc3, _mc4 = st.columns(4)
    for _col, _lbl, _val, _sub, _bg, _tc in [
        (_mc1, "Total Findings",     str(_mc_total), "across all documents",     "#f7f9fb", "#191c1e"),
        (_mc2, "Critical",           str(_mc_crit),  "immediate attention",      "#fff1f2", "#93000a"),
        (_mc3, "High",               str(_mc_high),  "elevated exposure",        "#fef3c7", "#92400e"),
        (_mc4, "Med / Low",          str(_mc_other), "monitor and track",        "#f0fdf4", "#065f46"),
    ]:
        with _col:
            st.markdown(
                f'<div class="metric-card" style="background:{_bg};">'
                f'<div style="font-size:11px;font-weight:600;letter-spacing:0.05em;'
                f'text-transform:uppercase;color:#475569;margin-bottom:12px;">{_lbl}</div>'
                f'<div style="font-size:32px;font-weight:700;color:{_tc};line-height:1;">{_val}</div>'
                f'<div style="margin-top:8px;font-size:12px;color:#64748b;">{_sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

    # Filters
    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    with col_f1:
        sev_filter = st.multiselect(
            "Severity",
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            default=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        )
    with col_f2:
        type_filter = st.multiselect(
            "Risk Type",
            ["Legal", "Financial", "Operational", "Compliance"],
            default=["Legal", "Financial", "Operational", "Compliance"],
        )

    sev_set = {s.upper() for s in sev_filter}
    filtered = [
        l for l in all_liabilities
        if l.get("severity", "").upper() in sev_set
        and l.get("risk_type", "") in type_filter
    ]

    # Summary strip
    crit = len([l for l in filtered if l.get("severity","").upper() == "CRITICAL"])
    high = len([l for l in filtered if l.get("severity","").upper() == "HIGH"])
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin:4px 0 16px 0;flex-wrap:wrap;">'
        f'<span style="font-size:14px;font-weight:700;color:#191c1e;">Total {len(filtered)}</span>'
        + _badge(f"⚠ {crit} Critical", "critical")
        + _badge(f"{high} High", "high")
        + f'<span style="font-size:14px;color:#475569;">· {len(filtered) - crit - high} other</span>'
        + "</div>",
        unsafe_allow_html=True,
    )

    if not filtered:
        st.info("No findings match the current filters.")
        return

    st.markdown('<div class="table-shell">', unsafe_allow_html=True)

    col_widths = "110px 90px 1fr 160px 60px 100px"
    st.markdown(
        f'<div class="table-header" style="grid-template-columns:{col_widths};">'
        + "".join(
            f'<span style="font-size:12px;font-weight:600;letter-spacing:0.05em;color:#475569;text-transform:uppercase;">{h}</span>'
            for h in ["Risk Type", "Severity", "Description", "Source Document", "Page", "Verification"]
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    sev_badge_map = {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "medium",
        "LOW": "low",
    }

    for i, l in enumerate(filtered):
        sev = l.get("severity", "MEDIUM").upper()
        bc = sev_badge_map.get(sev, "medium")
        st.markdown(
            f'<div class="table-row" style="grid-template-columns:{col_widths};align-items:start;">'
            f'<span style="font-size:13px;font-weight:600;color:#475569;">{l.get("risk_type","Unknown")}</span>'
            + _badge(sev, bc)
            + f'<span style="font-size:13px;color:#191c1e;line-height:1.5;">{l.get("description","")}</span>'
            f'<span style="font-size:13px;color:#475569;">{l.get("source_doc","")}</span>'
            f'<span style="font-size:13px;color:#475569;">{l.get("page","N/A")}</span>'
            + _badge("PENDING", "pending")
            + "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:13px;color:#94a3b8;margin-top:12px;">'
        f"Showing 1–{len(filtered)} of {len(filtered)} findings</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="surface-card" style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;">'
        '<span style="font-size:13px;color:#475569;">Showing 1-4 of 124 findings</span>'
        '<div style="display:flex;align-items:center;gap:4px;">'
        '<button style="width:32px;height:32px;border:1px solid #e0e3e5;background:white;border-radius:4px;color:#94a3b8;">‹</button>'
        '<button style="width:32px;height:32px;border:1px solid #e0e3e5;background:white;border-radius:4px;color:#0f172a;font-weight:600;">1</button>'
        '<button style="width:32px;height:32px;border:none;background:transparent;border-radius:4px;color:#475569;">2</button>'
        '<button style="width:32px;height:32px;border:none;background:transparent;border-radius:4px;color:#475569;">3</button>'
        '<span style="padding:0 4px;color:#94a3b8;">...</span>'
        '<button style="width:32px;height:32px;border:1px solid #e0e3e5;background:white;border-radius:4px;color:#475569;">›</button>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('</div>', unsafe_allow_html=True)


# ── Router ────────────────────────────────────────────────────────────────────

page = st.session_state.page

if page == "dashboard":
    _page_dashboard()
elif page == "document_hub":
    _page_document_hub()
elif page == "audit_analysis":
    _page_audit_analysis()
elif page == "liability_reports":
    _page_liability_reports()
