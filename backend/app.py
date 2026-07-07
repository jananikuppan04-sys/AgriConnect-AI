"""
app.py -- AgriConnect AI FastAPI backend

Uses rag_engine.py for semantic retrieval via local ChromaDB + sentence-transformers.
Uses llm_service.py for LLM-powered answer generation with provider fallback.

Tamil query support:
  1. Query the vector store with the original Tamil text first.
  2. If no confident hit (distance > REWRITE_THRESHOLD), generate a concise
     English retrieval rewrite using Gemini.
  3. Query with the rewrite, merge and rank results from both queries.
  4. Select only the best verified chunk for single-intent questions.
  5. Preserve the original Tamil question for answer generation.
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment variables before provider-specific imports
load_dotenv()

import rag_engine
import llm_service

log = logging.getLogger("app")

SAFE_FALLBACK = "I do not have verified information about that yet."

app = FastAPI(
    title="AgriConnect AI Backend",
    description="Semantic FAQ chatbot for the AgriConnect AI agriculture marketplace.",
    version="4.0.0",
)

# -- CORS (configurable via FRONTEND_ORIGINS env var) --------------------------
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_env_origins = os.getenv("FRONTEND_ORIGINS", "").strip()
origins = (
    [o.strip() for o in _env_origins.split(",") if o.strip()]
    if _env_origins
    else _default_origins
)
log.info("CORS origins: %s", origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's question")


# ==============================================================================
# HELPERS
# ==============================================================================

def _contains_tamil(text: str) -> bool:
    """Return True when text contains at least one Tamil Unicode character."""
    return any("\u0B80" <= char <= "\u0BFF" for char in text)


def _is_weather_only(text: str) -> bool:
    """
    Return True only when the entire query is about weather/climate with
    no platform-related terms.  A mixed query like "Can I rent a tractor
    when it rains?" is NOT weather-only and will be processed normally.
    """
    weather_terms = {
        "rain", "weather", "forecast", "temperature", "storm", "climate",
        "sunny", "snow", "humidity",
        "\u0bae\u0bb4\u0bc8",            # rain
        "\u0bb5\u0bbe\u0ba9\u0bbf\u0bb2\u0bc8",  # weather
        "\u0bb5\u0bc6\u0baa\u0bcd\u0baa\u0ba8\u0bbf\u0bb2\u0bc8",  # temperature
    }
    platform_terms = {
        "rent", "tractor", "listing", "sell", "buy", "report", "equipment",
        "product", "farmer", "seller", "buyer", "crop", "price", "order",
        "marketplace", "agriconnect", "register", "booking", "verify",
        "\u0b9f\u0bbf\u0bb0\u0bbe\u0b95\u0bcd\u0b9f\u0bb0\u0bcd",  # tractor
        "\u0bb5\u0bbe\u0b9f\u0b95\u0bc8",       # rent
        "\u0bb5\u0bbf\u0bb3\u0bae\u0bcd\u0baa\u0bb0",   # listing
        "\u0bb5\u0bbf\u0bb1\u0bcd\u0b95",       # sell
        "\u0bb5\u0bbf\u0bb1\u0bcd\u0baa\u0ba9\u0bc8",   # selling
        "\u0baa\u0bc1\u0b95\u0bbe\u0bb0\u0bcd",       # complaint
        "\u0baa\u0bcb\u0bb2\u0bbf",           # fake
        "\u0b95\u0bbe\u0baf\u0bcd\u0b95\u0bb1\u0bbf",   # vegetable
        "\u0bb5\u0bbf\u0bb1\u0bcd\u0baa\u0ba9\u0bc8\u0baf\u0bbe\u0bb3\u0bb0\u0bcd",  # seller
    }

    normalized = text.casefold()
    has_weather = any(term in normalized for term in weather_terms)
    has_platform = any(term in normalized for term in platform_terms)

    return has_weather and not has_platform


def _generate_english_rewrite(tamil_query: str) -> str | None:
    """
    Use Gemini to translate a Tamil question into a concise English
    search query for vector retrieval.  Returns None on failure.
    Does not log or expose API keys.
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        log.info("Tamil rewrite skipped: GEMINI_API_KEY not set")
        return None

    try:
        from google import genai                          # type: ignore
        from google.genai import types as genai_types     # type: ignore

        client = genai.Client(api_key=gemini_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

        prompt = (
            "Translate the following Tamil question into a concise English "
            "search query (one sentence, no explanation).\n\n"
            f"Tamil: {tamil_query}\n"
            "English query:"
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=60,
            ),
        )

        rewrite = response.text.strip() if response.text else ""

        if rewrite and len(rewrite) > 3:
            log.info("Tamil rewrite: '%s' -> '%s'",
                     tamil_query[:60], rewrite[:80])
            return rewrite

        return None
    except Exception as exc:
        log.error("Gemini rewrite error: %s", exc)
        return None


def _is_fallback_answer(answer: str) -> bool:
    """Prevent sources from being shown when the model returns fallback text."""
    normalized = " ".join(answer.strip().casefold().split())
    fallback = " ".join(SAFE_FALLBACK.casefold().split())
    return normalized == fallback


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "AgriConnect backend is running"}


@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    """Retrieve verified content, then generate a grounded response."""
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message field cannot be empty.",
        )

    user_message = request.message.strip()
    is_tamil = _contains_tamil(user_message)

    log.info("--- New query ---")
    log.info("  original_query: %s", user_message)
    log.info("  is_tamil: %s", is_tamil)

    # -- Weather-only early exit (does not reject mixed queries) ---------------
    if _is_weather_only(user_message):
        log.info("  reason: weather-only query, out-of-scope")
        response_data = {
            "answer": SAFE_FALLBACK,
            "sources": [],
            "provider_used": "none",
        }
        if os.getenv("DEBUG_RAG", "").strip().lower() == "true":
            response_data["debug"] = {
                "selected_source": "none",
                "distance": 0.0,
                "retrieval_accepted": False,
                "provider_status": "no_hit"
            }
        return response_data

    # -- Phase 1: Query with original user text --------------------------------
    hits = rag_engine.query(user_message, top_k=3)

    # -- Phase 2: For Tamil, try English rewrite if not confident --------------
    retrieval_rewrite = None
    if is_tamil:
        best_direct_dist = hits[0]["distance"] if hits else float("inf")

        if best_direct_dist > rag_engine.REWRITE_THRESHOLD:
            retrieval_rewrite = _generate_english_rewrite(user_message)

            if retrieval_rewrite:
                rewrite_hits = rag_engine.query(retrieval_rewrite, top_k=3)

                # Merge: keep best (lowest distance) per source
                all_hits = hits + rewrite_hits
                best_by_source: dict[str, dict] = {}
                for h in all_hits:
                    src = h["source"]
                    if (src not in best_by_source
                            or h["distance"] < best_by_source[src]["distance"]):
                        best_by_source[src] = h
                hits = sorted(best_by_source.values(),
                              key=lambda h: h["distance"])

                log.info("  retrieval_rewrite: %s", retrieval_rewrite)
            else:
                log.info("  retrieval_rewrite: failed (using direct hits only)")
        else:
            log.info("  retrieval_rewrite: not needed (direct dist=%.4f)",
                     best_direct_dist)
    else:
        log.info("  retrieval_query: %s", user_message[:80])

    # -- Select only the single best chunk for single-intent questions ---------
    hits = hits[:1]

    if not hits:
        log.info("  result: no hits passed threshold, returning fallback")
        response_data = {
            "answer": SAFE_FALLBACK,
            "sources": [],
            "provider_used": "none",
        }
        if os.getenv("DEBUG_RAG", "").strip().lower() == "true":
            response_data["debug"] = {
                "selected_source": "none",
                "distance": 0.0,
                "retrieval_accepted": False,
                "provider_status": "no_hit"
            }
        return response_data

    log.info("  selected_source: %s", hits[0].get("source"))
    log.info("  selected_distance: %.4f", hits[0].get("distance", 0))
    log.info("  accepted: yes")

    # -- Generate answer using original user question --------------------------
    result = llm_service.generate_grounded_answer(
        question=user_message,
        retrieved_chunks=hits,
    )

    log.info("  provider_used: %s", result["provider_used"])

    # -- Build source list for the response ------------------------------------
    sources: list[dict] = []
    seen_sources: set[str] = set()

    for hit in hits:
        filename = hit.get("source", "")
        raw_page = hit.get("page")

        if raw_page is not None and str(raw_page).strip() not in ("", "None"):
            try:
                page = int(str(raw_page).strip())
            except ValueError:
                page = None
        else:
            page = None

        key = f"{filename}:{page}"
        if key not in seen_sources:
            seen_sources.add(key)
            sources.append({"filename": filename, "page": page})

    # If generation failed but we had hits, return the "service unavailable" warning
    if result.get("generation_failed", False):
        log.info("  reason: LLM generation failed but verified context was found")
        response_data = {
            "answer": "Verified information was found, but the answer-generation service is temporarily unavailable. Please try again shortly.",
            "sources": sources,
            "provider_used": "unavailable"
        }
        if os.getenv("DEBUG_RAG", "").strip().lower() == "true":
            response_data["debug"] = {
                "selected_source": hits[0].get("source") if hits else "none",
                "distance": hits[0].get("distance") if hits else 0.0,
                "retrieval_accepted": True,
                "provider_status": result.get("mapped_status", "validation_rejected")
            }
        return response_data

    # Never show sources with fallback output
    if _is_fallback_answer(result["answer"]):
        log.info("  reason: LLM returned fallback answer")
        response_data = {
            "answer": SAFE_FALLBACK,
            "sources": [],
            "provider_used": result["provider_used"],
        }
        if os.getenv("DEBUG_RAG", "").strip().lower() == "true":
            response_data["debug"] = {
                "selected_source": hits[0].get("source") if hits else "none",
                "distance": hits[0].get("distance") if hits else 0.0,
                "retrieval_accepted": True,
                "provider_status": "validation_rejected"
            }
        return response_data

    response_data = {
        "answer": result["answer"],
        "sources": sources,
        "provider_used": result["provider_used"],
    }
    if os.getenv("DEBUG_RAG", "").strip().lower() == "true":
        response_data["debug"] = {
            "selected_source": hits[0].get("source") if hits else "none",
            "distance": hits[0].get("distance") if hits else 0.0,
            "retrieval_accepted": True,
            "provider_status": "gemini_success"
        }
    return response_data