"""
llm_service.py -- LLM generation layer for AgriConnect AI

Provider order:
1. Gemini (google-genai SDK) -- primary
2. OpenRouter (requests / REST) -- backup
3. Safe fallback -- used when no provider returns a valid grounded answer
"""

import logging
import os
import textwrap

from dotenv import load_dotenv

# Load .env (safe if app.py has already loaded it)
load_dotenv()

log = logging.getLogger("llm_service")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "").strip()

SAFE_FALLBACK = "I do not have verified information about that yet."
_MAX_OUTPUT_TOKENS = 220


_SYSTEM_INSTRUCTION = textwrap.dedent(
    f"""\
    You are the AgriConnect AI Assistant for a verified agriculture marketplace.

    Use only the VERIFIED CONTEXT provided below. Do not invent facts, prices,
    dates, policies, availability, rules, or advice.

    Output requirements:
    - Return only the final answer. Do not reproduce raw document text, headings,
      document titles, numbering, source labels, or the prompt.
    - If the user asks in Tamil, answer in clear natural Tamil.
    - Tamil answers must contain one to three COMPLETE sentences and end with
      proper sentence punctuation. Never return a Tamil fragment or English text.
    - If the user asks in English, answer in clear English.
    - Keep the answer under 90 words.
    - Do not mention the provider, retrieved chunks, source files, or that you
      are an AI model.

    If the verified context is insufficient to answer the question, reply exactly:
    {SAFE_FALLBACK}
    """
)


def _contains_tamil(text: str) -> bool:
    """Return True when text contains at least one Tamil Unicode character."""
    return any("\u0B80" <= char <= "\u0BFF" for char in text)


def _normalise(text: str) -> str:
    """Collapse whitespace for consistent output validation."""
    return " ".join(text.strip().split())


def _is_valid_generated_answer(answer: str, question: str) -> bool:
    """
    Reject blank, incomplete, raw-context, or language-mismatched outputs.

    Validation rules (per requirements):
      - Tamil question must receive Tamil characters.
      - Reject obvious fragments under four words.
      - Reject raw source headings/chunk text.
      - Do NOT require exactly . ! ? or period as the final character.
    """
    cleaned = _normalise(answer)

    # Empty
    if not cleaned:
        log.info("  validation: rejected (empty)")
        return False

    # Safe fallback is always valid
    if cleaned.casefold() == SAFE_FALLBACK.casefold():
        return True

    # Reject obvious fragments (< 4 words)
    if len(cleaned.split()) < 4:
        log.info("  validation: rejected (fragment, < 4 words)")
        return False

    # Tamil question must get Tamil answer
    if _contains_tamil(question) and not _contains_tamil(cleaned):
        log.info("  validation: rejected (Tamil question got non-Tamil answer)")
        return False

    # Reject raw knowledge-base headings/chunks reaching the UI
    raw_markers = (
        "equipment rental policy rental flow",
        "platform listing regulations",
        "--- verified context ---",
        "source:",
        "context:",
        "--- end verified context ---",
    )
    if any(marker in cleaned.casefold() for marker in raw_markers):
        log.info("  validation: rejected (contains raw source markers)")
        return False

    # Passed all checks -- no strict punctuation requirement
    return True


def _build_context_block(retrieved_chunks: list[dict]) -> str:
    """Format accepted vector-search results for the LLM prompt."""
    parts: list[str] = []

    for chunk in retrieved_chunks:
        source = chunk.get("source", "unknown")
        page = chunk.get("page")

        if page is not None and str(page).strip() not in ("", "None"):
            page_label = str(page).strip()
        else:
            page_label = "N/A"

        parts.append(
            f"Source: {source}\n"
            f"Page: {page_label}\n"
            f"Context:\n{chunk.get('text', '').strip()}"
        )

    return "\n\n".join(parts)


def _build_full_prompt(question: str, context_block: str) -> str:
    """Combine instructions, grounded context, and the original user question."""
    return (
        f"{_SYSTEM_INSTRUCTION}\n\n"
        "--- VERIFIED CONTEXT ---\n"
        f"{context_block}\n"
        "--- END VERIFIED CONTEXT ---\n\n"
        f"User question: {question}\n"
        "Final answer:"
    )


def _call_gemini(question: str, context_block: str) -> tuple[str | None, str]:
    """Call Gemini and accept only complete, language-matched answers. Returns (answer, status_string)."""
    if not GEMINI_API_KEY:
        log.info("LLM provider: Gemini skipped (GEMINI_API_KEY not set)")
        return None, "no_api_key"

    try:
        from google import genai                       # type: ignore
        from google.genai import types as genai_types  # type: ignore

        client = genai.Client(api_key=GEMINI_API_KEY)
        base_prompt = _build_full_prompt(question, context_block)

        # A second attempt handles occasional incomplete model output.
        for attempt in range(2):
            prompt = base_prompt

            if attempt == 1:
                prompt += (
                    "\n\nCorrection: Return a complete final answer only. "
                    "Do not return a fragment, heading, source label, or raw context. "
                    "Follow the requested language exactly."
                )

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=_MAX_OUTPUT_TOKENS,
                ),
            )

            answer = response.text.strip() if response.text else ""

            if _is_valid_generated_answer(answer, question):
                log.info("LLM provider: Gemini (model=%s)", GEMINI_MODEL)
                return answer, "gemini_success"

            log.warning(
                "Gemini returned an invalid or incomplete answer; attempt %d rejected.",
                attempt + 1,
            )

        return None, "validation_rejected"

    except Exception as exc:
        log.error("Gemini API error: %s", exc)
        exc_str = str(exc).lower()
        if "429" in exc_str or "resource_exhausted" in exc_str or "quota" in exc_str:
            return None, "gemini_quota_exhausted"
        return None, "api_error"


def _call_openrouter(question: str, context_block: str) -> tuple[str | None, str]:
    """Call OpenRouter only when its credentials and model are configured. Returns (answer, status_string)."""
    if not OPENROUTER_API_KEY:
        log.info("LLM provider: OpenRouter skipped (OPENROUTER_API_KEY not set)")
        return None, "openrouter_skipped"

    if not OPENROUTER_MODEL:
        log.info("LLM provider: OpenRouter skipped (OPENROUTER_MODEL not set)")
        return None, "openrouter_skipped"

    try:
        import requests  # type: ignore

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": _build_full_prompt(question, context_block),
                    }
                ],
                "max_tokens": _MAX_OUTPUT_TOKENS,
                "temperature": 0.1,
            },
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://agriconnect.ai",
                "X-Title": "AgriConnect AI",
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        choices = data.get("choices", [])

        if not choices:
            log.warning("OpenRouter returned no choices.")
            return None, "api_error"

        answer = choices[0].get("message", {}).get("content", "").strip()

        if not _is_valid_generated_answer(answer, question):
            log.warning("OpenRouter returned an invalid or incomplete answer.")
            return None, "validation_rejected"

        log.info("LLM provider: OpenRouter backup (model=%s)", OPENROUTER_MODEL)
        return answer, "openrouter_success"

    except Exception as exc:
        log.error("OpenRouter API error: %s", exc)
        return None, "api_error"


def generate_grounded_answer(
    question: str,
    retrieved_chunks: list[dict],
) -> dict:
    """
    Generate a grounded answer without exposing raw retrieved text.

    A provider must return a valid, complete response. Otherwise the function
    uses the exact safe fallback so app.py can return an empty sources list.
    """
    context_block = _build_context_block(retrieved_chunks)

    # 1. Try Gemini
    answer, gemini_status = _call_gemini(question, context_block)
    if answer is not None:
        return {
            "answer": answer,
            "provider_used": "gemini",
            "provider_status": gemini_status,
            "generation_failed": False,
        }

    # 2. Try OpenRouter backup
    answer_or, or_status = _call_openrouter(question, context_block)
    if answer_or is not None:
        return {
            "answer": answer_or,
            "provider_used": "openrouter",
            "provider_status": or_status,
            "generation_failed": False,
        }

    # Determine final error status to propagate
    # Prioritize quota limit or validation rejection status
    final_status = gemini_status
    if final_status in ("no_api_key", "api_error") and or_status != "openrouter_skipped":
        final_status = or_status

    # Map status to one of: gemini_quota_exhausted | validation_rejected | no_hit (or default to validation_rejected)
    mapped_status = "validation_rejected"
    if final_status == "gemini_quota_exhausted":
        mapped_status = "gemini_quota_exhausted"
    elif final_status == "validation_rejected":
        mapped_status = "validation_rejected"

    log.warning("No provider returned a valid answer. Final status: %s (mapped: %s)", final_status, mapped_status)
    return {
        "answer": SAFE_FALLBACK,
        "provider_used": "none",
        "provider_status": final_status,
        "mapped_status": mapped_status,
        "generation_failed": True,
    }
