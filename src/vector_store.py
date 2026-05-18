from __future__ import annotations

import base64 as _base64
import io as _io
import os
import re
import shutil
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Allow MPS to use all unified memory on Apple Silicon.
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"

_BYALDI_ROOT = Path(".byaldi")
_MODEL_ID = "vidore/colqwen2-v1.0"
_BATCH_SIZE = 4


def _get_device() -> str:
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


# Module-level cache: index_name → loaded RAGMultiModalModel instance.
_rag_cache: dict[str, object] = {}

# Loaded once, reused across all index_document() calls.
_pretrained_model: object = None


def _index_name(doc_name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_name)[:60]
    return sanitized if len(sanitized) >= 3 else sanitized + "doc"


def _get_rag_for_doc(doc_name: str):
    from byaldi import RAGMultiModalModel

    index_name = _index_name(doc_name)

    if index_name in _rag_cache:
        return _rag_cache[index_name]

    index_path = _BYALDI_ROOT / index_name
    if not index_path.exists():
        return None

    rag = RAGMultiModalModel.from_index(
        index_path=index_name,
        index_root=str(_BYALDI_ROOT),
        device=_get_device(),
    )
    _rag_cache[index_name] = rag
    return rag


def _load_pretrained() -> object:
    global _pretrained_model
    if _pretrained_model is None:
        from byaldi import RAGMultiModalModel
        _pretrained_model = RAGMultiModalModel.from_pretrained(
            _MODEL_ID, verbose=0, device=_get_device()
        )
    return _pretrained_model


def _build_index_batched(
    rag,
    image_paths: list[Path],
    index_name: str,
    store_collection: bool,
    max_width: int,
    max_height: int,
    batch_size: int,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    """Parallel image I/O + batched GPU encoding; bypasses byaldi's one-at-a-time loop."""
    import torch
    from PIL import Image

    m = rag.model  # ColPaliModel

    index_path = _BYALDI_ROOT / index_name
    if index_path.exists():
        shutil.rmtree(index_path)

    m.index_name = index_name
    m.full_document_collection = store_collection
    m.max_image_width = max_width
    m.max_image_height = max_height
    m.indexed_embeddings = []
    m.embed_id_to_doc_id = {}
    m.doc_ids_to_file_names = {}
    m.doc_ids = set()
    m.doc_id_to_metadata = {}
    m.highest_doc_id = -1
    m.collection = {}

    def load_resize(path: Path) -> Image.Image:
        img = Image.open(path).convert("RGB")
        img.thumbnail((max_width, max_height), Image.LANCZOS)
        return img

    n = len(image_paths)
    workers = min(8, os.cpu_count() or 4)

    # Pre-submit all loads so disk I/O overlaps with GPU work on previous batch.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(load_resize, p) for p in image_paths]

        for batch_start in range(0, n, batch_size):
            batch_end = min(batch_start + batch_size, n)
            batch_paths = image_paths[batch_start:batch_end]
            batch_images = [futures[i].result() for i in range(batch_start, batch_end)]

            # One GPU forward pass for the whole batch.
            embeddings = m.encode_image(batch_images)  # [B, seq_len, dim] on CPU

            for j, (path, img, emb) in enumerate(
                zip(batch_paths, batch_images, torch.unbind(embeddings))
            ):
                doc_id = batch_start + j
                embed_id = len(m.indexed_embeddings)

                m.indexed_embeddings.append(emb)
                m.embed_id_to_doc_id[embed_id] = {"doc_id": doc_id, "page_id": 1}
                m.doc_ids_to_file_names[doc_id] = str(path)
                m.doc_ids.add(doc_id)
                m.highest_doc_id = max(m.highest_doc_id, doc_id)

                if store_collection:
                    buf = _io.BytesIO()
                    img.save(buf, format="PNG")
                    m.collection[embed_id] = _base64.b64encode(buf.getvalue()).decode()

            if on_progress:
                on_progress(batch_end, n)

    m._export_index()


def index_document(
    pages: list,
    doc_name: str,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    """Embed and index pre-rendered page images using ColPali via byaldi."""
    if not pages:
        return

    image_dir = Path(pages[0].image_path).parent
    index_name = _index_name(doc_name)
    n = len(pages)

    if on_progress:
        on_progress(0, n)

    image_paths = sorted(
        p for p in image_dir.iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
    )

    rag = _load_pretrained()
    _build_index_batched(
        rag,
        image_paths=image_paths,
        index_name=index_name,
        store_collection=True,
        max_width=768,
        max_height=768,
        batch_size=_BATCH_SIZE,
        on_progress=on_progress,
    )
    _rag_cache[index_name] = rag


def reset_collection(doc_name: str) -> None:
    """Remove a document's index from cache and disk."""
    index_name = _index_name(doc_name)
    _rag_cache.pop(index_name, None)
    index_path = _BYALDI_ROOT / index_name
    if index_path.exists():
        shutil.rmtree(index_path)


def query_document(question: str, doc_name: str, n_results: int = 3) -> list[dict]:
    """Semantic search over visual page embeddings."""
    rag = _get_rag_for_doc(doc_name)
    if rag is None:
        return []

    results = rag.search(question, k=n_results, return_base64_results=True)

    return [
        {
            "base64": r.base64,
            "page_num": r.page_num,
            "score": r.score,
        }
        for r in results
        if r.base64
    ]
