from __future__ import annotations

import re
from typing import Optional
import chromadb
from src.extractor import Chunk

_client: Optional[chromadb.PersistentClient] = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path="./chroma_db")
    return _client


def _collection_name(doc_name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_name)[:60]
    return sanitized if len(sanitized) >= 3 else sanitized + "doc"


def index_document(chunks: list[Chunk], doc_name: str) -> None:
    client = _get_client()
    name = _collection_name(doc_name)

    try:
        client.delete_collection(name)
    except Exception:
        pass

    collection = client.create_collection(name)

    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        collection.add(
            ids=[c.chunk_id for c in batch],
            documents=[c.text for c in batch],
            metadatas=[{"page_num": c.page_num, "doc_name": c.doc_name} for c in batch],
        )


def index_batch(chunks: list[Chunk], doc_name: str) -> None:
    """Add a batch of chunks to an existing collection (used for progress reporting)."""
    client = _get_client()
    name = _collection_name(doc_name)

    try:
        collection = client.get_collection(name)
    except Exception:
        collection = client.create_collection(name)

    collection.add(
        ids=[c.chunk_id for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[{"page_num": c.page_num, "doc_name": c.doc_name} for c in chunks],
    )


def reset_collection(doc_name: str) -> None:
    client = _get_client()
    name = _collection_name(doc_name)
    try:
        client.delete_collection(name)
    except Exception:
        pass


def query_document(question: str, doc_name: str, n_results: int = 5) -> list[dict]:
    client = _get_client()
    name = _collection_name(doc_name)

    try:
        collection = client.get_collection(name)
    except Exception:
        return []

    count = collection.count()
    if count == 0:
        return []

    results = collection.query(
        query_texts=[question],
        n_results=min(n_results, count),
    )

    if not results["documents"] or not results["documents"][0]:
        return []

    return [
        {
            "text": results["documents"][0][i],
            "page_num": results["metadatas"][0][i]["page_num"],
            "doc_name": results["metadatas"][0][i]["doc_name"],
        }
        for i in range(len(results["documents"][0]))
    ]
