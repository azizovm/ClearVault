# ClearVault — Due Diligence AI

A local-only, AI-powered tool for M&A / investment due diligence. Upload financial documents (PDFs), get instant Q&A with page citations, and receive an auto-generated liability findings register — all without your documents leaving your machine.

---

## What it does

1. **Ingest** a PDF (e.g. an S-1, cap table, legal disclosure). The app extracts all text and tables page-by-page and splits them into ~400-word chunks.
2. **Index** those chunks into a local ChromaDB vector store so they can be retrieved by semantic similarity.
3. **Scan** the document with an LLM (Groq / llama-3.3-70b) to identify liabilities, categorised by risk type and severity.
4. **Answer** due diligence questions in a chat interface. Every answer is grounded in the document and cites the exact page numbers.

Everything runs locally except the LLM calls, which go to Groq's API.

---

## Project structure

```
ClearVault-master/
├── app.py                # Streamlit app — all UI and page routing
├── src/
│   ├── extractor.py      # PDF → Chunk objects (pdfplumber)
│   ├── llm.py            # Groq API calls: Q&A with citations + liability scan
│   └── vector_store.py   # ChromaDB wrapper: index, query, reset
├── smoke-test.py         # One-shot test to verify Groq API key works
├── samples/
│   └── klaviyo_s1.pdf    # Demo document: Klaviyo SEC S-1 filing (2023)
└── .env.example          # Required environment variables
```

### `app.py`
The entire front-end. Four pages, routed via `st.session_state.page`:

| Page | Key | What it shows |
|------|-----|---------------|
| Project Dashboard | `dashboard` | Metrics (docs audited, total risks, critical count) and an indexed-documents table |
| Document Hub | `document_hub` | File uploader + sample loader; triggers the 3-step processing pipeline |
| Audit Analysis | `audit_analysis` | Split-pane chat + PDF viewer; ask questions and jump to cited pages |
| Liability Reports | `liability_reports` | Filterable table of all identified risks across all documents |

### `src/extractor.py`
- `Chunk` dataclass: `text`, `page_num`, `doc_name`, `chunk_id`
- `get_page_count(pdf_path)` — quick page count via pdfplumber
- `extract_chunks(pdf_path, chunk_size=400)` — full extraction (not used directly by the app, which does inline extraction for progress reporting)

### `src/llm.py`
- `answer_with_citations(question, chunks)` — sends retrieved chunks to llama-3.3-70b with a strict prompt that requires `[Page N]` inline citations; returns `answer`, `cited_pages`, `source_chunks`
- `extract_liabilities(chunks)` — sends a sample of chunks (up to 30, spread across the document) and parses structured findings: `risk_type`, `severity`, `description`, `page`

### `src/vector_store.py`
- Wraps a persistent `chromadb.PersistentClient` stored at `./chroma_db/`
- Each document gets its own ChromaDB collection (name is sanitised from the filename)
- `reset_collection` / `index_batch` — used together during ingestion for streaming progress
- `query_document(question, doc_name, n_results=5)` — returns the top-N semantically similar chunks for a question

---

## Setup

### Prerequisites
- Python 3.10+
- A free [Groq API key](https://console.groq.com/)

### Install

```bash
pip install streamlit pdfplumber chromadb groq python-dotenv pymupdf
```

### Configure

```bash
cp .env.example .env
# edit .env and set GROQ_API_KEY=your_key_here
```

### Run

```bash
streamlit run app.py
```

### Verify your API key

```bash
python smoke-test.py
# should print: ready
```

---

## How the processing pipeline works

When you upload (or load the sample) PDF:

1. **Local Structuring** — pdfplumber extracts text and inline tables page-by-page. Tables are formatted as pipe-delimited rows wrapped in `[TABLE]...[/TABLE]` markers.
2. **Embedding & Indexing** — chunks are added to ChromaDB in batches of 100. ChromaDB's default embedding model handles vectorisation locally.
3. **AI Liability Scan** — up to 30 evenly-spaced chunks are sent to Groq in one call. The LLM returns structured risk findings (type, severity, description, page) which are parsed and stored in session state.

---

## Sample document

`samples/klaviyo_s1.pdf` is Klaviyo's 2023 SEC S-1 filing — a real-world, multi-hundred-page financial disclosure. It's included so you can test the full pipeline immediately without sourcing your own document.

---

## Key design decisions

- **Local-only storage** — documents and vector embeddings never leave your machine; only question/context text is sent to Groq.
- **Session-scoped state** — all indexed documents live in `st.session_state`; restarting the app clears in-memory state but the ChromaDB files at `./chroma_db/` persist between runs.
- **No authentication** — this is a single-user local tool; the "Secure Logout" and "SA" avatar in the UI are decorative placeholders.
- **Groq / llama-3.3-70b** — chosen for speed and a free tier; swapping to another provider requires only editing `src/llm.py`.
