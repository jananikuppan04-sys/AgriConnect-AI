"""
rag_engine.py  –  Local semantic search engine for AgriConnect AI

How it works (plain language):
1. Every Markdown file in knowledge_base/ is loaded and cleaned.
2. Each file is split into overlapping word-chunks (~300 words each).
3. The sentence-transformers model converts each chunk into a numeric
   vector (embedding) that captures its *meaning*, not just its words.
4. All vectors are stored in a local ChromaDB collection on disk
   (backend/vector_store/), so we don't recompute them every restart.
5. When a user asks a question, the question is also embedded and the
   ChromaDB collection is searched for the closest chunks by cosine
   similarity – this is semantic retrieval.
6. The top-3 matches are returned together with their source filenames
   and a relevance distance score.
"""

import os
import re
import math
import logging

# ── Lazy imports ──────────────────────────────────────────────────────────────
# chromadb and sentence_transformers are heavy; only imported when this module
# is first loaded (at server startup), not on every request.
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE          = os.path.dirname(__file__)
KB_DIR         = os.path.join(_HERE, "knowledge_base")
VECTOR_DIR     = os.path.join(_HERE, "vector_store")
COLLECTION_NAME = "agriconnect_kb"

# ── Chunking parameters ───────────────────────────────────────────────────────
CHUNK_SIZE    = 60 # target words per chunk
CHUNK_OVERLAP = 12  # words shared between consecutive chunks

# ── Relevance threshold ───────────────────────────────────────────────────────
# ChromaDB returns L2 (Euclidean) distance; smaller = more similar.
# For all-MiniLM-L6-v2 cosine-space embeddings, distances > 1.4 are
# effectively "no match" – anything below this is considered relevant.
MAX_DISTANCE = 0.76

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger("rag_engine")


# ==============================================================================
# 1. TEXT UTILITIES
# ==============================================================================

def _clean_markdown(text: str) -> str:
    """
    Strip Markdown syntax so the embeddings capture meaning, not formatting:
    – Remove heading markers (#, ##, ###…)
    – Remove bold/italic markers (* _ **)
    – Remove inline code backticks
    – Collapse multiple blank lines into one
    """
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"\*{1,3}|_{1,3}", "", text)                  # bold/italic
    text = re.sub(r"`+", "", text)                               # inline code
    text = re.sub(r"\n{3,}", "\n\n", text)                       # excess blank lines
    return text.strip()


def _split_into_chunks(text: str, source: str) -> list[dict]:
    """
    Split a cleaned text into overlapping word-windows.

    Each chunk is a dict:
        {
          "text":       str,   # chunk text sent to the embedder
          "source":     str,   # original .md filename
          "chunk_id":   str,   # unique ID used by ChromaDB
        }

    Overlap lets sentences that fall on chunk boundaries still be
    found, regardless of which chunk the query lands in.
    """
    words = text.split()
    chunks = []
    start = 0
    chunk_num = 0

    while start < len(words):
        end   = min(start + CHUNK_SIZE, len(words))
        chunk = " ".join(words[start:end])
        chunks.append({
            "text":     chunk,
            "source":   source,
            "chunk_id": f"{source}__chunk{chunk_num}",
        })
        chunk_num += 1
        # Advance by (CHUNK_SIZE - CHUNK_OVERLAP) so next chunk re-uses
        # the last CHUNK_OVERLAP words of the current chunk.
        start += CHUNK_SIZE - CHUNK_OVERLAP
        if end == len(words):
            break

    return chunks


def _load_all_chunks() -> list[dict]:
    """
    Walk knowledge_base/, clean each .md file, and split into chunks.
    Returns a flat list of chunk dicts ready for embedding.
    """
    all_chunks: list[dict] = []

    if not os.path.isdir(KB_DIR):
        log.warning("knowledge_base/ directory not found at %s", KB_DIR)
        return all_chunks

    md_files = [f for f in os.listdir(KB_DIR) if f.endswith(".md")]
    log.info("📂 Markdown files discovered: %s", md_files)

    for filename in md_files:
        path = os.path.join(KB_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            cleaned = _clean_markdown(raw)
            chunks  = _split_into_chunks(cleaned, filename)
            all_chunks.extend(chunks)
            log.info("   %s  →  %d chunk(s)", filename, len(chunks))
        except Exception as exc:
            log.error("Failed to load %s: %s", filename, exc)

    log.info("✅ Total chunks created: %d", len(all_chunks))
    return all_chunks


# ==============================================================================
# 2. VECTOR STORE SETUP  (runs once at import time / server startup)
# ==============================================================================

def _build_vector_store() -> tuple:
    """
    Load or build the ChromaDB collection.

    – If the collection already has documents, we reuse them (fast restart).
    – If the collection is empty (first run or cleared), we embed and insert
      all chunks from scratch.

    Returns (collection, model) ready for querying.
    """
    os.makedirs(VECTOR_DIR, exist_ok=True)

    # Persistent client writes data to disk under VECTOR_DIR
    client = chromadb.PersistentClient(path=VECTOR_DIR)

    # get_or_create is idempotent – safe to call every startup
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},   # cosine similarity for sentence-transformers
    )

    # Load the local embedding model (downloads ~90 MB on first run, cached after)
    log.info("🤖 Loading embedding model: all-MiniLM-L6-v2 …")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    log.info("✅ Embedding model loaded.")

    existing_count = collection.count()
    if existing_count > 0:
        log.info("⚡ Vector store already populated (%d vectors). Skipping re-indexing.", existing_count)
        return collection, model

    # ── First-time indexing ───────────────────────────────────────────────────
    chunks = _load_all_chunks()
    if not chunks:
        log.warning("No chunks to embed – knowledge_base/ may be empty.")
        return collection, model

    log.info("🔢 Generating embeddings for %d chunks …", len(chunks))
    texts      = [c["text"]     for c in chunks]
    ids        = [c["chunk_id"] for c in chunks]
    metadatas  = [{"source": c["source"], "chunk_id": c["chunk_id"]} for c in chunks]

    # encode() returns a numpy array; tolist() converts to plain Python lists
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    # Upsert in one batch for speed
    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    log.info("✅ Vector store ready – %d vectors indexed.", collection.count())
    return collection, model


# ── Initialise at import time so startup logs appear before first request ──
log.info("=" * 60)
log.info("AgriConnect AI  –  RAG Engine starting up …")
log.info("=" * 60)
_collection, _model = _build_vector_store()
log.info("=" * 60)
log.info("RAG Engine ready. Listening for queries.")
log.info("=" * 60)


# ==============================================================================
# 3. PUBLIC QUERY FUNCTION
# ==============================================================================

def query(user_question: str, top_k: int = 3) -> list[dict]:
    """
    Embed the user's question and return the top-k most semantically
    relevant chunks from the knowledge base.

    Each result dict contains:
        "text"     – the matched chunk text
        "source"   – the .md filename it came from
        "distance" – cosine distance (0 = identical, 2 = opposite)

    Results whose distance exceeds MAX_DISTANCE are filtered out so the
    caller can detect "no relevant content found" cleanly.
    """
    if not user_question.strip():
        return []

    # Embed the question using the same model used for indexing
    query_embedding = _model.encode([user_question]).tolist()

    results = _collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, _collection.count() or 1),
        include=["documents", "metadatas", "distances"],
    )

    hits: list[dict] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if dist <= MAX_DISTANCE:           # only keep genuinely relevant hits
            hits.append({
                "text":     doc,
                "source":   meta["source"],
                "distance": round(dist, 4),
            })

    return hits
