"""
Lightweight vector store built on sqlite-vec + OpenAI embeddings.
Replaces ChromaDB (which crashes on Python 3.14 due to onnxruntime DLL issues).

Collections: weather_history, news_history, employee_context
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import struct
from datetime import datetime
from typing import Any

import sqlite_vec

_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "aria_vectors.db")
_EMBED_DIM = 1536  # text-embedding-3-small

# ── Connection ─────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    db = sqlite3.connect(os.path.abspath(_DB_PATH))
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.row_factory = sqlite3.Row
    return db


def _init_schema(db: sqlite3.Connection) -> None:
    """Create metadata + vector tables if they don't exist."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id          TEXT PRIMARY KEY,
            collection  TEXT NOT NULL,
            content     TEXT NOT NULL,
            metadata    TEXT NOT NULL DEFAULT '{}',
            created_at  TEXT NOT NULL
        )
    """)
    for coll in ("weather_history", "news_history", "employee_context"):
        db.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vec_{coll}
            USING vec0(embedding float[{_EMBED_DIM}])
        """)
    db.commit()


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack(data: bytes) -> list[float]:
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))


# ── Embedding ──────────────────────────────────────────────────────────────────

def _embed(texts: list[str]) -> list[list[float]]:
    """Embed texts via OpenRouter (compatible with openai SDK). Falls back to zero vector."""
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.endswith("..."):
        return [[0.0] * _EMBED_DIM for _ in texts]
    try:
        from openai import OpenAI
        # OpenRouter is OpenAI-compatible; use its base URL when key is sk-or-v1-*
        base_url = (
            "https://openrouter.ai/api/v1"
            if api_key.startswith("sk-or-")
            else None
        )
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception:
        return [[0.0] * _EMBED_DIM for _ in texts]


def _doc_id(collection: str, content: str) -> str:
    h = hashlib.sha256(f"{collection}:{content}".encode()).hexdigest()[:16]
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{collection[:4]}_{ts}_{h}"


# ── Public API ─────────────────────────────────────────────────────────────────

VALID_COLLECTIONS = {"weather_history", "news_history", "employee_context"}


def upsert(collection: str, content: str, metadata: dict | None = None) -> str:
    """Embed and store a document. Returns the doc_id."""
    if collection not in VALID_COLLECTIONS:
        raise ValueError(f"Unknown collection: {collection}. Use: {VALID_COLLECTIONS}")
    metadata = metadata or {}
    doc_id = _doc_id(collection, content)
    embeddings = _embed([content])
    vec = embeddings[0]

    db = _get_conn()
    _init_schema(db)
    try:
        db.execute(
            "INSERT OR REPLACE INTO documents (id, collection, content, metadata, created_at) VALUES (?,?,?,?,?)",
            (doc_id, collection, content, json.dumps(metadata), datetime.utcnow().isoformat()),
        )
        # sqlite-vec rowid must be integer — use a hash-based int
        rowid = int(hashlib.sha256(doc_id.encode()).hexdigest()[:8], 16) % (2**31)
        # delete old entry for this rowid if exists (upsert via delete+insert)
        db.execute(f"DELETE FROM vec_{collection} WHERE rowid = ?", (rowid,))
        db.execute(
            f"INSERT INTO vec_{collection}(rowid, embedding) VALUES (?, ?)",
            (rowid, _pack(vec)),
        )
        # store rowid on document for retrieval
        db.execute("UPDATE documents SET metadata = ? WHERE id = ?",
                   (json.dumps({**metadata, "_rowid": rowid}), doc_id))
        db.commit()
    finally:
        db.close()
    return doc_id


def search(collection: str, query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Semantic search. Returns list of {id, content, metadata, distance}."""
    if collection not in VALID_COLLECTIONS:
        raise ValueError(f"Unknown collection: {collection}")
    n_results = min(n_results, 20)
    query_vec = _embed([query])[0]

    db = _get_conn()
    _init_schema(db)
    try:
        rows = db.execute(
            f"SELECT rowid, distance FROM vec_{collection} WHERE embedding MATCH ? AND k=?",
            (_pack(query_vec), n_results),
        ).fetchall()
        if not rows:
            return []
        rowids = [r["rowid"] for r in rows]
        dist_map = {r["rowid"]: r["distance"] for r in rows}

        placeholders = ",".join("?" * len(rowids))
        docs = db.execute(
            f"SELECT id, collection, content, metadata FROM documents "
            f"WHERE json_extract(metadata,'$._rowid') IN ({placeholders})",
            rowids,
        ).fetchall()

        results = []
        for d in docs:
            meta = json.loads(d["metadata"])
            rowid = meta.get("_rowid")
            results.append({
                "id": d["id"],
                "collection": d["collection"],
                "content": d["content"],
                "metadata": meta,
                "distance": dist_map.get(rowid),
            })
        results.sort(key=lambda x: x["distance"] or 9.9)
        return results
    finally:
        db.close()


def list_collections() -> list[dict[str, Any]]:
    """Return each collection with its document count."""
    db = _get_conn()
    _init_schema(db)
    try:
        results = []
        for coll in sorted(VALID_COLLECTIONS):
            row = db.execute(
                "SELECT COUNT(*) as cnt FROM documents WHERE collection = ?", (coll,)
            ).fetchone()
            results.append({"collection": coll, "document_count": row["cnt"]})
        return results
    finally:
        db.close()


def get_all_documents(collection: str, limit: int = 100) -> list[dict[str, Any]]:
    """Fetch raw documents from a collection (for the UI explorer)."""
    db = _get_conn()
    _init_schema(db)
    try:
        rows = db.execute(
            "SELECT id, content, metadata, created_at FROM documents "
            "WHERE collection=? ORDER BY created_at DESC LIMIT ?",
            (collection, limit),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "content": r["content"],
                "metadata": json.loads(r["metadata"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        db.close()
