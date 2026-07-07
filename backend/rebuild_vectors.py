"""
rebuild_vectors.py -- Rebuild ChromaDB vector store for AgriConnect AI.
Run once from the backend/ directory with the venv activated:
    python rebuild_vectors.py

Stores EMBEDDING_MODEL, INDEX_VERSION, and a SHA-256 fingerprint of all
knowledge_base/*.md files in the Chroma collection metadata so that
rag_engine.py can detect stale indexes at startup.
"""

import os
import re
import hashlib
import logging

import chromadb
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("rebuild")

HERE       = os.path.dirname(os.path.abspath(__file__))
KB_DIR     = os.path.join(HERE, "knowledge_base")
VECTOR_DIR = os.path.join(HERE, "vector_store")
COLLECTION = "agriconnect_kb"

# These constants MUST match rag_engine.py
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
INDEX_VERSION   = "2"
CHUNK_SIZE      = 60
OVERLAP         = 12


def clean_md(text: str) -> str:
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}|_{1,3}", "", text)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_chunks(text: str, source: str) -> list:
    words = text.split()
    chunks, start, num = [], 0, 0
    while start < len(words):
        end  = min(start + CHUNK_SIZE, len(words))
        body = " ".join(words[start:end])
        chunks.append({
            "text":   body,
            "source": source,
            "id":     f"{source}__chunk{num}",
        })
        num  += 1
        start += CHUNK_SIZE - OVERLAP
        if end == len(words):
            break
    return chunks


def compute_kb_fingerprint() -> str:
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


# -- Load and chunk all knowledge base files -----------------------------------
all_chunks = []
for fn in sorted(os.listdir(KB_DIR)):
    if fn.endswith(".md"):
        path = os.path.join(KB_DIR, fn)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        c = split_chunks(clean_md(raw), fn)
        all_chunks.extend(c)
        log.info("  %s -> %d chunks", fn, len(c))

log.info("Total chunks: %d", len(all_chunks))

# -- Embed ---------------------------------------------------------------------
log.info("Loading model: %s ...", EMBEDDING_MODEL)
model = SentenceTransformer(EMBEDDING_MODEL)

passages   = [c["text"] for c in all_chunks]
log.info("Embedding %d chunks ...", len(passages))
embeddings = model.encode(
    passages,
    normalize_embeddings=True,
    show_progress_bar=True,
).tolist()

# -- Write to ChromaDB --------------------------------------------------------
kb_fingerprint = compute_kb_fingerprint()
collection_meta = {
    "hnsw:space":      "cosine",
    "embedding_model": EMBEDDING_MODEL,
    "index_version":   INDEX_VERSION,
    "kb_fingerprint":  kb_fingerprint,
}

client = chromadb.PersistentClient(path=VECTOR_DIR)
try:
    client.delete_collection(COLLECTION)
    log.info("Old collection deleted.")
except Exception:
    log.info("No existing collection to delete.")

col = client.create_collection(COLLECTION, metadata=collection_meta)
col.upsert(
    ids        = [c["id"]     for c in all_chunks],
    documents  = [c["text"]   for c in all_chunks],
    embeddings = embeddings,
    metadatas  = [{"source": c["source"], "chunk_id": c["id"]} for c in all_chunks],
)
log.info("Vector store rebuilt with %d vectors.", col.count())
log.info("Metadata: model=%s  version=%s  fingerprint=%s",
         EMBEDDING_MODEL, INDEX_VERSION, kb_fingerprint[:16] + "...")
log.info("Done!")
