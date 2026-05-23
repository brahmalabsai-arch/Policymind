"""
Hybrid retrieval: dense (BGE) + sparse (BM25) → RRF → cross-encoder reranking.
Parent-child: retrieve child chunks, return parent text for full context.
"""

import pickle
import numpy as np
from functools import lru_cache

from sentence_transformers import SentenceTransformer, CrossEncoder
import chromadb

from config import (
    CHROMA_DB_PATH, BM25_INDEX_PATH,
    EMBEDDING_MODEL, RERANKER_MODEL,
    N_RETRIEVE, TOP_K,
)

# ---------------------------------------------------------------------------
# Lazy singletons (loaded on first call, reused across requests)
# ---------------------------------------------------------------------------

_embedding_model: SentenceTransformer | None = None
_reranker: CrossEncoder | None = None
_chroma_collection = None
_bm25_data: dict | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL, max_length=512)
    return _reranker


def get_chroma():
    global _chroma_collection
    if _chroma_collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _chroma_collection = client.get_collection("policy_docs")
    return _chroma_collection


def get_bm25() -> dict:
    global _bm25_data
    if _bm25_data is None:
        with open(BM25_INDEX_PATH, "rb") as f:
            _bm25_data = pickle.load(f)
    return _bm25_data


# ---------------------------------------------------------------------------
# Query routing: classify intent → metadata filter
# ---------------------------------------------------------------------------

ROUTE_MAP = [
    (["eligible", "eligibility", "qualify", "qualification", "can i apply", "who can apply",
      "requirements for applying", "apply for dealer", "apply for ro"],
     {"document_part": "policy", "hint_sections": ["6", "7", "8"]}),

    (["fee", "fees", "cost", "charge", "payment", "pay", "rupee", "rs.", "lakh",
      "application fee", "fixed fee", "bid amount", "security deposit", "working capital"],
     {"document_part": "policy", "hint_sections": ["16", "17", "28", "32", "33"]}),

    (["select", "selection", "draw of lot", "bid", "bidding", "how is dealer selected",
      "selection process", "selection procedure", "draw"],
     {"document_part": "policy", "hint_sections": ["18", "19", "20"]}),

    (["loi", "letter of intent", "after selection", "post selection"],
     {"document_part": "policy", "hint_sections": ["22", "23"]}),

    (["disqualif", "banned", "barred", "not eligible", "ineligible", "blacklisted"],
     {"document_part": "policy", "hint_sections": ["14", "30", "31"]}),

    (["grievance", "complaint", "appeal", "dispute", "redress"],
     {"document_part": "policy", "hint_sections": ["24"]}),

    (["reservation", "roster", "quota", "sc/st", "obc", "defence", "sports", "freedom fighter",
      "physically handicapped", "ph", "ossp", "pacs"],
     {"document_part": "policy", "hint_sections": ["3", "4"]}),

    (["location", "identify", "market class", "a class", "b class", "rural", "e class", "nh", "sh"],
     {"document_part": "policy", "hint_sections": ["1", "2"]}),

    (["facilities", "infrastructure", "equipment", "tank", "dispenser", "canopy"],
     {"document_part": "policy", "hint_sections": ["12", "33"]}),

    (["annexure", "template", "letter format", "format", "proforma"],
     {"document_part": "annexure", "hint_sections": []}),

    (["appendix", "application form", "affidavit", "certificate", "disability certificate"],
     {"document_part": "appendix", "hint_sections": []}),
]


def classify_query(query: str) -> dict:
    q = query.lower()
    for keywords, route in ROUTE_MAP:
        if any(kw in q for kw in keywords):
            return route
    return {"document_part": None, "hint_sections": []}


# ---------------------------------------------------------------------------
# Hybrid search
# ---------------------------------------------------------------------------

def _rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion over multiple ranked ID lists."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def search(query: str, top_k: int = TOP_K, n_retrieve: int = N_RETRIEVE) -> list[dict]:
    """
    Returns list of dicts: {chunk_id, text, metadata, score}
    Child chunks are promoted to their parent text for full context.
    """
    route = classify_query(query)
    collection = get_chroma()
    bm25_data = get_bm25()

    total_indexed = collection.count()
    n = min(n_retrieve, total_indexed)

    # --- Dense search ---
    model = get_embedding_model()
    q_emb = model.encode(query, normalize_embeddings=True).tolist()

    dense_where = {"document_part": route["document_part"]} if route["document_part"] else None

    dense_res = collection.query(
        query_embeddings=[q_emb],
        n_results=n,
        where=dense_where,
        include=["documents", "metadatas", "distances"],
    )
    dense_ids: list[str] = dense_res["ids"][0]
    dense_docs: list[str] = dense_res["documents"][0]
    dense_metas: list[dict] = dense_res["metadatas"][0]

    # --- BM25 sparse search ---
    tokenized_q = query.lower().split()
    bm25 = bm25_data["bm25"]
    all_ids: list[str] = bm25_data["chunk_ids"]
    all_metas: list[dict] = bm25_data["chunk_metas"]

    scores = bm25.get_scores(tokenized_q)
    top_idx = np.argsort(scores)[::-1][:n_retrieve]

    # Apply document_part filter if routing specified one
    bm25_ids: list[str] = []
    for i in top_idx:
        meta = all_metas[i]
        if route["document_part"] and meta.get("document_part") != route["document_part"]:
            continue
        bm25_ids.append(all_ids[i])
        if len(bm25_ids) >= n_retrieve:
            break

    # --- Hint-section boosting ---
    # If routing gave specific section hints, promote chunks from those sections
    hint_ids: list[str] = []
    if route.get("hint_sections"):
        for i, meta in enumerate(all_metas):
            if str(meta.get("section_id", "")) in route["hint_sections"]:
                hint_ids.append(all_ids[i])

    # --- RRF fusion (dense + sparse + hint) ---
    rankings = [dense_ids, bm25_ids]
    if hint_ids:
        rankings.append(hint_ids)
    fused = _rrf(rankings)
    fused_ids = [fid for fid, _ in fused[:n_retrieve]]

    # --- Build id → (doc, meta) lookup ---
    id_doc: dict[str, str] = {}
    id_meta: dict[str, dict] = {}
    for did, doc, meta in zip(dense_ids, dense_docs, dense_metas):
        id_doc[did] = doc
        id_meta[did] = meta

    # Fetch missing BM25/hint results from Chroma
    missing = [fid for fid in fused_ids if fid not in id_doc]
    if missing:
        try:
            fetched = collection.get(ids=missing[:n_retrieve], include=["documents", "metadatas"])
            for fid, doc, meta in zip(fetched["ids"], fetched["documents"], fetched["metadatas"]):
                id_doc[fid] = doc
                id_meta[fid] = meta
        except Exception:
            pass

    candidates = [(fid, id_doc[fid]) for fid in fused_ids if fid in id_doc]

    # --- Cross-encoder reranking ---
    # Keep extra candidates (top_k * 4) so the parent-dedup step has options.
    rerank_keep = max(top_k * 4, top_k)
    if len(candidates) > top_k:
        reranker = get_reranker()
        rerank_inputs = [(query, doc) for _, doc in candidates]
        rerank_scores = reranker.predict(rerank_inputs, show_progress_bar=False)
        ranked = sorted(zip(candidates, rerank_scores), key=lambda x: x[1], reverse=True)
        top_candidates = [cand for cand, _ in ranked[:rerank_keep]]
    else:
        top_candidates = candidates[:rerank_keep]

    # --- Parent promotion + dedup ---
    # Children → parent text. Multiple children of the same parent collapse to ONE result.
    # Standalone (parent-only or non-policy) chunks dedupe by their own ID.
    results = []
    seen_keys: set[str] = set()

    for chunk_id, doc in top_candidates:
        meta = id_meta.get(chunk_id, {})
        parent_id = meta.get("parent_id", "")
        level = meta.get("chunk_level", "")

        if parent_id and level == "child":
            # Dedup by parent_id — only emit the parent once
            if parent_id in seen_keys:
                continue
            seen_keys.add(parent_id)
            try:
                parent = collection.get(ids=[parent_id], include=["documents", "metadatas"])
                if parent["documents"]:
                    doc = parent["documents"][0]
                    meta = parent["metadatas"][0]
                    chunk_id = parent_id
            except Exception:
                pass
        else:
            # Parent chunk or standalone (annexure/appendix) — dedup by own id
            key = chunk_id
            # If this is a parent that we've already shown via a child promotion, skip
            if key in seen_keys:
                continue
            seen_keys.add(key)

        results.append({"chunk_id": chunk_id, "text": doc, "metadata": meta})

        if len(results) >= top_k:
            break

    return results
