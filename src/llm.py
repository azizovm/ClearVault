from __future__ import annotations

import os
import re
from typing import Optional
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client: Optional[Groq] = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")
        _client = Groq(api_key=api_key)
    return _client


def answer_with_citations(question: str, chunks: list[dict]) -> dict:
    context = "\n\n".join(
        f"[PAGE {c['page_num']}]\n{c['text']}" for c in chunks
    )

    prompt = f"""You are a senior M&A due diligence analyst. Answer the question using ONLY the provided context.

Rules:
- Cite every claim with [Page N] inline
- Be specific and numerical where possible
- Flag any risks or red flags you notice
- If you cannot answer from the context, say so explicitly

Context:
{context}

Question: {question}

Structure your answer as:
1. Direct Answer (with [Page N] citations inline)
2. Key Findings (bullet points, each cited)
3. Risk Assessment (if applicable)"""

    client = _get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1500,
    )

    answer = response.choices[0].message.content
    cited_pages = sorted(set(int(m) for m in re.findall(r"\[Page (\d+)\]", answer)))

    return {
        "answer": answer,
        "cited_pages": cited_pages,
        "source_chunks": chunks,
    }


def extract_liabilities(chunks: list[dict]) -> list[dict]:
    context = "\n\n".join(
        f"[PAGE {c['page_num']}]\n{c['text']}" for c in chunks
    )

    prompt = f"""You are an M&A risk analyst performing due diligence. Analyze these document excerpts and identify ALL liabilities, risks, and red flags.

For each finding output EXACTLY this format, separated by ---:
RISK_TYPE: Legal | Financial | Operational | Compliance
SEVERITY: CRITICAL | HIGH | MEDIUM | LOW
DESCRIPTION: One concise sentence describing the specific risk
PAGE: page number

---

Context:
{context}

Be thorough and conservative. Identify every material risk."""

    client = _get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000,
    )

    findings = []
    for block in response.choices[0].message.content.split("---"):
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
