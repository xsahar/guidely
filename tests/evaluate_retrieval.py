import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.document_loader import process_documents
from backend.services.vector_store import VectorStore


EVALUATION_QUERIES = (
    ("How many vacation and PTO days are provided each year?", "pto_policy.txt"),
    ("pto", "pto_policy.txt"),
    ("IT", "it_policy.txt"),
    ("What are remote work hours and home office benefits?", "remote_work_policy.txt"),
    ("How do employees secure company accounts and laptops?", "security_policy.txt"),
    ("How can I install software or request IT help?", "it_policy.txt"),
    ("How should employees report harassment or ethical concerns?", "code_of_conduct.txt"),
)


def main() -> None:
    chunks = process_documents("backend/data/sample-docs")
    store = VectorStore()
    store.build_index(chunks)
    hits = 0

    for query, expected_source in EVALUATION_QUERIES:
        results = store.search(query, top_k=3)
        found = any(result["filename"] == expected_source for result in results)
        hits += int(found)
        print(
            f"{'PASS' if found else 'FAIL'}: {query} -> "
            f"{[result['filename'] for result in results]} (expected {expected_source})"
        )

    score = hits / len(EVALUATION_QUERIES)
    print(f"Retrieval@3: {hits}/{len(EVALUATION_QUERIES)} ({score:.1%})")
    out_of_scope = store.search("What is the company cafeteria menu?", top_k=3)
    print(f"Out-of-scope query sources: {[result['filename'] for result in out_of_scope]}")
    if out_of_scope:
        raise SystemExit("Out-of-scope query returned low-relevance sources.")
    short_noise = store.search("t", top_k=3)
    print(f"One-character query sources: {[result['filename'] for result in short_noise]}")
    if short_noise:
        raise SystemExit("One-character query returned low-relevance sources.")
    if score < 0.8:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
