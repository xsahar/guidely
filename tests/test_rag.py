import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routes import query as query_route
from backend.services import vector_store as vector_store_module
from backend.services.document_loader import chunk_text, load_text_files
from backend.services.llm_chain import LLMChain, is_abstention
from backend.services.vector_store import VectorStore


class VectorStoreTests(unittest.TestCase):
    def setUp(self):
        self.vectors = {
            "best": np.array([1.0, 0.0, 0.0], dtype="float32"),
            "near": np.array([0.99, 0.1, 0.0], dtype="float32"),
            "unrelated": np.array([0.0, 1.0, 0.0], dtype="float32"),
            "weak-query": np.array([0.0, 0.0, 1.0], dtype="float32"),
        }
        self.encode = patch.object(
            vector_store_module.embedding_model,
            "encode",
            side_effect=lambda texts, **_kwargs: np.stack(
                [self.vectors[text.split("\n")[-1]] for text in texts]
            ),
        )
        self.encode.start()
        self.addCleanup(self.encode.stop)

    def test_search_returns_relevant_top_three_and_excludes_weak_matches(self):
        store = VectorStore(dimension=3)
        store.build_index(
            [
                {"filename": "pto_policy.txt", "text": "best"},
                {"filename": "another_policy.txt", "text": "near"},
                {"filename": "unrelated.txt", "text": "unrelated"},
            ]
        )

        matches = store.search("best", top_k=3)
        matched_sources = {match["filename"] for match in matches}
        self.assertEqual(matched_sources, {"pto_policy.txt", "another_policy.txt"})
        self.assertNotIn("unrelated.txt", matched_sources)
        self.assertEqual(store.search("weak-query", top_k=3), [])

    def test_short_filename_terms_find_uploaded_document_even_with_weak_embedding(self):
        store = VectorStore(dimension=3)

        def encode(texts, **_kwargs):
            return np.stack([
                np.array([0.0, 1.0, 0.0], dtype="float32")
                if text.startswith("Document:")
                else np.array([1.0, 0.0, 0.0], dtype="float32")
                for text in texts
            ])

        with patch.object(vector_store_module.embedding_model, "encode", side_effect=encode):
            store.build_index([{"filename": "it_policy.txt", "text": "Approved tools only."}])
            results = store.search("IT", top_k=3)
            self.assertEqual([result["filename"] for result in results], ["it_policy.txt"])
            self.assertEqual(store.search("t", top_k=3), [])

    def test_short_terms_match_text_inside_config_identifiers(self):
        store = VectorStore(dimension=3)

        def encode(texts, **_kwargs):
            return np.stack([
                np.array([0.0, 1.0, 0.0], dtype="float32")
                if text.startswith("Document:")
                else np.array([1.0, 0.0, 0.0], dtype="float32")
                for text in texts
            ])

        with patch.object(vector_store_module.embedding_model, "encode", side_effect=encode):
            store.build_index([
                {
                    "filename": "windows_setup.txt",
                    "text": "[wsl2]\nnetworkingMode=mirrored\nAPI configuration",
                }
            ])

            for term in ("wsl", "api"):
                with self.subTest(term=term):
                    results = store.search(term, top_k=3)
                    self.assertEqual(
                        [result["filename"] for result in results],
                        ["windows_setup.txt"],
                    )

    def test_cache_reuses_unchanged_embeddings_and_rebuilds_changed_content(self):
        with tempfile.TemporaryDirectory() as directory:
            chunks = [{"filename": "pto.txt", "text": "best"}]
            first = VectorStore(dimension=3, cache_dir=Path(directory))
            first.load_or_build_index(chunks)
            self.assertFalse(first.cache_hit)
            self.assertEqual(first.embedded_chunks, 1)

            with patch.object(vector_store_module.embedding_model, "encode") as encode:
                second = VectorStore(dimension=3, cache_dir=Path(directory))
                second.load_or_build_index(chunks)
                self.assertTrue(second.cache_hit)
                self.assertEqual(second.embedded_chunks, 0)
                encode.assert_not_called()

            changed = VectorStore(dimension=3, cache_dir=Path(directory))
            changed.load_or_build_index([{"filename": "pto.txt", "text": "near"}])
            self.assertFalse(changed.cache_hit)
            self.assertEqual(changed.embedded_chunks, 1)

    def test_document_chunking_has_expected_overlap(self):
        words = [f"word{index}" for index in range(400)]
        chunks = chunk_text(" ".join(words), chunk_size=200, overlap=30)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].split()[-30:], chunks[1].split()[:30])

    def test_corrupted_utf8_document_is_skipped_and_logged(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "broken.txt").write_bytes(b"\xff")
            Path(directory, "valid.txt").write_text("valid policy", encoding="utf-8")
            with self.assertLogs("backend.services.document_loader", level="ERROR"):
                documents = load_text_files(directory)
        self.assertEqual([document["filename"] for document in documents], ["valid.txt"])


class LLMChainTests(unittest.TestCase):
    def test_abstention_answers_do_not_cite_retrieved_documents(self):
        chain = LLMChain.__new__(LLMChain)
        chain.vector_store = SimpleNamespace(
            search=lambda *_args, **_kwargs: [
                {"filename": "it_policy.txt", "text": "Only approved software may be installed."}
            ]
        )
        chain.model = "test-model"
        chain.client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(
                                    content="I'm sorry, but I don't have enough information to answer."
                                )
                            )
                        ]
                    )
                )
            )
        )

        result = chain.generate_response("What is the cafeteria menu?")
        self.assertEqual(result["sources"], [])
        self.assertTrue(is_abstention(result["answer"]))

    def test_empty_model_answer_is_replaced_with_no_source_message(self):
        chain = LLMChain.__new__(LLMChain)
        chain.vector_store = SimpleNamespace(
            search=lambda *_args, **_kwargs: [{"filename": "pto.txt", "text": "20 days"}]
        )
        chain.model = "test-model"
        chain.client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **_kwargs: SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
                    )
                )
            )
        )

        result = chain.generate_response("PTO?")
        self.assertTrue(result["answer"])
        self.assertEqual(result["sources"], [])

    def test_abstention_detection_handles_common_phrasing(self):
        self.assertTrue(is_abstention("I could not find relevant documentation."))
        self.assertTrue(is_abstention("That is not mentioned in the provided policy."))
        self.assertTrue(is_abstention("I’m sorry, but I don’t have enough information."))
        self.assertFalse(is_abstention("Employees receive 20 paid leave days annually."))

    def test_no_retrieval_returns_no_sources_without_calling_model(self):
        chain = LLMChain.__new__(LLMChain)
        chain.vector_store = SimpleNamespace(search=lambda *_args, **_kwargs: [])
        chain.client = None

        result = chain.generate_response("What is the cafeteria menu?")
        self.assertEqual(result["sources"], [])
        self.assertTrue(is_abstention(result["answer"]))


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(query_route.router)
        self.app.state.llm_chain = None
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_empty_query_and_missing_answer_service_return_clear_errors(self):
        empty = self.client.post("/query", json={"query": "  "})
        self.assertEqual(empty.status_code, 400)

        missing_field = self.client.post("/query", json={})
        self.assertEqual(missing_field.status_code, 422)

        unavailable = self.client.post("/query", json={"query": "policy"})
        self.assertEqual(unavailable.status_code, 503)
        self.assertIn("GROQ_API_KEY", unavailable.json()["detail"])

    def test_upload_replaces_document_and_updates_listing(self):
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(query_route, "DOCUMENTS_DIR", Path(directory)),
                patch.object(query_route, "rebuild_services", return_value={"documents": 1, "chunks": 1}) as rebuild,
            ):
                response = self.client.post(
                    "/documents/upload",
                    files={"file": ("policy.txt", b"updated policy", "text/plain")},
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(Path(directory, "policy.txt").read_bytes(), b"updated policy")
                self.assertEqual(rebuild.call_count, 1)

                listing = self.client.get("/documents")
                self.assertEqual(listing.json()["documents"][0]["name"], "policy.txt")

                invalid = self.client.post(
                    "/documents/upload",
                    files={"file": ("policy.pdf", b"not text", "application/pdf")},
                )
                self.assertEqual(invalid.status_code, 400)

    def test_provider_errors_return_gateway_status_codes(self):
        class ProviderFailure(Exception):
            pass

        class ProviderTimeout(Exception):
            pass

        def raise_provider_failure(*_args, **_kwargs):
            raise ProviderFailure()

        def raise_provider_timeout(*_args, **_kwargs):
            raise ProviderTimeout()

        self.app.state.llm_chain = SimpleNamespace(generate_response=raise_provider_failure)
        with patch.object(query_route, "GroqError", ProviderFailure):
            failure = self.client.post("/query", json={"query": "policy"})
        self.assertEqual(failure.status_code, 502)

        self.app.state.llm_chain = SimpleNamespace(generate_response=raise_provider_timeout)
        with (
            patch.object(query_route, "APITimeoutError", ProviderTimeout),
            patch.object(query_route, "GroqError", ProviderFailure),
        ):
            timeout = self.client.post("/query", json={"query": "policy"})
        self.assertEqual(timeout.status_code, 504)

    def test_reindex_rebuilds_vector_store_from_document_files(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "policy.txt").write_text("A sample company policy.", encoding="utf-8")
            request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

            class FakeVectorStore:
                def load_or_build_index(self, chunks):
                    self.chunks = chunks
                    self.cache_hit = False
                    self.embedded_chunks = len(chunks)

            fake_store = FakeVectorStore()
            with (
                patch.object(query_route, "DOCUMENTS_DIR", Path(directory)),
                patch.object(query_route, "VectorStore", return_value=fake_store),
                patch.object(query_route, "LLMChain", return_value="configured chain"),
            ):
                result = query_route.rebuild_services(request)

        self.assertEqual(
            result,
            {
                "documents": 1,
                "chunks": 1,
                "cache_hit": False,
                "chunks_reembedded": 1,
            },
        )
        self.assertEqual(fake_store.chunks[0]["filename"], "policy.txt")
        self.assertIs(request.app.state.vector_store, fake_store)
        self.assertEqual(request.app.state.llm_chain, "configured chain")


class MetricsTests(unittest.TestCase):
    def test_metrics_endpoint_reports_query_latency_and_failures(self):
        from backend.main import app

        with TestClient(app) as client:
            response = client.post("/query", json={"query": "  "})
            self.assertEqual(response.status_code, 400)
            metrics = client.get("/metrics").json()

        self.assertGreaterEqual(metrics["query_requests"], 1)
        self.assertGreater(metrics["query_latency"]["median_ms"], 0)
        self.assertGreater(metrics["query_latency"]["p95_ms"], 0)
        self.assertGreaterEqual(metrics["query_failures_by_status"]["400"], 1)
        self.assertGreaterEqual(metrics["query_failures_by_type"]["invalid_query"], 1)


if __name__ == "__main__":
    unittest.main()
