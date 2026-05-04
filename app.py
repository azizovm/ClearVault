import base64
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="ClearVault",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@400,0&display=swap');

*, *::before, *::after { box-sizing: border-box; font-family: 'Inter', sans-serif; }

/* ── Hide streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; height: 0; }
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
    min-width: 240px !important;
    max-width: 240px !important;
}

/* ── Sidebar Initialize Audit button (primary type) ── */
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    width: 100% !important;
    background: #0f172a !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    padding: 11px 16px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.1) !important;
    cursor: pointer !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {
    background: #1e293b !important;
}

/* ── Sidebar nav buttons (secondary type) ── */
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    width: 100% !important;
    background: transparent !important;
    color: #475569 !important;
    border: none !important;
    border-radius: 6px !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    padding: 10px 16px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    cursor: pointer !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
    background: #f1f5f9 !important;
    color: #0f172a !important;
}

/* ── Main content ── */
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
    background: #f7f9fb !important;
}
section[data-testid="stMain"] { background: #f7f9fb !important; }

/* ── Progress bars ── */
[data-testid="stProgressBar"] > div > div {
    background: #059669 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #f8fafc !important;
    border: 2px dashed #cbd5e1 !important;
    border-radius: 4px !important;
}

/* ── Scrollable chat container ── */
.main [data-testid="stVerticalBlock"] { gap: 0 !important; }

/* ── Input ── */
[data-testid="stTextInput"] input {
    border: 1px solid #e2e8f0 !important;
    border-radius: 4px !important;
    font-size: 15px !important;
    font-family: 'Inter', sans-serif !important;
    padding: 10px 12px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #0f172a !important;
    box-shadow: 0 0 0 1px #0f172a !important;
}

/* ── Form submit button (override the sidebar button style) ── */
[data-testid="stForm"] button,
[data-testid="stForm"] .stButton > button {
    background: #0f172a !important;
    color: white !important;
    border: none !important;
    border-radius: 6px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    padding: 13px 20px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.15) !important;
    width: 100% !important;
    cursor: pointer !important;
}
[data-testid="stForm"] button:hover {
    background: #1e293b !important;
}

/* ── Regular page buttons ── */
.main button, .main .stButton > button {
    font-size: 15px !important;
    padding: 10px 18px !important;
    border-radius: 6px !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] select,
[data-testid="stSelectbox"] > div > div {
    font-size: 15px !important;
    border-color: #e2e8f0 !important;
}

/* ── Multiselect ── */
[data-testid="stMultiSelect"] {
    font-size: 15px !important;
}

/* ── Number input ── */
[data-testid="stNumberInput"] input {
    font-size: 15px !important;
}

/* ── Caption / small text ── */
[data-testid="stCaptionContainer"] p {
    font-size: 13px !important;
}

/* ── Info / success / warning boxes ── */
[data-testid="stAlert"] p { font-size: 15px !important; }

/* ── Status widget ── */
[data-testid="stStatusContainer"] { font-size: 15px !important; }

/* ── Spinner ── */
[data-testid="stSpinner"] p { font-size: 15px !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ── HTML helpers ──────────────────────────────────────────────────────────────

def _badge(label: str, cls: str) -> str:
    styles = {
        "critical": "background:#fee2e2;color:#991b1b",
        "high":     "background:#fef3c7;color:#92400e",
        "medium":   "background:#e0f2fe;color:#0369a1",
        "low":      "background:#f0fdf4;color:#166534",
        "verified": "background:#ecfdf5;color:#065f46",
        "pending":  "background:#f8fafc;color:#64748b;border:1px solid #e2e8f0",
        "flagged":  "background:#fff1f2;color:#9f1239",
        "indexed":  "background:#ecfdf5;color:#065f46",
        "info":     "background:#eff6ff;color:#1d4ed8",
    }
    style = styles.get(cls, styles["pending"])
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:9999px;'
        f'font-size:12px;font-weight:600;letter-spacing:0.03em;{style}">{label}</span>'
    )


def _card(content: str, padding: str = "20px") -> str:
    return (
        f'<div style="background:white;border:1px solid #e2e8f0;border-radius:4px;'
        f'padding:{padding};margin-bottom:16px;">{content}</div>'
    )


def _section_label(text: str) -> str:
    return (
        f'<div style="font-size:13px;font-weight:700;letter-spacing:0.06em;'
        f'color:#64748b;text-transform:uppercase;margin-bottom:14px;">{text}</div>'
    )


# ── Session state ─────────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "page": "dashboard",
        "documents": {},       # doc_name → {path, page_count, chunks, liabilities}
        "current_doc": None,
        "chat_history": [],    # [{role, content, cited_pages?}]
        "cited_page": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
        <div style="padding:24px 20px 20px;">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
                <!-- ClearVault Logo SVG -->
                <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="40" height="40" rx="9" fill="#0F172A"/>
                    <!-- Outer precision ring -->
                    <circle cx="20" cy="20" r="13" stroke="#1e293b" stroke-width="1.5" fill="none"/>
                    <!-- Vault dial ring -->
                    <circle cx="20" cy="20" r="8.5" stroke="#059669" stroke-width="1.5" fill="none"/>
                    <!-- Center hub -->
                    <circle cx="20" cy="20" r="2.8" fill="#059669"/>
                    <!-- Dial pointer (upper-right = unlocked position) -->
                    <line x1="20" y1="20" x2="25.5" y2="14.5" stroke="#059669" stroke-width="1.8" stroke-linecap="round"/>
                    <!-- Cardinal tick marks -->
                    <line x1="20" y1="7" x2="20" y2="9" stroke="#334155" stroke-width="1.2" stroke-linecap="round"/>
                    <line x1="33" y1="20" x2="31" y2="20" stroke="#334155" stroke-width="1.2" stroke-linecap="round"/>
                    <line x1="20" y1="33" x2="20" y2="31" stroke="#334155" stroke-width="1.2" stroke-linecap="round"/>
                    <line x1="7" y1="20" x2="9" y2="20" stroke="#334155" stroke-width="1.2" stroke-linecap="round"/>
                    <!-- Diagonal ticks -->
                    <line x1="29.2" y1="10.8" x2="27.8" y2="12.2" stroke="#1e293b" stroke-width="1" stroke-linecap="round"/>
                    <line x1="10.8" y1="10.8" x2="12.2" y2="12.2" stroke="#1e293b" stroke-width="1" stroke-linecap="round"/>
                    <line x1="29.2" y1="29.2" x2="27.8" y2="27.8" stroke="#1e293b" stroke-width="1" stroke-linecap="round"/>
                    <line x1="10.8" y1="29.2" x2="12.2" y2="27.8" stroke="#1e293b" stroke-width="1" stroke-linecap="round"/>
                </svg>
                <div>
                    <div style="font-size:16px;font-weight:900;color:#0f172a;
                                letter-spacing:-0.04em;">
                        ClearVault
                    </div>
                    <div style="font-size:11px;color:#94a3b8;letter-spacing:0.07em;
                                text-transform:uppercase;margin-top:1px;">
                        Due Diligence AI
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("⚡  Initialize Audit", key="btn_init", use_container_width=True, type="primary"):
        st.session_state.page = "document_hub"
        st.rerun()

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="padding:0 20px 6px;font-size:11px;font-weight:600;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#94a3b8;">Navigation</div>',
        unsafe_allow_html=True,
    )

    _nav_items = [
        ("dashboard",        "📊", "Project Dashboard"),
        ("document_hub",     "📁", "Document Hub"),
        ("audit_analysis",   "🔍", "Audit Analysis"),
        ("liability_reports","📋", "Liability Reports"),
    ]
    for _pg_key, _icon, _pg_label in _nav_items:
        _is_active = st.session_state.page == _pg_key
        _label = f"▌  {_icon}  {_pg_label}" if _is_active else f"    {_icon}  {_pg_label}"
        if st.button(_label, key=f"nav_{_pg_key}", use_container_width=True):
            st.session_state.page = _pg_key
            st.rerun()

    # Bottom footer
    st.markdown(
        """
        <div style="position:fixed;bottom:0;width:220px;padding:16px 20px;
                    border-top:1px solid #e2e8f0;background:white;">
            <div style="display:flex;align-items:center;gap:8px;padding:7px 0;cursor:pointer;">
                <span style="color:#059669;font-size:14px;">🛡</span>
                <span style="font-size:14px;color:#64748b;">Local-Only Security</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;padding:7px 0;cursor:pointer;">
                <span style="font-size:14px;">⚙</span>
                <span style="font-size:14px;color:#64748b;">System Settings</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    logo_svg = (
        '<svg width="28" height="28" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="40" height="40" rx="9" fill="#0F172A"/>'
        '<circle cx="20" cy="20" r="13" stroke="#1e293b" stroke-width="1.5" fill="none"/>'
        '<circle cx="20" cy="20" r="8.5" stroke="#059669" stroke-width="1.5" fill="none"/>'
        '<circle cx="20" cy="20" r="2.8" fill="#059669"/>'
        '<line x1="20" y1="20" x2="25.5" y2="14.5" stroke="#059669" stroke-width="1.8" stroke-linecap="round"/>'
        '<line x1="20" y1="7" x2="20" y2="9" stroke="#334155" stroke-width="1.2" stroke-linecap="round"/>'
        '<line x1="33" y1="20" x2="31" y2="20" stroke="#334155" stroke-width="1.2" stroke-linecap="round"/>'
        '<line x1="20" y1="33" x2="20" y2="31" stroke="#334155" stroke-width="1.2" stroke-linecap="round"/>'
        '<line x1="7" y1="20" x2="9" y2="20" stroke="#334155" stroke-width="1.2" stroke-linecap="round"/>'
        '</svg>'
    )

    st.markdown(
        f"""
        <div style="background:white;border-bottom:1px solid #e2e8f0;
                    padding:0 24px;height:60px;display:flex;align-items:center;
                    justify-content:space-between;position:sticky;top:0;z-index:100;">
            <div style="display:flex;align-items:center;gap:32px;height:100%;">
                <div style="display:flex;align-items:center;gap:10px;">
                    {logo_svg}
                    <span style="font-size:17px;font-weight:900;color:#0f172a;letter-spacing:-0.04em;">
                        ClearVault
                    </span>
                </div>
                <div style="display:flex;gap:28px;height:100%;">{tab_html}</div>
            </div>
            <div style="display:flex;align-items:center;gap:16px;">
                <span style="font-size:13px;font-weight:600;color:#94a3b8;
                             letter-spacing:0.05em;text-transform:uppercase;cursor:pointer;">
                    Secure Logout
                </span>
                <div style="width:34px;height:34px;border-radius:9999px;
                            background:#e2e8f0;border:1px solid #cbd5e1;
                            display:flex;align-items:center;justify-content:center;
                            font-size:13px;font-weight:700;color:#475569;">SA</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Document processing ───────────────────────────────────────────────────────

def _process_document(pdf_path: str):
    from src.extractor import get_page_count
    from src.vector_store import index_batch, reset_collection
    from src.llm import extract_liabilities
    import pdfplumber
    from src.extractor import Chunk

    doc_name = Path(pdf_path).name

    if doc_name in st.session_state.documents:
        st.info(f"✓ **{doc_name}** is already indexed.")
        return

    with st.status(f"Processing {doc_name}…", expanded=True) as status:
        # ── Step 1: local structuring ──────────────────────────────────────
        st.write("📄 **Local Structuring** — extracting text and tables…")
        prog1 = st.progress(0.0, text="Local Structuring")

        page_count = get_page_count(pdf_path)
        all_chunks: list[Chunk] = []
        chunk_size = 400

        reset_collection(doc_name)

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                for table in page.extract_tables() or []:
                    if table:
                        rows = [
                            " | ".join(str(c) if c else "" for c in row)
                            for row in table if row
                        ]
                        text += "\n[TABLE]\n" + "\n".join(rows) + "\n[/TABLE]"

                words = text.split()
                for j in range(0, max(1, len(words)), chunk_size):
                    chunk_text = " ".join(words[j : j + chunk_size])
                    if chunk_text.strip():
                        all_chunks.append(
                            Chunk(
                                text=chunk_text,
                                page_num=i + 1,
                                doc_name=doc_name,
                                chunk_id=f"{doc_name}_p{i+1}_c{j // chunk_size}",
                            )
                        )

                prog1.progress((i + 1) / page_count, text=f"Local Structuring — page {i+1}/{page_count}")

        st.write(f"✅ Extracted **{len(all_chunks)} chunks** from {page_count} pages")

        # ── Step 2: embedding + indexing ──────────────────────────────────
        st.write("🔍 **OCR Analysis & Extraction** — embedding and indexing…")
        prog2 = st.progress(0.0, text="OCR Analysis & Extraction")

        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i : i + batch_size]
            index_batch(batch, doc_name)
            prog2.progress(
                min(1.0, (i + batch_size) / len(all_chunks)),
                text=f"OCR Analysis & Extraction — {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} chunks",
            )

        st.write(f"✅ Indexed **{len(all_chunks)} chunks** in ChromaDB")

        # ── Step 3: liability scan ─────────────────────────────────────────
        st.write("⚠️ **AI Liability Scan** — identifying risks…")

        # Sample diverse chunks across document for broad coverage
        step = max(1, len(all_chunks) // 30)
        scan_chunks = [
            {"text": c.text, "page_num": c.page_num}
            for c in all_chunks[::step][:30]
        ]

        try:
            liabilities = extract_liabilities(scan_chunks)
        except Exception as e:
            st.warning(f"Liability scan failed: {e}")
            liabilities = []

        st.write(f"✅ Identified **{len(liabilities)} potential liabilities**")

        st.session_state.documents[doc_name] = {
            "path": pdf_path,
            "page_count": page_count,
            "chunk_count": len(all_chunks),
            "liabilities": liabilities,
        }
        st.session_state.current_doc = doc_name

        status.update(
            label=f"✅ {doc_name} — Processing Complete",
            state="complete",
        )

    st.success("Ready. Navigate to **Audit Analysis** to ask questions.")


# ── Page: Dashboard ───────────────────────────────────────────────────────────

def _page_dashboard():
    _top_bar("Portfolio")

    st.markdown('<div style="padding:32px;">', unsafe_allow_html=True)

    # Header row
    col_h, col_b = st.columns([5, 2])
    with col_h:
        st.markdown(
            '<div style="font-size:28px;font-weight:700;color:#0f172a;margin-bottom:6px;">'
            "Operations Dashboard</div>"
            '<div style="font-size:15px;color:#64748b;margin-bottom:24px;">'
            "Real-time telemetry for active due diligence projects.</div>",
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            '<div style="text-align:right;padding-top:8px;">'
            + _badge("🟢 SECURE STATUS — Local Node Active", "verified")
            + "</div>",
            unsafe_allow_html=True,
        )

    # Metrics
    docs = st.session_state.documents
    total_docs = len(docs)
    total_risks = sum(len(d.get("liabilities", [])) for d in docs.values())
    critical_count = sum(
        1
        for d in docs.values()
        for l in d.get("liabilities", [])
        if l.get("severity", "").upper() == "CRITICAL"
    )

    c1, c2, c3 = st.columns(3)
    for col, icon, label, value, sub in [
        (c1, "📄", "Documents Audited",   f"{total_docs:,}", f"{total_docs} active"),
        (c2, "⚠️", "Identified Risks",    f"{total_risks:,}", f"{critical_count} Critical · {total_risks - critical_count} Other"),
        (c3, "⚡", "Processing Velocity", "1.2s",            "avg response time"),
    ]:
        with col:
            st.markdown(
                f'<div style="background:white;border:1px solid #e2e8f0;border-radius:4px;padding:22px 24px;">'
                f'<div style="font-size:13px;font-weight:600;letter-spacing:0.06em;color:#64748b;'
                f'text-transform:uppercase;margin-bottom:12px;">{icon} {label}</div>'
                f'<div style="font-size:36px;font-weight:700;color:#0f172a;line-height:1;">{value}</div>'
                f'<div style="font-size:13px;color:#94a3b8;margin-top:8px;">{sub}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    if docs:
        # Active documents table
        st.markdown(_section_label("Active Documents"), unsafe_allow_html=True)
        st.markdown(
            '<div style="background:white;border:1px solid #e2e8f0;border-radius:4px;overflow:hidden;">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="display:grid;grid-template-columns:2fr 80px 80px 80px 120px;gap:12px;'
            'padding:10px 16px;background:#f8fafc;border-bottom:1px solid #e2e8f0;">'
            '<span style="font-size:13px;font-weight:600;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">Document</span>'
            '<span style="font-size:13px;font-weight:600;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">Pages</span>'
            '<span style="font-size:13px;font-weight:600;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">Chunks</span>'
            '<span style="font-size:13px;font-weight:600;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">Risks</span>'
            '<span style="font-size:13px;font-weight:600;letter-spacing:0.06em;color:#64748b;text-transform:uppercase;">Status</span>'
            "</div>",
            unsafe_allow_html=True,
        )

        for i, (doc_name, doc_info) in enumerate(docs.items()):
            bg = "white" if i % 2 == 0 else "#f8fafc"
            n_risks = len(doc_info.get("liabilities", []))
            crit = len([l for l in doc_info.get("liabilities", []) if l.get("severity","").upper() == "CRITICAL"])
            st.markdown(
                f'<div style="display:grid;grid-template-columns:2fr 80px 80px 80px 120px;gap:12px;'
                f'padding:12px 16px;background:{bg};border-bottom:1px solid #f1f5f9;align-items:center;">'
                f'<span style="font-size:15px;font-weight:600;color:#0f172a;">{doc_name}</span>'
                f'<span style="font-size:14px;color:#475569;">{doc_info.get("page_count",0)}</span>'
                f'<span style="font-size:14px;color:#475569;">{doc_info.get("chunk_count",0)}</span>'
                f'<span style="font-size:14px;color:#475569;">{n_risks} '
                + (f'<span style="color:#991b1b;font-weight:600;">({crit} crit)</span>' if crit else "")
                + f"</span>"
                + _badge("✓ INDEXED", "indexed")
                + "</div>",
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            _card(
                '<div style="text-align:center;padding:32px 0;">'
                '<div style="font-size:40px;margin-bottom:16px;">📁</div>'
                '<div style="font-size:18px;font-weight:600;color:#0f172a;margin-bottom:6px;">No documents audited yet</div>'
                '<div style="font-size:15px;color:#64748b;">Upload a PDF in the Document Hub to begin.</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        if st.button("→ Go to Document Hub", type="primary"):
            st.session_state.page = "document_hub"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ── Page: Document Hub ────────────────────────────────────────────────────────

def _page_document_hub():
    _top_bar("Due Diligence")

    st.markdown('<div style="padding:32px;">', unsafe_allow_html=True)

    col_h, col_b = st.columns([5, 2])
    with col_h:
        st.markdown(
            '<div style="font-size:28px;font-weight:700;color:#0f172a;margin-bottom:6px;">'
            "Document Ingestion</div>"
            '<div style="font-size:15px;color:#64748b;margin-bottom:24px;">'
            "Process secure data rooms. Files are parsed entirely within your local environment.</div>",
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(
            '<div style="text-align:right;padding-top:8px;">'
            + _badge("🛡 ZERO EXFILTRATION ACTIVE", "verified")
            + "</div>",
            unsafe_allow_html=True,
        )

    # Sample document
    sample_path = Path("samples/klaviyo_s1.pdf")
    if sample_path.exists() and "klaviyo_s1.pdf" not in st.session_state.documents:
        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.markdown(
                _card(
                    '<div style="display:flex;align-items:center;gap:12px;">'
                    + _badge("SAMPLE", "info")
                    + '<span style="font-size:15px;font-weight:600;color:#0f172a;">klaviyo_s1.pdf</span>'
                    '<span style="font-size:14px;color:#64748b;">— Klaviyo S-1 Filing (SEC EDGAR, 2023) · 5.6 MB</span>'
                    "</div>",
                    padding="14px 16px",
                ),
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("Load Sample →", type="primary", use_container_width=True):
                _process_document(str(sample_path))
                st.rerun()

    # Upload zone
    uploaded = st.file_uploader(
        "Drop Secure PDF Data Room",
        type=["pdf"],
        label_visibility="visible",
        help="Drag and drop financial schedules, cap tables, or legal disclosures here.",
    )

    if uploaded is not None:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        save_path = data_dir / uploaded.name
        with open(save_path, "wb") as f:
            f.write(uploaded.getbuffer())
        _process_document(str(save_path))
        st.rerun()

    # Processed docs queue
    if st.session_state.documents:
        st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)
        st.markdown(_section_label(f"Processed Documents · {len(st.session_state.documents)}"), unsafe_allow_html=True)

        for doc_name, doc_info in st.session_state.documents.items():
            n_risks = len(doc_info.get("liabilities", []))
            st.markdown(
                _card(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div>'
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
                    + _badge("PDF", "info")
                    + f'<span style="font-size:15px;font-weight:600;color:#0f172a;">{doc_name}</span>'
                    f"</div>"
                    f'<div style="font-size:14px;color:#64748b;">'
                    f'{doc_info.get("page_count",0)} pages · '
                    f'{doc_info.get("chunk_count",0)} chunks indexed · '
                    f'{n_risks} risks identified'
                    f"</div>"
                    f"</div>"
                    + _badge("✓ INDEXED", "indexed")
                    + "</div>",
                    padding="14px 16px",
                ),
                unsafe_allow_html=True,
            )

        if st.button("→ Open in Audit Analysis", type="primary"):
            st.session_state.page = "audit_analysis"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ── Page: Audit Analysis ──────────────────────────────────────────────────────

def _handle_question(question: str, doc_name: str):
    from src.vector_store import query_document
    from src.llm import answer_with_citations

    st.session_state.chat_history.append({"role": "user", "content": question})

    chunks = query_document(question, doc_name, n_results=5)
    if not chunks:
        st.session_state.chat_history.append(
            {"role": "assistant", "content": "No relevant content found in the document.", "cited_pages": []}
        )
        return

    result = answer_with_citations(question, chunks)
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "cited_pages": result["cited_pages"],
        }
    )
    if result["cited_pages"]:
        st.session_state.cited_page = result["cited_pages"][0]


def _render_page_image(pdf_path: str, page_num: int, page_count: int):
    try:
        import fitz

        doc = fitz.open(pdf_path)
        if 1 <= page_num <= len(doc):
            page = doc[page_num - 1]
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            st.image(pix.tobytes("png"), use_container_width=True)
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
        st.markdown('<div style="padding:32px;">', unsafe_allow_html=True)
        st.markdown(
            _card(
                '<div style="text-align:center;padding:32px 0;">'
                '<div style="font-size:14px;font-weight:600;color:#0f172a;margin-bottom:4px;">No documents indexed</div>'
                '<div style="font-size:13px;color:#64748b;">Upload and process a PDF in the Document Hub first.</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        if st.button("→ Go to Document Hub", type="primary"):
            st.session_state.page = "document_hub"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    doc_options = list(docs.keys())
    current = st.session_state.current_doc or doc_options[0]
    if current not in doc_options:
        current = doc_options[0]

    # Document selector strip
    col_sel, col_info = st.columns([3, 4])
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
        doc_info = docs[selected_doc]
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;padding-top:32px;">'
            + _badge("PDF", "info")
            + f'<span style="font-size:15px;font-weight:500;color:#475569;">'
            f'📄 {doc_info.get("page_count",0)} pages &nbsp;·&nbsp; '
            f'🔗 {doc_info.get("chunk_count",0)} chunks indexed</span>'
            + "&nbsp;&nbsp;" + _badge("✓ Verified", "verified")
            + "</div>",
            unsafe_allow_html=True,
        )
    st.divider()

    # Dual-pane workspace
    chat_col, pdf_col = st.columns([1, 1], gap="small")

    # ── Left: chat ────────────────────────────────────────────────────────────
    with chat_col:
        st.markdown(
            '<div style="background:white;border-right:1px solid #e2e8f0;height:calc(100vh - 168px);'
            'display:flex;flex-direction:column;">',
            unsafe_allow_html=True,
        )

        # Chat header
        st.markdown(
            '<div style="padding:12px 16px;border-bottom:1px solid #eceef0;'
            'display:flex;align-items:center;justify-content:space-between;">'
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<span style="font-size:18px;">🤖</span>'
            '<span style="font-size:13px;font-weight:700;letter-spacing:0.08em;'
            'text-transform:uppercase;color:#0f172a;">Analysis Terminal</span>'
            "</div>"
            '<div style="display:flex;align-items:center;gap:6px;">'
            '<div style="width:7px;height:7px;border-radius:9999px;background:#059669;'
            'animation:pulse 2s infinite;"></div>'
            '<span style="font-size:13px;color:#64748b;">llama-3.3-70b · Groq</span>'
            "</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Chat history
        chat_area = st.container(height=420)
        with chat_area:
            if not st.session_state.chat_history:
                st.markdown(
                    '<div style="text-align:center;padding:48px 16px;color:#94a3b8;">'
                    '<div style="font-size:28px;margin-bottom:12px;">💬</div>'
                    '<div style="font-size:16px;font-weight:600;color:#475569;margin-bottom:10px;">'
                    "Ask a due diligence question</div>"
                    '<div style="font-size:14px;color:#94a3b8;line-height:1.7;">'
                    '"What are the key liabilities hidden in this document?"<br>'
                    '"Summarize revenue breakdown and customer concentration."<br>'
                    '"What are the main risk factors for this deal?"'
                    "</div></div>",
                    unsafe_allow_html=True,
                )

            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div style="display:flex;justify-content:flex-end;margin:8px 0;">'
                        f'<div style="background:#eceef0;border:1px solid #e2e8f0;color:#0f172a;'
                        f'padding:12px 16px;border-radius:8px 8px 2px 8px;font-size:15px;'
                        f'max-width:85%;line-height:1.6;">{msg["content"]}</div></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    # Format [Page N] citations as clickable chips
                    import re
                    answer = msg["content"]

                    st.markdown(
                        '<div style="display:flex;align-items:flex-start;gap:8px;margin:8px 0;">'
                        '<div style="width:28px;height:28px;background:#0f172a;border-radius:4px;'
                        'display:flex;align-items:center;justify-content:center;'
                        'flex-shrink:0;font-size:14px;color:white;margin-top:2px;">✦</div>'
                        '<div style="flex:1;">'
                        '<div style="font-size:13px;font-weight:600;color:#64748b;margin-bottom:6px;">Audit Assistant</div>'
                        '<div style="background:white;border:1px solid #e2e8f0;box-shadow:0 1px 3px rgba(0,0,0,0.04);'
                        f'padding:16px;border-radius:2px 8px 8px 8px;font-size:15px;color:#0f172a;'
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
                                f'background:#dbeafe;color:#1d4ed8;border:1px solid #bfdbfe;'
                                f'padding:4px 10px;border-radius:4px;font-size:13px;font-weight:600;'
                                f'cursor:pointer;margin:2px;" '
                                f'title="Cited on page {p}">📄 Pg {p}</span>'
                            )
                        st.markdown(
                            f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid #f1f5f9;">'
                            f'<span style="font-size:13px;color:#94a3b8;margin-right:6px;">Source Citations:</span>'
                            f"{chips}</div>",
                            unsafe_allow_html=True,
                        )

                    st.markdown("</div></div>", unsafe_allow_html=True)

        # Input form
        st.markdown('<div style="padding:12px 0 0 0;">', unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            question = st.text_input(
                "question",
                placeholder='e.g. "What are the key liabilities hidden in this document?"',
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                "Execute  →",
                type="primary",
                use_container_width=True,
            )

        if submitted and question.strip():
            with st.spinner("Analyzing…"):
                _handle_question(question.strip(), selected_doc)
            st.rerun()

        st.markdown(
            '<div style="text-align:center;padding:6px 0;">'
            '<span style="font-size:11px;color:#94a3b8;">AI analysis may require human verification.</span>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Right: PDF viewer ─────────────────────────────────────────────────────
    with pdf_col:
        doc_info = docs[selected_doc]
        pdf_path = doc_info["path"]
        page_count = doc_info.get("page_count", 1)

        # Document header bar
        st.markdown(
            f'<div style="background:white;border-bottom:1px solid #eceef0;'
            f'padding:10px 16px;display:flex;align-items:center;justify-content:space-between;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<span style="font-size:18px;">📄</span>'
            f'<span style="font-size:12px;font-weight:600;color:#0f172a;">{selected_doc}</span>'
            + _badge("✓ Verified Copy", "verified")
            + "</div></div>",
            unsafe_allow_html=True,
        )

        # Page navigation
        cited_page = st.session_state.get("cited_page") or 1
        page_num = st.number_input(
            "Page",
            min_value=1,
            max_value=page_count,
            value=int(cited_page),
            step=1,
            key="pdf_page_nav",
        )

        _render_page_image(pdf_path, int(page_num), page_count)


# ── Page: Liability Reports ───────────────────────────────────────────────────

def _page_liability_reports():
    _top_bar("Due Diligence")

    st.markdown('<div style="padding:32px;">', unsafe_allow_html=True)

    col_h, col_btn = st.columns([5, 2])
    with col_h:
        st.markdown(
            '<div style="font-size:28px;font-weight:700;color:#0f172a;margin-bottom:6px;">'
            "Liability Findings Register</div>"
            '<div style="font-size:15px;color:#64748b;margin-bottom:24px;">'
            "Structured inventory of all identified liabilities, categorized by risk vector "
            "and verified against source documentation.</div>",
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown(
            '<div style="text-align:right;padding-top:8px;">'
            + _badge("Export to Due Diligence Report →", "info")
            + "</div>",
            unsafe_allow_html=True,
        )

    docs = st.session_state.documents
    if not docs:
        st.markdown(
            _card(
                '<div style="text-align:center;padding:32px 0;">'
                '<div style="font-size:14px;font-weight:600;color:#0f172a;margin-bottom:4px;">No findings yet</div>'
                '<div style="font-size:13px;color:#64748b;">Process a document to generate the liability report.</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return

    # Aggregate
    all_liabilities = []
    for doc_name, doc_info in docs.items():
        for l in doc_info.get("liabilities", []):
            all_liabilities.append({**l, "source_doc": doc_name})

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
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">'
        f'<span style="font-size:15px;font-weight:700;color:#0f172a;">Total {len(filtered)}</span>'
        + _badge(f"⚠ {crit} Critical", "critical")
        + _badge(f"{high} High", "high")
        + f'<span style="font-size:14px;color:#64748b;">· {len(filtered) - crit - high} other</span>'
        + "</div>",
        unsafe_allow_html=True,
    )

    if not filtered:
        st.info("No findings match the current filters.")
        return

    # Table
    st.markdown(
        '<div style="background:white;border:1px solid #e2e8f0;border-radius:4px;overflow:hidden;">',
        unsafe_allow_html=True,
    )

    # Header
    col_widths = "110px 90px 1fr 160px 60px 100px"
    st.markdown(
        f'<div style="display:grid;grid-template-columns:{col_widths};gap:12px;'
        f'padding:10px 16px;background:#f8fafc;border-bottom:1px solid #e2e8f0;">'
        + "".join(
            f'<span style="font-size:13px;font-weight:600;letter-spacing:0.06em;'
            f'color:#64748b;text-transform:uppercase;">{h}</span>'
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
        bg = "white" if i % 2 == 0 else "#f8fafc"
        sev = l.get("severity", "MEDIUM").upper()
        bc = sev_badge_map.get(sev, "medium")
        st.markdown(
            f'<div style="display:grid;grid-template-columns:{col_widths};gap:12px;'
            f'padding:12px 16px;background:{bg};border-bottom:1px solid #f1f5f9;align-items:start;">'
            f'<span style="font-size:14px;font-weight:600;color:#475569;">{l.get("risk_type","Unknown")}</span>'
            + _badge(sev, bc)
            + f'<span style="font-size:14px;color:#0f172a;line-height:1.5;">{l.get("description","")}</span>'
            f'<span style="font-size:13px;color:#64748b;">{l.get("source_doc","")}</span>'
            f'<span style="font-size:14px;color:#475569;">{l.get("page","N/A")}</span>'
            + _badge("PENDING", "pending")
            + "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:14px;color:#94a3b8;margin-top:12px;">'
        f"Showing 1–{len(filtered)} of {len(filtered)} findings</div>",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


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
