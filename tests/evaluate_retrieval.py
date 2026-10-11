import sys
from pathlib import Path
from statistics import median
from time import perf_counter
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.document_loader import process_documents
from backend.services.llm_chain import LLMChain
from backend.services.vector_store import VectorStore


DATA_DIR = Path("backend/data/sample-docs")
EVALUATION_QUERIES = (
    ("How many vacation and PTO days are provided each year?", {"pto_policy.txt"}),
    ("pto", {"pto_policy.txt"}),
    ("IT", {"it_policy.txt"}),
    ("What are remote work hours and home office benefits?", {"remote_work_policy.txt"}),
    ("How do employees secure company accounts and laptops?", {"security_policy.txt"}),
    ("How can I install software or request IT help?", {"it_policy.txt"}),
    ("How should employees report harassment or ethical concerns?", {"code_of_conduct.txt"}),
    (
        "What networking mode does WSL2 use?",
        {"wsl_api_test.txt", "api-key (cursor).txt"},
    ),
    ("Which port does the internal test API use?", {"wsl_api_test.txt"}),
)
OUT_OF_SCOPE_QUERY = "What is the company cafeteria menu?"
TARGETS = {
    "retrieval_at_3": 0.80,
    "answer_reference_coverage": 0.90,
    "source_precision": 0.80,
    "median_latency_ms": 3000,
    "p95_latency_ms": 5000,
}


def make_offline_chain(store: VectorStore) -> LLMChain:
    chain = LLMChain.__new__(LLMChain)
    chain.vector_store = store
    chain.model = "offline-evaluation-stub"
    chain.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **_kwargs: SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content="Evaluation response based on the retrieved context."
                            )
                        )
                    ]
                )
            )
        )
    )
    return chain


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    index = max(0, int(len(ordered) * percentile_value + 0.999999) - 1)
    return ordered[index]


def main() -> None:
    chunks = process_documents(str(DATA_DIR))
    if not chunks:
        raise SystemExit(f"No text document chunks found under {DATA_DIR}.")

    store = VectorStore()
    store.load_or_build_index(chunks)
    repeated_store = VectorStore()
    repeated_store.load_or_build_index(chunks)
    cache_hit_rate = (
        1.0
        if repeated_store.cache_hit and repeated_store.embedded_chunks == 0
        else 0.0
    )

    chain = make_offline_chain(store)
    available_files = {chunk["filename"] for chunk in chunks}
    retrieval_hits = 0
    reference_hits = 0
    correct_sources = 0
    cited_sources = 0

    for question, expected_sources in EVALUATION_QUERIES:
        expected = expected_sources.intersection(available_files)
        if not expected:
            raise SystemExit(
                f"Expected source files are missing for evaluation query: {question}"
            )

        top_three = store.search(question, top_k=3)
        retrieval_found = any(
            result["filename"] in expected for result in top_three
        )
        retrieval_hits += int(retrieval_found)

        result = chain.generate_response(question, top_k=5)
        sources = result["sources"]
        matching_sources = expected.intersection(sources)
        reference_hits += int(bool(matching_sources))
        correct_sources += len(matching_sources)
        cited_sources += len(sources)
        print(
            f"{'PASS' if retrieval_found else 'FAIL'}: {question} -> {sources} "
            f"(expected one of {sorted(expected)})"
        )

    retrieval_at_3 = retrieval_hits / len(EVALUATION_QUERIES)
    reference_coverage = reference_hits / len(EVALUATION_QUERIES)
    source_precision = correct_sources / cited_sources if cited_sources else 0.0
    print(
        f"Retrieval@3: {retrieval_hits}/{len(EVALUATION_QUERIES)} "
        f"({retrieval_at_3:.1%}; target >=80%)"
    )
    print(
        f"Answer reference coverage: {reference_hits}/{len(EVALUATION_QUERIES)} "
        f"({reference_coverage:.1%}; target >=90%, offline answer stub)"
    )
    print(
        f"Source precision: {correct_sources}/{cited_sources} "
        f"({source_precision:.1%}; target >=80%)"
    )
    print(
        f"Unchanged-index cache reuse: {cache_hit_rate:.0%} "
        f"({repeated_store.embedded_chunks} chunks re-embedded)"
    )

    answerless = chain.generate_response(OUT_OF_SCOPE_QUERY)
    print(
        "Out-of-scope query: "
        f"sources={answerless['sources']} "
        f"(expected []); answer={answerless['answer']}"
    )
    if answerless["sources"]:
        raise SystemExit("Out-of-scope query unexpectedly returned source citations.")

    short_noise = chain.generate_response("t")
    print(f"One-character query sources: {short_noise['sources']} (expected [])")
    if short_noise["sources"]:
        raise SystemExit("One-character query unexpectedly returned source citations.")

    for question, _expected in EVALUATION_QUERIES:
        chain.generate_response(question, top_k=5)
    timings_ms = []
    for _ in range(5):
        for question, _expected in EVALUATION_QUERIES:
            started = perf_counter()
            chain.generate_response(question, top_k=5)
            timings_ms.append((perf_counter() - started) * 1000)

    median_ms = median(timings_ms)
    p95_ms = percentile(timings_ms, 0.95)
    print(
        f"Cached local pipeline latency (offline answer stub, {len(timings_ms)} runs): "
        f"median={median_ms:.2f} ms (target <3000 ms), "
        f"p95={p95_ms:.2f} ms (target <5000 ms)"
    )
    print(
        "Provider latency is excluded from this offline benchmark; use GET /metrics "
        "to observe live end-to-end query latency."
    )

    passed = (
        retrieval_at_3 >= TARGETS["retrieval_at_3"]
        and reference_coverage >= TARGETS["answer_reference_coverage"]
        and source_precision >= TARGETS["source_precision"]
        and cache_hit_rate == 1.0
        and median_ms < TARGETS["median_latency_ms"]
        and p95_ms < TARGETS["p95_latency_ms"]
    )
    if not passed:
        raise SystemExit("One or more evaluation metrics did not meet their target.")


if __name__ == "__main__":
    main()
