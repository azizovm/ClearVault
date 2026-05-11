from __future__ import annotations

import concurrent.futures
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class Page:
    image_path: str
    page_num: int
    doc_name: str


def get_page_count(pdf_path: str) -> int:
    with fitz.open(pdf_path) as doc:
        return len(doc)


def _process_page(idx: int, pdf_path: str, dpi: int, image_dir: Path, doc_name: str) -> Page:
    """Tek bir sayfayı işleyen yardımcı fonksiyon (Paralel çalışma için)."""
    # Thread-safe olması için dokümanı her thread içinde ayrı açıyoruz
    with fitz.open(pdf_path) as doc:
        page = doc[idx]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        # M4'ün I/O hızına ayak uydurmak için dosya yolları Path objesiyle yönetiliyor
        img_path = image_dir / f"page_{idx + 1:04d}.png"
        pix.save(str(img_path))
        
        return Page(
            image_path=str(img_path),
            page_num=idx + 1,
            doc_name=doc_name,
        )


def extract_pages(
    pdf_path: str,
    dpi: int = 150,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[Page]:
    """PDF sayfalarını PNG olarak paralel işler ve kaydeder. M4 için optimize edilmiştir."""
    doc_name = Path(pdf_path).name
    image_dir = Path("data") / "images" / Path(pdf_path).stem
    image_dir.mkdir(parents=True, exist_ok=True)

    total = get_page_count(pdf_path)
    pages: list[Page] = []
    completed = 0

    # M4 çekirdeklerini tam kapasite kullanmak için ThreadPoolExecutor kullanıyoruz.
    # PyMuPDF C seviyesinde çalıştığı için multithreading burada çok verimlidir.
    max_workers = min(32, (total or 1)) 
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Tüm sayfalar için iş ataması yap
        future_to_page = {
            executor.submit(_process_page, idx, pdf_path, dpi, image_dir, doc_name): idx
            for idx in range(total)
        }

        # İşlemler bittikçe sonuçları topla
        for future in concurrent.futures.as_completed(future_to_page):
            pages.append(future.result())
            completed += 1
            if on_progress:
                on_progress(completed, total)

    # as_completed sonuçları karışık sırayla döndürebileceği için sayfa numarasına göre sıralıyoruz
    pages.sort(key=lambda p: p.page_num)
    
    return pages