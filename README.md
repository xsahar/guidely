# Guidely — Open-Source Internal RAG Knowledge Assistant

Guidely is a full-stack internal Retrieval-Augmented Generation (RAG) knowledge assistant. It ingests company policy documents, converts them into high-dimensional vector embeddings locally using `sentence-transformers`, indexes them in a local FAISS vector database, and uses the Groq SDK to deliver accurate, grounded answers with strict source citations.

---

## 🌟 Key Features

- **100% Free Stack:** Uses open-source local embedding models (`all-MiniLM-L6-v2`), local FAISS vector storage, and free-tier Groq LLM inference.
- **Decoupled Architecture:** Modular FastAPI backend paired with a fast React + Vite frontend single-page application.
- **Hallucination Prevention:** Strict system prompts prevent model hallucination by enforcing answer grounding solely on retrieved document context.
- **Instant Source Attribution:** Displays explicit source badges for every document chunk retrieved during search.

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

- **`backend/main.py`**: Initializes the FastAPI web application, configures CORS middleware to allow cross-origin requests from `http://localhost:5173`, and mounts application routers.
- **`backend/services/document_loader.py`**: Reads raw `.txt` files from `backend/data/` and splits text into overlapping chunks using a sliding window algorithm.
- **`backend/services/vector_store.py`**: Encodes text chunks into 384-dimensional dense vectors via `all-MiniLM-L6-v2` and performs $L_2$ Euclidean distance similarity searches with FAISS.
- **`backend/services/llm_chain.py`**: Constructs system prompts formatted with retrieved document context and streams requests to the Groq API.
- **`frontend/src/App.jsx`**: Manages search input state, executes asynchronous `POST` requests to `http://127.0.0.1:8000/query`, and dynamically renders response text alongside source document badges.

---

## 🚀 Getting Started

For full step-by-step instructions on setting up your virtual environment, installing dependencies, and running both dev servers, please refer to [SETUP.md](./SETUP.md).