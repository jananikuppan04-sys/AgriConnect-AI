"""
test_rag.py -- Test script for AgriConnect AI RAG chatbot

Two test modes:
  A. Deterministic retrieval tests (NO API calls required)
     Verify that each query retrieves the expected source filename.
     Tamil queries use pre-validated English rewrites for retrieval testing.

  B. Optional live Gemini integration tests (requires GEMINI_API_KEY)
     Verify complete Tamil/English answers via the full pipeline.

Run from backend/ with venv activated:
    python test_rag.py            # Mode A only (deterministic, offline)
    python test_rag.py --live     # Mode A + Mode B (requires Gemini API)
"""

import os
import sys
import argparse
import json

# Force UTF-8 stdout on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend/ is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


SAFE_FALLBACK = "I do not have verified information about that yet."

# -- Test cases ----------------------------------------------------------------
# Pre-validated English rewrites derived from diagnostics.py measurements:
#   Tamil tractor rewrite "How to rent a tractor?" -> rental_policy.md dist=0.4237
#   Tamil fake listing rewrite "How to report a fake or suspicious listing?"
#                               -> platform_faq.md dist=0.3117

IN_SCOPE_CASES = [
    {
        "query": "What is AgriConnect AI?",
        "expected_source": "platform_faq.md",
        "language": "en",
        "english_rewrite": None,   # English query, no rewrite needed
    },
    {
        "query": "Can I rent a tractor?",
        "expected_source": "rental_policy.md",
        "language": "en",
        "english_rewrite": None,
    },
    {
        "query": "How do I report a suspicious listing?",
        "expected_source": "platform_faq.md",
        "language": "en",
        "english_rewrite": None,
    },
    {
        "query": "\u0ba8\u0bbe\u0ba9\u0bcd \u0b9f\u0bbf\u0bb0\u0bbe\u0b95\u0bcd\u0b9f\u0bb0\u0bc8 \u0bb5\u0bbe\u0b9f\u0b95\u0bc8\u0b95\u0bcd\u0b95\u0bc1 \u0b8e\u0b9f\u0bc1\u0b95\u0bcd\u0b95 \u0bb5\u0bbf\u0bb0\u0bc1\u0bae\u0bcd\u0baa\u0bc1\u0b95\u0bbf\u0bb1\u0bc7\u0ba9\u0bcd. \u0b8e\u0baa\u0bcd\u0baa\u0b9f\u0bbf?",
        "expected_source": "rental_policy.md",
        "language": "ta",
        "english_rewrite": "How to rent a tractor?",
    },
    {
        "query": "\u0baa\u0bcb\u0bb2\u0bbf\u0baf\u0bbe\u0ba9 \u0bb5\u0bbf\u0bb3\u0bae\u0bcd\u0baa\u0bb0\u0ba4\u0bcd\u0ba4\u0bc8 \u0ba8\u0bbe\u0ba9\u0bcd \u0b8e\u0baa\u0bcd\u0baa\u0b9f\u0bbf \u0baa\u0bc1\u0b95\u0bbe\u0bb0\u0bcd \u0b9a\u0bc6\u0baf\u0bcd\u0baf\u0bb2\u0bbe\u0bae\u0bcd?",
        "expected_source": "platform_faq.md",
        "language": "ta",
        "english_rewrite": "How to report a fake or suspicious listing?",
    },
]

OUT_OF_SCOPE_CASES = [
    {
        "query": "\u0ba8\u0bbe\u0bb3\u0bc8\u0b95\u0bcd\u0b95\u0bc1 \u0bae\u0bb4\u0bc8 \u0baa\u0bc6\u0baf\u0bcd\u0baf\u0bc1\u0bae\u0bbe?",
        "expected_answer": SAFE_FALLBACK,
        "expected_sources": [],
    },
]


def _contains_tamil(text: str) -> bool:
    return any("\u0B80" <= c <= "\u0BFF" for c in text)


# ==============================================================================
# MODE A: Deterministic retrieval tests (NO API calls)
# ==============================================================================

def run_retrieval_tests() -> list[dict]:
    """
    Test that each query retrieves the correct source filename.
    Tamil queries use pre-validated English rewrites -- no Gemini API needed.
    This mirrors the app.py dual-query flow deterministically.
    """
    import rag_engine

    results = []
    print("\n" + "=" * 70)
    print("MODE A: Deterministic Retrieval Tests (offline)")
    print("=" * 70)

    for tc in IN_SCOPE_CASES:
        query_text = tc["query"]
        expected = tc["expected_source"]
        english_rewrite = tc.get("english_rewrite")

        # Phase 1: direct query
        hits = rag_engine.query(query_text, top_k=3)

        # Phase 2: for Tamil with a pre-validated rewrite, simulate dual-query
        if english_rewrite:
            best_direct_dist = hits[0]["distance"] if hits else float("inf")

            if best_direct_dist > rag_engine.REWRITE_THRESHOLD:
                rewrite_hits = rag_engine.query(english_rewrite, top_k=3)

                # Merge: best per source (mirrors app.py logic)
                all_hits = hits + rewrite_hits
                best_by_src: dict[str, dict] = {}
                for h in all_hits:
                    src = h["source"]
                    if (src not in best_by_src
                            or h["distance"] < best_by_src[src]["distance"]):
                        best_by_src[src] = h
                hits = sorted(best_by_src.values(),
                              key=lambda h: h["distance"])

        # Single-intent: take only the best chunk
        hits = hits[:1]

        top_source = hits[0]["source"] if hits else None
        top_dist = hits[0]["distance"] if hits else None
        passed = top_source == expected

        status_label = "PASS" if passed else "FAIL"
        print(f"\n  [{status_label}] {query_text[:65]}")
        print(f"         expected={expected}  got={top_source}  dist={top_dist}")
        if english_rewrite:
            print(f"         rewrite='{english_rewrite}'")

        results.append({
            "query": query_text,
            "expected_source": expected,
            "actual_source": top_source,
            "distance": top_dist,
            "rewrite": english_rewrite,
            "passed": passed,
        })

    # Out-of-scope: verify weather-only detection
    for tc in OUT_OF_SCOPE_CASES:
        query_text = tc["query"]

        from app import _is_weather_only
        is_oos = _is_weather_only(query_text)

        passed = is_oos
        status_label = "PASS" if passed else "FAIL"
        print(f"\n  [{status_label}] {query_text} (out-of-scope)")
        print(f"         weather_only_detected={is_oos}")

        results.append({
            "query": query_text,
            "expected_source": None,
            "actual_source": None,
            "distance": None,
            "rewrite": None,
            "passed": passed,
            "out_of_scope": True,
        })

    return results


# ==============================================================================
# MODE B: Live Gemini integration tests (requires API key)
# ==============================================================================

def run_live_tests() -> list[dict]:
    """Full pipeline tests querying the actual live FastAPI endpoint at http://127.0.0.1:8000/chat."""
    import requests

    results = []
    print("\n" + "=" * 70)
    print("MODE B: Live FastAPI /chat Integration Tests")
    print("=" * 70)

    url = "http://127.0.0.1:8000/chat"

    for tc in IN_SCOPE_CASES:
        query_text = tc["query"]
        expected_source = tc["expected_source"]
        language = tc["language"]

        try:
            res = requests.post(url, json={"message": query_text}, timeout=30)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"\n  [FAIL] {query_text[:65]}")
            print(f"         Request failed: {e}")
            results.append({
                "query": query_text, "passed": False,
                "reason": f"Request failed: {e}",
            })
            continue

        answer = data.get("answer", "")
        sources = data.get("sources", [])
        provider = data.get("provider_used", "")

        # Validate
        checks = []

        # Check 1: Expected source is present in the sources array
        source_found = any(s.get("filename") == expected_source for s in sources)
        checks.append(("source", source_found))

        # Check 2: Answer is not the generic fallback / unavailable
        is_fallback = (
            answer.strip() == SAFE_FALLBACK or
            "service is temporarily unavailable" in answer.strip().lower()
        )
        checks.append(("not_fallback", not is_fallback))

        # Check 3: Provider status is successful (e.g. gemini/openrouter, not unavailable/none)
        provider_ok = provider in ("gemini", "openrouter")
        checks.append(("provider_success", provider_ok))

        # Check 4: Tamil answer contains Tamil characters
        if language == "ta":
            has_tamil = _contains_tamil(answer)
            checks.append(("tamil_chars", has_tamil))
            word_count = len(answer.split())
            checks.append(("not_fragment", word_count >= 4))

        all_passed = all(ok for _, ok in checks)
        status_label = "PASS" if all_passed else "FAIL"

        check_str = ", ".join(f"{name}={'OK' if ok else 'FAIL'}"
                              for name, ok in checks)
        print(f"\n  [{status_label}] {query_text[:65]}")
        print(f"         checks: {check_str}")
        print(f"         answer: {answer[:120]}...")
        print(f"         provider: {provider}")

        results.append({
            "query": query_text,
            "checks": dict(checks),
            "answer_preview": answer[:150],
            "provider": provider,
            "passed": all_passed,
        })

    # Out-of-scope test
    for tc in OUT_OF_SCOPE_CASES:
        query_text = tc["query"]
        try:
            res = requests.post(url, json={"message": query_text}, timeout=30)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"\n  [FAIL] {query_text} (out-of-scope)")
            print(f"         Request failed: {e}")
            results.append({
                "query": query_text, "passed": False,
                "reason": f"Request failed: {e}",
            })
            continue

        answer = data.get("answer", "")
        sources = data.get("sources", [])
        provider = data.get("provider_used", "")

        # Weather returns the true no-knowledge fallback with sources=[]
        passed = (
            answer == SAFE_FALLBACK and
            sources == [] and
            provider == "none"
        )
        status_label = "PASS" if passed else "FAIL"
        print(f"\n  [{status_label}] {query_text} (out-of-scope)")
        print(f"         answer: {answer[:100]}")
        print(f"         sources: {sources}")

        results.append({
            "query": query_text,
            "passed": passed,
            "out_of_scope": True,
            "answer": answer[:150],
        })

    return results


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="AgriConnect AI RAG tests")
    parser.add_argument("--live", action="store_true",
                        help="Run Mode B live Gemini integration tests")
    args = parser.parse_args()

    all_results: list[dict] = []

    # Mode A (always runs, fully deterministic, no API calls)
    retrieval_results = run_retrieval_tests()
    all_results.extend(retrieval_results)

    # Mode B (optional, requires live Gemini API)
    live_results = []
    if args.live:
        live_results = run_live_tests()
        all_results.extend(live_results)

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    a_pass = sum(1 for r in retrieval_results if r["passed"])
    a_total = len(retrieval_results)
    print(f"  Mode A (Retrieval):    {a_pass}/{a_total} passed")

    if live_results:
        b_pass = sum(1 for r in live_results if r["passed"])
        b_total = len(live_results)
        print(f"  Mode B (Integration):  {b_pass}/{b_total} passed")
    elif args.live:
        print(f"  Mode B (Integration):  skipped (no API key)")

    total_pass = sum(1 for r in all_results if r["passed"])
    total_total = len(all_results)

    print(f"\n  TOTAL: {total_pass}/{total_total}")

    if total_pass == total_total:
        print("\n  ALL TESTS PASSED")
    else:
        print("\n  SOME TESTS FAILED")
        failed = [r for r in all_results if not r["passed"]]
        for f in failed:
            print(f"    FAILED: {f.get('query', '?')[:60]}")

    # Save results
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "test_results.json")
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(all_results, fp, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to: {out_path}")

    # Exit code
    sys.exit(0 if total_pass == total_total else 1)


if __name__ == "__main__":
    main()
