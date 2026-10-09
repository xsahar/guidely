
```markdown
# Guidely - Project Overview

Guidely is an internal knowledge assistant. It reads company policy text files, converts them into vector embeddings, stores them in a FAISS vector database, and uses OpenAI to answer user questions accurately with source citations.

---

## Folder Structure

```text
guidely/
├── backend/
│   ├── data/
│   │   └── sample-docs/      # Policy text files (.txt) used as the knowledge base
│   ├── models/               # Data structures (Pydantic schemas)
│   ├── routes/               # API endpoint handlers (documents, search, chat)
│   ├── services/             # RAG engine (document parsing, FAISS search, OpenAI)
│   └── main.py               # Main FastAPI server entry point
├── .env                      # API keys and secret configuration
├── .venv/                    # Python virtual environment (installed libraries)
└── requirements.txt          # List of installed Python dependencies

```

---

## Core File Descriptions

* **`backend/main.py`**: Initializes the FastAPI web app, enables CORS middleware, and sets up health check routes.
* **`backend/services/rag_service.py`**: Handles text chunking, FAISS vector indexing, vector retrieval, and OpenAI response generation.
* **`backend/data/sample-docs/`**: Stores plain text files (`.txt`) that the assistant searches to answer queries.
* **`.env`**: Stores the `OPENAI_API_KEY` so secrets remain isolated from application code.
* **`requirements.txt`**: Records package versions for environment reproducibility.

```

```