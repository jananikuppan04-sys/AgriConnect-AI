"""
app.py  –  AgriConnect AI FastAPI backend
Uses rag_engine.py for semantic retrieval via local ChromaDB + sentence-transformers.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import the RAG engine – this triggers startup indexing / model loading
import rag_engine

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AgriConnect AI Backend",
    description="Semantic FAQ chatbot for the AgriConnect AI agriculture marketplace.",
    version="2.0.0",
)

# ── CORS – allow only the local Vite dev server ───────────────────────────────
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Data models ───────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's question")


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Quick liveness probe – unchanged from v1."""
    return {
        "status": "ok",
        "message": "AgriConnect backend is running",
    }


@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    """
    Semantic FAQ retrieval endpoint.

    1. Validates the incoming message is non-empty.
    2. Queries the RAG engine for the top-3 most relevant chunks.
    3. Returns the best chunk as the answer, with source filenames.
    4. Falls back gracefully when no relevant content is found.
    """
    # ── Validation ────────────────────────────────────────────────────────────
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message field cannot be empty.",
        )

    user_message = request.message.strip()

    # ── Semantic retrieval ────────────────────────────────────────────────────
    # rag_engine.query() returns a list of dicts sorted by relevance (closest first).
    # Each dict: { "text": str, "source": str, "distance": float }
    hits = rag_engine.query(user_message, top_k=3)

    # ── No relevant content found ─────────────────────────────────────────────
    if not hits:
        return {
            "answer": "I do not have verified information about that yet.",
            "sources": [],
        }

    # ── Build the response ────────────────────────────────────────────────────
    # Use the top (closest) chunk as the primary answer.
    best = hits[0]
    answer = f"Based on AgriConnect AI information:\n\n{best['text']}"

    # Collect unique source filenames across all returned hits (preserving order).
    seen: set[str] = set()
    unique_sources: list[str] = []
    for hit in hits:
        if hit["source"] not in seen:
            seen.add(hit["source"])
            unique_sources.append(hit["source"])

    return {
        "answer": answer,
        "sources": unique_sources,
    }
