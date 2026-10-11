# Guidely — Open-Source Internal RAG Knowledge Assistant

Guidely is a full-stack internal Retrieval-Augmented Generation (RAG) knowledge assistant. It ingests company policy documents, converts them into high-dimensional vector embeddings locally using `sentence-transformers`, indexes them in a local FAISS vector database, and uses the Groq SDK to deliver accurate, grounded answers with strict source citations.

---

## 🌟 Key Features

- **100% Free Stack:** Uses open-source local embedding models (`all-MiniLM-L6-v2`), local FAISS vector storage, and free-tier Groq LLM inference.
- **Decoupled Architecture:** Modular FastAPI backend paired with a fast React + Vite frontend single-page application.
- **Hallucination Prevention:** Strict system prompts prevent model hallucination by enforcing answer grounding solely on retrieved document context.
- **Relevant Source Attribution:** Displays only the documents used to answer a question; abstention answers have no source badges.

---

## 🏗️ Architecture & Data Flow

```
[ React / Vite UI ] ──(HTTP POST)──► [ FastAPI Backend ]
  (localhost:5173)                   (127.0.0.1:8000)
                                            │
                                    [ VectorStore ]
                               (sentence-transformers + FAISS)
                                            │
                                      [ LLMChain ]
                                       (Groq SDK)
```

---

## 📁 Directory Structure

```text
guidely/
├── backend/
│   ├── data/                 # Policy text files (.txt) used as knowledge base
│   ├── models/               # Pydantic schemas for API payload validation
│   ├── routes/               # FastAPI route handlers (/query endpoint)
│   ├── services/             # Core RAG engine components
│   │   ├── document_loader.py # Text loading, cleaning, and sliding-window chunking
│   │   ├── vector_store.py    # HuggingFace embeddings & FAISS similarity search
│   │   └── llm_chain.py       # Groq API integration & RAG prompt engineering
│   └── main.py               # FastAPI entry point & CORS middleware configuration
├── frontend/                 # React + Vite single-page application
│   ├── src/
│   │   ├── App.jsx           # Main UI component, state management, and fetch handling
│   │   └── main.jsx          # React DOM entry point
│   ├── package.json          # Frontend dependencies & scripts
│   └── vite.config.js        # Vite build tool configuration
├── docs/                     # System architecture & frontend documentation
│   └── frontend.md           # Deep dive into React state & Vite dev server flow
├── .env                      # Environment variables (GROQ_API_KEY)
├── requirements.txt          # Python backend dependencies
├── README.md                 # Project overview and repository landing page
└── SETUP.md                  # Step-by-step local development setup guide
```

---

## 🔑 Core File Descriptions

- **`backend/main.py`**: Initializes the FastAPI web application, configures CORS for the local Vite frontend, tracks request metrics, and mounts application routers.
- **`backend/services/document_loader.py`**: Reads UTF-8 `.txt` files from `backend/data/sample-docs/`, logs and skips unreadable files, and splits documents into overlapping chunks.
- **`backend/services/vector_store.py`**: Encodes text chunks into normalized 384-dimensional vectors via `all-MiniLM-L6-v2`, persists a content-fingerprinted FAISS cache, and filters low-relevance cosine matches.
- **`backend/services/llm_chain.py`**: Constructs grounded prompts from retrieved context and sends requests to the Groq API.
- **`backend/routes/query.py`**: Handles questions, document listing, text-file upload/replacement, and re-index requests.
- **`frontend/src/App.jsx`**: Provides question and document-management views, including upload/replacement and index refresh.

---

## 🚀 Getting Started

For full step-by-step instructions on setting up your virtual environment, installing dependencies, and running both dev servers, please refer to [SETUP.md](./SETUP.md).

## Evaluation & Metrics

Run the reproducible top-three retrieval evaluation and backend behavior tests from the repository root after installing backend dependencies:

```bash
python tests/evaluate_retrieval.py
python -m unittest discover -s tests -v
```

The seven-question sample retrieval evaluation measured **7/7 correct documents in the top three (100%)** against this small labeled sample set; it exits unsuccessfully below the 80% target. This result is a small-corpus check, not a guarantee of general search quality. Unit tests cover relevant-result filtering, empty/abstention citations, unchanged-index cache reuse, chunk overlap, corrupt UTF-8 input, API errors, metrics, document upload, and re-indexing.

| Metric | Target | Current evidence |
| :--- | :--- | :--- |
| Retrieval@3 | $\ge 80\%$ | 100% (7/7 sample queries; run the script to reproduce) |
| Embedding cache reuse | 100% for unchanged documents | Covered by cache reuse unit test and startup cache-hit log |
| Answer reference coverage | $\ge 90\%$ | Not measured against a labeled live-LLM answer set |
| Median query latency | $<3$ s | Reported by `GET /metrics`; depends on runtime and provider |
| p95 query latency | $<5$ s | Reported by `GET /metrics`; depends on runtime and provider |
| Failure handling | Correct error responses | Covered for empty/missing queries, unavailable service, provider errors/timeouts, invalid uploads, and unreadable documents |
| Source precision | $\ge80\%$ | Not measured against human-labeled answer citations |

`GET /metrics` reports query count, observed median and p95 query latency, HTTP failure counts by status and type, and whether the most recent index load reused cached embeddings. The persistent FAISS cache is invalidated when document content, the embedding model, or vector dimension changes.

The API also exposes `GET /documents`, `POST /documents/upload` (new `.txt` files or replacements), and `POST /documents/reindex`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

Uploaded documents are indexed immediately and can be found by asking about their contents or searching for distinctive terms in their filename. Re-index scans the saved sample documents again; unchanged content reuses the FAISS embedding cache.

### API error behavior
- Empty queries return HTTP 400; malformed/missing fields are rejected by request validation.
- If `GROQ_API_KEY` is missing, the document search service can start, while queries return HTTP 503 with a configuration message.
- Provider timeouts return HTTP 504; other Groq provider failures return HTTP 502.
- Unreadable or invalid UTF-8 documents are logged and skipped during indexing.
- Queries with no sufficiently relevant chunks return an abstention answer with an empty source list.