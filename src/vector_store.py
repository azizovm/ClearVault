from __future__ import annotations

import re
import shutil
from collections.abc import Callable
from pathlib import Path

_BYALDI_ROOT = Path(".byaldi")


def _get_device() -> str:
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"



# Module-level cache: index_name → loaded RAGMultiModalModel instance.
# Persists across Streamlit reruns within the same server process.
_rag_cache: dict[str, object] = {}

# Cached pretrained model — loaded once, reused across all index_document() calls.
_pretrained_model: object = None


def _index_name(doc_name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_name)[:60]
    return sanitized if len(sanitized) >= 3 else sanitized + "doc"


def _get_rag_for_doc(doc_name: str):
    """Return a loaded RAGMultiModalModel for doc_name, loading from disk if needed."""
    from byaldi import RAGMultiModalModel

    index_name = _index_name(doc_name)

    if index_name in _rag_cache:
        return _rag_cache[index_name]

    index_path = _BYALDI_ROOT / index_name
    if not index_path.exists():
        return None

    rag = RAGMultiModalModel.from_index(
        index_path=str(_BYALDI_ROOT),
        index_name=index_name,
        device=_get_device(),
    )
    _rag_cache[index_name] = rag
    return rag


def _load_pretrained() -> object:
    """Load ColQwen2 once and cache it for the lifetime of the process."""
    global _pretrained_model
    if _pretrained_model is None:
        from byaldi import RAGMultiModalModel
        _pretrained_model = RAGMultiModalModel.from_pretrained(
            "vidore/colqwen2-v1.0", verbose=0, device=_get_device()
        )
    return _pretrained_model


def index_document(
    pages: list,
    doc_name: str,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    """Embed and index pre-rendered page images using ColQwen2 via byaldi."""
    if not pages:
        return

    image_dir = str(Path(pages[0].image_path).parent)
    index_name = _index_name(doc_name)
    n = len(pages)

    if on_progress:
        on_progress(0, n)

    rag = _load_pretrained()
    rag.index(
        input_path=image_dir,
        index_name=index_name,
        store_collection_with_index=True,
        overwrite=True,
        max_image_width=1024,
        max_image_height=1024,
    )
    _rag_cache[index_name] = rag

    if on_progress:
        on_progress(n, n)


def reset_collection(doc_name: str) -> None:
    """Remove a document's index from the in-memory cache and disk."""
    index_name = _index_name(doc_name)
    _rag_cache.pop(index_name, None)
    index_path = _BYALDI_ROOT / index_name
    if index_path.exists():
        shutil.rmtree(index_path)


def query_document(question: str, doc_name: str, n_results: int = 3) -> list[dict]:
    """Semantic search over visual page embeddings. Returns dicts with base64 + page_num."""
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
