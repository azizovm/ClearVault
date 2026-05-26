from __future__ import annotations

import re


def _numeric_variants(s: str) -> list[str]:
    """Generate search variants for a markdown table cell to handle PDF formatting differences.

    Covers: currency prefix, thousand-separator commas, parentheses-negative ↔ minus,
    trailing decimal zeros, and casefold for text labels.
    """
    s = s.strip()
    if not s:
        return []

    seen: set[str] = set()
    out: list[str] = []

    def push(v: str) -> None:
        v = v.strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)

    push(s)
    push(s.casefold())

    # Strip leading currency symbol
    nc = re.sub(r'^[$€£¥]\s*', '', s)
    push(nc)

    # Determine sign form and extract bare magnitude
    paren_m = re.match(r'^\((.+)\)$', nc)
    if paren_m:
        inner = re.sub(r'^[$€£¥]\s*', '', paren_m.group(1))
        sign_forms = [f'({inner})', f'-{inner}', inner]
    elif nc.startswith('-'):
        inner = nc[1:]
        sign_forms = [f'-{inner}', f'({inner})', inner]
    else:
        sign_forms = [nc]

    for form in sign_forms:
        push(form)
        # Without thousand-separating commas
        push(re.sub(r',', '', form))
        # Without trailing decimal zeros (e.g. .00)
        no_trail = re.sub(r'\.0+$', '', form)
        push(no_trail)
        push(re.sub(r',', '', no_trail))

    return out


def _extract_table_from_answer(answer: str) -> str | None:
    """Return the first complete Markdown pipe table block in the answer text, or None."""
    lines = answer.split("\n")
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


def _parse_table_data_rows(table_md: str) -> list[list[str]]:
    """Parse a Markdown pipe table and return only data rows (skip header + separator)."""
    rows: list[list[str]] = []
    for line in table_md.strip().splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        if re.match(r'^[\|\s\-:]+$', line):
            continue
        cells = [c.strip() for c in line.split('|')]
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]
        if cells:
            rows.append(cells)
    # rows[0] is the header row — skip it
    return rows[1:] if len(rows) > 1 else []


def resolve_table_provenance(table_md: str, chunks: list[dict]) -> dict:
    """Match each markdown table data row to the chunk page containing its cell values.

    Each chunk dict must have 'text' (raw page text) and 'page_num'.
    Rows with no chunk match get None — never guessed, never inherited from adjacent rows.

    Returns:
        row_pages: list[int | None]  — one entry per data row
        highlight_terms_by_page: dict[int, list[str]]  — matched variant strings per page
        cited_pages: list[int]  — sorted unique pages with ≥1 match
    """
    data_rows = _parse_table_data_rows(table_md)

    row_pages: list[int | None] = []
    highlight_terms_by_page: dict[int, list[str]] = {}

    for row in data_rows:
        cell_variant_sets: list[list[str]] = [
            _numeric_variants(cell) for cell in row if cell.strip()
        ]

        if not cell_variant_sets:
            row_pages.append(None)
            continue

        matched_page: int | None = None
        matched_variants: list[str] = []

        for chunk in chunks:
            chunk_text = chunk.get("text", "")
            if not chunk_text:
                continue
            page_num = chunk.get("page_num")
            if page_num is None:
                continue

            found: list[str] = []
            for variants in cell_variant_sets:
                for v in variants:
                    if v and v in chunk_text:
                        found.append(v)
                        break  # one variant match per cell is sufficient

            if found:
                matched_page = int(page_num)
                matched_variants = found
                break

        row_pages.append(matched_page)

        if matched_page is not None:
            bucket = highlight_terms_by_page.setdefault(matched_page, [])
            existing = set(bucket)
            for v in matched_variants:
                if v not in existing:
                    bucket.append(v)
                    existing.add(v)

    return {
        "row_pages": row_pages,
        "highlight_terms_by_page": highlight_terms_by_page,
        "cited_pages": sorted(highlight_terms_by_page.keys()),
    }
