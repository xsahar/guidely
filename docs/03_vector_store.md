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

### 2. FAISS Index (`faiss.IndexFlatIP`)
* Stores normalized 384-D floating-point vectors in memory.
* Uses inner product on normalized vectors to rank by **cosine similarity**.

---

## Methods & Execution Flow

### `build_index(chunks)`
1. Extracts text from all document chunks.
2. Encodes text into 384-D numerical arrays.
3. Adds arrays to FAISS index and retains matching metadata array.

### `search(query, top_k=3)`
1. Converts user query string (e.g., *"How many vacation days do I get?"*) into a 384-D vector.
2. FAISS searches for the $k$ nearest vector points.
3. Keeps results scoring at least `0.30` and within `0.15` of the best score, so unrelated nearest neighbors are excluded. For short single-word searches, exact terms in filenames or text can also find a matching chunk; three-or-more-character prefixes match identifier tokens such as `wsl` in `wsl2` and `api` in `APIKey`. If no chunk matches, the answer chain returns an abstention with no source citations.

### Persistent cache
The FAISS index and chunk metadata are stored under `backend/data/.vector-cache/`. A SHA-256 fingerprint of the chunk contents, embedding model, and vector dimension invalidates stale cache entries. An unchanged index is loaded without recomputing embeddings.

---

## Complete Pipeline Summary
```text
Text File -> Document Chunks -> 384-D Vector Embeddings -> FAISS Index -> Semantic Match