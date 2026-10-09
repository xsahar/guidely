import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.services.document_loader import process_documents
from backend.services.vector_store import VectorStore
from backend.services.llm_chain import LLMChain
from backend.routes.query import router as query_router

app = FastAPI(title="Guidely API", version="1.0.0")

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store instances on app state
app.state.vector_store = VectorStore()
app.state.llm_chain = None


@app.on_event("startup")
def startup_event():
    docs_path = "backend/data/sample-docs"
    if os.path.exists(docs_path):
        chunks = process_documents(docs_path)
        app.state.vector_store.build_index(chunks)
        app.state.llm_chain = LLMChain(vector_store=app.state.vector_store, model="openai/gpt-oss-20b")
        print("Guidely backend initialized and indexed sample docs.")
    else:
        print(f"Warning: Directory '{docs_path}' not found.")


@app.get("/")
def read_root():
    return {"message": "Guidely API is running!"}


# Include routes
app.include_router(query_router)