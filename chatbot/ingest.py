"""
Ingestion pipeline: PDF → chunks → ChromaDB + BM25 index.

Run once (or after PDF updates):
    python ingest.py
"""

import re
import pickle
import sys
from pathlib import Path

import pdfplumber
from sentence_transformers import SentenceTransformer
import chromadb

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    print("Installing rank-bm25...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rank-bm25", "-q"])
    from rank_bm25 import BM25Okapi

from config import (
    CHROMA_DB_PATH, BM25_INDEX_PATH,
    EMBEDDING_MODEL, POLICY_END_PAGE, ANNEXURE_END_PAGE,
    SECTION_TITLES, CHILD_CHUNK_WORDS, CHILD_CHUNK_OVERLAP, MAX_CHARS_PER_CHUNK,
)
from pdf_loader import resolve_pdf

# ---------------------------------------------------------------------------
# 1. PDF extraction
# ---------------------------------------------------------------------------

FOOTER_RE = re.compile(r"\n?\d{1,3}\s*\nVersion\s*1\.0[^\n]*", re.IGNORECASE)


def extract_pages(pdf_path: Path) -> list[dict]:
    """Return one dict per page: {page_num, text, has_table}."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            raw = page.extract_text() or ""
            text = FOOTER_RE.sub("", raw).strip()

            tables = page.extract_tables() or []
            table_strs = []
            for tbl in tables:
                rows = [" | ".join(cell or "" for cell in row) for row in tbl if row]
                if rows:
                    table_strs.append("\n".join(rows))

            if table_strs:
                text += "\n\n[TABLE]\n" + "\n\n[TABLE]\n".join(table_strs)

            pages.append({
                "page_num": i + 1,
                "text": text,
                "has_table": bool(table_strs),
            })
    return pages


# ---------------------------------------------------------------------------
# 2. Chunking
# ---------------------------------------------------------------------------

ANNEXURE_HEAD_RE = re.compile(r"Annexure\s*[–\-]\s*([A-Z0-9]+)", re.IGNORECASE)
APPENDIX_HEAD_RE = re.compile(r"Appendix\s*[–\-]\s*([A-Z0-9]+)", re.IGNORECASE)


def find_section_boundaries(text: str, max_section: int = 33) -> list[tuple[int, int]]:
    """
    Walk sections 1..max_section sequentially. For each N, find the first occurrence
    of "^N. " followed by a letter, AFTER the previous section's position.
    This is robust to:
      - trailing punctuation (`:` after title)
      - en-dash, curly quotes, mixed case
      - lowercase section titles (Section 32, 33)
    Returns list of (section_number, char_offset).
    """
    boundaries: list[tuple[int, int]] = []
    cursor = 0
    for n in range(1, max_section + 1):
        pattern = re.compile(rf"^{n}\.\s+[A-Za-z]", re.MULTILINE)
        match = pattern.search(text, cursor)
        if match:
            boundaries.append((n, match.start()))
            cursor = match.end()
    return boundaries


def _words_to_chunks(text: str, chunk_words: int, overlap: int) -> list[str]:
    words = text.split()
    if len(words) <= chunk_words:
        return [text]
    chunks = []
    step = max(1, chunk_words - overlap)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start: start + chunk_words])
        chunks.append(chunk)
        if start + chunk_words >= len(words):
            break
    return chunks


def _make_chunk(chunk_id, parent_id, level, section_id, title, doc_part, page_start, page_end, text, has_table=False):
    return {
        "chunk_id": chunk_id,
        "parent_id": parent_id or "",
        "chunk_level": level,
        "section_id": str(section_id),
        "section_title": title,
        "document_part": doc_part,
        "page_start": int(page_start),
        "page_end": int(page_end),
        "has_table": has_table,
        "text": text[:MAX_CHARS_PER_CHUNK],
    }


def chunk_policy(pages: list[dict]) -> list[dict]:
    """Section-aware parent/child chunking for policy pages 1–45."""
    # Skip page 2 (table of contents)
    policy_pages = [p for p in pages if 1 <= p["page_num"] <= POLICY_END_PAGE and p["page_num"] != 2]

    # Join all text; track page boundaries
    joined = ""
    page_bounds: list[tuple[int, int, int]] = []  # (start_char, end_char, page_num)
    for p in policy_pages:
        start = len(joined)
        joined += p["text"] + "\n\n"
        page_bounds.append((start, len(joined), p["page_num"]))

    def char_to_page(pos: int) -> int:
        for s, e, pn in page_bounds:
            if s <= pos < e:
                return pn
        return page_bounds[-1][2]

    # Find section boundaries (sections 1..33 walked in order)
    boundaries = find_section_boundaries(joined, max_section=33)

    chunks: list[dict] = []

    # Introduction (before section 1)
    intro_end = boundaries[0][1] if boundaries else len(joined)
    intro_text = joined[:intro_end].strip()
    if intro_text:
        chunks.append(_make_chunk(
            "section_0", None, "parent", "0", "Introduction",
            "policy", 3, char_to_page(intro_end), intro_text,
        ))
        chunks.append(_make_chunk(
            "section_0_child_0", "section_0", "child", "0", "Introduction",
            "policy", 3, char_to_page(intro_end), intro_text,
        ))

    # Numbered sections
    for idx, (sec_n, sec_start) in enumerate(boundaries):
        sec_num = str(sec_n)
        sec_title = SECTION_TITLES.get(sec_num, f"Section {sec_num}")
        sec_end = boundaries[idx + 1][1] if idx + 1 < len(boundaries) else len(joined)
        sec_text = joined[sec_start:sec_end].strip()

        page_s = char_to_page(sec_start)
        page_e = char_to_page(sec_end - 1)
        parent_id = f"section_{sec_num}"
        has_tbl = any(p["has_table"] for p in policy_pages if page_s <= p["page_num"] <= page_e)

        # Parent chunk (whole section, capped)
        chunks.append(_make_chunk(
            parent_id, None, "parent", sec_num, sec_title,
            "policy", page_s, page_e, sec_text, has_tbl,
        ))

        # Child chunks
        for c_idx, child_text in enumerate(_words_to_chunks(sec_text, CHILD_CHUNK_WORDS, CHILD_CHUNK_OVERLAP)):
            chunks.append(_make_chunk(
                f"{parent_id}_child_{c_idx}", parent_id, "child", sec_num, sec_title,
                "policy", page_s, page_e, child_text, has_tbl,
            ))

    return chunks


def chunk_annexures(pages: list[dict]) -> list[dict]:
    """One chunk per Annexure (pages 46–133)."""
    ann_pages = [p for p in pages if POLICY_END_PAGE < p["page_num"] <= ANNEXURE_END_PAGE]
    return _group_by_header(ann_pages, ANNEXURE_HEAD_RE, "annexure", "Annexure")


def chunk_appendices(pages: list[dict]) -> list[dict]:
    """One chunk per Appendix (pages 134–183)."""
    app_pages = [p for p in pages if p["page_num"] > ANNEXURE_END_PAGE]
    return _group_by_header(app_pages, APPENDIX_HEAD_RE, "appendix", "Appendix")


def _group_by_header(pages, pattern, doc_part, label) -> list[dict]:
    chunks: list[dict] = []
    current_id = None
    current_texts: list[str] = []
    current_start = None
    prev_page = None
    used_ids: dict[str, int] = {}  # id → count, for deduplication

    def flush():
        if current_id and current_texts:
            full_text = "\n\n".join(current_texts)
            base_id = f"{doc_part}_{current_id}"
            count = used_ids.get(base_id, 0)
            chunk_id = base_id if count == 0 else f"{base_id}_{count}"
            used_ids[base_id] = count + 1
            chunks.append(_make_chunk(
                chunk_id, None, "parent",
                f"{label}-{current_id}", f"{label} {current_id}",
                doc_part, current_start, prev_page, full_text,
            ))

    for page in pages:
        m = pattern.search(page["text"])
        if m:
            new_id = m.group(1).upper()
            if new_id == current_id:
                # Same group continuing on next page — just accumulate
                current_texts.append(page["text"])
            else:
                flush()
                current_id = new_id
                current_start = page["page_num"]
                current_texts = [page["text"]]
        else:
            if current_texts is not None:
                current_texts.append(page["text"])
        prev_page = page["page_num"]

    flush()
    return chunks


def create_all_chunks(pages: list[dict]) -> list[dict]:
    policy = chunk_policy(pages)
    annexures = chunk_annexures(pages)
    appendices = chunk_appendices(pages)
    return policy + annexures + appendices


# ---------------------------------------------------------------------------
# 3. Index building
# ---------------------------------------------------------------------------

def build_index(chunks: list[dict]) -> None:
    print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
    print("(First run downloads ~670 MB — subsequent runs use cache)\n")
    model = SentenceTransformer(EMBEDDING_MODEL)

    # --- Chroma ---
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        client.delete_collection("policy_docs")
        print("Cleared existing Chroma collection.")
    except Exception:
        pass

    collection = client.create_collection(
        "policy_docs",
        metadata={"hnsw:space": "cosine"},
    )

    texts = [c["text"] for c in chunks]
    batch = 32

    for i in range(0, len(chunks), batch):
        b = chunks[i: i + batch]
        bt = texts[i: i + batch]
        print(f"  Embedding batch {i // batch + 1}/{-(-len(chunks) // batch)} ({len(b)} chunks)...")
        embeddings = model.encode(bt, normalize_embeddings=True, show_progress_bar=False).tolist()

        # Chroma requires metadata values to be str/int/float/bool only
        metas = []
        for c in b:
            m = {k: v for k, v in c.items() if k != "text"}
            m = {k: (str(v) if not isinstance(v, (str, int, float, bool)) else v) for k, v in m.items()}
            metas.append(m)

        collection.add(
            ids=[c["chunk_id"] for c in b],
            embeddings=embeddings,
            documents=bt,
            metadatas=metas,
        )

    print(f"\nChroma: {collection.count()} chunks indexed.")

    # --- BM25 ---
    print("Building BM25 index...")
    tokenized = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized)

    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump({
            "bm25": bm25,
            "chunk_ids": [c["chunk_id"] for c in chunks],
            "chunk_metas": [{k: v for k, v in c.items() if k != "text"} for c in chunks],
            "texts": texts,
        }, f)

    print(f"BM25: {len(chunks)} chunks indexed.\n")
    print("Index build complete!")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_ingest() -> None:
    """Full pipeline. Used both from CLI and from app.py at first boot."""
    pdf_path = resolve_pdf()
    print(f"PDF: {pdf_path}")

    print("Extracting pages...")
    pages = extract_pages(pdf_path)
    print(f"  {len(pages)} pages extracted.")

    print("Creating chunks...")
    chunks = create_all_chunks(pages)

    by_part: dict[str, int] = {}
    for c in chunks:
        by_part.setdefault(c["document_part"], 0)
        by_part[c["document_part"]] += 1
    print(f"  {len(chunks)} chunks total: {by_part}")

    print("\nBuilding index...")
    build_index(chunks)


if __name__ == "__main__":
    run_ingest()
