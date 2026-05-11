from __future__ import annotations

import base64
import io
import os
import re
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

_model: Optional[genai.GenerativeModel] = None


def _get_model() -> genai.GenerativeModel:
    global _model
    if _model is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set. Add it to your .env file.")
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel("gemini-2.0-flash")
    return _model


def _b64_to_pil(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64)))


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


def answer_with_citations(question: str, chunks: list[dict]) -> dict:
    """Answer a due diligence question from retrieved page images."""
    model = _get_model()

    content: list = []
    page_refs: list[int] = []

    for c in chunks:
        if c.get("base64"):
            content.append(_b64_to_pil(c["base64"]))
            page_refs.append(c["page_num"])

    if not content:
        return {"answer": "No relevant pages found.", "cited_pages": [], "source_chunks": chunks}

    page_label = ", ".join(f"Page {p}" for p in page_refs)
    prompt = f"{_QA_PROMPT}\n\nShown pages: {page_label}.\n\nQuestion: {question}"
    content.append(prompt)

    response = model.generate_content(content)
    answer = response.text
    cited_pages = sorted(set(int(m) for m in re.findall(r"\[Page (\d+)\]", answer)))

    return {
        "answer": answer,
        "cited_pages": cited_pages,
        "source_chunks": chunks,
    }


def extract_liabilities(scan_pages: list[dict]) -> list[dict]:
    """Scan sampled document pages for liabilities using Gemini Vision."""
    model = _get_model()

    content: list = []
    for p in scan_pages:
        try:
            content.append(Image.open(p["image_path"]))
        except Exception:
            pass

    if not content:
        return []

    content.append(_LIABILITY_PROMPT)
    response = model.generate_content(content)

    findings: list[dict] = []
    for block in response.text.split("---"):
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
