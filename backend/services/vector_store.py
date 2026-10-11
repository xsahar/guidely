import hashlib
import json
import logging
import re
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(MODEL_NAME)


class VectorStore:
    def __init__(self, dimension: int = 384, cache_dir: Path | None = None):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks_metadata = []
        self.cache_dir = cache_dir or Path(__file__).resolve().parents[1] / "data" / ".vector-cache"
        self.cache_index_path = self.cache_dir / "index.faiss"
        self.cache_metadata_path = self.cache_dir / "metadata.json"
        self.cache_hit = False
        self.embedded_chunks = 0

    def _fingerprint(self, chunks: list[dict]) -> str:
        content = json.dumps(
            {"model": MODEL_NAME, "dimension": self.dimension, "chunks": chunks},
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def load_or_build_index(self, chunks: list[dict]) -> None:
        fingerprint = self._fingerprint(chunks)
        try:
            cache_metadata = json.loads(self.cache_metadata_path.read_text(encoding="utf-8"))
            cached_index = faiss.read_index(str(self.cache_index_path))
            if (
                cache_metadata.get("fingerprint") == fingerprint
                and cache_metadata.get("model") == MODEL_NAME
                and cached_index.d == self.dimension
                and cached_index.ntotal == len(cache_metadata.get("chunks", []))
            ):
                self.index = cached_index
                self.chunks_metadata = cache_metadata["chunks"]
                self.cache_hit = True
                self.embedded_chunks = 0
                logger.info("Loaded cached embeddings for %d unchanged chunks.", cached_index.ntotal)
                return
        except FileNotFoundError:
            pass
        except (OSError, ValueError, RuntimeError) as exc:
            logger.warning("Unable to load embedding cache; rebuilding it: %s", exc)

        self.build_index(chunks)
        self._save_cache(fingerprint)

    def _save_cache(self, fingerprint: str) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        index_temp = self.cache_index_path.with_suffix(".faiss.tmp")
        metadata_temp = self.cache_metadata_path.with_suffix(".json.tmp")
        faiss.write_index(self.index, str(index_temp))
        metadata_temp.write_text(
            json.dumps(
                {
                    "fingerprint": fingerprint,
                    "model": MODEL_NAME,
                    "chunks": self.chunks_metadata,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        index_temp.replace(self.cache_index_path)
        metadata_temp.replace(self.cache_metadata_path)

    def build_index(self, chunks: list[dict]) -> None:
        """Embed chunks into a fresh cosine-similarity FAISS index."""
        new_index = faiss.IndexFlatIP(self.dimension)
        if chunks:
            texts = [
                f"Document: {chunk['filename']}\n{chunk['text']}"
                for chunk in chunks
            ]
            logger.info("Generating embeddings for %d chunks.", len(texts))
            embeddings = embedding_model.encode(
                texts, convert_to_numpy=True, normalize_embeddings=True
            )
            new_index.add(np.asarray(embeddings, dtype="float32"))

        self.index = new_index
        self.chunks_metadata = [dict(chunk) for chunk in chunks]
        self.cache_hit = False
        self.embedded_chunks = len(chunks)
        logger.info("Indexed %d vectors into FAISS.", self.index.ntotal)

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.30,
        score_margin: float = 0.15,
    ) -> list[dict]:
        """Return relevant top-k chunks; do not return weak nearest-neighbor matches."""
        if self.index.ntotal == 0:
            return []

        query_vector = embedding_model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        ).astype("float32")
        limit = min(max(top_k, 1), self.index.ntotal)
        similarities, indices = self.index.search(query_vector, limit)
        best_score = float(similarities[0][0])
        cutoff = max(min_similarity, best_score - score_margin)

        results_by_index = {}
        for similarity, idx in zip(similarities[0], indices[0]):
            if idx != -1 and idx < len(self.chunks_metadata) and similarity >= cutoff:
                match = self.chunks_metadata[idx].copy()
                match["score"] = float(similarity)
                results_by_index[idx] = match

        query_tokens = set(re.findall(r"\w+", query.casefold()))
        is_short_term = (
            len(query_tokens) == 1
            and 2 <= len(query.strip()) <= 5
        )
        if is_short_term:
            acronym = next(iter(query_tokens))

            def contains_term(value: str) -> bool:
                normalized = re.sub(
                    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])",
                    " ",
                    value,
                ).casefold()
                terms = re.findall(r"\w+", normalized)
                return acronym in terms or (
                    len(acronym) >= 3
                    and any(term.startswith(acronym) for term in terms)
                )

            filename_matches = [
                (idx, chunk)
                for idx, chunk in enumerate(self.chunks_metadata)
                if contains_term(re.sub(r"[_-]", " ", chunk["filename"]))
            ]
            exact_matches = filename_matches or [
                (idx, chunk)
                for idx, chunk in enumerate(self.chunks_metadata)
                if contains_term(chunk["text"])
            ]
            for idx, chunk in exact_matches:
                match = chunk.copy()
                match["score"] = max(float(match.get("score", 0)), min_similarity)
                results_by_index[idx] = match

        return sorted(
            results_by_index.values(),
            key=lambda match: (
                match["score"],
                match["filename"].casefold().startswith(f"{query.strip().casefold()}_"),
            ),
            reverse=True,
        )[:limit]
