from dataclasses import dataclass
from pathlib import Path
import pdfplumber


@dataclass
class Chunk:
    text: str
    page_num: int
    doc_name: str
    chunk_id: str


def get_page_count(pdf_path: str) -> int:
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)


def extract_chunks(pdf_path: str, chunk_size: int = 400) -> list[Chunk]:
    doc_name = Path(pdf_path).name
    chunks = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""

            tables = page.extract_tables() or []
            for table in tables:
                if not table:
                    continue
                rows = [
                    " | ".join(str(cell) if cell else "" for cell in row)
                    for row in table
                    if row
                ]
                text += "\n[TABLE]\n" + "\n".join(rows) + "\n[/TABLE]"

            words = text.split()
            for i in range(0, max(1, len(words)), chunk_size):
                chunk_text = " ".join(words[i : i + chunk_size])
                if chunk_text.strip():
                    chunk_id = f"{doc_name}_p{page_num}_c{i // chunk_size}"
                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            page_num=page_num,
                            doc_name=doc_name,
                            chunk_id=chunk_id,
                        )
                    )

    return chunks
