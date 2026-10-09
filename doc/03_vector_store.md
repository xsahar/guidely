### File 3: `docs/03_vector_store.md`

```markdown
# 03. Vector Embeddings & FAISS Search

## Overview
Converts text chunks into mathematical vectors (embeddings) and indexes them in FAISS for fast semantic search.

* **File Location:** `backend/services/vector_store.py`

---

## Key Components

### 1. Embedding Model (`all-MiniLM-L6-v2`)
* Provided by `SentenceTransformers`.
* Converts any string into a **384-dimensional vector**.
* Maps semantic meaning so terms like *"vacation days"* and *"paid leave"* sit close together in vector space.

### 2. FAISS Index (`faiss.IndexFlatL2`)
* Stores 384-D floating-point vectors in memory.
* Uses **Euclidean Distance ($L2$)** to compute distance between query and document vectors.

---

## Methods & Execution Flow

### `build_index(chunks)`
1. Extracts text from all document chunks.
2. Encodes text into 384-D numerical arrays.
3. Adds arrays to FAISS index and retains matching metadata array.

### `search(query, top_k=2)`
1. Converts user query string (e.g., *"How many vacation days do I get?"*) into a 384-D vector.
2. FAISS searches for the $k$ nearest vector points.
3. Returns top matching text snippets with distance scores.

---

## Complete Pipeline Summary
```text
Text File -> Document Chunks -> 384-D Vector Embeddings -> FAISS Index -> Semantic Match