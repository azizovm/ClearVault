from __future__ import annotations

import base64
import os
import re
from typing import Optional

from dotenv import load_dotenv
from groq import Groq

from src.extractor import extract_page_text, find_pdf_path
from src.provenance import resolve_table_provenance, _extract_table_from_answer

load_dotenv()

_client: Optional[Groq] = None
# Groq'ta mevcut vision-capable model — değiştirmek istersen .env'e GROQ_MODEL ekle
_MODEL = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")
        _client = Groq(api_key=api_key)
    return _client


def _b64_to_data_url(b64: str) -> str:
    return f"data:image/png;base64,{b64}"


def _path_to_data_url(image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


_QA_PROMPT = """\
You are a senior M&A due diligence analyst. Answer the question using ONLY \
the document pages shown in the images above.

RULES:
- Cite every factual claim with [Page N] inline.
- Be specific and numerical where possible.
- If the answer contains ANY tabular data (financial statements, cap tables, \
schedules, comparisons), you MUST present it as a Markdown table using the | pipe \
syntax. Preserve exact row labels, column headers, and all cell values exactly \
as they appear in the document.
- Flag risks or red flags with ⚠️.
- If you cannot answer from the provided pages, say so explicitly.

Structure your response as:
1. Direct Answer (with [Page N] citations inline)
2. Key Findings (bullet points, each cited)
3. [Markdown table — mandatory when extracting financial or tabular data]
4. Risk Assessment (if applicable)"""


_LIABILITY_PROMPT = """\
You are an M&A risk analyst performing due diligence. Analyze the document pages \
shown above and identify ALL liabilities, risks, and red flags visible in the images.

For each finding output EXACTLY this format, separated by ---:
RISK_TYPE: Legal | Financial | Operational | Compliance
SEVERITY: CRITICAL | HIGH | MEDIUM | LOW
DESCRIPTION: One concise sentence describing the specific risk
PAGE: page number

---

Be thorough and conservative. Identify every material risk visible in the pages."""


_GROUND_TRUTH_INSTRUCTION = """\
GROUND TRUTH — RAW TEXT FROM PDF

You have been given two sources for each page:
  (a) a rendered image of the page, and
  (b) the deterministic raw text extracted directly from the PDF text \
layer (shown below).

STRICT RULE: For any number, date, percentage, currency amount, or \
proper noun appearing in your answer or in any Markdown table, you \
MUST verify it against the raw text below. If the raw text and the \
image disagree, the raw text is the ground truth — use the raw text \
value. If the raw text is missing for a page (no text layer detected \
or no source PDF located), you may rely on the image but you MUST \
flag every such value with the marker ⚠️ unverified inline.

Never silently emit a number that does not appear in the raw text \
when raw text is present for that page."""


def _flag_unverified_table(answer: str, has_raw_text: bool) -> str:
    """Append ' ⚠️ unverified' to every number-containing data cell in every
    Markdown table in the answer when no raw ground-truth text is available.
    No-op when has_raw_text is True.
    """
    if has_raw_text:
        return answer

    _SEP_TOKEN = re.compile(r"^\s*:?-+:?\s*$")

    def _is_separator(line: str) -> bool:
        s = line.strip()
        if s.count("|") < 1:
            return False
        tokens = [t for t in s.split("|") if t.strip()]
        return bool(tokens) and all(_SEP_TOKEN.match(t) for t in tokens)

    def _is_pipe_row(line: str) -> bool:
        return line.strip().count("|") >= 2

    def _inject(line: str) -> str:
        parts = line.split("|")
        if len(parts) < 3:
            return line
        out = [parts[0]]
        for cell in parts[1:-1]:
            stripped = cell.strip()
            if not stripped or "⚠️ unverified" in cell:
                out.append(cell)
            elif re.search(r"\d", stripped):
                rstripped = cell.rstrip()
                trailing = cell[len(rstripped):]
                out.append(rstripped + " ⚠️ unverified" + trailing)
            else:
                out.append(cell)
        out.append(parts[-1])
        return "|".join(out)

    OUTSIDE, SAW_HEADER, IN_BODY = 0, 1, 2
    state = OUTSIDE
    out_lines = []

    for line in answer.splitlines(keepends=False):
        is_sep = _is_separator(line)
        is_pipe = not is_sep and _is_pipe_row(line)

        if state == OUTSIDE:
            out_lines.append(line)
            if is_pipe:
                state = SAW_HEADER
        elif state == SAW_HEADER:
            if is_sep:
                out_lines.append(line)
                state = IN_BODY
            else:
                out_lines.append(line)
                state = OUTSIDE
        else:  # IN_BODY
            if is_pipe:
                out_lines.append(_inject(line))
            else:
                out_lines.append(line)
                state = OUTSIDE

    return "\n".join(out_lines)


def _extract_highlight_terms(raw_text_sections: list[str]) -> list[str]:
    """Return searchable terms derived deterministically from raw PDF text (never from LLM output).

    Extracts up to 5 numeric tokens (dollar amounts, percentages, comma-separated numbers)
    and up to 5 row-label strings (words before wide whitespace gaps, typical of financial tables).
    """
    combined = "\n".join(raw_text_sections)
    terms: list[str] = []
    seen: set[str] = set()

    for m in re.finditer(
        r'\$[\d,]+(?:\.\d+)?[MBKmk]?'
        r'|[\d,]+(?:\.\d+)?%'
        r'|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b',
        combined,
    ):
        t = m.group().strip()
        if t and t not in seen:
            seen.add(t)
            terms.append(t)
        if len(terms) >= 5:
            break

    for line in combined.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r'^([A-Za-z][A-Za-z &/()\-]{3,40})\s{2,}', stripped)
        if m:
            label = m.group(1).strip()
            if label and label not in seen:
                seen.add(label)
                terms.append(label)
        if len(terms) >= 10:
            break

    return terms


def answer_with_citations(question: str, chunks: list[dict], doc_name: str | None = None) -> dict:
    """Answer a due diligence question from retrieved page images with raw-text cross-validation."""
    client = _get_client()

    image_blocks: list = []
    page_refs: list[int] = []
    contributing_chunks: list[dict] = []

    for c in chunks:
        if c.get("base64"):
            image_blocks.append({
                "type": "image_url",
                "image_url": {"url": _b64_to_data_url(c["base64"])},
            })
            page_refs.append(c["page_num"])
            contributing_chunks.append(c)

    if not image_blocks:
        return {
            "answer": "No relevant pages found.",
            "cited_pages": [],
            "row_pages": [],
            "highlight_terms_by_page": {},
            "provenance_cited_pages": [],
            "first_chunk_page": None,
            "source_chunks": chunks,
            "is_verified": False,
        }

    # Resolve PDF path from doc_name parameter (all chunks come from the same document)
    _doc_pdf_path: str | None = find_pdf_path(doc_name) if doc_name else None

    raw_text_sections: list[str] = []
    page_text_map: dict[int, str] = {}
    has_raw_text = False
    for c in contributing_chunks:
        page_num = c["page_num"]
        if "pdf_path" in c:
            pdf_path: str | None = c["pdf_path"]
        elif "doc_name" in c:
            pdf_path = find_pdf_path(c["doc_name"])
        elif _doc_pdf_path:
            pdf_path = _doc_pdf_path
        else:
            raw_text_sections.append(
                f"===== Raw text from Page {page_num} =====\n"
                f"(no source PDF located on disk — verify visually)\n"
            )
            continue

        if not pdf_path:
            raw_text_sections.append(
                f"===== Raw text from Page {page_num} =====\n"
                f"(no source PDF located on disk — verify visually)\n"
            )
            continue

        text = extract_page_text(pdf_path, page_num)
        if text and text.strip():
            has_raw_text = True
            page_text_map[page_num] = text
            raw_text_sections.append(
                f"===== Raw text from Page {page_num} =====\n{text}\n"
            )
        else:
            raw_text_sections.append(
                f"===== Raw text from Page {page_num} =====\n"
                f"(no text layer detected on this page — verify visually)\n"
            )

    # Enrich chunks with extracted text so provenance resolver can string-match cells
    enriched_chunks = [
        {**c, "text": page_text_map.get(c["page_num"], "")}
        for c in contributing_chunks
    ]

    page_label = ", ".join(f"Page {p}" for p in page_refs)
    full_prompt = (
        _QA_PROMPT
        + "\n\n" + _GROUND_TRUTH_INSTRUCTION
        + "\n\n" + "\n".join(raw_text_sections)
        + f"\n\nShown pages: {page_label}.\n\nQuestion: {question}"
    )

    content = image_blocks + [{"type": "text", "text": full_prompt}]

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": content}],
        max_tokens=2048,
    )
    answer = response.choices[0].message.content or ""
    answer = _flag_unverified_table(answer, has_raw_text=has_raw_text)
    cited_pages = sorted(set(int(m) for m in re.findall(r"\[Page (\d+)\]", answer)))

    table_md = _extract_table_from_answer(answer)
    if table_md:
        prov = resolve_table_provenance(table_md, enriched_chunks)
    else:
        prov = {"row_pages": [], "highlight_terms_by_page": {}, "cited_pages": []}

    return {
        "answer": answer,
        "cited_pages": cited_pages,
        "row_pages": prov["row_pages"],
        "highlight_terms_by_page": prov["highlight_terms_by_page"],
        "provenance_cited_pages": prov["cited_pages"],
        "first_chunk_page": contributing_chunks[0]["page_num"] if contributing_chunks else None,
        "source_chunks": chunks,
        "is_verified": has_raw_text,
    }


def extract_liabilities(scan_pages: list[dict]) -> list[dict]:
    """Scan sampled document pages for liabilities using Groq Vision."""
    client = _get_client()

    image_blocks: list = []
    for p in scan_pages:
        try:
            image_blocks.append({
                "type": "image_url",
                "image_url": {"url": _path_to_data_url(p["image_path"])},
            })
        except Exception:
            pass

    if not image_blocks:
        return []

    content = image_blocks + [{"type": "text", "text": _LIABILITY_PROMPT}]

    response = client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": content}],
        max_tokens=2048,
    )
    text = response.choices[0].message.content or ""

    findings: list[dict] = []
    for block in text.split("---"):
        block = block.strip()
        if not block:
            continue
        finding: dict = {}
        for line in block.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                finding[key.strip().upper()] = val.strip()
        if "DESCRIPTION" in finding and finding["DESCRIPTION"]:
            findings.append(
                {
                    "risk_type": finding.get("RISK_TYPE", "Financial"),
                    "severity": finding.get("SEVERITY", "MEDIUM"),
                    "description": finding["DESCRIPTION"],
                    "page": finding.get("PAGE", "N/A"),
                    "verification": "PENDING",
                }
            )

    return findings