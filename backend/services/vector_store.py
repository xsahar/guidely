import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Load the lightweight embedding model (384 dimensions)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

class VectorStore:
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.chunks_metadata = []

    def build_index(self, chunks: list):
        """Generates embeddings for all chunks and adds them to FAISS."""
        if not chunks:
            print("No chunks provided to build index.")
            return

        texts = [c["text"] for c in chunks]
        print(f"Generating embeddings for {len(texts)} chunks...")
        
        # Convert text chunks to dense vector array
        embeddings = embedding_model.encode(texts, convert_to_numpy=True)
        
        # Add to FAISS index
        self.index.add(np.array(embeddings).astype("float32"))
        self.chunks_metadata = chunks
        print(f"Successfully indexed {self.index.ntotal} vectors into FAISS!")

    def search(self, query: str, top_k: int = 2):
        """Searches FAISS index for the most relevant chunks to the query."""
        if self.index.ntotal == 0:
            return []

        query_vector = embedding_model.encode([query], convert_to_numpy=True).astype("float32")
        distances, indices = self.index.search(query_vector, top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx < len(self.chunks_metadata):
                match = self.chunks_metadata[idx].copy()
                match["score"] = float(dist)
                results.append(match)
        return results