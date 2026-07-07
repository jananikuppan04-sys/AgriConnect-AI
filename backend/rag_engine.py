"""
rag_engine.py  --  Local semantic search engine for AgriConnect AI

How it works:
1. Every Markdown file in knowledge_base/ is loaded and cleaned.
2. Each file is split into overlapping word-chunks (~60 words each).
3. The sentence-transformers model converts each chunk into a numeric
   vector (embedding) that captures its meaning.
4. All vectors are stored in a local ChromaDB collection on disk
   (backend/vector_store/), so we don't recompute them every restart.
5. When a user asks a question, the question is also embedded and the
   ChromaDB collection is searched for the closest chunks by cosine
   similarity -- this is semantic retrieval.
6. The top matches are returned together with their source filenames
   and a relevance distance score.

Stale-index detection:
   The collection metadata stores EMBEDDING_MODEL, INDEX_VERSION, and a
   SHA-256 fingerprint of all knowledge_base/*.md file contents. If any
   of these values differ at startup, the collection is automatically
   rebuilt.
"""

import os
import re
import hashlib
import logging

import chromadb
from sentence_transformers import SentenceTransformer

# -- Configuration ------------------------------------------------------------
_HERE           = os.path.dirname(__file__)
KB_DIR          = os.path.join(_HERE, "knowledge_base")
VECTOR_DIR      = os.path.join(_HERE, "vector_store")
COLLECTION_NAME = "agriconnect_kb"

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
INDEX_VERSION   = "2"   # Bump when chunking parameters change

CHUNK_SIZE    = 60      # target words per chunk
CHUNK_OVERLAP = 12      # words shared between consecutive chunks

# -- Evidence-based relevance threshold ----------------------------------------
# Measured via diagnostics.py on all six required test queries:
#
#   In-scope distances (direct):    0.1599  0.3148  0.4914  0.6477
#   In-scope distances (rewrite):   0.3117  0.4237
#   Out-of-scope distance (direct): 0.8286
#   Out-of-scope distance (rewrite):0.7942
#
#   Worst in-scope:  0.6477  (Tamil fake-listing, direct query)
#   Best out-scope:  0.7942  (weather, English rewrite)
#   Gap:             0.1465
#   Midpoint:        0.72
#   Threshold:       0.75  (midpoint + safety margin)
#
MAX_DISTANCE = 0.75

# Confidence threshold: if the best direct hit is worse than this,
# a Gemini English rewrite is attempted for Tamil queries.
REWRITE_THRESHOLD = 0.55

# -- Logging -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("rag_engine")


# ==============================================================================
# 1. TEXT UTILITIES
# ==============================================================================

def _clean_markdown(text: str) -> str:
    """
    Strip Markdown syntax so the embeddings capture meaning, not formatting.
    """
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)   # headings
    text = re.sub(r"\*{1,3}|_{1,3}", "", text)                    # bold/italic
    text = re.sub(r"`+", "", text)                                 # inline code
    text = re.sub(r"\n{3,}", "\n\n", text)                         # excess blanks
    return text.strip()


def _split_into_chunks(text: str, source: str) -> list[dict]:
    """Split cleaned text into overlapping word-windows."""
    words = text.split()
    chunks: list[dict] = []
    start = 0
    chunk_num = 0

    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunk = " ".join(words[start:end])
        chunks.append({
            "text":     chunk,
            "source":   source,
            "chunk_id": f"{source}__chunk{chunk_num}",
        })
        chunk_num += 1
        start += CHUNK_SIZE - CHUNK_OVERLAP
        if end == len(words):
            break

    return chunks


def _load_all_chunks() -> list[dict]:
    """Walk knowledge_base/, clean each .md file, and split into chunks."""
    all_chunks: list[dict] = []

    if not os.path.isdir(KB_DIR):
        log.warning("knowledge_base/ directory not found at %s", KB_DIR)
        return all_chunks

    md_files = sorted(f for f in os.listdir(KB_DIR) if f.endswith(".md"))
    log.info("Markdown files discovered: %s", md_files)

    for filename in md_files:
        path = os.path.join(KB_DIR, filename)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read()
            cleaned = _clean_markdown(raw)
            chunks = _split_into_chunks(cleaned, filename)
            all_chunks.extend(chunks)
            log.info("  %s -> %d chunk(s)", filename, len(chunks))
        except Exception as exc:
            log.error("Failed to load %s: %s", filename, exc)

    log.info("Total chunks created: %d", len(all_chunks))
    return all_chunks


# ==============================================================================
# 2. STALE-INDEX DETECTION
# ==============================================================================

def _compute_kb_fingerprint() -> str:
    """SHA-256 over sorted knowledge_base/*.md filenames and contents."""
    hasher = hashlib.sha256()

    if not os.path.isdir(KB_DIR):
        return hasher.hexdigest()

    for filename in sorted(os.listdir(KB_DIR)):
        if filename.endswith(".md"):
            path = os.path.join(KB_DIR, filename)
            try:
                with open(path, "rb") as fh:
                    hasher.update(filename.encode("utf-8"))
                    hasher.update(fh.read())
            except Exception:
                pass

    return hasher.hexdigest()


def _is_index_stale(collection) -> bool:
    """Return True when the stored collection metadata differs from current config."""
    try:
        meta = collection.metadata or {}
    except Exception:
        return True

    stored_model       = meta.get("embedding_model", "")
    stored_version     = meta.get("index_version", "")
    stored_fingerprint = meta.get("kb_fingerprint", "")

    current_fingerprint = _compute_kb_fingerprint()

    stale = False
    if stored_model != EMBEDDING_MODEL:
        log.info("Stale index: embedding model changed (%s -> %s)",
                 stored_model, EMBEDDING_MODEL)
        stale = True
    if stored_version != INDEX_VERSION:
        log.info("Stale index: index version changed (%s -> %s)",
                 stored_version, INDEX_VERSION)
        stale = True
    if stored_fingerprint != current_fingerprint:
        log.info("Stale index: knowledge base content changed (SHA-256 mismatch)")
        stale = True

    return stale


# ==============================================================================
# 3. VECTOR STORE SETUP  (runs once at import time / server startup)
# ==============================================================================

def _build_vector_store() -> tuple:
    """
    Load or rebuild the ChromaDB collection.

    Automatically rebuilds when:
      - The collection does not exist or is empty.
      - The embedding model, index version, or KB file fingerprint has changed.
    """
    os.makedirs(VECTOR_DIR, exist_ok=True)

    client = chromadb.PersistentClient(path=VECTOR_DIR)

    kb_fingerprint = _compute_kb_fingerprint()
    collection_meta = {
        "hnsw:space":       "cosine",
        "embedding_model":  EMBEDDING_MODEL,
        "index_version":    INDEX_VERSION,
        "kb_fingerprint":   kb_fingerprint,
    }

    # Load model (needed for both reuse and rebuild)
    log.info("Loading embedding model: %s", EMBEDDING_MODEL)
    model = SentenceTransformer(EMBEDDING_MODEL)
    log.info("Embedding model loaded.")

    # Check existing collection
    existing = None
    try:
        existing = client.get_collection(COLLECTION_NAME)
    except Exception:
        pass

    needs_rebuild = False
    if existing is None:
        log.info("No existing vector store found. Building from scratch.")
        needs_rebuild = True
    elif existing.count() == 0:
        log.info("Vector store is empty. Rebuilding.")
        needs_rebuild = True
    elif _is_index_stale(existing):
        log.info("Vector store is stale. Rebuilding.")
        needs_rebuild = True
    else:
        log.info("Vector store is current (%d vectors). Skipping re-indexing.",
                 existing.count())
        return existing, model

    # -- Rebuild ---------------------------------------------------------------
    if existing is not None:
        try:
            client.delete_collection(COLLECTION_NAME)
            log.info("Old collection deleted.")
        except Exception:
            pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata=collection_meta,
    )

    chunks = _load_all_chunks()
    if not chunks:
        log.warning("No chunks to embed -- knowledge_base/ may be empty.")
        return collection, model

    log.info("Generating embeddings for %d chunks ...", len(chunks))
    texts     = [c["text"]     for c in chunks]
    ids       = [c["chunk_id"] for c in chunks]
    metadatas = [{"source": c["source"], "chunk_id": c["chunk_id"]}
                 for c in chunks]

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    log.info("Vector store ready -- %d vectors indexed.", collection.count())
    return collection, model


# -- Initialise at import time ------------------------------------------------
log.info("=" * 60)
log.info("AgriConnect AI -- RAG Engine starting up")
log.info("=" * 60)
_collection, _model = _build_vector_store()
log.info("=" * 60)
log.info("RAG Engine ready. Listening for queries.")
log.info("=" * 60)


# ==============================================================================
# 4. PUBLIC QUERY FUNCTION
# ==============================================================================

def query(user_question: str, top_k: int = 3) -> list[dict]:
    """
    Embed the user's question and return the top-k most semantically
    relevant chunks from the knowledge base.

    Each result dict contains:
        "text"     -- the matched chunk text
        "source"   -- the .md filename it came from
        "distance" -- cosine distance (0 = identical, 2 = opposite)

    Results whose distance exceeds MAX_DISTANCE are filtered out so the
    caller can detect "no relevant content found" cleanly.
    """
    if not user_question.strip():
        return []

    query_embedding = _model.encode(
        [user_question],
        normalize_embeddings=True,
    ).tolist()

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
        if dist <= MAX_DISTANCE:
            hits.append({
                "text":     doc,
                "source":   meta["source"],
                "distance": round(dist, 4),
            })
            log.info("  ACCEPT  dist=%.4f  source=%-25s  query=%.50s",
                     dist, meta["source"], user_question)
        else:
            log.info("  REJECT  dist=%.4f  source=%-25s  (exceeds %.2f)  query=%.50s",
                     dist, meta["source"], MAX_DISTANCE, user_question)

    return hits
